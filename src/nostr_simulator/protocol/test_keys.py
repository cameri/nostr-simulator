"""Tests for Nostr protocol key management."""

from .keys import (
    KeyManager,
    NostrKeyPair,
    generate_keypair,
    sign_event_dict,
    verify_signature,
)


class TestNostrKeyPair:
    """Test NostrKeyPair functionality."""

    def test_generate_keypair(self) -> None:
        """Test keypair generation."""
        keypair = NostrKeyPair.generate()

        assert len(keypair.private_key) == 64  # 32 bytes as hex
        assert len(keypair.public_key) == 64   # 32 bytes as hex

        # Verify they are valid hex
        bytes.fromhex(keypair.private_key)
        bytes.fromhex(keypair.public_key)

    def test_generate_unique_keypairs(self) -> None:
        """Test that generated keypairs are unique."""
        keypair1 = NostrKeyPair.generate()
        keypair2 = NostrKeyPair.generate()

        assert keypair1.private_key != keypair2.private_key
        assert keypair1.public_key != keypair2.public_key

    def test_from_private_key(self) -> None:
        """Test creating keypair from private key."""
        private_key = "a" * 64
        keypair = NostrKeyPair.from_private_key(private_key)

        assert keypair.private_key == private_key
        assert len(keypair.public_key) == 64

    def test_from_invalid_private_key(self) -> None:
        """Test creating keypair from invalid private key."""
        try:
            NostrKeyPair.from_private_key("invalid")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "must be 64 hex characters" in str(e)

    def test_sign_event(self) -> None:
        """Test event signing."""
        keypair = NostrKeyPair.generate()
        event_data = "test event data"

        signature = keypair.sign_event(event_data)

        assert len(signature) == 64  # 32 bytes as hex
        bytes.fromhex(signature)  # Should be valid hex

    def test_consistent_signing(self) -> None:
        """Test that signing is consistent."""
        keypair = NostrKeyPair.generate()
        event_data = "test event data"

        sig1 = keypair.sign_event(event_data)
        sig2 = keypair.sign_event(event_data)

        assert sig1 == sig2  # Same data should produce same signature

    def test_npub_nsec_format(self) -> None:
        """Test npub and nsec format."""
        keypair = NostrKeyPair.generate()

        npub = keypair.get_npub()
        nsec = keypair.get_nsec()

        assert npub.startswith("npub1")
        assert nsec.startswith("nsec1")
        assert len(npub) == 69  # npub1 + 64 hex chars
        assert len(nsec) == 69  # nsec1 + 64 hex chars

    def test_string_representation(self) -> None:
        """Test string representation."""
        keypair = NostrKeyPair.generate()
        str_repr = str(keypair)

        assert "NostrKeyPair" in str_repr
        assert keypair.public_key[:8] in str_repr


class TestKeyFunctions:
    """Test standalone key functions."""

    def test_generate_keypair_function(self) -> None:
        """Test the generate_keypair function."""
        keypair = generate_keypair()

        assert isinstance(keypair, NostrKeyPair)
        assert len(keypair.private_key) == 64
        assert len(keypair.public_key) == 64

    def test_verify_signature_valid_format(self) -> None:
        """Test signature verification with valid format."""
        public_key = "a" * 64
        event_data = "test data"
        signature = "b" * 64

        # Our simplified verification should pass for any valid format
        result = verify_signature(public_key, event_data, signature)
        assert result is True

    def test_verify_signature_invalid_format(self) -> None:
        """Test signature verification with invalid format."""
        public_key = "a" * 64
        event_data = "test data"

        # Too short
        result = verify_signature(public_key, event_data, "abc")
        assert result is False

        # Invalid hex
        result = verify_signature(public_key, event_data, "g" * 64)
        assert result is False

    def test_sign_event_dict(self) -> None:
        """Test signing an event dictionary."""
        private_key = "a" * 64
        event_dict = {
            "pubkey": "b" * 64,
            "created_at": 1234567890,
            "kind": 1,
            "tags": [],
            "content": "test content",
        }

        signature = sign_event_dict(private_key, event_dict)

        assert len(signature) == 64
        bytes.fromhex(signature)  # Should be valid hex


class TestKeyManager:
    """Test KeyManager functionality."""

    def test_generate_key(self) -> None:
        """Test generating and storing a key."""
        manager = KeyManager()

        keypair = manager.generate_key("test_key")

        assert isinstance(keypair, NostrKeyPair)
        assert manager.get_key("test_key") == keypair

    def test_get_nonexistent_key(self) -> None:
        """Test getting a nonexistent key."""
        manager = KeyManager()

        result = manager.get_key("nonexistent")
        assert result is None

    def test_list_keys(self) -> None:
        """Test listing stored keys."""
        manager = KeyManager()

        assert manager.list_keys() == []

        manager.generate_key("key1")
        manager.generate_key("key2")

        keys = manager.list_keys()
        assert "key1" in keys
        assert "key2" in keys
        assert len(keys) == 2

    def test_remove_key(self) -> None:
        """Test removing a key."""
        manager = KeyManager()

        manager.generate_key("test_key")
        assert manager.get_key("test_key") is not None

        result = manager.remove_key("test_key")
        assert result is True
        assert manager.get_key("test_key") is None

        # Try to remove again
        result = manager.remove_key("test_key")
        assert result is False

    def test_sign_with_key(self) -> None:
        """Test signing with a stored key."""
        manager = KeyManager()

        keypair = manager.generate_key("test_key")
        event_data = "test event data"

        signature = manager.sign_with_key("test_key", event_data)
        expected_signature = keypair.sign_event(event_data)

        assert signature == expected_signature

    def test_sign_with_nonexistent_key(self) -> None:
        """Test signing with a nonexistent key."""
        manager = KeyManager()

        result = manager.sign_with_key("nonexistent", "data")
        assert result is None
