"""Tool-augmented confidential agent with local tool execution.

This example demonstrates an agent that:
  1. Receives a user query that may require tool use
  2. Plans which tools to invoke (local Python functions)
  3. Executes tools locally (no network round-trip)
  4. Submits the tool results back to the LLM via the encrypted pipeline
  5. Returns the final synthesized answer

Tools implemented:
  - calculator: evaluate arithmetic expressions safely
  - datetime: get current date/time
  - word_count: count words in a text snippet

The LLM is invoked through the Blindference encrypted inference pipeline
for every step that needs reasoning, keeping all prompts confidential.

Backends:
  - Python SDK (default)
  - TypeScript SDK via subprocess or REST (swap the submit function)
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=False)

from blindference_agent import BlindferenceAgent, InferenceResult

logger = logging.getLogger("tool_agent")


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

ToolFunc = Callable[..., str]


def _tool_calculator(expression: str) -> str:
    """Safely evaluate a simple arithmetic expression."""
    # Whitelist: digits, operators, parentheses, decimal point, spaces
    if not re.fullmatch(r"[\d\+\-\*\/\.\(\)\s]+", expression):
        return "Error: invalid characters in expression"
    try:
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as exc:
        return f"Error: {exc}"


def _tool_datetime(_: str = "") -> str:
    """Return the current UTC date and time."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _tool_word_count(text: str) -> str:
    """Count words in the provided text."""
    return str(len(text.split()))


TOOL_REGISTRY: dict[str, ToolFunc] = {
    "calculator": _tool_calculator,
    "datetime": _tool_datetime,
    "word_count": _tool_word_count,
}

TOOL_SCHEMA = """Available tools:
1. calculator(expression: str) -> str
   Evaluates a simple arithmetic expression (e.g., "2 + 2 * 3").

2. datetime() -> str
   Returns the current UTC date and time.

3. word_count(text: str) -> str
   Counts the number of words in the provided text.
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ToolUsingAgent:
    """Agent that plans tool use, executes locally, and submits follow-ups
    through the encrypted inference pipeline."""

    def __init__(
        self,
        model_id: str = "groq:llama-3.3-70b-versatile",
        verifier_count: int = 2,
        mock: bool = False,
    ) -> None:
        self.model_id = model_id
        self.verifier_count = verifier_count
        self.mock = mock
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

    async def _infer(self, prompt: str) -> InferenceResult:
        """Submit a prompt through the encrypted pipeline."""
        agent = await self._ensure_agent()
        return await agent.inference(
            prompt=prompt,
            model_id=self.model_id,
            verifier_count=self.verifier_count,
        )

    async def run(self, user_query: str) -> str:
        """End-to-end tool-augmented inference."""
        logger.info("User query: %s", user_query)

        # Step 1: Planning — ask the LLM which tools to use
        plan_prompt = f"""<system>
You are a planning assistant. The user has asked a question. Decide whether
any tools are needed to answer it accurately. If tools are needed, list
them in the format TOOL:tool_name:argument. If no tools are needed,
reply with NO_TOOLS.

{TOOL_SCHEMA}
</system>

<user>
{user_query}
</user>

<assistant>
Plan:"""

        logger.info("[Step 1] Planning...")
        plan_result = await self._infer(plan_prompt)
        plan_text = plan_result.text.strip()
        logger.info("Plan: %s", plan_text[:200])

        # Parse tool calls from plan
        tool_calls: list[tuple[str, str]] = []
        for line in plan_text.splitlines():
            line = line.strip()
            if line.startswith("TOOL:"):
                parts = line.split(":", 2)
                if len(parts) == 3:
                    tool_calls.append((parts[1], parts[2]))

        # Step 2: Execute tools locally
        tool_results: list[str] = []
        if tool_calls:
            logger.info("[Step 2] Executing %d tool(s)...", len(tool_calls))
            for tool_name, argument in tool_calls:
                tool_fn = TOOL_REGISTRY.get(tool_name)
                if tool_fn is None:
                    result = f"Error: unknown tool '{tool_name}'"
                else:
                    try:
                        result = tool_fn(argument)
                    except Exception as exc:
                        result = f"Error executing {tool_name}: {exc}"
                tool_results.append(f"{tool_name}({argument}) -> {result}")
                logger.info("  %s", tool_results[-1])
        else:
            logger.info("[Step 2] No tools needed.")

        # Step 3: Final answer with tool results
        if tool_results:
            final_prompt = f"""<system>
You are a helpful assistant. Use the tool results below to answer the
user's question accurately. Incorporate the tool output naturally.
</system>

<user>
{user_query}
</user>

<tools>
{"\n".join(tool_results)}
</tools>

<assistant>"""
        else:
            final_prompt = f"""<system>
You are a helpful assistant. Answer the user's question directly.
</system>

<user>
{user_query}
</user>

<assistant>"""

        logger.info("[Step 3] Final inference...")
        final_result = await self._infer(final_prompt)
        logger.info("Done (leader=%s...)", final_result.leader_address[:10])

        return final_result.text

    async def close(self) -> None:
        if self._agent is not None:
            await self._agent.close()


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 70)
    print("Tool-Augmented Confidential Agent")
    print("=" * 70)

    use_mock = os.environ.get("BLF_MOCK", "false").lower() in ("1", "true", "yes")
    if use_mock:
        print("⚠️  MOCK MODE — plaintext submission\n")

    agent = ToolUsingAgent(mock=use_mock)

    queries = [
        "What is 42 multiplied by 17 plus 100?",
        "How many words are in the sentence 'The quick brown fox jumps over the lazy dog'?",
        "What is the current UTC time?",
        "Explain the concept of differential privacy in two sentences.",
    ]

    try:
        for query in queries:
            print(f"\n🔍 Query: {query}")
            print("-" * 70)
            answer = await agent.run(query)
            print(f"\n📤 Answer:\n{answer}")
            print("=" * 70)
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
