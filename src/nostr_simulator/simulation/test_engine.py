"""Tests for simulation engine."""

import time
from unittest.mock import MagicMock, patch

import pytest

from ..config import Config, SimulationConfig
from .engine import SimulationEngine
from .events import Event, EventHandler


class TestEventHandler(EventHandler):
    """Test event handler for testing purposes."""

    def __init__(self) -> None:
        self.handled_events: list[Event] = []
        self.can_handle_types = {"test_event"}

    def handle_event(self, event: Event) -> list[Event]:
        """Handle a test event."""
        self.handled_events.append(event)
        # Create a follow-up event
        if event.event_type == "test_event":
            return [
                Event(
                    time=event.time + 1.0,
                    priority=0,
                    event_type="follow_up_event",
                    data={"original_id": event.event_id},
                )
            ]
        return []

    def can_handle(self, event_type: str) -> bool:
        """Check if can handle event type."""
        return event_type in self.can_handle_types


class TestSimulationEngine:
    """Test SimulationEngine functionality."""

    def test_initialization(self) -> None:
        """Test that engine initializes correctly."""
        config = Config(simulation=SimulationConfig(duration=100.0))
        engine = SimulationEngine(config)

        assert engine.config == config
        assert engine.current_time == 0.0
        assert engine.event_count == 0
        assert not engine.is_running
        assert engine.duration == 100.0

    def test_schedule_event(self) -> None:
        """Test event scheduling."""
        config = Config()
        engine = SimulationEngine(config)

        # Schedule an event
        event_id = engine.schedule_event(
            delay=5.0, event_type="test_event", data={"test": "data"}
        )

        assert event_id is not None
        assert engine.get_queue_size() == 1

    def test_schedule_absolute_event(self) -> None:
        """Test absolute time event scheduling."""
        config = Config()
        engine = SimulationEngine(config)

        # Schedule an event at absolute time
        event_id = engine.schedule_absolute_event(time=10.0, event_type="test_event")

        assert event_id is not None
        assert engine.get_queue_size() == 1

    def test_cancel_event(self) -> None:
        """Test event cancellation."""
        config = Config()
        engine = SimulationEngine(config)

        # Schedule and cancel an event
        event_id = engine.schedule_event(5.0, "test_event")
        assert engine.cancel_event(event_id)

        # Try to cancel non-existent event
        assert not engine.cancel_event("non_existent_id")

    def test_register_event_handler(self) -> None:
        """Test event handler registration."""
        config = Config()
        engine = SimulationEngine(config)
        handler = TestEventHandler()

        engine.register_event_handler("test_event", handler)

        # Schedule and process an event to test handler
        engine.schedule_event(1.0, "test_event", data={"test": True})

        # Run for a short time to process the event
        engine.duration = 2.0
        engine.run()

        # Check that handler processed the event
        assert len(handler.handled_events) == 1
        assert handler.handled_events[0].event_type == "test_event"

    def test_simulation_time_limit(self) -> None:
        """Test that simulation stops at time limit."""
        config = Config(simulation=SimulationConfig(duration=10.0))
        engine = SimulationEngine(config)

        # Schedule events beyond the time limit
        engine.schedule_event(5.0, "test_event")
        engine.schedule_event(15.0, "test_event")  # This should not be processed

        engine.run()

        # Should stop at duration limit
        assert engine.current_time <= 10.0

    def test_event_count_limit(self) -> None:
        """Test that simulation stops at event count limit."""
        config = Config(simulation=SimulationConfig(max_events=2))
        engine = SimulationEngine(config)

        # Schedule multiple events
        engine.schedule_event(1.0, "test_event")
        engine.schedule_event(2.0, "test_event")
        engine.schedule_event(3.0, "test_event")

        engine.run()

        # Should stop after processing 2 events
        assert engine.event_count == 2

    def test_stop_simulation(self) -> None:
        """Test stopping simulation manually."""
        config = Config(simulation=SimulationConfig(duration=100.0))
        engine = SimulationEngine(config)

        # Start simulation in background and stop it
        def stop_after_delay() -> None:
            time.sleep(0.1)  # Short delay
            engine.stop()

        import threading

        stop_thread = threading.Thread(target=stop_after_delay)
        stop_thread.start()

        engine.run()
        stop_thread.join()

        assert not engine.is_running

    def test_get_current_time(self) -> None:
        """Test getting current simulation time."""
        config = Config()
        engine = SimulationEngine(config)

        assert engine.get_current_time() == 0.0

        # Schedule and process an event
        engine.schedule_event(5.0, "test_event")
        engine.duration = 10.0
        engine.run()

        assert engine.get_current_time() >= 5.0

    def test_get_metrics(self) -> None:
        """Test getting simulation metrics."""
        config = Config()
        engine = SimulationEngine(config)

        metrics = engine.get_metrics()
        assert isinstance(metrics, dict)
        assert "total_events_processed" in metrics

    def test_empty_event_queue(self) -> None:
        """Test simulation with no events."""
        config = Config(simulation=SimulationConfig(duration=10.0))
        engine = SimulationEngine(config)

        # Run with no scheduled events
        engine.run()

        # Should complete immediately
        assert engine.event_count == 0

    @patch("time.time")
    def test_performance_metrics(self, mock_time: MagicMock) -> None:
        """Test that performance metrics are calculated correctly."""
        # Mock wall clock time
        mock_time.side_effect = [0.0, 1.0]  # 1 second wall time

        config = Config(simulation=SimulationConfig(duration=5.0))
        engine = SimulationEngine(config)

        # Schedule a few events
        engine.schedule_event(1.0, "test_event")
        engine.schedule_event(2.0, "test_event")

        engine.run()

        # Performance metrics should be calculated
        assert engine.start_wall_time == 0.0
        assert engine.end_wall_time == 1.0


if __name__ == "__main__":
    pytest.main([__file__])
