"""Event validation system for Nostr protocol."""

from __future__ import annotations

import json
import time
from typing import Any

from .events import NostrEvent, NostrEventKind
from .keys import verify_signature


class ValidationError(Exception):
    """Raised when event validation fails."""

    pass


class EventValidator:
    """Validates Nostr events according to protocol specifications."""

    def __init__(
        self,
        max_content_length: int = 65536,  # 64KB
        max_tags: int = 2500,
        max_tag_values: int = 100,
        max_tag_value_length: int = 1024,
        timestamp_tolerance_seconds: int = 600,  # 10 minutes
    ) -> None:
        """Initialize the event validator.

        Args:
            max_content_length: Maximum length of event content.
            max_tags: Maximum number of tags per event.
            max_tag_values: Maximum number of values per tag.
            max_tag_value_length: Maximum length of tag value.
            timestamp_tolerance_seconds: Allowed timestamp deviation from current time.
        """
        self.max_content_length = max_content_length
        self.max_tags = max_tags
        self.max_tag_values = max_tag_values
        self.max_tag_value_length = max_tag_value_length
        self.timestamp_tolerance_seconds = timestamp_tolerance_seconds

    def validate_event(self, event: NostrEvent, check_signature: bool = True) -> None:
        """Validate a Nostr event.

        Args:
            event: The event to validate.
            check_signature: Whether to verify the cryptographic signature.

        Raises:
            ValidationError: If the event is invalid.
        """
        self._validate_basic_structure(event)
        self._validate_content_length(event)
        self._validate_tags(event)
        self._validate_timestamp(event)
        self._validate_kind(event)
        self._validate_id(event)

        if check_signature:
            self._validate_signature(event)

    def _validate_basic_structure(self, event: NostrEvent) -> None:
        """Validate basic event structure."""
        if not event.pubkey:
            raise ValidationError("Event must have a public key")

        if len(event.pubkey) != 64:
            raise ValidationError("Public key must be 64 hex characters")

        try:
            bytes.fromhex(event.pubkey)
        except ValueError:
            raise ValidationError("Public key must be valid hex")

        if not event.id:
            raise ValidationError("Event must have an ID")

        if len(event.id) != 64:
            raise ValidationError("Event ID must be 64 hex characters")

        try:
            bytes.fromhex(event.id)
        except ValueError:
            raise ValidationError("Event ID must be valid hex")

    def _validate_content_length(self, event: NostrEvent) -> None:
        """Validate content length."""
        if len(event.content.encode('utf-8')) > self.max_content_length:
            raise ValidationError(
                f"Content exceeds maximum length of {self.max_content_length} bytes"
            )

    def _validate_tags(self, event: NostrEvent) -> None:
        """Validate event tags."""
        if len(event.tags) > self.max_tags:
            raise ValidationError(f"Too many tags (max: {self.max_tags})")

        for i, tag in enumerate(event.tags):
            if not tag.name:
                raise ValidationError(f"Tag {i} has empty name")

            if len(tag.name.encode('utf-8')) > self.max_tag_value_length:
                raise ValidationError(f"Tag {i} name too long")

            if len(tag.values) > self.max_tag_values:
                raise ValidationError(
                    f"Tag {i} has too many values (max: {self.max_tag_values})"
                )

            for j, value in enumerate(tag.values):
                if len(value.encode('utf-8')) > self.max_tag_value_length:
                    raise ValidationError(f"Tag {i} value {j} too long")

    def _validate_timestamp(self, event: NostrEvent) -> None:
        """Validate event timestamp."""
        if event.created_at <= 0:
            raise ValidationError("Timestamp must be positive")

        current_time = int(time.time())
        time_diff = abs(current_time - event.created_at)

        if time_diff > self.timestamp_tolerance_seconds:
            raise ValidationError(
                f"Timestamp too far from current time (diff: {time_diff}s)"
            )

    def _validate_kind(self, event: NostrEvent) -> None:
        """Validate event kind."""
        # Kind validation is mostly about checking if it's a known kind
        # For simulation, we'll be more permissive and allow custom kinds
        if event.kind < 0:
            raise ValidationError("Event kind cannot be negative")

        # Check for specific kind requirements
        if event.kind == NostrEventKind.DELETE:
            # Delete events should have 'e' tags pointing to events to delete
            e_tags = event.get_tag_values("e")
            if not e_tags:
                raise ValidationError("Delete events must have 'e' tags")

        elif event.kind == NostrEventKind.REACTION:
            # Reaction events should have 'e' or 'p' tags
            e_tags = event.get_tag_values("e")
            p_tags = event.get_tag_values("p")
            if not e_tags and not p_tags:
                raise ValidationError("Reaction events must have 'e' or 'p' tags")

    def _validate_id(self, event: NostrEvent) -> None:
        """Validate event ID calculation."""
        calculated_id = event.calculate_id()
        if event.id != calculated_id:
            raise ValidationError(
                f"Event ID mismatch. Expected: {calculated_id}, got: {event.id}"
            )

    def _validate_signature(self, event: NostrEvent) -> None:
        """Validate event signature."""
        if not event.sig:
            raise ValidationError("Event must have a signature")

        if len(event.sig) != 128:  # 64 bytes as hex
            raise ValidationError("Signature must be 128 hex characters")

        try:
            bytes.fromhex(event.sig)
        except ValueError:
            raise ValidationError("Signature must be valid hex")

        # Create the signing data
        signing_data = [
            0,  # Reserved for future use
            event.pubkey,
            event.created_at,
            event.kind.value,
            [tag.to_list() for tag in event.tags],
            event.content,
        ]

        json_str = json.dumps(signing_data, separators=(",", ":"), ensure_ascii=False)

        if not verify_signature(event.pubkey, json_str, event.sig):
            raise ValidationError("Invalid signature")

    def validate_event_dict(self, event_dict: dict[str, Any]) -> None:
        """Validate an event dictionary.

        Args:
            event_dict: Dictionary representation of an event.

        Raises:
            ValidationError: If the event is invalid.
        """
        try:
            event = NostrEvent.from_dict(event_dict)
            self.validate_event(event)
        except (KeyError, ValueError, TypeError) as e:
            raise ValidationError(f"Invalid event structure: {e}")

    def is_valid_event(self, event: NostrEvent, check_signature: bool = True) -> bool:
        """Check if an event is valid without raising exceptions.

        Args:
            event: The event to validate.
            check_signature: Whether to verify the cryptographic signature.

        Returns:
            True if the event is valid, False otherwise.
        """
        try:
            self.validate_event(event, check_signature)
            return True
        except ValidationError:
            return False


class RelayPolicy:
    """Defines relay-specific validation policies."""

    def __init__(
        self,
        allowed_kinds: set[int] | None = None,
        blocked_pubkeys: set[str] | None = None,
        require_pow: bool = False,
        min_pow_difficulty: int = 0,
        max_events_per_minute: int = 60,
    ) -> None:
        """Initialize relay policy.

        Args:
            allowed_kinds: Set of allowed event kinds (None = all allowed).
            blocked_pubkeys: Set of blocked public keys.
            require_pow: Whether to require proof of work.
            min_pow_difficulty: Minimum PoW difficulty.
            max_events_per_minute: Maximum events per minute per pubkey.
        """
        self.allowed_kinds = allowed_kinds
        self.blocked_pubkeys = blocked_pubkeys or set()
        self.require_pow = require_pow
        self.min_pow_difficulty = min_pow_difficulty
        self.max_events_per_minute = max_events_per_minute

        # Rate limiting tracking
        self._event_counts: dict[str, list[float]] = {}

    def check_policy(self, event: NostrEvent, current_time: float) -> tuple[bool, str]:
        """Check if event passes relay policy.

        Args:
            event: The event to check.
            current_time: Current simulation time.

        Returns:
            Tuple of (allowed, reason).
        """
        # Check blocked pubkeys
        if event.pubkey in self.blocked_pubkeys:
            return False, "Pubkey is blocked"

        # Check allowed kinds
        if self.allowed_kinds is not None and event.kind.value not in self.allowed_kinds:
            return False, f"Event kind {event.kind.value} not allowed"

        # Check rate limiting
        if not self._check_rate_limit(event.pubkey, current_time):
            return False, "Rate limit exceeded"

        # Check proof of work
        if self.require_pow:
            pow_difficulty = self._calculate_pow_difficulty(event)
            if pow_difficulty < self.min_pow_difficulty:
                return False, f"Insufficient PoW (got {pow_difficulty}, need {self.min_pow_difficulty})"

        return True, "Accepted"

    def _check_rate_limit(self, pubkey: str, current_time: float) -> bool:
        """Check rate limiting for a pubkey."""
        if pubkey not in self._event_counts:
            self._event_counts[pubkey] = []

        # Clean old entries (older than 1 minute)
        cutoff_time = current_time - 60.0
        self._event_counts[pubkey] = [
            t for t in self._event_counts[pubkey] if t > cutoff_time
        ]

        # Check if under limit
        if len(self._event_counts[pubkey]) >= self.max_events_per_minute:
            return False

        # Add current event
        self._event_counts[pubkey].append(current_time)
        return True

    def _calculate_pow_difficulty(self, event: NostrEvent) -> int:
        """Calculate the proof of work difficulty for an event."""
        # Count leading zeros in the event ID
        difficulty = 0
        for char in event.id:
            if char == '0':
                difficulty += 4  # Each hex digit is 4 bits
            else:
                # Count leading zeros in the binary representation of this hex digit
                hex_value = int(char, 16)
                for i in range(4):
                    if (hex_value >> (3 - i)) & 1 == 0:
                        difficulty += 1
                    else:
                        break
                break
        return difficulty
