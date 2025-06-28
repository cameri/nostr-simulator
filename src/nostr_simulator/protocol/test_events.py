"""Tests for Nostr protocol events implementation."""

import json

from .events import NostrEvent, NostrEventKind, NostrTag


class TestNostrTag:
    """Test NostrTag functionality."""

    def test_create_tag(self) -> None:
        """Test creating a tag."""
        tag = NostrTag(name="e", values=["event_id", "relay_url"])
        assert tag.name == "e"
        assert tag.values == ["event_id", "relay_url"]

    def test_to_list(self) -> None:
        """Test converting tag to list format."""
        tag = NostrTag(name="p", values=["pubkey", "petname"])
        assert tag.to_list() == ["p", "pubkey", "petname"]

    def test_from_list(self) -> None:
        """Test creating tag from list format."""
        tag_list = ["e", "event_id", "relay_url", "marker"]
        tag = NostrTag.from_list(tag_list)
        assert tag.name == "e"
        assert tag.values == ["event_id", "relay_url", "marker"]

    def test_from_empty_list_raises_error(self) -> None:
        """Test that empty list raises error."""
        try:
            NostrTag.from_list([])
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Tag list cannot be empty" in str(e)

    def test_string_representation(self) -> None:
        """Test string representation."""
        tag = NostrTag(name="t", values=["bitcoin", "nostr"])
        assert str(tag) == "#t:bitcoin:nostr"

        tag_no_values = NostrTag(name="mention")
        assert str(tag_no_values) == "#mention"


class TestNostrEvent:
    """Test NostrEvent functionality."""

    def test_create_basic_event(self) -> None:
        """Test creating a basic event."""
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello, Nostr!",
            created_at=1234567890,
            pubkey="a" * 64,
        )

        assert event.kind == NostrEventKind.TEXT_NOTE
        assert event.content == "Hello, Nostr!"
        assert event.created_at == 1234567890
        assert event.pubkey == "a" * 64
        assert event.id != ""  # ID should be auto-generated
        assert len(event.id) == 64  # SHA256 hex

    def test_id_calculation(self) -> None:
        """Test event ID calculation."""
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test content",
            created_at=1234567890,
            pubkey="b" * 64,
        )

        # Calculate ID manually
        serialized = [
            0,
            "b" * 64,
            1234567890,
            1,
            [],
            "Test content",
        ]
        json_str = json.dumps(serialized, separators=(",", ":"), ensure_ascii=False)

        import hashlib
        expected_id = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

        assert event.id == expected_id

    def test_to_dict(self) -> None:
        """Test converting event to dictionary."""
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test",
            created_at=1234567890,
            pubkey="c" * 64,
            sig="d" * 128,
        )
        event.add_tag("p", "some_pubkey")

        event_dict = event.to_dict()

        assert event_dict["kind"] == 1
        assert event_dict["content"] == "Test"
        assert event_dict["created_at"] == 1234567890
        assert event_dict["pubkey"] == "c" * 64
        assert event_dict["sig"] == "d" * 128
        assert event_dict["tags"] == [["p", "some_pubkey"]]
        assert "id" in event_dict

    def test_from_dict(self) -> None:
        """Test creating event from dictionary."""
        event_dict = {
            "id": "a" * 64,
            "pubkey": "b" * 64,
            "created_at": 1234567890,
            "kind": 1,
            "tags": [["p", "some_pubkey"], ["e", "event_id", "relay"]],
            "content": "Test content",
            "sig": "c" * 128,
        }

        # First create an event to get the correct ID
        temp_event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test content",
            created_at=1234567890,
            pubkey="b" * 64,
        )
        temp_event.add_tag("p", "some_pubkey")
        temp_event.add_tag("e", "event_id", "relay")

        # Update dict with correct ID
        event_dict["id"] = temp_event.id

        event = NostrEvent.from_dict(event_dict)

        assert event.kind == NostrEventKind.TEXT_NOTE
        assert event.content == "Test content"
        assert event.pubkey == "b" * 64
        assert len(event.tags) == 2

    def test_json_serialization(self) -> None:
        """Test JSON serialization and deserialization."""
        original_event = NostrEvent(
            kind=NostrEventKind.SET_METADATA,
            content='{"name":"Alice","about":"Nostr user"}',
            created_at=1234567890,
            pubkey="e" * 64,
        )

        json_str = original_event.to_json()
        deserialized_event = NostrEvent.from_json(json_str)

        assert deserialized_event.kind == original_event.kind
        assert deserialized_event.content == original_event.content
        assert deserialized_event.id == original_event.id

    def test_add_tag(self) -> None:
        """Test adding tags to event."""
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test",
            created_at=1234567890,
            pubkey="f" * 64,
        )

        original_id = event.id
        event.add_tag("t", "bitcoin")

        # ID should change when tags are added
        assert event.id != original_id
        assert len(event.tags) == 1
        assert event.tags[0].name == "t"
        assert event.tags[0].values == ["bitcoin"]

    def test_get_tag_values(self) -> None:
        """Test getting tag values."""
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test",
            created_at=1234567890,
            pubkey="g" * 64,
        )
        event.add_tag("p", "pubkey1")
        event.add_tag("p", "pubkey2", "petname")
        event.add_tag("e", "event_id")

        p_values = event.get_tag_values("p")
        assert len(p_values) == 2
        assert ["pubkey1"] in p_values
        assert ["pubkey2", "petname"] in p_values

        e_values = event.get_tag_values("e")
        assert len(e_values) == 1
        assert ["event_id"] in e_values

    def test_get_first_tag_value(self) -> None:
        """Test getting first tag value."""
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test",
            created_at=1234567890,
            pubkey="h" * 64,
        )
        event.add_tag("p", "pubkey1", "petname1")
        event.add_tag("p", "pubkey2", "petname2")

        first_pubkey = event.get_first_tag_value("p", 0)
        assert first_pubkey == "pubkey1"

        first_petname = event.get_first_tag_value("p", 1)
        assert first_petname == "petname1"

        nonexistent = event.get_first_tag_value("x", 0)
        assert nonexistent is None

    def test_event_type_checks(self) -> None:
        """Test event type checking methods."""
        # Regular event
        regular_event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test",
            created_at=1234567890,
            pubkey="i" * 64,
        )
        assert not regular_event.is_replaceable()
        assert not regular_event.is_ephemeral()
        assert not regular_event.is_parameterized_replaceable()

        # Replaceable event
        replaceable_event = NostrEvent(
            kind=NostrEventKind(10000),
            content="Test",
            created_at=1234567890,
            pubkey="j" * 64,
        )
        assert replaceable_event.is_replaceable()
        assert not replaceable_event.is_ephemeral()
        assert not replaceable_event.is_parameterized_replaceable()

        # Ephemeral event
        ephemeral_event = NostrEvent(
            kind=NostrEventKind(20000),
            content="Test",
            created_at=1234567890,
            pubkey="k" * 64,
        )
        assert not ephemeral_event.is_replaceable()
        assert ephemeral_event.is_ephemeral()
        assert not ephemeral_event.is_parameterized_replaceable()

        # Parameterized replaceable event
        param_event = NostrEvent(
            kind=NostrEventKind(30000),
            content="Test",
            created_at=1234567890,
            pubkey="l" * 64,
        )
        assert not param_event.is_replaceable()
        assert not param_event.is_ephemeral()
        assert param_event.is_parameterized_replaceable()

    def test_replacement_id(self) -> None:
        """Test replacement ID generation."""
        pubkey = "m" * 64

        # Regular event
        regular_event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test",
            created_at=1234567890,
            pubkey=pubkey,
        )
        assert regular_event.get_replacement_id() == regular_event.id

        # Replaceable event
        replaceable_event = NostrEvent(
            kind=NostrEventKind(10000),
            content="Test",
            created_at=1234567890,
            pubkey=pubkey,
        )
        assert replaceable_event.get_replacement_id() == f"{pubkey}:10000"

        # Parameterized replaceable event
        param_event = NostrEvent(
            kind=NostrEventKind(30000),
            content="Test",
            created_at=1234567890,
            pubkey=pubkey,
        )
        param_event.add_tag("d", "identifier")
        assert param_event.get_replacement_id() == f"{pubkey}:30000:identifier"

    def test_event_equality(self) -> None:
        """Test event equality based on ID."""
        event1 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test",
            created_at=1234567890,
            pubkey="n" * 64,
        )

        event2 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test",
            created_at=1234567890,
            pubkey="n" * 64,
        )

        assert event1 == event2  # Same content should produce same ID

        event3 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Different content",
            created_at=1234567890,
            pubkey="n" * 64,
        )

        assert event1 != event3  # Different content should produce different ID

    def test_string_representation(self) -> None:
        """Test string representation."""
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test",
            created_at=1234567890,
            pubkey="o" * 64,
        )

        str_repr = str(event)
        assert "NostrEvent" in str_repr
        assert "TEXT_NOTE" in str_repr
        assert event.id[:8] in str_repr
        assert event.pubkey[:8] in str_repr

    def test_real_world_event(self) -> None:
        """Test validation of a real-world Nostr event."""
        # Real event from the network with valid ID and signature
        event_dict = {
            "pubkey": "00000000827ffaa94bfea288c3dfce4422c794fbb96625b6b31e9049f729d700",
            "kind": 1,
            "sig": "17c2d6346c78b24b20a5b4e9fb4d1aff0543dbe5983111ad73f37db7669338ff53cdff1bce892e6da2053912d7018d759203b6c9a628a069a32c3b00755ef03a",
            "created_at": 1751119008,
            "tags": [
                ["e", "de6f26b370b7495f66d504aee2b95e80068a9bf7dbfdb9e1c3592fe031d1c131", "", "root"],
                ["e", "aa6e1b86f1c16b97ba5d12b1e0dc01d72f423bdb4f1f5067bb7c2099e3e05d53", "", "reply"],
                ["p", "8fb9450003a599bb1b34f03fadb9b137f6c0e5a850ba205964bee4732ccce549"]
            ],
            "content": "Nothing was bothering me, so I felt bored",
            "id": "ed5d4980b94ac8de8579bdf067afb0e6c197ae1ee1ff8d649c74240435584d87"
        }

        # Create event from dictionary
        event = NostrEvent.from_dict(event_dict)

        # Verify basic properties
        assert event.pubkey == "00000000827ffaa94bfea288c3dfce4422c794fbb96625b6b31e9049f729d700"
        assert event.kind == NostrEventKind.TEXT_NOTE
        assert event.content == "Nothing was bothering me, so I felt bored"
        assert event.created_at == 1751119008
        assert event.id == "ed5d4980b94ac8de8579bdf067afb0e6c197ae1ee1ff8d649c74240435584d87"
        assert event.sig == "17c2d6346c78b24b20a5b4e9fb4d1aff0543dbe5983111ad73f37db7669338ff53cdff1bce892e6da2053912d7018d759203b6c9a628a069a32c3b00755ef03a"

        # Verify tags
        assert len(event.tags) == 3

        # Check e tags (event references)
        e_tags = event.get_tag_values("e")
        assert len(e_tags) == 2
        assert ["de6f26b370b7495f66d504aee2b95e80068a9bf7dbfdb9e1c3592fe031d1c131", "", "root"] in e_tags
        assert ["aa6e1b86f1c16b97ba5d12b1e0dc01d72f423bdb4f1f5067bb7c2099e3e05d53", "", "reply"] in e_tags

        # Check p tags (pubkey references)
        p_tags = event.get_tag_values("p")
        assert len(p_tags) == 1
        assert ["8fb9450003a599bb1b34f03fadb9b137f6c0e5a850ba205964bee4732ccce549"] in p_tags

        # Verify ID calculation is correct
        calculated_id = event.calculate_id()
        assert calculated_id == event.id

        # Test round-trip serialization
        json_str = event.to_json()
        deserialized_event = NostrEvent.from_json(json_str)
        assert deserialized_event == event

        # Test dictionary conversion round-trip
        event_dict_output = event.to_dict()
        recreated_event = NostrEvent.from_dict(event_dict_output)
        assert recreated_event == event

    def test_real_world_event_structure_validation(self) -> None:
        """Test structural validation of the real-world event."""
        event_dict = {
            "pubkey": "00000000827ffaa94bfea288c3dfce4422c794fbb96625b6b31e9049f729d700",
            "kind": 1,
            "sig": "17c2d6346c78b24b20a5b4e9fb4d1aff0543dbe5983111ad73f37db7669338ff53cdff1bce892e6da2053912d7018d759203b6c9a628a069a32c3b00755ef03a",
            "created_at": 1751119008,
            "tags": [
                ["e", "de6f26b370b7495f66d504aee2b95e80068a9bf7dbfdb9e1c3592fe031d1c131", "", "root"],
                ["e", "aa6e1b86f1c16b97ba5d12b1e0dc01d72f423bdb4f1f5067bb7c2099e3e05d53", "", "reply"],
                ["p", "8fb9450003a599bb1b34f03fadb9b137f6c0e5a850ba205964bee4732ccce549"]
            ],
            "content": "Nothing was bothering me, so I felt bored",
            "id": "ed5d4980b94ac8de8579bdf067afb0e6c197ae1ee1ff8d649c74240435584d87"
        }

        event = NostrEvent.from_dict(event_dict)

        # Verify pubkey format
        assert len(event.pubkey) == 64
        bytes.fromhex(event.pubkey)  # Should not raise

        # Verify ID format
        assert len(event.id) == 64
        bytes.fromhex(event.id)  # Should not raise

        # Verify signature format
        assert len(event.sig) == 128  # 64 bytes as hex
        bytes.fromhex(event.sig)  # Should not raise

        # Verify timestamp is reasonable (not in far future or past)
        import time as time_module
        current_time = int(time_module.time())
        # Event should be from reasonable time range (not more than a day in future)
        assert event.created_at <= current_time + 86400

        # Verify tags structure
        for tag in event.tags:
            assert isinstance(tag.name, str)
            assert len(tag.name) > 0
            assert isinstance(tag.values, list)
            for value in tag.values:
                assert isinstance(value, str)

    def test_real_world_event_tag_access(self) -> None:
        """Test tag access methods with the real-world event."""
        event_dict = {
            "pubkey": "00000000827ffaa94bfea288c3dfce4422c794fbb96625b6b31e9049f729d700",
            "kind": 1,
            "sig": "17c2d6346c78b24b20a5b4e9fb4d1aff0543dbe5983111ad73f37db7669338ff53cdff1bce892e6da2053912d7018d759203b6c9a628a069a32c3b00755ef03a",
            "created_at": 1751119008,
            "tags": [
                ["e", "de6f26b370b7495f66d504aee2b95e80068a9bf7dbfdb9e1c3592fe031d1c131", "", "root"],
                ["e", "aa6e1b86f1c16b97ba5d12b1e0dc01d72f423bdb4f1f5067bb7c2099e3e05d53", "", "reply"],
                ["p", "8fb9450003a599bb1b34f03fadb9b137f6c0e5a850ba205964bee4732ccce549"]
            ],
            "content": "Nothing was bothering me, so I felt bored",
            "id": "ed5d4980b94ac8de8579bdf067afb0e6c197ae1ee1ff8d649c74240435584d87"
        }

        event = NostrEvent.from_dict(event_dict)        # Test getting first event reference (root)
        root_event_id = event.get_first_tag_value("e", 0)
        assert root_event_id == "de6f26b370b7495f66d504aee2b95e80068a9bf7dbfdb9e1c3592fe031d1c131"

        # Test getting relay URL (empty string at index 1)
        root_relay = event.get_first_tag_value("e", 1)
        assert root_relay == ""

        # Test getting event type marker at index 2
        root_type = event.get_first_tag_value("e", 2)
        assert root_type == "root"

        # Test getting referenced pubkey
        referenced_pubkey = event.get_first_tag_value("p", 0)
        assert referenced_pubkey == "8fb9450003a599bb1b34f03fadb9b137f6c0e5a850ba205964bee4732ccce549"

        # Test getting all e tag values
        e_values = event.get_tag_values("e")
        assert len(e_values) == 2

        # Test getting non-existent tag
        non_existent = event.get_first_tag_value("z", 0)
        assert non_existent is None

    def test_signature_validation(self) -> None:
        """Test event signature validation methods."""
        from ..protocol.keys import NostrKeyPair, sign_event_dict

        # Create a keypair and event
        keypair = NostrKeyPair.generate()
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test signature validation",
            created_at=1234567890,
            pubkey=keypair.public_key,
        )

        # Event without signature should be invalid
        assert not event.is_signature_valid()

        # Add a proper signature
        event_dict = event.to_dict()
        signature = sign_event_dict(keypair.private_key, event_dict)
        event.sig = signature

        # Now signature should be valid
        assert event.is_signature_valid()

        # Test with invalid signature format
        event.sig = "invalid"
        assert not event.is_signature_valid()

        # Test with wrong length signature
        event.sig = "a" * 64  # Too short
        assert not event.is_signature_valid()

        # Test with non-hex signature
        event.sig = "g" * 128  # Invalid hex
        assert not event.is_signature_valid()

    def test_id_validation(self) -> None:
        """Test event ID validation methods."""
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test ID validation",
            created_at=1234567890,
            pubkey="a" * 64,
        )

        # Event with auto-generated ID should be valid
        assert event.is_id_valid()

        # Test with invalid ID
        event.id = "invalid"
        assert not event.is_id_valid()

        # Test with wrong length ID
        event.id = "a" * 32  # Too short
        assert not event.is_id_valid()

        # Test with non-hex ID
        event.id = "g" * 64  # Invalid hex
        assert not event.is_id_valid()

        # Test with empty ID
        event.id = ""
        assert not event.is_id_valid()

        # Restore correct ID
        event.id = event.calculate_id()
        assert event.is_id_valid()

    def test_comprehensive_validation(self) -> None:
        """Test the comprehensive is_valid method."""
        from ..protocol.keys import NostrKeyPair, sign_event_dict

        # Create a valid event with signature
        keypair = NostrKeyPair.generate()
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test comprehensive validation",
            created_at=1234567890,
            pubkey=keypair.public_key,
        )

        # Add proper signature
        event_dict = event.to_dict()
        signature = sign_event_dict(keypair.private_key, event_dict)
        event.sig = signature

        # Should be valid with signature check
        assert event.is_valid(check_signature=True)

        # Should be valid without signature check
        assert event.is_valid(check_signature=False)

        # Test with invalid ID
        original_id = event.id
        event.id = "a" * 64  # Wrong ID
        assert not event.is_valid(check_signature=False)
        assert not event.is_valid(check_signature=True)

        # Restore ID, break signature
        event.id = original_id
        event.sig = "b" * 128  # Wrong signature
        assert event.is_valid(check_signature=False)  # ID is valid
        assert not event.is_valid(check_signature=True)  # Signature is invalid

    def test_real_world_event_validation(self) -> None:
        """Test validation methods with the real-world event."""
        event_dict = {
            "pubkey": "00000000827ffaa94bfea288c3dfce4422c794fbb96625b6b31e9049f729d700",
            "kind": 1,
            "sig": "17c2d6346c78b24b20a5b4e9fb4d1aff0543dbe5983111ad73f37db7669338ff53cdff1bce892e6da2053912d7018d759203b6c9a628a069a32c3b00755ef03a",
            "created_at": 1751119008,
            "tags": [
                ["e", "de6f26b370b7495f66d504aee2b95e80068a9bf7dbfdb9e1c3592fe031d1c131", "", "root"],
                ["e", "aa6e1b86f1c16b97ba5d12b1e0dc01d72f423bdb4f1f5067bb7c2099e3e05d53", "", "reply"],
                ["p", "8fb9450003a599bb1b34f03fadb9b137f6c0e5a850ba205964bee4732ccce549"]
            ],
            "content": "Nothing was bothering me, so I felt bored",
            "id": "ed5d4980b94ac8de8579bdf067afb0e6c197ae1ee1ff8d649c74240435584d87"
        }

        event = NostrEvent.from_dict(event_dict)

        # The ID should be valid (matches calculated hash)
        assert event.is_id_valid()

        # The signature should be valid (properly formatted, though we can't
        # cryptographically verify it in our simplified system)
        assert event.is_signature_valid()

        # Comprehensive validation should pass
        assert event.is_valid(check_signature=True)
        assert event.is_valid(check_signature=False)
