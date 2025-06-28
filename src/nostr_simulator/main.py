"""Main entry point for the Nostr Simulator."""

import sys

from .agents.base import AgentManager
from .config import Config, load_config_from_env
from .logging_config import get_logger, setup_logging
from .simulation.engine import SimulationEngine


def create_simulation(config: Config) -> SimulationEngine:
    """Create and configure a simulation engine.

    Args:
        config: Simulation configuration.

    Returns:
        Configured simulation engine.
    """
    # Create simulation engine
    engine = SimulationEngine(config)

    # Create agent manager
    AgentManager(engine)

    # TODO: Create and register agents based on configuration
    # This will be implemented in Phase 2

    return engine


def main() -> None:
    """Main entry point for the simulator."""
    # Set up logging
    setup_logging()
    logger = get_logger(__name__)

    logger.info("Starting Nostr Simulator")

    try:
        # Load configuration
        config = load_config_from_env()
        logger.info("Loaded configuration")

        # Create simulation
        simulation = create_simulation(config)
        logger.info("Created simulation engine")

        # Run simulation
        simulation.run()

        # Get final metrics
        metrics = simulation.get_metrics()
        logger.info(
            f"Simulation completed. Processed {metrics.get('total_events_processed', 0)} events"
        )

    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
