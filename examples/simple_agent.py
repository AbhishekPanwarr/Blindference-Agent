"""Simple one-shot confidential inference example."""

import asyncio
import os

from blindference_agent import BlindferenceAgent


async def main():
    agent = BlindferenceAgent(
        icl_url=os.environ.get("BLF_ICL_URL", "https://icl.blindference.xyz"),
        cofhe_rpc=os.environ.get("BLF_COFHE_RPC", ""),
        private_key=os.environ.get("BLF_PRIVATE_KEY", ""),
    )

    result = await agent.inference(
        prompt="What are the key risks of DeFi yield farming?",
        model_id="groq:llama-3.3-70b-versatile",
        verifier_count=2,
    )

    print("=" * 60)
    print("Result:")
    print(result.text)
    print("=" * 60)
    print(f"Model:     {result.model_id}")
    print(f"Leader:    {result.leader_address}")
    print(f"Verifiers: {', '.join(result.verifier_addresses)}")
    print(f"Commitment: {result.commitment_hash}")
    print(f"Request ID: {result.request_id}")


if __name__ == "__main__":
    asyncio.run(main())
