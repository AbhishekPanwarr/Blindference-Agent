"""Interactive chat session with the Blindference network.

A REPL that submits each user message as a confidential inference request
and displays a live execution trace for every turn.
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


def _print_progress(status: str, poll_count: int) -> None:
    step_names = {
        "QUEUED":     "⏳  Queued — building quorum",
        "ASSIGNED":   "👑  Assigned — leader selected",
        "EXECUTING":  "🧠  Executing — leader inference + verifier replay",
        "VERIFYING":  "🔗  Verifying — on-chain commitment",
        "ACCEPTED":   "✅  Accepted — quorum consensus reached",
        "REJECTED":   "❌  Rejected — quorum failed",
        "DISPUTED":   "⚠️  Disputed — consensus not reached",
    }
    msg = step_names.get(status, status)
    print(f"\r      [{poll_count:3d}] {msg}", end="")


async def _poll_with_progress(agent, request_id: str, max_polls: int = 100) -> None:
    """Poll until ACCEPTED, printing live status."""
    for i in range(max_polls):
        status = await agent.icl.get_status(request_id)
        _print_progress(status.status, i + 1)
        if status.status == "ACCEPTED":
            print()
            return status
        if status.status in ("REJECTED", "DISPUTED"):
            print()
            raise RuntimeError(f"Inference failed: {status.status}")
        await asyncio.sleep(3.0)
    print()
    raise TimeoutError("Quorum consensus timeout")


async def chat_loop():
    print("=" * 70)
    print("Blindference Agent — Interactive Chat")
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
        print(f"[ERROR] Failed to initialize agent: {exc}")
        if not use_mock:
            print("        Check that BLF_COFHE_RPC and BLF_PRIVATE_KEY are set in .env")
            print("        Or run with BLF_MOCK=1 for a no-infrastructure demo.")
        sys.exit(1)

    wallet = await agent._ensure_wallet()
    print(f"Wallet: {wallet}")
    print()
    print("Commands:  type your message  |  'exit' / 'quit' / 'q'  to leave")
    print()

    history = []

    while True:
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input.strip():
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            break

        history.append({"role": "user", "content": user_input})
        print("  Encrypting prompt + CoFHE key + IPFS upload + storeKey + ICL submit...")

        try:
            request = await agent.submit(
                prompt=user_input,
                model_id="groq:llama-3.3-70b-versatile",
                verifier_count=2,
            )
            print(f"  Request ID: {request.request_id}")
            print("  Waiting for quorum consensus...")

            status = await _poll_with_progress(agent, request.request_id)
            print("  Decrypting result...")

            result = await agent._decrypt_result(status, request.model_id)
        except Exception as exc:
            print(f"  [ERROR] {exc}")
            continue

        history.append({"role": "agent", "content": result.text})
        print()
        print(f"Agent: {result.text}")
        print(f"  Metadata: leader={result.leader_address[:20]}..., verifiers={len(result.verifier_addresses)}, commitment={result.commitment_hash[:20]}...")
        print()

    print("\nSession ended. 👋")
    await agent.close()


if __name__ == "__main__":
    asyncio.run(chat_loop())
