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
import { createCofheConfig, createCofheClient } from '@cofhe/sdk/node'
import { chains } from '@cofhe/sdk/chains'
import { Encryptable, FheTypes } from '@cofhe/sdk'
import type { CofheClient, EncryptedItemInput } from '@cofhe/sdk'

import {
  generateAesKey,
  encryptAesGcm,
  decryptAesGcm,
  packAesPayload,
  unpackAesPayload,
  splitKeyForCofhe,
  combineKeyHalves,
  uploadToIpfs,
  downloadFromIpfs,
} from './crypto'

// ── Types ───────────────────────────────────────────────────────────────

export type BlindferenceAgentConfig = {
  privateKey: string
  paymentServiceUrl: string
  iclUrl?: string
  ipfsGateway?: string
  pinataJwt?: string
  rpcUrl: string
  chainId?: number
  promptKeyStoreAddress?: string
  cofheConfig?: Record<string, unknown>
}

export type InferOptions = {
  prompt: string
  modelId?: string
  currency?: 'BLIND' | 'cUSDC'
  insurance?: boolean
}

export type InferenceResult = {
  jobId: string
  taskId: string
  status: 'COMPLETED' | 'FAILED' | 'REJECTED'
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

export type DeveloperStats = {
  total_jobs: number
  completed: number
  failed: number
  rejected: number
  total_cusdc_spent: number
  total_blind_spent: number
}

// ── Constants ───────────────────────────────────────────────────────────

const DEFAULT_PROMPT_KEY_STORE_ADDRESS = '0x1E22dD12f448B15f1Ca8560fB6B4463834FaAf73'
const DEFAULT_PAYMENT_WALLET = '0x7F9B413Da50e72415b16Eb9df6e5E59774a338dc'
const DEFAULT_BLIND_TOKEN = '0x232D5470DaaC7AD552a42d876aDEF1f778033cE0'

const promptKeyStoreAbi = parseAbi([
  'function storeKey(bytes32 jobId, (uint256 ctHash, uint8 securityZone, uint8 utype, bytes signature) encHigh, (uint256 ctHash, uint8 securityZone, uint8 utype, bytes signature) encLow, address[] allowedNodes)',
  'function getEncryptedKey(bytes32 jobId) view returns ((uint256 ctHash, uint8 securityZone, uint8 utype, bytes signature) encHigh, (uint256 ctHash, uint8 securityZone, uint8 utype, bytes signature) encLow)',
])

// ── Agent Class ─────────────────────────────────────────────────────────

export class BlindferenceAgent {
  private paymentClient: AxiosInstance
  private iclClient: AxiosInstance
  private walletClient: WalletClient
  private publicClient: PublicClient
  private config: Required<BlindferenceAgentConfig> & {
    iclUrl: string
    ipfsGateway: string
  }
  private cofheClient: CofheClient | null = null

  constructor(config: BlindferenceAgentConfig) {
    this.config = {
      paymentServiceUrl: config.paymentServiceUrl,
      iclUrl: config.iclUrl || config.paymentServiceUrl.replace(':8001', ':8000'),
      ipfsGateway: config.ipfsGateway || 'https://gateway.pinata.cloud/ipfs',
      pinataJwt: config.pinataJwt || '',
      rpcUrl: config.rpcUrl,
      chainId: config.chainId || 421614,
      promptKeyStoreAddress: config.promptKeyStoreAddress || DEFAULT_PROMPT_KEY_STORE_ADDRESS,
      cofheConfig: config.cofheConfig || {},
      privateKey: config.privateKey,
    }

    this.paymentClient = axios.create({
      baseURL: this.config.paymentServiceUrl,
      headers: { 'Content-Type': 'application/json' },
    })

    this.iclClient = axios.create({
      baseURL: this.config.iclUrl,
      headers: { 'Content-Type': 'application/json' },
    })

    const account = privateKeyToAccount(config.privateKey as Hex)
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

  // ── CoFHE Client ──────────────────────────────────────────────────────

  async initCofhe(): Promise<void> {
    if (this.cofheClient) return

    const cofheConfig = createCofheConfig({
      supportedChains: [chains.arbSepolia],
      useWorkers: false,
      fheKeyStorage: null,
      ...this.config.cofheConfig,
    })

    this.cofheClient = createCofheClient(cofheConfig)
    if (!this.cofheClient) {
      throw new Error('Failed to create CoFHE client')
    }
    // @ts-ignore — viem version mismatch between project and @cofhe/sdk
    await this.cofheClient.connect(this.publicClient as any, this.walletClient as any)
  }

  // ── Inference ─────────────────────────────────────────────────────────

  async infer(options: InferOptions): Promise<InferenceResult> {
    await this.initCofhe()
    if (!this.cofheClient) {
      throw new Error('CoFHE client failed to initialize')
    }

    const modelId = options.modelId || 'groq:llama-3.3-70b-versatile'
    const currency = options.currency || 'cUSDC'
    const insurance = options.insurance || false

    // 1. Generate taskId
    const taskId = this._generateTaskId()

    // 2. AES encrypt prompt
    const aesKey = generateAesKey()
    const { iv, authTag, ciphertext } = encryptAesGcm(options.prompt, aesKey)
    const packedPrompt = packAesPayload(iv, authTag, ciphertext)

    // 3. Upload to IPFS (via ICL endpoint)
    const promptCid = await this._uploadToIcl(packedPrompt)

    // 4. Split key into halves
    const { high, low } = splitKeyForCofhe(aesKey)

    // 5. CoFHE encrypt key halves
    const encResult = await this.cofheClient
      .encryptInputs([Encryptable.uint128(high), Encryptable.uint128(low)])
      .execute()
    const highInput = encResult[0]
    const lowInput = encResult[1]

    // 6. Store key on-chain
    const storeTxHash = await this._storePromptKey(taskId, highInput, lowInput)

    // 7. Get quorum preview
    const previewResp = await this.iclClient.post('/v1/inference/quorum-preview', {
      model_id: modelId,
      min_tier: 0,
      verifier_count: 2,
      zdr_required: false,
    })
    const preview = previewResp.data

    // 8. Submit job to Payment Service
    const submitResp = await this.paymentClient.post('/v1/jobs/submit', {
      user_address: this.getAddress(),
      prompt_cid: promptCid,
      model_id: modelId,
      encrypted_prompt_key_high: highInput.ctHash.toString(),
      encrypted_prompt_key_low: lowInput.ctHash.toString(),
      payment_mode: 'credits',
      payment_currency: currency.toLowerCase(),
      insurance_opt_in: insurance,
      task_id: taskId,
      min_tier: 0,
      zdr_required: false,
      verifier_count: 2,
      permits: [],
      metadata: {
        cofhe_prompt_key_inputs: {
          high: this._serializeEncryptedInput(highInput),
          low: this._serializeEncryptedInput(lowInput),
        },
        prompt_length: options.prompt.length,
        vertical: 'blindference-text-demo',
        model: modelId,
        is_agent_job: true,
        uavp_enabled: true,
        prompt_key_store_tx: storeTxHash,
        prompt_key_store_status: 'stored_by_user',
        prompt_key_store_address: this.config.promptKeyStoreAddress,
        source: 'sdk',
      },
    })

    const jobId = submitResp.data.job_id
    if (!jobId) {
      throw new Error('Payment Service response did not include a job identifier')
    }

    // 9. Poll for completion
    const jobStatus = await this._pollJobStatus(jobId)

    if (jobStatus.status !== 'COMPLETED') {
      return {
        jobId,
        taskId,
        status: jobStatus.status as 'FAILED' | 'REJECTED',
      }
    }

    // 10. Decrypt output
    if (!jobStatus.output_cid) {
      throw new Error('Job completed but no output CID found')
    }

    const outputKey = await this._decryptOutputKey(taskId)
    const outputPlaintext = await this._downloadAndDecryptOutput(
      jobStatus.output_cid,
      outputKey,
    )

    return {
      jobId,
      taskId,
      status: 'COMPLETED',
      output: outputPlaintext,
      outputCid: jobStatus.output_cid,
      commitmentHash: jobStatus.result_hash,
    }
  }

  // ── Credits ───────────────────────────────────────────────────────────

  async getBalance(address?: string): Promise<CreditBalance> {
    const addr = address || this.getAddress()
    const resp = await this.paymentClient.get<CreditBalance>(`/v1/balance/${addr}`)
    return resp.data
  }

  async getPackages(): Promise<CreditPackage[]> {
    const resp = await this.paymentClient.get<{ packages: CreditPackage[] }>('/v1/credits/packages')
    return resp.data.packages
  }

  async deposit(amountWei: bigint, currency: 'BLIND' | 'cUSDC'): Promise<string> {
    const tokenAddress = currency === 'BLIND' ? DEFAULT_BLIND_TOKEN : await this._getCusdcTokenAddress()
    const paymentWallet = await this._getPaymentWalletAddress()

    const txHash = await this.walletClient.writeContract({
      address: tokenAddress as Hex,
      abi: parseAbi(['function transfer(address to, uint256 amount) returns (bool)']),
      functionName: 'transfer',
      args: [paymentWallet as Hex, amountWei],
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

    const txHash = await this.deposit(BigInt(pkg.price_blind_wei), 'BLIND')

    const resp = await this.paymentClient.post<CreditBalance & { status: string; package_id: string; credits_awarded_cusdc: number; tx_hash: string }>(
      '/v1/credits/purchase-package',
      {
        package_id: packageId,
        tx_hash: txHash,
      }
    )

    return { balance: resp.data, txHash }
  }

  // ── Developer Stats ───────────────────────────────────────────────────

  async getDeveloperStats(address?: string): Promise<DeveloperStats> {
    const addr = address || this.getAddress()
    const resp = await this.paymentClient.get<DeveloperStats>(`/v1/developers/${addr}/stats`)
    return resp.data
  }

  // ── Private Helpers ───────────────────────────────────────────────────

  private _generateTaskId(): string {
    const bytes = Buffer.alloc(32)
    for (let i = 0; i < 32; i++) {
      bytes[i] = Math.floor(Math.random() * 256)
    }
    return '0x' + bytes.toString('hex')
  }

  private async _uploadToIcl(data: Buffer): Promise<string> {
    const FormData = (await import('form-data')).default
    const form = new FormData()
    form.append('file', data, { filename: 'blindference-text-prompt.bin' })

    const resp = await this.iclClient.post('/v1/inference/upload-prompt', form, {
      headers: form.getHeaders(),
    })

    return resp.data.cid
  }

  private async _storePromptKey(
    taskId: string,
    highInput: EncryptedItemInput,
    lowInput: EncryptedItemInput,
  ): Promise<string> {
    const toContractInput = (item: EncryptedItemInput) => ({
      ctHash: item.ctHash,
      securityZone: item.securityZone ?? 0,
      utype: Number(item.utype),
      signature: item.signature as Hex,
    })

    const safeAllowedNodes = [this.walletClient.account!.address]

    const latestBlock = await this.publicClient.getBlock({ blockTag: 'latest' })
    const fallbackPriorityFeePerGas = 2_000_000n
    const maxPriorityFeePerGas = await this.publicClient
      .estimateMaxPriorityFeePerGas()
      .catch(() => fallbackPriorityFeePerGas)
    const priorityFeePerGas = maxPriorityFeePerGas > 0n ? maxPriorityFeePerGas : fallbackPriorityFeePerGas
    const baseFeePerGas = latestBlock.baseFeePerGas
    const feeParams =
      baseFeePerGas != null
        ? {
            maxPriorityFeePerGas: priorityFeePerGas,
            maxFeePerGas: baseFeePerGas * 2n + priorityFeePerGas + 1_000_000n,
          }
        : {
            gasPrice: await this.publicClient.getGasPrice(),
          }

    const hash = await this.walletClient.writeContract({
      account: this.walletClient.account!,
      address: this.config.promptKeyStoreAddress as Hex,
      abi: promptKeyStoreAbi,
      chain: arbitrumSepolia,
      functionName: 'storeKey',
      args: [
        taskId as Hex,
        toContractInput(highInput),
        toContractInput(lowInput),
        safeAllowedNodes,
      ],
      ...feeParams,
    })

    const receipt = await this.publicClient.waitForTransactionReceipt({ hash })
    if (receipt.status !== 'success') {
      throw new Error(`PromptKeyStore transaction failed for task ${taskId}`)
    }

    return hash
  }

  private async _pollJobStatus(jobId: string, maxAttempts = 60): Promise<any> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 3000))

      const resp = await this.paymentClient.get(`/v1/jobs/${jobId}`)
      const data = resp.data

      if (data.status === 'COMPLETED') {
        return data
      }

      if (data.status === 'FAILED' || data.status === 'REFUNDED') {
        return { status: 'FAILED', ...data }
      }
    }

    throw new Error(`Polling timed out after ${maxAttempts} attempts`)
  }

  private async _decryptOutputKey(taskId: string): Promise<Buffer> {
    if (!this.cofheClient) {
      throw new Error('CoFHE client not initialized')
    }

    const keyData = await this.publicClient.readContract({
      address: this.config.promptKeyStoreAddress as Hex,
      abi: promptKeyStoreAbi,
      functionName: 'getEncryptedKey',
      args: [taskId as Hex],
    })

    // keyData is [encHigh, encLow] each with ctHash, securityZone, utype, signature
    const encHigh = keyData[0] as any
    const encLow = keyData[1] as any

    let permit = await this.cofheClient.permits.getOrCreateSelfPermit()
    const nowSec = Math.floor(Date.now() / 1000)
    if (permit.expiration < nowSec) {
      await this.cofheClient.permits.removeActivePermit()
      permit = await this.cofheClient.permits.getOrCreateSelfPermit()
    }

    const high = await this.cofheClient
      .decryptForView(BigInt(encHigh.ctHash.toString()), FheTypes.Uint128)
      .withPermit(permit)
      .execute()
    const low = await this.cofheClient
      .decryptForView(BigInt(encLow.ctHash.toString()), FheTypes.Uint128)
      .withPermit(permit)
      .execute()

    return combineKeyHalves(high, low)
  }

  private async _downloadAndDecryptOutput(cid: string, key: Buffer): Promise<string> {
    const data = await downloadFromIpfs(cid, this.config.ipfsGateway)
    const { iv, authTag, ciphertext } = unpackAesPayload(data)
    return decryptAesGcm(ciphertext, key, iv, authTag)
  }

  private _serializeEncryptedInput(input: EncryptedItemInput): Record<string, unknown> {
    return {
      ctHash: input.ctHash.toString(),
      securityZone: input.securityZone,
      utype: Number(input.utype),
      signature: input.signature,
    }
  }

  private async _getPaymentWalletAddress(): Promise<string> {
    return DEFAULT_PAYMENT_WALLET
  }

  private async _getCusdcTokenAddress(): Promise<string> {
    // For cUSDC, we'd need the token address. In the frontend this comes from env.
    // For now, return a placeholder — the deposit method is only used for BLIND in practice.
    return '0x42E47f9bA89712C317f60A72C81A610A2b68c48a'
  }
}
