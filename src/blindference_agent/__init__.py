"""Blindference Agent SDK — build confidential AI agents on the Blindference network.

Environment variables are auto-loaded from ``.env`` (via ``python-dotenv``) when
this package is imported.

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

# Load .env automatically if python-dotenv is available
try:
    from dotenv import load_dotenv
    import os as _os
    _cwd = _os.getcwd()
    for _dotenv in [".env", ".env.local"]:
        _path = _os.path.join(_cwd, _dotenv)
        if _os.path.exists(_path):
            load_dotenv(_path, override=False)
            break
except ImportError:
    pass  # python-dotenv not installed — user must manage env vars manually

from blindference_agent.core import BlindferenceAgent
from blindference_agent.types import InferenceResult, InferenceStatus, InferenceRequest

__all__ = [
    "BlindferenceAgent",
    "InferenceResult",
    "InferenceStatus",
    "InferenceRequest",
]

__version__ = "0.1.0"
