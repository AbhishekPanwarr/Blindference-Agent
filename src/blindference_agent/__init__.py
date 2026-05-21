"""Blindference Agent SDK — build confidential AI agents on the Blindference network.

Quickstart::

    import asyncio
    from blindference_agent import BlindferenceAgent

    async def main():
        agent = BlindferenceAgent(
            icl_url="https://icl.blindference.xyz",
            cofhe_rpc="https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY",
            private_key="0x...",
        )
        result = await agent.inference(
            "Explain quantum computing",
            model_id="groq:llama-3.3-70b-versatile",
        )
        print(result.text)

    asyncio.run(main())
"""

from blindference_agent.core import BlindferenceAgent
from blindference_agent.types import InferenceResult, InferenceStatus, InferenceRequest

__all__ = [
    "BlindferenceAgent",
    "InferenceResult",
    "InferenceStatus",
    "InferenceRequest",
]

__version__ = "0.1.0"
