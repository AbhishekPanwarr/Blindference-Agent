"""Batch inference example — submit multiple prompts concurrently.

Each prompt runs through its own quorum consensus pipeline."""

import asyncio
import os

from blindference_agent import BlindferenceAgent


async def batch_inference(prompts: list[str], model_id: str = "groq:llama-3.3-70b-versatile"):
    """Submit multiple prompts concurrently and collect all results."""
    agent = BlindferenceAgent(
        icl_url=os.environ.get("BLF_ICL_URL", "https://icl.blindference.xyz"),
        cofhe_rpc=os.environ.get("BLF_COFHE_RPC", ""),
        private_key=os.environ.get("BLF_PRIVATE_KEY", ""),
    )

    print(f"Submitting {len(prompts)} prompts concurrently...\n")

    # Submit all requests in parallel
    requests = await asyncio.gather(*[
        agent.submit(prompt, model_id, verifier_count=2)
        for prompt in prompts
    ])

    # Wait for all to complete
    results = []
    for req in requests:
        while True:
            status = await agent.icl.get_status(req.request_id)
            if status.status == "ACCEPTED":
                result = await agent._decrypt_result(status, req.model_id)
                results.append(result)
                break
            await asyncio.sleep(1.0)

    print("=" * 60)
    for i, (prompt, result) in enumerate(zip(prompts, results), 1):
        print(f"\nPrompt {i}: {prompt}")
        print(f"Result: {result.text[:120]}...")
        print(f"Request: {result.request_id}")
    print("=" * 60)

    await agent.close()
    return results


if __name__ == "__main__":
    prompts = [
        "What is machine learning in one sentence?",
        "Explain neural networks briefly",
        "What is overfitting in ML?",
    ]
    asyncio.run(batch_inference(prompts))
