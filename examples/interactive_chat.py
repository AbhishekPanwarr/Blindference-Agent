"""Interactive chat loop with the Blindference network."""

import asyncio
import os

from blindference_agent import BlindferenceAgent


async def chat_loop():
    """Simple REPL chat with the Blindference Agent."""
    agent = BlindferenceAgent(
        icl_url=os.environ.get("BLF_ICL_URL", "https://icl.blindference.xyz"),
        mock=True,  # Use mock=True for quick demos; set to False for real encryption
    )

    print("🤖 Blindference Agent Chat")
    print("Type your question or 'exit' to quit")
    print("=" * 60)

    history = []

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ("exit", "quit", "q"):
            break

        history.append({"role": "user", "content": user_input})
        print("  Thinking...")

        result = await agent.inference(
            prompt=user_input,
            model_id="groq:llama-3.3-70b-versatile",
            verifier_count=2,
        )

        history.append({"role": "agent", "content": result.text})
        print(f"\nAgent: {result.text}")
        print(f"  [Leader: {result.leader_address[:20]}..., Verifiers: {len(result.verifier_addresses)}]")

    print("\nGoodbye! 👋")
    await agent.close()


if __name__ == "__main__":
    asyncio.run(chat_loop())
