"""Tests for logging configuration module."""

import logging
import os
import tempfile
from unittest.mock import patch

import pytest
import yaml

from .logging_config import DEFAULT_LOGGING_CONFIG, get_logger, setup_logging


class TestSetupLogging:
    """Test cases for setup_logging function."""

    def test_setup_logging_with_valid_config_file(self):
        """Should set up logging from valid YAML configuration file."""
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"simple": {"format": "%(levelname)s - %(message)s"}},
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "simple"}
            },
            "root": {"level": "INFO", "handlers": ["console"]},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            setup_logging(config_path)

            # Verify logging is configured
            logger = logging.getLogger()
            assert logger.level == logging.INFO

        finally:
            os.unlink(config_path)

    def test_setup_logging_with_nonexistent_config_file(self):
        """Should fall back to basic configuration when config file doesn't exist."""
        nonexistent_path = "/path/that/does/not/exist.yaml"

        with patch("logging.basicConfig") as mock_basic_config:
            setup_logging(nonexistent_path, default_level=logging.DEBUG)

            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args
            assert call_args[1]["level"] == logging.DEBUG
            assert "%(asctime)s - %(name)s - %(levelname)s - %(message)s" in str(
                call_args[1]["format"]
            )

    def test_setup_logging_with_environment_variable_override(self):
        """Should use config path from environment variable when set."""
        config = DEFAULT_LOGGING_CONFIG

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            env_config_path = f.name

        try:
            with patch.dict(os.environ, {"LOG_CFG": env_config_path}):
                with patch("logging.config.dictConfig") as mock_dict_config:
                    setup_logging("default_path.yaml")

                    mock_dict_config.assert_called_once_with(config)

        finally:
            os.unlink(env_config_path)

    def test_setup_logging_with_invalid_yaml_file(self):
        """Should handle invalid YAML files gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_config_path = f.name

        try:
            with patch("logging.basicConfig"):
                # This should raise an exception during YAML parsing
                with pytest.raises(yaml.YAMLError):
                    setup_logging(invalid_config_path)

        finally:
            os.unlink(invalid_config_path)


class TestGetLogger:
    """Test cases for get_logger function."""

    def test_get_logger_returns_logger_instance(self):
        """Should return a logging.Logger instance with specified name."""
        logger_name = "test_logger"
        logger = get_logger(logger_name)

        assert isinstance(logger, logging.Logger)
        assert logger.name == logger_name

    def test_get_logger_returns_same_instance_for_same_name(self):
        """Should return the same logger instance for the same name."""
        logger_name = "same_logger"
        logger1 = get_logger(logger_name)
        logger2 = get_logger(logger_name)

        assert logger1 is logger2

    def test_get_logger_returns_different_instances_for_different_names(self):
        """Should return different logger instances for different names."""
        logger1 = get_logger("logger1")
        logger2 = get_logger("logger2")

        assert logger1 is not logger2
        assert logger1.name != logger2.name


class TestDefaultLoggingConfig:
    """Test cases for DEFAULT_LOGGING_CONFIG."""

    def test_default_config_structure(self):
        """Should have proper structure for logging configuration."""
        config = DEFAULT_LOGGING_CONFIG

        assert "version" in config
        assert config["version"] == 1
        assert "disable_existing_loggers" in config
        assert "formatters" in config
        assert "handlers" in config
        assert "loggers" in config
        assert "root" in config

    def test_default_config_formatters(self):
        """Should have required formatters defined."""
        formatters = DEFAULT_LOGGING_CONFIG["formatters"]

        assert "standard" in formatters
        assert "detailed" in formatters
        assert "json" in formatters

        # Check format strings contain required elements
        assert "%(asctime)s" in formatters["standard"]["format"]
        assert "%(levelname)s" in formatters["standard"]["format"]
        assert "%(name)s" in formatters["standard"]["format"]
        assert "%(message)s" in formatters["standard"]["format"]

    def test_default_config_handlers(self):
        """Should have required handlers defined."""
        handlers = DEFAULT_LOGGING_CONFIG["handlers"]

        assert "console" in handlers
        assert "file" in handlers
        assert "error_file" in handlers

        # Check console handler
        console = handlers["console"]
        assert console["class"] == "logging.StreamHandler"
        assert console["formatter"] == "standard"

        # Check file handlers
        file_handler = handlers["file"]
        assert file_handler["class"] == "logging.handlers.RotatingFileHandler"
        assert "maxBytes" in file_handler
        assert "backupCount" in file_handler

    def test_default_config_loggers(self):
        """Should have required loggers defined."""
        loggers = DEFAULT_LOGGING_CONFIG["loggers"]

        assert "nostr_simulator" in loggers
        assert "nostr_simulator.simulation" in loggers
        assert "nostr_simulator.agents" in loggers

        # Check main logger
        main_logger = loggers["nostr_simulator"]
        assert main_logger["level"] == "DEBUG"
        assert "console" in main_logger["handlers"]
        assert "file" in main_logger["handlers"]
        assert "error_file" in main_logger["handlers"]
        assert main_logger["propagate"] is False

    def test_default_config_root_logger(self):
        """Should have root logger properly configured."""
        root = DEFAULT_LOGGING_CONFIG["root"]

        assert root["level"] == "WARNING"
        assert "console" in root["handlers"]
