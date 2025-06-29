#!/usr/bin/env python3
"""Demonstration script for the HonestUserAgent."""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nostr_simulator.agents.user import HonestUserAgent, UserBehaviorPattern
from nostr_simulator.simulation.engine import SimulationEngine


def main() -> None:
    """Demonstrate user agent functionality."""
    print("🌟 Nostr Simulator - User Agent Demonstration")
    print("=" * 50)

    # Create simulation engine (simplified)
    print("\n📊 Creating simulation environment...")

    # Create different behavior patterns
    social_butterfly = UserBehaviorPattern(
        posting_frequency=5.0,  # 5 posts per hour
        online_duration=3.0,    # 3 hours online
        social_activity=0.9,    # Very social
        follow_ratio=0.3,       # Follows 30% of discovered users
    )

    lurker = UserBehaviorPattern(
        posting_frequency=0.5,  # 0.5 posts per hour
        online_duration=1.0,    # 1 hour online
        social_activity=0.2,    # Not very social
        follow_ratio=0.05,      # Follows 5% of discovered users
    )

    # Create users
    print("\n👥 Creating user agents...")

    alice = HonestUserAgent("alice", behavior_pattern=social_butterfly)
    bob = HonestUserAgent("bob", behavior_pattern=lurker)

    print(f"   🦋 Alice - Social Butterfly: {alice.behavior_pattern.posting_frequency} posts/hour")
    print(f"   👀 Bob - Lurker: {bob.behavior_pattern.posting_frequency} posts/hour")

    # Activate users
    print("\n🟢 Activating users...")
    alice.activate(0.0)
    bob.activate(0.0)

    # Connect to relays
    print("\n🔗 Connecting to relays...")
    relays = ["relay1", "relay2", "relay3"]

    alice.connect_to_relays(relays)
    bob.connect_to_relays(relays[:2])  # Bob connects to fewer relays

    print(f"   Alice connected to: {alice.connected_relays}")
    print(f"   Bob connected to: {bob.connected_relays}")

    # Simulate posting
    print("\n📝 Simulating posting behavior...")

    alice.post_text_note("Hello Nostr! Excited to be here! 🎉")
    bob.post_text_note("Just checking out this decentralized social network...")

    print(f"   Alice posts made: {alice.posts_made}")
    print(f"   Bob posts made: {bob.posts_made}")

    # Simulate social interactions
    print("\n🤝 Simulating social interactions...")

    # Alice discovers and might follow Bob
    alice.follow_user("bob")
    bob.add_follower("alice")

    # Bob discovers Alice but might not follow (low follow ratio)
    follow_decision = bob.should_follow_user("alice")
    if follow_decision:
        bob.follow_user("alice")
        alice.add_follower("bob")

    print(f"   Alice following: {alice.following}")
    print(f"   Alice followers: {alice.followers}")
    print(f"   Bob following: {bob.following}")
    print(f"   Bob followers: {bob.followers}")

    # Generate varied content
    print("\n📄 Content generation variety:")
    for i in range(3):
        content = alice.generate_post_content()
        print(f"   Post {i+1}: {content}")

    # Show statistics
    print("\n📈 User Statistics:")
    print("\n👤 Alice:")
    alice_stats = alice.get_stats()
    for key, value in alice_stats.items():
        if key != "behavior_pattern":
            print(f"   {key}: {value}")

    print("\n👤 Bob:")
    bob_stats = bob.get_stats()
    for key, value in bob_stats.items():
        if key != "behavior_pattern":
            print(f"   {key}: {value}")

    # Show follow probabilities
    print("\n🎲 Follow Decision Simulation (100 trials):")
    alice_follows = sum(alice.should_follow_user(f"user{i}") for i in range(100))
    bob_follows = sum(bob.should_follow_user(f"user{i}") for i in range(100))

    print(f"   Alice would follow: {alice_follows}% of discovered users")
    print(f"   Bob would follow: {bob_follows}% of discovered users")

    print("\n✅ User agent demonstration completed!")
    print("\nKey features demonstrated:")
    print("   • Configurable behavior patterns")
    print("   • Social graph management (following/followers)")
    print("   • Multi-relay connectivity")
    print("   • Content generation and posting")
    print("   • Realistic social interaction decisions")
    print("   • Comprehensive statistics tracking")


if __name__ == "__main__":
    main()
