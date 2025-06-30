"""Local reputation tokens anti-spam strategy."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from ..protocol.events import NostrEvent
from .base import AntiSpamStrategy, StrategyResult


@dataclass
class ReputationAccount:
    """Reputation account for a user."""

    pubkey: str
    tokens: float
    earned_total: float
    spent_total: float
    last_activity: float
    last_decay: float
    reputation_score: float = 0.0

    def can_spend(self, amount: float) -> bool:
        """Check if account has enough tokens to spend.

        Args:
            amount: Amount of tokens to spend.

        Returns:
            True if account has sufficient tokens.
        """
        return self.tokens >= amount

    def spend_tokens(self, amount: float) -> bool:
        """Spend tokens from the account.

        Args:
            amount: Amount of tokens to spend.

        Returns:
            True if tokens were spent successfully.
        """
        if self.can_spend(amount):
            self.tokens -= amount
            self.spent_total += amount
            return True
        return False

    def earn_tokens(self, amount: float, current_time: float) -> None:
        """Earn tokens for the account.

        Args:
            amount: Amount of tokens to earn.
            current_time: Current simulation time.
        """
        self.tokens += amount
        self.earned_total += amount
        self.last_activity = current_time

    def apply_decay(self, decay_rate: float, current_time: float) -> None:
        """Apply token decay to the account.

        Args:
            decay_rate: Rate of decay per time unit.
            current_time: Current simulation time.
        """
        if self.last_decay == 0:
            self.last_decay = current_time
            return

        elapsed = current_time - self.last_decay
        if elapsed > 0:
            decay_factor = (1 - decay_rate) ** elapsed
            self.tokens *= decay_factor
            self.last_decay = current_time

    def update_reputation_score(self, current_time: float) -> None:
        """Update reputation score based on activity.

        Args:
            current_time: Current simulation time.
        """
        # Simple reputation based on earn/spend ratio and recent activity
        if self.spent_total > 0:
            ratio = self.earned_total / self.spent_total
        else:
            # If no spending yet, start with lower base score
            ratio = 0.5 if self.earned_total <= 10.0 else 1.0  # Assume initial tokens

        # Recent activity bonus (within last 24 hours)
        time_since_activity = current_time - self.last_activity
        recency_bonus = max(0, 1 - (time_since_activity / 86400))  # 24 hours in seconds

        self.reputation_score = min(1.0, ratio * 0.7 + recency_bonus * 0.3)


class ReputationTokenStrategy(AntiSpamStrategy):
    """Local reputation token anti-spam strategy.

    Users earn tokens through positive behaviors and spend them to post.
    High-reputation users can bypass token requirements.
    """

    def __init__(
        self,
        initial_tokens: float = 10.0,
        post_cost: float = 1.0,
        earn_rate: float = 0.1,  # tokens per second for activity
        decay_rate: float = 0.001,  # daily decay rate
        reputation_threshold: float = 0.8,  # threshold to bypass token cost
        max_tokens: float = 100.0,
    ) -> None:
        """Initialize reputation token strategy.

        Args:
            initial_tokens: Tokens given to new users.
            post_cost: Token cost per event.
            earn_rate: Rate at which tokens are earned for activity.
            decay_rate: Daily decay rate for unused tokens.
            reputation_threshold: Reputation score to bypass token costs.
            max_tokens: Maximum tokens a user can hold.
        """
        super().__init__("reputation_tokens")
        self.initial_tokens = initial_tokens
        self.post_cost = post_cost
        self.earn_rate = earn_rate
        self.decay_rate = decay_rate
        self.reputation_threshold = reputation_threshold
        self.max_tokens = max_tokens
        self._accounts: dict[str, ReputationAccount] = {}

    def _get_or_create_account(self, pubkey: str, current_time: float) -> ReputationAccount:
        """Get or create reputation account for a user.

        Args:
            pubkey: Public key of the user.
            current_time: Current simulation time.

        Returns:
            ReputationAccount for the user.
        """
        if pubkey not in self._accounts:
            self._accounts[pubkey] = ReputationAccount(
                pubkey=pubkey,
                tokens=self.initial_tokens,
                earned_total=self.initial_tokens,
                spent_total=0.0,
                last_activity=current_time,
                last_decay=current_time,
            )
        return self._accounts[pubkey]

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate event using reputation token system."""
        start_time = time.time()

        account = self._get_or_create_account(event.pubkey, current_time)

        # Apply token decay
        account.apply_decay(self.decay_rate, current_time)

        # Update reputation score
        account.update_reputation_score(current_time)

        # Check if user has high reputation to bypass token cost
        if account.reputation_score >= self.reputation_threshold:
            allowed = True
            reason = f"High reputation user (score: {account.reputation_score:.2f}) bypasses token cost"
            metrics = {
                "reputation_score": account.reputation_score,
                "tokens_remaining": account.tokens,
                "bypassed_cost": True,
            }
        else:
            # Check if user can afford the post
            if account.can_spend(self.post_cost):
                allowed = True
                reason = f"Token payment successful ({self.post_cost} tokens)"
                metrics = {
                    "reputation_score": account.reputation_score,
                    "tokens_remaining": account.tokens,
                    "bypassed_cost": False,
                }
            else:
                allowed = False
                reason = f"Insufficient tokens (has {account.tokens:.1f}, needs {self.post_cost})"
                metrics = {
                    "reputation_score": account.reputation_score,
                    "tokens_remaining": account.tokens,
                    "bypassed_cost": False,
                }

        computational_cost = time.time() - start_time

        return StrategyResult(
            allowed=allowed,
            reason=reason,
            metrics=metrics,
            computational_cost=computational_cost,
        )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update state after processing an event.

        Args:
            event: The processed event.
            current_time: Current simulation time.
        """
        account = self._get_or_create_account(event.pubkey, current_time)

        # If event was allowed, handle token spending and earning
        if account.reputation_score < self.reputation_threshold:
            # Spend tokens for the post (if user didn't bypass)
            account.spend_tokens(self.post_cost)

        # Earn tokens for activity (posting is activity)
        earn_amount = self.earn_rate
        account.earn_tokens(earn_amount, current_time)

        # Cap tokens at maximum
        account.tokens = min(account.tokens, self.max_tokens)

        # Update metrics
        self._metrics[f"account_{event.pubkey}_tokens"] = account.tokens
        self._metrics[f"account_{event.pubkey}_reputation"] = account.reputation_score
        self._metrics["total_accounts"] = len(self._accounts)
        self._metrics["average_reputation"] = sum(
            acc.reputation_score for acc in self._accounts.values()
        ) / len(self._accounts)

    def get_account_info(self, pubkey: str) -> dict[str, Any] | None:
        """Get account information for a user.

        Args:
            pubkey: Public key of the user.

        Returns:
            Account information or None if account doesn't exist.
        """
        if pubkey not in self._accounts:
            return None

        account = self._accounts[pubkey]
        return {
            "pubkey": account.pubkey,
            "tokens": account.tokens,
            "earned_total": account.earned_total,
            "spent_total": account.spent_total,
            "reputation_score": account.reputation_score,
            "last_activity": account.last_activity,
        }

    def add_tokens(self, pubkey: str, amount: float, current_time: float) -> bool:
        """Manually add tokens to a user's account (for testing or rewards).

        Args:
            pubkey: Public key of the user.
            amount: Amount of tokens to add.
            current_time: Current simulation time.

        Returns:
            True if tokens were added successfully.
        """
        if amount <= 0:
            return False

        account = self._get_or_create_account(pubkey, current_time)
        account.earn_tokens(amount, current_time)
        account.tokens = min(account.tokens, self.max_tokens)
        return True

    def penalize_user(self, pubkey: str, penalty: float) -> bool:
        """Penalize a user by reducing their tokens and reputation.

        Args:
            pubkey: Public key of the user.
            penalty: Penalty amount (tokens to remove).

        Returns:
            True if penalty was applied successfully.
        """
        if pubkey not in self._accounts or penalty <= 0:
            return False

        account = self._accounts[pubkey]
        account.tokens = max(0, account.tokens - penalty)
        account.reputation_score = max(0, account.reputation_score - 0.1)
        return True

    def get_token_distribution(self) -> dict[str, int]:
        """Get distribution of token amounts across users.

        Returns:
            Dictionary mapping token ranges to user counts.
        """
        distribution = {
            "0-1": 0,
            "1-5": 0,
            "5-10": 0,
            "10-25": 0,
            "25-50": 0,
            "50+": 0,
        }

        for account in self._accounts.values():
            tokens = account.tokens
            if tokens <= 1:
                distribution["0-1"] += 1
            elif tokens <= 5:
                distribution["1-5"] += 1
            elif tokens <= 10:
                distribution["5-10"] += 1
            elif tokens <= 25:
                distribution["10-25"] += 1
            elif tokens <= 50:
                distribution["25-50"] += 1
            else:
                distribution["50+"] += 1

        return distribution


class ReputationTokenRenewal(AntiSpamStrategy):
    """Token renewal strategy that replenishes tokens over time."""

    def __init__(
        self,
        base_strategy: ReputationTokenStrategy,
        renewal_rate: float = 0.5,  # tokens per hour
        renewal_interval: float = 3600.0,  # seconds between renewals
    ) -> None:
        """Initialize token renewal strategy.

        Args:
            base_strategy: Base reputation token strategy to extend.
            renewal_rate: Rate of token renewal per interval.
            renewal_interval: Time between renewal cycles.
        """
        super().__init__("reputation_tokens_with_renewal")
        self.base_strategy = base_strategy
        self.renewal_rate = renewal_rate
        self.renewal_interval = renewal_interval
        self._last_renewal: dict[str, float] = {}

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate event with token renewal."""
        # First apply any pending renewals
        self._apply_renewal(event.pubkey, current_time)

        # Then evaluate using base strategy
        return self.base_strategy.evaluate_event(event, current_time)

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update state with renewal tracking."""
        self.base_strategy.update_state(event, current_time)
        self._last_renewal[event.pubkey] = current_time

    def _apply_renewal(self, pubkey: str, current_time: float) -> None:
        """Apply token renewal for a user.

        Args:
            pubkey: Public key of the user.
            current_time: Current simulation time.
        """
        if pubkey not in self._last_renewal:
            self._last_renewal[pubkey] = current_time
            return

        time_since_renewal = current_time - self._last_renewal[pubkey]
        if time_since_renewal >= self.renewal_interval:
            # Calculate number of renewal cycles that have passed
            cycles = int(time_since_renewal / self.renewal_interval)
            renewal_amount = cycles * self.renewal_rate

            if renewal_amount > 0:
                self.base_strategy.add_tokens(pubkey, renewal_amount, current_time)
                self._last_renewal[pubkey] = current_time

    def get_metrics(self) -> dict[str, Any]:
        """Get combined metrics."""
        metrics = self.base_strategy.get_metrics()
        metrics.update(self._metrics)
        return metrics
