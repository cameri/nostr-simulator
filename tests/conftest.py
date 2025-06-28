"""Test configuration and fixtures."""

import shutil
import tempfile
from pathlib import Path

import pytest

from nostr_simulator.config import Config, NetworkConfig, SimulationConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return Config(
        simulation=SimulationConfig(duration=100.0, time_step=1.0, random_seed=42),
        network=NetworkConfig(num_relays=5, num_honest_users=20, num_malicious_users=2),
    )


@pytest.fixture
def minimal_config():
    """Create a minimal configuration for testing."""
    return Config()
