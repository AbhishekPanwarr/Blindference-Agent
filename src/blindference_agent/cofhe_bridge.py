"""CoFHE bridge — spawns the TypeScript bridge subprocess for on-chain
encryption, decryption, and key storage."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("blindference-agent.cofhe")


class CoFHEBridge:
    """Spawn and communicate with the @cofhe/sdk/node TypeScript bridge.

    The bridge uses JSON messages over stdin/stdout to perform:
        - ``encrypt_uint128(value)`` → CoFHE ciphertext handle
        - ``decrypt_for_view(ctHash, permit)`` → decrypted value
        - ``store_key(task_id, encrypted_high, encrypted_low, allowed_nodes)`` → tx hash
    """

    def __init__(
        self,
        rpc_url: str,
        chain_id: int = 421614,
        private_key: str | None = None,
        bridge_script_path: str | None = None,
    ) -> None:
        self.rpc = rpc_url
        self.chain_id = chain_id
        self.private_key = private_key or ""
        self._proc: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()

        # Discover bridge script — shipped with the package or user-provided
        if bridge_script_path:
            self._script = bridge_script_path
        else:
            # Look in package data, then in node_modules, then cwd
            candidates = [
                Path(__file__).parent / "cofhe_bridge.mjs",
                Path(__file__).parent.parent.parent / "node_modules" / "@cofhe" / "sdk" / "node" / "bridge.mjs",
                Path.cwd() / "cofhe_bridge.mjs",
            ]
            self._script = next((str(p) for p in candidates if p.exists()), "")

        if not self._script:
            raise RuntimeError(
                "CoFHE bridge script not found. Set BLF_COFHE_BRIDGE_PATH or "
                "install @cofhe/sdk and place cofhe_bridge.mjs next to your script."
            )

    async def start(self) -> None:
        """Start the bridge subprocess."""
        if self._proc is not None and self._proc.returncode is None:
            return  # Already running

        # Create a temporary localStorage file for permit persistence
        ls_path = Path(tempfile.gettempdir()) / "blindference-agent-localstorage.json"
        env = {
            **os.environ,
            "COFHE_RPC": self.rpc,
            "COFHE_CHAIN_ID": str(self.chain_id),
            "COFHE_PRIVATE_KEY": self.private_key,
            "COFHE_LOCAL_STORAGE_PATH": str(ls_path),
        }

        logger.info("Starting CoFHE bridge: %s", self._script)
        self._proc = await asyncio.create_subprocess_exec(
            "node", self._script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # Wait for ready signal
        line = await self._readline()
        ready = json.loads(line)
        if ready.get("status") != "ready":
            raise RuntimeError(f"CoFHE bridge failed to start: {ready}")
        logger.info("CoFHE bridge ready (wallet=%s)", ready.get("address", "unknown"))

    async def stop(self) -> None:
        """Terminate the bridge subprocess."""
        if self._proc is None:
            return
        try:
            self._proc.terminate()
            await asyncio.wait_for(self._proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            self._proc.kill()
        self._proc = None

    # ------------------------------------------------------------------
    # Bridge actions
    # ------------------------------------------------------------------

    async def encrypt_uint128(self, value: int) -> dict[str, Any]:
        """CoFHE-encrypt a uint128 value.

        Returns a dict with ``ctHash`` (string) and other metadata.
        """
        return await self._send({"action": "encrypt_uint128", "value": value})

    async def decrypt_for_view(self, ct_hash: int | str, permit: dict[str, Any] | None = None) -> int:
        """Decrypt a CoFHE ciphertext handle for view (with permit if needed).

        Returns the decrypted integer value.
        """
        payload: dict[str, Any] = {"action": "decrypt_for_view", "ctHash": int(ct_hash)}
        if permit:
            payload["permit"] = permit
        result = await self._send(payload)
        return int(result.get("value", 0))

    async def store_key(
        self,
        task_id: str,
        encrypted_high: dict[str, Any],
        encrypted_low: dict[str, Any],
        allowed_nodes: list[str],
        contract_address: str | None = None,
    ) -> str:
        """Store CoFHE-encrypted AES key halves on-chain via PromptKeyStore.

        Returns the transaction hash.
        """
        payload: dict[str, Any] = {
            "action": "store_prompt_key",
            "taskId": task_id,
            "encryptedHighInput": encrypted_high,
            "encryptedLowInput": encrypted_low,
            "allowedNodes": allowed_nodes,
        }
        if contract_address:
            payload["contractAddress"] = contract_address
        result = await self._send(payload)
        return result.get("txHash", "")

    # ------------------------------------------------------------------
    # Low-level I/O
    # ------------------------------------------------------------------

    async def _send(self, msg: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            if self._proc is None or self._proc.returncode is not None:
                raise RuntimeError("CoFHE bridge is not running. Call start() first.")

            line = json.dumps(msg) + "\n"
            self._proc.stdin.write(line.encode("utf-8"))
            await self._proc.stdin.drain()

            response_line = await self._readline()
            response = json.loads(response_line)

            if response.get("error"):
                raise RuntimeError(f"CoFHE bridge error: {response['error']}")
            return response

    async def _readline(self) -> str:
        if self._proc is None or self._proc.stdout is None:
            raise RuntimeError("CoFHE bridge stdout not available")
        line = await self._proc.stdout.readline()
        if not line:
            raise RuntimeError("CoFHE bridge closed stdout unexpectedly")
        return line.decode("utf-8").strip()

    async def __aenter__(self) -> CoFHEBridge:
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop()
