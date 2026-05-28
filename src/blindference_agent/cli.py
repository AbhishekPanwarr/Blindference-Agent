"""CLI for the Blindference Agent SDK."""

from __future__ import annotations

import asyncio
import os

import click

from blindference_agent.core import BlindferenceAgent


def _load_env() -> None:
    """Load .env file if present."""
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
    except ImportError:
        pass


_load_env()


@click.group()
@click.version_option(version="0.1.0", prog_name="blindference-agent")
def main() -> None:
    """Blindference Agent — build confidential AI agents."""


@main.command()
@click.option("--dir", default=".", help="Directory to scaffold the agent project")
def init(dir: str) -> None:
    """Scaffold a new agent project."""
    import os as _os
    target = _os.path.abspath(dir)
    _os.makedirs(target, exist_ok=True)

    created_any = False

    # Write .env from package template
    env_path = _os.path.join(target, ".env")
    if not _os.path.exists(env_path):
        # Copy .env.example shipped with the package
        pkg_dir = _os.path.dirname(_os.path.abspath(__file__))
        example = _os.path.join(pkg_dir, "..", "..", "..", ".env.example")
        if _os.path.exists(example):
            import shutil
            shutil.copy(example, env_path)
        else:
            # Fallback: write minimal template
            with open(env_path, "w") as f:
                f.write(
                    "# Blindference Agent SDK — Environment Variables\n"
                    "# Copy this file to .env and fill in your values.\n"
                    "# NEVER commit this file to git.\n\n"
                    "# REQUIRED — Arbitrum Sepolia RPC (get key at https://www.alchemy.com/)\n"
                    "BLF_COFHE_RPC=https://arb-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY_HERE\n\n"
                    "# REQUIRED — Wallet private key (32-byte hex, 0x-prefixed, fresh wallet only)\n"
                    "BLF_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE\n\n"
                    "# REQUIRED — Payment Service URL (where job payments are processed)\n"
                    "BLF_PAYMENT_URL=https://payment.blindference.xyz\n\n"
                    "# ICL endpoint (defaults to https://icl.blindference.xyz)\n"
                    "# BLF_ICL_URL=https://icl.blindference.xyz\n\n"
                    "# Pinata JWT for IPFS uploads (get at https://pinata.cloud/keys)\n"
                    "# BLF_PINATA_JWT=YOUR_PINATA_JWT_HERE\n"
                )
        click.echo(f"  Created {env_path}")
        created_any = True
    else:
        click.echo(f"  Already exists: {env_path}")

    # Write agent.py template
    agent_path = _os.path.join(target, "agent.py")
    if not _os.path.exists(agent_path):
        with open(agent_path, "w") as f:
            f.write(
                "\"\"\"My confidential agent.\"\"\"\n"
                "import asyncio\n"
                "from blindference_agent import BlindferenceAgent\n\n"
                "async def main():\n"
                "    agent = BlindferenceAgent(\n"
                "        icl_url=os.environ['BLF_ICL_URL'],\n"
                "        cofhe_rpc=os.environ['BLF_COFHE_RPC'],\n"
                "        private_key=os.environ['BLF_PRIVATE_KEY'],\n"
                "    )\n"
                "    result = await agent.inference(\n"
                "        prompt='Explain quantum computing',\n"
                "        model_id='groq:llama-3.3-70b-versatile',\n"
                "    )\n"
                "    print(result.text)\n\n"
                "if __name__ == '__main__':\n"
                "    asyncio.run(main())\n"
            )
        click.echo(f"  Created {agent_path}")
        created_any = True
    else:
        click.echo(f"  Already exists: {agent_path}")

    # Write requirements.txt
    req_path = _os.path.join(target, "requirements.txt")
    if not _os.path.exists(req_path):
        with open(req_path, "w") as f:
            f.write("blindference-agent\n")
        click.echo(f"  Created {req_path}")
        created_any = True
    else:
        click.echo(f"  Already exists: {req_path}")

    if created_any:
        click.echo(f"\nAgent project initialized in {target}")
    else:
        click.echo(f"\nAgent project already exists in {target}")
    click.echo("Next steps:")
    click.echo("  1. Edit .env with your API keys and private key")
    click.echo("  2. Run: blindference-agent test")
    click.echo("  3. Run: python agent.py")


@main.command()
def test() -> None:
    """Test connectivity to ICL and CoFHE bridge."""
    async def _test() -> None:
        icl_url = os.environ.get("BLF_ICL_URL", "https://icl.blindference.xyz")
        cofhe_rpc = os.environ.get("BLF_COFHE_RPC", "")
        private_key = os.environ.get("BLF_PRIVATE_KEY", "")

        click.echo("Testing ICL connectivity ...")
        from blindference_agent.icl_client import ICLClient
        icl = ICLClient(icl_url)
        try:
            # Try a simple GET to root or health endpoint
            await icl._get("/health")
            click.echo("  ✓ ICL reachable")
        except Exception as e:
            click.echo(f"  ✗ ICL error: {e}")
        finally:
            await icl.close()

        if not cofhe_rpc or not private_key:
            click.echo("Skipping CoFHE test (BLF_COFHE_RPC or BLF_PRIVATE_KEY not set)")
            return

        click.echo("Testing CoFHE bridge ...")
        from blindference_agent.cofhe_bridge import CoFHEBridge
        bridge = CoFHEBridge(
            rpc_url=cofhe_rpc,
            private_key=private_key,
        )
        try:
            await bridge.start()
            click.echo("  ✓ CoFHE bridge started")
            # Try a simple encrypt
            result = await bridge.encrypt_uint128(42)
            click.echo(f"  ✓ CoFHE encrypt test: ctHash={result.get('ctHash', 'N/A')[:16]}...")
        except Exception as e:
            click.echo(f"  ✗ CoFHE error: {e}")
        finally:
            await bridge.stop()

    asyncio.run(_test())


@main.command()
@click.argument("script_path")
def run(script_path: str) -> None:
    """Run an agent script."""
    import runpy
    runpy.run_path(script_path, run_name="__main__")


if __name__ == "__main__":
    main()
