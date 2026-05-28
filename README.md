# Blindference Agent SDK

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![npm: @blindference/agent-sdk](https://img.shields.io/badge/npm-%40blindference%2Fagent--sdk-red.svg)](https://www.npmjs.com/package/@blindference/agent-sdk)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Confidential AI agent SDK — submit encrypted inference requests to a decentralized quorum of verified nodes.**

Blindference Agent enables developers to build agents that send prompts through end-to-end encryption (AES-256-GCM + Fhenix CoFHE), execute across a leader-verifier quorum for integrity, and receive decrypted results locally. No plaintext leaves the developer's machine.

Available in **Python** and **TypeScript/Node.js**.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step 0: Wallet & Testnet Setup](#step-0-wallet--testnet-setup)
3. [Installation](#installation)
4. [Your First Confidential Inference](#your-first-confidential-inference)
5. [Python SDK API Reference](#python-sdk-api-reference)
6. [TypeScript SDK Quickstart](#typescript-sdk-quickstart)
7. [CLI Reference](#cli-reference)
8. [REST API Reference](#rest-api-reference)
9. [Python ↔ TypeScript Interop](#python--typescript-interop)
10. [Examples](#examples)
11. [LangChain Integration](#langchain-integration)
12. [Supported Models](#supported-models)
13. [Architecture](#architecture)
14. [Cookbook](#cookbook)
15. [Testing](#testing)
16. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.10+** — check with `python --version`
- **Node.js 18+** — check with `node --version`
- **npm 9+** — check with `npm --version`
- **Git**
- A **MetaMask wallet** with Arbitrum Sepolia testnet configured
- **Testnet ETH** on Arbitrum Sepolia (for gas fees)
- **Testnet BLIND tokens** (for payments) — get from the [Blindference Faucet](https://blindference.xyz/faucet)

### Quick Check

```bash
python --version   # >= 3.10
node --version     # >= 18.0.0
npm --version      # >= 9.0.0
```

---

## Step 0: Wallet & Testnet Setup

### 1. Create a Wallet

If you don't have one, install [MetaMask](https://metamask.io/) and create a new wallet. **For development, always use a fresh wallet with no mainnet funds.**

### 2. Add Arbitrum Sepolia to MetaMask

Network details:
- **Network Name**: Arbitrum Sepolia
- **RPC URL**: `https://sepolia-rollup.arbitrum.io/rpc`
- **Chain ID**: `421614`
- **Currency Symbol**: ETH
- **Block Explorer**: `https://sepolia.arbiscan.io`

### 3. Get Testnet ETH

Use a Sepolia faucet:
- [Alchemy Sepolia Faucet](https://sepoliafaucet.com/)
- [QuickNode Sepolia Faucet](https://faucet.quicknode.com/ethereum/sepolia)
- [Google Cloud Sepolia Faucet](https://cloud.google.com/application/web3/faucet/ethereum/sepolia)

You'll need ~0.001 ETH for a few transactions.

### 4. Get BLIND Tokens

Visit the [Blindference Faucet](https://blindference.xyz/faucet) or use the CLI:

```bash
npx @blindference/agent-sdk balance
# If balance is 0, request from the web faucet first
```

### 5. Get an Alchemy API Key

Sign up at [Alchemy](https://www.alchemy.com/), create an app on **Arbitrum Sepolia**, and copy the HTTP API key.

### 6. Export Your Private Key

In MetaMask: Account → Account Details → Show Private Key. **Never commit this to git.**

---

## Installation

### Python SDK

```bash
git clone https://github.com/baync180705/blindference-agent.git
cd blindference-agent
pip install -e ".[dev,langchain]"
npm install   # Required for the CoFHE bridge
```

### TypeScript SDK

```bash
npm install @blindference/agent-sdk
```

### Environment Setup

```bash
cp .env.example .env
# Edit .env with your keys:
#   BLF_COFHE_RPC=https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY
#   BLF_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE
#   BLF_ICL_URL=https://icl.blindference.xyz
```

The SDK auto-loads `.env` and `.env.local` via `python-dotenv` when imported — no manual `load_dotenv()` call needed.

### Setup Validation

After installation, validate your setup:

```bash
# Python SDK
blindference-agent test

# TypeScript SDK
npx @blindference/agent-sdk balance

# Or manually test ICL connectivity
curl http://localhost:8000/health
```

Expected output:
```
Testing ICL connectivity ...
  ✓ ICL reachable
Testing CoFHE bridge ...
  ✓ CoFHE bridge started
  ✓ CoFHE encrypt test: ctHash=0x28c0b27e...
```

---

## Your First Confidential Inference

### Python: Simple One-Shot

```bash
cd examples
python simple_agent.py
```

Expected output:
```
======================================================================
Blindference Agent — Confidential Inference Demo
======================================================================

[1/9] Initializing agent...
        ICL URL: https://icl.blindference.xyz
        CoFHE RPC: https://arb-sepolia.g.alchemy.com/v2/...
        Private key: SET

[2/9] Encrypting prompt with AES-256-GCM...
[3/9] CoFHE-encrypting key halves...
[4/9] Uploading encrypted prompt to IPFS...
        Prompt CID: QmS9...
[5/9] Storing key on-chain (task_id=0x...)...
        StoreKey tx: 0x1a2b...
[6/9] Fetching quorum preview...
        Leader: 0x61e7...
        Verifiers: 0x1234..., 0x5678...
[7/9] Submitting to ICL...
[8/9] Waiting for quorum consensus...
        Status: RUNNING... (poll 1/60)
        Status: ACCEPTED (poll 12/60)
[9/9] Decrypting result...

Result: The quick brown fox jumps over the lazy dog.
Leader: 0x61e7...
Verifiers: 0x1234..., 0x5678...
Commitment: 0x1d8d...
```

### TypeScript: Simple One-Shot

```bash
export BLINDFERENCE_PRIVATE_KEY=0xYOUR_KEY
npx @blindference/agent-sdk infer \
  --prompt "What is the capital of France?" \
  --model groq:llama-3.3-70b-versatile
```

Expected output:
```
Initializing CoFHE client...
Submitting inference...

✅ Inference completed
   Job ID:    550e8400-e29b-41d4-a716-446655440000
   Task ID:   0x1234...

   Output:
   The capital of France is Paris.
```

### Local REST Server

Start the server:

```bash
npx @blindference/agent-sdk start --port 4000
```

Submit a request:

```bash
curl -X POST http://localhost:4000/infer \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Explain quantum computing","modelId":"groq:llama-3.3-70b-versatile"}'
```

---

## Python SDK API Reference

### Core Classes

#### `BlindferenceAgent`

The main entry point for confidential inference.

```python
class BlindferenceAgent:
    def __init__(
        self,
        icl_url: str,                    # ICL endpoint URL
        cofhe_rpc: str = "",             # Arbitrum Sepolia RPC URL
        private_key: str = "",            # 0x-prefixed private key
        chain_id: int = 421614,           # Arbitrum Sepolia
        cofhe_bridge_path: str | None = None,  # Path to cofhe_bridge.mjs
        mock: bool = False,                # Skip encryption (testing only)
    )
```

**Key Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `async inference(prompt, model_id, verifier_count=2, min_tier=0, poll_interval=3.0, timeout=300.0)` | Full pipeline: encrypt → submit → poll → decrypt | `InferenceResult` |
| `async submit(prompt, model_id, verifier_count=2, min_tier=0)` | Encrypt and submit without polling | `InferenceRequest` |
| `async stream_status(request_id, interval=3.0)` | Yield live status updates until terminal state | `AsyncIterator[InferenceStatus]` |
| `async close()` | Clean up CoFHE bridge and ICL session | `None` |

**Example — Streaming Status:**

```python
async for status in agent.stream_status(request.request_id, interval=2.0):
    print(f"Status: {status.status}")
    if status.status in ("ACCEPTED", "REJECTED", "DISPUTED"):
        break
```

**Example — Async Context Manager:**

```python
async with BlindferenceAgent(...) as agent:
    result = await agent.inference("Hello", "groq:llama-3.3-70b-versatile")
    print(result.text)
```

#### `InferenceResult`

```python
@dataclass
class InferenceResult:
    request_id: str          # UUID from ICL
    task_id: str             # On-chain bytes32 identifier
    text: str                # Decrypted plaintext output
    model_id: str            # Model used for inference
    output_cid: str          # IPFS CID of encrypted output
    leader_address: str      # Leader node address
    verifier_addresses: list[str]  # Verifier node addresses
    commitment_hash: str     # On-chain result commitment
    result_commit_tx: str | None  # Transaction hash
    timestamps: dict | None  # Execution timing metadata
```

### What Happens Under the Hood

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
ICL selects quorum: 1 Leader + N Verifiers
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

---

## Development Mode

For local testing and CI pipelines without managing keys or the CoFHE bridge, enable mock mode:

```python
agent = BlindferenceAgent(
    icl_url="https://icl.blindference.xyz",
    mock=True,  # Skips encryption — plaintext flow for testing
)
```

Mock mode bypasses all cryptography and submits prompts as plaintext. **Never use for sensitive data.**

---

## TypeScript SDK Quickstart

### Install

```bash
npm install @blindference/agent-sdk
```

### Configuration

```typescript
import { BlindferenceAgent } from '@blindference/agent-sdk'

const agent = new BlindferenceAgent({
  privateKey: process.env.BLINDFERENCE_PRIVATE_KEY,     // Required
  paymentServiceUrl: 'http://localhost:8001',          // Required
  rpcUrl: 'https://sepolia-rollup.arbitrum.io/rpc',    // Required
  chainId: 421614,                                     // Default
  promptKeyStoreAddress: '0x1E22dD12f448B15f1Ca8560fB6B4463834FaAf73', // Default
  cofheConfig: {                                       // Optional
    fheKeyStorage: null,
    useWorkers: false,
  },
})
```

### Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `async initCofhe()` | Initialize CoFHE client (auto-called by `infer`) | `void` |
| `async infer(options)` | Full pipeline: encrypt → submit → poll → decrypt | `InferenceResult` |
| `async getBalance(address?)` | Query credit balances from Payment Service | `CreditBalance` |
| `async getPackages()` | List available credit packages | `CreditPackage[]` |
| `async deposit(amountWei, currency)` | Deposit BLIND or cUSDC to Payment Service | `string` (tx hash) |
| `async purchasePackage(packageId)` | Purchase a credit package with BLIND | `{ balance, txHash }` |
| `async getDeveloperStats(address?)` | Fetch SDK usage statistics | `DeveloperStats` |

### Infer Options

```typescript
interface InferOptions {
  prompt: string                           // Required: the prompt text
  modelId?: string                        // Default: 'groq:llama-3.3-70b-versatile'
  currency?: 'BLIND' | 'cUSDC'           // Default: 'cUSDC'
  insurance?: boolean                     // Default: false
}
```

### Example — Basic Inference

```typescript
const result = await agent.infer({
  prompt: 'Explain quantum computing in simple terms',
  modelId: 'groq:llama-3.3-70b-versatile',
})

console.log(result.output)           // Decrypted plaintext
console.log(result.jobId)             // UUID job identifier
console.log(result.taskId)            // On-chain task identifier
console.log(result.status)            // 'COMPLETED' | 'FAILED' | 'REJECTED'
```

### Example — With Insurance

```typescript
const result = await agent.infer({
  prompt: 'Analyze this smart contract for vulnerabilities...',
  modelId: 'gemini:gemini-2.5-flash',
  currency: 'cUSDC',
  insurance: true,  // Enables coverage and dispute resolution
})
```

---

## CLI Reference

The CLI is available as `blindference-agent` when installed globally, or via `npx`:

```bash
npx @blindference/agent-sdk <command> [options]
```

### Global Install

```bash
npm install -g @blindference/agent-sdk
blindference-agent --help
```

### Commands

#### `start` — Start Local REST Server

```bash
blindference-agent start [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-p, --port <port>` | `4000` | Server port |
| `--payment-service <url>` | `http://localhost:8001` | Payment Service URL |
| `--icl <url>` | Auto-derived | ICL URL (defaults to payment service port -1) |
| `--ipfs-gateway <url>` | `https://gateway.pinata.cloud/ipfs` | IPFS download gateway |
| `--rpc-url <url>` | `https://sepolia-rollup.arbitrum.io/rpc` | Arbitrum Sepolia RPC |
| `--pinata-jwt <jwt>` | — | Pinata JWT for direct IPFS uploads |
| `--prompt-key-store <address>` | Default | PromptKeyStore contract address |

**Example:**
```bash
blindference-agent start --port 4000 --payment-service http://localhost:8001
```

**Endpoints:**

| Method | Path | Body / Params | Response |
|--------|------|---------------|----------|
| `POST` | `/infer` | `{ prompt, modelId?, currency?, insurance? }` | `{ jobId, taskId, status, output, outputCid, commitmentHash }` |
| `GET` | `/status/:jobId` | — | Full job status from Payment Service |
| `GET` | `/balance` | — | `{ user_address, balance_cusdc, balance_blind, ... }` |
| `GET` | `/health` | — | `{ status: "ok", agent: "0x..." }` |

#### `infer` — Run Single Inference

```bash
blindference-agent infer [options]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--prompt <text>` | ✅ | — | The prompt text |
| `--model <modelId>` | — | `groq:llama-3.3-70b-versatile` | Model identifier |
| `--currency <currency>` | — | `cUSDC` | Payment currency (`BLIND` or `cUSDC`) |
| `--insurance` | — | `false` | Enable insurance coverage |
| `--payment-service <url>` | — | `http://localhost:8001` | Payment Service URL |
| `--rpc-url <url>` | — | `https://sepolia-rollup.arbitrum.io/rpc` | RPC endpoint |

**Example:**
```bash
blindference-agent infer \
  --prompt "What is the capital of France?" \
  --model groq:llama-3.3-70b-versatile \
  --currency cUSDC
```

#### `balance` — Check Credit Balances

```bash
blindference-agent balance [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--payment-service <url>` | `http://localhost:8001` | Payment Service URL |

**Output:**
```
💰 Credit Balances
   Address:   0x...
   cUSDC:     100.00
   BLIND:     50.00
   Total Deposited cUSDC: 200.00
   Total Deposited BLIND: 100.00
   Total Spent cUSDC:     100.00
   Total Spent BLIND:     50.00
```

#### `buy-package` — Purchase Credit Package

```bash
blindference-agent buy-package [options]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--id <packageId>` | ✅ | — | Package ID (`starter`, `pro`, `enterprise`) |
| `--payment-service <url>` | — | `http://localhost:8001` | Payment Service URL |
| `--rpc-url <url>` | — | `https://sepolia-rollup.arbitrum.io/rpc` | RPC endpoint |

**Example:**
```bash
blindference-agent buy-package --id pro
```

### Environment Variables

All commands read from environment variables (set in `.env` or exported):

| Variable | Required | Description |
|----------|----------|-------------|
| `BLINDFERENCE_PRIVATE_KEY` | ✅ (or `PRIVATE_KEY`) | 0x-prefixed wallet private key |
| `BLF_ICL_URL` | — | ICL endpoint (default: `https://icl.blindference.xyz`) |
| `BLF_COFHE_RPC` | — | Arbitrum Sepolia RPC URL |

---

## REST API Reference

When running `blindference-agent start`, the following REST API is available:

### `POST /infer` — Submit Inference

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
  "taskId": "0x1234...",
  "status": "FAILED",
  "output": null,
  "error": "Quorum rejected: hash mismatch"
}
```

### `GET /status/:jobId` — Job Status

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "user_address": "0x...",
  "model_id": "groq:llama-3.3-70b-versatile",
  "amount_cusdc": "10.00",
  "leader_address": "0x61e7...",
  "verifier_addresses": ["0x1234...", "0x5678..."],
  "result_hash": "0x1d8d...",
  "output_cid": "QmS9...",
  "encrypted_output_key_high": "65074...",
  "encrypted_output_key_low": "44873...",
  "created_at": "2026-05-28T12:00:00Z",
  "updated_at": "2026-05-28T12:00:30Z"
}
```

### `GET /balance` — Credit Balances

**Response:**
```json
{
  "user_address": "0x...",
  "balance_cusdc": "100.00",
  "balance_blind": "50.00",
  "total_deposited_cusdc": "200.00",
  "total_deposited_blind": "100.00",
  "total_spent_cusdc": "100.00",
  "total_spent_blind": "50.00"
}
```

### `GET /health` — Health Check

**Response:**
```json
{
  "status": "ok",
  "agent": "0x..."
}
```

---

## Python ↔ TypeScript Interop

Python agents can delegate CoFHE operations to the TypeScript SDK when native Python CoFHE bindings are unavailable or when running in mixed-language environments.

| Pattern | Approach | Example |
|---------|----------|---------|
| Subprocess CLI | `subprocess.run(["npx", "@blindference/agent-sdk", "infer", ...])` | [`ts_sdk_subprocess.py`](examples/ts_sdk_subprocess.py) |
| REST Server | Start TS server, call via `aiohttp`/`requests` | [`ts_sdk_server.py`](examples/ts_sdk_server.py) |

### Python Calling TS CLI

```python
import subprocess

result = subprocess.run(
    ["npx", "-y", "@blindference/agent-sdk", "infer",
     "--prompt", "Hello world",
     "--model", "groq:llama-3.3-70b-versatile"],
    capture_output=True,
    text=True,
    env={"BLINDFERENCE_PRIVATE_KEY": "0x..."},
)
print(result.stdout)
```

### Python Calling TS REST Server

```python
import aiohttp
import asyncio

async def infer_via_ts_server(prompt: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:4000/infer",
            json={"prompt": prompt, "modelId": "groq:llama-3.3-70b-versatile"},
        ) as resp:
            return await resp.json()

result = asyncio.run(infer_via_ts_server("Hello"))
print(result["output"])
```

---

## Examples

| Example | Language | Description |
|---------|----------|-------------|
| [`getting_started.ipynb`](examples/getting_started.ipynb) | Python | Interactive Jupyter notebook: setup validation, inference, streaming, batch, chat |
| [`simple_agent.py`](examples/simple_agent.py) | Python | One-shot inference with result metadata |
| [`streaming_agent.py`](examples/streaming_agent.py) | Python | Live execution trace with quorum step tracking |
| [`batch_inference.py`](examples/batch_inference.py) | Python | Concurrent multi-prompt submission |
| [`interactive_chat.py`](examples/interactive_chat.py) | Python | REPL chat loop with conversation history |
| [`risk_scoring_agent.py`](examples/risk_scoring_agent.py) | Python | Confidential numeric feature inference (loan risk) |
| [`langchain_rag.py`](examples/langchain_rag.py) | Python | LangChain Retrieval-Augmented Generation integration |
| [`ts_sdk_subprocess.py`](examples/ts_sdk_subprocess.py) | Python | Call TypeScript SDK CLI from Python via subprocess |
| [`ts_sdk_server.py`](examples/ts_sdk_server.py) | Python | Control TS SDK REST server from Python via HTTP |
| [`multi_turn_chat_agent.py`](examples/multi_turn_chat_agent.py) | Python | Stateful multi-turn chat agent with rolling memory |
| [`autonomous_research_agent.py`](examples/autonomous_research_agent.py) | Python | Decompose queries, parallel infer, synthesize reports |
| [`tool_using_agent.py`](examples/tool_using_agent.py) | Python | Local tool execution + encrypted LLM reasoning |

---

## Cookbook

### Recipe 1: Build a Slack Bot

```python
from slack_bolt.async_app import AsyncApp
from blindference_agent import BlindferenceAgent

app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])
agent = BlindferenceAgent(...)

@app.message(".*")
async def handle_message(message, say):
    result = await agent.inference(
        prompt=message["text"],
        model_id="groq:llama-3.3-70b-versatile",
    )
    await say(f"{result.text}\n\n_Verified by quorum: {result.leader_address[:10]}..._")
```

### Recipe 2: OpenAI-Compatible API Wrapper

```python
from fastapi import FastAPI
from blindference_agent import BlindferenceAgent

api = FastAPI()
agent = BlindferenceAgent(...)

@api.post("/v1/chat/completions")
async def chat_completions(request: dict):
    result = await agent.inference(
        prompt=request["messages"][-1]["content"],
        model_id=request.get("model", "groq:llama-3.3-70b-versatile"),
    )
    return {
        "choices": [{"message": {"role": "assistant", "content": result.text}}],
        "model": request.get("model"),
    }
```

### Recipe 3: Batch Processing CSV

```python
import asyncio
import csv
from blindference_agent import BlindferenceAgent

async def process_csv(input_path: str, output_path: str):
    agent = BlindferenceAgent(...)
    
    with open(input_path) as f, open(output_path, "w") as out:
        reader = csv.DictReader(f)
        writer = csv.DictWriter(out, fieldnames=["input", "output", "leader", "commitment"])
        writer.writeheader()
        
        tasks = []
        for row in reader:
            task = agent.inference(row["prompt"], "groq:llama-3.3-70b-versatile")
            tasks.append((row, task))
        
        results = await asyncio.gather(*[t[1] for t in tasks])
        for (row, _), result in zip(tasks, results):
            writer.writerow({
                "input": row["prompt"],
                "output": result.text,
                "leader": result.leader_address,
                "commitment": result.commitment_hash,
            })

asyncio.run(process_csv("input.csv", "output.csv"))
```

### Recipe 4: Scheduled Health Check Agent

```python
import asyncio
from datetime import datetime
from blindference_agent import BlindferenceAgent

async def health_monitor():
    agent = BlindferenceAgent(...)
    while True:
        result = await agent.inference(
            prompt=f"Analyze system health at {datetime.now()}",
            model_id="groq:llama-3.3-70b-versatile",
        )
        if "critical" in result.text.lower():
            await send_alert(result.text)
        await asyncio.sleep(3600)  # Check every hour

asyncio.run(health_monitor())
```

### Recipe 5: Multi-Model Ensemble

```python
import asyncio
from blindference_agent import BlindferenceAgent

async def ensemble_inference(prompt: str):
    agent = BlindferenceAgent(...)
    models = [
        "groq:llama-3.3-70b-versatile",
        "gemini:gemini-2.5-flash",
    ]
    
    tasks = [agent.inference(prompt, model) for model in models]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_results = [r for r in results if not isinstance(r, Exception)]
    # Aggregate or vote on results
    return max(set(r.text for r in valid_results), key=lambda x: sum(1 for r in valid_results if r.text == x))

asyncio.run(ensemble_inference("What is 2+2?"))
```

---

## LangChain Integration

```python
from langchain.chains import RetrievalQA
from blindference_agent.integrations.langchain import BlindferenceLLM

llm = BlindferenceLLM(
    icl_url="https://icl.blindference.xyz",
    cofhe_rpc="...",
    private_key="0x...",
    model="groq:llama-3.3-70b-versatile",
)

qa = RetrievalQA.from_chain_type(llm=llm, retriever=...)
result = qa.invoke("What is FHE?")
```

LangChain is an optional integration — the core `BlindferenceAgent` API requires no framework.

---

## Supported Models

| Model ID | Provider | Tier |
|----------|----------|------|
| `groq:llama-3.3-70b-versatile` | Groq | 0 |
| `gemini:gemini-2.5-flash` | Google | 0 |
| `facebook/opt-125m` | Local vLLM | 0 |

All models run through the same quorum consensus pipeline.

---

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Agent (Python)   │────▶│  AES-256-GCM  │────▶│  CoFHE Bridge   │
│  Your machine     │     │  Encryption   │     │  (subprocess)   │
└─────────────────┘     └──────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌──────────────┐
                                               │  On-Chain    │
                                               │  Key Storage │
                                               │  (Arbitrum)  │
                                               └──────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Decrypted      │◀────│  ICL         │◀────│  Quorum Nodes   │
│  Result         │     │  Coordinator │     │  Leader + N Verifiers│
└─────────────────┘     └──────────────┘     └─────────────────┘
```

1. **Encryption Layer** — AES-256-GCM for data at rest, CoFHE for key distribution
2. **Consensus Layer** — 1 leader executes, N verifiers replay and hash-match
3. **Settlement Layer** — Accepted results committed on Arbitrum Sepolia
4. **Decryption Layer** — Agent reconstitutes AES key via CoFHE threshold decryption

---

## Testing

```bash
python -m pytest tests/ -q
```

22 tests covering AES-GCM roundtrip, key split/merge, type validation, and CLI scaffolding.

---

## Troubleshooting

### Common Errors

#### `CoFHE bridge script not found`

**Cause:** The Python SDK cannot find `cofhe_bridge.mjs`.

**Fix:**
```bash
npm install   # In the repository root
# Or if using the npm package:
npm install @cofhe/sdk viem
```

#### `node: command not found`

**Cause:** Node.js is not installed or not on PATH.

**Fix:**
```bash
# macOS
brew install node

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify
node --version  # >= 18.0.0
```

#### `Private key or RPC not set`

**Cause:** Environment variables are missing.

**Fix:**
```bash
cp .env.example .env
# Edit .env:
#   BLF_COFHE_RPC=https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY
#   BLF_PRIVATE_KEY=0xYOUR_KEY
```

For quick testing without real keys:
```python
agent = BlindferenceAgent(icl_url="...", mock=True)
```

#### `Insufficient credits: need X cUSDC / Y BLIND`

**Cause:** Your Payment Service account has insufficient balance.

**Fix:**
1. Get BLIND tokens from the [faucet](https://blindference.xyz/faucet)
2. Deposit: `blindference-agent deposit --amount 1000000000000000000 --currency BLIND`
3. Or purchase a package: `blindference-agent buy-package --id starter`

#### `max fee per gas less than block base fee`

**Cause:** Arbitrum Sepolia base fee spiked above the default gas price.

**Fix:** The SDK now automatically adds a 50% buffer to gas estimates. If still failing:
```bash
# Increase gas price manually in .env
BLF_GAS_PRICE_MULTIPLIER=2.0
```

#### `IPFS upload failed: 404`

**Cause:** Pinata API endpoint changed or JWT revoked.

**Fix:**
1. Get a new Pinata JWT from [pinata.cloud](https://pinata.cloud)
2. Update `.env`: `BLF_PINATA_JWT=your_new_jwt`
3. Or use the ICL upload endpoint instead of direct Pinata

#### `sealOutput request failed: HTTP 403`

**Cause:** CoFHE ACL access not granted for the ciphertext handle.

**Fix:** Ensure the `storeKey()` transaction completed successfully before submitting to ICL. The vault contract (`BlindferenceInputVault`) must validate the ciphertext on-chain to grant ACL access.

#### `ICL forward failed after 3 attempts`

**Cause:** ICL is unreachable or returning errors.

**Fix:**
```bash
# Test ICL connectivity
curl http://localhost:8000/health
# Or:
blindference-agent test
```

If ICL is down:
1. Restart ICL: `uvicorn main:app --host 127.0.0.1 --port 8000`
2. Verify ICL wallet has gas: check Arbitrum Sepolia balance

#### `Polling timed out after 60 attempts`

**Cause:** Job is taking longer than 3 minutes, or quorum is stuck.

**Fix:**
1. Check job status manually: `curl http://localhost:8001/v1/jobs/{jobId}`
2. Check node health: ensure 3+ nodes are registered and attested
3. Increase timeout: `agent.inference(..., timeout=600.0)`

#### `Module not found: '@cofhe/sdk/node'`

**Cause:** TypeScript SDK dependencies not installed.

**Fix:**
```bash
cd js
npm install
npm run build
```

#### `TypeError: storage.setItem is not a function`

**Cause:** Browser polyfill conflicts with Node.js environment.

**Fix:** The SDK includes a localStorage polyfill that auto-detects broken implementations. If still failing:
```bash
export COFHE_LOCAL_STORAGE_PATH=/tmp/cofhe-storage.json
```

### Debug Mode

Enable verbose logging:

**Python:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**CLI:**
```bash
BLINDFERENCE_LOG_LEVEL=debug blindference-agent infer --prompt "test"
```

### Getting Help

- [GitHub Issues](https://github.com/baync180705/blindference-agent/issues)
- [Blindference Discord](https://discord.gg/blindference)
- [Documentation](https://docs.blindference.xyz)

---

## Next Steps

Now that you've run your first confidential inference:

1. **Explore Examples** — Check out [`examples/`](examples/) for batch processing, chat agents, LangChain integration, and more
2. **Build Your Agent** — Use the [Cookbook](#cookbook) recipes for Slack bots, API wrappers, and scheduled tasks
3. **Run a Node** — Contribute compute to the network: [Blindference Node](https://github.com/baync180705/blindference-node)
4. **Read the Docs** — Deep dive into protocol architecture: [docs.blindference.xyz](https://docs.blindference.xyz)
5. **Join the Community** — Get help and share your projects on [Discord](https://discord.gg/blindference)

---

## License

MIT — see [LICENSE](LICENSE).

## Links

- [Blindference Node](https://github.com/baync180705/blindference-node) — Run a compute node in the quorum
- [Blindference Docs](https://docs.blindference.xyz) — Full protocol documentation
- [Blindference Network](https://blindference.xyz) — Protocol overview
- [npm Package](https://www.npmjs.com/package/@blindference/agent-sdk) — @blindference/agent-sdk
