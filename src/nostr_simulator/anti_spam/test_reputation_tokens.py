"""Tests for reputation tokens anti-spam strategy."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from nostr_simulator.anti_spam.reputation_tokens import (
    ReputationAccount,
    ReputationTokenRenewal,
    ReputationTokenStrategy,
)
from nostr_simulator.protocol.events import NostrEvent, NostrEventKind, NostrTag


class TestReputationAccount:
    """Test ReputationAccount class."""

    def test_create_account(self) -> None:
        """Test creating a reputation account."""
        account = ReputationAccount(
            pubkey="test_pubkey",
            tokens=10.0,
            earned_total=10.0,
            spent_total=0.0,
            last_activity=1000.0,
            last_decay=1000.0,
        )

        assert account.pubkey == "test_pubkey"
        assert account.tokens == 10.0
        assert account.earned_total == 10.0
        assert account.spent_total == 0.0
        assert account.reputation_score == 0.0

    def test_can_spend_tokens(self) -> None:
        """Test checking if account can spend tokens."""
        account = ReputationAccount(
            pubkey="test",
            tokens=5.0,
            earned_total=10.0,
            spent_total=5.0,
            last_activity=1000.0,
            last_decay=1000.0,
        )

        assert account.can_spend(3.0) is True
        assert account.can_spend(5.0) is True
        assert account.can_spend(6.0) is False

    def test_spend_tokens_success(self) -> None:
        """Test successful token spending."""
        account = ReputationAccount(
            pubkey="test",
            tokens=10.0,
            earned_total=10.0,
            spent_total=0.0,
            last_activity=1000.0,
            last_decay=1000.0,
        )

        result = account.spend_tokens(3.0)

        assert result is True
        assert account.tokens == 7.0
        assert account.spent_total == 3.0

    def test_spend_tokens_insufficient(self) -> None:
        """Test token spending with insufficient tokens."""
        account = ReputationAccount(
            pubkey="test",
            tokens=2.0,
            earned_total=10.0,
            spent_total=8.0,
            last_activity=1000.0,
            last_decay=1000.0,
        )

        result = account.spend_tokens(5.0)

        assert result is False
        assert account.tokens == 2.0
        assert account.spent_total == 8.0

    def test_earn_tokens(self) -> None:
        """Test earning tokens."""
        account = ReputationAccount(
            pubkey="test",
            tokens=5.0,
            earned_total=10.0,
            spent_total=5.0,
            last_activity=1000.0,
            last_decay=1000.0,
        )

        account.earn_tokens(3.0, 2000.0)

        assert account.tokens == 8.0
        assert account.earned_total == 13.0
        assert account.last_activity == 2000.0

    def test_apply_decay(self) -> None:
        """Test token decay application."""
        account = ReputationAccount(
            pubkey="test",
            tokens=10.0,
            earned_total=10.0,
            spent_total=0.0,
            last_activity=1000.0,
            last_decay=1000.0,
        )

        # Apply decay after 1000 seconds with 0.001 decay rate
        account.apply_decay(0.001, 2000.0)

        # tokens should be reduced: 10.0 * (1 - 0.001)^1000 ≈ 3.68
        assert account.tokens < 10.0
        assert account.tokens > 3.0
        assert account.last_decay == 2000.0

    def test_apply_decay_initial(self) -> None:
        """Test decay application with initial timestamp."""
        account = ReputationAccount(
            pubkey="test",
            tokens=10.0,
            earned_total=10.0,
            spent_total=0.0,
            last_activity=1000.0,
            last_decay=0,
        )

        account.apply_decay(0.001, 1000.0)

        # Should set last_decay but not change tokens
        assert account.tokens == 10.0
        assert account.last_decay == 1000.0

    def test_update_reputation_score_high_ratio(self) -> None:
        """Test reputation score with high earn/spend ratio."""
        account = ReputationAccount(
            pubkey="test",
            tokens=10.0,
            earned_total=20.0,
            spent_total=5.0,  # ratio = 4.0
            last_activity=1000.0,
            last_decay=1000.0,
        )

        account.update_reputation_score(1000.0)  # No time passed

        # Score should be high due to good ratio and no time decay
        assert account.reputation_score > 0.7

    def test_update_reputation_score_with_time_decay(self) -> None:
        """Test reputation score with time since last activity."""
        account = ReputationAccount(
            pubkey="test",
            tokens=10.0,
            earned_total=20.0,
            spent_total=10.0,  # ratio = 2.0
            last_activity=1000.0,
            last_decay=1000.0,
        )

        # 12 hours later (43200 seconds)
        account.update_reputation_score(44200.0)

        # Score should be reduced due to time decay (50% of 24 hours = 0.5 recency)
        expected_score = min(1.0, 2.0 * 0.7 + 0.5 * 0.3)  # ~1.0 (capped)
        assert account.reputation_score > 0.9  # Should still be high but less than perfect

    def test_update_reputation_score_no_spending(self) -> None:
        """Test reputation score with no spending history."""
        account = ReputationAccount(
            pubkey="test",
            tokens=10.0,
            earned_total=10.0,
            spent_total=0.0,
            last_activity=1000.0,
            last_decay=1000.0,
        )

        account.update_reputation_score(1000.0)

        # Should use base score for no spending with initial tokens
        expected_score = min(1.0, 0.5 * 0.7 + 1.0 * 0.3)  # = 0.65
        assert abs(account.reputation_score - expected_score) < 0.01


class TestReputationTokenStrategy:
    """Test ReputationTokenStrategy class."""

    def test_init(self) -> None:
        """Test strategy initialization."""
        strategy = ReputationTokenStrategy(
            initial_tokens=20.0,
            post_cost=2.0,
            earn_rate=0.2,
            decay_rate=0.002,
            reputation_threshold=0.9,
            max_tokens=200.0,
        )

        assert strategy.name == "reputation_tokens"
        assert strategy.initial_tokens == 20.0
        assert strategy.post_cost == 2.0
        assert strategy.earn_rate == 0.2
        assert strategy.decay_rate == 0.002
        assert strategy.reputation_threshold == 0.9
        assert strategy.max_tokens == 200.0

    def test_get_or_create_account_new(self) -> None:
        """Test creating a new account."""
        strategy = ReputationTokenStrategy()
        pubkey = "new_user"

        account = strategy._get_or_create_account(pubkey, 1000.0)

        assert account.pubkey == pubkey
        assert account.tokens == strategy.initial_tokens
        assert account.earned_total == strategy.initial_tokens
        assert account.spent_total == 0.0
        assert account.last_activity == 1000.0

    def test_get_or_create_account_existing(self) -> None:
        """Test retrieving an existing account."""
        strategy = ReputationTokenStrategy()
        pubkey = "existing_user"

        # Create account first
        account1 = strategy._get_or_create_account(pubkey, 1000.0)
        account1.tokens = 5.0

        # Retrieve same account
        account2 = strategy._get_or_create_account(pubkey, 2000.0)

        assert account1 is account2
        assert account2.tokens == 5.0

    def test_evaluate_event_new_user_sufficient_tokens(self) -> None:
        """Test evaluating event for new user with sufficient tokens."""
        strategy = ReputationTokenStrategy(initial_tokens=10.0, post_cost=1.0, reputation_threshold=0.9)

        event = NostrEvent(
            id="test_id",
            pubkey="new_user",
            created_at=1000,
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            tags=[],
            sig="test_sig",
        )

        with patch("time.time", return_value=1000.0):
            result = strategy.evaluate_event(event, 1000.0)

        assert result.allowed is True
        assert "Token payment successful" in result.reason
        assert result.metrics is not None
        assert result.metrics["tokens_remaining"] == 10.0  # Tokens not spent yet in evaluate
        assert result.metrics["bypassed_cost"] is False

    def test_evaluate_event_insufficient_tokens(self) -> None:
        """Test evaluating event with insufficient tokens."""
        strategy = ReputationTokenStrategy(initial_tokens=0.5, post_cost=1.0, reputation_threshold=0.9)

        event = NostrEvent(
            id="test_id",
            pubkey="poor_user",
            created_at=1000,
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            tags=[],
            sig="test_sig",
        )

        with patch("time.time", return_value=1000.0):
            result = strategy.evaluate_event(event, 1000.0)

        assert result.allowed is False
        assert "Insufficient tokens" in result.reason
        assert result.metrics is not None
        assert result.metrics["tokens_remaining"] == 0.5

    def test_evaluate_event_high_reputation_bypass(self) -> None:
        """Test high reputation user bypassing token cost."""
        strategy = ReputationTokenStrategy(
            initial_tokens=1.0,
            post_cost=10.0,
            reputation_threshold=0.8,
        )

        event = NostrEvent(
            id="test_id",
            pubkey="trusted_user",
            created_at=1000,
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            tags=[],
            sig="test_sig",
        )

        # Create account and boost reputation properly
        account = strategy._get_or_create_account("trusted_user", 1000.0)
        account.earned_total = 50.0  # High earned total
        account.spent_total = 10.0   # Lower spent total for good ratio
        account.last_activity = 1000.0  # Recent activity
        account.update_reputation_score(1000.0)

        with patch("time.time", return_value=1000.0):
            result = strategy.evaluate_event(event, 1000.0)

        assert result.allowed is True
        assert "High reputation user" in result.reason
        assert result.metrics is not None
        assert result.metrics["bypassed_cost"] is True

    def test_update_state_normal_user(self) -> None:
        """Test state update for normal user."""
        strategy = ReputationTokenStrategy(
            initial_tokens=10.0,
            post_cost=1.0,
            earn_rate=0.5,
            max_tokens=20.0,
        )

        event = NostrEvent(
            id="test_id",
            pubkey="normal_user",
            created_at=1000,
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            tags=[],
            sig="test_sig",
        )

        # Create account with low reputation
        account = strategy._get_or_create_account("normal_user", 1000.0)
        account.reputation_score = 0.5  # Below threshold

        strategy.update_state(event, 1000.0)

        # Should spend tokens and earn tokens
        expected_tokens = 10.0 - 1.0 + 0.5  # initial - cost + earn
        assert account.tokens == expected_tokens
        assert account.spent_total == 1.0
        assert account.earned_total == 10.0 + 0.5  # initial + earned

    def test_update_state_high_reputation_user(self) -> None:
        """Test state update for high reputation user."""
        strategy = ReputationTokenStrategy(
            initial_tokens=10.0,
            post_cost=1.0,
            earn_rate=0.5,
            reputation_threshold=0.8,
        )

        event = NostrEvent(
            id="test_id",
            pubkey="trusted_user",
            created_at=1000,
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            tags=[],
            sig="test_sig",
        )

        # Create account with high reputation
        account = strategy._get_or_create_account("trusted_user", 1000.0)
        account.reputation_score = 0.9  # Above threshold

        strategy.update_state(event, 1000.0)

        # Should not spend tokens but still earn
        expected_tokens = 10.0 + 0.5  # initial + earn (no cost)
        assert account.tokens == expected_tokens
        assert account.spent_total == 0.0
        assert account.earned_total == 10.0 + 0.5

    def test_update_state_max_tokens_cap(self) -> None:
        """Test that tokens are capped at maximum."""
        strategy = ReputationTokenStrategy(
            initial_tokens=10.0,
            post_cost=1.0,
            earn_rate=5.0,
            max_tokens=12.0,
        )

        event = NostrEvent(
            id="test_id",
            pubkey="user",
            created_at=1000,
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            tags=[],
            sig="test_sig",
        )

        # Create account with high reputation to avoid spending
        account = strategy._get_or_create_account("user", 1000.0)
        account.reputation_score = 0.9

        strategy.update_state(event, 1000.0)

        # Should be capped at max_tokens
        assert account.tokens == 12.0

    def test_get_account_info_existing(self) -> None:
        """Test getting account info for existing user."""
        strategy = ReputationTokenStrategy()
        pubkey = "existing_user"

        # Create account
        account = strategy._get_or_create_account(pubkey, 1000.0)
        account.tokens = 5.0
        account.reputation_score = 0.7

        info = strategy.get_account_info(pubkey)

        assert info is not None
        assert info["pubkey"] == pubkey
        assert info["tokens"] == 5.0
        assert info["reputation_score"] == 0.7
        assert info["earned_total"] == 10.0
        assert info["spent_total"] == 0.0

    def test_get_account_info_nonexistent(self) -> None:
        """Test getting account info for non-existent user."""
        strategy = ReputationTokenStrategy()

        info = strategy.get_account_info("nonexistent_user")

        assert info is None

    def test_add_tokens_success(self) -> None:
        """Test manually adding tokens to an account."""
        strategy = ReputationTokenStrategy(max_tokens=20.0)
        pubkey = "user"

        result = strategy.add_tokens(pubkey, 5.0, 1000.0)

        assert result is True
        account = strategy._get_or_create_account(pubkey, 1000.0)
        expected_tokens = 10.0 + 5.0  # initial + added
        assert account.tokens == expected_tokens

    def test_add_tokens_with_cap(self) -> None:
        """Test adding tokens with maximum cap."""
        strategy = ReputationTokenStrategy(initial_tokens=18.0, max_tokens=20.0)
        pubkey = "user"

        result = strategy.add_tokens(pubkey, 5.0, 1000.0)

        assert result is True
        account = strategy._get_or_create_account(pubkey, 1000.0)
        assert account.tokens == 20.0  # Capped at max

    def test_add_tokens_invalid_amount(self) -> None:
        """Test adding invalid token amount."""
        strategy = ReputationTokenStrategy()

        result = strategy.add_tokens("user", -5.0, 1000.0)
        assert result is False

        result = strategy.add_tokens("user", 0.0, 1000.0)
        assert result is False

    def test_penalize_user_success(self) -> None:
        """Test penalizing a user."""
        strategy = ReputationTokenStrategy()
        pubkey = "bad_user"

        # Create account with some tokens and reputation
        account = strategy._get_or_create_account(pubkey, 1000.0)
        account.tokens = 8.0
        account.reputation_score = 0.7

        result = strategy.penalize_user(pubkey, 3.0)

        assert result is True
        assert account.tokens == 5.0
        assert account.reputation_score == 0.6  # Reduced by 0.1

    def test_penalize_user_nonexistent(self) -> None:
        """Test penalizing a non-existent user."""
        strategy = ReputationTokenStrategy()

        result = strategy.penalize_user("nonexistent", 3.0)

        assert result is False

    def test_penalize_user_invalid_penalty(self) -> None:
        """Test penalizing with invalid penalty amount."""
        strategy = ReputationTokenStrategy()
        pubkey = "user"

        # Create account
        strategy._get_or_create_account(pubkey, 1000.0)

        result = strategy.penalize_user(pubkey, -1.0)
        assert result is False

        result = strategy.penalize_user(pubkey, 0.0)
        assert result is False

    def test_get_token_distribution(self) -> None:
        """Test getting token distribution across users."""
        strategy = ReputationTokenStrategy()

        # Create accounts with different token amounts
        users = [
            ("user1", 0.5),
            ("user2", 3.0),
            ("user3", 8.0),
            ("user4", 15.0),
            ("user5", 30.0),
            ("user6", 75.0),
        ]

        for pubkey, tokens in users:
            account = strategy._get_or_create_account(pubkey, 1000.0)
            account.tokens = tokens

        distribution = strategy.get_token_distribution()

        assert distribution["0-1"] == 1  # user1
        assert distribution["1-5"] == 1  # user2
        assert distribution["5-10"] == 1  # user3
        assert distribution["10-25"] == 1  # user4
        assert distribution["25-50"] == 1  # user5
        assert distribution["50+"] == 1  # user6


class TestReputationTokenRenewal:
    """Test ReputationTokenRenewal class."""

    def test_init(self) -> None:
        """Test renewal strategy initialization."""
        base_strategy = ReputationTokenStrategy()
        renewal = ReputationTokenRenewal(
            base_strategy=base_strategy,
            renewal_rate=1.0,
            renewal_interval=1800.0,
        )

        assert renewal.name == "reputation_tokens_with_renewal"
        assert renewal.base_strategy is base_strategy
        assert renewal.renewal_rate == 1.0
        assert renewal.renewal_interval == 1800.0

    def test_evaluate_event_no_renewal_needed(self) -> None:
        """Test evaluation when no renewal is needed."""
        base_strategy = ReputationTokenStrategy(reputation_threshold=0.9)
        renewal = ReputationTokenRenewal(base_strategy, renewal_rate=1.0, renewal_interval=3600.0)

        event = NostrEvent(
            id="test_id",
            pubkey="user",
            created_at=1000,
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            tags=[],
            sig="test_sig",
        )

        with patch("time.time", return_value=1000.0):
            result = renewal.evaluate_event(event, 1000.0)

        assert result.allowed is True
        assert "Token payment successful" in result.reason

    def test_evaluate_event_with_renewal(self) -> None:
        """Test evaluation with token renewal."""
        base_strategy = ReputationTokenStrategy(
            initial_tokens=2.0,
            post_cost=1.0,
            reputation_threshold=0.9,
            decay_rate=0.0  # Disable decay for this test
        )
        renewal = ReputationTokenRenewal(
            base_strategy,
            renewal_rate=2.0,
            renewal_interval=3600.0,
        )

        event = NostrEvent(
            id="test_id",
            pubkey="user",
            created_at=1000,
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            tags=[],
            sig="test_sig",
        )

        # Set up user with low tokens but eligible for renewal
        account = base_strategy._get_or_create_account("user", 1000.0)
        account.tokens = 0.5  # Insufficient for post
        renewal._last_renewal["user"] = 1000.0 - 3600.0  # 1 hour ago

        with patch("time.time", return_value=1000.0):
            result = renewal.evaluate_event(event, 4600.0)  # Current time allows renewal

        # Should have been renewed and now allowed
        assert result.allowed is True
        assert account.tokens >= 1.0  # Should have enough after renewal

    def test_update_state(self) -> None:
        """Test state update with renewal tracking."""
        base_strategy = ReputationTokenStrategy()
        renewal = ReputationTokenRenewal(base_strategy)

        event = NostrEvent(
            id="test_id",
            pubkey="user",
            created_at=1000,
            kind=NostrEventKind.TEXT_NOTE,
            content="test content",
            tags=[],
            sig="test_sig",
        )

        renewal.update_state(event, 1000.0)

        assert renewal._last_renewal["user"] == 1000.0

    def test_apply_renewal_initial(self) -> None:
        """Test initial renewal application."""
        base_strategy = ReputationTokenStrategy()
        renewal = ReputationTokenRenewal(base_strategy)

        renewal._apply_renewal("new_user", 1000.0)

        assert renewal._last_renewal["new_user"] == 1000.0

    def test_apply_renewal_multiple_cycles(self) -> None:
        """Test renewal with multiple cycles."""
        base_strategy = ReputationTokenStrategy(max_tokens=50.0)
        renewal = ReputationTokenRenewal(
            base_strategy,
            renewal_rate=2.0,
            renewal_interval=3600.0,
        )

        pubkey = "user"
        account = base_strategy._get_or_create_account(pubkey, 1000.0)
        initial_tokens = account.tokens

        # Set last renewal to 2.5 hours ago (2 complete cycles)
        renewal._last_renewal[pubkey] = 1000.0 - (2.5 * 3600.0)

        renewal._apply_renewal(pubkey, 1000.0)

        # Should have added 2 * 2.0 = 4.0 tokens (2 complete cycles)
        expected_tokens = min(initial_tokens + 4.0, base_strategy.max_tokens)
        assert account.tokens == expected_tokens

    def test_get_metrics_combined(self) -> None:
        """Test getting combined metrics from both strategies."""
        base_strategy = ReputationTokenStrategy()
        renewal = ReputationTokenRenewal(base_strategy)

        # Add some metrics to both strategies
        base_strategy._metrics["base_metric"] = "base_value"
        renewal._metrics["renewal_metric"] = "renewal_value"

        metrics = renewal.get_metrics()

        assert "base_metric" in metrics
        assert "renewal_metric" in metrics
        assert metrics["base_metric"] == "base_value"
        assert metrics["renewal_metric"] == "renewal_value"
