"""Blindference Agent SDK — Python Agent Example

This example demonstrates how to build a Python agent that uses the
@abhieren/blindference-agent TypeScript CLI for end-to-end confidential inference.

The SDK handles:
  - CoFHE client initialization
  - AES-256-GCM prompt encryption
  - Fhenix CoFHE key-half encryption
  - On-chain key storage
  - IPFS upload
  - Quorum consensus polling
  - Output decryption

Prerequisites:
    cd Blindference-Agent
    npm install
    npm run build

    # Set environment variables (see .env.example)
    export BLF_PRIVATE_KEY=0x...
    export BLF_PAYMENT_URL=http://127.0.0.1:8001
    export BLF_RPC_URL=https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY

Usage:
    python examples/agent_demo.py "What is quantum computing?"
    python examples/agent_demo.py --model groq:llama-3.3-70b-versatile "Explain FHE"
    python examples/agent_demo.py --balance
    python examples/agent_demo.py --buy-package starter
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("blindference-agent-demo")


def _find_sdk_entrypoint() -> list[str]:
    """Resolve the SDK CLI entry point from common locations."""
    repo_root = Path(__file__).parent.parent.resolve()

    # 1. Local dist build (development)
    local_cli = repo_root / "dist" / "cli.js"
    if local_cli.exists():
        return ["node", str(local_cli)]

    # 2. npx (production / published package)
    return ["npx", "-y", "@abhieren/blindference-agent"]


def _run_sdk_command(*args: str, timeout: float = 300.0) -> str:
    """Execute an SDK CLI command and return stdout."""
    cmd = _find_sdk_entrypoint() + list(args)
    logger.info("Running: %s", " ".join(cmd))

    env = {**os.environ, "NODE_NO_WARNINGS": "1"}
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )

    if result.returncode != 0:
        logger.error("SDK stderr:\n%s", result.stderr)
        raise RuntimeError(
            f"SDK command failed (exit {result.returncode}): {result.stderr[:500]}"
        )

    return result.stdout


def parse_inference_output(stdout: str) -> dict[str, Any]:
    """Parse the CLI inference output into a structured dict."""
    lines = stdout.strip().splitlines()
    result: dict[str, Any] = {
        "jobId": None,
        "taskId": None,
        "status": "UNKNOWN",
        "output": None,
    }
    output_lines: list[str] = []
    in_output = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Job ID:"):
            result["jobId"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Task ID:"):
            result["taskId"] = stripped.split(":", 1)[1].strip()
        elif "Inference completed" in stripped:
            result["status"] = "COMPLETED"
        elif "Inference FAILED" in stripped or "Inference REJECTED" in stripped:
            result["status"] = stripped.split()[1]
        elif stripped.startswith("Output:"):
            in_output = True
        elif in_output and stripped:
            output_lines.append(stripped)

    result["output"] = "\n".join(output_lines).strip() if output_lines else None
    return result


def parse_balance_output(stdout: str) -> dict[str, str]:
    """Parse the CLI balance output."""
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


class BlindferenceAgent:
    """Python wrapper around the @abhieren/blindference-agent CLI.

    This class provides a clean Python interface for:
      - Confidential inference (encrypt → submit → poll → decrypt)
      - Credit balance checks
      - Package purchases

    All heavy lifting (CoFHE encryption, blockchain interaction, IPFS)
    is delegated to the TypeScript SDK via subprocess.
    """

    def __init__(self, model: str = "groq:llama-3.3-70b-versatile", currency: str = "cUSDC"):
        self.model = model
        self.currency = currency

    def infer(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Submit a confidential inference job and return the result."""
        model = kwargs.get("model", self.model)
        currency = kwargs.get("currency", self.currency)
        insurance = "--insurance" if kwargs.get("insurance") else ""

        args = [
            "infer",
            "--prompt", prompt,
            "--model", model,
            "--currency", currency,
        ]
        if insurance:
            args.append(insurance)

        stdout = _run_sdk_command(*args, timeout=300.0)
        return parse_inference_output(stdout)

    def balance(self) -> dict[str, str]:
        """Check credit balances for the configured wallet."""
        stdout = _run_sdk_command("balance", timeout=30.0)
        return parse_balance_output(stdout)

    def buy_package(self, package_id: str) -> dict[str, Any]:
        """Purchase a credit package (starter, pro, enterprise)."""
        stdout = _run_sdk_command("buy-package", "--id", package_id, timeout=60.0)
        # Simple parse — look for tx hash and new balances
        result: dict[str, Any] = {"packageId": package_id, "txHash": None}
        for line in stdout.strip().splitlines():
            stripped = line.strip()
            if stripped.startswith("Tx Hash:"):
                result["txHash"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("New cUSDC:"):
                result["newCusdc"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("New BLIND:"):
                result["newBlind"] = stripped.split(":", 1)[1].strip()
        return result


def demo_inference(prompt: str, model: str) -> None:
    """Run a single inference demo."""
    print("=" * 70)
    print(" Blindference Agent SDK — Python Demo")
    print("=" * 70)

    agent = BlindferenceAgent(model=model)

    # 1. Check balance
    print("\n[1/4] Checking credit balances...")
    balances = agent.balance()
    print(f"   Address: {balances.get('address', 'N/A')}")
    print(f"   cUSDC:   {balances.get('cusdc', 'N/A')}")
    print(f"   BLIND:   {balances.get('blind', 'N/A')}")

    # 2. Submit inference
    print(f"\n[2/4] Submitting confidential inference...")
    print(f"   Prompt: {prompt}")
    print(f"   Model:  {model}")
    print("   (This will encrypt the prompt, store keys on-chain, and run quorum consensus)")

    result = agent.infer(prompt, model=model)

    # 3. Display result
    print(f"\n[3/4] Result received!")
    print(f"   Status:  {result['status']}")
    print(f"   Job ID:  {result['jobId']}")
    print(f"   Task ID: {result['taskId']}")

    if result["output"]:
        print(f"\n   Output:\n   {result['output']}")
    else:
        print("   (No output returned — job may have failed)")

    print("\n[4/4] Done.")
    print("=" * 70)


def demo_batch_inference(prompts: list[str], model: str) -> None:
    """Run multiple inference jobs sequentially."""
    print("=" * 70)
    print(" Blindference Agent SDK — Batch Inference Demo")
    print("=" * 70)

    agent = BlindferenceAgent(model=model)
    balances = agent.balance()
    print(f"\nWallet: {balances.get('address', 'N/A')}")
    print(f"cUSDC:  {balances.get('cusdc', 'N/A')}\n")

    for i, prompt in enumerate(prompts, 1):
        print(f"[{i}/{len(prompts)}] Prompt: {prompt}")
        result = agent.infer(prompt, model=model)
        print(f"       Status: {result['status']} | Job: {result['jobId']}")
        if result["output"]:
            # Truncate long outputs for display
            output = result["output"]
            display = output[:200] + "..." if len(output) > 200 else output
            print(f"       Output: {display}")
        print()

    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Blindference Agent SDK — Python Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "What is quantum computing?"
  %(prog)s --model groq:llama-3.3-70b-versatile "Explain homomorphic encryption"
  %(prog)s --balance
  %(prog)s --buy-package starter
  %(prog)s --batch "Q1" "Q2" "Q3"
        """,
    )
    parser.add_argument("prompt", nargs="?", help="Prompt for inference")
    parser.add_argument("--model", default="groq:llama-3.3-70b-versatile", help="Model ID")
    parser.add_argument("--currency", default="cUSDC", help="Payment currency")
    parser.add_argument("--insurance", action="store_true", help="Enable insurance")
    parser.add_argument("--balance", action="store_true", help="Check balance only")
    parser.add_argument("--buy-package", metavar="ID", help="Purchase credit package (starter/pro/enterprise)")
    parser.add_argument("--batch", nargs="+", help="Run batch inference with multiple prompts")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    agent = BlindferenceAgent(model=args.model, currency=args.currency)

    if args.balance:
        balances = agent.balance()
        if args.json:
            print(json.dumps(balances, indent=2))
        else:
            print(f"Address: {balances.get('address', 'N/A')}")
            print(f"cUSDC:   {balances.get('cusdc', 'N/A')}")
            print(f"BLIND:   {balances.get('blind', 'N/A')}")
        return

    if args.buy_package:
        result = agent.buy_package(args.buy_package)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Package:    {result['packageId']}")
            print(f"Tx Hash:    {result.get('txHash', 'N/A')}")
            print(f"New cUSDC:  {result.get('newCusdc', 'N/A')}")
            print(f"New BLIND:  {result.get('newBlind', 'N/A')}")
        return

    if args.batch:
        demo_batch_inference(args.batch, args.model)
        return

    if not args.prompt:
        parser.print_help()
        sys.exit(1)

    if args.json:
        result = agent.infer(args.prompt, model=args.model, insurance=args.insurance)
        print(json.dumps(result, indent=2))
    else:
        demo_inference(args.prompt, args.model)


if __name__ == "__main__":
    main()
