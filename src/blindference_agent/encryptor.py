"""AES-GCM prompt encryption and CoFHE key-splitting utilities."""

from __future__ import annotations

import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from blindference_agent.types import EncryptedPayload, CoFHEKeyHandles


def generate_aes_key() -> bytes:
    """Generate a 32-byte (256-bit) random AES key."""
    return os.urandom(32)


def encrypt_prompt(plaintext: str, key: bytes | None = None) -> EncryptedPayload:
    """Encrypt a prompt with AES-256-GCM.

    Args:
        plaintext: The raw user prompt.
        key: Optional 32-byte AES key. If ``None``, a new random key is generated.

    Returns:
        :class:`EncryptedPayload` with ciphertext, IV, auth tag, and the raw key.
    """
    aes_key = key or generate_aes_key()
    iv = os.urandom(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(aes_key)
    ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    # AES-GCM appends the 16-byte auth tag to the ciphertext
    return EncryptedPayload(
        ciphertext=ciphertext[:-16],
        iv=iv,
        auth_tag=ciphertext[-16:],
        aes_key=aes_key,
    )


def pack_payload(payload: EncryptedPayload) -> bytes:
    """Pack an encrypted payload into a single byte string for IPFS upload.

    Format: ``[iv (12 bytes)] [auth_tag (16 bytes)] [ciphertext]``
    """
    return payload.iv + payload.auth_tag + payload.ciphertext


def decrypt_output(ciphertext: bytes, key: bytes) -> str:
    """Decrypt an AES-GCM ciphertext (IV + auth_tag + ciphertext) with the
    given 32-byte AES key.

    Args:
        ciphertext: The packed output blob (same format as :func:`pack_payload`).
        key: The 32-byte AES key.

    Returns:
        The decrypted plaintext string.
    """
    iv = ciphertext[:12]
    auth_tag = ciphertext[12:28]
    ct = ciphertext[28:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(iv, ct + auth_tag, None)
    return plaintext.decode("utf-8")


def split_key(key: bytes) -> tuple[bytes, bytes]:
    """Split a 32-byte AES key into two 16-byte halves for CoFHE encryption.

    Returns:
        ``(high, low)`` — each 16 bytes.
    """
    return key[:16], key[16:]


def merge_key(high: bytes, low: bytes) -> bytes:
    """Merge two 16-byte halves back into a 32-byte AES key."""
    return high + low


async def encrypt_key_via_bridge(
    bridge,
    high: bytes,
    low: bytes,
) -> CoFHEKeyHandles:
    """Encrypt AES key halves using the CoFHE bridge.

    Args:
        bridge: An instance of :class:`blindference_agent.cofhe_bridge.CoFHEBridge`.
        high: High 16 bytes of the AES key.
        low: Low 16 bytes of the AES key.

    Returns:
        :class:`CoFHEKeyHandles` with CoFHE ctHashes for each half.
    """
    high_result = await bridge.encrypt_uint128(int.from_bytes(high, "big"))
    low_result = await bridge.encrypt_uint128(int.from_bytes(low, "big"))
    return CoFHEKeyHandles(
        high=str(high_result["ctHash"]),
        low=str(low_result["ctHash"]),
    )
