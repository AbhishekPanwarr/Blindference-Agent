import './shim'
import { randomBytes } from 'crypto'
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

// ── Contract Addresses (override via env vars) ────────────────────────
// These match the frontend/ICL deployed contracts on Arbitrum Sepolia.
// Use BLF_PROMPT_KEY_STORE_ADDRESS env var to override without code changes.

const DEFAULT_PROMPT_KEY_STORE_ADDRESS = process.env.BLF_PROMPT_KEY_STORE_ADDRESS || '0x7120fAbdAD2FC5B05CD814A59457eB5fCd9Cfa7E'
const DEFAULT_PAYMENT_WALLET = process.env.BLF_PAYMENT_WALLET_ADDRESS || '0x7F9B413Da50e72415b16Eb9df6e5E59774a338dc'
const DEFAULT_BLIND_TOKEN = process.env.BLF_BLIND_TOKEN_ADDRESS || '0x232D5470DaaC7AD552a42d876aDEF1f778033cE0'
const DEFAULT_CUSDC_TOKEN = process.env.BLF_CUSDC_TOKEN_ADDRESS || '0x42E47f9bA89712C317f60A72C81A610A2b68c48a'

const promptKeyStoreAbi = parseAbi([
  'function storeKey(bytes32 jobId, (uint256 ctHash, uint8 securityZone, uint8 utype, bytes signature) encHigh, (uint256 ctHash, uint8 securityZone, uint8 utype, bytes signature) encLow, address[] allowedNodes)',
  'function getEncryptedKey(bytes32 jobId) view returns (uint256 encHigh, uint256 encLow)',
  'function outputKeys(bytes32 jobId) view returns (uint256 KoH, uint256 KoL)',
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
    // Validate required fields
    if (!config.paymentServiceUrl) {
      throw new Error('paymentServiceUrl is required. Set it to your Payment Service endpoint (e.g. https://payment.blindference.xyz)')
    }
    if (!config.rpcUrl) {
      throw new Error('rpcUrl is required. Set it to your Arbitrum Sepolia RPC endpoint (e.g. https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY)')
    }
    if (!config.privateKey) {
      throw new Error('privateKey is required. Set it via BLF_PRIVATE_KEY env var or pass explicitly.')
    }

    // Normalize private key — ensure 0x prefix for viem
    const rawKey = config.privateKey
    const normalizedKey = rawKey.startsWith('0x') ? rawKey : `0x${rawKey}`

    this.config = {
      paymentServiceUrl: config.paymentServiceUrl,
      iclUrl: config.iclUrl || 'https://icl.blindference.xyz',
      ipfsGateway: config.ipfsGateway || 'https://gateway.pinata.cloud/ipfs',
      pinataJwt: config.pinataJwt || '',
      rpcUrl: config.rpcUrl,
      chainId: config.chainId || 421614,
      promptKeyStoreAddress: config.promptKeyStoreAddress || DEFAULT_PROMPT_KEY_STORE_ADDRESS,
      cofheConfig: config.cofheConfig || {},
      privateKey: normalizedKey,
    }

    this.paymentClient = axios.create({
      baseURL: this.config.paymentServiceUrl,
      headers: { 'Content-Type': 'application/json' },
    })

    this.iclClient = axios.create({
      baseURL: this.config.iclUrl,
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
    // viem version mismatch between project and @cofhe/sdk: cast to unknown then to expected type
    await this.cofheClient.connect(
      this.publicClient as unknown as Parameters<typeof this.cofheClient.connect>[0],
      this.walletClient as unknown as Parameters<typeof this.cofheClient.connect>[1]
    )
  }

  // ── Inference ─────────────────────────────────────────────────────────

  async infer(options: InferOptions): Promise<InferenceResult> {
    // Validate connections before starting
    await this._validateConnections()

    await this.initCofhe()
    if (!this.cofheClient) {
      throw new Error('CoFHE client failed to initialize')
    }

    const modelId = options.modelId || 'groq:llama-3.3-70b-versatile'
    const currency = options.currency || 'cUSDC'
    const insurance = options.insurance || false

    console.log(`[infer] Model: ${modelId}, Currency: ${currency}, Insurance: ${insurance}`)

    // 1. Generate taskId
    const taskId = this._generateTaskId()
    console.log(`[infer] Task ID: ${taskId}`)

    // 2. AES encrypt prompt
    console.log('[infer] Step 1/8: AES-256-GCM encrypting prompt...')
    const aesKey = generateAesKey()
    const { iv, authTag, ciphertext } = encryptAesGcm(options.prompt, aesKey)
    const packedPrompt = packAesPayload(iv, authTag, ciphertext)
    console.log(`[infer] Step 1/8: Done (${packedPrompt.length} bytes)`)

    // 3. Split key into halves
    const { high, low } = splitKeyForCofhe(aesKey)

    // 4. CoFHE encrypt key halves (with retry, matching frontend)
    console.log('[infer] Step 2/8: CoFHE encrypting key halves (this may take 10-30s)...')
    const { highInput, lowInput } = await this._cofheEncryptWithRetry(high, low)
    console.log(`[infer] Step 2/8: Done (high ctHash: ${highInput.ctHash.toString().slice(0, 20)}...)`)

    // 5. Get quorum preview BEFORE storeKey so we can pass node addresses to the contract
    console.log('[infer] Step 3/8: Fetching quorum preview from ICL...')
    let preview: any
    let allowedNodes: string[] = []
    try {
      const previewResp = await this.iclClient.get('/v1/inference/quorum-preview', {
        params: {
          model_id: modelId,
          min_tier: 0,
          verifier_count: 2,
          zdr_required: false,
        },
      })
      preview = previewResp.data
      allowedNodes = [preview.leader, ...preview.verifiers]
      console.log(`[infer] Step 3/8: Done (leader: ${preview.leader.slice(0, 12)}..., ${preview.verifiers.length} verifiers)`)
    } catch (previewErr: any) {
      console.warn('[infer] Step 3/8: Quorum preview failed:', previewErr.message || previewErr)
      console.warn('[infer] Falling back to wallet-only allowedNodes.')
      allowedNodes = [this.getAddress()]
      preview = null
    }

    // 6. Store key on-chain with actual quorum node addresses (or wallet as fallback)
    console.log('[infer] Step 4/8: Storing encrypted key on-chain...')
    const storeTxHash = await this._storePromptKey(taskId, highInput, lowInput, allowedNodes)
    console.log(`[infer] Step 4/8: Done (tx: ${storeTxHash})`)

    // 7. Upload to IPFS
    console.log('[infer] Step 5/8: Uploading encrypted prompt to ICL/IPFS...')
    const promptCid = await this._uploadToIcl(packedPrompt)
    console.log(`[infer] Step 5/8: Done (CID: ${promptCid})`)

    // Extract provider from modelId (e.g., "groq:llama-3.3-70b-versatile" → provider "groq", model "llama-3.3-70b-versatile")
    const modelParts = modelId.split(':')
    const provider = modelParts.length >= 2 ? modelParts[0] : 'unknown'
    const modelName = modelParts.length >= 2 ? modelParts.slice(1).join(':') : modelId

    // 8. Submit job to Payment Service
    console.log('[infer] Step 6/8: Submitting job to Payment Service...')
    const submitResp = await this.paymentClient.post('/v1/jobs/submit', {
      user_address: this.getAddress(),
      prompt_cid: promptCid,
      model_id: modelId,
      encrypted_prompt_key_high: highInput.ctHash.toString(),
      encrypted_prompt_key_low: lowInput.ctHash.toString(),
      payment_mode: 'credits',
      payment_currency: currency.toLowerCase(),
      insurance_opt_in: insurance,
      escrow_id: null,
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
        provider,
        model: modelName,
        is_agent_job: true,
        uavp_enabled: true,
        prompt_key_store_tx: storeTxHash,
        prompt_key_store_status: 'stored_by_user',
        prompt_key_store_address: this.config.promptKeyStoreAddress,
      },
    })

    const jobId = submitResp.data.job_id
    if (!jobId) {
      throw new Error('Payment Service response did not include a job identifier')
    }
    console.log(`[infer] Step 6/8: Done (job_id: ${jobId})`)

    // 9. Poll for completion
    console.log('[infer] Step 7/8: Polling for job completion (this may take 1-3 minutes)...')
    const jobStatus = await this._pollJobStatus(jobId)
    console.log(`[infer] Step 7/8: Done (status: ${jobStatus.status})`)

    if (jobStatus.status !== 'COMPLETED') {
      return {
        jobId,
        taskId,
        status: jobStatus.status as 'FAILED' | 'REJECTED',
      }
    }

    // 10. Decrypt output
    console.log('[infer] Step 8/8: Decrypting output...')
    if (!jobStatus.output_cid) {
      throw new Error('Job completed but no output CID found')
    }
    if (!jobStatus.encrypted_output_key_high || !jobStatus.encrypted_output_key_low) {
      throw new Error('Job completed but no output encryption key handles found in status')
    }

    const outputKey = await this._decryptOutputKey(
      BigInt(jobStatus.encrypted_output_key_high),
      BigInt(jobStatus.encrypted_output_key_low),
    )
    const outputPlaintext = await this._downloadAndDecryptOutput(
      jobStatus.output_cid,
      outputKey,
    )
    console.log('[infer] Step 8/8: Done')

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

  private async _validateConnections(): Promise<void> {
    const errors: string[] = []

    // Test ICL
    try {
      await this.iclClient.get('/health', { timeout: 5000 })
    } catch (err: any) {
      errors.push(`ICL unreachable at ${this.config.iclUrl}: ${err.message || err}`)
    }

    // Test Payment Service
    try {
      await this.paymentClient.get('/health', { timeout: 5000 })
    } catch (err: any) {
      errors.push(`Payment Service unreachable at ${this.config.paymentServiceUrl}: ${err.message || err}`)
    }

    // Test RPC
    try {
      await this.publicClient.getBlockNumber()
    } catch (err: any) {
      errors.push(`RPC unreachable at ${this.config.rpcUrl}: ${err.message || err}`)
    }

    if (errors.length > 0) {
      throw new Error(
        'Connection validation failed. Please check your endpoints and ensure services are running.\n' +
        '  If services are local, ensure:\n' +
        '    ICL:           cd network/packages/icl && uvicorn main:app --host 0.0.0.0 --port 8000\n' +
        '    Payment Service: cd network/packages/icl && (check payment service port, usually 8001)\n' +
        '\nErrors:\n  - ' + errors.join('\n  - ')
      )
    }

    console.log('[validate] All services reachable (ICL, Payment Service, RPC)')
  }

  private async _cofheEncryptWithRetry(high: bigint, low: bigint): Promise<{ highInput: any; lowInput: any }> {
    if (!this.cofheClient) {
      throw new Error('CoFHE client not initialized')
    }

    const COFHE_RETRY_ERRORS = [
      'Failed to fetch',
      'Failed to fetch FHE key and CRS',
      'Error serializing FHE publicKey',
      'Error serializing CRS',
      'NetworkError',
    ]

    function isRetryable(err: unknown): boolean {
      const msg = err instanceof Error ? err.message : String(err)
      return COFHE_RETRY_ERRORS.some((p) => msg.includes(p))
    }

    try {
      const encResult = await this.cofheClient
        .encryptInputs([Encryptable.uint128(high), Encryptable.uint128(low)])
        .execute()
      return { highInput: encResult[0], lowInput: encResult[1] }
    } catch (firstErr) {
      if (!isRetryable(firstErr)) throw firstErr

      console.warn('[infer] CoFHE encrypt failed with transient error, retrying once:', firstErr)
      const encResult = await this.cofheClient
        .encryptInputs([Encryptable.uint128(high), Encryptable.uint128(low)])
        .execute()
      return { highInput: encResult[0], lowInput: encResult[1] }
    }
  }

  private _generateTaskId(): string {
    const bytes = randomBytes(32)
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
    allowedNodes?: string[],
  ): Promise<string> {
    const toContractInput = (item: EncryptedItemInput) => ({
      ctHash: item.ctHash,
      securityZone: item.securityZone ?? 0,
      utype: Number(item.utype),
      signature: item.signature as Hex,
    })

    const safeAllowedNodes = allowedNodes && allowedNodes.length > 0
      ? allowedNodes
      : [this.walletClient.account!.address]

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
        safeAllowedNodes.map((addr) => addr as Hex),
      ],
      ...feeParams,
    })

    const receipt = await this.publicClient.waitForTransactionReceipt({ hash })
    if (receipt.status !== 'success') {
      throw new Error(`PromptKeyStore transaction failed for task ${taskId}`)
    }

    return hash
  }

  private async _pollJobStatus(jobId: string, maxAttempts = 120): Promise<any> {
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

    throw new Error(`Polling timed out after ${maxAttempts} attempts (~${Math.round(maxAttempts * 3 / 60)} minutes). The job may still be processing; check status with: node dist/cli.js status ${jobId}`)
  }

  private async _decryptOutputKey(highHandle: bigint, lowHandle: bigint): Promise<Buffer> {
    if (!this.cofheClient) {
      throw new Error('CoFHE client not initialized')
    }

    let permit = await this.cofheClient.permits.getOrCreateSelfPermit()
    const nowSec = Math.floor(Date.now() / 1000)
    if (permit.expiration < nowSec) {
      await this.cofheClient.permits.removeActivePermit()
      permit = await this.cofheClient.permits.getOrCreateSelfPermit()
    }

    const high = await this.cofheClient
      .decryptForView(highHandle, FheTypes.Uint128)
      .withPermit(permit)
      .execute()
    const low = await this.cofheClient
      .decryptForView(lowHandle, FheTypes.Uint128)
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
    return DEFAULT_CUSDC_TOKEN
  }
}
