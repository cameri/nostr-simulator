"""Proof of Work anti-spam strategy scenario."""

import time
from typing import List

from ..anti_spam.pow import ProofOfWorkStrategy
from ..protocol.events import NostrEvent, NostrEventKind, NostrTag
from ..protocol.keys import NostrKeyPair


def create_sample_event(content: str, keypair: NostrKeyPair) -> NostrEvent:
    """Create a sample Nostr event."""
    return NostrEvent(
        kind=NostrEventKind.TEXT_NOTE,
        content=content,
        created_at=int(time.time()),
        pubkey=keypair.public_key,
    )


def add_proof_of_work(event: NostrEvent, difficulty: int) -> bool:
    """Add proof of work to an event by finding a valid nonce."""
    print(f"🔨 Mining PoW for event: '{event.content[:50]}...' (difficulty: {difficulty})")

    start_time = time.time()
    nonce = 0
    max_attempts = 100000  # Prevent infinite loops

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
            end_time = time.time()
            print(f"✅ PoW found! Nonce: {nonce}, Time: {end_time - start_time:.2f}s, Leading zeros: {leading_zeros}")
            return True

        nonce += 1

    print(f"❌ PoW mining timed out after {max_attempts} attempts")
    return False


def run_pow_scenario():
    """Run the Proof of Work anti-spam strategy scenario."""
    print("🎯 Nostr Simulator - Proof of Work Scenario")
    print("=" * 50)

    # Create PoW strategy with different difficulty levels
    easy_pow = ProofOfWorkStrategy(min_difficulty=4, max_difficulty=20, adaptive=False)
    medium_pow = ProofOfWorkStrategy(min_difficulty=8, max_difficulty=20, adaptive=False)
    hard_pow = ProofOfWorkStrategy(min_difficulty=12, max_difficulty=20, adaptive=False)

    # Create keypair for events
    keypair = NostrKeyPair.generate()

    # Test events
    test_events = [
        "Hello, Nostr! This is my first message.",
        "Spam message #1 - Buy crypto now!",
        "Spam message #2 - Click this link!",
        "Legitimate message about decentralized protocols.",
        "Another spam attempt - Get rich quick!"
    ]

    print(f"👤 Using public key: {keypair.public_key[:16]}...")
    print()

    for i, (content, strategy, strategy_name) in enumerate([
        (test_events[0], easy_pow, "Easy PoW (4 bits)"),
        (test_events[1], medium_pow, "Medium PoW (8 bits)"),
        (test_events[2], hard_pow, "Hard PoW (12 bits)")
    ]):
        print(f"📝 Test {i+1}: {strategy_name}")
        print(f"   Message: '{content}'")

        # Create event
        event = create_sample_event(content, keypair)

        # Test without PoW first
        result = strategy.evaluate_event(event, time.time())
        print(f"   Without PoW: {'✅ ALLOWED' if result.allowed else '❌ BLOCKED'} - {result.reason}")

        # Add PoW and test again
        if add_proof_of_work(event, strategy.current_difficulty):
            result = strategy.evaluate_event(event, time.time())
            print(f"   With PoW: {'✅ ALLOWED' if result.allowed else '❌ BLOCKED'} - {result.reason}")
            strategy.update_state(event, time.time())

        print(f"   Strategy metrics: {strategy.get_metrics()}")
        print()

    print("🔄 Testing adaptive difficulty adjustment...")
    adaptive_pow = ProofOfWorkStrategy(
        min_difficulty=4,
        max_difficulty=16,
        target_solve_time=2.0,
        adaptive=True
    )

    # Simulate multiple events to trigger difficulty adjustment
    for i in range(5):
        content = f"Adaptive test message #{i+1}"
        event = create_sample_event(content, keypair)

        print(f"   Event {i+1}: Current difficulty = {adaptive_pow.current_difficulty}")

        if add_proof_of_work(event, adaptive_pow.current_difficulty):
            result = adaptive_pow.evaluate_event(event, time.time())
            adaptive_pow.update_state(event, time.time())
            print(f"   Result: {result.reason}")

    print(f"   Final metrics: {adaptive_pow.get_metrics()}")
    print()

    print("📊 Scenario Summary:")
    print("- Proof of Work acts as a computational barrier to spam")
    print("- Higher difficulty = more computation required = harder to spam")
    print("- Adaptive difficulty adjusts based on solving times")
    print("- Legitimate users pay computational cost, but spammers pay much more")


if __name__ == "__main__":
    run_pow_scenario()
