"""Configuration management for the Nostr Simulator."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, validator


class SimulationConfig(BaseModel):
    """Configuration for simulation parameters."""

    duration: float = Field(
        default=3600.0, description="Simulation duration in seconds"
    )
    time_step: float = Field(default=1.0, description="Simulation time step in seconds")
    random_seed: int | None = Field(
        default=None, description="Random seed for reproducibility"
    )
    max_events: int | None = Field(
        default=None, description="Maximum number of events to process"
    )

    @validator("duration")
    def duration_must_be_positive(cls, v: float) -> float:
        """Validate that duration is positive."""
        if v <= 0:
            raise ValueError("Duration must be positive")
        return v

    @validator("time_step")
    def time_step_must_be_positive(cls, v: float) -> float:
        """Validate that time step is positive."""
        if v <= 0:
            raise ValueError("Time step must be positive")
        return v


class NetworkConfig(BaseModel):
    """Configuration for network topology."""

    num_relays: int = Field(default=10, description="Number of relay nodes")
    num_honest_users: int = Field(default=100, description="Number of honest users")
    num_malicious_users: int = Field(
        default=10, description="Number of malicious users"
    )
    connection_probability: float = Field(
        default=0.3, description="Probability of connection between nodes"
    )

    @validator("num_relays", "num_honest_users", "num_malicious_users")
    def counts_must_be_positive(cls, v: int) -> int:
        """Validate that counts are positive."""
        if v < 0:
            raise ValueError("Counts must be non-negative")
        return v

    @validator("connection_probability")
    def probability_must_be_valid(cls, v: float) -> float:
        """Validate that probability is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Probability must be between 0 and 1")
        return v


class AntiSpamConfig(BaseModel):
    """Configuration for anti-spam strategies."""

    enabled_strategies: list[str] = Field(
        default_factory=lambda: ["rate_limiting"],
        description="List of enabled anti-spam strategies",
    )
    pow_difficulty: int = Field(default=4, description="Proof of Work difficulty")
    rate_limit_per_second: float = Field(
        default=1.0, description="Rate limit events per second"
    )
    wot_trust_threshold: float = Field(
        default=0.5, description="Web of Trust threshold"
    )

    @validator("pow_difficulty")
    def pow_difficulty_must_be_positive(cls, v: int) -> int:
        """Validate that PoW difficulty is positive."""
        if v < 0:
            raise ValueError("PoW difficulty must be non-negative")
        return v

    @validator("rate_limit_per_second")
    def rate_limit_must_be_positive(cls, v: float) -> float:
        """Validate that rate limit is positive."""
        if v <= 0:
            raise ValueError("Rate limit must be positive")
        return v

    @validator("wot_trust_threshold")
    def trust_threshold_must_be_valid(cls, v: float) -> float:
        """Validate that trust threshold is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Trust threshold must be between 0 and 1")
        return v


class AttackConfig(BaseModel):
    """Configuration for attack scenarios."""

    sybil_attack_enabled: bool = Field(
        default=False, description="Enable Sybil attacks"
    )
    burst_spam_enabled: bool = Field(
        default=False, description="Enable burst spam attacks"
    )
    replay_attack_enabled: bool = Field(
        default=False, description="Enable replay attacks"
    )
    offline_abuse_enabled: bool = Field(
        default=False, description="Enable offline abuse"
    )

    sybil_identities_per_attacker: int = Field(
        default=10, description="Number of identities per Sybil attacker"
    )
    burst_spam_rate: float = Field(
        default=10.0, description="Burst spam rate (events per second)"
    )
    burst_duration: float = Field(
        default=60.0, description="Duration of burst attacks in seconds"
    )

    @validator("sybil_identities_per_attacker")
    def sybil_identities_must_be_positive(cls, v: int) -> int:
        """Validate that Sybil identities count is positive."""
        if v <= 0:
            raise ValueError("Sybil identities count must be positive")
        return v

    @validator("burst_spam_rate")
    def burst_rate_must_be_positive(cls, v: float) -> float:
        """Validate that burst spam rate is positive."""
        if v <= 0:
            raise ValueError("Burst spam rate must be positive")
        return v

    @validator("burst_duration")
    def burst_duration_must_be_positive(cls, v: float) -> float:
        """Validate that burst duration is positive."""
        if v <= 0:
            raise ValueError("Burst duration must be positive")
        return v


class MetricsConfig(BaseModel):
    """Configuration for metrics collection."""

    enabled: bool = Field(default=True, description="Enable metrics collection")
    collection_interval: float = Field(
        default=10.0, description="Metrics collection interval in seconds"
    )
    output_format: str = Field(
        default="json", description="Output format (json, csv, yaml)"
    )
    output_file: str | None = Field(default=None, description="Output file path")

    @validator("collection_interval")
    def interval_must_be_positive(cls, v: float) -> float:
        """Validate that collection interval is positive."""
        if v <= 0:
            raise ValueError("Collection interval must be positive")
        return v

    @validator("output_format")
    def output_format_must_be_valid(cls, v: str) -> str:
        """Validate that output format is supported."""
        valid_formats = {"json", "csv", "yaml"}
        if v not in valid_formats:
            raise ValueError(f"Output format must be one of {valid_formats}")
        return v


class Config(BaseModel):
    """Main configuration class for the Nostr Simulator."""

    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    antispam: AntiSpamConfig = Field(default_factory=AntiSpamConfig)
    attacks: AttackConfig = Field(default_factory=AttackConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)

    class Config:
        """Pydantic configuration."""

        extra = "forbid"
        validate_assignment = True


def load_config(config_path: str | Path) -> Config:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Loaded configuration object.

    Raises:
        FileNotFoundError: If the configuration file doesn't exist.
        ValueError: If the configuration is invalid.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file) as f:
        config_data = yaml.safe_load(f)

    return Config(**config_data)


def load_config_from_env(env_var: str = "NOSTR_SIM_CONFIG") -> Config:
    """Load configuration from environment variable.

    Args:
        env_var: Environment variable containing the config file path.

    Returns:
        Loaded configuration object or default configuration.
    """
    config_path = os.getenv(env_var)
    if config_path:
        return load_config(config_path)
    return Config()


def save_config(config: Config, config_path: str | Path) -> None:
    """Save configuration to a YAML file.

    Args:
        config: Configuration object to save.
        config_path: Path where to save the configuration file.
    """
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)

    with open(config_file, "w") as f:
        yaml.dump(config.dict(), f, default_flow_style=False, sort_keys=False)


def get_default_config() -> Config:
    """Get the default configuration.

    Returns:
        Default configuration object.
    """
    return Config()
