"""Tests for metrics collector module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from ..config import MetricsConfig
from .events import Event
from .metrics import MetricsCollector


class MockEngine:
    """Mock simulation engine for testing."""

    def __init__(self, queue_size: int = 0, event_count: int = 0):
        self.queue_size = queue_size
        self.event_count = event_count

    def get_queue_size(self) -> int:
        return self.queue_size

    def get_event_count(self) -> int:
        return self.event_count


class TestMetricsCollector:
    """Test cases for MetricsCollector class."""

    def test_init_with_enabled_config(self) -> None:
        """Should initialize with enabled metrics collection."""
        config = MetricsConfig(
            enabled=True,
            collection_interval=1.0,
            output_file="metrics.json",
            output_format="json",
        )

        collector = MetricsCollector(config)

        assert collector.config == config
        assert not collector.is_collecting
        assert collector.collection_count == 0
        assert "total_events_processed" in collector.metrics
        assert "queue_size" in collector.time_series_metrics

    def test_init_with_disabled_config(self) -> None:
        """Should initialize with disabled metrics collection."""
        config = MetricsConfig(enabled=False)

        collector = MetricsCollector(config)

        assert collector.config == config
        assert not collector.is_collecting

    def test_initialize_metrics_creates_expected_structure(self) -> None:
        """Should initialize metrics with expected structure."""
        config = MetricsConfig(enabled=True)
        collector = MetricsCollector(config)

        # Check summary metrics
        assert collector.metrics["simulation_start_time"] is None
        assert collector.metrics["simulation_end_time"] is None
        assert collector.metrics["total_events_processed"] == 0
        assert isinstance(collector.metrics["events_by_type"], dict)
        assert collector.metrics["average_queue_size"] == 0.0
        assert collector.metrics["max_queue_size"] == 0
        assert "performance" in collector.metrics

        # Check time series metrics
        assert "queue_size" in collector.time_series_metrics
        assert "events_processed" in collector.time_series_metrics
        assert "system_performance" in collector.time_series_metrics

    def test_start_collection_when_enabled(self) -> None:
        """Should start collection when enabled."""
        config = MetricsConfig(enabled=True)
        collector = MetricsCollector(config)

        with patch("time.time", return_value=1000.0):
            collector.start_collection()

        assert collector.is_collecting
        assert collector.metrics["simulation_start_time"] == 1000.0

    def test_start_collection_when_disabled(self) -> None:
        """Should not start collection when disabled."""
        config = MetricsConfig(enabled=False)
        collector = MetricsCollector(config)

        collector.start_collection()

        assert not collector.is_collecting
        assert collector.metrics["simulation_start_time"] is None

    def test_stop_collection(self) -> None:
        """Should stop collection and finalize metrics."""
        config = MetricsConfig(enabled=True)
        collector = MetricsCollector(config)
        collector.start_collection()

        with patch("time.time", return_value=2000.0):
            with patch.object(collector, "_finalize_metrics") as mock_finalize:
                with patch.object(collector, "_export_metrics") as mock_export:
                    collector.stop_collection()

        assert not collector.is_collecting
        assert collector.metrics["simulation_end_time"] == 2000.0
        mock_finalize.assert_called_once()
        mock_export.assert_called_once()

    def test_should_collect_when_not_collecting(self) -> None:
        """Should return False when not collecting."""
        config = MetricsConfig(enabled=True, collection_interval=1.0)
        collector = MetricsCollector(config)

        assert not collector.should_collect(5.0)

    def test_should_collect_when_interval_not_reached(self) -> None:
        """Should return False when collection interval not reached."""
        config = MetricsConfig(enabled=True, collection_interval=2.0)
        collector = MetricsCollector(config)
        collector.is_collecting = True
        collector.last_collection_time = 5.0

        assert not collector.should_collect(6.0)  # Only 1.0 elapsed, need 2.0

    def test_should_collect_when_interval_reached(self) -> None:
        """Should return True when collection interval reached."""
        config = MetricsConfig(enabled=True, collection_interval=2.0)
        collector = MetricsCollector(config)
        collector.is_collecting = True
        collector.last_collection_time = 5.0

        assert collector.should_collect(7.0)  # 2.0 elapsed, meets interval

    def test_collect_metrics_updates_time_series(self) -> None:
        """Should update time series metrics when collecting."""
        config = MetricsConfig(enabled=True, collection_interval=1.0)
        collector = MetricsCollector(config)
        collector.is_collecting = True

        mock_engine = MockEngine(queue_size=5, event_count=10)
        current_time = 3.0

        with patch("time.time", return_value=1000.0):
            collector.metrics["simulation_start_time"] = 999.0
            collector.collect_metrics(current_time, mock_engine)

        # Check queue size metrics
        assert len(collector.time_series_metrics["queue_size"]) == 1
        queue_metric = collector.time_series_metrics["queue_size"][0]
        assert queue_metric["time"] == current_time
        assert queue_metric["value"] == 5

        # Check max queue size
        assert collector.metrics["max_queue_size"] == 5

        # Check events processed metrics
        assert len(collector.time_series_metrics["events_processed"]) == 1
        event_metric = collector.time_series_metrics["events_processed"][0]
        assert event_metric["time"] == current_time
        assert event_metric["value"] == 10

    def test_collect_metrics_updates_max_queue_size(self) -> None:
        """Should update max queue size when new maximum is reached."""
        config = MetricsConfig(enabled=True, collection_interval=1.0)
        collector = MetricsCollector(config)
        collector.is_collecting = True
        collector.metrics["max_queue_size"] = 3

        mock_engine = MockEngine(queue_size=7, event_count=0)

        collector.collect_metrics(2.0, mock_engine)

        assert collector.metrics["max_queue_size"] == 7

    def test_collect_metrics_skips_when_should_not_collect(self) -> None:
        """Should skip collection when should_collect returns False."""
        config = MetricsConfig(enabled=True, collection_interval=2.0)
        collector = MetricsCollector(config)
        collector.is_collecting = True
        collector.last_collection_time = 5.0

        mock_engine = MockEngine()

        collector.collect_metrics(6.0, mock_engine)  # Too soon

        assert len(collector.time_series_metrics["queue_size"]) == 0

    def test_record_event_processed_when_collecting(self) -> None:
        """Should record event processing when collecting."""
        config = MetricsConfig(enabled=True)
        collector = MetricsCollector(config)
        collector.is_collecting = True

        event = Event(event_type="test_event", time=1.0, priority=1, data={})

        collector.record_event_processed(event)

        assert collector.metrics["total_events_processed"] == 1
        assert collector.metrics["events_by_type"]["test_event"] == 1

    def test_record_event_processed_when_not_collecting(self) -> None:
        """Should not record event processing when not collecting."""
        config = MetricsConfig(enabled=True)
        collector = MetricsCollector(config)
        collector.is_collecting = False

        event = Event(event_type="test_event", time=1.0, priority=1, data={})

        collector.record_event_processed(event)

        assert collector.metrics["total_events_processed"] == 0

    def test_record_multiple_events_by_type(self) -> None:
        """Should correctly count events by type."""
        config = MetricsConfig(enabled=True)
        collector = MetricsCollector(config)
        collector.is_collecting = True

        events = [
            Event(event_type="type_a", time=1.0, priority=1, data={}),
            Event(event_type="type_b", time=2.0, priority=1, data={}),
            Event(event_type="type_a", time=3.0, priority=1, data={}),
            Event(event_type="type_a", time=4.0, priority=1, data={}),
            Event(event_type="type_b", time=5.0, priority=1, data={}),
        ]

        for event in events:
            collector.record_event_processed(event)

        assert collector.metrics["total_events_processed"] == 5
        assert collector.metrics["events_by_type"]["type_a"] == 3
        assert collector.metrics["events_by_type"]["type_b"] == 2

    def test_get_current_metrics_with_queue_data(self) -> None:
        """Should calculate average queue size in current metrics."""
        config = MetricsConfig(enabled=True)
        collector = MetricsCollector(config)

        # Add some queue size data
        collector.time_series_metrics["queue_size"] = [
            {"time": 1.0, "value": 2},
            {"time": 2.0, "value": 4},
            {"time": 3.0, "value": 6},
        ]

        metrics = collector.get_current_metrics()

        assert metrics["average_queue_size"] == 4.0  # (2+4+6)/3

    def test_export_metrics_json_format(self) -> None:
        """Should export metrics in JSON format."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file = f.name

        try:
            config = MetricsConfig(
                enabled=True, output_file=output_file, output_format="json"
            )
            collector = MetricsCollector(config)
            collector.metrics["total_events_processed"] = 100
            collector._export_metrics()

            # Verify file was created and contains expected data
            assert Path(output_file).exists()

            with open(output_file) as f:
                data = json.load(f)

            assert "summary" in data
            assert "time_series" in data
            assert "collection_info" in data
            assert data["summary"]["total_events_processed"] == 100

        finally:
            Path(output_file).unlink(missing_ok=True)

    def test_add_custom_metric(self) -> None:
        """Should add custom metrics."""
        config = MetricsConfig(enabled=True)
        collector = MetricsCollector(config)

        collector.add_custom_metric("custom_value", 42)
        collector.add_custom_metric("custom_string", "test")

        assert "custom" in collector.metrics
        assert collector.metrics["custom"]["custom_value"] == 42
        assert collector.metrics["custom"]["custom_string"] == "test"

    def test_increment_counter(self) -> None:
        """Should increment counter metrics."""
        config = MetricsConfig(enabled=True)
        collector = MetricsCollector(config)

        collector.increment_counter("test_counter")
        collector.increment_counter("test_counter", 5)
        collector.increment_counter("other_counter", 3)

        assert "counters" in collector.metrics
        assert collector.metrics["counters"]["test_counter"] == 6  # 1 + 5
        assert collector.metrics["counters"]["other_counter"] == 3

    def test_finalize_metrics_calculates_performance(self) -> None:
        """Should calculate performance metrics during finalization."""
        config = MetricsConfig(enabled=True)
        collector = MetricsCollector(config)

        # Set up test data
        collector.metrics["simulation_start_time"] = 1000.0
        collector.metrics["simulation_end_time"] = 1002.0  # 2 seconds
        collector.metrics["total_events_processed"] = 200

        collector.time_series_metrics["queue_size"] = [
            {"time": 1.0, "value": 5},
            {"time": 2.0, "value": 15},
        ]

        collector.time_series_metrics["system_performance"] = [
            {"time": 10.0, "simulation_speed_factor": 5.0}
        ]

        collector._finalize_metrics()

        assert collector.metrics["average_queue_size"] == 10.0  # (5+15)/2
        assert collector.metrics["performance"]["events_per_second"] == 100.0  # 200/2
        assert collector.metrics["performance"]["simulation_speed_factor"] == 5.0
