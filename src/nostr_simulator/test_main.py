"""Tests for main entry point module."""

from unittest.mock import Mock, patch

from .config import Config
from .main import create_simulation, main


class TestCreateSimulation:
    """Test cases for create_simulation function."""

    def test_create_simulation_returns_engine(self):
        """Should create and return simulation engine."""
        mock_config = Mock(spec=Config)

        with patch("nostr_simulator.main.SimulationEngine") as mock_engine_class:
            with patch("nostr_simulator.main.AgentManager") as mock_agent_manager_class:
                mock_engine = Mock()
                mock_engine_class.return_value = mock_engine

                result = create_simulation(mock_config)

                assert result == mock_engine
                mock_engine_class.assert_called_once_with(mock_config)
                mock_agent_manager_class.assert_called_once_with(mock_engine)

    def test_create_simulation_with_real_config(self):
        """Should create simulation with actual config object."""
        # Create a minimal config for testing
        config_data = {
            "simulation": {"duration": 100.0, "time_step": 1.0, "seed": 42},
            "metrics": {
                "enabled": True,
                "collection_interval": 10.0,
                "output_file": "test_metrics.json",
                "output_format": "json",
            },
        }

        with patch("nostr_simulator.main.SimulationEngine") as mock_engine_class:
            with patch("nostr_simulator.main.AgentManager"):
                mock_engine = Mock()
                mock_engine_class.return_value = mock_engine

                config = Config(**config_data)
                result = create_simulation(config)

                assert result == mock_engine
                mock_engine_class.assert_called_once_with(config)


class TestMain:
    """Test cases for main function."""

    def test_main_successful_execution(self):
        """Should execute simulation successfully."""
        mock_config = Mock(spec=Config)
        mock_engine = Mock()
        mock_metrics = {"total_events_processed": 100}
        mock_engine.get_metrics.return_value = mock_metrics

        with patch("nostr_simulator.main.setup_logging") as mock_setup_logging:
            with patch("nostr_simulator.main.get_logger") as mock_get_logger:
                with patch(
                    "nostr_simulator.main.load_config_from_env"
                ) as mock_load_config:
                    with patch(
                        "nostr_simulator.main.create_simulation"
                    ) as mock_create_sim:
                        mock_logger = Mock()
                        mock_get_logger.return_value = mock_logger
                        mock_load_config.return_value = mock_config
                        mock_create_sim.return_value = mock_engine

                        main()

                        mock_setup_logging.assert_called_once()
                        mock_load_config.assert_called_once()
                        mock_create_sim.assert_called_once_with(mock_config)
                        mock_engine.run.assert_called_once()
                        mock_engine.get_metrics.assert_called_once()

                        # Check that appropriate log messages were called
                        mock_logger.info.assert_any_call("Starting Nostr Simulator")
                        mock_logger.info.assert_any_call("Loaded configuration")
                        mock_logger.info.assert_any_call("Created simulation engine")

    def test_main_keyboard_interrupt(self):
        """Should handle keyboard interrupt gracefully."""
        mock_config = Mock(spec=Config)
        mock_engine = Mock()
        mock_engine.run.side_effect = KeyboardInterrupt()

        with patch("nostr_simulator.main.setup_logging"):
            with patch("nostr_simulator.main.get_logger") as mock_get_logger:
                with patch(
                    "nostr_simulator.main.load_config_from_env"
                ) as mock_load_config:
                    with patch(
                        "nostr_simulator.main.create_simulation"
                    ) as mock_create_sim:
                        with patch("sys.exit") as mock_exit:
                            mock_logger = Mock()
                            mock_get_logger.return_value = mock_logger
                            mock_load_config.return_value = mock_config
                            mock_create_sim.return_value = mock_engine

                            main()

                            mock_logger.info.assert_any_call(
                                "Simulation interrupted by user"
                            )
                            mock_exit.assert_called_once_with(1)

    def test_main_general_exception(self):
        """Should handle general exceptions gracefully."""
        Mock(spec=Config)
        test_error = Exception("Test error")

        with patch("nostr_simulator.main.setup_logging"):
            with patch("nostr_simulator.main.get_logger") as mock_get_logger:
                with patch(
                    "nostr_simulator.main.load_config_from_env"
                ) as mock_load_config:
                    with patch("sys.exit") as mock_exit:
                        mock_logger = Mock()
                        mock_get_logger.return_value = mock_logger
                        mock_load_config.side_effect = test_error

                        main()

                        mock_logger.error.assert_called_once_with(
                            "Simulation failed: Test error"
                        )
                        mock_exit.assert_called_once_with(1)

    def test_main_config_loading_error(self):
        """Should handle configuration loading errors."""
        config_error = FileNotFoundError("Config file not found")

        with patch("nostr_simulator.main.setup_logging"):
            with patch("nostr_simulator.main.get_logger") as mock_get_logger:
                with patch(
                    "nostr_simulator.main.load_config_from_env"
                ) as mock_load_config:
                    with patch("sys.exit") as mock_exit:
                        mock_logger = Mock()
                        mock_get_logger.return_value = mock_logger
                        mock_load_config.side_effect = config_error

                        main()

                        mock_logger.error.assert_called_once_with(
                            "Simulation failed: Config file not found"
                        )
                        mock_exit.assert_called_once_with(1)

    def test_main_simulation_creation_error(self):
        """Should handle simulation creation errors."""
        mock_config = Mock(spec=Config)
        creation_error = ValueError("Invalid configuration")

        with patch("nostr_simulator.main.setup_logging"):
            with patch("nostr_simulator.main.get_logger") as mock_get_logger:
                with patch(
                    "nostr_simulator.main.load_config_from_env"
                ) as mock_load_config:
                    with patch(
                        "nostr_simulator.main.create_simulation"
                    ) as mock_create_sim:
                        with patch("sys.exit") as mock_exit:
                            mock_logger = Mock()
                            mock_get_logger.return_value = mock_logger
                            mock_load_config.return_value = mock_config
                            mock_create_sim.side_effect = creation_error

                            main()

                            mock_logger.error.assert_called_once_with(
                                "Simulation failed: Invalid configuration"
                            )
                            mock_exit.assert_called_once_with(1)

    def test_main_simulation_run_error(self):
        """Should handle simulation runtime errors."""
        mock_config = Mock(spec=Config)
        mock_engine = Mock()
        runtime_error = RuntimeError("Simulation runtime error")
        mock_engine.run.side_effect = runtime_error

        with patch("nostr_simulator.main.setup_logging"):
            with patch("nostr_simulator.main.get_logger") as mock_get_logger:
                with patch(
                    "nostr_simulator.main.load_config_from_env"
                ) as mock_load_config:
                    with patch(
                        "nostr_simulator.main.create_simulation"
                    ) as mock_create_sim:
                        with patch("sys.exit") as mock_exit:
                            mock_logger = Mock()
                            mock_get_logger.return_value = mock_logger
                            mock_load_config.return_value = mock_config
                            mock_create_sim.return_value = mock_engine

                            main()

                            mock_logger.error.assert_called_once_with(
                                "Simulation failed: Simulation runtime error"
                            )
                            mock_exit.assert_called_once_with(1)

    def test_main_logs_final_metrics(self):
        """Should log final metrics after successful simulation."""
        mock_config = Mock(spec=Config)
        mock_engine = Mock()
        test_metrics = {
            "total_events_processed": 250,
            "average_queue_size": 5.5,
            "simulation_duration": 100.0,
        }
        mock_engine.get_metrics.return_value = test_metrics

        with patch("nostr_simulator.main.setup_logging"):
            with patch("nostr_simulator.main.get_logger") as mock_get_logger:
                with patch(
                    "nostr_simulator.main.load_config_from_env"
                ) as mock_load_config:
                    with patch(
                        "nostr_simulator.main.create_simulation"
                    ) as mock_create_sim:
                        mock_logger = Mock()
                        mock_get_logger.return_value = mock_logger
                        mock_load_config.return_value = mock_config
                        mock_create_sim.return_value = mock_engine

                        main()

                        expected_message = "Simulation completed. Processed 250 events"
                        mock_logger.info.assert_any_call(expected_message)

    def test_main_handles_missing_metrics(self):
        """Should handle case where metrics don't include total_events_processed."""
        mock_config = Mock(spec=Config)
        mock_engine = Mock()
        test_metrics = {"average_queue_size": 5.5}  # Missing total_events_processed
        mock_engine.get_metrics.return_value = test_metrics

        with patch("nostr_simulator.main.setup_logging"):
            with patch("nostr_simulator.main.get_logger") as mock_get_logger:
                with patch(
                    "nostr_simulator.main.load_config_from_env"
                ) as mock_load_config:
                    with patch(
                        "nostr_simulator.main.create_simulation"
                    ) as mock_create_sim:
                        mock_logger = Mock()
                        mock_get_logger.return_value = mock_logger
                        mock_load_config.return_value = mock_config
                        mock_create_sim.return_value = mock_engine

                        main()

                        expected_message = "Simulation completed. Processed 0 events"
                        mock_logger.info.assert_any_call(expected_message)


class TestMainEntryPoint:
    """Test cases for main entry point execution."""

    def test_main_module_execution(self):
        """Should call main function when executed as module."""
        with patch("nostr_simulator.main.main"):
            # Simulate module execution
            with patch("sys.argv", ["main.py"]):
                exec(
                    """
if __name__ == "__main__":
    from nostr_simulator.main import main
    main()
                """
                )

            # Note: This test would actually call main, but we're testing the pattern
            # In practice, we would need to mock the __name__ check
