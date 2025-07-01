"""Core metrics system for tracking anti-spam effectiveness and system performance."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from ..anti_spam.base import StrategyResult
from ..logging_config import get_logger
from ..protocol.events import NostrEvent


@dataclass
class FalsePositiveNegativeStats:
    """Statistics for false positives and negatives."""

    true_positives: int = 0  # Spam correctly blocked
    true_negatives: int = 0  # Legitimate messages correctly allowed
    false_positives: int = 0  # Legitimate messages incorrectly blocked
    false_negatives: int = 0  # Spam incorrectly allowed

    @property
    def precision(self) -> float:
        """Calculate precision (TP / (TP + FP))."""
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator > 0 else 0.0

    @property
    def recall(self) -> float:
        """Calculate recall (TP / (TP + FN))."""
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator > 0 else 0.0

    @property
    def f1_score(self) -> float:
        """Calculate F1 score (2 * precision * recall / (precision + recall))."""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def accuracy(self) -> float:
        """Calculate accuracy ((TP + TN) / (TP + TN + FP + FN))."""
        total = (
            self.true_positives
            + self.true_negatives
            + self.false_positives
            + self.false_negatives
        )
        return (self.true_positives + self.true_negatives) / total if total > 0 else 0.0


@dataclass
class RelayLoadStats:
    """Statistics for relay computational and bandwidth load."""

    total_cpu_time: float = 0.0  # Total CPU time in seconds
    total_bandwidth_bytes: int = 0  # Total bandwidth used in bytes
    event_processing_times: list[float] = field(
        default_factory=list
    )  # Individual event processing times
    peak_cpu_usage: float = 0.0  # Peak CPU usage percentage
    peak_bandwidth_rate: float = 0.0  # Peak bandwidth rate in bytes/second

    @property
    def average_cpu_time_per_event(self) -> float:
        """Calculate average CPU time per event."""
        return (
            self.total_cpu_time / len(self.event_processing_times)
            if self.event_processing_times
            else 0.0
        )

    @property
    def average_bandwidth_per_event(self) -> float:
        """Calculate average bandwidth per event."""
        return (
            self.total_bandwidth_bytes / len(self.event_processing_times)
            if self.event_processing_times
            else 0.0
        )


@dataclass
class LatencyStats:
    """Statistics for latency measurements."""

    processing_latencies: list[float] = field(
        default_factory=list
    )  # Event processing latencies
    validation_latencies: list[float] = field(
        default_factory=list
    )  # Validation latencies
    strategy_latencies: dict[str, list[float]] = field(
        default_factory=lambda: defaultdict(list)
    )  # Per-strategy latencies

    @property
    def average_processing_latency(self) -> float:
        """Calculate average processing latency."""
        return (
            sum(self.processing_latencies) / len(self.processing_latencies)
            if self.processing_latencies
            else 0.0
        )

    @property
    def p95_processing_latency(self) -> float:
        """Calculate 95th percentile processing latency."""
        if not self.processing_latencies:
            return 0.0
        sorted_latencies = sorted(self.processing_latencies)
        index = min(int(0.95 * (len(sorted_latencies) - 1)), len(sorted_latencies) - 1)
        return sorted_latencies[index]

    @property
    def p99_processing_latency(self) -> float:
        """Calculate 99th percentile processing latency."""
        if not self.processing_latencies:
            return 0.0
        sorted_latencies = sorted(self.processing_latencies)
        index = min(int(0.99 * (len(sorted_latencies) - 1)), len(sorted_latencies) - 1)
        return sorted_latencies[index]


@dataclass
class SpamReductionStats:
    """Statistics for spam reduction effectiveness."""

    total_spam_events: int = 0  # Total spam events detected
    blocked_spam_events: int = 0  # Spam events blocked
    allowed_spam_events: int = 0  # Spam events that got through
    total_legitimate_events: int = 0  # Total legitimate events
    blocked_legitimate_events: int = 0  # Legitimate events blocked

    @property
    def spam_reduction_percentage(self) -> float:
        """Calculate percentage of spam blocked."""
        return (
            (self.blocked_spam_events / self.total_spam_events * 100)
            if self.total_spam_events > 0
            else 0.0
        )

    @property
    def legitimate_pass_rate(self) -> float:
        """Calculate percentage of legitimate events that passed."""
        allowed_legitimate = (
            self.total_legitimate_events - self.blocked_legitimate_events
        )
        return (
            (allowed_legitimate / self.total_legitimate_events * 100)
            if self.total_legitimate_events > 0
            else 0.0
        )


@dataclass
class ResilienceStats:
    """Statistics for measuring system resilience."""

    offline_attacks_detected: int = 0  # Attacks detected while offline
    offline_attacks_missed: int = 0  # Attacks missed while offline
    recovery_time_seconds: float = 0.0  # Time to recover from attacks
    sybil_resistance_score: float = 0.0  # Score for sybil resistance (0-1)
    adaptive_response_count: int = 0  # Number of adaptive responses triggered

    @property
    def offline_detection_rate(self) -> float:
        """Calculate offline attack detection rate."""
        total_offline_attacks = (
            self.offline_attacks_detected + self.offline_attacks_missed
        )
        return (
            (self.offline_attacks_detected / total_offline_attacks * 100)
            if total_offline_attacks > 0
            else 0.0
        )


class FalsePositiveNegativeTracker:
    """Tracks false positives and negatives for anti-spam strategies."""

    def __init__(self) -> None:
        """Initialize the tracker."""
        self.logger = get_logger(__name__)
        self.stats_by_strategy: dict[str, FalsePositiveNegativeStats] = defaultdict(
            FalsePositiveNegativeStats
        )
        self.overall_stats = FalsePositiveNegativeStats()

        # Ground truth tracking
        self.event_labels: dict[str, bool] = {}  # event_id -> is_spam
        self.strategy_decisions: dict[str, dict[str, bool]] = defaultdict(
            dict
        )  # strategy -> event_id -> blocked

    def label_event(self, event: NostrEvent, is_spam: bool) -> None:
        """Label an event as spam or legitimate for ground truth.

        Args:
            event: The event to label.
            is_spam: True if the event is spam, False if legitimate.
        """
        self.event_labels[event.id] = is_spam

    def record_strategy_decision(
        self, strategy_name: str, event: NostrEvent, result: StrategyResult
    ) -> None:
        """Record a strategy's decision on an event.

        Args:
            strategy_name: Name of the strategy.
            event: The event that was evaluated.
            result: The strategy's decision result.
        """
        blocked = not result.allowed
        self.strategy_decisions[strategy_name][event.id] = blocked

        # Update stats if we have ground truth
        if event.id in self.event_labels:
            is_spam = self.event_labels[event.id]
            stats = self.stats_by_strategy[strategy_name]

            if is_spam and blocked:
                stats.true_positives += 1
                self.overall_stats.true_positives += 1
            elif is_spam and not blocked:
                stats.false_negatives += 1
                self.overall_stats.false_negatives += 1
            elif not is_spam and blocked:
                stats.false_positives += 1
                self.overall_stats.false_positives += 1
            elif not is_spam and not blocked:
                stats.true_negatives += 1
                self.overall_stats.true_negatives += 1

    def get_stats(self, strategy_name: str | None = None) -> FalsePositiveNegativeStats:
        """Get false positive/negative stats.

        Args:
            strategy_name: Strategy to get stats for, or None for overall stats.

        Returns:
            Statistics for the specified strategy or overall.
        """
        if strategy_name is None:
            return self.overall_stats
        return self.stats_by_strategy[strategy_name]

    def get_all_stats(self) -> dict[str, FalsePositiveNegativeStats]:
        """Get stats for all strategies.

        Returns:
            Dictionary mapping strategy names to their stats.
        """
        result = dict(self.stats_by_strategy)
        result["overall"] = self.overall_stats
        return result


class RelayLoadMonitor:
    """Monitors computational and bandwidth load on relays."""

    def __init__(self, window_size: int = 100) -> None:
        """Initialize the monitor.

        Args:
            window_size: Size of the sliding window for rate calculations.
        """
        self.logger = get_logger(__name__)
        self.window_size = window_size

        self.stats = RelayLoadStats()
        self.recent_processing_times: deque[tuple[float, float]] = deque(
            maxlen=window_size
        )  # (timestamp, processing_time)
        self.recent_bandwidth_usage: deque[tuple[float, int]] = deque(
            maxlen=window_size
        )  # (timestamp, bytes)

    def record_event_processing(
        self, event: NostrEvent, processing_time: float, bytes_processed: int
    ) -> None:
        """Record processing time and bandwidth for an event.

        Args:
            event: The processed event.
            processing_time: Time taken to process the event in seconds.
            bytes_processed: Number of bytes processed for this event.
        """
        current_time = time.time()

        self.stats.total_cpu_time += processing_time
        self.stats.total_bandwidth_bytes += bytes_processed
        self.stats.event_processing_times.append(processing_time)

        self.recent_processing_times.append((current_time, processing_time))
        self.recent_bandwidth_usage.append((current_time, bytes_processed))

        # Update peak values
        if processing_time > self.stats.peak_cpu_usage:
            self.stats.peak_cpu_usage = processing_time

        # Calculate current bandwidth rate (bytes per second over last second)
        current_bandwidth_rate = self._calculate_bandwidth_rate()
        if current_bandwidth_rate > self.stats.peak_bandwidth_rate:
            self.stats.peak_bandwidth_rate = current_bandwidth_rate

    def _calculate_bandwidth_rate(self) -> float:
        """Calculate current bandwidth rate in bytes per second."""
        if not self.recent_bandwidth_usage:
            return 0.0

        current_time = time.time()
        one_second_ago = current_time - 1.0

        # Sum bytes processed in the last second
        bytes_last_second = sum(
            bytes_count
            for timestamp, bytes_count in self.recent_bandwidth_usage
            if timestamp >= one_second_ago
        )

        return float(bytes_last_second)

    def get_stats(self) -> RelayLoadStats:
        """Get current relay load statistics.

        Returns:
            Current relay load statistics.
        """
        return self.stats

    def get_current_cpu_load(self) -> float:
        """Get current CPU load (events per second).

        Returns:
            Current CPU load in events per second.
        """
        if not self.recent_processing_times:
            return 0.0

        current_time = time.time()
        one_second_ago = current_time - 1.0

        # Count events processed in the last second
        events_last_second = sum(
            1
            for timestamp, _ in self.recent_processing_times
            if timestamp >= one_second_ago
        )

        return float(events_last_second)

    def get_current_bandwidth_rate(self) -> float:
        """Get current bandwidth rate in bytes per second.

        Returns:
            Current bandwidth rate.
        """
        return self._calculate_bandwidth_rate()


class LatencyMeasurement:
    """Measures latency for various operations."""

    def __init__(self) -> None:
        """Initialize the latency measurement system."""
        self.logger = get_logger(__name__)
        self.stats = LatencyStats()
        self.active_measurements: dict[str, float] = {}  # operation_id -> start_time

    def start_measurement(self, operation_id: str) -> None:
        """Start measuring latency for an operation.

        Args:
            operation_id: Unique identifier for the operation.
        """
        self.active_measurements[operation_id] = time.perf_counter()

    def end_measurement(
        self, operation_id: str, measurement_type: str = "processing"
    ) -> float:
        """End measurement and record latency.

        Args:
            operation_id: Unique identifier for the operation.
            measurement_type: Type of measurement ("processing", "validation", or strategy name).

        Returns:
            The measured latency in seconds.
        """
        if operation_id not in self.active_measurements:
            self.logger.warning(
                f"No active measurement found for operation {operation_id}"
            )
            return 0.0

        start_time = self.active_measurements.pop(operation_id)
        latency = time.perf_counter() - start_time

        if measurement_type == "processing":
            self.stats.processing_latencies.append(latency)
        elif measurement_type == "validation":
            self.stats.validation_latencies.append(latency)
        else:
            # Assume it's a strategy name
            self.stats.strategy_latencies[measurement_type].append(latency)

        return latency

    def record_latency(
        self, latency: float, measurement_type: str = "processing"
    ) -> None:
        """Directly record a latency measurement.

        Args:
            latency: The latency value in seconds.
            measurement_type: Type of measurement ("processing", "validation", or strategy name).
        """
        if measurement_type == "processing":
            self.stats.processing_latencies.append(latency)
        elif measurement_type == "validation":
            self.stats.validation_latencies.append(latency)
        else:
            # Assume it's a strategy name
            self.stats.strategy_latencies[measurement_type].append(latency)

    def get_stats(self) -> LatencyStats:
        """Get current latency statistics.

        Returns:
            Current latency statistics.
        """
        return self.stats

    def get_strategy_stats(self, strategy_name: str) -> dict[str, float]:
        """Get latency statistics for a specific strategy.

        Args:
            strategy_name: Name of the strategy.

        Returns:
            Dictionary with average, p95, and p99 latencies for the strategy.
        """
        latencies = self.stats.strategy_latencies.get(strategy_name, [])
        if not latencies:
            return {"average": 0.0, "p95": 0.0, "p99": 0.0}

        sorted_latencies = sorted(latencies)
        return {
            "average": sum(latencies) / len(latencies),
            "p95": (
                sorted_latencies[
                    min(
                        int(0.95 * (len(sorted_latencies) - 1)),
                        len(sorted_latencies) - 1,
                    )
                ]
                if len(sorted_latencies) > 0
                else 0.0
            ),
            "p99": (
                sorted_latencies[
                    min(
                        int(0.99 * (len(sorted_latencies) - 1)),
                        len(sorted_latencies) - 1,
                    )
                ]
                if len(sorted_latencies) > 0
                else 0.0
            ),
        }


class SpamReductionCalculator:
    """Calculates spam reduction effectiveness."""

    def __init__(self) -> None:
        """Initialize the spam reduction calculator."""
        self.logger = get_logger(__name__)
        self.stats_by_strategy: dict[str, SpamReductionStats] = defaultdict(
            SpamReductionStats
        )
        self.overall_stats = SpamReductionStats()

        # Event tracking
        self.event_labels: dict[str, bool] = {}  # event_id -> is_spam
        self.strategy_decisions: dict[str, dict[str, bool]] = defaultdict(
            dict
        )  # strategy -> event_id -> blocked

    def label_event(self, event: NostrEvent, is_spam: bool) -> None:
        """Label an event as spam or legitimate.

        Args:
            event: The event to label.
            is_spam: True if spam, False if legitimate.
        """
        self.event_labels[event.id] = is_spam

        if is_spam:
            self.overall_stats.total_spam_events += 1
        else:
            self.overall_stats.total_legitimate_events += 1

    def record_strategy_decision(
        self, strategy_name: str, event: NostrEvent, blocked: bool
    ) -> None:
        """Record a strategy's decision to block or allow an event.

        Args:
            strategy_name: Name of the strategy.
            event: The event that was evaluated.
            blocked: True if the event was blocked, False if allowed.
        """
        self.strategy_decisions[strategy_name][event.id] = blocked

        # Update stats if we have ground truth
        if event.id in self.event_labels:
            is_spam = self.event_labels[event.id]
            stats = self.stats_by_strategy[strategy_name]

            if is_spam:
                if blocked:
                    stats.blocked_spam_events += 1
                    self.overall_stats.blocked_spam_events += 1
                else:
                    stats.allowed_spam_events += 1
                    self.overall_stats.allowed_spam_events += 1
                stats.total_spam_events += 1
            else:
                if blocked:
                    stats.blocked_legitimate_events += 1
                    self.overall_stats.blocked_legitimate_events += 1
                stats.total_legitimate_events += 1

    def get_stats(self, strategy_name: str | None = None) -> SpamReductionStats:
        """Get spam reduction statistics.

        Args:
            strategy_name: Strategy to get stats for, or None for overall stats.

        Returns:
            Spam reduction statistics.
        """
        if strategy_name is None:
            return self.overall_stats
        return self.stats_by_strategy[strategy_name]

    def get_all_stats(self) -> dict[str, SpamReductionStats]:
        """Get stats for all strategies.

        Returns:
            Dictionary mapping strategy names to their stats.
        """
        result = dict(self.stats_by_strategy)
        result["overall"] = self.overall_stats
        return result


class ResilienceMetrics:
    """Measures system resilience against various attack vectors."""

    def __init__(self) -> None:
        """Initialize the resilience metrics system."""
        self.logger = get_logger(__name__)
        self.stats = ResilienceStats()

        # Attack tracking
        self.attack_events: list[tuple[float, str, bool]] = (
            []
        )  # (timestamp, attack_type, detected)
        self.recovery_start_times: dict[str, float] = (
            {}
        )  # attack_type -> recovery_start_time

    def record_attack(
        self, attack_type: str, detected: bool, timestamp: float | None = None
    ) -> None:
        """Record an attack event.

        Args:
            attack_type: Type of attack (e.g., "sybil", "burst_spam", "replay").
            detected: True if the attack was detected, False otherwise.
            timestamp: Timestamp of the attack, or None for current time.
        """
        if timestamp is None:
            timestamp = time.time()

        self.attack_events.append((timestamp, attack_type, detected))

        if attack_type in ["offline_sybil", "offline_spam", "offline_replay"]:
            if detected:
                self.stats.offline_attacks_detected += 1
            else:
                self.stats.offline_attacks_missed += 1

    def start_recovery(self, attack_type: str) -> None:
        """Mark the start of recovery from an attack.

        Args:
            attack_type: Type of attack being recovered from.
        """
        self.recovery_start_times[attack_type] = time.time()

    def end_recovery(self, attack_type: str) -> None:
        """Mark the end of recovery from an attack.

        Args:
            attack_type: Type of attack that was recovered from.
        """
        if attack_type in self.recovery_start_times:
            recovery_time = time.time() - self.recovery_start_times.pop(attack_type)
            self.stats.recovery_time_seconds += recovery_time

    def update_sybil_resistance_score(self, score: float) -> None:
        """Update the sybil resistance score.

        Args:
            score: Sybil resistance score between 0 and 1.
        """
        self.stats.sybil_resistance_score = max(0.0, min(1.0, score))

    def record_adaptive_response(self) -> None:
        """Record that an adaptive response was triggered."""
        self.stats.adaptive_response_count += 1

    def get_stats(self) -> ResilienceStats:
        """Get current resilience statistics.

        Returns:
            Current resilience statistics.
        """
        return self.stats

    def get_attack_timeline(self) -> list[tuple[float, str, bool]]:
        """Get timeline of all attack events.

        Returns:
            List of (timestamp, attack_type, detected) tuples.
        """
        return self.attack_events.copy()


class CoreMetricsCollector:
    """Central collector for all core metrics."""

    def __init__(self) -> None:
        """Initialize the core metrics collector."""
        self.logger = get_logger(__name__)

        # Individual metric systems
        self.fp_fn_tracker = FalsePositiveNegativeTracker()
        self.relay_load_monitor = RelayLoadMonitor()
        self.latency_measurement = LatencyMeasurement()
        self.spam_reduction_calculator = SpamReductionCalculator()
        self.resilience_metrics = ResilienceMetrics()

        # Collection state
        self.collection_start_time = time.time()
        self.is_collecting = False

    def start_collection(self) -> None:
        """Start metrics collection."""
        self.is_collecting = True
        self.collection_start_time = time.time()
        self.logger.info("Started core metrics collection")

    def stop_collection(self) -> None:
        """Stop metrics collection."""
        self.is_collecting = False
        self.logger.info("Stopped core metrics collection")

    def label_event(self, event: NostrEvent, is_spam: bool) -> None:
        """Label an event for ground truth tracking.

        Args:
            event: The event to label.
            is_spam: True if spam, False if legitimate.
        """
        if self.is_collecting:
            self.fp_fn_tracker.label_event(event, is_spam)
            self.spam_reduction_calculator.label_event(event, is_spam)

    def record_strategy_evaluation(
        self, strategy_name: str, event: NostrEvent, result: StrategyResult
    ) -> None:
        """Record the result of a strategy evaluation.

        Args:
            strategy_name: Name of the strategy.
            event: The event that was evaluated.
            result: The strategy's evaluation result.
        """
        if self.is_collecting:
            self.fp_fn_tracker.record_strategy_decision(strategy_name, event, result)
            self.spam_reduction_calculator.record_strategy_decision(
                strategy_name, event, not result.allowed
            )

            # Record latency if provided in metrics
            if result.metrics and "latency" in result.metrics:
                self.latency_measurement.record_latency(
                    result.metrics["latency"], strategy_name
                )

    def record_event_processing(
        self, event: NostrEvent, processing_time: float, bytes_processed: int
    ) -> None:
        """Record event processing metrics.

        Args:
            event: The processed event.
            processing_time: Time taken to process the event.
            bytes_processed: Number of bytes processed.
        """
        if self.is_collecting:
            self.relay_load_monitor.record_event_processing(
                event, processing_time, bytes_processed
            )

    def record_attack(self, attack_type: str, detected: bool) -> None:
        """Record an attack event.

        Args:
            attack_type: Type of attack.
            detected: Whether the attack was detected.
        """
        if self.is_collecting:
            self.resilience_metrics.record_attack(attack_type, detected)

    def get_comprehensive_report(self) -> dict[str, Any]:
        """Get a comprehensive metrics report.

        Returns:
            Dictionary containing all metrics and statistics.
        """
        collection_duration = time.time() - self.collection_start_time

        return {
            "collection_info": {
                "duration_seconds": collection_duration,
                "is_collecting": self.is_collecting,
                "start_time": self.collection_start_time,
            },
            "false_positive_negative": {
                "overall": self.fp_fn_tracker.get_stats(),
                "by_strategy": self.fp_fn_tracker.get_all_stats(),
            },
            "relay_load": self.relay_load_monitor.get_stats(),
            "latency": {
                "overall": self.latency_measurement.get_stats(),
                "by_strategy": {
                    strategy: self.latency_measurement.get_strategy_stats(strategy)
                    for strategy in self.latency_measurement.stats.strategy_latencies.keys()
                },
            },
            "spam_reduction": {
                "overall": self.spam_reduction_calculator.get_stats(),
                "by_strategy": self.spam_reduction_calculator.get_all_stats(),
            },
            "resilience": {
                "stats": self.resilience_metrics.get_stats(),
                "attack_timeline": self.resilience_metrics.get_attack_timeline(),
            },
        }
