"""Group Signature Schemes anti-spam strategy implementation."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from ..protocol.events import NostrEvent
from .base import AntiSpamStrategy, StrategyResult


@dataclass
class GroupMember:
    """Represents a member of a group."""

    pubkey: str
    member_id: str
    joined_at: float
    is_active: bool = True
    reputation_score: float = 1.0


@dataclass
class GroupSignature:
    """Represents a group signature for verification."""

    signature: bytes
    group_id: str
    member_proof: bytes
    anonymity_level: int
    timestamp: float


@dataclass
class Group:
    """Represents a group with signature capabilities."""

    group_id: str
    name: str
    admin_pubkey: str
    created_at: float
    members: dict[str, GroupMember] = field(default_factory=dict)
    group_key: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    is_active: bool = True
    max_members: int = 100
    min_reputation: float = 0.5


class GroupSignatureStrategy(AntiSpamStrategy):
    """Group Signature Schemes anti-spam strategy.

    This strategy allows only verified members of specific groups to post,
    providing both authentication and anonymity within the group.
    """

    def __init__(
        self,
        require_group_membership: bool = True,
        allow_multiple_groups: bool = True,
        min_group_size: int = 3,
        signature_validity_period: float = 3600.0,  # 1 hour
        anonymity_threshold: int = 5,  # Minimum members for anonymity
    ) -> None:
        """Initialize the Group Signature strategy.

        Args:
            require_group_membership: Whether group membership is required.
            allow_multiple_groups: Whether users can be in multiple groups.
            min_group_size: Minimum group size for valid signatures.
            signature_validity_period: How long signatures remain valid.
            anonymity_threshold: Minimum group size for anonymity guarantees.
        """
        super().__init__("group_signature")

        self.require_group_membership = require_group_membership
        self.allow_multiple_groups = allow_multiple_groups
        self.min_group_size = min_group_size
        self.signature_validity_period = signature_validity_period
        self.anonymity_threshold = anonymity_threshold

        # Storage for groups and members
        self._groups: dict[str, Group] = {}
        self._member_groups: dict[str, set[str]] = {}  # pubkey -> set of group_ids
        self._signature_cache: dict[str, GroupSignature] = {}

        self._metrics = {
            "events_processed": 0,
            "group_signatures_verified": 0,
            "invalid_signatures": 0,
            "non_members_rejected": 0,
            "expired_signatures": 0,
            "small_groups_rejected": 0,
            "groups_created": 0,
            "members_added": 0,
        }

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate event using group signature validation.

        Args:
            event: The event to evaluate.
            current_time: Current simulation time.

        Returns:
            StrategyResult indicating if the event is allowed and why.
        """
        start_time = time.time()
        self._metrics["events_processed"] += 1

        if not self.require_group_membership:
            # If group membership is not required, allow all events
            computational_cost = time.time() - start_time
            return StrategyResult(
                allowed=True,
                reason="Group membership not required",
                metrics={"validation_type": "bypass"},
                computational_cost=computational_cost,
            )

        # Extract group signature from event
        group_signature = self._extract_group_signature(event)
        if group_signature is None:
            self._metrics["non_members_rejected"] += 1
            computational_cost = time.time() - start_time
            return StrategyResult(
                allowed=False,
                reason="No group signature found",
                metrics={"validation_type": "no_signature"},
                computational_cost=computational_cost,
            )

        # Validate the group signature
        validation_result = self._validate_group_signature(
            event, group_signature, current_time
        )

        computational_cost = time.time() - start_time

        if validation_result["valid"]:
            self._metrics["group_signatures_verified"] += 1
            return StrategyResult(
                allowed=True,
                reason=validation_result["reason"],
                metrics={
                    "validation_type": "group_signature",
                    "group_id": group_signature.group_id,
                    "anonymity_level": group_signature.anonymity_level,
                },
                computational_cost=computational_cost,
            )
        else:
            # Track specific error types
            error_type = validation_result.get("error_type", "unknown")
            if error_type == "expired":
                self._metrics["expired_signatures"] += 1
            elif error_type == "invalid":
                self._metrics["invalid_signatures"] += 1
            elif error_type == "small_group":
                self._metrics["small_groups_rejected"] += 1

            return StrategyResult(
                allowed=False,
                reason=validation_result["reason"],
                metrics={
                    "validation_type": "group_signature_failed",
                    "error_type": error_type,
                },
                computational_cost=computational_cost,
            )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update state after processing event.

        Args:
            event: The processed event.
            current_time: Current simulation time.
        """
        # Clean up expired signatures
        self._cleanup_expired_signatures(current_time)

        # Cache the signature if valid
        group_signature = self._extract_group_signature(event)
        if group_signature:
            signature_key = (
                f"{event.pubkey}:{group_signature.group_id}:{group_signature.timestamp}"
            )
            self._signature_cache[signature_key] = group_signature

    def create_group(
        self,
        group_id: str,
        name: str,
        admin_pubkey: str,
        current_time: float,
        max_members: int = 100,
    ) -> bool:
        """Create a new group.

        Args:
            group_id: Unique identifier for the group.
            name: Human-readable name for the group.
            admin_pubkey: Public key of the group administrator.
            current_time: Current simulation time.
            max_members: Maximum number of members allowed.

        Returns:
            True if group was created successfully, False otherwise.
        """
        if group_id in self._groups:
            return False

        group = Group(
            group_id=group_id,
            name=name,
            admin_pubkey=admin_pubkey,
            created_at=current_time,
            max_members=max_members,
        )

        self._groups[group_id] = group
        self._metrics["groups_created"] += 1

        # Add admin as first member
        self.add_member_to_group(group_id, admin_pubkey, current_time)

        return True

    def add_member_to_group(
        self, group_id: str, pubkey: str, current_time: float
    ) -> bool:
        """Add a member to a group.

        Args:
            group_id: ID of the group to add member to.
            pubkey: Public key of the member to add.
            current_time: Current simulation time.

        Returns:
            True if member was added successfully, False otherwise.
        """
        if group_id not in self._groups:
            return False

        group = self._groups[group_id]

        if not group.is_active:
            return False

        if len(group.members) >= group.max_members:
            return False

        if pubkey in group.members:
            return False

        # Generate unique member ID
        member_id = hashlib.sha256(
            f"{group_id}:{pubkey}:{current_time}".encode()
        ).hexdigest()[:16]

        member = GroupMember(
            pubkey=pubkey,
            member_id=member_id,
            joined_at=current_time,
        )

        group.members[pubkey] = member

        # Update member groups mapping
        if pubkey not in self._member_groups:
            self._member_groups[pubkey] = set()
        self._member_groups[pubkey].add(group_id)

        self._metrics["members_added"] += 1

        return True

    def remove_member_from_group(self, group_id: str, pubkey: str) -> bool:
        """Remove a member from a group.

        Args:
            group_id: ID of the group to remove member from.
            pubkey: Public key of the member to remove.

        Returns:
            True if member was removed successfully, False otherwise.
        """
        if group_id not in self._groups:
            return False

        group = self._groups[group_id]

        if pubkey not in group.members:
            return False

        # Don't allow removing the admin
        if pubkey == group.admin_pubkey:
            return False

        del group.members[pubkey]

        # Update member groups mapping
        if pubkey in self._member_groups:
            self._member_groups[pubkey].discard(group_id)
            if not self._member_groups[pubkey]:
                del self._member_groups[pubkey]

        return True

    def generate_group_signature(
        self, pubkey: str, group_id: str, event_data: str, current_time: float
    ) -> GroupSignature | None:
        """Generate a group signature for an event.

        Args:
            pubkey: Public key of the member creating the signature.
            group_id: ID of the group to sign for.
            event_data: The event data to sign.
            current_time: Current simulation time.

        Returns:
            Generated group signature, or None if invalid.
        """
        if group_id not in self._groups:
            return None

        group = self._groups[group_id]

        if not group.is_active:
            return None

        if pubkey not in group.members:
            return None

        member = group.members[pubkey]
        if not member.is_active:
            return None

        # Check minimum group size
        active_members = sum(1 for m in group.members.values() if m.is_active)
        if active_members < self.min_group_size:
            return None

        # Generate signature components
        signature_data = f"{group_id}:{event_data}:{current_time}"
        signature = hmac.new(
            group.group_key, signature_data.encode(), hashlib.sha256
        ).digest()

        # Generate member proof (anonymized)
        member_proof_data = f"{member.member_id}:{signature_data}"
        member_proof = hashlib.sha256(member_proof_data.encode()).digest()[:16]

        # Determine anonymity level based on group size
        anonymity_level = min(active_members, self.anonymity_threshold)

        return GroupSignature(
            signature=signature,
            group_id=group_id,
            member_proof=member_proof,
            anonymity_level=anonymity_level,
            timestamp=current_time,
        )

    def _extract_group_signature(self, event: NostrEvent) -> GroupSignature | None:
        """Extract group signature from event tags.

        Args:
            event: The event to extract signature from.

        Returns:
            GroupSignature if found, None otherwise.
        """
        for tag in event.tags:
            if tag.name == "group_sig" and len(tag.values) >= 1:
                try:
                    sig_data = tag.values[0].split(":")
                    if len(sig_data) >= 5:
                        signature = bytes.fromhex(sig_data[0])
                        group_id = sig_data[1]
                        member_proof = bytes.fromhex(sig_data[2])
                        anonymity_level = int(sig_data[3])
                        timestamp = float(sig_data[4])

                        return GroupSignature(
                            signature=signature,
                            group_id=group_id,
                            member_proof=member_proof,
                            anonymity_level=anonymity_level,
                            timestamp=timestamp,
                        )
                except (ValueError, IndexError):
                    continue

        return None

    def _validate_group_signature(
        self, event: NostrEvent, group_signature: GroupSignature, current_time: float
    ) -> dict[str, Any]:
        """Validate a group signature.

        Args:
            event: The event containing the signature.
            group_signature: The group signature to validate.
            current_time: Current simulation time.

        Returns:
            Dictionary with validation result and reason.
        """
        # Check if signature is expired
        age = current_time - group_signature.timestamp
        if age > self.signature_validity_period:
            return {
                "valid": False,
                "reason": f"Group signature expired: {age:.1f}s old",
                "error_type": "expired",
            }

        # Check if group exists
        if group_signature.group_id not in self._groups:
            return {
                "valid": False,
                "reason": "Group does not exist",
                "error_type": "invalid",
            }

        group = self._groups[group_signature.group_id]

        if not group.is_active:
            return {
                "valid": False,
                "reason": "Group is not active",
                "error_type": "invalid",
            }

        # Check minimum group size
        active_members = sum(1 for m in group.members.values() if m.is_active)
        if active_members < self.min_group_size:
            return {
                "valid": False,
                "reason": f"Group too small: {active_members} < {self.min_group_size}",
                "error_type": "small_group",
            }

        # Verify the signature
        signature_data = (
            f"{group_signature.group_id}:{event.content}:{group_signature.timestamp}"
        )
        expected_signature = hmac.new(
            group.group_key, signature_data.encode(), hashlib.sha256
        ).digest()

        if not hmac.compare_digest(group_signature.signature, expected_signature):
            return {
                "valid": False,
                "reason": "Invalid group signature",
                "error_type": "invalid",
            }

        return {
            "valid": True,
            "reason": f"Valid group signature from group {group_signature.group_id}",
            "group_size": active_members,
            "anonymity_level": group_signature.anonymity_level,
        }

    def _cleanup_expired_signatures(self, current_time: float) -> None:
        """Clean up expired signatures from cache.

        Args:
            current_time: Current simulation time.
        """
        expired_keys = []
        for key, signature in self._signature_cache.items():
            age = current_time - signature.timestamp
            if age > self.signature_validity_period:
                expired_keys.append(key)

        for key in expired_keys:
            del self._signature_cache[key]

    def get_group_info(self, group_id: str) -> dict[str, Any] | None:
        """Get information about a group.

        Args:
            group_id: ID of the group to get info for.

        Returns:
            Dictionary with group information, or None if not found.
        """
        if group_id not in self._groups:
            return None

        group = self._groups[group_id]
        active_members = sum(1 for m in group.members.values() if m.is_active)

        return {
            "group_id": group.group_id,
            "name": group.name,
            "admin_pubkey": group.admin_pubkey,
            "created_at": group.created_at,
            "is_active": group.is_active,
            "total_members": len(group.members),
            "active_members": active_members,
            "max_members": group.max_members,
        }

    def get_member_groups(self, pubkey: str) -> list[str]:
        """Get list of group IDs that a member belongs to.

        Args:
            pubkey: Public key of the member.

        Returns:
            List of group IDs.
        """
        return list(self._member_groups.get(pubkey, set()))

    def is_member_of_group(self, pubkey: str, group_id: str) -> bool:
        """Check if a pubkey is a member of a specific group.

        Args:
            pubkey: Public key to check.
            group_id: Group ID to check membership in.

        Returns:
            True if pubkey is a member of the group, False otherwise.
        """
        if group_id not in self._groups:
            return False

        group = self._groups[group_id]
        return pubkey in group.members and group.members[pubkey].is_active
