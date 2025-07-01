"""Tests for the core metrics system."""

import time

from ..anti_spam.base import StrategyResult
from ..protocol.events import NostrEvent, NostrEventKind
from ..protocol.keys import NostrKeyPair
from .core_metrics import (
    CoreMetricsCollector,
    FalsePositiveNegativeStats,
    FalsePositiveNegativeTracker,
    LatencyMeasurement,
    RelayLoadMonitor,
    ResilienceMetrics,
    SpamReductionCalculator,
)


class TestFalsePositiveNegativeStats:
    """Test the FalsePositiveNegativeStats class."""

    def test_precision_calculation(self) -> None:
        """Test precision calculation."""
        stats = FalsePositiveNegativeStats(true_positives=8, false_positives=2)
        assert stats.precision == 0.8  # 8 / (8 + 2)

    def test_precision_zero_denominator(self) -> None:
        """Test precision with zero denominator."""
        stats = FalsePositiveNegativeStats()
        assert stats.precision == 0.0

    def test_recall_calculation(self) -> None:
        """Test recall calculation."""
        stats = FalsePositiveNegativeStats(true_positives=8, false_negatives=2)
        assert stats.recall == 0.8  # 8 / (8 + 2)

    def test_recall_zero_denominator(self) -> None:
        """Test recall with zero denominator."""
        stats = FalsePositiveNegativeStats()
        assert stats.recall == 0.0

    def test_f1_score_calculation(self) -> None:
        """Test F1 score calculation."""
        stats = FalsePositiveNegativeStats(
            true_positives=8, false_positives=2, false_negatives=1
        )
        precision = 8 / 10  # 0.8
        recall = 8 / 9  # ~0.889
        expected_f1 = 2 * precision * recall / (precision + recall)
        assert abs(stats.f1_score - expected_f1) < 1e-6

    def test_f1_score_zero_denominator(self) -> None:
        """Test F1 score with zero denominator."""
        stats = FalsePositiveNegativeStats()
        assert stats.f1_score == 0.0

    def test_accuracy_calculation(self) -> None:
        """Test accuracy calculation."""
        stats = FalsePositiveNegativeStats(
            true_positives=8, true_negatives=12, false_positives=2, false_negatives=3
        )
        assert stats.accuracy == 0.8  # (8 + 12) / (8 + 12 + 2 + 3)

    def test_accuracy_zero_denominator(self) -> None:
        """Test accuracy with zero denominator."""
        stats = FalsePositiveNegativeStats()
        assert stats.accuracy == 0.0


class TestFalsePositiveNegativeTracker:
    """Test the FalsePositiveNegativeTracker class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.tracker = FalsePositiveNegativeTracker()
        self.keypair = NostrKeyPair.generate()

    def create_test_event(self, content: str = "test") -> NostrEvent:
        """Create a test event."""
        return NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content=content,
            created_at=int(time.time()),
            pubkey=self.keypair.public_key,
        )

    def test_label_event(self) -> None:
        """Test event labeling."""
        event = self.create_test_event()
        self.tracker.label_event(event, True)
        assert self.tracker.event_labels[event.id] is True

    def test_record_strategy_decision_true_positive(self) -> None:
        """Test recording a true positive decision."""
        event = self.create_test_event()
        self.tracker.label_event(event, True)  # Spam

        result = StrategyResult(allowed=False, reason="blocked spam")
        self.tracker.record_strategy_decision("test_strategy", event, result)

        stats = self.tracker.get_stats("test_strategy")
        assert stats.true_positives == 1
        assert stats.false_positives == 0
        assert stats.true_negatives == 0
        assert stats.false_negatives == 0

    def test_record_strategy_decision_false_positive(self) -> None:
        """Test recording a false positive decision."""
        event = self.create_test_event()
        self.tracker.label_event(event, False)  # Legitimate

        result = StrategyResult(allowed=False, reason="blocked legitimate")
        self.tracker.record_strategy_decision("test_strategy", event, result)

        stats = self.tracker.get_stats("test_strategy")
        assert stats.true_positives == 0
        assert stats.false_positives == 1
        assert stats.true_negatives == 0
        assert stats.false_negatives == 0

    def test_record_strategy_decision_true_negative(self) -> None:
        """Test recording a true negative decision."""
        event = self.create_test_event()
        self.tracker.label_event(event, False)  # Legitimate

        result = StrategyResult(allowed=True, reason="allowed legitimate")
        self.tracker.record_strategy_decision("test_strategy", event, result)

        stats = self.tracker.get_stats("test_strategy")
        assert stats.true_positives == 0
        assert stats.false_positives == 0
        assert stats.true_negatives == 1
        assert stats.false_negatives == 0

    def test_record_strategy_decision_false_negative(self) -> None:
        """Test recording a false negative decision."""
        event = self.create_test_event()
        self.tracker.label_event(event, True)  # Spam

        result = StrategyResult(allowed=True, reason="allowed spam")
        self.tracker.record_strategy_decision("test_strategy", event, result)

        stats = self.tracker.get_stats("test_strategy")
        assert stats.true_positives == 0
        assert stats.false_positives == 0
        assert stats.true_negatives == 0
        assert stats.false_negatives == 1

    def test_overall_stats(self) -> None:
        """Test overall statistics tracking."""
        event1 = self.create_test_event("spam1")
        event2 = self.create_test_event("legitimate1")

        self.tracker.label_event(event1, True)  # Spam
        self.tracker.label_event(event2, False)  # Legitimate

        result1 = StrategyResult(allowed=False, reason="blocked spam")
        result2 = StrategyResult(allowed=True, reason="allowed legitimate")

        self.tracker.record_strategy_decision("strategy1", event1, result1)
        self.tracker.record_strategy_decision("strategy2", event2, result2)

        overall_stats = self.tracker.get_stats()
        assert overall_stats.true_positives == 1
        assert overall_stats.true_negatives == 1
        assert overall_stats.false_positives == 0
        assert overall_stats.false_negatives == 0

    def test_get_all_stats(self) -> None:
        """Test getting all strategy stats."""
        event = self.create_test_event()
        self.tracker.label_event(event, True)

        result = StrategyResult(allowed=False, reason="blocked")
        self.tracker.record_strategy_decision("strategy1", event, result)
        self.tracker.record_strategy_decision("strategy2", event, result)

        all_stats = self.tracker.get_all_stats()
        assert "strategy1" in all_stats
        assert "strategy2" in all_stats
        assert "overall" in all_stats
        assert all_stats["overall"].true_positives == 2  # Both strategies recorded


class TestRelayLoadMonitor:
    """Test the RelayLoadMonitor class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.monitor = RelayLoadMonitor(window_size=10)
        self.keypair = NostrKeyPair.generate()

    def create_test_event(self) -> NostrEvent:
        """Create a test event."""
        return NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test event",
            created_at=int(time.time()),
            pubkey=self.keypair.public_key,
        )

    def test_record_event_processing(self) -> None:
        """Test recording event processing metrics."""
        event = self.create_test_event()
        self.monitor.record_event_processing(event, 0.1, 1024)

        stats = self.monitor.get_stats()
        assert stats.total_cpu_time == 0.1
        assert stats.total_bandwidth_bytes == 1024
        assert len(stats.event_processing_times) == 1
        assert stats.event_processing_times[0] == 0.1

    def test_peak_values_tracking(self) -> None:
        """Test tracking of peak values."""
        event1 = self.create_test_event()
        event2 = self.create_test_event()

        self.monitor.record_event_processing(event1, 0.1, 1024)
        self.monitor.record_event_processing(event2, 0.2, 2048)  # Higher values

        stats = self.monitor.get_stats()
        assert stats.peak_cpu_usage == 0.2
        # Peak bandwidth rate calculation depends on timing
        assert stats.peak_bandwidth_rate >= 0

    def test_average_calculations(self) -> None:
        """Test average calculation properties."""
        event1 = self.create_test_event()
        event2 = self.create_test_event()

        self.monitor.record_event_processing(event1, 0.1, 1000)
        self.monitor.record_event_processing(event2, 0.3, 2000)

        stats = self.monitor.get_stats()
        assert stats.average_cpu_time_per_event == 0.2  # (0.1 + 0.3) / 2
        assert stats.average_bandwidth_per_event == 1500.0  # (1000 + 2000) / 2

    def test_current_load_calculation(self) -> None:
        """Test current load calculation."""
        event = self.create_test_event()

        # Record multiple events quickly
        for _ in range(3):
            self.monitor.record_event_processing(event, 0.1, 1024)

        cpu_load = self.monitor.get_current_cpu_load()
        bandwidth_rate = self.monitor.get_current_bandwidth_rate()

        # Should have some load (exact values depend on timing)
        assert cpu_load >= 0
        assert bandwidth_rate >= 0


class TestLatencyMeasurement:
    """Test the LatencyMeasurement class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.latency = LatencyMeasurement()

    def test_start_end_measurement(self) -> None:
        """Test start/end measurement workflow."""
        self.latency.start_measurement("test_op")
        time.sleep(0.01)  # Small delay
        measured_latency = self.latency.end_measurement("test_op", "processing")

        assert measured_latency > 0
        assert len(self.latency.stats.processing_latencies) == 1
        assert self.latency.stats.processing_latencies[0] > 0

    def test_end_measurement_without_start(self) -> None:
        """Test ending measurement without starting."""
        latency = self.latency.end_measurement("nonexistent_op")
        assert latency == 0.0

    def test_record_latency_direct(self) -> None:
        """Test directly recording latency."""
        self.latency.record_latency(0.05, "validation")
        assert len(self.latency.stats.validation_latencies) == 1
        assert self.latency.stats.validation_latencies[0] == 0.05

    def test_strategy_latency_recording(self) -> None:
        """Test recording strategy-specific latencies."""
        self.latency.record_latency(0.1, "pow_strategy")
        self.latency.record_latency(0.2, "pow_strategy")

        strategy_stats = self.latency.get_strategy_stats("pow_strategy")
        assert (
            abs(strategy_stats["average"] - 0.15) < 1e-10
        )  # Use tolerance for floating point
        assert strategy_stats["p95"] > 0
        assert strategy_stats["p99"] > 0

    def test_percentile_calculations(self) -> None:
        """Test percentile calculations."""
        # Add many latency measurements
        latencies = [0.01 * i for i in range(1, 101)]  # 0.01 to 1.0
        for lat in latencies:
            self.latency.record_latency(lat, "processing")

        stats = self.latency.get_stats()
        assert (
            abs(stats.average_processing_latency - 0.505) < 1e-10
        )  # Average of 0.01 to 1.0
        # Use tolerance for percentile calculations due to floating point and indexing
        assert abs(stats.p95_processing_latency - 0.95) <= 0.01  # Allow small variance
        assert abs(stats.p99_processing_latency - 0.99) <= 0.01

    def test_empty_strategy_stats(self) -> None:
        """Test getting stats for non-existent strategy."""
        stats = self.latency.get_strategy_stats("nonexistent")
        assert stats["average"] == 0.0
        assert stats["p95"] == 0.0
        assert stats["p99"] == 0.0


class TestSpamReductionCalculator:
    """Test the SpamReductionCalculator class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.calculator = SpamReductionCalculator()
        self.keypair = NostrKeyPair.generate()

    def create_test_event(self, content: str = "test") -> NostrEvent:
        """Create a test event."""
        return NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content=content,
            created_at=int(time.time()),
            pubkey=self.keypair.public_key,
        )

    def test_label_event_spam(self) -> None:
        """Test labeling an event as spam."""
        event = self.create_test_event()
        self.calculator.label_event(event, True)

        assert self.calculator.overall_stats.total_spam_events == 1
        assert self.calculator.overall_stats.total_legitimate_events == 0

    def test_label_event_legitimate(self) -> None:
        """Test labeling an event as legitimate."""
        event = self.create_test_event()
        self.calculator.label_event(event, False)

        assert self.calculator.overall_stats.total_spam_events == 0
        assert self.calculator.overall_stats.total_legitimate_events == 1

    def test_record_spam_blocked(self) -> None:
        """Test recording blocked spam."""
        event = self.create_test_event()
        self.calculator.label_event(event, True)  # Spam
        self.calculator.record_strategy_decision(
            "test_strategy", event, True
        )  # Blocked

        stats = self.calculator.get_stats("test_strategy")
        assert stats.blocked_spam_events == 1
        assert stats.allowed_spam_events == 0

    def test_record_spam_allowed(self) -> None:
        """Test recording allowed spam."""
        event = self.create_test_event()
        self.calculator.label_event(event, True)  # Spam
        self.calculator.record_strategy_decision(
            "test_strategy", event, False
        )  # Allowed

        stats = self.calculator.get_stats("test_strategy")
        assert stats.blocked_spam_events == 0
        assert stats.allowed_spam_events == 1

    def test_record_legitimate_blocked(self) -> None:
        """Test recording blocked legitimate event."""
        event = self.create_test_event()
        self.calculator.label_event(event, False)  # Legitimate
        self.calculator.record_strategy_decision(
            "test_strategy", event, True
        )  # Blocked

        stats = self.calculator.get_stats("test_strategy")
        assert stats.blocked_legitimate_events == 1

    def test_spam_reduction_percentage(self) -> None:
        """Test spam reduction percentage calculation."""
        # Create 10 spam events, block 8 of them
        for i in range(10):
            event = self.create_test_event(f"spam_{i}")
            self.calculator.label_event(event, True)
            blocked = i < 8  # Block first 8
            self.calculator.record_strategy_decision("test_strategy", event, blocked)

        stats = self.calculator.get_stats("test_strategy")
        assert stats.spam_reduction_percentage == 80.0  # 8/10 * 100

    def test_legitimate_pass_rate(self) -> None:
        """Test legitimate pass rate calculation."""
        # Create 10 legitimate events, block 2 of them
        for i in range(10):
            event = self.create_test_event(f"legitimate_{i}")
            self.calculator.label_event(event, False)
            blocked = i < 2  # Block first 2
            self.calculator.record_strategy_decision("test_strategy", event, blocked)

        stats = self.calculator.get_stats("test_strategy")
        assert stats.legitimate_pass_rate == 80.0  # (10-2)/10 * 100

    def test_overall_stats(self) -> None:
        """Test overall statistics aggregation."""
        event1 = self.create_test_event("spam1")
        event2 = self.create_test_event("legitimate1")

        self.calculator.label_event(event1, True)
        self.calculator.label_event(event2, False)

        self.calculator.record_strategy_decision(
            "strategy1", event1, True
        )  # Block spam
        self.calculator.record_strategy_decision(
            "strategy2", event2, False
        )  # Allow legitimate

        overall_stats = self.calculator.get_stats()
        assert overall_stats.total_spam_events == 1
        assert overall_stats.total_legitimate_events == 1
        assert overall_stats.blocked_spam_events == 1
        assert overall_stats.blocked_legitimate_events == 0


class TestResilienceMetrics:
    """Test the ResilienceMetrics class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.metrics = ResilienceMetrics()

    def test_record_attack_detected(self) -> None:
        """Test recording a detected attack."""
        self.metrics.record_attack("sybil", True)

        timeline = self.metrics.get_attack_timeline()
        assert len(timeline) == 1
        assert timeline[0][1] == "sybil"
        assert timeline[0][2] is True

    def test_record_offline_attacks(self) -> None:
        """Test recording offline attacks."""
        self.metrics.record_attack("offline_sybil", True)
        self.metrics.record_attack("offline_spam", False)

        stats = self.metrics.get_stats()
        assert stats.offline_attacks_detected == 1
        assert stats.offline_attacks_missed == 1
        assert stats.offline_detection_rate == 50.0

    def test_recovery_timing(self) -> None:
        """Test recovery timing measurement."""
        self.metrics.start_recovery("sybil_attack")
        time.sleep(0.01)  # Small delay
        self.metrics.end_recovery("sybil_attack")

        stats = self.metrics.get_stats()
        assert stats.recovery_time_seconds > 0

    def test_sybil_resistance_score(self) -> None:
        """Test sybil resistance score updates."""
        self.metrics.update_sybil_resistance_score(0.85)
        assert self.metrics.get_stats().sybil_resistance_score == 0.85

        # Test clamping
        self.metrics.update_sybil_resistance_score(1.5)
        assert self.metrics.get_stats().sybil_resistance_score == 1.0

        self.metrics.update_sybil_resistance_score(-0.5)
        assert self.metrics.get_stats().sybil_resistance_score == 0.0

    def test_adaptive_response_tracking(self) -> None:
        """Test adaptive response tracking."""
        self.metrics.record_adaptive_response()
        self.metrics.record_adaptive_response()

        stats = self.metrics.get_stats()
        assert stats.adaptive_response_count == 2


class TestCoreMetricsCollector:
    """Test the CoreMetricsCollector class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.collector = CoreMetricsCollector()
        self.keypair = NostrKeyPair.generate()

    def create_test_event(self, content: str = "test") -> NostrEvent:
        """Create a test event."""
        return NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content=content,
            created_at=int(time.time()),
            pubkey=self.keypair.public_key,
        )

    def test_start_stop_collection(self) -> None:
        """Test starting and stopping collection."""
        assert not self.collector.is_collecting

        self.collector.start_collection()
        assert self.collector.is_collecting

        self.collector.stop_collection()
        assert not self.collector.is_collecting

    def test_label_event_integration(self) -> None:
        """Test event labeling integration."""
        self.collector.start_collection()

        event = self.create_test_event()
        self.collector.label_event(event, True)

        # Check that both subsystems received the label
        self.collector.fp_fn_tracker.get_stats()
        self.collector.spam_reduction_calculator.get_stats()

        # Events should be tracked but no decisions recorded yet
        assert event.id in self.collector.fp_fn_tracker.event_labels
        assert event.id in self.collector.spam_reduction_calculator.event_labels

    def test_strategy_evaluation_integration(self) -> None:
        """Test strategy evaluation integration."""
        self.collector.start_collection()

        event = self.create_test_event()
        self.collector.label_event(event, True)  # Spam

        result = StrategyResult(allowed=False, reason="blocked spam")
        self.collector.record_strategy_evaluation("test_strategy", event, result)

        # Check that metrics were recorded in both systems
        fp_fn_stats = self.collector.fp_fn_tracker.get_stats("test_strategy")
        spam_stats = self.collector.spam_reduction_calculator.get_stats("test_strategy")

        assert fp_fn_stats.true_positives == 1
        assert spam_stats.blocked_spam_events == 1

    def test_comprehensive_report(self) -> None:
        """Test comprehensive report generation."""
        self.collector.start_collection()

        # Generate some test data
        event = self.create_test_event()
        self.collector.label_event(event, True)

        result = StrategyResult(allowed=False, reason="blocked")
        self.collector.record_strategy_evaluation("test_strategy", event, result)

        self.collector.record_event_processing(event, 0.1, 1024)
        self.collector.record_attack("sybil", True)

        report = self.collector.get_comprehensive_report()

        # Verify report structure
        assert "collection_info" in report
        assert "false_positive_negative" in report
        assert "relay_load" in report
        assert "latency" in report
        assert "spam_reduction" in report
        assert "resilience" in report

        # Verify some data
        assert report["collection_info"]["is_collecting"] is True
        assert (
            report["false_positive_negative"]["by_strategy"][
                "test_strategy"
            ].true_positives
            == 1
        )
        assert report["relay_load"].total_cpu_time == 0.1

    def test_collection_state_filtering(self) -> None:
        """Test that metrics are only recorded when collecting."""
        # Don't start collection
        event = self.create_test_event()
        self.collector.label_event(event, True)

        result = StrategyResult(allowed=False, reason="blocked")
        self.collector.record_strategy_evaluation("test_strategy", event, result)

        # Nothing should be recorded
        fp_fn_stats = self.collector.fp_fn_tracker.get_stats("test_strategy")
        assert fp_fn_stats.true_positives == 0
        assert fp_fn_stats.false_positives == 0
        assert fp_fn_stats.true_negatives == 0
        assert fp_fn_stats.false_negatives == 0
