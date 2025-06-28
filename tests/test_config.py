"""Tests for the configuration module."""

import pytest

from nostr_simulator.config import (
    Config,
    NetworkConfig,
    SimulationConfig,
    get_default_config,
    load_config,
    save_config,
)


class TestSimulationConfig:
    """Test SimulationConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = SimulationConfig()
        assert config.duration == 3600.0
        assert config.time_step == 1.0
        assert config.random_seed is None
        assert config.max_events is None

    def test_custom_values(self):
        """Test setting custom values."""
        config = SimulationConfig(
            duration=1800.0, time_step=0.5, random_seed=42, max_events=1000
        )
        assert config.duration == 1800.0
        assert config.time_step == 0.5
        assert config.random_seed == 42
        assert config.max_events == 1000

    def test_duration_validation(self):
        """Test that duration must be positive."""
        with pytest.raises(ValueError, match="Duration must be positive"):
            SimulationConfig(duration=0.0)

        with pytest.raises(ValueError, match="Duration must be positive"):
            SimulationConfig(duration=-1.0)

    def test_time_step_validation(self):
        """Test that time_step must be positive."""
        with pytest.raises(ValueError, match="Time step must be positive"):
            SimulationConfig(time_step=0.0)

        with pytest.raises(ValueError, match="Time step must be positive"):
            SimulationConfig(time_step=-0.1)


class TestNetworkConfig:
    """Test NetworkConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = NetworkConfig()
        assert config.num_relays == 10
        assert config.num_honest_users == 100
        assert config.num_malicious_users == 10
        assert config.connection_probability == 0.3

    def test_custom_values(self):
        """Test setting custom values."""
        config = NetworkConfig(
            num_relays=5,
            num_honest_users=50,
            num_malicious_users=5,
            connection_probability=0.5,
        )
        assert config.num_relays == 5
        assert config.num_honest_users == 50
        assert config.num_malicious_users == 5
        assert config.connection_probability == 0.5

    def test_count_validation(self):
        """Test that counts must be non-negative."""
        with pytest.raises(ValueError, match="Counts must be non-negative"):
            NetworkConfig(num_relays=-1)

        with pytest.raises(ValueError, match="Counts must be non-negative"):
            NetworkConfig(num_honest_users=-1)

        with pytest.raises(ValueError, match="Counts must be non-negative"):
            NetworkConfig(num_malicious_users=-1)

    def test_probability_validation(self):
        """Test that probability must be between 0 and 1."""
        with pytest.raises(ValueError, match="Probability must be between 0 and 1"):
            NetworkConfig(connection_probability=-0.1)

        with pytest.raises(ValueError, match="Probability must be between 0 and 1"):
            NetworkConfig(connection_probability=1.1)


class TestConfig:
    """Test main Config class."""

    def test_default_config(self):
        """Test that default configuration is valid."""
        config = Config()
        assert isinstance(config.simulation, SimulationConfig)
        assert isinstance(config.network, NetworkConfig)
        assert config.simulation.duration == 3600.0
        assert config.network.num_relays == 10

    def test_custom_config(self, sample_config):
        """Test creating config with custom values."""
        assert sample_config.simulation.duration == 100.0
        assert sample_config.network.num_relays == 5

    def test_get_default_config(self):
        """Test get_default_config function."""
        config = get_default_config()
        assert isinstance(config, Config)
        assert config.simulation.duration == 3600.0


class TestConfigIO:
    """Test configuration file I/O."""

    def test_save_and_load_config(self, temp_dir, sample_config):
        """Test saving and loading configuration."""
        config_file = temp_dir / "test_config.yaml"

        # Save config
        save_config(sample_config, config_file)
        assert config_file.exists()

        # Load config
        loaded_config = load_config(config_file)
        assert loaded_config.simulation.duration == sample_config.simulation.duration
        assert loaded_config.network.num_relays == sample_config.network.num_relays

    def test_load_nonexistent_config(self, temp_dir):
        """Test loading non-existent configuration file."""
        config_file = temp_dir / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config(config_file)

    def test_save_config_creates_directory(self, temp_dir, sample_config):
        """Test that save_config creates parent directories."""
        config_file = temp_dir / "subdir" / "config.yaml"

        save_config(sample_config, config_file)
        assert config_file.exists()
        assert config_file.parent.exists()
