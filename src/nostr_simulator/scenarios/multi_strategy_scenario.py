"""Multi-strategy anti-spam scenario demonstrating various defense mechanisms."""

import time
from typing import Dict, List, Tuple, Any

from ..anti_spam.pow import ProofOfWorkStrategy
from ..protocol.events import NostrEvent, NostrEventKind, NostrTag
from ..protocol.keys import NostrKeyPair
from ..protocol.validation import RelayPolicy


def create_sample_event(content: str, keypair: NostrKeyPair, kind: NostrEventKind = NostrEventKind.TEXT_NOTE) -> NostrEvent:
    """Create a sample Nostr event."""
    return NostrEvent(
        kind=kind,
        content=content,
        created_at=int(time.time()),
        pubkey=keypair.public_key,
    )


def add_pow_to_event(event: NostrEvent, difficulty: int, max_attempts: int = 10000) -> bool:
    """Add proof of work to an event by finding a valid nonce."""
    nonce = 0

    while nonce < max_attempts:
        # Create temporary event with nonce tag
        temp_event = NostrEvent(
            kind=event.kind,
            content=event.content,
            created_at=event.created_at,
            pubkey=event.pubkey,
            tags=event.tags + [NostrTag(name="nonce", values=[str(nonce), str(difficulty)])]
        )

        # Calculate leading zeros in event ID
        event_id_bytes = bytes.fromhex(temp_event.id)
        leading_zeros = 0
        for byte in event_id_bytes:
            if byte == 0:
                leading_zeros += 8
            else:
                leading_zeros += (8 - byte.bit_length())
                break

        if leading_zeros >= difficulty:
            # Found valid PoW!
            event.tags = temp_event.tags
            event.id = temp_event.id
            return True

        nonce += 1

    return False


def simulate_user_behavior(
    user_type: str,
    keypair: NostrKeyPair,
    strategies: Dict[str, Any],
    current_time: float
) -> List[Tuple[NostrEvent, Dict[str, bool]]]:
    """Simulate different user behavior patterns."""

    results = []

    if user_type == "honest":
        messages = [
            "Good morning, everyone! How's your day going?",
            "Just read an interesting article about decentralized networks.",
            "Working on some code today. Love the problem-solving aspect.",
        ]

        for content in messages:
            event = create_sample_event(content, keypair)

            # Honest users are willing to do reasonable PoW
            if "pow" in strategies:
                add_pow_to_event(event, strategies["pow"].current_difficulty)

            # Test event against all strategies
            strategy_results = {}
            for name, strategy in strategies.items():
                if name == "pow":
                    result = strategy.evaluate_event(event, current_time)
                    strategy_results[name] = result.allowed
                    if result.allowed:
                        strategy.update_state(event, current_time)
                elif name == "rate_limit":
                    policy_result = strategy.check_policy(event, current_time)
                    strategy_results[name] = policy_result[0]  # (allowed, reason)

            results.append((event, strategy_results))
            current_time += 60  # 1 minute between honest messages

    elif user_type == "spammer":
        # Spammers send many messages quickly
        spam_messages = [
            "🚀 CRYPTO MOON SOON! Buy now at cryptoscam.com 🚀",
            "💰 URGENT: Limited time offer! Click here for FREE MONEY 💰",
            "🔥 HOT SINGLES in your area! Click now! 🔥",
            "⚡ BITCOIN GIVEAWAY! Send 1 BTC get 2 back! ⚡",
            "🎁 You've won $10,000! Claim your prize now! 🎁",
        ] * 3  # Repeat spam messages

        for content in spam_messages:
            event = create_sample_event(content, keypair)

            # Spammers typically won't do PoW (too expensive)
            # They might try very low difficulty PoW
            if "pow" in strategies:
                add_pow_to_event(event, min(2, strategies["pow"].current_difficulty))

            # Test event against all strategies
            strategy_results = {}
            for name, strategy in strategies.items():
                if name == "pow":
                    result = strategy.evaluate_event(event, current_time)
                    strategy_results[name] = result.allowed
                    if result.allowed:
                        strategy.update_state(event, current_time)
                elif name == "rate_limit":
                    policy_result = strategy.check_policy(event, current_time)
                    strategy_results[name] = policy_result[0]

            results.append((event, strategy_results))
            current_time += 5  # 5 seconds between spam messages (high frequency)

    elif user_type == "sybil":
        # Sybil attacker uses multiple identities
        sybil_keypairs = [NostrKeyPair.generate() for _ in range(5)]

        for i, sybil_keypair in enumerate(sybil_keypairs):
            content = f"Identity #{i+1}: This looks like a normal message but I'm a sybil!"
            event = create_sample_event(content, sybil_keypair)

            # Sybil attackers might do minimal PoW
            if "pow" in strategies:
                add_pow_to_event(event, max(1, strategies["pow"].current_difficulty - 2))

            strategy_results = {}
            for name, strategy in strategies.items():
                if name == "pow":
                    result = strategy.evaluate_event(event, current_time)
                    strategy_results[name] = result.allowed
                    if result.allowed:
                        strategy.update_state(event, current_time)
                elif name == "rate_limit":
                    policy_result = strategy.check_policy(event, current_time)
                    strategy_results[name] = policy_result[0]

            results.append((event, strategy_results))
            current_time += 10  # 10 seconds between sybil messages

    return results


def run_multi_strategy_scenario() -> None:
    """Run a comprehensive scenario testing multiple anti-spam strategies."""
    print("🎯 Nostr Simulator - Multi-Strategy Anti-Spam Scenario")
    print("=" * 60)

    # Initialize strategies
    strategies = {
        "pow": ProofOfWorkStrategy(min_difficulty=6, max_difficulty=20, adaptive=True),
        "rate_limit": RelayPolicy(max_events_per_minute=10)
    }

    print("🛡️  Initialized Anti-Spam Strategies:")
    print("   • Proof of Work (adaptive, 6-20 bits)")
    print("   • Rate Limiting (10 events/minute)")
    print()

    # Create different user types
    honest_user = NostrKeyPair.generate()
    spammer = NostrKeyPair.generate()
    current_time = time.time()

    # Track overall statistics
    total_stats: Dict[str, Dict[str, Any]] = {
        "honest": {"total": 0, "blocked": {"pow": 0, "rate_limit": 0}},
        "spammer": {"total": 0, "blocked": {"pow": 0, "rate_limit": 0}},
        "sybil": {"total": 0, "blocked": {"pow": 0, "rate_limit": 0}}
    }

    # Simulate different user types
    for user_type, keypair in [
        ("honest", honest_user),
        ("spammer", spammer),
        ("sybil", spammer)  # Sybil uses different keypairs internally
    ]:
        print(f"👤 Simulating {user_type.upper()} user behavior:")
        print(f"   Public key: {keypair.public_key[:16]}...")

        results = simulate_user_behavior(user_type, keypair, strategies, current_time)

        # Analyze results
        for event, strategy_results in results:
            total_stats[user_type]["total"] += 1

            allowed_by_all = all(strategy_results.values())
            blocked_by = [name for name, allowed in strategy_results.items() if not allowed]

            status = "✅ ALLOWED" if allowed_by_all else f"❌ BLOCKED by {', '.join(blocked_by)}"
            print(f"   📝 '{event.content[:40]}...' → {status}")

            # Update blocking stats
            for strategy_name in blocked_by:
                total_stats[user_type]["blocked"][strategy_name] += 1

        print()

    # Print final statistics
    print("📊 Final Statistics:")
    print("=" * 40)

    for user_type, stats in total_stats.items():
        if stats["total"] > 0:
            print(f"{user_type.upper()} users:")
            print(f"  Total messages: {stats['total']}")

            for strategy_name, blocked_count in stats["blocked"].items():
                block_rate = (blocked_count / stats["total"]) * 100
                print(f"  Blocked by {strategy_name}: {blocked_count}/{stats['total']} ({block_rate:.1f}%)")
            print()

    # Strategy-specific metrics
    print("🔧 Strategy Metrics:")
    for name, strategy in strategies.items():
        if hasattr(strategy, 'get_metrics'):
            metrics = strategy.get_metrics()
            print(f"{name.upper()}: {metrics}")

    print()
    print("📝 Scenario Insights:")
    print("• Honest users typically pass all filters (willing to do PoW, reasonable rate)")
    print("• Spammers are blocked by PoW requirements and rate limiting")
    print("• Sybil attackers may bypass rate limits but struggle with PoW costs")
    print("• Multiple strategies provide defense in depth")


if __name__ == "__main__":
    run_multi_strategy_scenario()
