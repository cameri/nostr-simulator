"""Hashchain and rolling codes anti-spam strategies."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import Any

from ..protocol.events import NostrEvent
from .base import AntiSpamStrategy, StrategyResult


@dataclass
class HashchainState:
    """State of a user's hashchain."""

    seed: bytes  # Secret seed for the chain
    current_hash: bytes  # Current position in the chain
    sequence_number: int  # Current sequence number
    last_update: float  # Last update timestamp
    chain_length: int  # Total length of the chain


@dataclass
class RollingCode:
    """A rolling code for anti-spam validation."""

    code: bytes  # The actual code
    timestamp: float  # When the code was generated
    sequence: int  # Sequence number in the chain
    expires_at: float  # When the code expires


class HashchainRollingCodes(AntiSpamStrategy):
    """Hashchain-based rolling codes for anti-spam protection."""

    def __init__(
        self,
        chain_length: int = 1000,
        code_validity_period: float = 300.0,  # 5 minutes
        rotation_interval: float = 60.0,  # 1 minute
        max_future_codes: int = 3,  # Allow some clock skew
        hash_algorithm: str = "sha256",
    ) -> None:
        """Initialize hashchain rolling codes strategy.

        Args:
            chain_length: Maximum length of each hashchain.
            code_validity_period: How long codes remain valid (seconds).
            rotation_interval: How often to rotate codes (seconds).
            max_future_codes: Maximum future codes to accept (clock skew tolerance).
            hash_algorithm: Hash algorithm to use.
        """
        super().__init__("hashchain_rolling_codes")
        self.chain_length = chain_length
        self.code_validity_period = code_validity_period
        self.rotation_interval = rotation_interval
        self.max_future_codes = max_future_codes
        self.hash_algorithm = hash_algorithm

        # User state tracking
        self._user_chains: dict[str, HashchainState] = {}
        self._used_codes: dict[str, set[bytes]] = {}  # Prevent replay attacks
        self._pending_codes: dict[str, list[RollingCode]] = {}

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate event using hashchain rolling codes."""
        start_time = time.time()

        # Get or create hashchain for this user
        if event.pubkey not in self._user_chains:
            self._initialize_user_chain(event.pubkey, current_time)

        chain_state = self._user_chains[event.pubkey]

        # Extract rolling code from event (we'll look for it in tags)
        rolling_code = self._extract_rolling_code(event)
        if not rolling_code:
            computational_cost = time.time() - start_time
            return StrategyResult(
                allowed=False,
                reason="No rolling code found in event",
                metrics={"chain_position": chain_state.sequence_number},
                computational_cost=computational_cost,
            )

        # Validate the rolling code
        validation_result = self._validate_rolling_code(
            event.pubkey, rolling_code, current_time
        )

        computational_cost = time.time() - start_time

        if validation_result["valid"]:
            # Update chain state
            self._advance_chain(event.pubkey, current_time)

            return StrategyResult(
                allowed=True,
                reason=validation_result["reason"],
                metrics={
                    "chain_position": chain_state.sequence_number,
                    "code_age": validation_result.get("code_age", 0),
                },
                computational_cost=computational_cost,
            )
        else:
            return StrategyResult(
                allowed=False,
                reason=validation_result["reason"],
                metrics={
                    "chain_position": chain_state.sequence_number,
                    "validation_error": validation_result.get("error_type", "unknown"),
                },
                computational_cost=computational_cost,
            )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update state after processing event."""
        # Clean up expired codes
        self._cleanup_expired_codes(current_time)

        # Mark code as used if event was processed
        rolling_code = self._extract_rolling_code(event)
        if rolling_code and event.pubkey in self._used_codes:
            self._used_codes[event.pubkey].add(rolling_code)

    def _initialize_user_chain(self, pubkey: str, current_time: float) -> None:
        """Initialize a new hashchain for a user."""
        seed = secrets.token_bytes(32)  # 256-bit seed
        initial_hash = self._hash_function(seed)

        self._user_chains[pubkey] = HashchainState(
            seed=seed,
            current_hash=initial_hash,
            sequence_number=0,
            last_update=current_time,
            chain_length=self.chain_length,
        )

        self._used_codes[pubkey] = set()
        self._pending_codes[pubkey] = []

    def _extract_rolling_code(self, event: NostrEvent) -> bytes | None:
        """Extract rolling code from event tags."""
        # Look for a tag with name "rolling_code"
        for tag in event.tags:
            if tag.name == "rolling_code" and tag.values:
                try:
                    return bytes.fromhex(tag.values[0])
                except ValueError:
                    continue
        return None

    def _validate_rolling_code(
        self, pubkey: str, code: bytes, current_time: float
    ) -> dict[str, Any]:
        """Validate a rolling code against the user's chain."""
        if pubkey not in self._user_chains:
            return {"valid": False, "reason": "No chain found for user"}

        # Check if code was already used (replay attack)
        if code in self._used_codes.get(pubkey, set()):
            return {
                "valid": False,
                "reason": "Rolling code already used",
                "error_type": "replay",
            }

        # Generate expected codes for current and near-future time slots
        expected_codes = self._generate_expected_codes(pubkey, current_time)

        for expected_code in expected_codes:
            if hmac.compare_digest(code, expected_code.code):
                # Check if code is still valid
                if current_time > expected_code.expires_at:
                    return {
                        "valid": False,
                        "reason": "Rolling code expired",
                        "error_type": "expired",
                    }

                code_age = current_time - expected_code.timestamp
                return {
                    "valid": True,
                    "reason": f"Valid rolling code (age: {code_age:.1f}s)",
                    "code_age": code_age,
                }

        return {
            "valid": False,
            "reason": "Invalid rolling code",
            "error_type": "invalid",
        }

    def _generate_expected_codes(
        self, pubkey: str, current_time: float
    ) -> list[RollingCode]:
        """Generate expected rolling codes for current time."""
        if pubkey not in self._user_chains:
            return []

        chain_state = self._user_chains[pubkey]
        codes = []

        # Generate codes for current and future time slots
        current_slot = int(current_time // self.rotation_interval)

        for i in range(self.max_future_codes + 1):
            slot_time = (current_slot - i) * self.rotation_interval
            if slot_time < 0:
                continue

            # Generate code for this time slot
            slot_data = f"{pubkey}:{slot_time}:{chain_state.sequence_number}".encode()
            code_hash = hmac.new(
                chain_state.current_hash, slot_data, self.hash_algorithm
            ).digest()[
                :16
            ]  # Use first 16 bytes

            code = RollingCode(
                code=code_hash,
                timestamp=slot_time,
                sequence=chain_state.sequence_number,
                expires_at=slot_time + self.code_validity_period,
            )
            codes.append(code)

        return codes

    def _advance_chain(self, pubkey: str, current_time: float) -> None:
        """Advance the user's hashchain."""
        if pubkey not in self._user_chains:
            return

        chain_state = self._user_chains[pubkey]

        # Check if we need to regenerate the chain (reached end)
        if chain_state.sequence_number >= self.chain_length - 1:
            self._regenerate_chain(pubkey, current_time)
            return

        # Advance the chain
        new_hash = self._hash_function(chain_state.current_hash)
        chain_state.current_hash = new_hash
        chain_state.sequence_number += 1
        chain_state.last_update = current_time

    def _regenerate_chain(self, pubkey: str, current_time: float) -> None:
        """Regenerate a user's hashchain when it reaches the end."""
        if pubkey not in self._user_chains:
            return

        # Generate new seed and restart chain
        new_seed = secrets.token_bytes(32)
        initial_hash = self._hash_function(new_seed)

        self._user_chains[pubkey] = HashchainState(
            seed=new_seed,
            current_hash=initial_hash,
            sequence_number=0,
            last_update=current_time,
            chain_length=self.chain_length,
        )

        # Clear used codes for this user
        self._used_codes[pubkey] = set()

    def _cleanup_expired_codes(self, current_time: float) -> None:
        """Clean up expired codes and old state."""
        for pubkey in list(self._used_codes.keys()):
            # Remove very old used codes (keep some history for replay prevention)
            # This is a simplified cleanup - in practice you'd want more sophisticated logic
            if len(self._used_codes[pubkey]) > 1000:  # Arbitrary limit
                # Keep only recent codes
                self._used_codes[pubkey] = set(list(self._used_codes[pubkey])[-500:])

    def _hash_function(self, data: bytes) -> bytes:
        """Apply the configured hash function to data."""
        if self.hash_algorithm == "sha256":
            return hashlib.sha256(data).digest()
        elif self.hash_algorithm == "sha512":
            return hashlib.sha512(data).digest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {self.hash_algorithm}")

    def generate_code_for_user(self, pubkey: str, current_time: float) -> bytes | None:
        """Generate a valid rolling code for a user (for testing/client use)."""
        if pubkey not in self._user_chains:
            self._initialize_user_chain(pubkey, current_time)

        expected_codes = self._generate_expected_codes(pubkey, current_time)
        if expected_codes:
            return expected_codes[0].code  # Return most current code
        return None

    def get_chain_info(self, pubkey: str) -> dict[str, Any] | None:
        """Get information about a user's chain state."""
        if pubkey not in self._user_chains:
            return None

        chain_state = self._user_chains[pubkey]
        return {
            "sequence_number": chain_state.sequence_number,
            "chain_length": chain_state.chain_length,
            "last_update": chain_state.last_update,
            "used_codes_count": len(self._used_codes.get(pubkey, set())),
        }

    def get_metrics(self) -> dict[str, Any]:
        """Get strategy metrics."""
        total_chains = len(self._user_chains)
        total_used_codes = sum(len(codes) for codes in self._used_codes.values())

        if total_chains > 0:
            avg_sequence = (
                sum(chain.sequence_number for chain in self._user_chains.values())
                / total_chains
            )
            chains_near_end = sum(
                1
                for chain in self._user_chains.values()
                if chain.sequence_number > chain.chain_length * 0.9
            )
        else:
            avg_sequence = 0
            chains_near_end = 0

        return {
            "total_chains": total_chains,
            "average_sequence_number": avg_sequence,
            "chains_near_end": chains_near_end,
            "total_used_codes": total_used_codes,
            "chain_length": self.chain_length,
            "code_validity_period": self.code_validity_period,
            "rotation_interval": self.rotation_interval,
        }


class TimeBasedCodeRotation(AntiSpamStrategy):
    """Simple time-based code rotation strategy."""

    def __init__(
        self,
        rotation_interval: float = 300.0,  # 5 minutes
        code_length: int = 8,  # bytes
        master_key: bytes | None = None,
    ) -> None:
        """Initialize time-based code rotation.

        Args:
            rotation_interval: How often codes rotate (seconds).
            code_length: Length of generated codes in bytes.
            master_key: Master key for code generation (auto-generated if None).
        """
        super().__init__("time_based_code_rotation")
        self.rotation_interval = rotation_interval
        self.code_length = code_length
        self.master_key = master_key or secrets.token_bytes(32)

        self._used_codes: dict[str, set[bytes]] = {}

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate event using time-based code rotation."""
        start_time = time.time()

        # Extract code from event
        code = self._extract_code(event)
        if not code:
            computational_cost = time.time() - start_time
            return StrategyResult(
                allowed=False,
                reason="No time-based code found in event",
                computational_cost=computational_cost,
            )

        # Check if code was already used
        if code in self._used_codes.get(event.pubkey, set()):
            computational_cost = time.time() - start_time
            return StrategyResult(
                allowed=False,
                reason="Time-based code already used",
                computational_cost=computational_cost,
            )

        # Validate code for current and recent time slots
        current_slot = int(current_time // self.rotation_interval)

        for slot_offset in range(3):  # Check current and 2 previous slots
            slot = current_slot - slot_offset
            expected_code = self._generate_code_for_slot(event.pubkey, slot)

            if hmac.compare_digest(code, expected_code):
                computational_cost = time.time() - start_time
                return StrategyResult(
                    allowed=True,
                    reason=f"Valid time-based code (slot offset: {slot_offset})",
                    metrics={"slot_offset": slot_offset, "current_slot": current_slot},
                    computational_cost=computational_cost,
                )

        computational_cost = time.time() - start_time
        return StrategyResult(
            allowed=False,
            reason="Invalid time-based code",
            computational_cost=computational_cost,
        )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update state after processing event."""
        code = self._extract_code(event)
        if code:
            if event.pubkey not in self._used_codes:
                self._used_codes[event.pubkey] = set()
            self._used_codes[event.pubkey].add(code)

        # Cleanup old codes periodically
        if len(self._used_codes.get(event.pubkey, set())) > 100:
            self._cleanup_old_codes(event.pubkey)

    def _extract_code(self, event: NostrEvent) -> bytes | None:
        """Extract time-based code from event."""
        for tag in event.tags:
            if tag.name == "time_code" and tag.values:
                try:
                    return bytes.fromhex(tag.values[0])
                except ValueError:
                    continue
        return None

    def _generate_code_for_slot(self, pubkey: str, slot: int) -> bytes:
        """Generate code for a specific time slot."""
        slot_data = f"{pubkey}:{slot}".encode()
        return hmac.new(self.master_key, slot_data, "sha256").digest()[
            : self.code_length
        ]

    def _cleanup_old_codes(self, pubkey: str) -> None:
        """Clean up old codes for a user."""
        if pubkey in self._used_codes:
            # Keep only the 50 most recent codes
            codes_list = list(self._used_codes[pubkey])
            self._used_codes[pubkey] = set(codes_list[-50:])

    def generate_current_code(self, pubkey: str, current_time: float) -> bytes:
        """Generate the current valid code for a user."""
        current_slot = int(current_time // self.rotation_interval)
        return self._generate_code_for_slot(pubkey, current_slot)

    def get_metrics(self) -> dict[str, Any]:
        """Get strategy metrics."""
        total_users = len(self._used_codes)
        total_used_codes = sum(len(codes) for codes in self._used_codes.values())

        return {
            "total_users": total_users,
            "total_used_codes": total_used_codes,
            "rotation_interval": self.rotation_interval,
            "code_length": self.code_length,
        }
