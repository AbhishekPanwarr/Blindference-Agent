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

# Load .env automatically if python-dotenv is available.
# Searches from the current working directory up to the filesystem root,
# so it works regardless of where the script is executed from.
try:
    from dotenv import load_dotenv
    import os as _os
    from pathlib import Path as _Path

    _start = _Path(_os.getcwd())
    _loaded = False
    for _dotenv in [".env", ".env.local"]:
        _path = _start / _dotenv
        if _path.exists():
            load_dotenv(str(_path), override=False)
            _loaded = True
            break
        # Walk up the directory tree
        for _parent in _start.parents:
            _path = _parent / _dotenv
            if _path.exists():
                load_dotenv(str(_path), override=False)
                _loaded = True
                break
        if _loaded:
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
