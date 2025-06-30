"""Tests for Group Signature Schemes anti-spam strategy."""

from __future__ import annotations

import time

from ..protocol.events import NostrEvent, NostrEventKind, NostrTag
from .group_signature import Group, GroupMember, GroupSignature, GroupSignatureStrategy


class TestGroupMember:
    """Test cases for GroupMember dataclass."""

    def test_group_member_creation(self) -> None:
        """Test GroupMember creation."""
        current_time = time.time()

        member = GroupMember(
            pubkey="test_pubkey",
            member_id="member_123",
            joined_at=current_time,
        )

        assert member.pubkey == "test_pubkey"
        assert member.member_id == "member_123"
        assert member.joined_at == current_time
        assert member.is_active
        assert member.reputation_score == 1.0


class TestGroupSignature:
    """Test cases for GroupSignature dataclass."""

    def test_group_signature_creation(self) -> None:
        """Test GroupSignature creation."""
        signature = b"test_signature"
        group_id = "group_123"
        member_proof = b"proof_123"
        anonymity_level = 5
        timestamp = time.time()

        group_sig = GroupSignature(
            signature=signature,
            group_id=group_id,
            member_proof=member_proof,
            anonymity_level=anonymity_level,
            timestamp=timestamp,
        )

        assert group_sig.signature == signature
        assert group_sig.group_id == group_id
        assert group_sig.member_proof == member_proof
        assert group_sig.anonymity_level == anonymity_level
        assert group_sig.timestamp == timestamp


class TestGroup:
    """Test cases for Group dataclass."""

    def test_group_creation(self) -> None:
        """Test Group creation."""
        current_time = time.time()

        group = Group(
            group_id="group_123",
            name="Test Group",
            admin_pubkey="admin_pubkey",
            created_at=current_time,
        )

        assert group.group_id == "group_123"
        assert group.name == "Test Group"
        assert group.admin_pubkey == "admin_pubkey"
        assert group.created_at == current_time
        assert len(group.members) == 0
        assert len(group.group_key) == 32  # 256-bit key
        assert group.is_active
        assert group.max_members == 100
        assert group.min_reputation == 0.5


class TestGroupSignatureStrategy:
    """Test cases for GroupSignatureStrategy."""

    def test_init(self) -> None:
        """Test strategy initialization."""
        strategy = GroupSignatureStrategy()
        assert strategy.name == "group_signature"
        assert strategy.require_group_membership
        assert strategy.allow_multiple_groups
        assert strategy.min_group_size == 3
        assert strategy.signature_validity_period == 3600.0
        assert strategy.anonymity_threshold == 5

    def test_init_custom_params(self) -> None:
        """Test strategy initialization with custom parameters."""
        strategy = GroupSignatureStrategy(
            require_group_membership=False,
            allow_multiple_groups=False,
            min_group_size=5,
            signature_validity_period=1800.0,
            anonymity_threshold=10,
        )
        assert not strategy.require_group_membership
        assert not strategy.allow_multiple_groups
        assert strategy.min_group_size == 5
        assert strategy.signature_validity_period == 1800.0
        assert strategy.anonymity_threshold == 10

    def test_bypass_when_not_required(self) -> None:
        """Test that events pass when group membership is not required."""
        strategy = GroupSignatureStrategy(require_group_membership=False)
        current_time = time.time()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time),
            pubkey="test_pubkey",
        )

        result = strategy.evaluate_event(event, current_time)
        assert result.allowed
        assert "not required" in result.reason.lower()

    def test_reject_without_group_signature(self) -> None:
        """Test rejection of events without group signatures."""
        strategy = GroupSignatureStrategy(require_group_membership=True)
        current_time = time.time()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time),
            pubkey="test_pubkey",
        )

        result = strategy.evaluate_event(event, current_time)
        assert not result.allowed
        assert "no group signature" in result.reason.lower()

    def test_create_group(self) -> None:
        """Test group creation."""
        strategy = GroupSignatureStrategy()
        current_time = time.time()

        # Create a new group
        success = strategy.create_group(
            "group_123",
            "Test Group",
            "admin_pubkey",
            current_time,
        )
        assert success

        # Check group info
        group_info = strategy.get_group_info("group_123")
        assert group_info is not None
        assert group_info["group_id"] == "group_123"
        assert group_info["name"] == "Test Group"
        assert group_info["admin_pubkey"] == "admin_pubkey"
        assert group_info["total_members"] == 1  # Admin added automatically
        assert group_info["active_members"] == 1

        # Try to create duplicate group
        duplicate_success = strategy.create_group(
            "group_123",
            "Duplicate Group",
            "other_admin",
            current_time,
        )
        assert not duplicate_success

    def test_add_member_to_group(self) -> None:
        """Test adding members to a group."""
        strategy = GroupSignatureStrategy()
        current_time = time.time()

        # Create group
        strategy.create_group("group_123", "Test Group", "admin_pubkey", current_time)

        # Add member
        success = strategy.add_member_to_group("group_123", "member1", current_time)
        assert success

        # Check membership
        assert strategy.is_member_of_group("member1", "group_123")
        assert strategy.is_member_of_group("admin_pubkey", "group_123")

        # Check member groups
        member_groups = strategy.get_member_groups("member1")
        assert "group_123" in member_groups

        # Try to add duplicate member
        duplicate_success = strategy.add_member_to_group(
            "group_123", "member1", current_time
        )
        assert not duplicate_success

        # Try to add to non-existent group
        invalid_success = strategy.add_member_to_group(
            "invalid_group", "member2", current_time
        )
        assert not invalid_success

    def test_remove_member_from_group(self) -> None:
        """Test removing members from a group."""
        strategy = GroupSignatureStrategy()
        current_time = time.time()

        # Create group and add member
        strategy.create_group("group_123", "Test Group", "admin_pubkey", current_time)
        strategy.add_member_to_group("group_123", "member1", current_time)

        # Remove member
        success = strategy.remove_member_from_group("group_123", "member1")
        assert success
        assert not strategy.is_member_of_group("member1", "group_123")

        # Try to remove admin (should fail)
        admin_remove_success = strategy.remove_member_from_group(
            "group_123", "admin_pubkey"
        )
        assert not admin_remove_success

        # Try to remove non-member
        invalid_success = strategy.remove_member_from_group("group_123", "non_member")
        assert not invalid_success

    def test_generate_group_signature(self) -> None:
        """Test group signature generation."""
        strategy = GroupSignatureStrategy(min_group_size=2)
        current_time = time.time()

        # Create group with sufficient members
        strategy.create_group("group_123", "Test Group", "admin_pubkey", current_time)
        strategy.add_member_to_group("group_123", "member1", current_time)

        # Generate signature
        signature = strategy.generate_group_signature(
            "admin_pubkey",
            "group_123",
            "test event content",
            current_time,
        )

        assert signature is not None
        assert signature.group_id == "group_123"
        assert signature.timestamp == current_time
        assert len(signature.signature) == 32  # SHA256 digest
        assert len(signature.member_proof) == 16

        # Try to generate for non-member
        invalid_signature = strategy.generate_group_signature(
            "non_member",
            "group_123",
            "test content",
            current_time,
        )
        assert invalid_signature is None

        # Try to generate for non-existent group
        invalid_group_signature = strategy.generate_group_signature(
            "admin_pubkey",
            "invalid_group",
            "test content",
            current_time,
        )
        assert invalid_group_signature is None

    def test_generate_signature_minimum_group_size(self) -> None:
        """Test that signature generation respects minimum group size."""
        strategy = GroupSignatureStrategy(min_group_size=3)
        current_time = time.time()

        # Create group with insufficient members
        strategy.create_group(
            "small_group", "Small Group", "admin_pubkey", current_time
        )

        # Try to generate signature (should fail due to small group size)
        signature = strategy.generate_group_signature(
            "admin_pubkey",
            "small_group",
            "test content",
            current_time,
        )
        assert signature is None

        # Add enough members
        strategy.add_member_to_group("small_group", "member1", current_time)
        strategy.add_member_to_group("small_group", "member2", current_time)

        # Now signature generation should work
        signature = strategy.generate_group_signature(
            "admin_pubkey",
            "small_group",
            "test content",
            current_time,
        )
        assert signature is not None

    def test_extract_group_signature(self) -> None:
        """Test extraction of group signature from event tags."""
        strategy = GroupSignatureStrategy()
        current_time = time.time()

        # Create event with group signature tag
        signature = b"\\x01\\x02\\x03\\x04"
        group_id = "group_123"
        member_proof = b"\\x05\\x06\\x07\\x08"
        anonymity_level = 5

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time),
            pubkey="test_pubkey",
            tags=[
                NostrTag(
                    name="group_sig",
                    values=[
                        f"{signature.hex()}:{group_id}:{member_proof.hex()}:{anonymity_level}:{current_time}"
                    ],
                ),
            ],
        )

        extracted = strategy._extract_group_signature(event)
        assert extracted is not None
        assert extracted.signature == signature
        assert extracted.group_id == group_id
        assert extracted.member_proof == member_proof
        assert extracted.anonymity_level == anonymity_level
        assert extracted.timestamp == current_time

        # Test event without group signature
        event_no_sig = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time),
            pubkey="test_pubkey",
        )

        extracted_none = strategy._extract_group_signature(event_no_sig)
        assert extracted_none is None

    def test_validate_group_signature(self) -> None:
        """Test group signature validation."""
        strategy = GroupSignatureStrategy(
            min_group_size=2, signature_validity_period=1800.0
        )
        current_time = time.time()

        # Create group and add member
        strategy.create_group("group_123", "Test Group", "admin_pubkey", current_time)
        strategy.add_member_to_group("group_123", "member1", current_time)

        # Generate valid signature
        signature = strategy.generate_group_signature(
            "admin_pubkey",
            "group_123",
            "test content",
            current_time,
        )
        assert signature is not None

        # Create event with valid signature
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            created_at=int(current_time),
            pubkey="admin_pubkey",
            tags=[
                NostrTag(
                    name="group_sig",
                    values=[
                        f"{signature.signature.hex()}:{signature.group_id}:{signature.member_proof.hex()}:{signature.anonymity_level}:{signature.timestamp}"
                    ],
                ),
            ],
        )

        result = strategy.evaluate_event(event, current_time)
        assert result.allowed
        assert "valid group signature" in result.reason.lower()

    def test_validate_expired_signature(self) -> None:
        """Test validation of expired signatures."""
        strategy = GroupSignatureStrategy(
            min_group_size=2, signature_validity_period=300.0
        )
        current_time = time.time()
        old_time = current_time - 600  # 10 minutes ago

        # Create group
        strategy.create_group("group_123", "Test Group", "admin_pubkey", current_time)
        strategy.add_member_to_group("group_123", "member1", current_time)

        # Generate old signature
        signature = strategy.generate_group_signature(
            "admin_pubkey",
            "group_123",
            "test content",
            old_time,
        )
        assert signature is not None

        # Create event with expired signature
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            created_at=int(current_time),
            pubkey="admin_pubkey",
            tags=[
                NostrTag(
                    name="group_sig",
                    values=[
                        f"{signature.signature.hex()}:{signature.group_id}:{signature.member_proof.hex()}:{signature.anonymity_level}:{signature.timestamp}"
                    ],
                ),
            ],
        )

        result = strategy.evaluate_event(event, current_time)
        assert not result.allowed
        assert "expired" in result.reason.lower()

    def test_validate_small_group_signature(self) -> None:
        """Test validation rejects signatures from groups that are too small."""
        strategy = GroupSignatureStrategy(min_group_size=3)
        current_time = time.time()

        # Create small group
        strategy.create_group(
            "small_group", "Small Group", "admin_pubkey", current_time
        )

        # Manually create a signature (bypassing the generation check)
        group = strategy._groups["small_group"]
        signature_data = f"small_group:test content:{current_time}"
        import hashlib
        import hmac

        signature_bytes = hmac.new(
            group.group_key, signature_data.encode(), hashlib.sha256
        ).digest()

        fake_signature = GroupSignature(
            signature=signature_bytes,
            group_id="small_group",
            member_proof=b"fake_proof_12345",
            anonymity_level=1,
            timestamp=current_time,
        )

        # Create event with signature from small group
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            created_at=int(current_time),
            pubkey="admin_pubkey",
            tags=[
                NostrTag(
                    name="group_sig",
                    values=[
                        f"{fake_signature.signature.hex()}:{fake_signature.group_id}:{fake_signature.member_proof.hex()}:{fake_signature.anonymity_level}:{fake_signature.timestamp}"
                    ],
                ),
            ],
        )

        result = strategy.evaluate_event(event, current_time)
        assert not result.allowed
        assert "group too small" in result.reason.lower()

    def test_update_state(self) -> None:
        """Test state updates after processing events."""
        strategy = GroupSignatureStrategy(min_group_size=2)
        current_time = time.time()

        # Create group and signature
        strategy.create_group("group_123", "Test Group", "admin_pubkey", current_time)
        strategy.add_member_to_group("group_123", "member1", current_time)

        signature = strategy.generate_group_signature(
            "admin_pubkey",
            "group_123",
            "test content",
            current_time,
        )
        assert signature is not None

        # Create event
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            created_at=int(current_time),
            pubkey="admin_pubkey",
            tags=[
                NostrTag(
                    name="group_sig",
                    values=[
                        f"{signature.signature.hex()}:{signature.group_id}:{signature.member_proof.hex()}:{signature.anonymity_level}:{signature.timestamp}"
                    ],
                ),
            ],
        )

        # Update state
        strategy.update_state(event, current_time)

        # Check that signature was cached
        signature_key = f"admin_pubkey:group_123:{current_time}"
        assert signature_key in strategy._signature_cache

    def test_cleanup_expired_signatures(self) -> None:
        """Test cleanup of expired signatures."""
        strategy = GroupSignatureStrategy(signature_validity_period=300.0)
        current_time = time.time()
        old_time = current_time - 600

        # Manually add an old signature to cache
        old_signature = GroupSignature(
            signature=b"old_signature",
            group_id="group_123",
            member_proof=b"old_proof",
            anonymity_level=5,
            timestamp=old_time,
        )

        strategy._signature_cache["old_key"] = old_signature

        # Add a recent signature
        recent_signature = GroupSignature(
            signature=b"recent_signature",
            group_id="group_123",
            member_proof=b"recent_proof",
            anonymity_level=5,
            timestamp=current_time,
        )

        strategy._signature_cache["recent_key"] = recent_signature

        # Cleanup
        strategy._cleanup_expired_signatures(current_time)

        # Old signature should be removed, recent one should remain
        assert "old_key" not in strategy._signature_cache
        assert "recent_key" in strategy._signature_cache

    def test_metrics_tracking(self) -> None:
        """Test that metrics are properly tracked."""
        strategy = GroupSignatureStrategy(min_group_size=2)
        current_time = time.time()

        # Create group and member
        strategy.create_group("group_123", "Test Group", "admin_pubkey", current_time)
        strategy.add_member_to_group("group_123", "member1", current_time)

        # Test with no signature
        event_no_sig = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(current_time),
            pubkey="test_pubkey",
        )

        strategy.evaluate_event(event_no_sig, current_time)

        # Generate and test valid signature
        signature = strategy.generate_group_signature(
            "admin_pubkey",
            "group_123",
            "test content",
            current_time,
        )

        assert signature is not None
        event_valid = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            created_at=int(current_time),
            pubkey="admin_pubkey",
            tags=[
                NostrTag(
                    name="group_sig",
                    values=[
                        f"{signature.signature.hex()}:{signature.group_id}:{signature.member_proof.hex()}:{signature.anonymity_level}:{signature.timestamp}"
                    ],
                ),
            ],
        )

        strategy.evaluate_event(event_valid, current_time)

        # Check metrics
        metrics = strategy.get_metrics()
        assert metrics["events_processed"] == 2
        assert metrics["non_members_rejected"] == 1
        assert metrics["group_signatures_verified"] == 1
        assert metrics["groups_created"] == 1
        assert metrics["members_added"] == 2  # Admin + member1

    def test_multiple_groups_membership(self) -> None:
        """Test that users can be members of multiple groups."""
        strategy = GroupSignatureStrategy(min_group_size=2, allow_multiple_groups=True)
        current_time = time.time()

        # Create two groups
        strategy.create_group("group1", "Group 1", "admin1", current_time)
        strategy.create_group("group2", "Group 2", "admin2", current_time)

        # Add same member to both groups
        strategy.add_member_to_group("group1", "member1", current_time)
        strategy.add_member_to_group("group2", "member1", current_time)

        # Check membership
        assert strategy.is_member_of_group("member1", "group1")
        assert strategy.is_member_of_group("member1", "group2")

        member_groups = strategy.get_member_groups("member1")
        assert "group1" in member_groups
        assert "group2" in member_groups
        assert len(member_groups) == 2
