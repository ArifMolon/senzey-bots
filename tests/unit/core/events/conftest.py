"""Shared fixtures for core/events unit tests."""

from collections.abc import Generator

import pytest

from senzey_bots.core.events.buffer import clear_buffer


@pytest.fixture(autouse=True)
def _clear_event_buffer() -> Generator[None, None, None]:
    """Clear the in-memory event buffer before each test to prevent state leakage."""
    clear_buffer()
    yield
    clear_buffer()
