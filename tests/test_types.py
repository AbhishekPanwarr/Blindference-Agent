"""Tests for blindference_agent.types."""

from blindference_agent.types import (
    CoFHEKeyHandles,
    EncryptedPayload,
    InferenceRequest,
    InferenceResult,
    InferenceStatus,
    QuorumNode,
    QuorumPreview,
)


class TestQuorumNode:
    def test_basic(self):
        node = QuorumNode(address="0x" + "a" * 40, tier=1, reputation_score=95)
        assert node.address == "0x" + "a" * 40
        assert node.tier == 1
        assert node.reputation_score == 95

    def test_defaults(self):
        node = QuorumNode(address="0x" + "b" * 40)
        assert node.tier == 0
        assert node.reputation_score == 0


class TestQuorumPreview:
    def test_basic(self):
        leader = QuorumNode("0x" + "c" * 40, tier=1)
        verifiers = [QuorumNode("0x" + "d" * 40, tier=0)]
        preview = QuorumPreview(leader=leader, verifiers=verifiers)
        assert preview.leader.address == "0x" + "c" * 40
        assert len(preview.verifiers) == 1


class TestInferenceRequest:
    def test_basic(self):
        req = InferenceRequest(
            request_id="abc123",
            task_id="task456",
            model_id="groq:llama-3.3-70b-versatile",
            mode="text",
            status="QUEUED",
        )
        assert req.request_id == "abc123"
        assert req.status == "QUEUED"


class TestInferenceStatus:
    def test_basic(self):
        status = InferenceStatus(
            request_id="abc123",
            step="quorum",
            status="QUEUED",
            confirm_count=0,
            verifier_count=2,
        )
        assert status.confirm_count == 0
        assert status.verifier_count == 2

    def test_defaults(self):
        status = InferenceStatus(
            request_id="abc123",
            step="quorum",
            status="QUEUED",
        )
        assert status.confirm_count == 0
        assert status.verifier_count == 2
        assert status.output_cid is None


class TestInferenceResult:
    def test_basic(self):
        result = InferenceResult(
            request_id="abc123",
            task_id="task456",
            text="Hello, world!",
            model_id="groq:llama-3.3-70b-versatile",
            output_cid="QmTest",
            leader_address="0x" + "e" * 40,
            verifier_addresses=["0x" + "f" * 40],
            commitment_hash="0xdeadbeef",
        )
        assert result.text == "Hello, world!"
        assert result.commitment_hash == "0xdeadbeef"


class TestEncryptedPayload:
    def test_basic(self):
        payload = EncryptedPayload(
            ciphertext=b"ct",
            iv=b"i" * 12,
            auth_tag=b"t" * 16,
            aes_key=b"k" * 32,
        )
        assert len(payload.iv) == 12
        assert len(payload.auth_tag) == 16
        assert len(payload.aes_key) == 32


class TestCoFHEKeyHandles:
    def test_basic(self):
        handles = CoFHEKeyHandles(high="12345", low="67890")
        assert handles.high == "12345"
        assert handles.low == "67890"
