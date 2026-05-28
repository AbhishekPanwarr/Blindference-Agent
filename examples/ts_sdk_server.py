"""Control the TypeScript SDK REST server from Python.

This example starts the blindference-agent local server as a background
subprocess and then submits inference requests via HTTP (aiohttp).

This pattern is ideal for:
  - Long-running agents that need a persistent CoFHE session
  - Microservices that want to delegate confidential inference
  - Load-balanced pools where the TS server runs as a sidecar

Prerequisites:
    npm install -g @blindference/agent-sdk
    # or reference the local js/ directory directly

Environment:
    BLINDFERENCE_PRIVATE_KEY  (or PRIVATE_KEY)
    BLF_ICL_URL               (optional, used by the TS server)
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import aiohttp
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=False)

logger = logging.getLogger("ts_sdk_server")

# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------

class BlindferenceServer:
    """Manages the blindference-agent TypeScript REST server subprocess."""

    def __init__(
        self,
        port: int = 4000,
        payment_service_url: str = "http://localhost:8001",
        rpc_url: str = "https://sepolia-rollup.arbitrum.io/rpc",
        server_script: str | None = None,
    ) -> None:
        self.port = port
        self.base_url = f"http://localhost:{port}"
        self.payment_service_url = payment_service_url
        self.rpc_url = rpc_url
        self._proc: asyncio.subprocess.Process | None = None
        self._server_script = server_script

    def _find_server_script(self) -> str:
        """Resolve the TS server entry point."""
        if self._server_script:
            return self._server_script

        repo_root = Path(__file__).parent.parent
        candidates = [
            repo_root / "js" / "dist" / "server.js",
            repo_root / "js" / "dist" / "cli.js",
            repo_root / "node_modules" / ".bin" / "blindference-agent",
        ]
        for p in candidates:
            if p.exists():
                return str(p)

        # Fallback to npx
        return "npx"

    async def start(self) -> None:
        """Start the server subprocess and wait for health."""
        script = self._find_server_script()

        if script.endswith(".js"):
            cmd = ["node", script, "start", "--port", str(self.port)]
        else:
            cmd = [
                "npx", "-y", "@blindference/agent-sdk",
                "start",
                "--port", str(self.port),
                "--payment-service", self.payment_service_url,
                "--rpc-url", self.rpc_url,
            ]

        logger.info("Starting TS server: %s", " ".join(cmd))
        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "NODE_NO_WARNINGS": "1"},
        )

        # Wait for health endpoint
        for attempt in range(30):
            await asyncio.sleep(0.5)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.base_url}/health", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            logger.info("TS server ready (agent=%s)", data.get("agent", "unknown"))
                            return
            except Exception:
                pass

        raise RuntimeError("TS server failed to start within 15 seconds")

    async def stop(self) -> None:
        """Gracefully terminate the server."""
        if self._proc is None:
            return
        self._proc.terminate()
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            self._proc.kill()
        self._proc = None
        logger.info("TS server stopped")

    async def __aenter__(self) -> BlindferenceServer:
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop()


# ---------------------------------------------------------------------------
# HTTP client helpers
# ---------------------------------------------------------------------------

async def infer_via_server(
    server: BlindferenceServer,
    prompt: str,
    model_id: str = "groq:llama-3.3-70b-versatile",
    currency: str = "cUSDC",
) -> dict[str, Any]:
    """POST /infer and return the parsed JSON response."""
    async with aiohttp.ClientSession() as session:
        payload = {
            "prompt": prompt,
            "modelId": model_id,
            "currency": currency,
        }
        async with session.post(
            f"{server.base_url}/infer",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300),
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Server returned {resp.status}: {text[:500]}")
            return await resp.json()


async def get_server_balance(server: BlindferenceServer) -> dict[str, Any]:
    """GET /balance and return the parsed JSON response."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{server.base_url}/balance",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Server returned {resp.status}: {text[:500]}")
            return await resp.json()


async def get_job_status(server: BlindferenceServer, job_id: str) -> dict[str, Any]:
    """GET /status/:jobId and return the parsed JSON response."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{server.base_url}/status/{job_id}",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Server returned {resp.status}: {text[:500]}")
            return await resp.json()


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
    print("Python Agent → TypeScript SDK REST Server Demo")
    print("=" * 70)

    async with BlindferenceServer(port=4000) as server:
        # 1. Check balance
        print("\n[1/3] Checking balances via REST server...")
        balances = await get_server_balance(server)
        print(f"   cUSDC: {balances.get('balance_cusdc', 'N/A')}")
        print(f"   BLIND: {balances.get('balance_blind', 'N/A')}")

        # 2. Submit inference
        print("\n[2/3] Submitting inference via REST server...")
        prompt = "Summarize the concept of homomorphic encryption in two paragraphs."
        print(f"   Prompt: {prompt}")

        result = await infer_via_server(server, prompt)
        print(f"\n   Job ID:  {result.get('jobId')}")
        print(f"   Status:  {result.get('status')}")

        if result.get("output"):
            print(f"\n   Output:\n   {result['output']}")
        else:
            print("   (No output returned)")

        # 3. Optional: poll status
        print("\n[3/3] Polling job status...")
        job_id = result.get("jobId")
        if job_id:
            status = await get_job_status(server, job_id)
            print(f"   Current server-side status: {status.get('status', 'unknown')}")

        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
