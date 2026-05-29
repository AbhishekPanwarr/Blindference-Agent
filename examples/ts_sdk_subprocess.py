"""Call the TypeScript SDK CLI from Python via subprocess.

This example demonstrates how a Python agent can offload CoFHE encryption
and inference to the Node.js/TypeScript SDK without implementing the
encryption pipeline in Python.

Prerequisites:
    npm install -g @abhieren/blindference-agent
    # or use npx directly (no global install needed)

Environment:
    BLINDFERENCE_PRIVATE_KEY  (or PRIVATE_KEY)
    Set via .env or export before running.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

# The SDK auto-loads .env — ensure it's available before importing anything
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=False)

logger = logging.getLogger("ts_sdk_subprocess")


def _find_npx() -> str:
    """Return the path to npx or 'npx' if available on PATH."""
    # Prefer local js/node_modules/.bin/npx if the repo layout is intact
    repo_root = Path(__file__).parent.parent
    local_npx = repo_root / "js" / "node_modules" / ".bin" / "npx"
    if local_npx.exists():
        return str(local_npx)
    return "npx"


def _run_ts_cli(*args: str, capture: bool = True, timeout: float = 300.0) -> str:
    """Execute the blindference-agent CLI via npx and return stdout."""
    npx = _find_npx()
    cmd = [npx, "-y", "@abhieren/blindference-agent"] + list(args)

    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        timeout=timeout,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )

    if result.returncode != 0:
        logger.error("CLI stderr:\n%s", result.stderr)
        raise RuntimeError(
            f"blindference-agent CLI failed (exit {result.returncode}): {result.stderr[:500]}"
        )

    return result.stdout


async def run_inference(prompt: str, model_id: str = "groq:llama-3.3-70b-versatile") -> dict:
    """Submit a single inference via the TS CLI and parse the result."""
    stdout = await asyncio.to_thread(
        _run_ts_cli,
        "infer",
        "--prompt", prompt,
        "--model", model_id,
        "--currency", "cUSDC",
        capture=True,
        timeout=300.0,
    )

    # The CLI prints structured output with lines like:
    #   ✅ Inference completed
    #      Job ID:    abc-123
    #      Output:
    #      <result text>
    # We attempt a simple heuristic parse.
    lines = stdout.strip().splitlines()
    output_lines: list[str] = []
    result = {"jobId": None, "taskId": None, "output": None, "status": "UNKNOWN"}

    in_output = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Job ID:"):
            result["jobId"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Task ID:"):
            result["taskId"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Output:"):
            in_output = True
        elif in_output:
            output_lines.append(stripped)
        elif "completed" in stripped.lower():
            result["status"] = "COMPLETED"
        elif "failed" in stripped.lower():
            result["status"] = "FAILED"

    result["output"] = "\n".join(output_lines).strip() if output_lines else None
    return result


async def get_balance() -> dict:
    """Fetch credit balances via the TS CLI balance command."""
    stdout = await asyncio.to_thread(
        _run_ts_cli,
        "balance",
        capture=True,
        timeout=30.0,
    )

    balances: dict[str, str] = {}
    for line in stdout.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith("cUSDC:"):
            balances["cusdc"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("BLIND:"):
            balances["blind"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Address:"):
            balances["address"] = stripped.split(":", 1)[1].strip()

    return balances


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 70)
    print("Python Agent → TypeScript SDK (subprocess) Demo")
    print("=" * 70)

    # 1. Check balance
    print("\n[1/3] Checking credit balances via TS CLI...")
    balances = await get_balance()
    print(f"   Address: {balances.get('address', 'N/A')}")
    print(f"   cUSDC:   {balances.get('cusdc', 'N/A')}")
    print(f"   BLIND:   {balances.get('blind', 'N/A')}")

    # 2. Submit inference
    print("\n[2/3] Submitting confidential inference via TS CLI...")
    prompt = "Explain zero-knowledge proofs in three sentences."
    print(f"   Prompt: {prompt}")

    result = await run_inference(prompt)
    print(f"\n   Job ID:  {result.get('jobId')}")
    print(f"   Status:  {result.get('status')}")

    if result.get("output"):
        print(f"\n   Output:\n   {result['output']}")
    else:
        print("   (No output — job may still be processing or failed)")

    print("\n[3/3] Done.")


if __name__ == "__main__":
    asyncio.run(main())
