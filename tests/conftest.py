"""Pytest configuration and fixtures for Blindference Agent tests."""

import pytest


@pytest.fixture
def sample_prompt():
    return "Explain quantum computing in one sentence."


@pytest.fixture
def sample_model_id():
    return "groq:llama-3.3-70b-versatile"
