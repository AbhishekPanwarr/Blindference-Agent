"""Streaming execution trace example.

Demonstrates live monitoring of quorum execution: encryption, assignment,
leader inference, verifier replay, on-chain commitment, and result decryption."""

import asyncio
import os

from blindference_agent import BlindferenceAgent


async def main():
    agent = BlindferenceAgent(
        icl_url=os.environ.get("BLF_ICL_URL", "https://icl.blindference.xyz"),
        cofhe_rpc=os.environ.get("BLF_COFHE_RPC", ""),
        private_key=os.environ.get("BLF_PRIVATE_KEY", ""),
    )

    # Submit and immediately stream progress
    request = await agent.submit(
        prompt="Explain the concept of zero-knowledge proofs",
        model_id="gemini:gemini-2.5-flash",
        verifier_count=2,
    )

    print(f"Request submitted: {request.request_id}")
    print("Monitoring quorum execution...\n")

    async for status in agent.stream_status(request.request_id, interval=2.0):
        step_emoji = {
            "quorum": "Building Quorum",
            "leader": "Leader Inference",
            "verifier": "Verifier Replay",
            "onchain": "On-Chain Commit",
            "decrypt": "Decrypt Result",
            "error": "Execution Error",
        }.get(status.step, status.step)

        print(
            f"[{status.status:12}] {step_emoji:20} | "
            f"Verifiers: {status.confirm_count}/{status.verifier_count}"
        )

        if status.status == "ACCEPTED":
            print("\nQuorum consensus reached. Decrypting result...")
            result = await agent._decrypt_result(status, request.model_id)
            print(f"\n{'='*60}")
            print(result.text)
            print(f"{'='*60}")
            break

        if status.status in ("REJECTED", "DISPUTED"):
            print(f"\nInference failed: {status.status}")
            break

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
