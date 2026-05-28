#!/usr/bin/env node

import { Command } from 'commander'
import { BlindferenceAgent } from './agent'
import { startServer } from './server'

const program = new Command()

program
  .name('blindference-agent')
  .description('Blindference Agent SDK CLI')
  .version('0.1.0')

program
  .command('start')
  .description('Start the local pipeline server')
  .option('-p, --port <port>', 'Server port', '4000')
  .option('--payment-service <url>', 'Payment Service URL', 'http://localhost:8001')
  .option('--icl <url>', 'ICL URL (defaults to payment service port -1)')
  .option('--ipfs-gateway <url>', 'IPFS download gateway', 'https://gateway.pinata.cloud/ipfs')
  .option('--rpc-url <url>', 'Arbitrum Sepolia RPC URL', 'https://sepolia-rollup.arbitrum.io/rpc')
  .option('--pinata-jwt <jwt>', 'Pinata JWT for direct IPFS uploads')
  .option('--prompt-key-store <address>', 'PromptKeyStore contract address')
  .action(async (options) => {
    const privateKey = process.env.BLINDFERENCE_PRIVATE_KEY || process.env.PRIVATE_KEY
    if (!privateKey) {
      console.error('Error: BLINDFERENCE_PRIVATE_KEY or PRIVATE_KEY environment variable is required')
      process.exit(1)
    }

    const port = parseInt(options.port, 10)
    const iclUrl = options.icl || options.paymentService.replace(':8001', ':8000')

    console.log(`Starting Blindference Agent Server on port ${port}...`)
    console.log(`  Payment Service: ${options.paymentService}`)
    console.log(`  ICL: ${iclUrl}`)
    console.log(`  RPC: ${options.rpcUrl}`)

    await startServer({
      port,
      paymentServiceUrl: options.paymentService,
      iclUrl,
      ipfsGateway: options.ipfsGateway,
      rpcUrl: options.rpcUrl,
      privateKey,
      pinataJwt: options.pinataJwt,
      promptKeyStoreAddress: options.promptKeyStore,
    })
  })

program
  .command('infer')
  .description('Run a single inference job')
  .requiredOption('--prompt <text>', 'The prompt text')
  .option('--model <modelId>', 'Model ID', 'groq:llama-3.3-70b-versatile')
  .option('--currency <currency>', 'Payment currency', 'cUSDC')
  .option('--insurance', 'Enable insurance', false)
  .option('--payment-service <url>', 'Payment Service URL', 'http://localhost:8001')
  .option('--icl <url>', 'ICL URL')
  .option('--ipfs-gateway <url>', 'IPFS download gateway', 'https://gateway.pinata.cloud/ipfs')
  .option('--rpc-url <url>', 'Arbitrum Sepolia RPC URL', 'https://sepolia-rollup.arbitrum.io/rpc')
  .option('--prompt-key-store <address>', 'PromptKeyStore contract address')
  .action(async (options) => {
    const privateKey = process.env.BLINDFERENCE_PRIVATE_KEY || process.env.PRIVATE_KEY
    if (!privateKey) {
      console.error('Error: BLINDFERENCE_PRIVATE_KEY or PRIVATE_KEY environment variable is required')
      process.exit(1)
    }

    const agent = new BlindferenceAgent({
      privateKey,
      paymentServiceUrl: options.paymentService,
      iclUrl: options.icl || options.paymentService.replace(':8001', ':8000'),
      ipfsGateway: options.ipfsGateway,
      rpcUrl: options.rpcUrl,
      promptKeyStoreAddress: options.promptKeyStore,
    })

    try {
      console.log('Initializing CoFHE client...')
      await agent.initCofhe()
      console.log('Submitting inference...')

      const result = await agent.infer({
        prompt: options.prompt,
        modelId: options.model,
        currency: options.currency,
        insurance: options.insurance,
      })

      if (result.status === 'COMPLETED') {
        console.log('\n✅ Inference completed')
        console.log(`   Job ID:    ${result.jobId}`)
        console.log(`   Task ID:   ${result.taskId}`)
        if (result.output) {
          console.log(`\n   Output:\n   ${result.output}`)
        }
      } else {
        console.log(`\n❌ Inference ${result.status}`)
        console.log(`   Job ID:  ${result.jobId}`)
        console.log(`   Task ID: ${result.taskId}`)
      }
    } catch (err: any) {
      console.error('Error:', err.message || err)
      process.exit(1)
    }
  })

program
  .command('balance')
  .description('Print credit balances for the configured wallet')
  .option('--payment-service <url>', 'Payment Service URL', 'http://localhost:8001')
  .action(async (options) => {
    const privateKey = process.env.BLINDFERENCE_PRIVATE_KEY || process.env.PRIVATE_KEY
    if (!privateKey) {
      console.error('Error: BLINDFERENCE_PRIVATE_KEY or PRIVATE_KEY environment variable is required')
      process.exit(1)
    }

    const agent = new BlindferenceAgent({
      privateKey,
      paymentServiceUrl: options.paymentService,
      rpcUrl: 'https://sepolia-rollup.arbitrum.io/rpc',
    })

    try {
      const balance = await agent.getBalance()
      console.log('\n💰 Credit Balances')
      console.log(`   Address:   ${balance.user_address}`)
      console.log(`   cUSDC:     ${balance.balance_cusdc}`)
      console.log(`   BLIND:     ${balance.balance_blind}`)
      console.log(`   Total Deposited cUSDC: ${balance.total_deposited_cusdc}`)
      console.log(`   Total Deposited BLIND: ${balance.total_deposited_blind}`)
      console.log(`   Total Spent cUSDC:     ${balance.total_spent_cusdc}`)
      console.log(`   Total Spent BLIND:     ${balance.total_spent_blind}`)
    } catch (err: any) {
      console.error('Error:', err.message || err)
      process.exit(1)
    }
  })

program
  .command('buy-package')
  .description('Purchase a credit package')
  .requiredOption('--id <packageId>', 'Package ID (e.g. starter, pro, enterprise)')
  .option('--payment-service <url>', 'Payment Service URL', 'http://localhost:8001')
  .option('--rpc-url <url>', 'Arbitrum Sepolia RPC URL', 'https://sepolia-rollup.arbitrum.io/rpc')
  .action(async (options) => {
    const privateKey = process.env.BLINDFERENCE_PRIVATE_KEY || process.env.PRIVATE_KEY
    if (!privateKey) {
      console.error('Error: BLINDFERENCE_PRIVATE_KEY or PRIVATE_KEY environment variable is required')
      process.exit(1)
    }

    const agent = new BlindferenceAgent({
      privateKey,
      paymentServiceUrl: options.paymentService,
      rpcUrl: options.rpcUrl,
    })

    try {
      console.log(`Purchasing package "${options.id}"...`)
      const { balance, txHash } = await agent.purchasePackage(options.id)
      console.log(`\n✅ Package purchased`)
      console.log(`   Tx Hash:       ${txHash}`)
      console.log(`   New cUSDC:     ${balance.balance_cusdc}`)
      console.log(`   New BLIND:     ${balance.balance_blind}`)
    } catch (err: any) {
      console.error('Error:', err.message || err)
      process.exit(1)
    }
  })

program.parse()
