"""Scenario for testing reputation tokens anti-spam strategy."""

from __future__ import annotations

import time

from nostr_simulator.anti_spam.reputation_tokens import ReputationTokenStrategy
from nostr_simulator.protocol.events import NostrEvent, NostrEventKind
from nostr_simulator.protocol.keys import NostrKeyPair


def create_text_note_event(content: str, keypair: NostrKeyPair) -> NostrEvent:
    """Create a text note event."""
    return NostrEvent(
        kind=NostrEventKind.TEXT_NOTE,
        content=content,
        created_at=int(time.time()),
        pubkey=keypair.public_key,
    )


def run_reputation_tokens_scenario() -> None:
    """Run the reputation tokens anti-spam strategy scenario."""
    print("🪙 Nostr Simulator - Reputation Tokens Scenario")
    print("=" * 50)

    # Create reputation tokens strategy
    reputation_strategy = ReputationTokenStrategy(
        initial_tokens=10.0,
        post_cost=1.0,
        earn_rate=0.1,
        decay_rate=0.001,
        reputation_threshold=0.8,
        max_tokens=100.0,
    )

    # Create test users
    print("👥 Creating test users...")
    honest_user = NostrKeyPair.generate()
    spammer = NostrKeyPair.generate()
    trusted_user = NostrKeyPair.generate()

    print(f"Honest user: {honest_user.public_key[:16]}...")
    print(f"Spammer: {spammer.public_key[:16]}...")
    print(f"Trusted user: {trusted_user.public_key[:16]}...")

    # Test 1: Normal user posting behavior
    print("\n📝 Test 1: Normal user posting behavior")
    print("-" * 40)

    for i in range(5):
        event = create_text_note_event(f"Honest post {i+1}", honest_user)
        result = reputation_strategy.evaluate_event(event, time.time())

        print(f"Post {i+1}: {'✅ Allowed' if result.allowed else '❌ Blocked'} - {result.reason}")

        if result.allowed:
            reputation_strategy.update_state(event, time.time())
            account_info = reputation_strategy.get_account_info(honest_user.public_key)
            if account_info:
                print(f"  Tokens: {account_info['tokens']:.1f}, Reputation: {account_info['reputation_score']:.2f}")

    # Test 2: Spam burst attack
    print("\n💥 Test 2: Spam burst attack")
    print("-" * 40)

    blocked_count = 0
    allowed_count = 0

    for i in range(15):  # Try to post 15 messages rapidly
        event = create_text_note_event(f"Spam message {i+1}", spammer)
        result = reputation_strategy.evaluate_event(event, time.time())

        if result.allowed:
            allowed_count += 1
            reputation_strategy.update_state(event, time.time())
        else:
            blocked_count += 1

        if i < 5 or not result.allowed:  # Show first 5 and any blocked
            print(f"Spam {i+1}: {'✅ Allowed' if result.allowed else '❌ Blocked'} - {result.reason}")

    print(f"\nSpam results: {allowed_count} allowed, {blocked_count} blocked")

    spammer_info = reputation_strategy.get_account_info(spammer.public_key)
    if spammer_info:
        print(f"Spammer tokens: {spammer_info['tokens']:.1f}, Reputation: {spammer_info['reputation_score']:.2f}")

    # Test 3: Building high reputation
    print("\n⭐ Test 3: Building high reputation user")
    print("-" * 40)

    # Manually boost reputation to simulate long-term good behavior
    trusted_account = reputation_strategy._get_or_create_account(trusted_user.public_key, time.time())
    trusted_account.earned_total += 50.0  # Simulate lots of earned tokens
    trusted_account.spent_total = 10.0    # Minimal spending
    trusted_account.update_reputation_score(time.time())

    print(f"Boosted reputation score: {trusted_account.reputation_score:.2f}")

    # Test high-reputation user bypassing costs
    for i in range(3):
        event = create_text_note_event(f"Trusted user post {i+1}", trusted_user)
        result = reputation_strategy.evaluate_event(event, time.time())

        print(f"Trusted post {i+1}: {'✅ Allowed' if result.allowed else '❌ Blocked'} - {result.reason}")

        if result.allowed:
            reputation_strategy.update_state(event, time.time())

    # Test 4: Token distribution analysis
    print("\n📊 Test 4: Token distribution analysis")
    print("-" * 40)

    distribution = reputation_strategy.get_token_distribution()
    print("Token distribution across users:")
    for range_name, count in distribution.items():
        if count > 0:
            print(f"  {range_name} tokens: {count} users")

    # Test 5: Token decay over time
    print("\n⏰ Test 5: Token decay over time")
    print("-" * 40)

    # Simulate time passing (1 day = 86400 seconds)
    future_time = time.time() + 86400

    # Check decay for honest user
    honest_account = reputation_strategy._get_or_create_account(honest_user.public_key, time.time())
    tokens_before = honest_account.tokens
    honest_account.apply_decay(reputation_strategy.decay_rate, future_time)
    tokens_after = honest_account.tokens

    print(f"Honest user tokens after 1 day:")
    print(f"  Before decay: {tokens_before:.2f}")
    print(f"  After decay: {tokens_after:.2f}")
    print(f"  Decay amount: {tokens_before - tokens_after:.2f}")

    print("\n✅ Reputation tokens scenario completed!")


if __name__ == "__main__":
    run_reputation_tokens_scenario()
