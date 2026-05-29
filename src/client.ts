import axios, { AxiosInstance } from 'axios'
import {
  createWalletClient,
  createPublicClient,
  http,
  parseAbi,
  type Hex,
  type WalletClient,
  type PublicClient,
  type Chain,
} from 'viem'
import { privateKeyToAccount } from 'viem/accounts'
import { arbitrumSepolia } from 'viem/chains'

export type InferenceClientConfig = {
  privateKey: string
  iclBaseUrl: string
  paymentBaseUrl: string
  rpcUrl: string
  chainId?: number
  pinataJwt?: string
}

export type InferenceResult = {
  requestId: string
  taskId: string
  status: string
  output?: string
  outputCid?: string
  commitmentHash?: string
}

export type CreditBalance = {
  user_address: string
  balance_cusdc: number
  balance_blind: number
  total_deposited_cusdc: number
  total_deposited_blind: number
  total_spent_cusdc: number
  total_spent_blind: number
}

export type CreditPackage = {
  id: string
  name: string
  base_calls: number
  bonus_percent: number
  total_calls: number
  price_blind: number
  price_blind_wei: number
}

export class InferenceClient {
  private iclClient: AxiosInstance
  private paymentClient: AxiosInstance
  private walletClient: WalletClient
  private publicClient: PublicClient
  private config: Required<InferenceClientConfig>

  constructor(config: InferenceClientConfig) {
    // Validate required fields
    if (!config.iclBaseUrl) {
      throw new Error('iclBaseUrl is required. Set it to your ICL endpoint (e.g. https://icl.blindference.xyz)')
    }
    if (!config.paymentBaseUrl) {
      throw new Error('paymentBaseUrl is required. Set it to your Payment Service endpoint')
    }
    if (!config.rpcUrl) {
      throw new Error('rpcUrl is required. Set it to your Arbitrum Sepolia RPC endpoint')
    }
    if (!config.privateKey) {
      throw new Error('privateKey is required')
    }

    // Normalize private key — ensure 0x prefix for viem
    const rawKey = config.privateKey
    const normalizedKey = rawKey.startsWith('0x') ? rawKey : `0x${rawKey}`

    this.config = {
      chainId: 421614,
      pinataJwt: '',
      ...config,
      privateKey: normalizedKey,
    }

    this.iclClient = axios.create({
      baseURL: this.config.iclBaseUrl,
      headers: { 'Content-Type': 'application/json' },
    })

    this.paymentClient = axios.create({
      baseURL: this.config.paymentBaseUrl,
      headers: { 'Content-Type': 'application/json' },
    })

    const account = privateKeyToAccount(this.config.privateKey as Hex)
    const chain: Chain = arbitrumSepolia

    this.walletClient = createWalletClient({
      account,
      chain,
      transport: http(this.config.rpcUrl),
    })

    this.publicClient = createPublicClient({
      chain,
      transport: http(this.config.rpcUrl),
    })
  }

  getAddress(): string {
    return this.walletClient.account!.address
  }

  // ── Credit & Payment ──────────────────────────────────────────────

  async getBalance(address?: string): Promise<CreditBalance> {
    const addr = address || this.getAddress()
    const resp = await this.paymentClient.get<CreditBalance>(`/v1/balance/${addr}`)
    return resp.data
  }

  async getPackages(): Promise<CreditPackage[]> {
    const resp = await this.paymentClient.get<{ packages: CreditPackage[] }>('/v1/credits/packages')
    return resp.data.packages
  }

  async depositBLIND(amountWei: bigint): Promise<string> {
    const paymentWalletAddress = await this._getPaymentWalletAddress()
    const blindTokenAddress = await this._getBlindTokenAddress()

    const txHash = await this.walletClient.writeContract({
      address: blindTokenAddress as Hex,
      abi: parseAbi(['function transfer(address to, uint256 amount) returns (bool)']),
      functionName: 'transfer',
      args: [paymentWalletAddress as Hex, amountWei],
      chain: arbitrumSepolia,
      account: this.walletClient.account!,
    })

    await this.publicClient.waitForTransactionReceipt({ hash: txHash })
    return txHash
  }

  async purchasePackage(packageId: string): Promise<{ balance: CreditBalance; txHash: string }> {
    const packages = await this.getPackages()
    const pkg = packages.find((p) => p.id === packageId)
    if (!pkg) {
      throw new Error(`Package ${packageId} not found`)
    }

    const txHash = await this.depositBLIND(BigInt(pkg.price_blind_wei))

    const resp = await this.paymentClient.post<CreditBalance & { status: string; package_id: string; credits_awarded_cusdc: number; tx_hash: string }>(
      '/v1/credits/purchase-package',
      {
        package_id: packageId,
        tx_hash: txHash,
      }
    )

    return { balance: resp.data, txHash }
  }

  // ── Inference ───────────────────────────────────────────────────────

  async submitEncryptedInference(
    payload: {
      taskId: string
      promptCid: string
      encryptedPromptKey: { high: string; low: string }
      modelId?: string
      paymentMode?: 'escrow' | 'credits'
      paymentCurrency?: 'cusdc' | 'blind'
      source?: 'frontend' | 'sdk'
    },
    options?: { insurance?: boolean }
  ): Promise<InferenceResult> {
    const modelId = payload.modelId || 'groq:llama-3.3-70b-versatile'

    // Get quorum preview
    const previewResp = await this.iclClient.post('/v1/inference/quorum-preview', {
      model_id: modelId,
      min_tier: 0,
      verifier_count: 2,
      zdr_required: false,
    })
    const preview = previewResp.data

    // Submit to ICL
    const resp = await this.iclClient.post('/v1/inference/requests', {
      developer_address: this.getAddress(),
      task_id: payload.taskId,
      mode: 'text',
      model_id: modelId,
      text_request: {
        prompt_cid: payload.promptCid,
        encrypted_prompt_key: payload.encryptedPromptKey,
        model_id: modelId,
        coverage_enabled: options?.insurance || false,
      },
      leader_address: preview.leader,
      verifier_addresses: preview.verifiers,
      min_tier: 0,
      zdr_required: false,
      verifier_count: 2,
      payment_mode: payload.paymentMode || 'credits',
      payment_currency: payload.paymentCurrency || 'blind',
      metadata: {
        source: payload.source || 'sdk',
      },
    })

    const data = resp.data as any
    const requestId = data.request_id || data.job_id

    if (!requestId) {
      throw new Error('ICL response did not include a request identifier')
    }

    // Poll for completion
    return this._pollUntilComplete(requestId)
  }

  // ── Private Helpers ─────────────────────────────────────────────────

  private async _getPaymentWalletAddress(): Promise<string> {
    // For now, fetch from Payment Service health endpoint or config
    // In production, this should be configurable
    const resp = await this.paymentClient.get('/health')
    // Health endpoint doesn't expose wallet address, so we use a default
    // This should be improved in production
    return '0x7F9B413Da50e72415b16Eb9df6e5E59774a338dc'
  }

  private async _getBlindTokenAddress(): Promise<string> {
    // Fetch from Payment Service or use default
    return '0x232D5470DaaC7AD552a42d876aDEF1f778033cE0'
  }

  private async _pollUntilComplete(requestId: string, maxAttempts = 60): Promise<InferenceResult> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 3000))

      const resp = await this.iclClient.get(`/v1/inference/${requestId}/status`)
      const data = resp.data as any

      if (data.status === 'ACCEPTED' || data.status === 'accepted') {
        return {
          requestId,
          taskId: data.task_id || data.job_id,
          status: 'COMPLETED',
          outputCid: data.output_cid,
          commitmentHash: data.commitment_hash,
        }
      }

      if (data.status === 'REJECTED' || data.status === 'rejected') {
        return {
          requestId,
          taskId: data.task_id || data.job_id,
          status: 'REJECTED',
        }
      }

      if (data.status === 'FAILED' || data.status === 'failed') {
        return {
          requestId,
          taskId: data.task_id || data.job_id,
          status: 'FAILED',
        }
      }
    }

    throw new Error(`Polling timed out after ${maxAttempts} attempts`)
  }
}
