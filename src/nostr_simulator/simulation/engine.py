"""Main simulation engine for discrete event simulation."""

from __future__ import annotations

import time
from typing import Any

from ..config import Config
from ..logging_config import get_logger
from .events import Event, EventDispatcher, EventHandler, EventQueue
from .metrics import MetricsCollector
from .time_manager import TimeManager


class SimulationEngine:
    """Main simulation engine that orchestrates the discrete event simulation."""

    def __init__(self, config: Config) -> None:
        """Initialize the simulation engine.

        Args:
            config: Simulation configuration.
        """
        self.config = config
        self.logger = get_logger(__name__)

        # Core components
        self.event_queue = EventQueue()
        self.event_dispatcher = EventDispatcher()
        self.time_manager = TimeManager(config.simulation.time_step)
        self.metrics_collector = MetricsCollector(config.metrics)

        # Simulation state
        self.is_running = False
        self.current_time = 0.0
        self.event_count = 0
        self.max_events = config.simulation.max_events
        self.duration = config.simulation.duration

        # Performance tracking
        self.start_wall_time: float | None = None
        self.end_wall_time: float | None = None

        self.logger.info("Simulation engine initialized")

    def register_event_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register an event handler for a specific event type.

        Args:
            event_type: The event type to handle.
            handler: The handler to register.
        """
        self.event_dispatcher.register_handler(event_type, handler)
        self.logger.debug(f"Registered handler for event type: {event_type}")

    def register_catch_all_handler(self, handler: EventHandler) -> None:
        """Register a catch-all event handler.

        Args:
            handler: The handler to register.
        """
        self.event_dispatcher.register_catch_all_handler(handler)
        self.logger.debug("Registered catch-all handler")

    def schedule_event(
        self,
        delay: float,
        event_type: str,
        priority: int = 0,
        data: dict[str, Any] | None = None,
        source_id: str | None = None,
        target_id: str | None = None,
    ) -> str:
        """Schedule an event to occur after a delay.

        Args:
            delay: Delay from current time when event should occur.
            event_type: Type of the event.
            priority: Event priority (lower = higher priority).
            data: Additional event data.
            source_id: ID of the event source.
            target_id: ID of the event target.

        Returns:
            The unique event ID.
        """
        event_time = self.current_time + delay
        return self.event_queue.schedule_event(
            time=event_time,
            event_type=event_type,
            priority=priority,
            data=data,
            source_id=source_id,
            target_id=target_id,
        )

    def schedule_absolute_event(
        self,
        time: float,
        event_type: str,
        priority: int = 0,
        data: dict[str, Any] | None = None,
        source_id: str | None = None,
        target_id: str | None = None,
    ) -> str:
        """Schedule an event to occur at an absolute time.

        Args:
            time: Absolute time when event should occur.
            event_type: Type of the event.
            priority: Event priority (lower = higher priority).
            data: Additional event data.
            source_id: ID of the event source.
            target_id: ID of the event target.

        Returns:
            The unique event ID.
        """
        return self.event_queue.schedule_event(
            time=time,
            event_type=event_type,
            priority=priority,
            data=data,
            source_id=source_id,
            target_id=target_id,
        )

    def cancel_event(self, event_id: str) -> bool:
        """Cancel a scheduled event.

        Args:
            event_id: ID of the event to cancel.

        Returns:
            True if event was found and cancelled.
        """
        return self.event_queue.cancel_event(event_id)

    def run(self) -> None:
        """Run the simulation until completion."""
        if self.is_running:
            self.logger.warning("Simulation is already running")
            return

        self.logger.info("Starting simulation")
        self.is_running = True
        self.start_wall_time = time.time()

        # Initialize metrics collection
        self.metrics_collector.start_collection()

        try:
            self._simulation_loop()
        except KeyboardInterrupt:
            self.logger.info("Simulation interrupted by user")
        except Exception as e:
            self.logger.error(f"Simulation error: {e}")
            raise
        finally:
            self._cleanup()

    def stop(self) -> None:
        """Stop the simulation."""
        if not self.is_running:
            return

        self.logger.info("Stopping simulation")
        self.is_running = False

    def _simulation_loop(self) -> None:
        """Main simulation loop."""
        self.logger.info(f"Running simulation for {self.duration} seconds")

        while self.is_running and self._should_continue():
            next_event = self.event_queue.get_next_event()

            if next_event is None:
                self.logger.info("No more events to process")
                break

            # Check if the next event exceeds the duration limit
            if next_event.time >= self.duration:
                self.logger.info(f"Next event at time {next_event.time} exceeds duration limit {self.duration}")
                break

            # Update simulation time
            self.current_time = next_event.time
            self.time_manager.set_current_time(self.current_time)

            # Process the event
            self._process_event(next_event)

            # Update event count
            self.event_count += 1

            # Check for periodic tasks
            self._check_periodic_tasks()

    def _process_event(self, event: Event) -> None:
        """Process a single event.

        Args:
            event: The event to process.
        """
        self.logger.debug(
            f"Processing event {event.event_id} at time {event.time}: {event.event_type}"
        )

        # Dispatch event to handlers
        new_events = self.event_dispatcher.dispatch_event(event)

        # Schedule any new events
        for new_event in new_events:
            self.event_queue.schedule_event(
                time=new_event.time,
                event_type=new_event.event_type,
                priority=new_event.priority,
                data=new_event.data,
                source_id=new_event.source_id,
                target_id=new_event.target_id,
            )

        # Record event processing in metrics
        self.metrics_collector.record_event_processed(event)

    def _should_continue(self) -> bool:
        """Check if simulation should continue.

        Returns:
            True if simulation should continue.
        """
        # Check time limit
        if self.current_time >= self.duration:
            self.logger.info(f"Simulation time limit reached: {self.current_time}")
            return False

        # Check event count limit
        if self.max_events and self.event_count >= self.max_events:
            self.logger.info(f"Event count limit reached: {self.event_count}")
            return False

        return True

    def _check_periodic_tasks(self) -> None:
        """Check and execute periodic tasks."""
        # Collect metrics if needed
        if self.metrics_collector.should_collect(self.current_time):
            self.metrics_collector.collect_metrics(self.current_time, self)

    def _cleanup(self) -> None:
        """Clean up simulation state."""
        self.is_running = False
        self.end_wall_time = time.time()

        # Stop metrics collection
        self.metrics_collector.stop_collection()

        # Log final statistics
        if self.start_wall_time and self.end_wall_time:
            wall_time = self.end_wall_time - self.start_wall_time
            self.logger.info(f"Simulation completed in {wall_time:.2f} wall seconds")
            self.logger.info(f"Simulated {self.current_time:.2f} simulation seconds")
            self.logger.info(f"Processed {self.event_count} events")

            if wall_time > 0:
                events_per_second = self.event_count / wall_time
                sim_speed = self.current_time / wall_time
                self.logger.info(f"Performance: {events_per_second:.2f} events/sec")
                self.logger.info(f"Simulation speed: {sim_speed:.2f}x real-time")

    def get_current_time(self) -> float:
        """Get the current simulation time.

        Returns:
            Current simulation time.
        """
        return self.current_time

    def get_event_count(self) -> int:
        """Get the number of events processed.

        Returns:
            Number of events processed.
        """
        return self.event_count

    def get_queue_size(self) -> int:
        """Get the current event queue size.

        Returns:
            Number of events in the queue.
        """
        return self.event_queue.size()

    def get_metrics(self) -> dict[str, Any]:
        """Get current simulation metrics.

        Returns:
            Dictionary of current metrics.
        """
        return self.metrics_collector.get_current_metrics()
