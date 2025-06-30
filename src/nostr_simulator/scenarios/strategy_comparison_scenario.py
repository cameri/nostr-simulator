"""Strategy comparison scenario for detailed anti-spam strategy analysis."""

import time
from typing import Any

from ..anti_spam.pow import ProofOfWorkStrategy
from ..protocol.events import NostrEvent, NostrEventKind, NostrTag
from ..protocol.keys import NostrKeyPair
from ..protocol.validation import RelayPolicy


def add_simple_pow(
    event: NostrEvent, difficulty: int, max_attempts: int = 5000
) -> bool:
    """Add PoW to an event with limited attempts for comparison."""
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


def test_pow_strategies() -> dict[str, dict[str, dict[str, Any]]]:
    """Test PoW strategies with different difficulty levels."""
    print("🔨 Proof of Work Strategy Comparison")
    print("-" * 45)

    # Create different difficulty strategies
    strategies = {
        "Low (4 bits)": ProofOfWorkStrategy(min_difficulty=4, adaptive=False),
        "Medium (8 bits)": ProofOfWorkStrategy(min_difficulty=8, adaptive=False),
        "High (12 bits)": ProofOfWorkStrategy(min_difficulty=12, adaptive=False),
    }

    # Test scenarios with different content types
    scenarios = [
        (
            "Legitimate message",
            "Hey everyone! Excited about this decentralized protocol.",
        ),
        ("Spam attempt", "🚀 URGENT: Buy this cryptocurrency NOW! Limited time offer!"),
        ("Borderline content", "Check out my new blog post about investing."),
        ("Social post", "Just had a great coffee ☕ at the local cafe!"),
        (
            "Technical discussion",
            "Implementing merkle trees for data integrity verification.",
        ),
    ]

    keypair = NostrKeyPair.generate()

    print(f"Testing with keypair: {keypair.public_key[:16]}...")
    print()

    results = {}

    for scenario_name, content in scenarios:
        print(f"📝 Scenario: {scenario_name}")
        print(f"   Content: '{content[:60]}{'...' if len(content) > 60 else ''}'")

        scenario_results = {}

        for strategy_name, strategy in strategies.items():
            event = NostrEvent(
                kind=NostrEventKind.TEXT_NOTE,
                content=content,
                created_at=int(time.time()),
                pubkey=keypair.public_key,
            )

            # Test without PoW
            result = strategy.evaluate_event(event, time.time())
            without_pow = "✅ PASS" if result.allowed else "❌ FAIL"

            # Try to add PoW
            pow_start_time = time.time()
            pow_success = add_simple_pow(event, strategy.current_difficulty)
            pow_time = time.time() - pow_start_time

            if pow_success:
                result_with_pow = strategy.evaluate_event(event, time.time())
                with_pow = "✅ PASS" if result_with_pow.allowed else "❌ FAIL"
                strategy.update_state(event, time.time())
                pow_status = f"⚡ {pow_time:.3f}s"
            else:
                with_pow = "⏰ TIMEOUT"
                pow_status = "⏰ >5000 attempts"

            scenario_results[strategy_name] = {
                "without_pow": without_pow,
                "with_pow": with_pow,
                "pow_time": pow_time if pow_success else None,
                "pow_status": pow_status,
            }

            print(
                f"   {strategy_name:12} | No PoW: {without_pow} | With PoW: {with_pow} | Time: {pow_status}"
            )

        results[scenario_name] = scenario_results
        print()

    return results


def test_rate_limiting_strategies() -> None:
    """Test rate limiting with different configurations."""
    print("🚦 Rate Limiting Strategy Comparison")
    print("-" * 40)

    # Different rate limiting policies
    policies = {
        "Strict (2/min)": RelayPolicy(max_events_per_minute=2),
        "Moderate (10/min)": RelayPolicy(max_events_per_minute=10),
        "Lenient (30/min)": RelayPolicy(max_events_per_minute=30),
    }

    keypair = NostrKeyPair.generate()
    current_time = time.time()

    print(f"Testing with keypair: {keypair.public_key[:16]}...")
    print()

    # Simulate different posting patterns
    posting_patterns = [
        ("Normal posting", 0.5, 10),  # 1 post every 30 seconds, 10 posts
        ("Burst posting", 0.1, 15),  # 1 post every 6 seconds, 15 posts
        ("Spam flood", 0.05, 25),  # 1 post every 3 seconds, 25 posts
    ]

    for pattern_name, interval, count in posting_patterns:
        print(f"📊 Pattern: {pattern_name} ({count} posts, {interval}s intervals)")

        # Create events for this pattern
        events = []
        for i in range(count):
            event = NostrEvent(
                kind=NostrEventKind.TEXT_NOTE,
                content=f"{pattern_name} message #{i+1}",
                created_at=int(current_time + i * interval),
                pubkey=keypair.public_key,
            )
            events.append(event)

        # Test against each policy
        for policy_name, policy in policies.items():
            accepted = 0
            rejected = 0

            # Reset policy state
            policy._event_counts.clear()

            for event in events:
                event_time = event.created_at
                allowed, reason = policy.check_policy(event, event_time)

                if allowed:
                    accepted += 1
                else:
                    rejected += 1

            acceptance_rate = (accepted / len(events)) * 100
            print(
                f"   {policy_name:15} | Accepted: {accepted:2d}/{count} ({acceptance_rate:4.1f}%)"
            )

        print()


def test_combined_strategies() -> None:
    """Test combined PoW + Rate Limiting strategies."""
    print("🎯 Combined Strategy Effectiveness")
    print("-" * 35)

    # Combined strategy configuration
    pow_strategy = ProofOfWorkStrategy(min_difficulty=6, adaptive=False)
    rate_policy = RelayPolicy(max_events_per_minute=5)

    print("Configuration: PoW (6 bits) + Rate Limiting (5/min)")
    print()

    # Test with different user types
    user_types = [
        (
            "Honest user",
            1,
            [
                "Good morning everyone!",
                "Interesting article about crypto",
                "Thanks for sharing",
            ],
        ),
        (
            "Casual spammer",
            3,
            ["Buy crypto now!", "Limited time offer!", "Get rich quick!"],
        ),
        (
            "Aggressive spammer",
            8,
            [
                "URGENT CRYPTO!",
                "FREE MONEY!",
                "CLICK HERE!",
                "SCAM ALERT!",
                "BUY NOW!",
                "PROFIT!",
                "MOONSHOT!",
                "LAMBO TIME!",
            ],
        ),
    ]

    current_time = time.time()
    overall_stats = {"total": 0, "pow_blocked": 0, "rate_blocked": 0, "allowed": 0}

    for user_type, message_count, messages in user_types:
        keypair = NostrKeyPair.generate()

        print(f"👤 {user_type} ({keypair.public_key[:8]}...):")

        user_stats = {"total": 0, "pow_blocked": 0, "rate_blocked": 0, "allowed": 0}
        time_offset = 0

        # Extend messages if needed
        extended_messages = (messages * ((message_count // len(messages)) + 1))[
            :message_count
        ]

        for i, content in enumerate(extended_messages):
            event = NostrEvent(
                kind=NostrEventKind.TEXT_NOTE,
                content=content,
                created_at=int(current_time + time_offset),
                pubkey=keypair.public_key,
            )

            user_stats["total"] += 1
            overall_stats["total"] += 1

            # Test rate limiting first
            rate_allowed, rate_reason = rate_policy.check_policy(
                event, current_time + time_offset
            )
            if not rate_allowed:
                user_stats["rate_blocked"] += 1
                overall_stats["rate_blocked"] += 1
                time_offset += 5  # 5 seconds between attempts
                continue

            # Test PoW
            pow_result = pow_strategy.evaluate_event(event, current_time + time_offset)
            if not pow_result.allowed:
                # Simulate honest users doing PoW, spammers trying minimal PoW
                if "honest" in user_type.lower():
                    if add_simple_pow(event, pow_strategy.current_difficulty):
                        pow_result = pow_strategy.evaluate_event(
                            event, current_time + time_offset
                        )
                        pow_strategy.update_state(event, current_time + time_offset)

                if not pow_result.allowed:
                    user_stats["pow_blocked"] += 1
                    overall_stats["pow_blocked"] += 1
                    time_offset += 5
                    continue

            # Event passed both checks
            user_stats["allowed"] += 1
            overall_stats["allowed"] += 1
            time_offset += 5

        # Print user statistics
        total = user_stats["total"]
        if total > 0:
            pow_rate = (user_stats["pow_blocked"] / total) * 100
            rate_rate = (user_stats["rate_blocked"] / total) * 100
            allowed_rate = (user_stats["allowed"] / total) * 100

            print(
                f"   📊 {total} messages: PoW blocked {pow_rate:.1f}%, "
                f"Rate blocked {rate_rate:.1f}%, Allowed {allowed_rate:.1f}%"
            )
        print()

    # Overall statistics
    total = overall_stats["total"]
    if total > 0:
        print("📋 Overall Effectiveness:")
        print(f"   Total messages tested: {total}")
        print(
            f"   Blocked by PoW: {overall_stats['pow_blocked']} ({overall_stats['pow_blocked']/total*100:.1f}%)"
        )
        print(
            f"   Blocked by rate limiting: {overall_stats['rate_blocked']} ({overall_stats['rate_blocked']/total*100:.1f}%)"
        )
        print(
            f"   Messages allowed: {overall_stats['allowed']} ({overall_stats['allowed']/total*100:.1f}%)"
        )


def run_strategy_comparison_scenario() -> None:
    """Run comprehensive strategy comparison scenario."""
    print("⚔️  Nostr Simulator - Strategy Comparison Scenario")
    print("=" * 60)
    print()

    # Test individual strategies
    print("Part 1: Individual Strategy Analysis")
    print("=" * 40)
    test_pow_strategies()
    print()

    test_rate_limiting_strategies()
    print()

    # Test combined strategies
    print("Part 2: Combined Strategy Analysis")
    print("=" * 40)
    test_combined_strategies()
    print()

    print("📊 Scenario Summary:")
    print(
        "• PoW effectiveness increases with difficulty but so does computational cost"
    )
    print("• Rate limiting is effective against burst attacks")
    print("• Combined strategies provide defense in depth")
    print("• Different user types show different blocking patterns")
    print("• Higher difficulty PoW may timeout for some legitimate content")


if __name__ == "__main__":
    run_strategy_comparison_scenario()
