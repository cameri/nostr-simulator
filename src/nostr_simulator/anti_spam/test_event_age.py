"""Tests for Event Age Proof anti-spam strategies."""

from __future__ import annotations

import time

from ..protocol.events import NostrEvent, NostrEventKind, NostrTag
from .event_age import AgeProof, EventAgeStrategy, TimestampVerificationStrategy


class TestTimestampVerificationStrategy:
    """Test cases for TimestampVerificationStrategy."""

    def test_init(self) -> None:
        """Test strategy initialization."""
        strategy = TimestampVerificationStrategy()
        assert strategy.name == "timestamp_verification"
        assert strategy.max_future_drift == 300.0
        assert strategy.max_past_age == 3600.0

    def test_init_custom_params(self) -> None:
        """Test strategy initialization with custom parameters."""
        strategy = TimestampVerificationStrategy(
            max_future_drift=600.0,
            max_past_age=7200.0,
        )
        assert strategy.max_future_drift == 600.0
        assert strategy.max_past_age == 7200.0

    def test_valid_timestamp(self) -> None:
        """Test validation of valid timestamp."""
        strategy = TimestampVerificationStrategy()
        current_time = time.time()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time - 100),  # 100 seconds ago
            pubkey="test_pubkey",
        )

        result = strategy.evaluate_event(event, current_time)
        assert result.allowed
        assert "valid" in result.reason.lower()
        assert result.metrics is not None
        assert "age" in result.metrics

    def test_future_event_rejection(self) -> None:
        """Test rejection of events too far in the future."""
        strategy = TimestampVerificationStrategy(max_future_drift=300.0)
        current_time = time.time()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time + 600),  # 10 minutes in future
            pubkey="test_pubkey",
        )

        result = strategy.evaluate_event(event, current_time)
        assert not result.allowed
        assert "future" in result.reason.lower()
        assert result.metrics is not None
        assert "drift" in result.metrics

        # Check metrics
        metrics = strategy.get_metrics()
        assert metrics["future_events_rejected"] == 1

    def test_old_event_rejection(self) -> None:
        """Test rejection of events that are too old."""
        strategy = TimestampVerificationStrategy(max_past_age=3600.0)
        current_time = time.time()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time - 7200),  # 2 hours ago
            pubkey="test_pubkey",
        )

        result = strategy.evaluate_event(event, current_time)
        assert not result.allowed
        assert "old" in result.reason.lower()
        assert result.metrics is not None
        assert "age" in result.metrics

        # Check metrics
        metrics = strategy.get_metrics()
        assert metrics["old_events_rejected"] == 1

    def test_boundary_conditions(self) -> None:
        """Test boundary conditions for timestamp validation."""
        strategy = TimestampVerificationStrategy(
            max_future_drift=300.0,
            max_past_age=3600.0,
        )
        current_time = time.time()

        # Just inside future boundary
        event_future = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time + 299),
            pubkey="test_pubkey",
        )
        result = strategy.evaluate_event(event_future, current_time)
        assert result.allowed

        # Just inside past boundary
        event_past = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time - 3599),
            pubkey="test_pubkey",
        )
        result = strategy.evaluate_event(event_past, current_time)
        assert result.allowed

    def test_update_state_no_op(self) -> None:
        """Test that update_state does nothing for simple verification."""
        strategy = TimestampVerificationStrategy()
        current_time = time.time()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time),
            pubkey="test_pubkey",
        )

        # Should not raise any exceptions
        strategy.update_state(event, current_time)

    def test_computational_cost_tracking(self) -> None:
        """Test that computational cost is tracked."""
        strategy = TimestampVerificationStrategy()
        current_time = time.time()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time),
            pubkey="test_pubkey",
        )

        result = strategy.evaluate_event(event, current_time)
        assert result.computational_cost >= 0.0


class TestEventAgeStrategy:
    """Test cases for EventAgeStrategy."""

    def test_init(self) -> None:
        """Test strategy initialization."""
        strategy = EventAgeStrategy()
        assert strategy.name == "event_age"
        assert strategy.max_future_drift == 600.0
        assert strategy.max_past_age == 86400.0
        assert strategy.chronological_validation
        assert not strategy.age_proof_required
        assert strategy.min_key_age == 3600.0

    def test_init_custom_params(self) -> None:
        """Test strategy initialization with custom parameters."""
        strategy = EventAgeStrategy(
            max_future_drift=300.0,
            max_past_age=7200.0,
            chronological_validation=False,
            age_proof_required=True,
            min_key_age=1800.0,
            age_proof_difficulty=6,
        )
        assert strategy.max_future_drift == 300.0
        assert strategy.max_past_age == 7200.0
        assert not strategy.chronological_validation
        assert strategy.age_proof_required
        assert strategy.min_key_age == 1800.0
        assert strategy.age_proof_difficulty == 6

    def test_valid_event_basic(self) -> None:
        """Test validation of a basic valid event."""
        strategy = EventAgeStrategy(
            chronological_validation=False,
            age_proof_required=False,
            min_key_age=0.0,
        )
        current_time = time.time()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time - 100),
            pubkey="test_pubkey",
        )

        result = strategy.evaluate_event(event, current_time)
        assert result.allowed
        assert "passed" in result.reason.lower()

    def test_timestamp_validation(self) -> None:
        """Test basic timestamp validation."""
        strategy = EventAgeStrategy()
        current_time = time.time()

        # Future event
        event_future = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time + 1200),  # 20 minutes in future
            pubkey="test_pubkey",
        )

        result = strategy.evaluate_event(event_future, current_time)
        assert not result.allowed
        assert "future" in result.reason.lower()

        # Old event
        event_old = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time - 172800),  # 2 days ago
            pubkey="test_pubkey",
        )

        result = strategy.evaluate_event(event_old, current_time)
        assert not result.allowed
        assert "old" in result.reason.lower()

    def test_chronological_validation(self) -> None:
        """Test chronological ordering validation."""
        strategy = EventAgeStrategy(
            chronological_validation=True,
            min_key_age=0.0,
        )
        current_time = time.time()
        pubkey = "test_pubkey"

        # First event
        event1 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="first",
            created_at=int(current_time - 200),
            pubkey=pubkey,
        )

        result1 = strategy.evaluate_event(event1, current_time)
        assert result1.allowed
        strategy.update_state(event1, current_time)

        # Second event (later timestamp) - should pass
        event2 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="second",
            created_at=int(current_time - 100),
            pubkey=pubkey,
        )

        result2 = strategy.evaluate_event(event2, current_time)
        assert result2.allowed
        strategy.update_state(event2, current_time)

        # Third event (earlier timestamp) - should fail
        event3 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="third",
            created_at=int(current_time - 150),  # Earlier than event2
            pubkey=pubkey,
        )

        result3 = strategy.evaluate_event(event3, current_time)
        assert not result3.allowed
        assert "chronological" in result3.reason.lower()

    def test_key_age_validation(self) -> None:
        """Test key age validation."""
        strategy = EventAgeStrategy(
            chronological_validation=False,
            min_key_age=3600.0,  # 1 hour
        )
        current_time = time.time()
        pubkey = "test_pubkey"

        # First event from new key - should fail
        event1 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time - 100),
            pubkey=pubkey,
        )

        result1 = strategy.evaluate_event(event1, current_time)
        assert not result1.allowed
        assert "young" in result1.reason.lower()

        # Simulate key aging
        strategy.update_state(event1, current_time)
        aged_time = current_time + 3700  # 1 hour and a bit later

        event2 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test2",
            created_at=int(aged_time - 100),
            pubkey=pubkey,
        )

        result2 = strategy.evaluate_event(event2, aged_time)
        assert result2.allowed

    def test_age_proof_required(self) -> None:
        """Test age proof requirement."""
        strategy = EventAgeStrategy(
            chronological_validation=False,
            age_proof_required=True,
            min_key_age=0.0,
        )
        current_time = time.time()

        # Event without age proof - should fail
        event_no_proof = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time - 100),
            pubkey="test_pubkey",
        )

        result = strategy.evaluate_event(event_no_proof, current_time)
        assert not result.allowed
        assert "age proof" in result.reason.lower()

    def test_extract_age_proof(self) -> None:
        """Test age proof extraction from event tags."""
        strategy = EventAgeStrategy()

        # Event with valid age proof tag
        timestamp = time.time()
        proof = b"\x00\x01\x02\x03"
        difficulty = 4
        key_age = 3600.0

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(timestamp),
            pubkey="test_pubkey",
            tags=[
                NostrTag(
                    name="age_proof",
                    values=[f"{timestamp}:{proof.hex()}:{difficulty}:{key_age}"],
                ),
            ],
        )

        age_proof = strategy._extract_age_proof(event)
        assert age_proof is not None
        assert age_proof.timestamp == timestamp
        assert age_proof.proof == proof
        assert age_proof.difficulty == difficulty
        assert age_proof.key_age == key_age

        # Event without age proof
        event_no_proof = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(timestamp),
            pubkey="test_pubkey",
        )

        age_proof_none = strategy._extract_age_proof(event_no_proof)
        assert age_proof_none is None

    def test_count_leading_zero_bits(self) -> None:
        """Test counting leading zero bits in hash."""
        strategy = EventAgeStrategy()

        # All zeros
        assert strategy._count_leading_zero_bits(b"\x00\x00\x00") == 24

        # No zeros
        assert strategy._count_leading_zero_bits(b"\xFF\xFF\xFF") == 0

        # Mixed
        assert strategy._count_leading_zero_bits(b"\x00\x00\x80") == 16
        assert strategy._count_leading_zero_bits(b"\x00\x00\x01") == 23

    def test_generate_age_proof(self) -> None:
        """Test age proof generation."""
        strategy = EventAgeStrategy(age_proof_difficulty=4)

        pubkey = "test_pubkey"
        timestamp = time.time()
        key_age = 3600.0

        age_proof = strategy.generate_age_proof(pubkey, timestamp, key_age)

        assert age_proof.timestamp == timestamp
        assert age_proof.key_age == key_age
        assert age_proof.difficulty == 4
        assert len(age_proof.proof) == 8

        # Verify the proof is valid
        assert strategy._verify_age_proof(
            NostrEvent(
                kind=NostrEventKind.TEXT_NOTE,
                content="test",
                created_at=int(timestamp),
                pubkey=pubkey,
            ),
            age_proof,
        )

    def test_verify_age_proof(self) -> None:
        """Test age proof verification."""
        strategy = EventAgeStrategy(age_proof_difficulty=4)

        pubkey = "test_pubkey"
        timestamp = time.time()
        key_age = 3600.0

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(timestamp),
            pubkey=pubkey,
        )

        # Generate a valid proof
        age_proof = strategy.generate_age_proof(pubkey, timestamp, key_age)
        assert strategy._verify_age_proof(event, age_proof)

        # Invalid proof (use all 0xFF bytes which will never meet difficulty requirement)
        invalid_proof = AgeProof(
            timestamp=timestamp,
            proof=b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF",  # All bits set, no leading zeros
            difficulty=4,
            key_age=key_age,
        )
        assert not strategy._verify_age_proof(event, invalid_proof)

    def test_metrics_tracking(self) -> None:
        """Test that metrics are properly tracked."""
        strategy = EventAgeStrategy()
        current_time = time.time()

        # Test various rejection scenarios
        pubkey = "test_pubkey"

        # Future event
        event_future = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time + 1200),
            pubkey=pubkey,
        )
        strategy.evaluate_event(event_future, current_time)

        # Old event
        event_old = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time - 172800),
            pubkey=pubkey,
        )
        strategy.evaluate_event(event_old, current_time)

        # Young key
        event_young_key = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time - 100),
            pubkey="new_pubkey",
        )
        strategy.evaluate_event(event_young_key, current_time)

        metrics = strategy.get_metrics()
        assert metrics["events_processed"] == 3
        assert metrics["future_events_rejected"] == 1
        assert metrics["old_events_rejected"] == 1
        assert metrics["young_key_rejections"] == 1

    def test_update_state(self) -> None:
        """Test state updates."""
        strategy = EventAgeStrategy()
        current_time = time.time()
        pubkey = "test_pubkey"

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time - 100),
            pubkey=pubkey,
        )

        # First update should record key first seen
        strategy.update_state(event, current_time)
        assert pubkey in strategy._key_first_seen
        assert strategy._key_first_seen[pubkey] == current_time

        # Should also update last event time for chronological validation
        assert pubkey in strategy._last_event_time
        assert strategy._last_event_time[pubkey] == event.created_at


class TestAgeProof:
    """Test cases for AgeProof dataclass."""

    def test_age_proof_creation(self) -> None:
        """Test AgeProof creation."""
        timestamp = time.time()
        proof = b"\\x00\\x01\\x02\\x03"
        difficulty = 4
        key_age = 3600.0

        age_proof = AgeProof(
            timestamp=timestamp,
            proof=proof,
            difficulty=difficulty,
            key_age=key_age,
        )

        assert age_proof.timestamp == timestamp
        assert age_proof.proof == proof
        assert age_proof.difficulty == difficulty
        assert age_proof.key_age == key_age
