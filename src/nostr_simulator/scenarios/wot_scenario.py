"""Web of Trust anti-spam strategy scenario."""

import time

from ..anti_spam.wot import WebOfTrustStrategy
from ..protocol.events import NostrEvent, NostrEventKind, NostrTag
from ..protocol.keys import NostrKeyPair


def create_contact_list_event(
    followees: list[str], keypair: NostrKeyPair
) -> NostrEvent:
    """Create a contact list event with followed pubkeys."""
    tags = [NostrTag("p", [pubkey]) for pubkey in followees]

    return NostrEvent(
        kind=NostrEventKind.CONTACTS,
        content="",
        created_at=int(time.time()),
        pubkey=keypair.public_key,
        tags=tags,
    )


def create_text_note_event(content: str, keypair: NostrKeyPair) -> NostrEvent:
    """Create a text note event."""
    return NostrEvent(
        kind=NostrEventKind.TEXT_NOTE,
        content=content,
        created_at=int(time.time()),
        pubkey=keypair.public_key,
    )


def run_wot_scenario() -> None:
    """Run the Web of Trust anti-spam strategy scenario."""
    print("🎯 Nostr Simulator - Web of Trust Scenario")
    print("=" * 50)

    # Create WoT strategy with moderate trust requirements
    wot_strategy = WebOfTrustStrategy(
        min_trust_score=0.5,
        trust_decay_factor=0.99,
        max_trust_depth=3,
        trust_propagation_factor=0.8,
    )

    # Create a network of users
    print("👥 Creating user network...")

    # Root trusted user (bootstrapped)
    alice_keypair = NostrKeyPair.generate()
    alice_pubkey = alice_keypair.public_key

    # Well-connected users
    bob_keypair = NostrKeyPair.generate()
    bob_pubkey = bob_keypair.public_key

    charlie_keypair = NostrKeyPair.generate()
    charlie_pubkey = charlie_keypair.public_key

    # New user (no trust yet)
    david_keypair = NostrKeyPair.generate()
    david_pubkey = david_keypair.public_key

    # Potential spammer
    eve_keypair = NostrKeyPair.generate()
    eve_pubkey = eve_keypair.public_key

    print(f"  Alice (Trusted Root): {alice_pubkey[:16]}...")
    print(f"  Bob (Well-connected): {bob_pubkey[:16]}...")
    print(f"  Charlie (Community):  {charlie_pubkey[:16]}...")
    print(f"  David (New User):     {david_pubkey[:16]}...")
    print(f"  Eve (Unknown):        {eve_pubkey[:16]}...")
    print()

    # Bootstrap Alice as trusted
    wot_strategy.bootstrapped_trusted_keys.add(alice_pubkey)
    # Initialize Alice's node in the trust graph
    from ..anti_spam.wot import TrustNode

    wot_strategy._trust_graph[alice_pubkey] = TrustNode(alice_pubkey, 1.0)

    print("🔗 Building trust network...")
    current_time = time.time()

    # Alice follows Bob and Charlie (direct trust)
    alice_contacts = create_contact_list_event(
        [bob_pubkey, charlie_pubkey], alice_keypair
    )
    wot_strategy.update_state(alice_contacts, current_time)
    print("  ✅ Alice follows Bob and Charlie")

    # Bob follows Charlie and David (Bob trusts these users)
    bob_contacts = create_contact_list_event(
        [charlie_pubkey, david_pubkey], bob_keypair
    )
    wot_strategy.update_state(bob_contacts, current_time + 1)
    print("  ✅ Bob follows Charlie and David")

    # Charlie follows David (reinforces David's trust)
    charlie_contacts = create_contact_list_event([david_pubkey], charlie_keypair)
    wot_strategy.update_state(charlie_contacts, current_time + 2)
    print("  ✅ Charlie follows David")

    # Eve has no connections (isolated)
    print("  ❌ Eve has no trust connections")
    print()

    # Show trust graph stats
    stats = wot_strategy.get_trust_graph_stats()
    print("📊 Trust Network Statistics:")
    print(f"  Total nodes: {stats['total_nodes']}")
    print(f"  Total trust relationships: {stats['total_edges']}")
    print(f"  Bootstrapped trusted keys: {stats['bootstrapped_nodes']}")
    print()

    # Test messages from different users
    test_messages = [
        (alice_keypair, "Hello everyone! This is Alice, your trusted moderator."),
        (bob_keypair, "Hi! Bob here. Alice trusts me, so I should be allowed."),
        (charlie_keypair, "Charlie posting. I'm trusted by both Alice and Bob."),
        (david_keypair, "David here. I'm new but Bob and Charlie follow me."),
        (eve_keypair, "Eve trying to post. I have no trust connections."),
    ]

    user_names = {
        alice_pubkey: "Alice (Trusted Root)",
        bob_pubkey: "Bob (Direct Trust)",
        charlie_pubkey: "Charlie (Direct Trust)",
        david_pubkey: "David (Transitive Trust)",
        eve_pubkey: "Eve (No Trust)",
    }

    print("📝 Testing message filtering...")
    print("-" * 50)

    for i, (keypair, message) in enumerate(test_messages):
        event = create_text_note_event(message, keypair)
        result = wot_strategy.evaluate_event(event, current_time + 10 + i)

        user_name = user_names[keypair.public_key]
        trust_score = result.metrics.get("trust_score", 0.0) if result.metrics else 0.0

        status_icon = "✅" if result.allowed else "❌"
        print(f"{status_icon} {user_name}")
        print(f"   Trust Score: {trust_score:.3f}")
        print(f"   Message: '{message[:60]}{'...' if len(message) > 60 else ''}'")
        print(f"   Result: {result.reason}")
        print()

    # Demonstrate trust decay over time
    print("⏰ Testing trust decay over time...")
    print("-" * 50)

    # Create a strategy with faster decay for demonstration
    fast_decay_wot = WebOfTrustStrategy(
        min_trust_score=0.5,
        trust_decay_factor=0.8,  # Faster decay
        max_trust_depth=3,
        trust_propagation_factor=0.8,
        bootstrapped_trusted_keys={alice_pubkey},
    )

    # Rebuild the trust network
    fast_decay_wot.update_state(alice_contacts, current_time)
    fast_decay_wot.update_state(bob_contacts, current_time + 1)
    fast_decay_wot.update_state(charlie_contacts, current_time + 2)

    # Test Bob's message at different time intervals
    bob_message = create_text_note_event("Bob posting at different times", bob_keypair)

    time_intervals = [0, 1, 2, 5]  # Time units after trust establishment

    for interval in time_intervals:
        result = fast_decay_wot.evaluate_event(
            bob_message, current_time + 10 + interval
        )
        trust_score = result.metrics.get("trust_score", 0.0) if result.metrics else 0.0
        status_icon = "✅" if result.allowed else "❌"

        print(
            f"{status_icon} Time +{interval}: Trust Score = {trust_score:.3f} ({'Allowed' if result.allowed else 'Rejected'})"
        )

    print()

    # Show final metrics
    final_metrics = wot_strategy.get_metrics()
    print("📈 Final Strategy Metrics:")
    print(f"  Total evaluations: {final_metrics['total_evaluations']}")
    print(f"  Events allowed: {final_metrics['allowed_events']}")
    print(f"  Events rejected: {final_metrics['rejected_events']}")
    print(f"  Trust graph size: {final_metrics['trust_graph_size']}")

    success_rate = (
        (final_metrics["allowed_events"] / final_metrics["total_evaluations"] * 100)
        if final_metrics["total_evaluations"] > 0
        else 0
    )
    print(f"  Success rate: {success_rate:.1f}%")
    print()

    print("✅ Web of Trust scenario completed!")
    print("🔍 Key observations:")
    print("  • Trusted users (Alice) always allowed")
    print("  • Direct trust relationships (Bob, Charlie) work well")
    print("  • Transitive trust (David) works with sufficient path strength")
    print("  • Unknown users (Eve) are filtered out")
    print("  • Trust scores decay over time, requiring fresh interactions")


if __name__ == "__main__":
    run_wot_scenario()
