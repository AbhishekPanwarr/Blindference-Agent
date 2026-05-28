"""Autonomous research agent that decomposes queries and synthesizes results.

This example demonstrates an agent that:
  1. Takes a broad research question
  2. Breaks it into focused sub-questions
  3. Submits each sub-question as a confidential inference job
  4. Collects answers in parallel
  5. Synthesizes a coherent final report

The decomposition and synthesis steps run locally (no network cost).
Only the sub-question inferences are sent through the Blindference
encrypted pipeline.

Backends:
  - Python SDK (default)
  - TypeScript SDK via subprocess or REST (swap `submit_query`)
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=False)

from blindference_agent import BlindferenceAgent, InferenceResult

logger = logging.getLogger("research_agent")


# ---------------------------------------------------------------------------
# Query decomposition (local — no network calls)
# ---------------------------------------------------------------------------

RESEARCH_DECOMPOSITION_PROMPT = """<system>
You are a research decomposition engine. Break the user's broad question
into 3-5 focused sub-questions that can be answered independently.
Return ONLY a JSON array of strings, no markdown, no commentary.
</system>

<user>
{question}
</user>

<assistant>"""

# For this demo, we use a hardcoded heuristic decomposition to avoid
# bootstrapping the agent with itself. In production, you'd run the
# decomposition through the same encrypted pipeline (or a smaller local model).

DECOMPOSITION_MAP: dict[str, list[str]] = {
    "Explain the risks and benefits of AI in healthcare.": [
        "What are the primary patient-safety risks of AI diagnostic tools?",
        "How can AI improve early disease detection accuracy?",
        "What privacy concerns arise from AI processing medical records?",
        "Which regulatory frameworks govern AI in clinical settings?",
    ],
    "What are zero-knowledge proofs and how do they apply to blockchain?": [
        "What is the mathematical foundation of zero-knowledge proofs?",
        "How do ZK-rollups improve blockchain scalability?",
        "What are the performance trade-offs of ZK versus optimistic rollups?",
    ],
}


def decompose_question(question: str) -> list[str]:
    """Return sub-questions for a known topic, or a single fallback."""
    for key, subs in DECOMPOSITION_MAP.items():
        if key.lower() in question.lower() or question.lower() in key.lower():
            return subs
    # Fallback: treat the whole question as one sub-question
    return [question]


# ---------------------------------------------------------------------------
# Synthesis (local — no network calls)
# ---------------------------------------------------------------------------

SYNTHESIS_PROMPT = """<system>
You are a research synthesis engine. Combine the following independent
answers into a single coherent report with clear sections.
Cite the sub-question index for each claim.
</system>

{answers_block}

<assistant>
# Research Report: {question}

"""


def build_synthesis_prompt(question: str, answers: list[str]) -> str:
    lines = ["## Sub-question Answers\n"]
    for i, ans in enumerate(answers, 1):
        lines.append(f"### [{i}]\n{ans}\n")
    answers_block = "\n".join(lines)

    return SYNTHESIS_PROMPT.format(
        question=question,
        answers_block=answers_block,
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ResearchAgent:
    """Decompose → parallel infer → synthesize."""

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

    async def submit_query(self, sub_question: str) -> InferenceResult:
        """Submit a single sub-question through the encrypted pipeline."""
        agent = await self._ensure_agent()
        return await agent.inference(
            prompt=sub_question,
            model_id=self.model_id,
            verifier_count=self.verifier_count,
        )

    async def research(self, question: str) -> dict[str, Any]:
        """Full research pipeline: decompose, parallel infer, synthesize."""
        logger.info("Decomposing question: %s", question)
        sub_questions = decompose_question(question)
        logger.info("Generated %d sub-questions", len(sub_questions))

        # Parallel inference
        logger.info("Submitting sub-questions in parallel...")
        tasks = [self.submit_query(q) for q in sub_questions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        answers: list[str] = []
        errors: list[str] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Sub-question %d failed: %s", i + 1, result)
                errors.append(str(result))
                answers.append(f"[Error: {result}]")
            else:
                answers.append(result.text)
                logger.info("Sub-question %d answered (leader=%s...)", i + 1, result.leader_address[:10])

        # Synthesis via one more encrypted inference
        synthesis_prompt = build_synthesis_prompt(question, answers)
        logger.info("Synthesizing final report...")
        synthesis = await self.submit_query(synthesis_prompt)

        return {
            "question": question,
            "sub_questions": sub_questions,
            "answers": answers,
            "errors": errors,
            "report": synthesis.text,
            "leader": synthesis.leader_address,
            "commitment": synthesis.commitment_hash,
        }

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
    print("Autonomous Research Agent — Confidential Parallel Inference")
    print("=" * 70)

    use_mock = os.environ.get("BLF_MOCK", "false").lower() in ("1", "true", "yes")
    if use_mock:
        print("⚠️  MOCK MODE — plaintext submission\n")

    agent = ResearchAgent(mock=use_mock)

    # Example research questions
    questions = [
        "Explain the risks and benefits of AI in healthcare.",
        "What are zero-knowledge proofs and how do they apply to blockchain?",
    ]

    try:
        for question in questions:
            print(f"\n🔬 Research Question: {question}")
            print("-" * 70)

            report = await agent.research(question)

            print(f"\n📊 Sub-questions: {len(report['sub_questions'])}")
            if report['errors']:
                print(f"   ⚠️  Errors: {len(report['errors'])}")

            print(f"\n📄 Synthesized Report:\n")
            print(report['report'][:800] + "..." if len(report['report']) > 800 else report['report'])
            print(f"\n   Leader:     {report['leader'][:10]}...")
            print(f"   Commitment: {report['commitment'][:16]}...")
            print("=" * 70)
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
