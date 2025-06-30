"""Nostr event structure implementation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class NostrEventKind(IntEnum):
    """Standard Nostr event kinds."""

    # Basic events
    SET_METADATA = 0
    TEXT_NOTE = 1
    RECOMMEND_RELAY = 2
    CONTACTS = 3
    ENCRYPTED_DIRECT_MESSAGE = 4
    DELETE = 5
    REPOST = 6
    REACTION = 7
    CHANNEL_CREATE = 40
    CHANNEL_METADATA = 41
    CHANNEL_MESSAGE = 42
    CHANNEL_HIDE_MESSAGE = 43
    CHANNEL_MUTE_USER = 44

    # Replaceable events
    REPLACEABLE_FIRST = 10000
    REPLACEABLE_LAST = 19999

    # Ephemeral events
    EPHEMERAL_FIRST = 20000
    EPHEMERAL_LAST = 29999

    # Parameterized replaceable events
    PARAM_REPLACEABLE_FIRST = 30000
    PARAM_REPLACEABLE_LAST = 39999


@dataclass
class NostrTag:
    """Represents a Nostr event tag."""

    name: str
    values: list[str] = field(default_factory=list)

    def to_list(self) -> list[str]:
        """Convert tag to list format for serialization."""
        return [self.name] + self.values

    @classmethod
    def from_list(cls, tag_list: list[str]) -> NostrTag:
        """Create tag from list format."""
        if not tag_list:
            raise ValueError("Tag list cannot be empty")
        return cls(name=tag_list[0], values=tag_list[1:])

    def __str__(self) -> str:
        """String representation of the tag."""
        return f"#{self.name}" + (":" + ":".join(self.values) if self.values else "")


@dataclass
class NostrEvent:
    """
    Represents a Nostr event.

    This class encapsulates all components of a Nostr protocol event, including metadata,
    content, cryptographic identifiers, and any attached tags.

    Attributes:
      kind (NostrEventKind):
        The type of the event as defined by NIP-01. Determines processing rules
        (e.g. replaceable, ephemeral, parameterized replaceable).
      content (str):
        The textual payload of the event, typically UTF-8 encoded.
      created_at (int):
        Unix timestamp (seconds since epoch) indicating when the event was created.
      pubkey (str):
        Hex-encoded public key of the event creator. Used for authentication
        and to derive the event ID when signing.
      id (str):
        Hexadecimal SHA-256 hash of the serialized event data. Automatically
        generated in __post_init__ if not supplied.
      sig (str):
        Hex-encoded Schnorr signature over the event ID. Proves authenticity
        and integrity of the event. May be empty until signed.
      tags (list[NostrTag]):
        Ordered list of NostrTag instances for categorization, threading,
        references, routing, or other metadata extensions.
    """

    """Represents a Nostr event."""

    kind: NostrEventKind
    content: str
    created_at: int
    pubkey: str
    id: str = ""
    sig: str = ""
    tags: list[NostrTag] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Generate event ID if not provided."""
        if not self.id:
            self.id = self.calculate_id()

    def calculate_id(self) -> str:
        """Calculate the event ID according to NIP-01."""
        # Create the serialized event data for ID calculation
        serialized = [
            0,  # Reserved for future use
            self.pubkey,
            self.created_at,
            self.kind.value,
            [tag.to_list() for tag in self.tags],
            self.content,
        ]

        # Convert to JSON string (compact, no spaces)
        json_str = json.dumps(serialized, separators=(",", ":"), ensure_ascii=False)

        # Calculate SHA256 hash
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary format."""
        return {
            "id": self.id,
            "pubkey": self.pubkey,
            "created_at": self.created_at,
            "kind": self.kind.value,
            "tags": [tag.to_list() for tag in self.tags],
            "content": self.content,
            "sig": self.sig,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NostrEvent:
        """Create event from dictionary format."""
        tags = [NostrTag.from_list(tag) for tag in data.get("tags", [])]

        event = cls(
            id=data.get("id", ""),
            pubkey=data["pubkey"],
            created_at=data["created_at"],
            kind=NostrEventKind(data["kind"]),
            tags=tags,
            content=data["content"],
            sig=data.get("sig", ""),
        )

        # Verify the ID matches if provided
        if event.id and event.id != event.calculate_id():
            raise ValueError("Event ID does not match calculated ID")

        return event

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_json(cls, json_str: str) -> NostrEvent:
        """Create event from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def get_tag_values(self, tag_name: str) -> list[list[str]]:
        """Get all values for tags with the given name."""
        return [tag.values for tag in self.tags if tag.name == tag_name]

    def get_first_tag_value(self, tag_name: str, index: int = 0) -> str | None:
        """Get the first value at the given index for a tag name."""
        values = self.get_tag_values(tag_name)
        if values and len(values[0]) > index:
            return values[0][index]
        return None

    def add_tag(self, name: str, *values: str) -> None:
        """Add a tag to the event."""
        self.tags.append(NostrTag(name=name, values=list(values)))
        # Recalculate ID since tags changed
        self.id = self.calculate_id()

    def is_replaceable(self) -> bool:
        """Check if this is a replaceable event."""
        return (
            NostrEventKind.REPLACEABLE_FIRST
            <= self.kind
            <= NostrEventKind.REPLACEABLE_LAST
        )

    def is_ephemeral(self) -> bool:
        """Check if this is an ephemeral event."""
        return (
            NostrEventKind.EPHEMERAL_FIRST <= self.kind <= NostrEventKind.EPHEMERAL_LAST
        )

    def is_parameterized_replaceable(self) -> bool:
        """Check if this is a parameterized replaceable event."""
        return (
            NostrEventKind.PARAM_REPLACEABLE_FIRST
            <= self.kind
            <= NostrEventKind.PARAM_REPLACEABLE_LAST
        )

    def get_replacement_id(self) -> str:
        """Get the replacement ID for replaceable events."""
        if self.is_parameterized_replaceable():
            # For parameterized replaceable events, use pubkey:kind:d_tag
            d_tag = self.get_first_tag_value("d", 0) or ""
            return f"{self.pubkey}:{self.kind.value}:{d_tag}"
        elif self.is_replaceable():
            # For regular replaceable events, use pubkey:kind
            return f"{self.pubkey}:{self.kind.value}"
        else:
            # For non-replaceable events, use the event ID
            return self.id

    def __str__(self) -> str:
        """String representation of the event."""
        return f"NostrEvent(id={self.id[:8]}..., kind={self.kind.name}, pubkey={self.pubkey[:8]}...)"

    def __eq__(self, other: object) -> bool:
        """Check event equality based on ID."""
        if not isinstance(other, NostrEvent):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on event ID."""
        return hash(self.id)

    def is_signature_valid(self) -> bool:
        """
        Validate the event signature.

        Verifies that the signature (sig) is cryptographically valid for this event's
        ID and public key. This is equivalent to secp256k1.schnorr.verify().

        Returns:
            True if the signature is valid, False otherwise.

        Note:
            This uses a simplified verification for simulation purposes.
            In a real implementation, this would use proper secp256k1 cryptography.
        """
        if not self.sig:
            return False

        if (
            len(self.sig) != 64 and len(self.sig) != 128
        ):  # Support both simulation (32 bytes) and real (64 bytes) as hex
            return False

        try:
            bytes.fromhex(self.sig)
        except ValueError:
            return False

        # For simulation, we'll use the same verification logic as in validation.py
        from .keys import verify_signature

        # Create the signing data according to NIP-01
        signing_data = [
            0,  # Reserved for future use
            self.pubkey,
            self.created_at,
            self.kind.value,
            [tag.to_list() for tag in self.tags],
            self.content,
        ]

        json_str = json.dumps(signing_data, separators=(",", ":"), ensure_ascii=False)
        return verify_signature(self.pubkey, json_str, self.sig)

    def is_id_valid(self) -> bool:
        """
        Validate the event ID.

        Verifies that the ID field matches the calculated hash of the event data
        according to NIP-01 specification.

        Returns:
            True if the ID is valid, False otherwise.
        """
        if not self.id:
            return False

        if len(self.id) != 64:  # 32 bytes as hex
            return False

        try:
            bytes.fromhex(self.id)
        except ValueError:
            return False

        # Check if the ID matches the calculated hash
        return self.id == self.calculate_id()

    def is_valid(self, check_signature: bool = False) -> bool:
        """
        Perform comprehensive validation of the event.

        Args:
            check_signature: Whether to validate the signature (requires sig field).

        Returns:
            True if the event is valid, False otherwise.
        """
        # Check ID validity
        if not self.is_id_valid():
            return False

        # Check basic format requirements
        if not self.pubkey or len(self.pubkey) != 64:
            return False

        try:
            bytes.fromhex(self.pubkey)
        except ValueError:
            return False

        # Check timestamp is reasonable
        if self.created_at < 0:
            return False

        # Check signature if requested
        if check_signature and not self.is_signature_valid():
            return False

        return True
