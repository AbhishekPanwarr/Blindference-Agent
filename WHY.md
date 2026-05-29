# Why Blindference Agent SDK Exists

> **Confidential AI inference for agents, bots, and autonomous systems.**
>
> *Your prompt never leaves your machine in plaintext. Ever.*

---

## The Problem We Solve

### AI Inference Today is Not Private

When you send a prompt to ChatGPT, Claude, or any cloud LLM API, three things happen:

1. **Your prompt travels in plaintext** over HTTPS to the provider's servers
2. **The provider logs, stores, and may train on your data** (check their Terms of Service)
3. **You have no cryptographic guarantee** that the response came from the model you requested

This is fine for "What is the capital of France?" but catastrophic for:
- **Financial data** ("Analyze this portfolio risk...")
- **Medical records** ("Summarize this patient history...")
- **Legal documents** ("Review this contract for liability...")
- **Proprietary code** ("Debug this internal algorithm...")
- **Agent memory** (Autonomous agents that accumulate sensitive context over time)

### The "Just Use a Local Model" Fallacy

Running Llama 3 on your laptop solves privacy, but creates new problems:
- **No consensus** — How do you know the model wasn't tampered with?
- **No accountability** — If the model hallucinates, who is responsible?
- **No premium models** — You can't run GPT-4 or Claude locally
- **No verifiable compute** — Did the node actually run inference, or just return a cached response?

### The "Just Trust the Cloud" Fallacy

Using OpenAI API with a Business Associate Agreement (BAA) is better, but:
- **You still send plaintext** — encryption in transit != encryption at rest
- **You still trust a single entity** — centralization is the anti-pattern of decentralization
- **No proof of execution** — You get a response, not a cryptographic attestation

---

## What Blindference Agent SDK Does

Blindference Agent SDK is a **TypeScript/Node.js toolkit** that lets you:

1. **Encrypt prompts locally** using AES-256-GCM + Fhenix CoFHE (Fully Homomorphic Encryption)
2. **Submit to a decentralized quorum** of verified compute nodes (1 Leader + N Verifiers)
3. **Receive cryptographically guaranteed results** — only if a majority of nodes agree on the exact same output
4. **Decrypt results locally** — the plaintext never touches any server

### The Magic: CoFHE + Quorum Consensus

```
Your Machine                                          Blindference Network
┌─────────────────┐                                  ┌────────────────────────┐
│ 1. Type prompt  │                                  │  Node 1 (Leader)       │
│ 2. AES encrypt  │─────Encrypted blob──────────────→│  Node 2 (Verifier)     │
│    locally      │      (IPFS + on-chain keys)     │  Node 3 (Verifier)     │
│                 │                                  │                        │
│ 3. Wait...      │                                  │  All 3 nodes decrypt   │
│                 │                                  │  the SAME prompt, run  │
│ 4. Receive      │←────Encrypted result────────────│  the SAME model, hash  │
│    encrypted    │      (only if 2/3 agree)        │  the SAME output       │
│    result       │                                  │                        │
│ 5. Decrypt      │                                  │  ICL commits on-chain  │
│    locally      │                                  │  if consensus reached    │
└─────────────────┘                                  └────────────────────────┘
     ↑                                                        ↑
     │                                                        │
Plaintext NEVER leaves        Cryptographic proof of          Nodes are verified
your machine                  honest execution                  via on-chain attestations
```

### Key Properties

| Property | How It's Achieved |
|----------|-------------------|
| **Prompt Privacy** | AES-256-GCM encryption; key split into CoFHE ciphertexts; only your wallet can decrypt |
| **Result Integrity** | SHA-256 commitment; quorum consensus; on-chain settlement |
| **Model Verifiability** | Nodes are attested (TPM/SGX/mock); tier-based selection |
| **No Single Point of Trust** | Leader + 2 verifiers must agree; no one node can cheat |
| **Payment Transparency** | cUSDC credits; on-chain escrow; auto-payout on consensus |

---

## Who Is This For?

### 1. Autonomous Agent Developers

Building a crypto trading bot, DeFi agent, or DAO automation tool?

```typescript
// Your agent can now query LLMs without exposing strategy
const result = await agent.infer({
  prompt: `Analyze this portfolio: ${encryptedPortfolioData}`,
  modelId: 'groq:llama-3.3-70b-versatile'
})
// The prompt is encrypted before it leaves your server
// The response is verified by 3 independent nodes
```

### 2. Privacy-First Application Developers

Building a medical AI assistant, legal document analyzer, or financial advisor?

```typescript
// HIPAA/GDPR-compliant inference without trusting the model provider
const result = await agent.infer({
  prompt: patientHistory,  // encrypted automatically
  modelId: 'gemini:gemini-2.5-flash',
  insurance: true  // coverage + dispute resolution
})
```

### 3. DeFi Protocol Developers

Need oracle-style LLM inference for smart contracts?

```typescript
// On-chain verifiable inference result
const result = await agent.infer({
  prompt: 'Is this transaction suspicious?',
  modelId: 'groq:llama-3.3-70b-versatile'
})
// result.commitmentHash can be verified on-chain
```

### 4. Python Developers

Not a TypeScript shop? No problem.

```python
# examples/agent_demo.py
from agent_demo import BlindferenceAgent

agent = BlindferenceAgent()
result = agent.infer("Explain zero-knowledge proofs")
print(result["output"])  # Decrypted plaintext
```

The SDK is a TypeScript CLI under the hood, but we provide Python wrappers.

---

## Quick Start (5 Minutes)

### 1. Install

```bash
npm install -g @abhieren/blindference-agent
```

### 2. Configure

Create a `.env` file:

```bash
cat > .env << 'EOF'
# REQUIRED: Your Arbitrum Sepolia wallet private key
# Generate a fresh wallet at https://metamask.io/, fund with Sepolia ETH
BLF_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE

# REQUIRED: RPC endpoint (get free key at https://www.alchemy.com/)
BLF_RPC_URL=https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY

# PRODUCTION endpoints (default — no need to change)
BLF_PAYMENT_URL=https://payment.blindference.xyz
BLF_ICL_URL=https://icl.blindference.xyz
EOF
```

### 3. Get Credits

```bash
# 1. Get free BLIND tokens from the faucet
# Visit: https://blindference.xyz/faucet

# 2. Purchase inference credits
blindference-agent buy-package --id starter
```

### 4. Run Inference

```bash
blindference-agent infer \
  --prompt "What is the capital of France?" \
  --model groq:llama-3.3-70b-versatile \
  --currency cUSDC
```

**What happens under the hood:**
1. CoFHE client initializes (5s)
2. Your prompt is AES-256-GCM encrypted locally
3. AES key is split and encrypted with Fhenix CoFHE
4. Encrypted prompt uploaded to IPFS
5. Job submitted to Payment Service
6. ICL selects 1 Leader + 2 Verifiers from attested nodes
7. All 3 nodes decrypt, run inference, submit hash commitments
8. ICL checks consensus (2/3 must match exactly)
9. Result encrypted with new AES key, uploaded to IPFS
10. You download and decrypt locally
11. Output displayed

**Timeline:** 30-180 seconds depending on model and quorum availability.

---

## Architecture Deep Dive

### Layer 1: Local Encryption

```
Plaintext Prompt
     ↓
AES-256-GCM (random key)
     ↓
Ciphertext + Auth Tag + IV → IPFS
     ↓
AES Key Split into High/Low 64-bit halves
     ↓
Each half encrypted with Fhenix CoFHE
     ↓
CoFHE ciphertext handles → Arbitrum Sepolia (on-chain storage)
```

**Why two layers?**
- AES is fast for large payloads (your prompt)
- CoFHE is slow but allows threshold decryption by multiple nodes
- The combination: fast + private + verifiable

### Layer 2: Quorum Selection

```
ICL (Inference Coordination Layer)
     ↓
Randomly selects 1 Leader + N Verifiers
     ↓
Nodes must have:
  - Valid attestation certificate (TPM/SGX/mock)
  - Minimum stake (1 wei on testnet)
  - Supported model tier match
     ↓
Node addresses added to on-chain ACL
     ↓
Each node receives a CoFHE sharing permit
```

**Why quorum?**
- Leader executes first → submits result
- Verifiers re-execute → confirm hash match
- If Leader cheats, verifiers reject → consensus fails → refund

### Layer 3: Consensus & Settlement

```
Leader submits:   output_cid + commitment_hash + encrypted_output_key
Verifier 1 submits: commitment_hash + verdict (CONFIRM/REJECT)
Verifier 2 submits: commitment_hash + verdict (CONFIRM/REJECT)
     ↓
ICL counts matching hashes
     ↓
If ≥2/3 match:
  → Status: ACCEPTED
  → On-chain commit of winning hash
  → Auto-payout to nodes
     ↓
If <2/3 match:
  → Status: REJECTED
  → Refund to user
  → Nodes slashed (future)
```

### Layer 4: Local Decryption

```
You receive:
  - output_cid (IPFS location of encrypted result)
  - encrypted_output_key_high/low (CoFHE handles)
     ↓
Your wallet calls CoFHE threshold network
     ↓
Decrypt output key halves → reconstruct AES key
     ↓
Download encrypted result from IPFS
     ↓
AES-GCM decrypt locally
     ↓
Plaintext output (never touched any server!)
```

---

## Security Model

### Threat: Prompt Leakage

| Attack Vector | Mitigation |
|---------------|------------|
| Network sniffing | AES-256-GCM + TLS 1.3 |
| IPFS node reads | AES encryption; ciphertext is meaningless without key |
| CoFHE threshold network | Fhenix uses multi-party computation; no single party sees plaintext |
| On-chain storage | Only CoFHE ciphertext handles stored; keys are encrypted |

### Threat: Result Tampering

| Attack Vector | Mitigation |
|---------------|------------|
| Leader returns wrong result | 2 verifiers must independently confirm hash match |
| Verifier collusion with leader | Random quorum selection; economic stake at risk |
| Model substitution | Attestation binds node to specific model weights |
| Censorship | Decentralized node network; no single point of control |

### Threat: Non-Payment / Free Riding

| Attack Vector | Mitigation |
|---------------|------------|
| User doesn't pay | Escrow created before inference; funds locked |
| Nodes don't execute | Stake slashed; reputation system |
| ICL doesn't route | Open-source; anyone can run ICL; on-chain settlement |

---

## Comparison Table

| Feature | OpenAI API | Local LLM | Blindference |
|---------|-----------|-----------|--------------|
| **Prompt Privacy** | ❌ Plaintext | ✅ Local | ✅ Encrypted (AES+CoFHE) |
| **Result Integrity** | ❌ Trust provider | ✅ You ran it | ✅ Quorum consensus |
| **Premium Models** | ✅ GPT-4, etc. | ❌ Limited | ✅ Groq, Gemini, etc. |
| **Verifiable Compute** | ❌ No proof | ❌ No proof | ✅ On-chain commitments |
| **Decentralized** | ❌ Centralized | ✅ Local only | ✅ Multi-node quorum |
| **Payment Model** | Subscription | Free | Pay-per-inference (cUSDC) |
| **Easy Integration** | ✅ SDK | ❌ Complex setup | ✅ One-line CLI |

---

## Development Setup

### Local Development (Advanced)

If you want to run the entire stack locally:

```bash
# Terminal 1: ICL
cd blindference/network/packages/icl
./.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2: Payment Service
cd blindference/network/packages/payment
./.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001

# Terminal 3: Node 1
cd blindference-node
BLF_PRIVATE_KEY=... BLF_CALLBACK_PORT=9101 ./venv/bin/blindference-node run

# Terminal 4: Node 2
BLF_PRIVATE_KEY=... BLF_CALLBACK_PORT=9102 ./venv/bin/blindference-node run

# Terminal 5: Node 3
BLF_PRIVATE_KEY=... BLF_CALLBACK_PORT=9103 ./venv/bin/blindference-node run

# Terminal 6: Your Agent
blindference-agent infer --prompt "test" --icl http://127.0.0.1:8000 --payment-service http://127.0.0.1:8001
```

See [LOCAL_DEV.md](LOCAL_DEV.md) for full instructions.

---

## FAQ

**Q: Is this production-ready?**
A: This is an **alpha testnet release** on Arbitrum Sepolia. The cryptography is sound, but the network is small. Do not use for high-stakes applications yet.

**Q: How much does inference cost?**
A: Starter package is ~10 cUSDC (~$0.01 USD) per inference. Costs depend on model and quorum size.

**Q: Can I use my own model?**
A: Not yet. The network currently supports Groq-hosted models (Llama 3.3 70B) and Gemini Flash. Self-hosted model support is on the roadmap.

**Q: What if all nodes are down?**
A: The ICL will return a timeout error. Your funds remain in escrow and can be refunded after the dispute window (24 hours).

**Q: Can I verify the result on-chain?**
A: Yes. Every accepted result has a `commitmentHash` that is committed to the `BlindferenceInference` contract on Arbitrum Sepolia. You can verify it yourself.

**Q: Is the code open source?**
A: Yes. MIT licensed. The node runtime, ICL, and SDK are all open source.

---

## Next Steps

1. **[Install the SDK](README.md#installation)** — `npm install -g @abhieren/blindference-agent`
2. **[Get testnet funds](README.md#prerequisites)** — ETH + BLIND tokens
3. **[Run your first inference](README.md#quickstart)** — One command, fully encrypted
4. **[Read the API docs](README.md#sdk-api)** — Programmatic usage
5. **[Run a node](https://github.com/baync180705/blindference-node)** — Earn cUSDC by providing compute

---

## Links

- **NPM Package**: [@abhieren/blindference-agent](https://www.npmjs.com/package/@abhieren/blindference-agent)
- **GitHub**: [AbhishekPanwarr/Blindference-Agent](https://github.com/AbhishekPanwarr/Blindference-Agent)
- **Network**: [blindference.xyz](https://blindference.xyz)
- **Docs**: [docs.blindference.xyz](https://docs.blindference.xyz)
- **Node Software**: [baync180705/blindference-node](https://github.com/baync180705/blindference-node)

---

*Built with ❤️ by the Blindference team. Privacy is not a feature — it's the foundation.*
