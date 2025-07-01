#!/usr/bin/env python3
"""Demo script for replay attack functionality."""

import time

from nostr_simulator.agents.adversarial.replay_attacker import (
    ReplayAttackerAgent,
    ReplayPattern,
    ReplayStrategy,
    ReplayTiming,
)
from nostr_simulator.protocol.events import NostrEvent, NostrEventKind
from nostr_simulator.protocol.keys import NostrKeyPair


def demo_replay_attack() -> (
    tuple[ReplayAttackerAgent, list[NostrEvent], list[NostrEvent]]
):
    """Demonstrate replay attack functionality."""
    print("🔁 Replay Attack Demo")
    print("=" * 50)

    # Create some legitimate events to be replayed
    legitimate_events = []
    print("\n📝 Creating legitimate events...")

    for i in range(5):
        keypair = NostrKeyPair.generate()
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content=f"Legitimate message {i+1} from honest user",
            created_at=int(
                time.time() - 3600 + (i * 300)
            ),  # 1 hour ago, spread over 20 minutes
            pubkey=keypair.public_key,
        )
        legitimate_events.append(event)
        print(
            f"   ✅ Event {i+1}: '{event.content[:30]}...' from {event.pubkey[:16]}..."
        )

    # Configure replay attack
    print("\n⚙️  Configuring replay attack...")
    timing = ReplayTiming(
        collection_duration=30.0,  # Short for demo
        replay_delay=5.0,
        replay_interval=2.0,
        replay_batch_size=2,
        timing_jitter=True,
    )

    strategy = ReplayStrategy(
        target_event_kinds=[NostrEventKind.TEXT_NOTE],
        min_event_age=30.0,  # 30 seconds minimum age for demo
        amplification_factor=2,  # Replay each event twice
        key_rotation=True,
        timestamp_modification=True,
        content_modification=True,
        detection_evasion=True,
    )

    pattern = ReplayPattern(
        timing=timing,
        strategy=strategy,
        collection_phase=True,
        replay_phase=True,
    )

    # Create attacker
    attacker = ReplayAttackerAgent("demo_replay_attacker", replay_pattern=pattern)
    print(f"   🎯 Created attacker with {len(attacker.replay_keys)} replay keys")

    # Start attack (collection phase)
    current_time = time.time()
    attacker.start_attack(current_time)
    print(f"\n🎬 Attack started at {current_time:.1f}")
    print(f"   📥 Collection phase active: {attacker.collection_active}")

    # Simulate collecting events (make them old enough)
    print("\n📊 Collecting legitimate events...")
    for i, event in enumerate(legitimate_events):
        collect_time = current_time - 120 + (i * 2)  # Collected 2 minutes ago
        attacker.collect_event(event, collect_time, f"relay_{i}")
        print(f"   📥 Collected event {i+1} from relay_{i}")

    # Wait to make events old enough for replay
    time.sleep(1)  # Brief pause

    print("\n📊 Collection stats:")
    print(f"   - Events collected: {len(attacker.collected_events)}")
    print(f"   - Total collected: {attacker.total_events_collected}")

    # Transition to replay phase
    replay_time = current_time + timing.collection_duration + timing.replay_delay
    attacker.start_replay_phase(replay_time)
    print(f"\n🔄 Replay phase started at {replay_time:.1f}")
    print(f"   - Events queued for replay: {len(attacker.events_to_replay)}")

    # Simulate replay process
    print("\n🎭 Performing replay attacks...")
    simulation_time = replay_time
    replayed_events = []
    replay_count = 0

    while (
        attacker.replay_active
        and replay_count < 10  # Limit for demo
        and simulation_time < replay_time + 60  # 1 minute limit
    ):
        if attacker.should_replay_now(simulation_time):
            batch_events = attacker.perform_replay(simulation_time)
            replayed_events.extend(batch_events)
            replay_count += len(batch_events)

            if batch_events:
                print(
                    f"   🔄 Replayed {len(batch_events)} events at {simulation_time:.1f}"
                )
                for event in batch_events:
                    original_key = event.pubkey[:16]
                    print(f"      - '{event.content[:40]}...' from {original_key}...")

        simulation_time += 1.0  # Advance 1 second

    # Final results
    metrics = attacker.get_attack_metrics()
    print("\n📊 Attack Summary:")
    print(f"   - Events collected: {metrics['total_events_collected']}")
    print(f"   - Events replayed: {metrics['total_events_replayed']}")
    print(f"   - Total amplifications: {metrics['total_amplifications']}")
    print(f"   - Active replay keys: {metrics['active_replay_keys']}")
    print(f"   - Detection events: {metrics['detection_events']}")

    print("\n🎯 Attack completed successfully!")
    print(f"   Original events: {len(legitimate_events)}")
    print(f"   Replayed events: {len(replayed_events)}")
    print(
        f"   Amplification ratio: {len(replayed_events) / len(legitimate_events):.1f}x"
    )

    # Show key rotation
    print("\n🔑 Key Usage:")
    used_keys = {event.pubkey for event in replayed_events}
    original_keys = {event.pubkey for event in legitimate_events}

    print(f"   - Original keys: {len(original_keys)}")
    print(f"   - Replay keys used: {len(used_keys)}")
    print(f"   - Key overlap: {'Yes' if used_keys & original_keys else 'No'}")

    return attacker, legitimate_events, replayed_events


if __name__ == "__main__":
    demo_replay_attack()
