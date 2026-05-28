import express, { Request, Response } from 'express'
import cors from 'cors'
import { BlindferenceAgent } from './agent'

export type ServerOptions = {
  port: number
  paymentServiceUrl: string
  iclUrl?: string
  ipfsGateway: string
  rpcUrl: string
  privateKey: string
  pinataJwt?: string
  promptKeyStoreAddress?: string
}

export async function startServer(options: ServerOptions): Promise<void> {
  const app = express()
  app.use(cors())
  app.use(express.json())

  const agent = new BlindferenceAgent({
    privateKey: options.privateKey,
    paymentServiceUrl: options.paymentServiceUrl,
    iclUrl: options.iclUrl || options.paymentServiceUrl.replace(':8001', ':8000'),
    ipfsGateway: options.ipfsGateway,
    rpcUrl: options.rpcUrl,
    pinataJwt: options.pinataJwt,
    promptKeyStoreAddress: options.promptKeyStoreAddress,
  })

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok', agent: agent.getAddress() })
  })

  // Get balance
  app.get('/balance', async (_req: Request, res: Response) => {
    try {
      const balance = await agent.getBalance()
      res.json(balance)
    } catch (err: any) {
      res.status(500).json({ error: err.message || 'Failed to fetch balance' })
    }
  })

  // Run inference
  app.post('/infer', async (req: Request, res: Response) => {
    const { prompt, modelId, currency, insurance } = req.body

    if (!prompt || typeof prompt !== 'string') {
      res.status(400).json({ error: 'Missing required field: prompt' })
      return
    }

    try {
      await agent.initCofhe()
      const result = await agent.infer({
        prompt,
        modelId,
        currency: currency || 'cUSDC',
        insurance: insurance || false,
      })

      res.json({
        jobId: result.jobId,
        taskId: result.taskId,
        status: result.status,
        output: result.output,
        outputCid: result.outputCid,
        commitmentHash: result.commitmentHash,
      })
    } catch (err: any) {
      res.status(500).json({ error: err.message || 'Inference failed' })
    }
  })

  // Get job status
  app.get('/status/:jobId', async (req: Request, res: Response) => {
    const { jobId } = req.params
    try {
      // Use the agent's getBalance endpoint pattern or create a direct client
      const axios = (await import('axios')).default
      const resp = await axios.get(`${options.paymentServiceUrl}/v1/jobs/${jobId}`)
      res.json(resp.data)
    } catch (err: any) {
      res.status(500).json({ error: err.message || 'Failed to fetch status' })
    }
  })

  return new Promise((resolve) => {
    app.listen(options.port, () => {
      console.log(`\nBlindference Agent Server running on port ${options.port}`)
      console.log(`   Endpoints:`)
      console.log(`     GET  /health           → Health check`)
      console.log(`     GET  /balance          → Credit balances`)
      console.log(`     POST /infer            → Submit inference (body: { prompt, modelId?, currency?, insurance? })`)
      console.log(`     GET  /status/:jobId    → Job status`)
      console.log(`\n   Press Ctrl+C to stop\n`)
      resolve()
    })
  })
}
