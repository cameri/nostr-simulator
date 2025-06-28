"""Tests for configuration management."""

import tempfile
from pathlib import Path

import pytest

from .config import (
    AntiSpamConfig,
    AttackConfig,
    Config,
    MetricsConfig,
    NetworkConfig,
    SimulationConfig,
    get_default_config,
    load_config,
    save_config,
)


class TestSimulationConfig:
    """Test SimulationConfig validation and functionality."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        config = SimulationConfig()
        assert config.duration == 3600.0
        assert config.time_step == 1.0
        assert config.random_seed is None
        assert config.max_events is None

    def test_duration_validation(self) -> None:
        """Test that duration must be positive."""
        with pytest.raises(ValueError, match="Duration must be positive"):
            SimulationConfig(duration=0.0)

        with pytest.raises(ValueError, match="Duration must be positive"):
            SimulationConfig(duration=-1.0)

    def test_time_step_validation(self) -> None:
        """Test that time step must be positive."""
        with pytest.raises(ValueError, match="Time step must be positive"):
            SimulationConfig(time_step=0.0)

        with pytest.raises(ValueError, match="Time step must be positive"):
            SimulationConfig(time_step=-1.0)

    def test_valid_configuration(self) -> None:
        """Test that valid configurations are accepted."""
        config = SimulationConfig(
            duration=1800.0, time_step=0.5, random_seed=42, max_events=1000
        )
        assert config.duration == 1800.0
        assert config.time_step == 0.5
        assert config.random_seed == 42
        assert config.max_events == 1000


class TestNetworkConfig:
    """Test NetworkConfig validation and functionality."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        config = NetworkConfig()
        assert config.num_relays == 10
        assert config.num_honest_users == 100
        assert config.num_malicious_users == 10
        assert config.connection_probability == 0.3

    def test_count_validation(self) -> None:
        """Test that counts must be non-negative."""
        with pytest.raises(ValueError, match="Counts must be non-negative"):
            NetworkConfig(num_relays=-1)

        with pytest.raises(ValueError, match="Counts must be non-negative"):
            NetworkConfig(num_honest_users=-1)

        with pytest.raises(ValueError, match="Counts must be non-negative"):
            NetworkConfig(num_malicious_users=-1)

    def test_probability_validation(self) -> None:
        """Test that probability must be between 0 and 1."""
        with pytest.raises(ValueError, match="Probability must be between 0 and 1"):
            NetworkConfig(connection_probability=-0.1)

        with pytest.raises(ValueError, match="Probability must be between 0 and 1"):
            NetworkConfig(connection_probability=1.1)

    def test_valid_configuration(self) -> None:
        """Test that valid configurations are accepted."""
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


class TestAntiSpamConfig:
    """Test AntiSpamConfig validation and functionality."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        config = AntiSpamConfig()
        assert config.enabled_strategies == ["rate_limiting"]
        assert config.pow_difficulty == 4
        assert config.rate_limit_per_second == 1.0
        assert config.wot_trust_threshold == 0.5

    def test_pow_difficulty_validation(self) -> None:
        """Test that PoW difficulty must be non-negative."""
        with pytest.raises(ValueError, match="PoW difficulty must be non-negative"):
            AntiSpamConfig(pow_difficulty=-1)

    def test_rate_limit_validation(self) -> None:
        """Test that rate limit must be positive."""
        with pytest.raises(ValueError, match="Rate limit must be positive"):
            AntiSpamConfig(rate_limit_per_second=0.0)

        with pytest.raises(ValueError, match="Rate limit must be positive"):
            AntiSpamConfig(rate_limit_per_second=-1.0)

    def test_trust_threshold_validation(self) -> None:
        """Test that trust threshold must be between 0 and 1."""
        with pytest.raises(ValueError, match="Trust threshold must be between 0 and 1"):
            AntiSpamConfig(wot_trust_threshold=-0.1)

        with pytest.raises(ValueError, match="Trust threshold must be between 0 and 1"):
            AntiSpamConfig(wot_trust_threshold=1.1)


class TestConfig:
    """Test main Config class functionality."""

    def test_default_configuration(self) -> None:
        """Test that default configuration is valid."""
        config = Config()
        assert isinstance(config.simulation, SimulationConfig)
        assert isinstance(config.network, NetworkConfig)
        assert isinstance(config.antispam, AntiSpamConfig)
        assert isinstance(config.attacks, AttackConfig)
        assert isinstance(config.metrics, MetricsConfig)

    def test_nested_configuration(self) -> None:
        """Test creating configuration with nested configs."""
        config = Config(
            simulation=SimulationConfig(duration=1800.0),
            network=NetworkConfig(num_relays=5),
        )
        assert config.simulation.duration == 1800.0
        assert config.network.num_relays == 5
        # Other configs should use defaults
        assert config.antispam.pow_difficulty == 4


class TestConfigFileOperations:
    """Test configuration file loading and saving."""

    def test_save_and_load_config(self) -> None:
        """Test saving and loading configuration from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_path = Path(f.name)

        try:
            # Create and save config
            original_config = Config(
                simulation=SimulationConfig(duration=1800.0, random_seed=42),
                network=NetworkConfig(num_relays=5),
            )
            save_config(original_config, config_path)

            # Load config
            loaded_config = load_config(config_path)

            # Verify loaded config matches original
            assert loaded_config.simulation.duration == 1800.0
            assert loaded_config.simulation.random_seed == 42
            assert loaded_config.network.num_relays == 5

        finally:
            config_path.unlink()

    def test_load_nonexistent_file(self) -> None:
        """Test loading from nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_file.yaml")

    def test_get_default_config(self) -> None:
        """Test getting default configuration."""
        config = get_default_config()
        assert isinstance(config, Config)
        assert config.simulation.duration == 3600.0
        assert config.network.num_relays == 10


if __name__ == "__main__":
    pytest.main([__file__])
