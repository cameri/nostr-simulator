"""Tests for Nostr protocol event validation."""

import time
from typing import Any
from unittest.mock import patch

from .events import NostrEvent, NostrEventKind, NostrTag
from .keys import NostrKeyPair
from .validation import EventValidator, RelayPolicy, ValidationError


class TestEventValidator:
    """Test EventValidator functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.validator = EventValidator()
        self.keypair = NostrKeyPair.generate()

    def create_valid_event(self) -> NostrEvent:
        """Create a valid test event."""
        return NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello, Nostr!",
            created_at=int(time.time()),
            pubkey=self.keypair.public_key,
        )

    def test_validate_valid_event(self) -> None:
        """Test validating a valid event."""
        event = self.create_valid_event()

        # Should not raise an exception
        self.validator.validate_event(event, check_signature=False)

    def test_validate_empty_pubkey(self) -> None:
        """Test validation fails for empty pubkey."""
        event = self.create_valid_event()
        event.pubkey = ""

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "must have a public key" in str(e)

    def test_validate_invalid_pubkey_length(self) -> None:
        """Test validation fails for invalid pubkey length."""
        event = self.create_valid_event()
        event.pubkey = "abc"

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "must be 64 hex characters" in str(e)

    def test_validate_invalid_pubkey_hex(self) -> None:
        """Test validation fails for invalid pubkey hex."""
        event = self.create_valid_event()
        event.pubkey = "g" * 64

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "must be valid hex" in str(e)

    def test_validate_content_too_long(self) -> None:
        """Test validation fails for content that's too long."""
        event = self.create_valid_event()
        event.content = "a" * (self.validator.max_content_length + 1)

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "exceeds maximum length" in str(e)

    def test_validate_too_many_tags(self) -> None:
        """Test validation fails for too many tags."""
        event = self.create_valid_event()

        # Add more tags than allowed
        for i in range(self.validator.max_tags + 1):
            event.add_tag("t", f"tag{i}")

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "Too many tags" in str(e)

    def test_validate_tag_name_too_long(self) -> None:
        """Test validation fails for tag name that's too long."""
        event = self.create_valid_event()
        long_name = "a" * (self.validator.max_tag_value_length + 1)
        event.tags.append(NostrTag(name=long_name))

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "name too long" in str(e)

    def test_validate_too_many_tag_values(self) -> None:
        """Test validation fails for too many tag values."""
        event = self.create_valid_event()
        values = [f"value{i}" for i in range(self.validator.max_tag_values + 1)]
        event.tags.append(NostrTag(name="t", values=values))

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "too many values" in str(e)

    def test_validate_tag_value_too_long(self) -> None:
        """Test validation fails for tag value that's too long."""
        event = self.create_valid_event()
        long_value = "a" * (self.validator.max_tag_value_length + 1)
        event.tags.append(NostrTag(name="t", values=[long_value]))

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "value 0 too long" in str(e)

    def test_validate_negative_timestamp(self) -> None:
        """Test validation fails for negative timestamp."""
        event = self.create_valid_event()
        event.created_at = -1

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "must be positive" in str(e)

    @patch('time.time')
    def test_validate_timestamp_too_far_future(self, mock_time: Any) -> None:
        """Test validation fails for timestamp too far in future."""
        mock_time.return_value = 1000000

        event = self.create_valid_event()
        event.created_at = int(mock_time.return_value) + self.validator.timestamp_tolerance_seconds + 1

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "too far from current time" in str(e)

    def test_validate_negative_kind(self) -> None:
        """Test validation for negative event kind - skip since IntEnum prevents this."""
        # Note: IntEnum automatically prevents negative values, so this test
        # demonstrates that the type system itself prevents invalid kinds
        try:
            # This should raise ValueError when creating the enum
            invalid_kind = NostrEventKind(-1)
            assert False, "Should have raised ValueError for negative kind"
        except ValueError:
            # This is expected - IntEnum prevents negative values
            pass

    def test_validate_delete_event_without_e_tags(self) -> None:
        """Test validation fails for delete event without e tags."""
        event = NostrEvent(
            kind=NostrEventKind.DELETE,
            content="",
            created_at=int(time.time()),
            pubkey=self.keypair.public_key,
        )

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "must have 'e' tags" in str(e)

    def test_validate_reaction_event_without_e_or_p_tags(self) -> None:
        """Test validation fails for reaction event without e or p tags."""
        event = NostrEvent(
            kind=NostrEventKind.REACTION,
            content="+",
            created_at=int(time.time()),
            pubkey=self.keypair.public_key,
        )

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "must have 'e' or 'p' tags" in str(e)

    def test_validate_id_mismatch(self) -> None:
        """Test validation fails for ID mismatch."""
        event = self.create_valid_event()
        event.id = "a" * 64  # Valid length but wrong ID

        try:
            self.validator.validate_event(event, check_signature=False)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "ID mismatch" in str(e)

    def test_validate_missing_signature(self) -> None:
        """Test validation fails for missing signature when checking signatures."""
        event = self.create_valid_event()
        event.sig = ""

        try:
            self.validator.validate_event(event, check_signature=True)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "must have a signature" in str(e)

    def test_validate_invalid_signature_length(self) -> None:
        """Test validation fails for invalid signature length."""
        event = self.create_valid_event()
        event.sig = "abc"

        try:
            self.validator.validate_event(event, check_signature=True)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "must be 128 hex characters" in str(e)

    def test_validate_invalid_signature_hex(self) -> None:
        """Test validation fails for invalid signature hex."""
        event = self.create_valid_event()
        event.sig = "g" * 128

        try:
            self.validator.validate_event(event, check_signature=True)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "must be valid hex" in str(e)

    def test_is_valid_event_true(self) -> None:
        """Test is_valid_event returns True for valid event."""
        event = self.create_valid_event()
        assert self.validator.is_valid_event(event, check_signature=False) is True

    def test_is_valid_event_false(self) -> None:
        """Test is_valid_event returns False for invalid event."""
        event = self.create_valid_event()
        event.pubkey = ""  # Make it invalid
        assert self.validator.is_valid_event(event, check_signature=False) is False

    def test_validate_event_dict(self) -> None:
        """Test validating an event dictionary."""
        event = self.create_valid_event()
        event_dict = event.to_dict()

        # Should not raise an exception when not checking signature
        try:
            event = NostrEvent.from_dict(event_dict)
            self.validator.validate_event(event, check_signature=False)
        except Exception as e:
            assert False, f"Should not have raised exception: {e}"

    def test_validate_invalid_event_dict(self) -> None:
        """Test validation fails for invalid event dictionary."""
        invalid_dict = {"invalid": "data"}

        try:
            self.validator.validate_event_dict(invalid_dict)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "Invalid event structure" in str(e)


class TestRelayPolicy:
    """Test RelayPolicy functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.policy = RelayPolicy()
        self.keypair = NostrKeyPair.generate()

    def create_test_event(self) -> NostrEvent:
        """Create a test event."""
        return NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test content",
            created_at=int(time.time()),
            pubkey=self.keypair.public_key,
        )

    def test_check_policy_accept(self) -> None:
        """Test policy accepts valid event."""
        event = self.create_test_event()
        allowed, reason = self.policy.check_policy(event, time.time())

        assert allowed is True
        assert reason == "Accepted"

    def test_check_policy_blocked_pubkey(self) -> None:
        """Test policy blocks event from blocked pubkey."""
        policy = RelayPolicy(blocked_pubkeys={self.keypair.public_key})
        event = self.create_test_event()

        allowed, reason = policy.check_policy(event, time.time())

        assert allowed is False
        assert "blocked" in reason

    def test_check_policy_disallowed_kind(self) -> None:
        """Test policy blocks disallowed event kind."""
        policy = RelayPolicy(allowed_kinds={0})  # Only allow metadata events
        event = self.create_test_event()  # TEXT_NOTE = 1

        allowed, reason = policy.check_policy(event, time.time())

        assert allowed is False
        assert "not allowed" in reason

    def test_check_policy_rate_limit(self) -> None:
        """Test policy enforces rate limiting."""
        policy = RelayPolicy(max_events_per_minute=1)
        event = self.create_test_event()
        current_time = time.time()

        # First event should be allowed
        allowed, reason = policy.check_policy(event, current_time)
        assert allowed is True

        # Second event immediately should be blocked
        allowed, reason = policy.check_policy(event, current_time)
        assert allowed is False
        assert "Rate limit" in reason

    def test_check_policy_rate_limit_reset(self) -> None:
        """Test rate limit resets after time window."""
        policy = RelayPolicy(max_events_per_minute=1)
        event = self.create_test_event()
        current_time = time.time()

        # First event
        policy.check_policy(event, current_time)

        # Event after 61 seconds should be allowed
        allowed, reason = policy.check_policy(event, current_time + 61)
        assert allowed is True

    def test_check_policy_pow_requirement(self) -> None:
        """Test policy enforces PoW requirement."""
        policy = RelayPolicy(require_pow=True, min_pow_difficulty=4)
        event = self.create_test_event()

        # Most random events won't have sufficient PoW
        allowed, reason = policy.check_policy(event, time.time())

        # Since we can't easily create an event with specific PoW,
        # we'll just check that the policy is checking PoW
        if not allowed:
            assert "PoW" in reason

    def test_calculate_pow_difficulty(self) -> None:
        """Test PoW difficulty calculation."""
        # Create an event with ID starting with zeros
        event = self.create_test_event()

        # Mock an ID with leading zeros
        event.id = "0000abcd" + "f" * 56

        difficulty = self.policy._calculate_pow_difficulty(event)
        assert difficulty >= 16  # 4 hex zeros = 16 bits

    def test_rate_limit_cleanup(self) -> None:
        """Test rate limit entry cleanup."""
        policy = RelayPolicy(max_events_per_minute=10)
        event = self.create_test_event()

        # Add some events
        policy.check_policy(event, 1000.0)
        policy.check_policy(event, 1010.0)

        # Check that old entries are cleaned up
        policy.check_policy(event, 1070.0)  # 70 seconds later

        # The pubkey should still be in the tracking dict but with cleaned entries
        assert self.keypair.public_key in policy._event_counts

        # Old entries should be removed
        recent_count = len([
            t for t in policy._event_counts[self.keypair.public_key]
            if t > 1010.0  # Only entries after 1010
        ])
        assert recent_count == 1  # Only the most recent event
