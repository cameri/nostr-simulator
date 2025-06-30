"""Tests for hashchain and rolling codes anti-spam strategies."""

import time

from ..protocol.events import NostrEvent, NostrEventKind, NostrTag
from .hashchain import (
    HashchainRollingCodes,
    HashchainState,
    RollingCode,
    TimeBasedCodeRotation,
)


class TestHashchainRollingCodes:
    """Test HashchainRollingCodes strategy."""

    def create_test_event(
        self, pubkey: str = "test_pubkey", rolling_code: str | None = None
    ) -> NostrEvent:
        """Create a test event with optional rolling code."""
        tags = []
        if rolling_code:
            tags.append(NostrTag(name="rolling_code", values=[rolling_code]))

        return NostrEvent(
            id="test_id",
            pubkey=pubkey,
            created_at=int(time.time()),
            kind=NostrEventKind.TEXT_NOTE,
            tags=tags,
            content="test content",
            sig="test_sig",
        )

    def test_strategy_creation(self) -> None:
        """Test strategy creation."""
        strategy = HashchainRollingCodes(
            chain_length=500,
            code_validity_period=180.0,
            rotation_interval=30.0,
        )

        assert strategy.name == "hashchain_rolling_codes"
        assert strategy.chain_length == 500
        assert strategy.code_validity_period == 180.0
        assert strategy.rotation_interval == 30.0

    def test_no_rolling_code_rejected(self) -> None:
        """Test that events without rolling codes are rejected."""
        strategy = HashchainRollingCodes()
        event = self.create_test_event()  # No rolling code

        result = strategy.evaluate_event(event, 0.0)

        assert result.allowed is False
        assert "No rolling code found" in result.reason

    def test_user_chain_initialization(self) -> None:
        """Test that user chains are automatically initialized."""
        strategy = HashchainRollingCodes()
        pubkey = "test_user"

        # Generate a code for the user (this should initialize the chain)
        current_time = time.time()
        code = strategy.generate_code_for_user(pubkey, current_time)

        assert code is not None
        assert pubkey in strategy._user_chains

        chain_info = strategy.get_chain_info(pubkey)
        assert chain_info is not None
        assert chain_info["sequence_number"] == 0

    def test_valid_rolling_code_accepted(self) -> None:
        """Test that valid rolling codes are accepted."""
        strategy = HashchainRollingCodes(rotation_interval=60.0)
        pubkey = "test_user"
        current_time = 1000.0

        # Generate a valid code
        code = strategy.generate_code_for_user(pubkey, current_time)
        assert code is not None

        # Create event with the valid code
        event = self.create_test_event(pubkey, code.hex())

        result = strategy.evaluate_event(event, current_time)

        assert result.allowed is True
        assert "Valid rolling code" in result.reason

    def test_invalid_rolling_code_rejected(self) -> None:
        """Test that invalid rolling codes are rejected."""
        strategy = HashchainRollingCodes()
        pubkey = "test_user"

        # Initialize chain
        strategy.generate_code_for_user(pubkey, 1000.0)

        # Use an invalid code
        event = self.create_test_event(pubkey, "deadbeef" * 4)

        result = strategy.evaluate_event(event, 1000.0)

        assert result.allowed is False
        assert "Invalid rolling code" in result.reason

    def test_replay_attack_prevention(self) -> None:
        """Test that replay attacks are prevented."""
        strategy = HashchainRollingCodes()
        pubkey = "test_user"
        current_time = 1000.0

        # Generate valid code
        code = strategy.generate_code_for_user(pubkey, current_time)
        assert code is not None
        event = self.create_test_event(pubkey, code.hex())

        # First use should be accepted
        result1 = strategy.evaluate_event(event, current_time)
        strategy.update_state(event, current_time)
        assert result1.allowed is True

        # Second use should be rejected (replay)
        result2 = strategy.evaluate_event(event, current_time + 1.0)
        assert result2.allowed is False
        assert "already used" in result2.reason

    def test_expired_code_rejected(self) -> None:
        """Test that expired codes are rejected."""
        strategy = HashchainRollingCodes(code_validity_period=60.0)
        pubkey = "test_user"
        current_time = 1000.0

        # Generate code
        code = strategy.generate_code_for_user(pubkey, current_time)
        assert code is not None
        event = self.create_test_event(pubkey, code.hex())

        # Use code after it expires
        expired_time = current_time + 120.0  # Well beyond validity period
        result = strategy.evaluate_event(event, expired_time)

        assert result.allowed is False
        assert "expired" in result.reason

    def test_chain_advancement(self) -> None:
        """Test that the chain advances after valid code use."""
        strategy = HashchainRollingCodes()
        pubkey = "test_user"
        current_time = 1000.0

        # Get initial chain info
        strategy.generate_code_for_user(pubkey, current_time)
        initial_info = strategy.get_chain_info(pubkey)
        assert initial_info is not None
        initial_sequence = initial_info["sequence_number"]

        # Use a valid code
        code = strategy.generate_code_for_user(pubkey, current_time)
        assert code is not None
        event = self.create_test_event(pubkey, code.hex())
        result = strategy.evaluate_event(event, current_time)
        assert result.allowed is True

        # Chain should advance after processing
        strategy.update_state(event, current_time)
        # Note: Chain advances in evaluate_event if valid
        final_info = strategy.get_chain_info(pubkey)
        assert final_info is not None
        assert final_info["sequence_number"] > initial_sequence

    def test_chain_regeneration(self) -> None:
        """Test that chains are regenerated when they reach the end."""
        strategy = HashchainRollingCodes(chain_length=5)  # Very short chain
        pubkey = "test_user"
        current_time = 1000.0

        # Initialize chain
        strategy.generate_code_for_user(pubkey, current_time)
        initial_info = strategy.get_chain_info(pubkey)

        # Manually advance to near end of chain
        chain_state = strategy._user_chains[pubkey]
        chain_state.sequence_number = 4  # Near end of 5-length chain

        # Use code that should trigger regeneration
        code = strategy.generate_code_for_user(pubkey, current_time)
        assert code is not None
        event = self.create_test_event(pubkey, code.hex())
        strategy.evaluate_event(event, current_time)

        # Chain should be regenerated
        final_info = strategy.get_chain_info(pubkey)
        assert final_info is not None
        assert final_info["sequence_number"] == 0  # Reset to beginning

    def test_clock_skew_tolerance(self) -> None:
        """Test that the strategy tolerates some clock skew."""
        strategy = HashchainRollingCodes(rotation_interval=60.0, max_future_codes=2)
        pubkey = "test_user"
        base_time = 1000.0

        # Generate code for slightly past time
        past_code = strategy.generate_code_for_user(pubkey, base_time - 30.0)
        assert past_code is not None
        event = self.create_test_event(pubkey, past_code.hex())

        # Should still be accepted within tolerance
        result = strategy.evaluate_event(event, base_time)
        assert result.allowed is True

    def test_different_hash_algorithms(self) -> None:
        """Test using different hash algorithms."""
        strategy_sha256 = HashchainRollingCodes(hash_algorithm="sha256")
        strategy_sha512 = HashchainRollingCodes(hash_algorithm="sha512")

        # Both should work without errors
        pubkey = "test_user"
        current_time = 1000.0

        code_256 = strategy_sha256.generate_code_for_user(pubkey, current_time)
        code_512 = strategy_sha512.generate_code_for_user(pubkey, current_time)

        assert code_256 is not None
        assert code_512 is not None
        assert code_256 != code_512  # Should be different

    def test_metrics(self) -> None:
        """Test strategy metrics."""
        strategy = HashchainRollingCodes()

        # Initially no data
        metrics = strategy.get_metrics()
        assert metrics["total_chains"] == 0
        assert metrics["average_sequence_number"] == 0

        # Add some users
        for i in range(3):
            pubkey = f"user_{i}"
            strategy.generate_code_for_user(pubkey, 1000.0)

        metrics = strategy.get_metrics()
        assert metrics["total_chains"] == 3
        assert metrics["chain_length"] == strategy.chain_length


class TestTimeBasedCodeRotation:
    """Test TimeBasedCodeRotation strategy."""

    def create_test_event(
        self, pubkey: str = "test_pubkey", time_code: str | None = None
    ) -> NostrEvent:
        """Create a test event with optional time code."""
        tags = []
        if time_code:
            tags.append(NostrTag(name="time_code", values=[time_code]))

        return NostrEvent(
            id="test_id",
            pubkey=pubkey,
            created_at=int(time.time()),
            kind=NostrEventKind.TEXT_NOTE,
            tags=tags,
            content="test content",
            sig="test_sig",
        )

    def test_strategy_creation(self) -> None:
        """Test strategy creation."""
        strategy = TimeBasedCodeRotation(
            rotation_interval=120.0,
            code_length=12,
        )

        assert strategy.name == "time_based_code_rotation"
        assert strategy.rotation_interval == 120.0
        assert strategy.code_length == 12
        assert len(strategy.master_key) == 32

    def test_no_time_code_rejected(self) -> None:
        """Test that events without time codes are rejected."""
        strategy = TimeBasedCodeRotation()
        event = self.create_test_event()  # No time code

        result = strategy.evaluate_event(event, 0.0)

        assert result.allowed is False
        assert "No time-based code found" in result.reason

    def test_valid_time_code_accepted(self) -> None:
        """Test that valid time codes are accepted."""
        strategy = TimeBasedCodeRotation(rotation_interval=300.0)
        pubkey = "test_user"
        current_time = 1500.0  # Slot 5 (1500 / 300)

        # Generate current valid code
        valid_code = strategy.generate_current_code(pubkey, current_time)
        event = self.create_test_event(pubkey, valid_code.hex())

        result = strategy.evaluate_event(event, current_time)

        assert result.allowed is True
        assert "Valid time-based code" in result.reason
        assert result.metrics is not None
        assert result.metrics["slot_offset"] == 0

    def test_recent_time_code_accepted(self) -> None:
        """Test that recent (but not current) time codes are accepted."""
        strategy = TimeBasedCodeRotation(rotation_interval=300.0)
        pubkey = "test_user"
        base_time = 1500.0

        # Generate code for previous slot
        previous_slot_time = base_time - 300.0
        previous_code = strategy.generate_current_code(pubkey, previous_slot_time)
        event = self.create_test_event(pubkey, previous_code.hex())

        # Should be accepted with slot offset 1
        result = strategy.evaluate_event(event, base_time)

        assert result.allowed is True
        assert result.metrics is not None
        assert result.metrics["slot_offset"] == 1

    def test_old_time_code_rejected(self) -> None:
        """Test that old time codes are rejected."""
        strategy = TimeBasedCodeRotation(rotation_interval=300.0)
        pubkey = "test_user"
        base_time = 1500.0

        # Generate code for very old slot (beyond tolerance)
        old_slot_time = base_time - 1200.0  # 4 slots ago
        old_code = strategy.generate_current_code(pubkey, old_slot_time)
        event = self.create_test_event(pubkey, old_code.hex())

        result = strategy.evaluate_event(event, base_time)

        assert result.allowed is False
        assert "Invalid time-based code" in result.reason

    def test_invalid_time_code_rejected(self) -> None:
        """Test that invalid time codes are rejected."""
        strategy = TimeBasedCodeRotation()
        event = self.create_test_event("test_user", "deadbeef" * 2)

        result = strategy.evaluate_event(event, 1000.0)

        assert result.allowed is False
        assert "Invalid time-based code" in result.reason

    def test_replay_prevention(self) -> None:
        """Test that replay attacks are prevented."""
        strategy = TimeBasedCodeRotation()
        pubkey = "test_user"
        current_time = 1000.0

        # Generate valid code
        code = strategy.generate_current_code(pubkey, current_time)
        event = self.create_test_event(pubkey, code.hex())

        # First use should be accepted
        result1 = strategy.evaluate_event(event, current_time)
        strategy.update_state(event, current_time)
        assert result1.allowed is True

        # Second use should be rejected
        result2 = strategy.evaluate_event(event, current_time + 1.0)
        assert result2.allowed is False
        assert "already used" in result2.reason

    def test_code_generation_deterministic(self) -> None:
        """Test that code generation is deterministic."""
        master_key = b"test_key_32_bytes_long_for_hmac"
        strategy = TimeBasedCodeRotation(master_key=master_key)

        pubkey = "test_user"
        time1 = 1000.0
        time2 = 1000.0  # Same time

        code1 = strategy.generate_current_code(pubkey, time1)
        code2 = strategy.generate_current_code(pubkey, time2)

        assert code1 == code2  # Should be identical

    def test_different_users_different_codes(self) -> None:
        """Test that different users get different codes."""
        strategy = TimeBasedCodeRotation()
        current_time = 1000.0

        code1 = strategy.generate_current_code("user1", current_time)
        code2 = strategy.generate_current_code("user2", current_time)

        assert code1 != code2

    def test_code_cleanup(self) -> None:
        """Test that old codes are cleaned up."""
        strategy = TimeBasedCodeRotation(rotation_interval=1.0)  # 1 second slots
        pubkey = "test_user"

        # Simulate many code uses across different time slots
        for i in range(150):  # More than cleanup threshold
            # Use larger time differences to ensure different slots
            time_val = float(i * 10)  # 10 second intervals
            code = strategy.generate_current_code(pubkey, time_val)
            event = self.create_test_event(pubkey, code.hex())
            strategy.update_state(event, time_val)

        # Should have triggered cleanup and reduced the count
        # Since sets don't preserve order, we can't guarantee exact count,
        # but it should be significantly less than 150
        assert len(strategy._used_codes[pubkey]) < 150
        assert (
            len(strategy._used_codes[pubkey]) <= 100
        )  # Should not exceed cleanup threshold

    def test_metrics(self) -> None:
        """Test strategy metrics."""
        strategy = TimeBasedCodeRotation()

        # Initially no data
        metrics = strategy.get_metrics()
        assert metrics["total_users"] == 0
        assert metrics["total_used_codes"] == 0

        # Simulate some usage
        for i in range(3):
            pubkey = f"user_{i}"
            code = strategy.generate_current_code(pubkey, 1000.0)
            event = self.create_test_event(pubkey, code.hex())
            strategy.update_state(event, 1000.0)

        metrics = strategy.get_metrics()
        assert metrics["total_users"] == 3
        assert metrics["total_used_codes"] == 3


class TestHashchainState:
    """Test HashchainState dataclass."""

    def test_hashchain_state_creation(self) -> None:
        """Test creating HashchainState."""
        seed = b"test_seed_32_bytes_long_for_test"
        current_hash = b"test_hash_value"

        state = HashchainState(
            seed=seed,
            current_hash=current_hash,
            sequence_number=42,
            last_update=1000.0,
            chain_length=1000,
        )

        assert state.seed == seed
        assert state.current_hash == current_hash
        assert state.sequence_number == 42
        assert state.last_update == 1000.0
        assert state.chain_length == 1000


class TestRollingCode:
    """Test RollingCode dataclass."""

    def test_rolling_code_creation(self) -> None:
        """Test creating RollingCode."""
        code = b"test_code_value"

        rolling_code = RollingCode(
            code=code,
            timestamp=1000.0,
            sequence=5,
            expires_at=1300.0,
        )

        assert rolling_code.code == code
        assert rolling_code.timestamp == 1000.0
        assert rolling_code.sequence == 5
        assert rolling_code.expires_at == 1300.0
