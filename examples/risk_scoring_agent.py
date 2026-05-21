"""Confidential risk scoring example.

Demonstrates submitting sensitive numeric features (loan application data)
through the encrypted inference pipeline. The model returns a risk score
without the input features ever being exposed in plaintext."""

import asyncio
import os

from blindference_agent import BlindferenceAgent


async def risk_scoring_example():
    """Submit a confidential risk scoring request."""
    agent = BlindferenceAgent(
        icl_url=os.environ.get("BLF_ICL_URL", "https://icl.blindference.xyz"),
        cofhe_rpc=os.environ.get("BLF_COFHE_RPC", ""),
        private_key=os.environ.get("BLF_PRIVATE_KEY", ""),
    )

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

    print("Confidential Risk Scoring")
    print("=" * 60)
    print(f"Features: {features}")
    print()

    result = await agent.inference(
        prompt=prompt,
        model_id="groq:llama-3.3-70b-versatile",
        verifier_count=2,
    )

    print("=" * 60)
    print(f"Result: {result.text}")
    print("=" * 60)
    print(f"Model:     {result.model_id}")
    print(f"Leader:    {result.leader_address}")
    print(f"Verifiers: {len(result.verifier_addresses)}")
    print(f"Commit:    {result.commitment_hash[:20]}...")

    await agent.close()
    return result


if __name__ == "__main__":
    asyncio.run(risk_scoring_example())
