"""Minimal mock ICL server for testing examples without real infrastructure.

Run this in one terminal:
    python examples/mock_icl_server.py

Then in another terminal, run any example with mock mode:
    BLF_MOCK=1 BLF_ICL_URL=http://localhost:8765 python examples/simple_agent.py

Endpoints simulated:
    POST /v1/inference/quorum-preview  → fake quorum
    POST /v1/inference/requests        → fake request submission
    GET  /v1/inference/<id>            → fake status (progresses through states)
    POST /v1/inference/upload          → fake IPFS CID
    GET  /v1/coverage/<id>           → fake coverage
"""

import random
import string
import time
from typing import Any

from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory request store
_requests: dict[str, dict[str, Any]] = {}


def _random_id() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=32))


def _fake_quorum():
    return {
        "leader": "0x" + "a" * 40,
        "leader_tier": 1,
        "leader_reputation": 95,
        "verifiers": ["0x" + "b" * 40, "0x" + "c" * 40],
        "verifier_tiers": {"0x" + "b" * 40: 1, "0x" + "c" * 40: 1},
        "verifier_reputations": {"0x" + "b" * 40: 92, "0x" + "c" * 40: 88},
    }


@app.route("/v1/inference/quorum-preview", methods=["POST"])
def quorum_preview():
    return jsonify(_fake_quorum())


@app.route("/v1/inference/requests", methods=["POST"])
def submit_request():
    req_id = _random_id()
    now = time.time()
    _requests[req_id] = {
        "request_id": req_id,
        "status": "QUEUED",
        "created_at": now,
        "output_cid": _store_output_for_request(req_id),
        "quorum": {
            "leader_address": "0x" + "a" * 40,
            "verifier_addresses": ["0x" + "b" * 40, "0x" + "c" * 40],
            "verifiers": [
                {"address": "0x" + "b" * 40, "verdict": "CONFIRM"},
                {"address": "0x" + "c" * 40, "verdict": "CONFIRM"},
            ],
        },
        "text_result": {},
    }
    return jsonify({"request_id": req_id, "job_id": req_id})


@app.route("/v1/inference/upload", methods=["POST"])
def upload_blob():
    return jsonify({"cid": f"Qm{_random_id()}"})


@app.route("/v1/inference/<req_id>", methods=["GET"])
def get_status(req_id: str):
    req = _requests.get(req_id)
    if req is None:
        return jsonify({"detail": "Not Found"}), 404

    now = time.time()
    elapsed = now - req["created_at"]

    # Simulate state progression every ~3 seconds
    if elapsed < 3:
        req["status"] = "QUEUED"
    elif elapsed < 6:
        req["status"] = "ASSIGNED"
    elif elapsed < 9:
        req["status"] = "EXECUTING"
    elif elapsed < 12:
        req["status"] = "VERIFYING"
    else:
        req["status"] = "ACCEPTED"
        req["text_result"] = {
            "output_cid": req.get("output_cid", f"Qm{_random_id()}"),
            "commitment_hash": "0x" + "d" * 64,
            "encrypted_output_key_high": "0",
            "encrypted_output_key_low": "0",
        }

    return jsonify(req)


@app.route("/v1/coverage/<req_id>", methods=["GET"])
def get_coverage(req_id: str):
    return jsonify({"request_id": req_id, "status": "ACCEPTED", "coverage": 100})


# Store generated output blobs keyed by CID so the agent can "download" them
_output_blobs: dict[str, bytes] = {}


@app.route("/ipfs/<cid>", methods=["GET"])
def ipfs_gateway(cid: str):
    """Serve stored output blobs so the agent can download in mock mode."""
    blob = _output_blobs.get(cid)
    if blob is None:
        return jsonify({"detail": "Not Found"}), 404
    return blob, 200, {"Content-Type": "application/octet-stream"}


def _store_output_for_request(req_id: str) -> str:
    """Generate a fake output blob for a request and store it."""
    import random, string
    cid = "Qm" + "".join(random.choices(string.ascii_lowercase + string.digits, k=32))
    fake_result = (
        f"This is a mock inference result for request {req_id}.\n\n"
        "In real mode, this would be the decrypted output from the quorum."
    )
    _output_blobs[cid] = fake_result.encode("utf-8")
    return cid


if __name__ == "__main__":
    print("Mock ICL server starting on http://localhost:8765")
    print("Use BLF_MOCK=1 BLF_ICL_URL=http://localhost:8765 to test examples")
    app.run(host="0.0.0.0", port=8765, debug=False)
