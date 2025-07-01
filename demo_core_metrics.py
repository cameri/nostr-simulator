#!/usr/bin/env python3
"""Demo script showcasing the Core Metrics System."""

import time

from nostr_simulator.anti_spam.pow import ProofOfWorkStrategy
from nostr_simulator.anti_spam.rate_limiting import TokenBucketRateLimiting
from nostr_simulator.anti_spam.wot import WebOfTrustStrategy
from nostr_simulator.config import Config
from nostr_simulator.metrics.core_metrics import CoreMetricsCollector
from nostr_simulator.protocol.events import NostrEvent, NostrEventKind
from nostr_simulator.protocol.keys import NostrKeyPair
from nostr_simulator.simulation.enhanced_engine import EnhancedSimulationEngine


def is_spam_event(event: NostrEvent) -> bool:
    """Simple spam detection function for ground truth labeling.

    Args:
        event: The event to evaluate.

    Returns:
        True if the event is considered spam.
    """
    spam_indicators = [
        "URGENT",
        "LIMITED TIME",
        "ACT NOW",
        "FREE MONEY",
        "GUARANTEED",
        "💰",
        "🚀",
        "BREAKING:",
        "You've won",
        "Click here",
    ]

    content_upper = event.content.upper()
    return any(indicator.upper() in content_upper for indicator in spam_indicators)


def create_legitimate_events(count: int = 20) -> list[NostrEvent]:
    """Create legitimate events for testing.

    Args:
        count: Number of events to create.

    Returns:
        List of legitimate events.
    """
    events = []
    legitimate_messages = [
        "Good morning everyone! Hope you're having a great day.",
        "Just finished reading an interesting article about decentralization.",
        "Working on some exciting new protocol improvements today.",
        "The weather is beautiful here. Perfect day for coding!",
        "Thanks for the helpful feedback on my last post.",
        "Looking forward to the conference next week.",
        "Has anyone tried the new Nostr client? What do you think?",
        "Debugging is like being a detective in a crime movie where you are also the murderer.",
        "Coffee and code - the perfect combination for a productive morning.",
        "Excited to see how the community is growing!",
        "Just pushed some updates to my project repository.",
        "The documentation for this feature is really well written.",
        "Learning something new every day in this space.",
        "Great discussion in the developer chat today.",
        "Reminder: backup your keys regularly!",
        "The decentralized web is the future.",
        "Proof of work is fascinating from a technical perspective.",
        "Web of trust networks are really elegant solutions.",
        "Rate limiting helps prevent abuse while maintaining usability.",
        "The balance between security and user experience is always tricky.",
    ]

    base_time = int(time.time())

    for i in range(count):
        keypair = NostrKeyPair.generate()
        content = legitimate_messages[i % len(legitimate_messages)]

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content=content,
            created_at=base_time + (i * 60),  # 1 minute apart
            pubkey=keypair.public_key,
        )
        events.append(event)

    return events


def create_spam_events(count: int = 10) -> list[NostrEvent]:
    """Create spam events for testing.

    Args:
        count: Number of spam events to create.

    Returns:
        List of spam events.
    """
    events = []
    spam_messages = [
        "🚀 URGENT: Limited time crypto offer! Act now!",
        "💰 You've won $50,000! Claim your prize instantly!",
        "🔥 Hot investment opportunity! 1000% returns guaranteed!",
        "⚡ BREAKING: New crypto coin will 100x! Buy now!",
        "🎁 Free money alert! Get $10,000 in 5 minutes!",
        "💎 EXCLUSIVE: Secret trading strategy revealed!",
        "🌟 URGENT: Click here for instant riches!",
        "🚨 LIMITED TIME: Double your Bitcoin overnight!",
        "💸 FREE CRYPTO GIVEAWAY: First 100 people only!",
        "⭐ GUARANTEED profits with this one weird trick!",
    ]

    base_time = int(time.time())

    for i in range(count):
        keypair = NostrKeyPair.generate()
        content = spam_messages[i % len(spam_messages)]

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content=content,
            created_at=base_time
            + (i * 30),  # 30 seconds apart (faster than legitimate)
            pubkey=keypair.public_key,
        )
        events.append(event)

    return events


def demo_core_metrics_system() -> None:
    """Demonstrate the core metrics system capabilities."""
    print("🔬 Core Metrics System Demo")
    print("=" * 50)

    # Initialize core metrics
    metrics = CoreMetricsCollector()
    metrics.start_collection()

    print("\n📊 Creating test events...")
    legitimate_events = create_legitimate_events(20)
    spam_events = create_spam_events(10)
    all_events = legitimate_events + spam_events

    print(f"   ✅ Created {len(legitimate_events)} legitimate events")
    print(f"   ❌ Created {len(spam_events)} spam events")

    # Label events for ground truth
    print("\n🏷️  Labeling events for ground truth...")
    for event in legitimate_events:
        metrics.label_event(event, False)  # Not spam
    for event in spam_events:
        metrics.label_event(event, True)  # Spam

    # Initialize anti-spam strategies
    print("\n🛡️  Initializing anti-spam strategies...")
    strategies = {
        "pow": ProofOfWorkStrategy(min_difficulty=4, max_difficulty=8),
        "rate_limit": TokenBucketRateLimiting(
            bucket_capacity=10, refill_rate=0.167
        ),  # ~10 per minute
        "wot": WebOfTrustStrategy(),
    }

    # Simulate event processing with metrics collection
    print("\n⚡ Processing events through strategies...")

    for i, event in enumerate(all_events):
        processing_start = time.perf_counter()

        # Simulate event processing time
        time.sleep(0.001)  # 1ms processing delay

        # Calculate processing metrics
        processing_time = time.perf_counter() - processing_start
        event_bytes = len(event.content.encode("utf-8")) + 200  # Rough estimate

        # Record processing metrics
        metrics.record_event_processing(event, processing_time, event_bytes)

        # Evaluate with each strategy
        for strategy_name, strategy in strategies.items():
            strategy_start = time.perf_counter()

            try:
                result = strategy.evaluate_event(event, time.time())
                strategy_latency = time.perf_counter() - strategy_start

                # Add latency to result
                if result.metrics is None:
                    result.metrics = {}
                result.metrics["latency"] = strategy_latency

                # Record strategy evaluation
                metrics.record_strategy_evaluation(strategy_name, event, result)

                print(
                    f"   Event {i+1:2d}: {strategy_name:10s} -> {'ALLOW' if result.allowed else 'BLOCK'}"
                )

            except Exception as e:
                print(f"   Error with strategy {strategy_name}: {e}")

        print()  # Blank line between events

    # Simulate some attacks for resilience metrics
    print("\n🎭 Simulating attack scenarios...")

    # Sybil attack
    metrics.record_attack("sybil", True)
    print("   🎭 Sybil attack: DETECTED")

    # Burst spam attack
    metrics.record_attack("burst_spam", True)
    print("   💥 Burst spam attack: DETECTED")

    # Replay attack
    metrics.record_attack("replay", False)
    print("   🔄 Replay attack: MISSED")

    # Offline attack
    metrics.record_attack("offline_sybil", True)
    print("   📱 Offline sybil attack: DETECTED")

    # Update resilience scores
    metrics.resilience_metrics.update_sybil_resistance_score(0.85)
    metrics.resilience_metrics.record_adaptive_response()
    metrics.resilience_metrics.record_adaptive_response()

    # Stop collection and generate report
    print("\n📋 Generating comprehensive metrics report...")
    metrics.stop_collection()

    report = metrics.get_comprehensive_report()

    # Display results
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE METRICS REPORT")
    print("=" * 60)

    # Collection info
    collection = report["collection_info"]
    print(f"\n⏱️  Collection Duration: {collection['duration_seconds']:.2f} seconds")

    # False positive/negative analysis
    fp_fn = report["false_positive_negative"]["overall"]
    print("\n🎯 Classification Performance:")
    print(f"   Accuracy:  {fp_fn.accuracy:.2%}")
    print(f"   Precision: {fp_fn.precision:.2%}")
    print(f"   Recall:    {fp_fn.recall:.2%}")
    print(f"   F1 Score:  {fp_fn.f1_score:.2%}")

    # Strategy-specific performance
    print("\n📊 Strategy Performance:")
    for strategy_name, stats in report["false_positive_negative"][
        "by_strategy"
    ].items():
        if strategy_name != "overall":
            print(
                f"   {strategy_name:12s}: Acc={stats.accuracy:.2%}, "
                f"Prec={stats.precision:.2%}, Rec={stats.recall:.2%}"
            )

    # Spam reduction
    spam_reduction = report["spam_reduction"]["overall"]
    print("\n🛡️  Spam Reduction:")
    print(f"   Spam blocked:       {spam_reduction.spam_reduction_percentage:.1f}%")
    print(f"   Legitimate passed:  {spam_reduction.legitimate_pass_rate:.1f}%")

    # Relay load
    load = report["relay_load"]
    print("\n💻 Relay Load:")
    print(f"   Total CPU time:     {load.total_cpu_time:.3f}s")
    print(f"   Total bandwidth:    {load.total_bandwidth_bytes:,} bytes")
    print(f"   Avg CPU per event:  {load.average_cpu_time_per_event * 1000:.2f}ms")
    print(f"   Avg bytes per event: {load.average_bandwidth_per_event:.0f} bytes")

    # Latency
    latency = report["latency"]["overall"]
    print("\n⚡ Latency:")
    print(f"   Average processing: {latency.average_processing_latency * 1000:.2f}ms")
    print(f"   P95 processing:     {latency.p95_processing_latency * 1000:.2f}ms")
    print(f"   P99 processing:     {latency.p99_processing_latency * 1000:.2f}ms")

    # Strategy latencies
    print("\n🔧 Strategy Latencies:")
    for strategy_name, stats in report["latency"]["by_strategy"].items():
        print(
            f"   {strategy_name:12s}: Avg={stats['average'] * 1000:.2f}ms, "
            f"P95={stats['p95'] * 1000:.2f}ms"
        )

    # Resilience
    resilience = report["resilience"]["stats"]
    print("\n🛡️  Resilience:")
    print(f"   Offline detection rate: {resilience.offline_detection_rate:.1f}%")
    print(f"   Sybil resistance:       {resilience.sybil_resistance_score:.2f}")
    print(f"   Adaptive responses:     {resilience.adaptive_response_count}")

    # Attack timeline
    timeline = report["resilience"]["attack_timeline"]
    print("\n🎭 Attack Timeline:")
    for _timestamp, attack_type, detected in timeline:
        status = "DETECTED" if detected else "MISSED"
        print(f"   {attack_type:15s}: {status}")

    print("\n" + "=" * 60)
    print("✅ Core Metrics System Demo Complete!")
    print("=" * 60)


def demo_enhanced_engine() -> None:
    """Demonstrate the enhanced simulation engine with integrated metrics."""
    print("\n🔧 Enhanced Engine Demo")
    print("=" * 50)

    # Create configuration
    config = Config()
    config.simulation.duration = 60.0  # 1 minute simulation
    config.simulation.time_step = 0.1

    # Create enhanced engine
    engine = EnhancedSimulationEngine(config)

    # Set up event labeler
    engine.set_event_labeler(is_spam_event)

    # Register anti-spam strategies
    engine.register_anti_spam_strategy("pow", ProofOfWorkStrategy(min_difficulty=4))
    engine.register_anti_spam_strategy(
        "rate_limit", TokenBucketRateLimiting(bucket_capacity=15, refill_rate=0.25)
    )  # ~15 per minute

    print("✅ Enhanced engine initialized with integrated metrics")

    # Create test events
    legitimate_events = create_legitimate_events(10)
    spam_events = create_spam_events(5)

    print(
        f"📝 Created {len(legitimate_events)} legitimate and {len(spam_events)} spam events"
    )

    # Process events through the engine
    print("⚡ Processing events through enhanced engine...")

    # Start the engine (but don't run the full simulation loop)
    engine.core_metrics.start_collection()

    # Process individual events
    for event in legitimate_events + spam_events:
        engine.process_nostr_event(event)

    # Record some attacks
    engine.record_attack("sybil", True)
    engine.record_attack("burst_spam", False)
    engine.update_sybil_resistance(0.9)
    engine.record_adaptive_response()

    # Get comprehensive metrics
    metrics = engine.get_comprehensive_metrics()

    print("\n📊 Enhanced Engine Metrics Summary:")
    print(f"   Events processed: {metrics['simulation_info']['event_count']}")
    print(
        f"   Registered strategies: {', '.join(metrics['simulation_info']['registered_strategies'])}"
    )

    core_metrics = metrics["core_metrics"]
    spam_reduction = core_metrics["spam_reduction"]["overall"]
    print(f"   Spam reduction: {spam_reduction.spam_reduction_percentage:.1f}%")

    resilience = core_metrics["resilience"]["stats"]
    print(f"   Sybil resistance: {resilience.sybil_resistance_score:.2f}")

    print("✅ Enhanced engine demo complete!")


if __name__ == "__main__":
    # Run the core metrics demo
    demo_core_metrics_system()

    # Run the enhanced engine demo
    demo_enhanced_engine()
