#!/usr/bin/env node
/**
 * Quorum logging test — submit a single inference job via the Agent SDK
 * and print the job_id so we can grep ICL/node logs for the QUORUM lines.
 */

require('dotenv').config()
const { BlindferenceAgent } = require('./dist/agent')

const PROMPT = process.argv[2] || 'What is the capital of France?'

async function main() {
  const agent = new BlindferenceAgent({
    privateKey: process.env.BLF_PRIVATE_KEY,
    paymentServiceUrl: process.env.BLF_PAYMENT_URL || 'http://127.0.0.1:8001',
    iclUrl: process.env.BLF_ICL_URL || 'http://127.0.0.1:8000',
    rpcUrl: process.env.BLF_RPC_URL || 'https://sepolia-rollup.arbitrum.io/rpc',
  })

  console.log('Agent address:', agent.getAddress())
  console.log('Prompt:', PROMPT)

  // Check balance first
  const balance = await agent.getBalance()
  console.log('Balance:', JSON.stringify(balance, null, 2))

  if (balance.balance_cusdc <= 0 && balance.balance_blind <= 0) {
    console.error('ERROR: No credits available. Purchase a package first.')
    process.exit(1)
  }

  // Run inference
  console.log('\nSubmitting inference request...')
  const result = await agent.infer({
    prompt: PROMPT,
    modelId: 'groq:llama-3.3-70b-versatile',
    currency: 'cUSDC',
    insurance: false,
  })

  console.log('\n--- RESULT ---')
  console.log('Status:', result.status)
  console.log('Job ID:', result.jobId)
  console.log('Task ID:', result.taskId)
  if (result.output) {
    console.log('Output:', result.output)
  }
  if (result.commitmentHash) {
    console.log('Commitment Hash:', result.commitmentHash)
  }

  // Print grep commands for the user to run in another terminal
  console.log('\n--- LOG GREP COMMANDS ---')
  console.log(`ICL quorum log:`)
  console.log(`  tail -f /tmp/icl.log | grep -E "QUORUM|${result.jobId}"`)
  console.log(`Node leader log:`)
  console.log(`  tail -f /tmp/node*.log | grep -E "LEADER|VERIFIER|${result.jobId}"`)
}

main().catch((err) => {
  console.error('Fatal error:', err.message || err)
  process.exit(1)
})
