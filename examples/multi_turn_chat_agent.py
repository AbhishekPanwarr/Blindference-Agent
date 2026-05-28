"""Multi-turn confidential chat agent with conversation memory.

This example builds a stateful chat agent that:
  1. Maintains a rolling conversation history
  2. Encrypts each turn end-to-end via the Blindference network
  3. Automatically injects a system prompt for context
  4. Handles streaming status updates for UX feedback

The agent can be backed by either:
  - The native Python SDK (blindference_agent.BlindferenceAgent)
  - The TypeScript SDK via subprocess or REST server

This example uses the Python SDK for simplicity; swap the
`submit_turn` coroutine to use the TS interop patterns from
`ts_sdk_subprocess.py` or `ts_sdk_server.py` if desired.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).with_name(".env"), override=False)

from blindference_agent import BlindferenceAgent, InferenceResult

logger = logging.getLogger("multi_turn_chat")


# ---------------------------------------------------------------------------
# Conversation state
# ---------------------------------------------------------------------------

@dataclass
class Turn:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class Conversation:
    turns: list[Turn] = field(default_factory=list)
    max_turns: int = 20  # rolling window — drop oldest beyond this

    def add(self, role: str, content: str) -> None:
        self.turns.append(Turn(role, content))
        if len(self.turns) > self.max_turns:
            # Drop oldest non-system turns first
            for i, t in enumerate(self.turns):
                if t.role != "system":
                    self.turns.pop(i)
                    break

    def to_prompt(self, system: str | None = None) -> str:
        """Serialize conversation into a single prompt string."""
        lines: list[str] = []
        if system:
            lines.append(f"<system>\n{system}\n</system>")
        for t in self.turns:
            tag = "user" if t.role == "user" else "assistant"
            lines.append(f"<{tag}>\n{t.content}\n</{tag}>")
        lines.append("<assistant>\n")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent wrapper
# ---------------------------------------------------------------------------

class ConfidentialChatAgent:
    """Stateful chat agent that submits encrypted turns to Blindference."""

    def __init__(
        self,
        system_prompt: str = (
            "You are a helpful, privacy-conscious AI assistant. "
            "You never reveal sensitive information. "
            "Keep answers concise and factual."
        ),
        model_id: str = "groq:llama-3.3-70b-versatile",
        verifier_count: int = 2,
        mock: bool = False,
    ) -> None:
        self.system = system_prompt
        self.model_id = model_id
        self.verifier_count = verifier_count
        self.mock = mock
        self.conversation = Conversation()
        self._agent: BlindferenceAgent | None = None

    async def _ensure_agent(self) -> BlindferenceAgent:
        if self._agent is None:
            self._agent = BlindferenceAgent(
                icl_url=os.environ.get("BLF_ICL_URL", "https://icl.blindference.xyz"),
                cofhe_rpc=os.environ.get("BLF_COFHE_RPC", ""),
                private_key=os.environ.get("BLF_PRIVATE_KEY", ""),
                mock=self.mock,
            )
        return self._agent

    async def submit_turn(self, user_message: str) -> InferenceResult:
        """Encrypt the conversation context + new user message and submit."""
        self.conversation.add("user", user_message)
        prompt = self.conversation.to_prompt(self.system)

        agent = await self._ensure_agent()
        result = await agent.inference(
            prompt=prompt,
            model_id=self.model_id,
            verifier_count=self.verifier_count,
        )

        self.conversation.add("assistant", result.text)
        return result

    async def stream_turn(
        self,
        user_message: str,
    ) -> AsyncIterator[str]:
        """Yield status updates, then the final result text."""
        self.conversation.add("user", user_message)
        prompt = self.conversation.to_prompt(self.system)

        agent = await self._ensure_agent()
        request = await agent.submit(
            prompt=prompt,
            model_id=self.model_id,
            verifier_count=self.verifier_count,
        )

        yield f"STATUS: Submitted request {request.request_id}"

        # Stream status updates
        async for status in agent.stream_status(request.request_id, interval=2.0):
            yield f"STATUS: {status.status}"
            if status.status in ("ACCEPTED", "REJECTED", "DISPUTED"):
                break

        # Fetch final result
        result = await agent._decrypt_result(status, self.model_id)
        self.conversation.add("assistant", result.text)
        yield f"RESULT: {result.text}"

    async def close(self) -> None:
        if self._agent is not None:
            await self._agent.close()


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------

async def interactive_chat():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 70)
    print("Confidential Multi-Turn Chat Agent")
    print("=" * 70)
    print("Type your message and press Enter. Type 'quit' or 'exit' to stop.\n")

    use_mock = os.environ.get("BLF_MOCK", "false").lower() in ("1", "true", "yes")
    if use_mock:
        print("⚠️  MOCK MODE — prompts sent in plaintext\n")

    agent = ConfidentialChatAgent(mock=use_mock)

    try:
        while True:
            try:
                user_input = input("You > ")
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break

            message = user_input.strip()
            if message.lower() in ("quit", "exit", "q"):
                print("Goodbye.")
                break
            if not message:
                continue

            print("Agent > ", end="", flush=True)

            # Non-streaming mode for REPL simplicity
            try:
                result = await agent.submit_turn(message)
                print(result.text)
                print(f"   (Leader: {result.leader_address[:10]}... | "
                      f"Commitment: {result.commitment_hash[:16]}...)")
            except Exception as exc:
                print(f"[Error] {exc}")

    finally:
        await agent.close()


# ---------------------------------------------------------------------------
# Batch conversation test (non-interactive)
# ---------------------------------------------------------------------------

async def batch_conversation():
    """Run a scripted multi-turn conversation and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    use_mock = os.environ.get("BLF_MOCK", "false").lower() in ("1", "true", "yes")
    agent = ConfidentialChatAgent(
        system_prompt="You are a cryptography tutor. Explain concepts simply.",
        mock=use_mock,
    )

    turns = [
        "What is homomorphic encryption?",
        "Can you give a real-world example where it's used?",
        "How does it compare to zero-knowledge proofs?",
    ]

    print("=" * 70)
    print("Batch Multi-Turn Conversation")
    print("=" * 70)

    try:
        for i, user_message in enumerate(turns, 1):
            print(f"\n[Turn {i}] User: {user_message}")
            result = await agent.submit_turn(user_message)
            print(f"[Turn {i}] Agent: {result.text[:300]}...")
            print(f"         Leader: {result.leader_address[:10]}...")
    finally:
        await agent.close()

    print("\nConversation complete.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Multi-turn confidential chat agent")
    parser.add_argument("--batch", action="store_true", help="Run scripted batch conversation")
    args = parser.parse_args()

    if args.batch:
        asyncio.run(batch_conversation())
    else:
        asyncio.run(interactive_chat())
