# Blindference Agent SDK

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Confidential AI agent SDK — submit encrypted inference requests to a decentralized quorum of verified nodes.**

Blindference Agent enables Python developers to build agents that send prompts through end-to-end encryption (AES-256-GCM + Fhenix CoFHE), execute across a leader-verifier quorum for integrity, and receive decrypted results locally. No plaintext leaves the developer's machine.

---

## Quickstart

### Clone and Install

```bash
git clone https://github.com/baync180705/blindference-agent.git
cd blindference-agent
pip install -e ".[dev,langchain]"
npm install
```

Create a `.env` file from the provided example:

```bash
cp .env.example .env
# Edit .env with your keys
```

Required environment variables:

| Variable | Purpose | Get From |
|----------|---------|----------|
| `BLF_COFHE_RPC` | Arbitrum Sepolia RPC endpoint | [Alchemy](https://www.alchemy.com/) |
| `BLF_PRIVATE_KEY` | Agent wallet private key | Generate fresh or use existing |
| `BLF_ICL_URL` | Inference Coordination Layer | `https://icl.blindference.xyz` |

The SDK auto-loads `.env` and `.env.local` via `python-dotenv` when imported — no manual `load_dotenv()` call needed.

### Run the Notebook

```bash
jupyter lab examples/getting_started.ipynb
```

The notebook walks through encrypted inference, streaming quorum progress, batch submission, and interactive chat.

---

## Core API

### Submit a Confidential Inference Request

```python
import asyncio
import os
from blindference_agent import BlindferenceAgent

async def main():
    agent = BlindferenceAgent(
        icl_url=os.environ.get("BLF_ICL_URL"),
        cofhe_rpc=os.environ.get("BLF_COFHE_RPC"),
        private_key=os.environ.get("BLF_PRIVATE_KEY"),
    )

    result = await agent.inference(
        prompt="Analyze the risks of this smart contract: ...",
        model_id="groq:llama-3.3-70b-versatile",
        verifier_count=2,
    )

    print(result.text)
    print(f"Leader: {result.leader_address}")
    print(f"Verifiers: {result.verifier_addresses}")
    print(f"Commitment: {result.commitment_hash}")

asyncio.run(main())
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

## TypeScript / Node.js SDK

A first-class TypeScript SDK is available for Node.js agents, serverless functions, and browser-adjacent runtimes.

### Install

```bash
npm install @blindference/agent-sdk
```

### Quickstart

```typescript
import { BlindferenceAgent } from '@blindference/agent-sdk'

const agent = new BlindferenceAgent({
  privateKey: process.env.BLINDFERENCE_PRIVATE_KEY,
  paymentServiceUrl: 'http://localhost:8001',
  rpcUrl: 'https://sepolia-rollup.arbitrum.io/rpc',
})

const result = await agent.infer({
  prompt: 'Explain zero-knowledge proofs in three sentences',
  modelId: 'groq:llama-3.3-70b-versatile',
})

console.log(result.output)
```

### CLI

```bash
# One-shot inference
npx @blindference/agent-sdk infer --prompt "What is 2+2?"

# Credit balances
npx @blindference/agent-sdk balance

# Purchase a package
npx @blindference/agent-sdk buy-package --id pro

# Start local REST server
npx @blindference/agent-sdk start --port 4000
```

### Local REST Server

```bash
npx @blindference/agent-sdk start --port 4000
```

Endpoints:
- `POST /infer` — submit inference (`{ prompt, modelId?, currency?, insurance? }`)
- `GET /status/:jobId` — job status
- `GET /balance` — credit balances
- `GET /health` — health check

The TypeScript SDK uses `@cofhe/sdk/node` directly (no subprocess bridge) and bundles the CoFHE bridge script so Python SDK users can resolve it from the npm package.

---

## Python ↔ TypeScript Interop

Python agents can delegate CoFHE operations to the TypeScript SDK when native Python CoFHE bindings are unavailable or when running in mixed-language environments.

| Pattern | Approach | Example |
|---------|----------|---------|
| Subprocess CLI | `subprocess.run(["npx", "@blindference/agent-sdk", "infer", ...])` | [`ts_sdk_subprocess.py`](examples/ts_sdk_subprocess.py) |
| REST Server | Start TS server, call via `aiohttp`/`requests` | [`ts_sdk_server.py`](examples/ts_sdk_server.py) |

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

### `CoFHE bridge script not found`

Run `npm install` in the repository root to install `@cofhe/sdk` and `viem` dependencies.

### `node: command not found`

Install Node.js ≥18: [nodejs.org](https://nodejs.org/)

### Private key or RPC not set

Ensure `.env` is populated with `BLF_COFHE_RPC` and `BLF_PRIVATE_KEY`. For quick validation without keys, use `mock=True`.

---

## License

MIT — see [LICENSE](LICENSE).

## Links

- [Blindference Node](https://github.com/baync180705/blindference-node) — Run a compute node in the quorum
- [Blindference Docs](https://docs.blindference.xyz) — Full protocol documentation
- [Blindference Network](https://blindference.xyz) — Protocol overview
