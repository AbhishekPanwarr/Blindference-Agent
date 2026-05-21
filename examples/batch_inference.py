"""Batch inference example — submit multiple prompts concurrently.

Each prompt runs through its own quorum consensus pipeline. This example
shows live progress for every job, so you can see exactly what is
happening in the confidential inference flow.
"""

import asyncio
import logging
import os
import sys

from blindference_agent import BlindferenceAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)


async def _poll_one(agent, request_id: str, label: str, max_polls: int = 100):
    """Poll a single request, printing a compact per-line progress log."""
    step_names = {
        "QUEUED":     "queued",
        "ASSIGNED":   "assigned",
        "EXECUTING":  "executing",
        "VERIFYING":  "verifying",
        "ACCEPTED":   "ACCEPTED",
        "REJECTED":   "REJECTED",
        "DISPUTED":   "DISPUTED",
    }
    for i in range(max_polls):
        status = await agent.icl.get_status(request_id)
        short = step_names.get(status.status, status.status)
        print(f"  [{label}] {short:10s} (poll {i + 1:3d})")
        if status.status == "ACCEPTED":
            return status
        if status.status in ("REJECTED", "DISPUTED"):
            raise RuntimeError(f"{label} failed: {status.status}")
        await asyncio.sleep(3.0)
    raise TimeoutError(f"{label} timeout")


async def batch_inference(prompts: list[str], model_id: str = "groq:llama-3.3-70b-versatile"):
    print("=" * 70)
    print("Blindference Agent — Batch Inference")
    print("=" * 70)
    print()
    print("Initializing agent...")

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
        print(f"[ERROR] {exc}")
        if not use_mock:
            print("        Check that BLF_COFHE_RPC and BLF_PRIVATE_KEY are set in .env")
            print("        Or run with BLF_MOCK=1 for a no-infrastructure demo.")
        sys.exit(1)

    wallet = await agent._ensure_wallet()
    print(f"Wallet: {wallet}")
    print()
    print(f"Submitting {len(prompts)} prompts concurrently...")
    print("Each job: encrypt → IPFS → storeKey → ICL → quorum consensus → decrypt")
    print()

    # Phase 1 — submit all in parallel
    print("--- Phase 1: Submit all requests ---")
    tasks = [
        agent.submit(prompt, model_id, verifier_count=2)
        for prompt in prompts
    ]
    requests = await asyncio.gather(*tasks)

    for i, req in enumerate(requests, 1):
        print(f"  Job {i}: request_id={req.request_id}, status={req.status}")
    print()

    # Phase 2 — poll all in parallel
    print("--- Phase 2: Wait for quorum consensus ---")
    poll_tasks = [
        _poll_one(agent, req.request_id, f"Job {i + 1}")
        for i, req in enumerate(requests)
    ]
    statuses = await asyncio.gather(*poll_tasks)
    print()

    # Phase 3 — decrypt all
    print("--- Phase 3: Decrypt results ---")
    results = []
    for i, (req, status) in enumerate(zip(requests, statuses), 1):
        print(f"  Job {i}: decrypting...")
        result = await agent._decrypt_result(status, req.model_id)
        results.append(result)
    print()

    # Display
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    for i, (prompt, result) in enumerate(zip(prompts, results), 1):
        print()
        print(f"Prompt {i}: {prompt}")
        print(f"Result:   {result.text[:200]}...")
        print(f"Request:  {result.request_id}")
        print(f"Leader:   {result.leader_address}")
        print(f"Commit:   {result.commitment_hash[:20]}...")
    print()
    print("=" * 70)

    await agent.close()
    print("Done. 👍")
    return results


if __name__ == "__main__":
    prompts = [
        "What is machine learning in one sentence?",
        "Explain neural networks briefly",
        "What is overfitting in ML?",
    ]
    asyncio.run(batch_inference(prompts))
