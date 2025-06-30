"""Web of Trust anti-spam strategy implementation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..protocol.events import NostrEvent, NostrEventKind
from .base import AntiSpamStrategy, StrategyResult


class TrustLevel(Enum):
    """Trust levels for easier interpretation."""

    UNTRUSTED = 0.0
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9
    ABSOLUTE = 1.0


@dataclass
class TrustNode:
    """Represents a node in the trust graph."""

    pubkey: str
    trust_score: float = 0.0
    trusted_by: set[str] = field(default_factory=set)
    trusts: set[str] = field(default_factory=set)
    _trust_scores_from: dict[str, tuple[float, float]] = field(default_factory=dict)  # pubkey -> (score, timestamp)
    _trust_scores_for: dict[str, tuple[float, float]] = field(default_factory=dict)  # pubkey -> (score, timestamp)

    def add_trusted_by(self, pubkey: str, score: float, timestamp: float = 0.0) -> None:
        """Add a pubkey that trusts this node."""
        self.trusted_by.add(pubkey)
        self._trust_scores_from[pubkey] = (score, timestamp)

    def add_trusts(self, pubkey: str, score: float, timestamp: float = 0.0) -> None:
        """Add a pubkey that this node trusts."""
        self.trusts.add(pubkey)
        self._trust_scores_for[pubkey] = (score, timestamp)

    def get_trust_score_from(self, pubkey: str) -> float:
        """Get trust score from a specific pubkey."""
        return self._trust_scores_from.get(pubkey, (0.0, 0.0))[0]

    def get_trust_score_for(self, pubkey: str) -> float:
        """Get trust score for a specific pubkey."""
        return self._trust_scores_for.get(pubkey, (0.0, 0.0))[0]

    def get_trust_timestamp_from(self, pubkey: str) -> float:
        """Get timestamp of trust relationship from a specific pubkey."""
        return self._trust_scores_from.get(pubkey, (0.0, 0.0))[1]

    def get_trust_timestamp_for(self, pubkey: str) -> float:
        """Get timestamp of trust relationship for a specific pubkey."""
        return self._trust_scores_for.get(pubkey, (0.0, 0.0))[1]


class WebOfTrustStrategy(AntiSpamStrategy):
    """Web of Trust anti-spam strategy.

    This strategy builds a trust graph from contact list events and evaluates
    events based on the trust score of their authors. Trust propagates through
    the network with decay, and trust relationships can decay over time.
    """

    def __init__(
        self,
        min_trust_score: float = 0.5,
        trust_decay_factor: float = 0.99,
        max_trust_depth: int = 3,
        bootstrapped_trusted_keys: set[str] | None = None,
        trust_propagation_factor: float = 0.8,
    ) -> None:
        """Initialize the Web of Trust strategy.

        Args:
            min_trust_score: Minimum trust score required to allow an event.
            trust_decay_factor: Factor by which trust decays over time (per time unit).
            max_trust_depth: Maximum depth for transitive trust calculation.
            bootstrapped_trusted_keys: Initial set of trusted public keys.
            trust_propagation_factor: Factor by which trust propagates through the network.
        """
        super().__init__("web_of_trust")

        self.min_trust_score = min_trust_score
        self.trust_decay_factor = trust_decay_factor
        self.max_trust_depth = max_trust_depth
        self.bootstrapped_trusted_keys = bootstrapped_trusted_keys or set()
        self.trust_propagation_factor = trust_propagation_factor

        # Trust graph: pubkey -> TrustNode
        self._trust_graph: dict[str, TrustNode] = {}

        # Initialize bootstrapped trusted keys
        for pubkey in self.bootstrapped_trusted_keys:
            self._trust_graph[pubkey] = TrustNode(pubkey, 1.0)

        # Metrics
        self._metrics = {
            "total_evaluations": 0,
            "allowed_events": 0,
            "rejected_events": 0,
            "trust_graph_size": 0,
            "bootstrapped_keys_count": len(self.bootstrapped_trusted_keys),
        }

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate if an event should be allowed based on Web of Trust.

        Args:
            event: The event to evaluate.
            current_time: Current simulation time.

        Returns:
            StrategyResult indicating if the event is allowed and why.
        """
        start_time = current_time

        self._metrics["total_evaluations"] += 1

        # Check if event is from a bootstrapped trusted key
        if event.pubkey in self.bootstrapped_trusted_keys:
            self._metrics["allowed_events"] += 1
            return StrategyResult(
                allowed=True,
                reason="Event from bootstrapped trusted key",
                metrics={
                    "trust_score": 1.0,
                    "trust_source": "bootstrapped",
                    "trust_depth": 0,
                },
                computational_cost=current_time - start_time,
            )

        # Calculate trust score for the event author
        trust_score = self._calculate_trust_score(event.pubkey, current_time)

        # Update metrics
        self._metrics["trust_graph_size"] = len(self._trust_graph)

        # Determine if event should be allowed
        allowed = trust_score >= self.min_trust_score

        if allowed:
            self._metrics["allowed_events"] += 1
            reason = f"Sufficient trust score: {trust_score:.3f}"
        else:
            self._metrics["rejected_events"] += 1
            reason = f"Insufficient trust score: {trust_score:.3f} < {self.min_trust_score}"

        return StrategyResult(
            allowed=allowed,
            reason=reason,
            metrics={
                "trust_score": trust_score,
                "trust_source": "calculated",
                "min_required": self.min_trust_score,
            },
            computational_cost=current_time - start_time,
        )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update internal state after processing an event.

        For contact list events (kind 3), extract trust relationships and
        update the trust graph.

        Args:
            event: The processed event.
            current_time: Current simulation time.
        """
        # Process contact list events to build trust graph
        if event.kind == NostrEventKind.CONTACTS:
            self._process_contact_list(event, current_time)

    def _process_contact_list(self, event: NostrEvent, current_time: float) -> None:
        """Process a contact list event to extract trust relationships.

        Args:
            event: Contact list event.
            current_time: Current simulation time.
        """
        # Ensure the author exists in the trust graph
        if event.pubkey not in self._trust_graph:
            self._trust_graph[event.pubkey] = TrustNode(event.pubkey)

        # Extract 'p' tags which represent followed pubkeys
        for tag in event.tags:
            if tag.name == "p" and tag.values:
                followed_pubkey = tag.values[0]

                # Default trust score for followed users
                trust_score = 0.7  # Medium-high trust for followed users

                # Check if there's a relay URL or other metadata that might indicate trust level
                if len(tag.values) > 1:
                    # Could parse relay URL or trust level from metadata
                    pass

                self._add_trust_relationship(
                    event.pubkey, followed_pubkey, trust_score, current_time
                )

    def _add_trust_relationship(
        self, truster: str, trusted: str, score: float, timestamp: float
    ) -> None:
        """Add a trust relationship between two pubkeys.

        Args:
            truster: Public key of the entity giving trust.
            trusted: Public key of the entity receiving trust.
            score: Trust score (0.0 to 1.0).
            timestamp: Timestamp of the trust relationship.
        """
        # Ensure both nodes exist in the graph
        if truster not in self._trust_graph:
            self._trust_graph[truster] = TrustNode(truster)
        if trusted not in self._trust_graph:
            self._trust_graph[trusted] = TrustNode(trusted)

        # Add the trust relationship
        self._trust_graph[truster].add_trusts(trusted, score, timestamp)
        self._trust_graph[trusted].add_trusted_by(truster, score, timestamp)

    def _calculate_trust_score(self, pubkey: str, current_time: float) -> float:
        """Calculate trust score for a pubkey using breadth-first search.

        Args:
            pubkey: Public key to calculate trust for.
            current_time: Current simulation time for decay calculation.

        Returns:
            Trust score between 0.0 and 1.0.
        """
        if pubkey in self.bootstrapped_trusted_keys:
            return 1.0

        if pubkey not in self._trust_graph:
            return 0.0

        # Use breadth-first search to find trust paths
        visited = set()
        queue = [(pubkey, 1.0, 0)]  # (pubkey, current_score, depth)
        max_trust_score = 0.0

        while queue:
            current_pubkey, current_score, depth = queue.pop(0)

            if current_pubkey in visited or depth > self.max_trust_depth:
                continue

            visited.add(current_pubkey)

            # If this is a bootstrapped trusted key, we found a trust path
            if current_pubkey in self.bootstrapped_trusted_keys and depth > 0:
                max_trust_score = max(max_trust_score, current_score)
                continue

            # If this pubkey is in our trust graph, explore its trusted-by relationships
            if current_pubkey in self._trust_graph:
                node = self._trust_graph[current_pubkey]

                for trusted_by_pubkey in node.trusted_by:
                    if trusted_by_pubkey not in visited:
                        # Get trust score and apply decay
                        base_score = node.get_trust_score_from(trusted_by_pubkey)
                        trust_timestamp = node.get_trust_timestamp_from(trusted_by_pubkey)

                        # Apply time-based decay
                        time_elapsed = current_time - trust_timestamp
                        decayed_score = base_score * (self.trust_decay_factor ** time_elapsed)

                        # For direct trust (depth 0), don't apply propagation factor
                        if depth == 0:
                            propagated_score = decayed_score
                        else:
                            # Apply propagation factor for transitive trust
                            propagated_score = current_score * decayed_score * self.trust_propagation_factor

                        if propagated_score > 0.01:  # Avoid exploring very low trust paths
                            queue.append((trusted_by_pubkey, propagated_score, depth + 1))

        return min(max_trust_score, 1.0)

    def get_trust_graph_stats(self) -> dict[str, Any]:
        """Get statistics about the trust graph.

        Returns:
            Dictionary with trust graph statistics.
        """
        if not self._trust_graph:
            return {
                "total_nodes": 0,
                "total_edges": 0,
                "bootstrapped_nodes": len(self.bootstrapped_trusted_keys),
                "average_trust_score": 0.0,
                "max_trust_score": 0.0,
            }

        total_edges = sum(len(node.trusts) for node in self._trust_graph.values())
        trust_scores = [node.trust_score for node in self._trust_graph.values()]

        return {
            "total_nodes": len(self._trust_graph),
            "total_edges": total_edges,
            "bootstrapped_nodes": len(self.bootstrapped_trusted_keys),
            "average_trust_score": sum(trust_scores) / len(trust_scores) if trust_scores else 0.0,
            "max_trust_score": max(trust_scores) if trust_scores else 0.0,
        }

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._metrics = {
            "total_evaluations": 0,
            "allowed_events": 0,
            "rejected_events": 0,
            "trust_graph_size": 0,
            "bootstrapped_keys_count": len(self.bootstrapped_trusted_keys),
        }
