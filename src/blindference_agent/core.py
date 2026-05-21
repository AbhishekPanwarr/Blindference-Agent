"""Core Blindference Agent — high-level interface for confidential inference."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from typing import Any, AsyncIterator

from blindference_agent.cofhe_bridge import CoFHEBridge
from blindference_agent.encryptor import (
    CoFHEKeyHandles,
    EncryptedPayload,
    decrypt_output,
    encrypt_key_via_bridge,
    encrypt_prompt,
    merge_key,
    pack_payload,
    split_key,
)
from blindference_agent.icl_client import ICLClient
from blindference_agent.types import (
    InferenceRequest,
    InferenceResult,
    InferenceStatus,
    QuorumPreview,
)

logger = logging.getLogger("blindference-agent")


def _generate_task_id(prompt: str, model_id: str) -> str:
    """Deterministic keccak-256 task ID from ``(prompt, model_id)``."""
    payload = f"{model_id}:{prompt}".encode("utf-8")
    return "0x" + hashlib.sha256(payload).hexdigest()


class BlindferenceAgent:
    """High-level agent for submitting confidential inference requests
    and retrieving decrypted results.

    Usage::

        agent = BlindferenceAgent(
            icl_url="https://icl.blindference.xyz",
            cofhe_rpc="https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY",
            private_key="0x...",
        )

        result = await agent.inference("What is 2+2?", "groq:llama-3.3-70b-versatile")
        print(result.text)
    """

    def __init__(
        self,
        icl_url: str,
        cofhe_rpc: str,
        private_key: str,
        chain_id: int = 421614,
        cofhe_bridge_path: str | None = None,
    ) -> None:
        self.icl = ICLClient(icl_url)
        self.cofhe = CoFHEBridge(
            rpc_url=cofhe_rpc,
            chain_id=chain_id,
            private_key=private_key,
            bridge_script_path=cofhe_bridge_path,
        )
        self._wallet_address = ""

    async def _ensure_wallet(self) -> str:
        """Start the bridge and retrieve the wallet address."""
        if self._wallet_address:
            return self._wallet_address
        await self.cofhe.start()
        # The bridge prints the address in its ready message; we store it here
        # For now, derive from private key (simplified)
        # In production, the bridge should expose a "get_address" action
        self._wallet_address = "0x" + os.urandom(20).hex()  # Placeholder
        return self._wallet_address

    # ------------------------------------------------------------------
    # One-shot inference
    # ------------------------------------------------------------------

    async def inference(
        self,
        prompt: str,
        model_id: str,
        verifier_count: int = 2,
        min_tier: int = 0,
        poll_interval: float = 3.0,
        timeout: float = 300.0,
    ) -> InferenceResult:
        """Submit a confidential inference request and block until the result
        is decrypted.

        This is the simplest API — it handles encryption, quorum preview,
        submission, polling, and decryption in one call.

        Args:
            prompt: The plaintext prompt.
            model_id: Model ID, e.g. ``"groq:llama-3.3-70b-versatile"``.
            verifier_count: Number of verifiers in the quorum (default 2).
            min_tier: Minimum node tier for quorum selection.
            poll_interval: Seconds between status polls.
            timeout: Maximum seconds to wait for completion.

        Returns:
            :class:`InferenceResult` with decrypted text and all metadata.

        Raises:
            TimeoutError: if the job does not reach ``ACCEPTED`` within *timeout*.
            RuntimeError: on CoFHE or ICL errors.
        """
        request = await self.submit(prompt, model_id, verifier_count, min_tier)

        # Poll until done or timeout
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            status = await self.icl.get_status(request.request_id)
            if status.status == "ACCEPTED":
                return await self._decrypt_result(status, request.model_id)
            if status.status in ("REJECTED", "DISPUTED"):
                raise RuntimeError(f"Inference {request.request_id} failed with status {status.status}")
            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Inference {request.request_id} did not complete within {timeout}s")

    # ------------------------------------------------------------------
    # Streaming status
    # ------------------------------------------------------------------

    async def stream_status(
        self,
        request_id: str,
        interval: float = 3.0,
    ) -> AsyncIterator[InferenceStatus]:
        """Yield live :class:`InferenceStatus` objects until the job
        reaches a terminal state.
        """
        async for status in self.icl.stream_status(request_id, interval):
            yield status

    # ------------------------------------------------------------------
    # Submit (encryption + upload + storeKey + ICL submit)
    # ------------------------------------------------------------------

    async def submit(
        self,
        prompt: str,
        model_id: str,
        verifier_count: int = 2,
        min_tier: int = 0,
    ) -> InferenceRequest:
        """Encrypt a prompt, get a quorum, store the key on-chain, and submit
        to the ICL.

        Returns immediately after submission — use :meth:`stream_status` or
        :meth:`inference` to track progress.
        """
        # 1 — Start CoFHE bridge
        await self.cofhe.start()
        wallet_address = await self._ensure_wallet()

        # 2 — Encrypt prompt with AES-GCM
        logger.info("Encrypting prompt ...")
        payload = encrypt_prompt(prompt)

        # 3 — Split AES key and CoFHE-encrypt halves
        high, low = split_key(payload.aes_key)
        logger.info("CoFHE-encrypting key halves ...")
        cofhe_keys = await encrypt_key_via_bridge(self.cofhe, high, low)

        # 4 — Upload encrypted blob to IPFS
        packed = pack_payload(payload)
        logger.info("Uploading encrypted prompt to IPFS ...")
        prompt_cid = await self.icl.upload_blob(packed)
        logger.info("Prompt CID: %s", prompt_cid)

        # 5 — Get quorum preview
        logger.info("Fetching quorum preview ...")
        quorum = await self.icl.quorum_preview(
            model_id=model_id,
            min_tier=min_tier,
            verifier_count=verifier_count,
        )
        allowed_nodes = [quorum.leader.address] + [v.address for v in quorum.verifiers]

        # 6 — Store key on-chain (requires wallet tx)
        task_id = _generate_task_id(prompt, model_id)
        logger.info("Storing key on-chain (task_id=%s) ...", task_id)
        store_tx = await self.cofhe.store_key(
            task_id=task_id,
            encrypted_high={"ctHash": int(cofhe_keys.high)},
            encrypted_low={"ctHash": int(cofhe_keys.low)},
            allowed_nodes=allowed_nodes,
        )
        logger.info("StoreKey tx: %s", store_tx)

        # 7 — Submit to ICL
        logger.info("Submitting to ICL ...")
        request = await self.icl.submit_text(
            developer_address=wallet_address,
            task_id=task_id,
            model_id=model_id,
            prompt_cid=prompt_cid,
            encrypted_prompt_key_high=cofhe_keys.high,
            encrypted_prompt_key_low=cofhe_keys.low,
            leader_address=quorum.leader.address,
            verifier_addresses=[v.address for v in quorum.verifiers],
            min_tier=min_tier,
            verifier_count=verifier_count,
            metadata={
                "model": model_id,
                "provider": model_id.split(":")[0],
                "prompt_key_store_tx": store_tx,
            },
        )
        logger.info("Request submitted: %s", request.request_id)
        return request

    # ------------------------------------------------------------------
    # Decrypt result
    # ------------------------------------------------------------------

    async def _decrypt_result(self, status: InferenceStatus, model_id: str) -> InferenceResult:
        """Download the encrypted output blob, decrypt the CoFHE output key,
        and AES-decrypt the result.
        """
        if not status.output_cid or not status.encrypted_output_key_high or not status.encrypted_output_key_low:
            raise RuntimeError("Result is missing output CID or encrypted keys")

        # 1 — Decrypt output key halves via CoFHE
        logger.info("Decrypting output key via CoFHE ...")
        high_val = await self.cofhe.decrypt_for_view(status.encrypted_output_key_high)
        low_val = await self.cofhe.decrypt_for_view(status.encrypted_output_key_low)
        output_key = merge_key(
            high_val.to_bytes(16, "big"),
            low_val.to_bytes(16, "big"),
        )

        # 2 — Download output blob from IPFS
        logger.info("Downloading output from IPFS (CID=%s) ...", status.output_cid)
        # Simple HTTP gateway download
        import aiohttp
        blob = b""
        gateways = [
            f"https://gateway.pinata.cloud/ipfs/{status.output_cid}",
            f"https://cloudflare-ipfs.com/ipfs/{status.output_cid}",
        ]
        for gw in gateways:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(gw, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status == 200:
                            blob = await resp.read()
                            break
            except Exception:
                continue
        if not blob:
            raise RuntimeError(f"Failed to download output from IPFS: {status.output_cid}")

        # 3 — AES-decrypt
        logger.info("AES-decrypting result ...")
        plaintext = decrypt_output(blob, output_key)

        # 4 — Fetch final metadata from ICL status
        raw = await self.icl._get(f"/v1/inference/{status.request_id}")
        quorum = raw.get("quorum", {})

        return InferenceResult(
            request_id=status.request_id,
            task_id=raw.get("task_id", status.request_id),
            text=plaintext,
            model_id=model_id,
            output_cid=status.output_cid,
            leader_address=quorum.get("leader_address", ""),
            verifier_addresses=quorum.get("verifier_addresses", []),
            commitment_hash=status.commitment_hash or "",
            result_commit_tx=status.result_commit_tx,
            timestamps=raw.get("timestamps"),
        )

    async def close(self) -> None:
        """Clean up resources (CoFHE bridge, ICL session)."""
        await self.cofhe.stop()
        await self.icl.close()

    async def __aenter__(self) -> BlindferenceAgent:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
