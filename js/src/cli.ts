#!/usr/bin/env node

import { config as dotenvConfig } from 'dotenv'
import { Command } from 'commander'
import { BlindferenceAgent } from './agent'
import { startServer } from './server'

// Auto-load .env file if present
dotenvConfig()

function getPrivateKey(): string | undefined {
  return process.env.BLF_PRIVATE_KEY || process.env.BLINDFERENCE_PRIVATE_KEY || process.env.PRIVATE_KEY
}

function getPaymentUrl(options: any): string {
  return options.paymentService || process.env.BLF_PAYMENT_URL
}

function requirePaymentUrl(options: any): string {
  const url = getPaymentUrl(options)
  if (!url) {
    console.error('Error: Payment Service URL is required.')
    console.error('  Set --payment-service <url> or BLF_PAYMENT_URL environment variable.')
    console.error('  Example: https://payment.blindference.xyz')
    process.exit(1)
  }
  return url
}

function requirePrivateKey(): string {
  const key = getPrivateKey()
  if (!key) {
    console.error('Error: Private key is required.')
    console.error('  Set BLF_PRIVATE_KEY environment variable (or BLINDFERENCE_PRIVATE_KEY / PRIVATE_KEY).')
    process.exit(1)
  }
  return key
}

const program = new Command()

program
  .name('blindference-agent')
  .description('Blindference Agent SDK CLI — Confidential AI inference on Arbitrum Sepolia')
  .version('0.1.0')

program
  .command('start')
  .description('Start the local pipeline server')
  .option('-p, --port <port>', 'Server port', '4000')
  .option('--payment-service <url>', 'Payment Service URL (or set BLF_PAYMENT_URL)')
  .option('--icl <url>', 'ICL URL (defaults to https://icl.blindference.xyz)')
  .option('--ipfs-gateway <url>', 'IPFS download gateway', 'https://gateway.pinata.cloud/ipfs')
  .option('--rpc-url <url>', 'Arbitrum Sepolia RPC URL (or set BLF_RPC_URL)', 'https://sepolia-rollup.arbitrum.io/rpc')
  .option('--pinata-jwt <jwt>', 'Pinata JWT for direct IPFS uploads')
  .option('--prompt-key-store <address>', 'PromptKeyStore contract address')
  .action(async (options) => {
    const privateKey = requirePrivateKey()
    const paymentUrl = requirePaymentUrl(options)
    const rpcUrl = options.rpcUrl || process.env.BLF_RPC_URL || 'https://sepolia-rollup.arbitrum.io/rpc'

    const port = parseInt(options.port, 10)
    const iclUrl = options.icl || 'https://icl.blindference.xyz'

    console.log(`Starting Blindference Agent Server on port ${port}...`)
    console.log(`  Payment Service: ${paymentUrl}`)
    console.log(`  ICL: ${iclUrl}`)
    console.log(`  RPC: ${rpcUrl}`)
    console.log(`  Chain: Arbitrum Sepolia (421614)`)

    await startServer({
      port,
      paymentServiceUrl: paymentUrl,
      iclUrl,
      ipfsGateway: options.ipfsGateway,
      rpcUrl,
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
  .option('--payment-service <url>', 'Payment Service URL (or set BLF_PAYMENT_URL)')
  .option('--icl <url>', 'ICL URL', 'https://icl.blindference.xyz')
  .option('--ipfs-gateway <url>', 'IPFS download gateway', 'https://gateway.pinata.cloud/ipfs')
  .option('--rpc-url <url>', 'Arbitrum Sepolia RPC URL (or set BLF_RPC_URL)', 'https://sepolia-rollup.arbitrum.io/rpc')
  .option('--prompt-key-store <address>', 'PromptKeyStore contract address')
  .action(async (options) => {
    const privateKey = requirePrivateKey()
    const paymentUrl = requirePaymentUrl(options)
    const rpcUrl = options.rpcUrl || process.env.BLF_RPC_URL || 'https://sepolia-rollup.arbitrum.io/rpc'

    const agent = new BlindferenceAgent({
      privateKey,
      paymentServiceUrl: paymentUrl,
      iclUrl: options.icl,
      ipfsGateway: options.ipfsGateway,
      rpcUrl,
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
        console.log('\nInference completed')
        console.log(`   Job ID:    ${result.jobId}`)
        console.log(`   Task ID:   ${result.taskId}`)
        if (result.output) {
          console.log(`\n   Output:\n   ${result.output}`)
        }
      } else {
        console.log(`\nInference ${result.status}`)
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
  .option('--payment-service <url>', 'Payment Service URL (or set BLF_PAYMENT_URL)')
  .action(async (options) => {
    const privateKey = requirePrivateKey()
    const paymentUrl = requirePaymentUrl(options)
    const rpcUrl = process.env.BLF_RPC_URL || 'https://sepolia-rollup.arbitrum.io/rpc'

    const agent = new BlindferenceAgent({
      privateKey,
      paymentServiceUrl: paymentUrl,
      rpcUrl,
    })

    try {
      const balance = await agent.getBalance()
      console.log('\nCredit Balances')
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
  .option('--payment-service <url>', 'Payment Service URL (or set BLF_PAYMENT_URL)')
  .option('--rpc-url <url>', 'Arbitrum Sepolia RPC URL (or set BLF_RPC_URL)', 'https://sepolia-rollup.arbitrum.io/rpc')
  .action(async (options) => {
    const privateKey = requirePrivateKey()
    const paymentUrl = requirePaymentUrl(options)
    const rpcUrl = options.rpcUrl || process.env.BLF_RPC_URL || 'https://sepolia-rollup.arbitrum.io/rpc'

    const agent = new BlindferenceAgent({
      privateKey,
      paymentServiceUrl: paymentUrl,
      rpcUrl,
    })

    try {
      console.log(`Purchasing package "${options.id}"...`)
      const { balance, txHash } = await agent.purchasePackage(options.id)
      console.log(`\nPackage purchased`)
      console.log(`   Tx Hash:       ${txHash}`)
      console.log(`   New cUSDC:     ${balance.balance_cusdc}`)
      console.log(`   New BLIND:     ${balance.balance_blind}`)
    } catch (err: any) {
      console.error('Error:', err.message || err)
      process.exit(1)
    }
  })

program.parse()
