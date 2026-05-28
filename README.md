# @blindference/agent-sdk

[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![npm](https://img.shields.io/badge/npm-%40blindference%2Fagent--sdk-red.svg)](https://www.npmjs.com/package/@blindference/agent-sdk)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Confidential AI inference SDK for Node.js — submit encrypted prompts to a decentralized quorum of verified nodes.**

Blindference Agent enables developers to build agents that send prompts through end-to-end encryption (AES-256-GCM + Fhenix CoFHE), execute across a leader-verifier quorum for integrity, and receive decrypted results locally. No plaintext leaves your machine.

Runs on **Arbitrum Sepolia** via `https://icl.blindference.xyz`.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Quickstart](#quickstart)
4. [CLI Reference](#cli-reference)
5. [SDK API](#sdk-api)
6. [REST Server](#rest-server)
7. [Python Interop](#python-interop)
8. [Configuration](#configuration)
9. [Architecture](#architecture)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Node.js 18+** — check with `node --version`
- **npm 9+** — check with `npm --version`
- A **MetaMask wallet** with Arbitrum Sepolia testnet
- **Testnet ETH** on Arbitrum Sepolia (for gas)
- **Testnet BLIND tokens** — get from the [Blindference Faucet](https://blindference.xyz/faucet)
- **cUSDC credits** — purchase with BLIND via CLI

### Quick Check

```bash
node --version   # >= 18.0.0
npm --version    # >= 9.0.0
```

---

## Installation

### Global CLI Install

```bash
npm install -g @blindference/agent-sdk
```

### Per-Project Install

```bash
npm install @blindference/agent-sdk
```

### Environment Setup

Create a `.env` file in your project root:

```bash
cat > .env << 'EOF'
# REQUIRED — Your wallet private key (0x-prefixed, fresh wallet only)
BLF_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE

# REQUIRED — Payment Service URL
BLF_PAYMENT_URL=https://payment.blindference.xyz

# Optional — Arbitrum Sepolia RPC (defaults to public endpoint)
# BLF_RPC_URL=https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY

# Optional — ICL URL (defaults to https://icl.blindference.xyz)
# BLF_ICL_URL=https://icl.blindference.xyz
EOF
```

The CLI auto-loads `.env` via [dotenv](https://github.com/motdotla/dotenv). No manual configuration needed.

**Never commit `.env` to git.**

---

## Quickstart

### 1. Check Balance

```bash
blindference-agent balance
```

**Expected Output:**
```
Credit Balances
   Address:   0x...
   cUSDC:     100.00
   BLIND:     50.00
```

If balance is 0, get BLIND from the [faucet](https://blindference.xyz/faucet) and purchase credits:

```bash
blindference-agent buy-package --id starter
```

### 2. Run Inference

```bash
blindference-agent infer \
  --prompt "What is the capital of France?" \
  --model groq:llama-3.3-70b-versatile \
  --currency cUSDC
```

**Expected Timeline:**
- 0-5s: CoFHE client initialization
- 5-35s: ZK proof generation (AES encryption + CoFHE key splitting)
- 35-180s: Quorum consensus polling
- Final: Decrypted output

**Expected Output:**
```
Inference completed
   Job ID:    550e8400-e29b-41d4-a716-446655440000
   Task ID:   0x1234...

   Output:
   The capital of France is Paris.
```

### 3. Start REST Server

```bash
blindference-agent start --port 4000
```

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/infer` | Submit inference |
| `GET` | `/status/:jobId` | Check job status |
| `GET` | `/balance` | Credit balances |
| `GET` | `/health` | Health check |

Test:
```bash
curl -X POST http://localhost:4000/infer \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Hello","modelId":"groq:llama-3.3-70b-versatile"}'
```

---

## CLI Reference

### Commands

#### `infer` — Run Confidential Inference

```bash
blindference-agent infer [options]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--prompt <text>` | ✅ | — | The prompt to encrypt and submit |
| `--model <id>` | — | `groq:llama-3.3-70b-versatile` | Model identifier |
| `--currency <cUSDC\|BLIND>` | — | `cUSDC` | Payment currency |
| `--insurance` | — | `false` | Enable coverage + dispute resolution |
| `--payment-service <url>` | — | `BLF_PAYMENT_URL` env | Payment Service URL |
| `--rpc-url <url>` | — | `BLF_RPC_URL` or public | Arbitrum Sepolia RPC |

**Examples:**

```bash
# Basic
blindference-agent infer --prompt "Explain quantum computing"

# With insurance
blindference-agent infer \
  --prompt "Audit this contract" \
  --model gemini:gemini-2.5-flash \
  --currency cUSDC \
  --insurance
```

#### `balance` — Check Credits

```bash
blindference-agent balance [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--payment-service <url>` | `BLF_PAYMENT_URL` env | Payment Service URL |

#### `buy-package` — Purchase Credits

```bash
blindference-agent buy-package --id <packageId> [options]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--id <packageId>` | ✅ | — | `starter`, `pro`, or `enterprise` |
| `--payment-service <url>` | — | `BLF_PAYMENT_URL` env | Payment Service URL |
| `--rpc-url <url>` | — | `BLF_RPC_URL` or public | Arbitrum Sepolia RPC |

**Example:**
```bash
blindference-agent buy-package --id pro
```

#### `start` — Launch REST Server

```bash
blindference-agent start [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-p, --port <port>` | `4000` | Server port |
| `--payment-service <url>` | `BLF_PAYMENT_URL` env | Payment Service URL |
| `--icl <url>` | `https://icl.blindference.xyz` | ICL endpoint |
| `--rpc-url <url>` | `BLF_RPC_URL` or public | Arbitrum Sepolia RPC |
| `--ipfs-gateway <url>` | `https://gateway.pinata.cloud/ipfs` | IPFS download gateway |

---

## SDK API

### Programmatic Usage

```typescript
import { BlindferenceAgent } from '@blindference/agent-sdk'

const agent = new BlindferenceAgent({
  privateKey: process.env.BLF_PRIVATE_KEY,
  paymentServiceUrl: process.env.BLF_PAYMENT_URL,
  rpcUrl: process.env.BLF_RPC_URL,
})

// Check balance
const balance = await agent.getBalance()
console.log(balance.balance_cusdc)

// Run inference
const result = await agent.infer({
  prompt: 'Explain zero-knowledge proofs',
  modelId: 'groq:llama-3.3-70b-versatile',
  currency: 'cUSDC',
  insurance: false,
})

console.log(result.output)        // Decrypted plaintext
console.log(result.jobId)         // UUID
console.log(result.taskId)        // On-chain bytes32
console.log(result.status)        // 'COMPLETED' | 'FAILED' | 'REJECTED'
```

### Constructor Options

```typescript
interface BlindferenceAgentConfig {
  privateKey: string                    // Required: 0x-prefixed private key
  paymentServiceUrl: string             // Required: Payment Service URL
  rpcUrl: string                        // Required: Arbitrum Sepolia RPC
  iclUrl?: string                       // Optional: defaults to https://icl.blindference.xyz
  ipfsGateway?: string                  // Optional: defaults to Pinata gateway
  chainId?: number                      // Optional: defaults to 421614 (Arbitrum Sepolia)
  promptKeyStoreAddress?: string        // Optional: on-chain key storage contract
  cofheConfig?: object                  // Optional: CoFHE SDK overrides
}
```

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `async infer(options)` | `InferenceResult` | Full pipeline: encrypt → submit → poll → decrypt |
| `async getBalance(address?)` | `CreditBalance` | Query credit balances |
| `async getPackages()` | `CreditPackage[]` | List available credit packages |
| `async deposit(amountWei, currency)` | `string` | Deposit BLIND/cUSDC (tx hash) |
| `async purchasePackage(packageId)` | `{ balance, txHash }` | Purchase credits with BLIND |
| `async getDeveloperStats(address?)` | `DeveloperStats` | SDK usage analytics |
| `getAddress()` | `string` | Wallet address derived from private key |

### Types

```typescript
interface InferOptions {
  prompt: string
  modelId?: string        // default: 'groq:llama-3.3-70b-versatile'
  currency?: 'BLIND' | 'cUSDC'
  insurance?: boolean
}

interface InferenceResult {
  jobId: string
  taskId: string
  status: 'COMPLETED' | 'FAILED' | 'REJECTED'
  output?: string
  outputCid?: string
  commitmentHash?: string
}
```

---

## REST Server

Start a local REST API for language-agnostic integration:

```bash
blindference-agent start --port 4000
```

### Endpoints

#### `POST /infer`

Submit a confidential inference job.

**Request:**
```json
{
  "prompt": "Explain quantum computing",
  "modelId": "groq:llama-3.3-70b-versatile",
  "currency": "cUSDC",
  "insurance": false
}
```

**Response (success):**
```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "taskId": "0x1234...",
  "status": "COMPLETED",
  "output": "Quantum computing uses qubits...",
  "outputCid": "QmS9...",
  "commitmentHash": "0x1d8d..."
}
```

**Response (failure):**
```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "FAILED",
  "error": "Quorum rejected: hash mismatch"
}
```

#### `GET /status/:jobId`

Get current job status from the Payment Service.

#### `GET /balance`

Get credit balances for the agent's wallet.

#### `GET /health`

Health check. Returns `{ status: "ok", agent: "0x..." }`.

---

## Python Interop

Python developers can call the TypeScript SDK via subprocess or HTTP:

### Subprocess (CLI)

```python
import subprocess
import json

result = subprocess.run(
    ["npx", "@blindference/agent-sdk", "infer",
     "--prompt", "Hello from Python",
     "--model", "groq:llama-3.3-70b-versatile"],
    capture_output=True,
    text=True,
    env={"BLF_PRIVATE_KEY": "0x...", "BLF_PAYMENT_URL": "https://payment.blindference.xyz"},
)
print(result.stdout)
```

### HTTP (REST Server)

```python
import requests

# Start server: blindference-agent start --port 4000
resp = requests.post("http://localhost:4000/infer", json={
    "prompt": "Hello from Python",
    "modelId": "groq:llama-3.3-70b-versatile",
})
print(resp.json()["output"])
```

### Async (aiohttp)

```python
import aiohttp
import asyncio

async def infer(prompt: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:4000/infer",
            json={"prompt": prompt, "modelId": "groq:llama-3.3-70b-versatile"},
        ) as resp:
            data = await resp.json()
            return data["output"]

print(asyncio.run(infer("Hello from Python")))
```

See `examples/` for complete Python interop scripts:
- `examples/ts_sdk_subprocess.py` — CLI subprocess wrapper
- `examples/ts_sdk_server.py` — Async HTTP client with server lifecycle

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BLF_PRIVATE_KEY` | ✅ | — | 0x-prefixed wallet private key |
| `BLF_PAYMENT_URL` | ✅ | — | Payment Service URL |
| `BLF_RPC_URL` | — | Public endpoint | Arbitrum Sepolia RPC |
| `BLF_ICL_URL` | — | `https://icl.blindference.xyz` | ICL endpoint |
| `BLF_PINATA_JWT` | — | — | Pinata JWT for IPFS uploads |
| `BLF_IPFS_GATEWAY` | — | `https://gateway.pinata.cloud/ipfs` | IPFS download gateway |
| `BLF_DEFAULT_MODEL` | — | `groq:llama-3.3-70b-versatile` | Default model ID |
| `BLF_VERIFIER_COUNT` | — | `2` | Quorum verifier count |
| `BLF_MIN_TIER` | — | `0` | Minimum node tier |
| `BLF_INSURANCE` | — | `false` | Enable insurance by default |
| `BLF_LOG_LEVEL` | — | `info` | Log level (debug, info, warn, error) |
| `BLF_SERVER_PORT` | — | `4000` | REST server port |

### Private Key Priority

The SDK checks private keys in this order:
1. `BLF_PRIVATE_KEY` (recommended)
2. `BLINDFERENCE_PRIVATE_KEY`
3. `PRIVATE_KEY`

---

## Architecture

```
Your Prompt (plaintext in memory only)
    ↓
AES-256-GCM encryption — key never leaves your machine
    ↓
AES key split into two halves
    ↓
Each half encrypted via Fhenix CoFHE threshold network
    ↓
Encrypted prompt blob uploaded to IPFS
    ↓
CoFHE ciphertext handles stored on-chain (Arbitrum Sepolia)
    ↓
ICL selects quorum: 1 Leader + N Verifiers via icl.blindference.xyz
    ↓
Each node decrypts its key half via CoFHE, reconstructs AES key
    ↓
All nodes run identical inference, hash the output
    ↓
Leader submits result + output key; Verifiers confirm hash match
    ↓
ICL aggregates consensus, commits accepted result on-chain
    ↓
You download encrypted output, decrypt AES key via CoFHE, decrypt result
```

**Layers:**
1. **Encryption** — AES-256-GCM + CoFHE key distribution
2. **Consensus** — 1 leader executes, N verifiers replay and hash-match
3. **Settlement** — Accepted results committed on Arbitrum Sepolia
4. **Decryption** — Threshold decryption reconstitutes AES key

---

## Troubleshooting

### "Private key is required"

Create `.env` in your current directory:
```bash
cat > .env << 'EOF'
BLF_PRIVATE_KEY=0xYOUR_KEY
BLF_PAYMENT_URL=https://payment.blindference.xyz
EOF
```

### "Payment Service URL is required"

Set the Payment Service URL:
```bash
export BLF_PAYMENT_URL=https://payment.blindference.xyz
```

### "Insufficient credits"

1. Get BLIND from [faucet](https://blindference.xyz/faucet)
2. Purchase credits: `blindference-agent buy-package --id starter`

### CoFHE initialization hangs

ZK proof generation takes 10-30 seconds. Do not interrupt.

### "Polling timed out"

Check if quorum nodes are active:
```bash
curl https://icl.blindference.xyz/health
```

### Debug Mode

```bash
BLF_LOG_LEVEL=debug blindference-agent infer --prompt "test"
```

---

## Links

- [NPM Package](https://www.npmjs.com/package/@blindference/agent-sdk)
- [GitHub](https://github.com/AbhishekPanwarr/Blindference-Agent)
- [Blindference Network](https://blindference.xyz)
- [Documentation](https://docs.blindference.xyz)
- [Blindference Node](https://github.com/baync180705/blindference-node) — Run a compute node

## License

MIT — see [LICENSE](LICENSE).
