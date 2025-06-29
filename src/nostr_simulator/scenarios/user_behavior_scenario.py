"""User agent behavior demonstration scenario."""

from ..agents.user import HonestUserAgent, UserBehaviorPattern
from ..protocol.keys import NostrKeyPair


def run_user_behavior_scenario():
    """Demonstrate user agent functionality and behavior patterns."""
    print("👥 Nostr Simulator - User Behavior Scenario")
    print("=" * 50)

    # Create different behavior patterns
    social_butterfly = UserBehaviorPattern(
        posting_frequency=5.0,  # 5 posts per hour
        follow_ratio=0.3,       # Follows 30% of discovered users
        social_activity=0.9,    # Very social
        online_duration=3.0     # Online 3 hours per session
    )

    lurker = UserBehaviorPattern(
        posting_frequency=0.5,  # 0.5 posts per hour
        follow_ratio=0.05,      # Follows 5% of discovered users
        social_activity=0.2,    # Not very social
        online_duration=1.0     # Online 1 hour per session
    )

    normal_user = UserBehaviorPattern(
        posting_frequency=2.0,  # 2 posts per hour
        follow_ratio=0.15,      # Follows 15% of discovered users
        social_activity=0.6,    # Moderately social
        online_duration=2.0     # Online 2 hours per session
    )

    # Create users with different behavior patterns
    print("\n👤 Creating user agents with different behavior patterns...")

    alice = HonestUserAgent("alice", behavior_pattern=social_butterfly)
    bob = HonestUserAgent("bob", behavior_pattern=lurker)
    charlie = HonestUserAgent("charlie", behavior_pattern=normal_user)

    users = [
        ("Alice", alice, "Social Butterfly"),
        ("Bob", bob, "Lurker"),
        ("Charlie", charlie, "Normal User")
    ]

    for name, user, pattern_type in users:
        print(f"   📊 {name} ({pattern_type}):")
        print(f"      Posting frequency: {user.behavior_pattern.posting_frequency}")
        print(f"      Follow ratio: {user.behavior_pattern.follow_ratio}")
        print(f"      Social activity: {user.behavior_pattern.social_activity}")
        print(f"      Online duration: {user.behavior_pattern.online_duration}")

    print("\n🟢 Activating users...")
    current_time = 0.0
    for _, user, _ in users:
        user.activate(current_time)

    # Connect to relays
    print("\n🔗 Connecting to relays...")
    relays = ["relay1", "relay2", "relay3"]

    alice.connect_to_relays(relays)
    bob.connect_to_relays(relays[:2])  # Bob connects to fewer relays
    charlie.connect_to_relays(relays)

    for name, user, _ in users:
        print(f"   {name} connected to: {len(user.connected_relays)} relays")

    # Simulate posting behavior
    print("\n📝 Simulating posting behavior...")

    post_samples = [
        "Hello Nostr! Excited to be here! 🎉",
        "Just checking out this decentralized social network...",
        "Working on some interesting protocols today.",
        "Beautiful sunset this evening 🌅",
        "Reading about cryptographic primitives.",
    ]

    for i, (name, user, _) in enumerate(users):
        content = post_samples[i % len(post_samples)]
        user.post_text_note(content)
        print(f"   {name}: '{content}'")

    # Simulate social interactions
    print("\n🤝 Simulating social interactions...")

    # Alice discovers and follows others (high follow probability)
    alice.follow_user("bob")
    alice.follow_user("charlie")
    bob.add_follower("alice")
    charlie.add_follower("alice")

    # Simulate follow decisions for other users
    users_to_discover = ["user1", "user2", "user3", "user4", "user5"]

    for name, user, _ in users:
        follows_made = 0
        for discovered_user in users_to_discover:
            if user.should_follow_user(discovered_user):
                follows_made += 1

        expected_follows = len(users_to_discover) * user.behavior_pattern.follow_ratio
        print(f"   {name}: Would follow {follows_made}/{len(users_to_discover)} users "
              f"(expected ~{expected_follows:.1f})")

    # Show social graph
    print(f"\n🌐 Social Graph:")
    print(f"   Alice following: {len(alice.following)} users")
    print(f"   Alice followers: {len(alice.followers)} users")
    print(f"   Bob followers: {len(bob.followers)} users")
    print(f"   Charlie followers: {len(charlie.followers)} users")

    # Generate varied content samples
    print("\n📄 Content generation variety:")
    for i in range(5):
        content = alice.generate_post_content()
        print(f"   Sample {i+1}: '{content}'")

    # Show comprehensive statistics
    print("\n📊 User Statistics:")
    for name, user, pattern_type in users:
        print(f"\n👤 {name} ({pattern_type}):")
        stats = user.get_stats()
        for key, value in stats.items():
            if key != "behavior_pattern":
                print(f"   {key}: {value}")

    # Demonstrate follow decision patterns
    print("\n🎲 Follow Decision Analysis (100 simulated discoveries):")
    trials = 100

    for name, user, _ in users:
        follows = sum(user.should_follow_user(f"user{i}") for i in range(trials))
        follow_rate = follows / trials
        expected_rate = user.behavior_pattern.follow_ratio

        print(f"   {name}: {follows}/{trials} follows ({follow_rate:.1%}) "
              f"- Expected: {expected_rate:.1%}")

    print("\n✅ User behavior scenario completed!")
    print("\nKey Insights:")
    print("• Different behavior patterns create realistic user diversity")
    print("• Social butterflies have high engagement and follow rates")
    print("• Lurkers consume content but have minimal social activity")
    print("• Follow decisions are probabilistic, creating organic social graphs")
    print("• Content generation varies to simulate realistic posting patterns")


if __name__ == "__main__":
    run_user_behavior_scenario()
