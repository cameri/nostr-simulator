"""Enhanced simulation engine with comprehensive metrics integration."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from ..anti_spam.base import AntiSpamStrategy
from ..config import Config
from ..metrics.core_metrics import CoreMetricsCollector
from ..protocol.events import NostrEvent
from .engine import SimulationEngine
from .events import Event


class EnhancedSimulationEngine(SimulationEngine):
    """Enhanced simulation engine with comprehensive metrics collection."""

    def __init__(self, config: Config) -> None:
        """Initialize the enhanced simulation engine.

        Args:
            config: Simulation configuration.
        """
        super().__init__(config)

        # Enhanced metrics system
        self.core_metrics = CoreMetricsCollector()

        # Anti-spam strategies registry
        self.anti_spam_strategies: dict[str, AntiSpamStrategy] = {}

        # Event labeling function (for ground truth)
        self.event_labeler: Callable[[NostrEvent], bool] | None = None

        self.logger.info(
            "Enhanced simulation engine initialized with comprehensive metrics"
        )

    def register_anti_spam_strategy(
        self, name: str, strategy: AntiSpamStrategy
    ) -> None:
        """Register an anti-spam strategy.

        Args:
            name: Name of the strategy.
            strategy: The strategy instance.
        """
        self.anti_spam_strategies[name] = strategy
        self.logger.info(f"Registered anti-spam strategy: {name}")

    def set_event_labeler(self, labeler: Callable[[NostrEvent], bool]) -> None:
        """Set the event labeling function for ground truth.

        Args:
            labeler: Function that takes a NostrEvent and returns True if spam, False if legitimate.
        """
        self.event_labeler = labeler
        self.logger.info("Event labeler function set for ground truth tracking")

    def run(self) -> None:
        """Run the enhanced simulation with comprehensive metrics."""
        if self.is_running:
            self.logger.warning("Simulation is already running")
            return

        self.logger.info("Starting enhanced simulation")
        self.is_running = True
        self.start_wall_time = time.time()

        # Start both metrics systems
        self.metrics_collector.start_collection()
        self.core_metrics.start_collection()

        try:
            self._simulation_loop()
        except KeyboardInterrupt:
            self.logger.info("Simulation interrupted by user")
        except Exception as e:
            self.logger.error(f"Simulation error: {e}")
            raise
        finally:
            self._cleanup()

    def _process_event(self, event: Event) -> None:
        """Process a single event with enhanced metrics collection.

        Args:
            event: The event to process.
        """
        start_time = time.perf_counter()

        # Process event normally
        super()._process_event(event)

        # Enhanced metrics collection for NostrEvent processing
        if hasattr(event, "data") and event.data and "nostr_event" in event.data:
            nostr_event = event.data["nostr_event"]
            if isinstance(nostr_event, NostrEvent):
                self._process_nostr_event_metrics(nostr_event, start_time)

    def _process_nostr_event_metrics(
        self, nostr_event: NostrEvent, start_time: float
    ) -> None:
        """Process metrics for a Nostr event.

        Args:
            nostr_event: The Nostr event to process.
            start_time: Processing start time.
        """
        processing_time = time.perf_counter() - start_time

        # Estimate bytes processed (rough calculation)
        event_bytes = (
            len(nostr_event.content.encode("utf-8")) + 200
        )  # Content + overhead

        # Record processing metrics
        self.core_metrics.record_event_processing(
            nostr_event, processing_time, event_bytes
        )

        # Label event if labeler is available
        if self.event_labeler:
            is_spam = self.event_labeler(nostr_event)
            self.core_metrics.label_event(nostr_event, is_spam)

        # Evaluate with anti-spam strategies
        for strategy_name, strategy in self.anti_spam_strategies.items():
            strategy_start = time.perf_counter()

            try:
                result = strategy.evaluate_event(nostr_event, self.current_time)

                # Add latency to result metrics
                strategy_latency = time.perf_counter() - strategy_start
                if result.metrics is None:
                    result.metrics = {}
                result.metrics["latency"] = strategy_latency

                # Record strategy evaluation
                self.core_metrics.record_strategy_evaluation(
                    strategy_name, nostr_event, result
                )

                # Update strategy state if event was allowed
                if result.allowed:
                    strategy.update_state(nostr_event, self.current_time)

                self.logger.debug(
                    f"Strategy {strategy_name}: {'ALLOWED' if result.allowed else 'BLOCKED'} "
                    f"event {nostr_event.id[:8]}... (reason: {result.reason})"
                )

            except Exception as e:
                self.logger.error(
                    f"Error evaluating event with strategy {strategy_name}: {e}"
                )

    def process_nostr_event(
        self,
        nostr_event: NostrEvent,
        event_type: str = "nostr_message",
        source_id: str | None = None,
    ) -> str:
        """Process a Nostr event through the simulation system.

        Args:
            nostr_event: The Nostr event to process.
            event_type: Type of simulation event.
            source_id: ID of the event source.

        Returns:
            The simulation event ID.
        """
        # Schedule the event for immediate processing
        return self.schedule_event(
            delay=0.0,
            event_type=event_type,
            data={"nostr_event": nostr_event},
            source_id=source_id,
        )

    def record_attack(self, attack_type: str, detected: bool) -> None:
        """Record an attack event.

        Args:
            attack_type: Type of attack (e.g., "sybil", "burst_spam", "replay").
            detected: Whether the attack was detected.
        """
        self.core_metrics.record_attack(attack_type, detected)
        self.logger.info(
            f"Recorded {attack_type} attack: {'DETECTED' if detected else 'MISSED'}"
        )

    def update_sybil_resistance(self, score: float) -> None:
        """Update the sybil resistance score.

        Args:
            score: Sybil resistance score between 0 and 1.
        """
        self.core_metrics.resilience_metrics.update_sybil_resistance_score(score)

    def record_adaptive_response(self) -> None:
        """Record that an adaptive response was triggered."""
        self.core_metrics.resilience_metrics.record_adaptive_response()

    def get_comprehensive_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics from both systems.

        Returns:
            Dictionary containing all collected metrics.
        """
        # Get base simulation metrics
        base_metrics = self.metrics_collector.get_current_metrics()

        # Get core metrics
        core_metrics = self.core_metrics.get_comprehensive_report()

        # Combine metrics
        return {
            "simulation": base_metrics,
            "core_metrics": core_metrics,
            "simulation_info": {
                "current_time": self.current_time,
                "event_count": self.event_count,
                "is_running": self.is_running,
                "registered_strategies": list(self.anti_spam_strategies.keys()),
            },
        }

    def _cleanup(self) -> None:
        """Enhanced cleanup with metrics finalization."""
        super()._cleanup()

        # Stop core metrics collection
        self.core_metrics.stop_collection()

        # Log final metrics summary
        metrics = self.get_comprehensive_metrics()
        self._log_metrics_summary(metrics)

    def _log_metrics_summary(self, metrics: dict[str, Any]) -> None:
        """Log a summary of the collected metrics.

        Args:
            metrics: The collected metrics.
        """
        self.logger.info("=== SIMULATION METRICS SUMMARY ===")

        # Simulation info
        sim_info = metrics["simulation_info"]
        self.logger.info(
            f"Simulation completed in {sim_info['current_time']:.2f} seconds"
        )
        self.logger.info(f"Total events processed: {sim_info['event_count']}")
        self.logger.info(
            f"Registered strategies: {', '.join(sim_info['registered_strategies'])}"
        )

        # Core metrics summary
        core = metrics["core_metrics"]

        # False positive/negative summary
        if "overall" in core["false_positive_negative"]["by_strategy"]:
            overall_fp_fn = core["false_positive_negative"]["by_strategy"]["overall"]
            self.logger.info(f"Overall Accuracy: {overall_fp_fn.accuracy:.2%}")
            self.logger.info(f"Overall Precision: {overall_fp_fn.precision:.2%}")
            self.logger.info(f"Overall Recall: {overall_fp_fn.recall:.2%}")
            self.logger.info(f"Overall F1 Score: {overall_fp_fn.f1_score:.2%}")

        # Spam reduction summary
        spam_overall = core["spam_reduction"]["overall"]
        self.logger.info(
            f"Spam Reduction: {spam_overall.spam_reduction_percentage:.1f}%"
        )
        self.logger.info(
            f"Legitimate Pass Rate: {spam_overall.legitimate_pass_rate:.1f}%"
        )

        # Performance summary
        relay_load = core["relay_load"]
        self.logger.info(
            f"Average CPU per event: {relay_load.average_cpu_time_per_event * 1000:.2f}ms"
        )
        self.logger.info(
            f"Average bandwidth per event: {relay_load.average_bandwidth_per_event:.0f} bytes"
        )

        # Latency summary
        latency = core["latency"]["overall"]
        self.logger.info(
            f"Average processing latency: {latency.average_processing_latency * 1000:.2f}ms"
        )
        self.logger.info(
            f"P95 processing latency: {latency.p95_processing_latency * 1000:.2f}ms"
        )

        # Resilience summary
        resilience = core["resilience"]["stats"]
        if resilience.offline_attacks_detected + resilience.offline_attacks_missed > 0:
            self.logger.info(
                f"Offline attack detection rate: {resilience.offline_detection_rate:.1f}%"
            )
        self.logger.info(
            f"Sybil resistance score: {resilience.sybil_resistance_score:.2f}"
        )

        self.logger.info("=== END METRICS SUMMARY ===")


def create_enhanced_engine(config: Config) -> EnhancedSimulationEngine:
    """Factory function to create an enhanced simulation engine.

    Args:
        config: Simulation configuration.

    Returns:
        Enhanced simulation engine instance.
    """
    return EnhancedSimulationEngine(config)
