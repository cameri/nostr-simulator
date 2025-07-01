"""Attack simulation scenario demonstrating various spam and abuse vectors."""

import random
import time
from typing import Any

from ..agents.adversarial.burst_spammer import BurstPattern, BurstSpammerAgent, BurstTiming
from ..anti_spam.pow import ProofOfWorkStrategy
from ..protocol.events import NostrEvent, NostrEventKind, NostrTag
from ..protocol.keys import NostrKeyPair
from ..protocol.validation import RelayPolicy


def simulate_sybil_attack(num_identities: int = 10) -> list[NostrKeyPair]:
    """Simulate a Sybil attack with multiple fake identities."""
    print(f"🎭 Generating {num_identities} Sybil identities...")
    return [NostrKeyPair.generate() for _ in range(num_identities)]


def simulate_burst_spam(
    keypair: NostrKeyPair, burst_size: int = 20
) -> list[NostrEvent]:
    """Simulate burst spam attack - many messages in quick succession."""
    print(f"💥 Generating burst spam: {burst_size} messages")

    spam_templates = [
        "🚀 URGENT: Limited time crypto offer! Act now! {}",
        "💰 You've won ${}! Claim your prize instantly!",
        "🔥 Hot investment opportunity! {} returns guaranteed!",
        "⚡ BREAKING: New crypto coin will 100x! Buy {} now!",
        "🎁 Free money alert! Get ${} in 5 minutes!",
    ]

    events = []
    current_time = int(time.time())

    for i in range(burst_size):
        template = random.choice(spam_templates)
        content = template.format(random.randint(1000, 99999))

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content=content,
            created_at=current_time + i,  # Very quick succession
            pubkey=keypair.public_key,
        )
        events.append(event)

    return events


def simulate_advanced_burst_spam() -> tuple[BurstSpammerAgent, list[NostrEvent]]:
    """Simulate advanced burst spam using BurstSpammerAgent."""
    print("💥 Creating advanced burst spam agent")

    # Configure burst attack pattern
    timing = BurstTiming(
        burst_duration=15.0,  # 15 second bursts
        burst_interval=30.0,  # 30 seconds between bursts
        messages_per_second=8.0,  # High intensity
        burst_count=3,  # 3 total bursts
        randomization=0.3,  # 30% timing variation
    )

    pattern = BurstPattern(
        timing=timing,
        initial_volume=20,  # Start with 20 messages per burst
        volume_scaling=1.8,  # Escalate by 80% each burst
        max_volume=60,  # Cap at 60 messages
        coordinated=True,  # Coordinate with other agents
        content_variation=True,  # Vary spam content
        timing_jitter=True,  # Add timing randomness
        escalation_mode=True,  # Increase intensity over time
    )

    # Create burst spammer agent
    agent = BurstSpammerAgent("burst_attacker_001", burst_pattern=pattern)

    # Simulate the attack by generating events the agent would create
    events = []
    current_time = time.time()

    # Start the attack
    agent.start_attack(current_time)

    # Simulate multiple burst cycles
    simulation_time = current_time
    while agent.attack_active and simulation_time < current_time + 300:  # 5 minute simulation
        # Check if should start a burst
        if agent.should_start_burst(simulation_time):
            agent.start_burst(simulation_time)
            print(f"   🚀 Starting burst {agent.current_burst} at {simulation_time:.1f}")

        # Check if should send message during burst
        if agent.should_send_message_in_burst(simulation_time):
            event = agent.create_spam_event(simulation_time)
            if event:
                events.append(event)

        # Update agent state
        agent.update_state(simulation_time)

        # Advance simulation time
        simulation_time += 0.5  # Advance by 0.5 seconds

    metrics = agent.get_attack_metrics()
    print(f"   📊 Attack completed: {metrics['total_bursts']} bursts, {metrics['total_messages']} messages")

    return agent, events


def simulate_hash_link_spam(keypair: NostrKeyPair) -> list[NostrEvent]:
    """Simulate hash-link spam - obfuscated malicious links."""
    print("🔗 Generating hash-link spam with obfuscated URLs")

    # Simulate obfuscated/suspicious links
    spam_links = [
        "bit.ly/3xK9mZ2 - URGENT crypto news!",
        "Check this out: tinyurl.com/crypto2024 💰",
        "Limited time: rb.gy/invest-now (expires in 1h)",
        "BREAKING: shorturl.at/wxyz123 🚀",
        "Free money here: is.gd/freecrypto 🎁",
    ]

    events = []
    current_time = int(time.time())

    for i, link_content in enumerate(spam_links):
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content=link_content,
            created_at=current_time + (i * 30),  # 30 seconds apart
            pubkey=keypair.public_key,
        )
        events.append(event)

    return events


def simulate_replay_attack(
    original_events: list[NostrEvent], attacker_keypair: NostrKeyPair
) -> list[NostrEvent]:
    """Simulate replay attack - reposting old content with new signatures."""
    print("🔄 Generating replay attack - reusing content from legitimate users")

    replayed_events = []
    current_time = int(time.time())

    for i, original in enumerate(original_events[:3]):  # Only replay first 3
        # Create new event with same content but different pubkey/timestamp
        replay_event = NostrEvent(
            kind=original.kind,
            content=f"[REPLAYED] {original.content}",  # Mark as replayed for demo
            created_at=current_time + (i * 10),
            pubkey=attacker_keypair.public_key,
        )
        replayed_events.append(replay_event)

    return replayed_events


def add_minimal_pow(event: NostrEvent, difficulty: int = 2) -> bool:
    """Add minimal PoW (attackers won't do expensive PoW)."""
    max_attempts = 100  # Very limited attempts

    for nonce in range(max_attempts):
        temp_event = NostrEvent(
            kind=event.kind,
            content=event.content,
            created_at=event.created_at,
            pubkey=event.pubkey,
            tags=event.tags
            + [NostrTag(name="nonce", values=[str(nonce), str(difficulty)])],
        )

        event_id_bytes = bytes.fromhex(temp_event.id)
        leading_zeros = 0
        for byte in event_id_bytes:
            if byte == 0:
                leading_zeros += 8
            else:
                leading_zeros += 8 - byte.bit_length()
                break

        if leading_zeros >= difficulty:
            event.tags = temp_event.tags
            event.id = temp_event.id
            return True

    return False


def test_events_against_strategies(
    events: list[NostrEvent],
    strategies: dict[str, Any],
    current_time: float,
    event_source: str,
) -> dict[str, int]:
    """Test a list of events against all strategies and return blocking stats."""

    stats = {
        "total": len(events),
        "blocked_by_pow": 0,
        "blocked_by_rate": 0,
        "allowed": 0,
    }

    for event in events:
        # Add minimal PoW for attackers
        add_minimal_pow(event, 2)

        blocked_by = []

        # Test against PoW strategy
        if "pow" in strategies:
            result = strategies["pow"].evaluate_event(event, current_time)
            if not result.allowed:
                blocked_by.append("pow")
                stats["blocked_by_pow"] += 1
            else:
                strategies["pow"].update_state(event, current_time)

        # Test against rate limiting
        if "rate_limit" in strategies:
            policy_result = strategies["rate_limit"].check_policy(event, current_time)
            if not policy_result[0]:
                blocked_by.append("rate")
                stats["blocked_by_rate"] += 1

        if not blocked_by:
            stats["allowed"] += 1

        current_time += 1  # Advance time

    return stats


def run_attack_simulation_scenario() -> None:
    """Run comprehensive attack simulation scenario."""
    print("⚔️  Nostr Simulator - Attack Simulation Scenario")
    print("=" * 60)

    # Initialize defensive strategies
    strategies = {
        "pow": ProofOfWorkStrategy(min_difficulty=8, max_difficulty=20, adaptive=False),
        "rate_limit": RelayPolicy(max_events_per_minute=5),  # Strict rate limiting
    }

    print("🛡️  Defensive Strategies:")
    print("   • Proof of Work (8 bits minimum)")
    print("   • Rate Limiting (5 events/minute)")
    print()

    # Create legitimate user for baseline
    honest_user = NostrKeyPair.generate()
    honest_events = [
        NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Good morning! Working on some interesting protocols today.",
            created_at=int(time.time()),
            pubkey=honest_user.public_key,
        ),
        NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Just finished reading about decentralized networks. Fascinating stuff!",
            created_at=int(time.time()) + 300,
            pubkey=honest_user.public_key,
        ),
    ]

    current_time = time.time()

    print("📊 Attack Simulation Results:")
    print("-" * 40)

    # Test 1: Sybil Attack
    print("1️⃣  Sybil Attack:")
    sybil_identities = simulate_sybil_attack(5)
    sybil_events = []

    for i, identity in enumerate(sybil_identities):
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content=f"Sybil identity #{i+1}: Looks legitimate but part of coordinated attack",
            created_at=int(current_time) + i,
            pubkey=identity.public_key,
        )
        sybil_events.append(event)

    sybil_stats = test_events_against_strategies(
        sybil_events, strategies, current_time, "Sybil"
    )
    print(
        f"   📈 {sybil_stats['blocked_by_pow']}/{sybil_stats['total']} blocked by PoW"
    )
    print(
        f"   ⏱️  {sybil_stats['blocked_by_rate']}/{sybil_stats['total']} blocked by rate limit"
    )
    print(f"   ✅ {sybil_stats['allowed']}/{sybil_stats['total']} messages allowed")
    print()

    # Test 2: Burst Spam Attack (Simple)
    print("2️⃣  Simple Burst Spam Attack:")
    spammer = NostrKeyPair.generate()
    burst_events = simulate_burst_spam(spammer, 15)

    burst_stats = test_events_against_strategies(
        burst_events, strategies, current_time + 100, "Burst"
    )
    print(
        f"   📈 {burst_stats['blocked_by_pow']}/{burst_stats['total']} blocked by PoW"
    )
    print(
        f"   ⏱️  {burst_stats['blocked_by_rate']}/{burst_stats['total']} blocked by rate limit"
    )
    print(f"   ✅ {burst_stats['allowed']}/{burst_stats['total']} messages allowed")
    print()

    # Test 2b: Advanced Burst Spam Attack
    print("2️⃣b Advanced Burst Spam Attack:")
    burst_agent, advanced_burst_events = simulate_advanced_burst_spam()

    advanced_burst_stats = test_events_against_strategies(
        advanced_burst_events, strategies, current_time + 200, "Advanced Burst"
    )
    print(
        f"   📈 {advanced_burst_stats['blocked_by_pow']}/{advanced_burst_stats['total']} blocked by PoW"
    )
    print(
        f"   ⏱️  {advanced_burst_stats['blocked_by_rate']}/{advanced_burst_stats['total']} blocked by rate limit"
    )
    print(f"   ✅ {advanced_burst_stats['allowed']}/{advanced_burst_stats['total']} messages allowed")
    print()

    # Test 3: Hash-Link Spam
    print("3️⃣  Hash-Link Spam Attack:")
    link_spammer = NostrKeyPair.generate()
    link_events = simulate_hash_link_spam(link_spammer)

    link_stats = test_events_against_strategies(
        link_events, strategies, current_time + 200, "Link"
    )
    print(f"   📈 {link_stats['blocked_by_pow']}/{link_stats['total']} blocked by PoW")
    print(
        f"   ⏱️  {link_stats['blocked_by_rate']}/{link_stats['total']} blocked by rate limit"
    )
    print(f"   ✅ {link_stats['allowed']}/{link_stats['total']} messages allowed")
    print()

    # Test 4: Replay Attack
    print("4️⃣  Replay Attack:")
    replay_attacker = NostrKeyPair.generate()
    replay_events = simulate_replay_attack(honest_events, replay_attacker)

    replay_stats = test_events_against_strategies(
        replay_events, strategies, current_time + 300, "Replay"
    )
    print(
        f"   📈 {replay_stats['blocked_by_pow']}/{replay_stats['total']} blocked by PoW"
    )
    print(
        f"   ⏱️  {replay_stats['blocked_by_rate']}/{replay_stats['total']} blocked by rate limit"
    )
    print(f"   ✅ {replay_stats['allowed']}/{replay_stats['total']} messages allowed")
    print()

    # Summary statistics
    total_attacks = (
        sybil_stats["total"]
        + burst_stats["total"]
        + link_stats["total"]
        + replay_stats["total"]
    )
    total_blocked_pow = (
        sybil_stats["blocked_by_pow"]
        + burst_stats["blocked_by_pow"]
        + link_stats["blocked_by_pow"]
        + replay_stats["blocked_by_pow"]
    )
    total_blocked_rate = (
        sybil_stats["blocked_by_rate"]
        + burst_stats["blocked_by_rate"]
        + link_stats["blocked_by_rate"]
        + replay_stats["blocked_by_rate"]
    )
    total_allowed = (
        sybil_stats["allowed"]
        + burst_stats["allowed"]
        + link_stats["allowed"]
        + replay_stats["allowed"]
    )

    print("📋 Overall Attack Defense Summary:")
    print(f"   🎯 Total attack events: {total_attacks}")
    print(
        f"   🛡️  Blocked by PoW: {total_blocked_pow} ({total_blocked_pow/total_attacks*100:.1f}%)"
    )
    print(
        f"   🛡️  Blocked by rate limit: {total_blocked_rate} ({total_blocked_rate/total_attacks*100:.1f}%)"
    )
    print(
        f"   ⚠️  Events that got through: {total_allowed} ({total_allowed/total_attacks*100:.1f}%)"
    )
    print()

    print("🔍 Key Insights:")
    print("• Proof of Work is highly effective against automated spam")
    print("• Rate limiting catches burst attacks and coordinated spam")
    print("• Sybil attacks are expensive when PoW is required")
    print("• Multiple defense layers provide better protection")
    print("• Attackers must balance cost vs. potential reach")


if __name__ == "__main__":
    run_attack_simulation_scenario()
