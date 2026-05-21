"""REST client for the Blindference ICL (Inference Coordination Layer)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from blindference_agent.types import (
    InferenceRequest,
    InferenceStatus,
    QuorumNode,
    QuorumPreview,
)

logger = logging.getLogger("blindference-agent.icl")


class ICLClient:
    """Typed async REST client for the Blindference ICL."""

    def __init__(self, base_url: str) -> None:
        self.base = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Quorum preview
    # ------------------------------------------------------------------

    async def quorum_preview(
        self,
        model_id: str,
        min_tier: int = 0,
        verifier_count: int = 2,
        zdr_required: bool = False,
    ) -> QuorumPreview:
        """Fetch a quorum preview for the given model.

        Returns the leader + verifier nodes selected by the ICL.
        """
        payload = {
            "model_id": model_id,
            "min_tier": min_tier,
            "verifier_count": verifier_count,
            "zdr_required": zdr_required,
        }
        data = await self._post("/v1/inference/quorum-preview", payload)
        leader = QuorumNode(
            address=data["leader"],
            tier=data.get("leader_tier", 0),
            reputation_score=data.get("leader_reputation", 0),
        )
        verifiers = [
            QuorumNode(
                address=v,
                tier=data.get("verifier_tiers", {}).get(v, 0),
                reputation_score=data.get("verifier_reputations", {}).get(v, 0),
            )
            for v in data.get("verifiers", [])
        ]
        return QuorumPreview(leader=leader, verifiers=verifiers)

    # ------------------------------------------------------------------
    # Submit request
    # ------------------------------------------------------------------

    async def submit_text(
        self,
        developer_address: str,
        task_id: str,
        model_id: str,
        prompt_cid: str,
        encrypted_prompt_key_high: str,
        encrypted_prompt_key_low: str,
        leader_address: str,
        verifier_addresses: list[str],
        min_tier: int = 0,
        verifier_count: int = 2,
        metadata: dict[str, Any] | None = None,
    ) -> InferenceRequest:
        """Submit a text-inference request to the ICL.

        Args:
            developer_address: The submitting wallet address.
            task_id: Keccak-256 hash used as the on-chain task ID.
            model_id: e.g. ``"groq:llama-3.3-70b-versatile"``.
            prompt_cid: IPFS CID of the AES-GCM encrypted prompt blob.
            encrypted_prompt_key_high: CoFHE ctHash of the high AES-key half.
            encrypted_prompt_key_low: CoFHE ctHash of the low AES-key half.
            leader_address: Address of the assigned leader node.
            verifier_addresses: List of assigned verifier node addresses.
            min_tier: Minimum node tier for quorum selection.
            verifier_count: Number of verifiers in the quorum.
            metadata: Optional extra metadata (model, provider, etc.).

        Returns:
            An :class:`InferenceRequest` with ``request_id`` and initial
            ``status="QUEUED"``.
        """
        payload = {
            "developer_address": developer_address,
            "task_id": task_id,
            "mode": "text",
            "model_id": model_id,
            "leader_address": leader_address,
            "verifier_addresses": verifier_addresses,
            "text_request": {
                "prompt_cid": prompt_cid,
                "encrypted_prompt_key": {
                    "high": encrypted_prompt_key_high,
                    "low": encrypted_prompt_key_low,
                },
                "model_id": model_id,
                "coverage_enabled": False,
            },
            "min_tier": min_tier,
            "zdr_required": False,
            "verifier_count": verifier_count,
            "metadata": metadata or {},
        }
        data = await self._post("/v1/inference/requests", payload)
        return InferenceRequest(
            request_id=data.get("request_id", data.get("job_id", "")),
            task_id=task_id,
            model_id=model_id,
            mode="text",
            status="QUEUED",
        )

    # ------------------------------------------------------------------
    # Poll status
    # ------------------------------------------------------------------

    async def get_status(self, request_id: str) -> InferenceStatus:
        """Poll the ICL for the current status of a request."""
        data = await self._get(f"/v1/inference/{request_id}")
        return _parse_status(data)

    async def stream_status(
        self,
        request_id: str,
        interval: float = 3.0,
    ):
        """Async generator that yields :class:`InferenceStatus` every
        *interval* seconds until the job reaches a terminal state
        (``ACCEPTED``, ``REJECTED``, or ``DISPUTED``).
        """
        while True:
            status = await self.get_status(request_id)
            yield status
            if status.status in ("ACCEPTED", "REJECTED", "DISPUTED"):
                break
            await asyncio.sleep(interval)

    # ------------------------------------------------------------------
    # Upload blob
    # ------------------------------------------------------------------

    async def upload_blob(self, data: bytes) -> str:
        """Upload an encrypted prompt blob to the ICL (Pinata-backed).

        Returns the IPFS CID.
        """
        session = await self._get_session()
        form = aiohttp.FormData()
        form.add_field("file", data, filename="prompt.bin", content_type="application/octet-stream")
        async with session.post(f"{self.base}/v1/inference/upload", data=form) as resp:
            if resp.status not in (200, 201):
                text = await resp.text()
                raise RuntimeError(f"Upload failed {resp.status}: {text}")
            result = await resp.json()
            return result["cid"]

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str) -> dict[str, Any]:
        session = await self._get_session()
        async with session.get(f"{self.base}{path}") as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"ICL GET {path} failed {resp.status}: {text}")
            return await resp.json()

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        session = await self._get_session()
        async with session.post(f"{self.base}{path}", json=payload) as resp:
            if resp.status not in (200, 201):
                text = await resp.text()
                raise RuntimeError(f"ICL POST {path} failed {resp.status}: {text}")
            return await resp.json()


def _parse_status(raw: dict[str, Any]) -> InferenceStatus:
    """Parse a raw ICL status response into a typed :class:`InferenceStatus`."""
    quorum = raw.get("quorum", {})
    verifiers = quorum.get("verifiers", [])
    confirm_count = sum(
        1 for v in verifiers if v.get("verdict") == "CONFIRM"
    )

    text_result = raw.get("text_result", {})
    return InferenceStatus(
        request_id=raw.get("request_id", raw.get("job_id", "")),
        step=_derive_step(raw.get("status", "QUEUED")),
        status=raw.get("status", "QUEUED"),
        confirm_count=confirm_count,
        verifier_count=len(verifiers),
        output_cid=text_result.get("output_cid"),
        encrypted_output_key_high=text_result.get("encrypted_output_key_high"),
        encrypted_output_key_low=text_result.get("encrypted_output_key_low"),
        commitment_hash=text_result.get("commitment_hash"),
        result_commit_tx=raw.get("result_commit_tx"),
    )


def _derive_step(status: str) -> str:
    """Map ICL status string to a human-readable step name."""
    mapping = {
        "QUEUED": "quorum",
        "ASSIGNED": "leader",
        "EXECUTING": "verifier",
        "VERIFYING": "onchain",
        "ACCEPTED": "decrypt",
        "REJECTED": "error",
        "DISPUTED": "error",
    }
    return mapping.get(status, "unknown")
