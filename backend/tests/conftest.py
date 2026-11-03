"""Shared pytest fixtures for all backend tests."""

import pytest
from backend.app.api.dependencies import reset_simulation_engine


@pytest.fixture(autouse=True)
def clean_simulation_engine():
    """Reset the singleton simulation engine before each test to prevent state leakage."""
    reset_simulation_engine()
    yield
    reset_simulation_engine()
