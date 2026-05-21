"""LangChain integration for Blindference.

Provides a :class:`BlindferenceLLM` wrapper that implements LangChain's
``BaseLLM`` interface, routing all inference through the Blindference network.

Install::

    pip install blindference-agent[langchain]

Usage::

    from langchain.llms import BlindferenceLLM

    llm = BlindferenceLLM(
        icl_url="https://icl.blindference.xyz",
        cofhe_rpc="https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY",
        private_key="0x...",
        model="groq:llama-3.3-70b-versatile",
    )

    result = llm.invoke("What is the capital of France?")
    print(result)
"""

from __future__ import annotations

import asyncio
from typing import Any, List, Optional

try:
    from langchain.llms.base import BaseLLM
    from langchain.schema import Generation, LLMResult
except ImportError:
    raise ImportError(
        "langchain is required for BlindferenceLLM. "
        "Install with: pip install blindference-agent[langchain]"
    )

from blindference_agent.core import BlindferenceAgent


class BlindferenceLLM(BaseLLM):
    """LangChain LLM wrapper that runs inference through the Blindference network.

    All prompts are encrypted end-to-end (AES-GCM + CoFHE) before leaving your
    machine. Results are decrypted locally after quorum consensus.
    """

    icl_url: str = "https://icl.blindference.xyz"
    cofhe_rpc: str = ""
    private_key: str = ""
    model: str = "groq:llama-3.3-70b-versatile"
    verifier_count: int = 2
    timeout: float = 300.0
    _agent: BlindferenceAgent | None = None

    def _get_agent(self) -> BlindferenceAgent:
        if self._agent is None:
            self._agent = BlindferenceAgent(
                icl_url=self.icl_url,
                cofhe_rpc=self.cofhe_rpc,
                private_key=self.private_key,
            )
        return self._agent

    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Generate completions for a batch of prompts."""
        agent = self._get_agent()

        async def _run_all():
            results = []
            for prompt in prompts:
                result = await agent.inference(
                    prompt=prompt,
                    model_id=self.model,
                    verifier_count=self.verifier_count,
                    timeout=self.timeout,
                )
                results.append(result.text)
            return results

        texts = asyncio.run(_run_all())
        generations = [
            [Generation(text=text)] for text in texts
        ]
        return LLMResult(generations=generations)

    async def _agenerate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Async generate completions."""
        agent = self._get_agent()
        results = []
        for prompt in prompts:
            result = await agent.inference(
                prompt=prompt,
                model_id=self.model,
                verifier_count=self.verifier_count,
                timeout=self.timeout,
            )
            results.append(result.text)

        generations = [
            [Generation(text=text)] for text in results
        ]
        return LLMResult(generations=generations)

    @property
    def _llm_type(self) -> str:
        return "blindference"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "icl_url": self.icl_url,
            "verifier_count": self.verifier_count,
        }


def _import_check() -> None:
    """Verify langchain is installed."""
    try:
        import langchain  # noqa: F401
    except ImportError:
        raise ImportError(
            "langchain is required. Install with: pip install blindference-agent[langchain]"
        )


__all__ = ["BlindferenceLLM"]
