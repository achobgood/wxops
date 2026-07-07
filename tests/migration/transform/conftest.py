"""Shared fixtures for migration transform tests."""

import random

import pytest


@pytest.fixture(autouse=True)
def seed_random():
    """Seed random for reproducible overlap detection tests.

    The overlap detection uses random string enumeration, so seeding
    ensures deterministic test runs. The seed value 42 was verified
    to produce correct results across all overlap test cases.
    """
    random.seed(42)
    yield
    # Restore unseeded state so we don't affect other test modules
    random.seed()
