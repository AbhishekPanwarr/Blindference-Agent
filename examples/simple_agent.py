"""Simple one-shot confidential inference with full execution trace.

This example demonstrates the complete Blindference flow with step-by-step
progress output so you can see exactly what is happening at each phase:

  1. Wallet initialization
  2. AES-256-GCM prompt encryption
  3. CoFHE key encryption (split into halves)
  4. IPFS upload of encrypted blob
  5. On-chain key storage (Arbitrum Sepolia)
  6. Quorum preview (leader + verifiers selected)
  7. ICL submission
  8. Polling for quorum consensus
  9. Result download + decryption
"""

import asyncio
import logging
import os
import sys

from blindference_agent import BlindferenceAgent

# Enable progress logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)

# Also show our agent steps
import builtins as _builtins
print = lambda *args, **kwargs: _builtins.print(*args, **kwargs)


async def main():
    print("=" * 70)
    print("Blindference Agent — Confidential Inference Demo")
    print("=" * 70)
    print()

    # ------------------------------------------------------------------
    # 1. Agent initialization
    # ------------------------------------------------------------------
    print("[1/9] Initializing agent...")
    print("        ICL URL:", os.environ.get("BLF_ICL_URL", "https://icl.blindference.xyz"))
    print("        CoFHE RPC:", os.environ.get("BLF_COFHE_RPC", "NOT SET")[:40] + "...")
    print("        Private key:", "SET" if os.environ.get("BLF_PRIVATE_KEY") else "NOT SET")
    print()

    use_mock = os.environ.get("BLF_MOCK", "0") in ("1", "true", "yes")
    if use_mock:
        print("        MODE: MOCK (no encryption, no CoFHE, no private key needed)")
        print("        Set BLF_MOCK=0 and configure .env for real confidential inference.")
        print()

    try:
        agent = BlindferenceAgent(
            icl_url=os.environ.get("BLF_ICL_URL", "https://icl.blindference.xyz"),
            cofhe_rpc=os.environ.get("BLF_COFHE_RPC", ""),
            private_key=os.environ.get("BLF_PRIVATE_KEY", ""),
            mock=use_mock,
        )
    except Exception as exc:
        print(f"[ERROR] Failed to initialize agent: {exc}")
        if not use_mock:
            print("        Check that BLF_COFHE_RPC and BLF_PRIVATE_KEY are set in .env")
            print("        Or run with BLF_MOCK=1 for a no-infrastructure demo.")
        sys.exit(1)

    wallet = await agent._ensure_wallet()
    print(f"[1/9] Agent ready — wallet: {wallet}")
    print()

    # ------------------------------------------------------------------
    # 2. Submit inference request (encryption + upload + store + submit)
    # ------------------------------------------------------------------
    print("[2/9] Encrypting prompt with AES-256-GCM...")
    print("[3/9] CoFHE-encrypting AES key halves...")
    print("[4/9] Uploading encrypted blob to IPFS...")
    print("[5/9] Storing key on-chain (Arbitrum Sepolia)...")
    print("[6/9] Fetching quorum preview...")
    print("[7/9] Submitting to ICL...")
    print()

    try:
        request = await agent.submit(
            prompt="What are the key risks of DeFi yield farming?",
            model_id="groq:llama-3.3-70b-versatile",
            verifier_count=2,
        )
    except Exception as exc:
        print(f"[ERROR] Submission failed: {exc}")
        print("        - Is the ICL running?")
        print("        - Is the CoFHE bridge configured?")
        print("        - Check ICL logs for errors")
        await agent.close()
        sys.exit(1)

    print(f"[7/9] Request submitted: {request.request_id}")
    print(f"        Status: {request.status}")
    print()

    # ------------------------------------------------------------------
    # 8. Poll for completion with live status
    # ------------------------------------------------------------------
    print("[8/9] Waiting for quorum consensus...")
    print("        (Leader runs inference, verifiers replay and confirm)")
    print()

    poll_count = 0
    max_polls = 100  # ~5 minutes at 3s intervals

    while poll_count < max_polls:
        status = await agent.icl.get_status(request.request_id)
        poll_count += 1

        step_names = {
            "QUEUED":     "⏳  Queued — building quorum",
            "ASSIGNED":   "👑  Assigned — leader selected",
            "EXECUTING":  "🧠  Executing — leader inference + verifier replay",
            "VERIFYING":  "🔗  Verifying — on-chain commitment",
            "ACCEPTED":   "✅  Accepted — quorum consensus reached",
            "REJECTED":   "❌  Rejected — quorum failed",
            "DISPUTED":   "⚠️  Disputed — consensus not reached",
        }

        step_msg = step_names.get(status.status, status.status)
        progress = f"[{poll_count:3d}] {step_msg}"

        if status.status == "ACCEPTED":
            print(f"\r{progress}", end="")
            print()  # newline
            print()
            break
        elif status.status in ("REJECTED", "DISPUTED"):
            print(f"\r{progress}", end="")
            print()
            print(f"[ERROR] Inference failed with status: {status.status}")
            await agent.close()
            sys.exit(1)
        else:
            print(f"\r{progress}", end="")

        await asyncio.sleep(3.0)
    else:
        print()
        print("[ERROR] Timeout waiting for quorum consensus")
        print("        - Are nodes running and attested?")
        print("        - Check ICL and node logs")
        await agent.close()
        sys.exit(1)

    # ------------------------------------------------------------------
    # 9. Decrypt and display result
    # ------------------------------------------------------------------
    print("[9/9] Downloading and decrypting result...")
    print()

    try:
        result = await agent._decrypt_result(status, request.model_id)
    except Exception as exc:
        print(f"[ERROR] Failed to decrypt result: {exc}")
        await agent.close()
        sys.exit(1)

    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print(result.text)
    print("=" * 70)
    print()
    print("Metadata:")
    print(f"  Model:        {result.model_id}")
    print(f"  Request ID:   {result.request_id}")
    print(f"  Task ID:      {result.task_id}")
    print(f"  Leader:       {result.leader_address}")
    print(f"  Verifiers:    {len(result.verifier_addresses)} ({', '.join(v[:20] + '...' for v in result.verifier_addresses)})")
    print(f"  Commitment:   {result.commitment_hash[:30]}..." if result.commitment_hash else "  Commitment:   N/A")
    print(f"  Output CID:   {result.output_cid}")
    print()

    await agent.close()
    print("Done. 👍")


if __name__ == "__main__":
    asyncio.run(main())
