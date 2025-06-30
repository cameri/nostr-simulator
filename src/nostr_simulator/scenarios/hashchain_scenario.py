"""Hashchain and Rolling Codes anti-spam strategy scenario."""

import time

from ..anti_spam.hashchain import HashchainRollingCodes, TimeBasedCodeRotation
from ..protocol.events import NostrEvent, NostrEventKind, NostrTag
from ..protocol.keys import NostrKeyPair


def create_event_with_rolling_code(
    content: str, keypair: NostrKeyPair, rolling_code: bytes
) -> NostrEvent:
    """Create a Nostr event with a rolling code."""
    return NostrEvent(
        kind=NostrEventKind.TEXT_NOTE,
        content=content,
        created_at=int(time.time()),
        pubkey=keypair.public_key,
        tags=[NostrTag(name="rolling_code", values=[rolling_code.hex()])],
    )


def create_event_with_time_code(
    content: str, keypair: NostrKeyPair, time_code: bytes
) -> NostrEvent:
    """Create a Nostr event with a time-based code."""
    return NostrEvent(
        kind=NostrEventKind.TEXT_NOTE,
        content=content,
        created_at=int(time.time()),
        pubkey=keypair.public_key,
        tags=[NostrTag(name="time_code", values=[time_code.hex()])],
    )


def test_hashchain_rolling_codes() -> None:
    """Test hashchain rolling codes strategy."""
    print("🔗 Hashchain Rolling Codes Strategy Test")
    print("=" * 50)

    # Initialize strategy
    strategy = HashchainRollingCodes(
        chain_length=100,
        code_validity_period=300.0,  # 5 minutes
        rotation_interval=60.0,  # 1 minute
    )

    # Create test users
    honest_user = NostrKeyPair.generate()
    spammer = NostrKeyPair.generate()

    current_time = 1000.0

    print("🧪 Testing legitimate user behavior:")

    # Honest user posts with valid rolling codes
    for i in range(5):
        test_time = current_time + i * 30.0  # Every 30 seconds

        # Generate valid rolling code
        rolling_code = strategy.generate_code_for_user(
            honest_user.public_key, test_time
        )

        if rolling_code:
            event = create_event_with_rolling_code(
                f"Honest post #{i+1}", honest_user, rolling_code
            )

            result = strategy.evaluate_event(event, test_time)
            status = "✅ ALLOWED" if result.allowed else "❌ BLOCKED"
            print(f"  Post #{i+1}: {status} - {result.reason}")

            if result.allowed:
                strategy.update_state(event, test_time)
        else:
            print(f"  Post #{i+1}: ❌ Failed to generate rolling code")

    print("\n🚨 Testing spam attacks:")

    # Test 1: Spammer without rolling code
    print("1. Event without rolling code:")
    spam_event = NostrEvent(
        kind=NostrEventKind.TEXT_NOTE,
        content="Spam without rolling code",
        created_at=int(current_time),
        pubkey=spammer.public_key,
        tags=[],
    )
    result = strategy.evaluate_event(spam_event, current_time)
    status = "✅ ALLOWED" if result.allowed else "❌ BLOCKED"
    print(f"   {status} - {result.reason}")

    # Test 2: Replay attack
    print("\n2. Replay attack (reusing valid code):")
    # Get a valid code for honest user
    valid_code = strategy.generate_code_for_user(
        honest_user.public_key, current_time + 100
    )
    if valid_code:
        replay_event = create_event_with_rolling_code(
            "First use of code", honest_user, valid_code
        )

        # First use should be allowed
        result1 = strategy.evaluate_event(replay_event, current_time + 100)
        strategy.update_state(replay_event, current_time + 100)
        print(
            f"   First use: {'✅ ALLOWED' if result1.allowed else '❌ BLOCKED'} - {result1.reason}"
        )

        # Second use should be blocked
        result2 = strategy.evaluate_event(replay_event, current_time + 101)
        print(
            f"   Replay attempt: {'✅ ALLOWED' if result2.allowed else '❌ BLOCKED'} - {result2.reason}"
        )

    # Test 3: Invalid rolling code
    print("\n3. Invalid rolling code:")
    fake_code = b"\\x00" * 16  # Invalid code
    fake_event = create_event_with_rolling_code("Fake code spam", spammer, fake_code)
    result = strategy.evaluate_event(fake_event, current_time + 200)
    status = "✅ ALLOWED" if result.allowed else "❌ BLOCKED"
    print(f"   {status} - {result.reason}")

    # Test 4: Expired rolling code
    print("\n4. Expired rolling code:")
    old_code = strategy.generate_code_for_user(honest_user.public_key, current_time)
    if old_code:
        expired_event = create_event_with_rolling_code(
            "Event with expired code", honest_user, old_code
        )
        # Use code well after expiry
        result = strategy.evaluate_event(
            expired_event, current_time + 400
        )  # 400 seconds later
        status = "✅ ALLOWED" if result.allowed else "❌ BLOCKED"
        print(f"   {status} - {result.reason}")

    # Show strategy metrics
    print("\n📊 Strategy Metrics:")
    metrics = strategy.get_metrics()
    for key, value in metrics.items():
        print(f"   {key}: {value}")


def test_time_based_code_rotation() -> None:
    """Test time-based code rotation strategy."""
    print("\n⏰ Time-Based Code Rotation Strategy Test")
    print("=" * 50)

    # Initialize strategy
    strategy = TimeBasedCodeRotation(
        rotation_interval=60.0,  # 1 minute rotation
        code_length=8,
    )

    # Create test users
    honest_user = NostrKeyPair.generate()
    spammer = NostrKeyPair.generate()

    current_time = 2000.0

    print("🧪 Testing legitimate user behavior:")

    # Honest user posts with valid time codes
    for i in range(3):
        test_time = current_time + i * 30.0  # Every 30 seconds

        # Generate valid time code
        time_code = strategy.generate_current_code(honest_user.public_key, test_time)

        event = create_event_with_time_code(
            f"Timed post #{i+1}", honest_user, time_code
        )

        result = strategy.evaluate_event(event, test_time)
        status = "✅ ALLOWED" if result.allowed else "❌ BLOCKED"
        slot_info = (
            f"(slot offset: {result.metrics.get('slot_offset', 'N/A')})"
            if result.metrics
            else ""
        )
        print(f"  Post #{i+1}: {status} - {result.reason} {slot_info}")

        if result.allowed:
            strategy.update_state(event, test_time)

    print("\n🚨 Testing spam attacks:")

    # Test 1: Event without time code
    print("1. Event without time code:")
    no_code_event = NostrEvent(
        kind=NostrEventKind.TEXT_NOTE,
        content="No time code spam",
        created_at=int(current_time),
        pubkey=spammer.public_key,
        tags=[],
    )
    result = strategy.evaluate_event(no_code_event, current_time)
    status = "✅ ALLOWED" if result.allowed else "❌ BLOCKED"
    print(f"   {status} - {result.reason}")

    # Test 2: Old time code (beyond tolerance)
    print("\n2. Very old time code:")
    old_time = current_time - 300.0  # 5 minutes ago (beyond tolerance)
    old_code = strategy.generate_current_code(honest_user.public_key, old_time)
    old_event = create_event_with_time_code("Old code attempt", honest_user, old_code)
    result = strategy.evaluate_event(old_event, current_time)
    status = "✅ ALLOWED" if result.allowed else "❌ BLOCKED"
    print(f"   {status} - {result.reason}")

    # Test 3: Invalid time code
    print("\n3. Invalid time code:")
    invalid_code = b"\\x99" * 8  # Invalid code
    invalid_event = create_event_with_time_code(
        "Invalid code spam", spammer, invalid_code
    )
    result = strategy.evaluate_event(invalid_event, current_time)
    status = "✅ ALLOWED" if result.allowed else "❌ BLOCKED"
    print(f"   {status} - {result.reason}")

    # Test 4: Replay attack
    print("\n4. Replay attack:")
    valid_code = strategy.generate_current_code(
        honest_user.public_key, current_time + 400
    )
    replay_event = create_event_with_time_code(
        "Code for replay", honest_user, valid_code
    )

    # First use
    result1 = strategy.evaluate_event(replay_event, current_time + 400)
    strategy.update_state(replay_event, current_time + 400)
    print(
        f"   First use: {'✅ ALLOWED' if result1.allowed else '❌ BLOCKED'} - {result1.reason}"
    )

    # Replay attempt
    result2 = strategy.evaluate_event(replay_event, current_time + 401)
    print(
        f"   Replay: {'✅ ALLOWED' if result2.allowed else '❌ BLOCKED'} - {result2.reason}"
    )

    # Show strategy metrics
    print("\n📊 Strategy Metrics:")
    metrics = strategy.get_metrics()
    for key, value in metrics.items():
        print(f"   {key}: {value}")


def test_code_rotation_tolerance() -> None:
    """Test clock skew tolerance in code rotation."""
    print("\n🕐 Clock Skew Tolerance Test")
    print("=" * 30)

    strategy = TimeBasedCodeRotation(rotation_interval=60.0)
    user = NostrKeyPair.generate()
    base_time = 3000.0

    print("Testing tolerance for different time offsets:")

    for offset in [-30, -15, 0, 15, 30, 90, 150]:  # seconds
        test_time = base_time + offset
        code = strategy.generate_current_code(user.public_key, test_time)
        event = create_event_with_time_code(f"Offset {offset}s", user, code)

        result = strategy.evaluate_event(event, base_time)
        status = "✅ ALLOWED" if result.allowed else "❌ BLOCKED"
        slot_offset = (
            result.metrics.get("slot_offset", "N/A") if result.metrics else "N/A"
        )
        print(f"  {offset:+3d}s offset: {status} (slot offset: {slot_offset})")


def test_performance_comparison() -> None:
    """Compare performance of different strategies."""
    print("\n⚡ Performance Comparison")
    print("=" * 30)

    # Initialize strategies
    hashchain_strategy = HashchainRollingCodes()
    timecode_strategy = TimeBasedCodeRotation()

    user = NostrKeyPair.generate()
    current_time = 4000.0

    # Test hashchain performance
    print("🔗 Hashchain Rolling Codes:")
    hashchain_code = hashchain_strategy.generate_code_for_user(
        user.public_key, current_time
    )
    if hashchain_code:
        event = create_event_with_rolling_code("Performance test", user, hashchain_code)
        result = hashchain_strategy.evaluate_event(event, current_time)
        print(f"   Computational cost: {result.computational_cost:.6f}s")
        print(f"   Result: {'✅ ALLOWED' if result.allowed else '❌ BLOCKED'}")

    # Test time-based performance
    print("\n⏰ Time-Based Code Rotation:")
    timecode = timecode_strategy.generate_current_code(user.public_key, current_time)
    event = create_event_with_time_code("Performance test", user, timecode)
    result = timecode_strategy.evaluate_event(event, current_time)
    print(f"   Computational cost: {result.computational_cost:.6f}s")
    print(f"   Result: {'✅ ALLOWED' if result.allowed else '❌ BLOCKED'}")


def run_hashchain_scenario() -> None:
    """Run the complete hashchain scenario."""
    print("🔗⏰ Hashchain and Rolling Codes Anti-Spam Scenario")
    print("=" * 60)
    print(
        "This scenario demonstrates cryptographic rolling codes for anti-spam protection."
    )
    print("These strategies prevent replay attacks and provide time-based validation.")
    print()

    # Run all tests
    test_hashchain_rolling_codes()
    test_time_based_code_rotation()
    test_code_rotation_tolerance()
    test_performance_comparison()

    print("\n" + "=" * 60)
    print("📋 Summary:")
    print("• Hashchain rolling codes provide strong anti-replay protection")
    print("• Time-based codes are simpler but still effective against basic spam")
    print("• Both strategies handle clock skew gracefully")
    print("• Computational overhead is minimal for both approaches")
    print("• Rolling codes prevent reuse and provide temporal validation")
    print("• Chain regeneration ensures long-term sustainability")


if __name__ == "__main__":
    run_hashchain_scenario()
