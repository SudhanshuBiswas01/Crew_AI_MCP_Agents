"""
conftest.py — shared pytest fixtures and configuration
"""

import pytest


def pytest_configure(config):
    """Register custom markers so pytest doesn't warn about unknown marks."""
    config.addinivalue_line(
        "markers",
        "e2e: end-to-end tests that require a running Ollama instance",
    )
