"""Interactive chat session with the Blindference network.

A simple REPL that submits each user message as a confidential inference request
and displays the result with quorum metadata."""

import asyncio
import os

from blindference_agent import BlindferenceAgent


async def chat_loop():
    """Interactive chat session."""
    agent = BlindferenceAgent(
        icl_url=os.environ.get("BLF_ICL_URL", "https://icl.blindference.xyz"),
        cofhe_rpc=os.environ.get("BLF_COFHE_RPC", ""),
        private_key=os.environ.get("BLF_PRIVATE_KEY", ""),
    )

    print("Blindference Agent — Interactive Session")
    print("Type 'exit' to quit")
    print("=" * 60)

    history = []

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ("exit", "quit", "q"):
            break

        history.append({"role": "user", "content": user_input})
        print("  Processing...")

        result = await agent.inference(
            prompt=user_input,
            model_id="groq:llama-3.3-70b-versatile",
            verifier_count=2,
        )

        history.append({"role": "agent", "content": result.text})
        print(f"\nAgent: {result.text}")
        print(f"  [Leader: {result.leader_address[:20]}..., Verifiers: {len(result.verifier_addresses)}]")

    print("\nSession ended.")
    await agent.close()


if __name__ == "__main__":
    asyncio.run(chat_loop())
