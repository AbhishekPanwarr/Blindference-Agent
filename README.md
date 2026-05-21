# Blindference Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Build confidential AI agents on the Blindference network.**

The Blindference Agent SDK lets Python developers submit encrypted inference requests to a decentralized quorum of nodes. All prompts are encrypted end-to-end (AES-256-GCM + CoFHE), executed by a leader + verifier quorum, and decrypted locally in your Python runtime.

## 🚀 Quickstart

### One-Command Setup

```bash
curl -sSL https://raw.githubusercontent.com/baync180705/blindference-agent/main/setup.sh | bash
```

Or manually:

```bash
# 1. Clone
git clone https://github.com/baync180705/blindference-agent.git
cd blindference-agent

# 2. Install Python deps
pip install -e ".[dev,langchain]"

# 3. Install CoFHE bridge deps (requires Node.js)
npm install

# 4. Edit .env with your keys
cp .env .env.local
# Edit .env.local with your Alchemy key and private key

# 5. Run the notebook
jupyter lab examples/getting_started.ipynb
```

### Requirements

| Component | Required For | Version |
|-----------|-------------|---------|
| Python | SDK runtime | ≥3.10 |
| Node.js | CoFHE bridge | ≥18 |
| npm | CoFHE dependencies | bundled with Node |
| Alchemy API key | Real CoFHE mode | free tier works |

> **Note**: The CoFHE bridge requires npm packages (`@cofhe/sdk`, `viem`). A pure `pip install` is not sufficient — clone the repo and run `npm install` for the bridge.

---

## 📓 Start with the Notebook

The fastest way to learn the API:

[**Open `examples/getting_started.ipynb`**](examples/getting_started.ipynb)

7 interactive cells covering:

| Cell | Topic |
|------|-------|
| 1 | Setup check (validate Python, Node.js, npm deps, `.env`) |
| 2 | Simple inference (real mode + mock mode) |
| 3 | Streaming progress with `tqdm` progress bar |
| 4 | Batch inference — 3 prompts concurrently |
| 5 | Inspect `InferenceResult` metadata |
| 6 | Quorum info — preview leader + verifiers |
| 7 | Interactive chat loop |

---

## 🔒 Two Modes: Real vs Mock

### Real Mode (End-to-End Encryption)

```python
import asyncio
import os
from blindference_agent import BlindferenceAgent

async def main():
    agent = BlindferenceAgent(
        icl_url="https://icl.blindference.xyz",
        cofhe_rpc=os.environ.get("BLF_COFHE_RPC"),      # Alchemy Arbitrum Sepolia
        private_key=os.environ.get("BLF_PRIVATE_KEY"),  # Agent wallet
    )

    result = await agent.inference(
        "Explain quantum computing",
        model_id="groq:llama-3.3-70b-versatile",
    )
    print(result.text)

asyncio.run(main())
```

**What happens:**
1. AES-256-GCM encrypts your prompt
2. CoFHE bridge encrypts the AES key halves on-chain
3. Uploads encrypted blob to IPFS
4. ICL selects quorum (1 leader + 2 verifiers)
5. Nodes decrypt, run inference, hash results
6. Quorum consensus committed on-chain
7. You download + decrypt the result

### Mock Mode (No Encryption — for Demos)

```python
agent = BlindferenceAgent(
    icl_url="https://icl.blindference.xyz",
    mock=True,  # <-- skips all encryption, no keys needed
)

result = await agent.inference(
    "Explain quantum computing",
    model_id="groq:llama-3.3-70b-versatile",
)
```

**Use mock mode for:**
- Quick API exploration
- CI/CD tests
- Notebook demos
- Debugging without managing keys

> ⚠️ **Mock mode sends plaintext prompts. Never use for sensitive data.**

---

## 📁 Examples

| Example | File | Description |
|---------|------|-------------|
| **Getting Started** | [`examples/getting_started.ipynb`](examples/getting_started.ipynb) | Interactive Jupyter notebook (7 cells) |
| **Simple Agent** | [`examples/simple_agent.py`](examples/simple_agent.py) | One-shot inference |
| **Streaming Agent** | [`examples/streaming_agent.py`](examples/streaming_agent.py) | Live execution trace with emojis |
| **Batch Inference** | [`examples/batch_inference.py`](examples/batch_inference.py) | 3 prompts concurrently with `asyncio.gather()` |
| **Interactive Chat** | [`examples/interactive_chat.py`](examples/interactive_chat.py) | REPL chat loop with history |
| **Risk Scoring** | [`examples/risk_scoring_agent.py`](examples/risk_scoring_agent.py) | Numeric feature inference (loan risk) |
| **LangChain RAG** | [`examples/langchain_rag.py`](examples/langchain_rag.py) | Retrieval-Augmented Generation with BlindferenceLLM |

---

## 🔗 Architecture

```
Your Agent (Python)
    ↓
AES-GCM encrypt prompt (real mode) or plaintext (mock)
    ↓
CoFHE bridge (subprocess) encrypts AES key halves
    ↓
Upload encrypted blob to IPFS
    ↓
Store key on-chain (Arbitrum Sepolia)
    ↓
Submit to ICL → Quorum preview → Leader + Verifiers
    ↓
Nodes decrypt via CoFHE → run inference → hash results
    ↓
ICL aggregates consensus → on-chain commitment
    ↓
Your Agent downloads output → CoFHE decrypt key → AES decrypt result
```

---

## 🤖 LangChain Integration

The SDK provides a `BlindferenceLLM` wrapper for LangChain chains and agents. Install the optional dependency:

```bash
pip install -e ".[langchain]"
```

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

> **LangChain is completely optional.** You can build agents directly with `BlindferenceAgent` — no framework needed.

---

## 🛠️ Supported Models

| Model ID | Provider | Latency |
|----------|----------|---------|
| `groq:llama-3.3-70b-versatile` | Groq | Fast |
| `gemini:gemini-2.5-flash` | Google | Fast |
| `facebook/opt-125m` | Local vLLM | Variable |

---

## 🧪 Tests

```bash
python -m pytest tests/ -q
```

Covers: AES-GCM roundtrip, key split/merge, type instantiation, CLI scaffold.

---

## 🆘 Troubleshooting

### `CoFHE bridge script not found`

Run `npm install` in the repo root to install `@cofhe/sdk` and `viem`.

### `node: command not found`

Install Node.js ≥18: [nodejs.org](https://nodejs.org/)

### `ValueError: cofhe_rpc and private_key required`

Either:
- Set them in `.env` for real mode
- Use `mock=True` for quick demos

### `npm install` fails

If you're behind a proxy or have npm registry issues:
```bash
npm config set registry https://registry.npmjs.org/
npm install
```

---

## 📄 License

MIT — see [LICENSE](LICENSE).

## 🔗 Links

- [Blindference Node](https://github.com/baync180705/blindference-node) — Run a compute node
- [Blindference Docs](https://docs.blindference.xyz) — Full documentation
- [Blindference Network](https://blindference.xyz) — Main website
