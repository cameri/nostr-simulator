"""Metrics collection and reporting for simulation."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Protocol

from ..config import MetricsConfig
from ..logging_config import get_logger
from .events import Event

if TYPE_CHECKING:
    pass


class EngineProtocol(Protocol):
    """Protocol for engine objects used in metrics collection."""

    def get_queue_size(self) -> int: ...
    def get_event_count(self) -> int: ...


class MetricsCollector:
    """Collects and manages simulation metrics."""

    def __init__(self, config: MetricsConfig) -> None:
        """Initialize the metrics collector.

        Args:
            config: Metrics configuration.
        """
        self.config = config
        self.logger = get_logger(__name__)

        # Metrics storage
        self.metrics: dict[str, Any] = {}
        self.time_series_metrics: dict[str, list[dict[str, Any]]] = {}

        # Collection state
        self.is_collecting = False
        self.last_collection_time = 0.0
        self.collection_count = 0

        # Initialize metric counters
        self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """Initialize metric counters."""
        self.metrics = {
            "simulation_start_time": None,
            "simulation_end_time": None,
            "total_events_processed": 0,
            "events_by_type": {},
            "average_queue_size": 0.0,
            "max_queue_size": 0,
            "performance": {"events_per_second": 0.0, "simulation_speed_factor": 0.0},
        }

        self.time_series_metrics = {
            "queue_size": [],
            "events_processed": [],
            "system_performance": [],
        }

    def start_collection(self) -> None:
        """Start metrics collection."""
        if self.config.enabled:
            self.is_collecting = True
            self.metrics["simulation_start_time"] = time.time()
            self.logger.info("Started metrics collection")

    def stop_collection(self) -> None:
        """Stop metrics collection."""
        if self.is_collecting:
            self.is_collecting = False
            self.metrics["simulation_end_time"] = time.time()
            self._finalize_metrics()
            self._export_metrics()
            self.logger.info("Stopped metrics collection")

    def should_collect(self, current_time: float) -> bool:
        """Check if metrics should be collected at current time.

        Args:
            current_time: Current simulation time.

        Returns:
            True if metrics should be collected.
        """
        if not self.is_collecting:
            return False

        return (
            current_time - self.last_collection_time
        ) >= self.config.collection_interval

    def collect_metrics(self, current_time: float, engine: EngineProtocol) -> None:
        """Collect metrics at current time.

        Args:
            current_time: Current simulation time.
            engine: Reference to the simulation engine.
        """
        if not self.should_collect(current_time):
            return

        self.last_collection_time = current_time
        self.collection_count += 1

        # Collect queue metrics
        queue_size = engine.get_queue_size()
        self.time_series_metrics["queue_size"].append(
            {"time": current_time, "value": queue_size}
        )

        # Update max queue size
        if queue_size > self.metrics["max_queue_size"]:
            self.metrics["max_queue_size"] = queue_size

        # Collect event processing metrics
        event_count = engine.get_event_count()
        self.time_series_metrics["events_processed"].append(
            {"time": current_time, "value": event_count}
        )

        # Collect performance metrics
        wall_time = time.time() - self.metrics["simulation_start_time"]
        if wall_time > 0:
            events_per_second = event_count / wall_time
            sim_speed = current_time / wall_time

            self.time_series_metrics["system_performance"].append(
                {
                    "time": current_time,
                    "events_per_second": events_per_second,
                    "simulation_speed_factor": sim_speed,
                }
            )

        self.logger.debug(f"Collected metrics at time {current_time}")

    def record_event_processed(self, event: Event) -> None:
        """Record that an event was processed.

        Args:
            event: The processed event.
        """
        if not self.is_collecting:
            return

        self.metrics["total_events_processed"] += 1

        # Count events by type
        event_type = event.event_type
        if event_type not in self.metrics["events_by_type"]:
            self.metrics["events_by_type"][event_type] = 0
        self.metrics["events_by_type"][event_type] += 1

    def get_current_metrics(self) -> dict[str, Any]:
        """Get current metrics snapshot.

        Returns:
            Dictionary of current metrics.
        """
        # Calculate dynamic metrics
        current_metrics = self.metrics.copy()

        # Calculate average queue size
        queue_sizes = [m["value"] for m in self.time_series_metrics["queue_size"]]
        if queue_sizes:
            current_metrics["average_queue_size"] = sum(queue_sizes) / len(queue_sizes)

        # Calculate final performance metrics
        if (
            self.metrics["simulation_start_time"]
            and self.metrics["simulation_end_time"]
        ):
            wall_time = (
                self.metrics["simulation_end_time"]
                - self.metrics["simulation_start_time"]
            )
            if wall_time > 0:
                events_per_second = self.metrics["total_events_processed"] / wall_time
                current_metrics["performance"]["events_per_second"] = events_per_second

        return current_metrics

    def _finalize_metrics(self) -> None:
        """Finalize metrics calculations."""
        # Calculate average queue size
        queue_sizes = [m["value"] for m in self.time_series_metrics["queue_size"]]
        if queue_sizes:
            self.metrics["average_queue_size"] = sum(queue_sizes) / len(queue_sizes)

        # Calculate final performance metrics
        if (
            self.metrics["simulation_start_time"]
            and self.metrics["simulation_end_time"]
        ):
            wall_time = (
                self.metrics["simulation_end_time"]
                - self.metrics["simulation_start_time"]
            )
            if wall_time > 0:
                events_per_second = self.metrics["total_events_processed"] / wall_time
                self.metrics["performance"]["events_per_second"] = events_per_second

                # Calculate simulation speed factor if we have time series data
                if self.time_series_metrics["system_performance"]:
                    last_perf = self.time_series_metrics["system_performance"][-1]
                    sim_time = last_perf["time"]
                    speed_factor = sim_time / wall_time
                    self.metrics["performance"][
                        "simulation_speed_factor"
                    ] = speed_factor

    def _export_metrics(self) -> None:
        """Export metrics to configured output."""
        if not self.config.output_file:
            return

        try:
            all_metrics = {
                "summary": self.get_current_metrics(),
                "time_series": self.time_series_metrics,
                "collection_info": {
                    "collection_count": self.collection_count,
                    "collection_interval": self.config.collection_interval,
                },
            }

            if self.config.output_format.lower() == "json":
                with open(self.config.output_file, "w") as f:
                    json.dump(all_metrics, f, indent=2, default=str)
            elif self.config.output_format.lower() == "yaml":
                import yaml

                with open(self.config.output_file, "w") as f:
                    yaml.dump(all_metrics, f, default_flow_style=False)
            else:
                self.logger.warning(
                    f"Unsupported output format: {self.config.output_format}"
                )

            self.logger.info(f"Exported metrics to {self.config.output_file}")

        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")

    def add_custom_metric(self, name: str, value: Any) -> None:
        """Add a custom metric.

        Args:
            name: Name of the metric.
            value: Value of the metric.
        """
        if "custom" not in self.metrics:
            self.metrics["custom"] = {}
        self.metrics["custom"][name] = value

    def increment_counter(self, name: str, amount: int = 1) -> None:
        """Increment a counter metric.

        Args:
            name: Name of the counter.
            amount: Amount to increment by.
        """
        if "counters" not in self.metrics:
            self.metrics["counters"] = {}
        if name not in self.metrics["counters"]:
            self.metrics["counters"][name] = 0
        self.metrics["counters"][name] += amount
