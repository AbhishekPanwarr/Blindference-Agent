"""Confidential risk scoring example.

Demonstrates submitting sensitive numeric features (loan application data)
through the encrypted inference pipeline with full execution trace. The
model returns a risk score without the input features ever being exposed
in plaintext on any node or intermediary server.
"""

import asyncio
import logging
import os
import sys

from blindference_agent import BlindferenceAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)


async def risk_scoring_example():
    print("=" * 70)
    print("Blindference Agent — Confidential Risk Scoring")
    print("=" * 70)
    print()
    print("Initializing agent...")

    use_mock = os.environ.get("BLF_MOCK", "0") in ("1", "true", "yes")
    if use_mock:
        print("        MODE: MOCK (no encryption, no CoFHE, no private key needed)")
        print("        Set BLF_MOCK=0 and configure .env for real confidential inference.")
        print()

    try:
        agent = BlindferenceAgent(
            icl_url=os.environ.get("BLF_ICL_URL", "https://icl.blindference.xyz"),
            cofhe_rpc=os.environ.get("BLF_COFHE_RPC", ""),
            private_key=os.environ.get("BLF_PRIVATE_KEY", ""),
            mock=use_mock,
        )
    except Exception as exc:
        print(f"[ERROR] {exc}")
        if not use_mock:
            print("        Check that BLF_COFHE_RPC and BLF_PRIVATE_KEY are set in .env")
            print("        Or run with BLF_MOCK=1 for a no-infrastructure demo.")
        sys.exit(1)

    wallet = await agent._ensure_wallet()
    print(f"Wallet: {wallet}")
    print()

    # Sensitive loan application features
    features = {
        "credit_score": 720,
        "loan_amount_usd": 50000,
        "account_age_months": 36,
        "previous_defaults": 0,
        "monthly_income": 8000,
    }

    prompt = (
        f"Risk assessment: credit_score={features['credit_score']}, "
        f"loan_amount={features['loan_amount_usd']}, "
        f"account_age={features['account_age_months']} months, "
        f"defaults={features['previous_defaults']}, "
        f"income={features['monthly_income']}. "
        "Return only a risk score from 0 (low risk) to 100 (high risk)."
    )

    print("Sensitive features:")
    for k, v in features.items():
        print(f"  • {k}: {v}")
    print()
    print("Submitting through confidential inference pipeline...")
    print("  Step 1: AES-256-GCM encrypt prompt")
    print("  Step 2: CoFHE-encrypt AES key halves")
    print("  Step 3: Upload encrypted blob to IPFS")
    print("  Step 4: Store key on-chain (Arbitrum Sepolia)")
    print("  Step 5: Submit to ICL")
    print()

    try:
        request = await agent.submit(
            prompt=prompt,
            model_id="groq:llama-3.3-70b-versatile",
            verifier_count=2,
        )
    except Exception as exc:
        print(f"[ERROR] Submission failed: {exc}")
        await agent.close()
        sys.exit(1)

    print(f"Request ID: {request.request_id}")
    print("Waiting for quorum consensus...")
    print()

    poll_count = 0
    max_polls = 100

    while poll_count < max_polls:
        status = await agent.icl.get_status(request.request_id)
        poll_count += 1

        step_names = {
            "QUEUED":     "⏳  Queued — building quorum",
            "ASSIGNED":   "👑  Assigned — leader selected",
            "EXECUTING":  "🧠  Executing — leader inference + verifier replay",
            "VERIFYING":  "🔗  Verifying — on-chain commitment",
            "ACCEPTED":   "✅  Accepted — quorum consensus reached",
            "REJECTED":   "❌  Rejected — quorum failed",
            "DISPUTED":   "⚠️  Disputed — consensus not reached",
        }

        step_msg = step_names.get(status.status, status.status)
        print(f"\r  [{poll_count:3d}] {step_msg}", end="")

        if status.status == "ACCEPTED":
            print()
            break
        elif status.status in ("REJECTED", "DISPUTED"):
            print()
            print(f"[ERROR] Inference failed: {status.status}")
            await agent.close()
            sys.exit(1)

        await asyncio.sleep(3.0)
    else:
        print()
        print("[ERROR] Timeout waiting for quorum consensus")
        await agent.close()
        sys.exit(1)

    print("Downloading and decrypting result...")
    try:
        result = await agent._decrypt_result(status, request.model_id)
    except Exception as exc:
        print(f"[ERROR] Decryption failed: {exc}")
        await agent.close()
        sys.exit(1)

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print(result.text)
    print("=" * 70)
    print()
    print("Metadata:")
    print(f"  Model:        {result.model_id}")
    print(f"  Request ID:   {result.request_id}")
    print(f"  Leader:       {result.leader_address}")
    print(f"  Verifiers:    {len(result.verifier_addresses)}")
    print(f"  Commitment:   {result.commitment_hash[:20]}...")
    print()

    await agent.close()
    print("Done. 👍")
    return result


if __name__ == "__main__":
    asyncio.run(risk_scoring_example())
