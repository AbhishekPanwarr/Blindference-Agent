"""Tests for blindference_agent.encryptor."""

import pytest

from blindference_agent.encryptor import (
    decrypt_output,
    encrypt_prompt,
    generate_aes_key,
    merge_key,
    pack_payload,
    split_key,
)


class TestEncryptPrompt:
    def test_encrypts_plaintext(self):
        key = generate_aes_key()
        payload = encrypt_prompt("Hello, Blindference!", key=key)

        assert payload.ciphertext != b"Hello, Blindference!"
        assert len(payload.iv) == 12
        assert len(payload.auth_tag) == 16
        assert payload.aes_key == key

    def test_generates_random_key_by_default(self):
        p1 = encrypt_prompt("test")
        p2 = encrypt_prompt("test")
        assert p1.aes_key != p2.aes_key


class TestPackAndDecrypt:
    def test_roundtrip(self):
        plaintext = "Roundtrip test message 🚀"
        key = generate_aes_key()
        payload = encrypt_prompt(plaintext, key=key)
        packed = pack_payload(payload)

        decrypted = decrypt_output(packed, key)
        assert decrypted == plaintext

    def test_different_keys_fail(self):
        key1 = generate_aes_key()
        key2 = generate_aes_key()
        payload = encrypt_prompt("secret", key=key1)
        packed = pack_payload(payload)

        with pytest.raises(Exception):
            decrypt_output(packed, key2)


class TestKeySplitMerge:
    def test_split_merge_roundtrip(self):
        key = generate_aes_key()
        high, low = split_key(key)
        assert len(high) == 16
        assert len(low) == 16
        assert high + low == key

    def test_merge_key(self):
        high = b"A" * 16
        low = b"B" * 16
        merged = merge_key(high, low)
        assert merged == b"A" * 16 + b"B" * 16
        assert len(merged) == 32

    def test_split_key_length(self):
        key = generate_aes_key()
        assert len(key) == 32
        high, low = split_key(key)
        assert len(high) == 16
        assert len(low) == 16
