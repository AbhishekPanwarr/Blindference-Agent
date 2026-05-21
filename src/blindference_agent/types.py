"""Blindference Agent SDK — type definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class QuorumNode:
    """A node selected for the inference quorum."""

    address: str
    tier: int = 0
    reputation_score: int = 0


@dataclass(frozen=True)
class QuorumPreview:
    """Result of a quorum-preview request."""

    leader: QuorumNode
    verifiers: list[QuorumNode]


@dataclass(frozen=True)
class InferenceRequest:
    """A submitted inference request."""

    request_id: str
    task_id: str
    model_id: str
    mode: Literal["text", "risk"]
    status: Literal["QUEUED", "ASSIGNED", "EXECUTING", "VERIFYING", "ACCEPTED", "REJECTED", "DISPUTED"]


@dataclass(frozen=True)
class InferenceStatus:
    """Live status of an inference job."""

    request_id: str
    step: str  # encrypt | quorum | leader | verifier | onchain | decrypt
    status: Literal["QUEUED", "ASSIGNED", "EXECUTING", "VERIFYING", "ACCEPTED", "REJECTED", "DISPUTED"]
    confirm_count: int = 0
    verifier_count: int = 2
    output_cid: str | None = None
    encrypted_output_key_high: str | None = None
    encrypted_output_key_low: str | None = None
    commitment_hash: str | None = None
    result_commit_tx: str | None = None


@dataclass(frozen=True)
class InferenceResult:
    """Final decrypted inference result."""

    request_id: str
    task_id: str
    text: str
    model_id: str
    output_cid: str
    leader_address: str
    verifier_addresses: list[str]
    commitment_hash: str
    result_commit_tx: str | None = None
    timestamps: dict[str, int] | None = None


@dataclass(frozen=True)
class EncryptedPayload:
    """AES-GCM encrypted prompt + metadata."""

    ciphertext: bytes
    iv: bytes
    auth_tag: bytes
    aes_key: bytes  # 32-byte raw key (kept in memory only)


@dataclass(frozen=True)
class CoFHEKeyHandles:
    """CoFHE-encrypted AES key halves returned by the bridge."""

    high: str  # ctHash of high 16 bytes
    low: str   # ctHash of low 16 bytes
