# Blindference Agent

**Build confidential AI agents on the Blindference network.**

The Blindference Agent SDK lets Python developers submit encrypted inference requests to a decentralized quorum of nodes. All prompts are encrypted end-to-end (AES-256-GCM + CoFHE), executed by a leader + verifier quorum, and decrypted locally in your browser or Python runtime.

## Features

- **End-to-end encryption** — AES-256-GCM + Fhenix CoFHE threshold encryption
- **Quorum consensus** — 1 leader + N verifiers, hash-match verification
- **Async-first API** — Native `async/await` with sync wrappers
- **CoFHE bridge included** — Spawns `@cofhe/sdk/node` subprocess automatically
- **LangChain integration** — `BlindferenceLLM` wrapper for RAG, chains, agents
- **Streaming status** — Live execution trace: encryption → quorum → leader → verifier → on-chain → decrypt

## Quickstart

```bash
pip install blindference-agent
```

```python
import asyncio
import os
from blindference_agent import BlindferenceAgent

async def main():
    agent = BlindferenceAgent(
        icl_url="https://icl.blindference.xyz",
        cofhe_rpc="https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY",
        private_key="0x...",
    )

    result = await agent.inference(
        "Explain quantum computing",
        model_id="groq:llama-3.3-70b-versatile",
    )
    print(result.text)

asyncio.run(main())
```

## CLI

```bash
# Scaffold a new agent project
blindference-agent init my-agent
cd my-agent
# Edit .env with your keys

# Test connectivity
blindference-agent test

# Run your agent
blindference-agent run agent.py
```

## LangChain Integration

```python
from integrations.langchain import BlindferenceLLM
from langchain.chains import RetrievalQA

llm = BlindferenceLLM(
    icl_url="https://icl.blindference.xyz",
    cofhe_rpc="...",
    private_key="0x...",
    model="groq:llama-3.3-70b-versatile",
)

qa = RetrievalQA.from_chain_type(llm=llm, retriever=...)
result = qa.invoke("What is FHE?")
```

## Streaming Progress

```python
async for status in agent.stream_status(request.request_id):
    print(f"{status.step}: {status.confirm_count}/{status.verifier_count} confirmed")
```

## Architecture

```
Your Agent (Python)
    ↓
AES-GCM encrypt prompt
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

## Supported Models

| Model ID | Provider | Latency |
|----------|----------|---------|
| `groq:llama-3.3-70b-versatile` | Groq | Fast |
| `gemini:gemini-2.5-flash` | Google | Fast |
| `facebook/opt-125m` | Local vLLM | Variable |

## License

MIT — see [LICENSE](LICENSE).
