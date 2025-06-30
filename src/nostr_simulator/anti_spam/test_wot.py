"""Tests for Web of Trust anti-spam strategy."""

from __future__ import annotations

import pytest

from ..protocol.events import NostrEvent, NostrEventKind, NostrTag
from .base import StrategyResult
from .wot import WebOfTrustStrategy, TrustLevel, TrustNode


class TestTrustNode:
    """Test cases for TrustNode."""

    def test_trust_node_creation(self) -> None:
        """Test creating a trust node."""
        node = TrustNode("pubkey123", 0.8)

        assert node.pubkey == "pubkey123"
        assert node.trust_score == 0.8
        assert node.trusted_by == set()
        assert node.trusts == set()

    def test_trust_node_add_trust_relationship(self) -> None:
        """Test adding trust relationships."""
        node1 = TrustNode("pubkey1", 0.8)
        node2 = TrustNode("pubkey2", 0.7)

        node1.add_trusts(node2.pubkey, 0.9)
        node2.add_trusted_by(node1.pubkey, 0.9)

        assert node2.pubkey in node1.trusts
        assert node1.pubkey in node2.trusted_by
        assert node1.get_trust_score_for(node2.pubkey) == 0.9
        assert node2.get_trust_score_from(node1.pubkey) == 0.9

    def test_trust_node_timestamps(self) -> None:
        """Test trust node timestamp methods."""
        node1 = TrustNode("pubkey1", 0.8)
        node2 = TrustNode("pubkey2", 0.7)

        timestamp = 1234567890.0
        node1.add_trusts(node2.pubkey, 0.9, timestamp)
        node2.add_trusted_by(node1.pubkey, 0.9, timestamp)

        assert node1.get_trust_timestamp_for(node2.pubkey) == timestamp
        assert node2.get_trust_timestamp_from(node1.pubkey) == timestamp

        # Test default values for non-existent relationships
        assert node1.get_trust_timestamp_from("unknown") == 0.0
        assert node2.get_trust_timestamp_for("unknown") == 0.0


class TestWebOfTrustStrategy:
    """Test cases for WebOfTrustStrategy."""

    def test_strategy_initialization(self) -> None:
        """Test strategy initialization with default parameters."""
        strategy = WebOfTrustStrategy()

        assert strategy.name == "web_of_trust"
        assert strategy.min_trust_score == 0.5
        assert strategy.trust_decay_factor == 0.99
        assert strategy.max_trust_depth == 3
        assert strategy.bootstrapped_trusted_keys == set()

    def test_strategy_initialization_with_parameters(self) -> None:
        """Test strategy initialization with custom parameters."""
        trusted_keys = {"key1", "key2"}
        strategy = WebOfTrustStrategy(
            min_trust_score=0.7,
            trust_decay_factor=0.95,
            max_trust_depth=5,
            bootstrapped_trusted_keys=trusted_keys
        )

        assert strategy.min_trust_score == 0.7
        assert strategy.trust_decay_factor == 0.95
        assert strategy.max_trust_depth == 5
        assert strategy.bootstrapped_trusted_keys == trusted_keys

    def test_evaluate_event_from_bootstrapped_key(self) -> None:
        """Test evaluating event from a bootstrapped trusted key."""
        trusted_keys = {"trusted_key"}
        strategy = WebOfTrustStrategy(bootstrapped_trusted_keys=trusted_keys)

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello world",
            created_at=1234567890,
            pubkey="trusted_key"
        )

        result = strategy.evaluate_event(event, 1234567890.0)

        assert result.allowed is True
        assert "bootstrapped trusted key" in result.reason
        assert result.metrics is not None
        assert result.metrics["trust_score"] == 1.0

    def test_evaluate_event_from_untrusted_key_no_graph(self) -> None:
        """Test evaluating event from untrusted key with no trust graph."""
        strategy = WebOfTrustStrategy()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello world",
            created_at=1234567890,
            pubkey="unknown_key"
        )

        result = strategy.evaluate_event(event, 1234567890.0)

        assert result.allowed is False
        assert "Insufficient trust score" in result.reason
        assert result.metrics is not None
        assert result.metrics["trust_score"] == 0.0

    def test_process_contact_list_event(self) -> None:
        """Test processing a contact list event to build trust graph."""
        strategy = WebOfTrustStrategy()

        # Create a contact list event
        tags = [
            NostrTag("p", ["friend1"]),
            NostrTag("p", ["friend2"]),
        ]

        event = NostrEvent(
            kind=NostrEventKind.CONTACTS,
            content="",
            created_at=1234567890,
            pubkey="user1",
            tags=tags
        )

        strategy.update_state(event, 1234567890.0)

        # Check that trust relationships were created
        assert "user1" in strategy._trust_graph
        assert "friend1" in strategy._trust_graph
        assert "friend2" in strategy._trust_graph

        user1_node = strategy._trust_graph["user1"]
        assert "friend1" in user1_node.trusts
        assert "friend2" in user1_node.trusts

    def test_process_non_contact_list_event(self) -> None:
        """Test that update_state ignores non-contact-list events without altering the graph."""
        strategy = WebOfTrustStrategy()
        initial_size = len(strategy._trust_graph)

        # Create a non-contact list event (TEXT_NOTE)
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test content",
            created_at=1,
            pubkey="user1"
        )
        strategy.update_state(event, 1.0)

        # Graph size should remain unchanged
        assert len(strategy._trust_graph) == initial_size

    def test_calculate_trust_score_direct_trust(self) -> None:
        """Test calculating trust score with direct trust relationship."""
        trusted_keys = {"trusted_user"}
        strategy = WebOfTrustStrategy(bootstrapped_trusted_keys=trusted_keys)

        # Add direct trust relationship
        strategy._add_trust_relationship("trusted_user", "target_user", 0.8, 1234567890.0)

        score = strategy._calculate_trust_score("target_user", 1234567890.0)
        assert score == 0.8

    def test_calculate_trust_score_transitive_trust(self) -> None:
        """Test calculating trust score with transitive trust."""
        trusted_keys = {"root_user"}
        strategy = WebOfTrustStrategy(
            bootstrapped_trusted_keys=trusted_keys,
            max_trust_depth=2,
            trust_propagation_factor=0.8
        )

        # Create trust chain: root_user -> intermediate_user -> target_user
        strategy._add_trust_relationship("root_user", "intermediate_user", 0.9, 1234567890.0)
        strategy._add_trust_relationship("intermediate_user", "target_user", 0.8, 1234567890.0)

        score = strategy._calculate_trust_score("target_user", 1234567890.0)
        # Should be 0.8 (from intermediate) * 0.9 (from root) * 0.8 (propagation factor) = 0.576
        expected_score = 0.8 * 0.9 * 0.8
        assert abs(score - expected_score) < 0.01

    def test_trust_decay_over_time(self) -> None:
        """Test trust score decay over time."""
        trusted_keys = {"user1"}
        strategy = WebOfTrustStrategy(
            trust_decay_factor=0.9,
            bootstrapped_trusted_keys=trusted_keys
        )

        # Add trust at time 0
        strategy._add_trust_relationship("user1", "user2", 1.0, 0.0)

        # Check trust score after some time
        # Assuming 1 time unit passes
        score = strategy._calculate_trust_score("user2", 1.0)
        expected_score = 1.0 * (0.9 ** 1)
        assert abs(score - expected_score) < 0.01

    def test_get_metrics(self) -> None:
        """Test getting strategy metrics."""
        strategy = WebOfTrustStrategy()

        # Process some events to generate metrics
        trusted_keys = {"trusted_key"}
        strategy.bootstrapped_trusted_keys = trusted_keys

        event1 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello",
            created_at=1234567890,
            pubkey="trusted_key"
        )

        event2 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello",
            created_at=1234567890,
            pubkey="untrusted_key"
        )

        strategy.evaluate_event(event1, 1234567890.0)
        strategy.evaluate_event(event2, 1234567890.0)

        metrics = strategy.get_metrics()
        assert "total_evaluations" in metrics
        assert "allowed_events" in metrics
        assert "rejected_events" in metrics
        assert "trust_graph_size" in metrics
        assert metrics["total_evaluations"] == 2
        assert metrics["allowed_events"] == 1
        assert metrics["rejected_events"] == 1

    def test_reset_metrics(self) -> None:
        """Test resetting strategy metrics."""
        strategy = WebOfTrustStrategy()

        # Generate some metrics
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello",
            created_at=1234567890,
            pubkey="some_key"
        )

        strategy.evaluate_event(event, 1234567890.0)
        assert strategy.get_metrics()["total_evaluations"] > 0

        strategy.reset_metrics()
        metrics = strategy.get_metrics()
        assert metrics["total_evaluations"] == 0
        assert metrics["allowed_events"] == 0
        assert metrics["rejected_events"] == 0

    def test_trust_level_enum(self) -> None:
        """Test TrustLevel enum values."""
        assert TrustLevel.UNTRUSTED.value == 0.0
        assert TrustLevel.LOW.value == 0.3
        assert TrustLevel.MEDIUM.value == 0.5
        assert TrustLevel.HIGH.value == 0.7
        assert TrustLevel.VERY_HIGH.value == 0.9
        assert TrustLevel.ABSOLUTE.value == 1.0

    def test_process_contact_list_with_empty_and_invalid_tags(self) -> None:
        """Test processing contact list with empty or invalid tags."""
        strategy = WebOfTrustStrategy()

        tags = [
            NostrTag("p", []),               # Empty values
            NostrTag("e", ["not_a_pubkey"]),  # Wrong tag type
            NostrTag("p", ["valid_pubkey"]),
        ]
        event = NostrEvent(
            kind=NostrEventKind.CONTACTS,
            content="",
            created_at=2,
            pubkey="user1",
            tags=tags,
        )
        strategy.update_state(event, 2.0)

        # Only valid tag should add a trust relationship
        assert "user1" in strategy._trust_graph
        assert "valid_pubkey" in strategy._trust_graph
        assert "not_a_pubkey" not in strategy._trust_graph
        assert len(strategy._trust_graph["user1"].trusts) == 1

    def test_process_contact_list_with_metadata(self) -> None:
        """Test processing contact list with additional metadata in tags (relay URL, petname)."""
        strategy = WebOfTrustStrategy()

        tags = [
            NostrTag("p", ["friend1", "relay_url"]),
            NostrTag("p", ["friend2", "relay_url", "petname"]),
        ]
        event = NostrEvent(
            kind=NostrEventKind.CONTACTS,
            content="",
            created_at=3,
            pubkey="user1",
            tags=tags,
        )
        strategy.update_state(event, 3.0)

        user1_node = strategy._trust_graph["user1"]
        # Both friends should be in trusts with default score
        assert "friend1" in user1_node.trusts
        assert "friend2" in user1_node.trusts
        assert user1_node.get_trust_score_for("friend1") == 0.7
        assert user1_node.get_trust_score_for("friend2") == 0.7

    def test_get_trust_graph_stats_empty(self) -> None:
        """Test get_trust_graph_stats returns zeros when graph is empty."""
        strategy = WebOfTrustStrategy()
        stats = strategy.get_trust_graph_stats()

        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0
        assert stats["bootstrapped_nodes"] == 0
        assert stats["average_trust_score"] == 0.0
        assert stats["max_trust_score"] == 0.0

    def test_get_trust_graph_stats_with_data(self) -> None:
        """Test get_trust_graph_stats with populated graph."""
        trusted_keys = {"trusted_user"}
        strategy = WebOfTrustStrategy(bootstrapped_trusted_keys=trusted_keys)

        strategy._add_trust_relationship("user1", "user2", 0.8, 1.0)
        strategy._add_trust_relationship("user2", "user3", 0.6, 1.0)

        stats = strategy.get_trust_graph_stats()
        # total_nodes includes bootstrapped_user + user1 + user2 + user3
        assert stats["total_nodes"] == 4
        assert stats["total_edges"] == 2
        assert stats["bootstrapped_nodes"] == 1
        assert stats["average_trust_score"] >= 0.0
        assert stats["max_trust_score"] <= 1.0

    def test_calculate_trust_score_no_path(self) -> None:
        """Test trust score is zero when no path to bootstrapped keys exists."""
        strategy = WebOfTrustStrategy(bootstrapped_trusted_keys={"root"})
        strategy._add_trust_relationship("a", "b", 0.8, 1.0)
        strategy._add_trust_relationship("b", "c", 0.7, 1.0)
        # 'c' not connected to 'root'
        assert strategy._calculate_trust_score("c", 2.0) == 0.0

    def test_calculate_trust_score_with_cycle(self) -> None:
        """Test trust score calculation handles cycles without infinite loop."""
        strategy = WebOfTrustStrategy(bootstrapped_trusted_keys={"root"}, max_trust_depth=3)
        strategy._add_trust_relationship("root", "a", 0.9, 1.0)
        strategy._add_trust_relationship("a", "b", 0.8, 1.0)
        strategy._add_trust_relationship("b", "a", 0.7, 1.0)
        # Should compute a positive score for 'b'
        score = strategy._calculate_trust_score("b", 2.0)
        assert score > 0.0

    def test_calculate_trust_score_respects_max_depth(self) -> None:
        """Test trust score respects max_trust_depth limit."""
        strategy = WebOfTrustStrategy(bootstrapped_trusted_keys={"root"}, max_trust_depth=1)
        strategy._add_trust_relationship("root", "a", 0.9, 1.0)
        strategy._add_trust_relationship("a", "b", 0.8, 1.0)
        score_b = strategy._calculate_trust_score("b", 2.0)
        # Depth exceeded, no trust path
        assert score_b == 0.0

    def test_calculate_trust_score_filters_low_propagation(self) -> None:
        """Test very low propagated trust paths are filtered out."""
        strategy = WebOfTrustStrategy(bootstrapped_trusted_keys={"root"}, trust_propagation_factor=0.01)
        strategy._add_trust_relationship("root", "a", 0.01, 1.0)
        strategy._add_trust_relationship("a", "b", 0.01, 1.0)
        score = strategy._calculate_trust_score("b", 2.0)
        assert score == 0.0

    def test_calculate_trust_score_multiple_paths(self) -> None:
        """Test trust score chooses maximum among multiple paths."""
        strategy = WebOfTrustStrategy(bootstrapped_trusted_keys={"k1","k2"}, trust_propagation_factor=0.8)
        strategy._add_trust_relationship("k1", "target", 0.6, 1.0)
        strategy._add_trust_relationship("k2", "mid", 0.9, 1.0)
        strategy._add_trust_relationship("mid", "target", 0.8, 1.0)
        # direct:0.6, indirect:0.9*0.8*0.8=0.576 => pick 0.6
        score = strategy._calculate_trust_score("target", 2.0)
        assert abs(score - 0.6) < 0.01

    def test_evaluate_event_at_and_below_threshold(self) -> None:
        """Test evaluate_event allows exactly threshold and rejects just below (no decay)."""
        strategy = WebOfTrustStrategy(
            min_trust_score=0.5,
            trust_decay_factor=1.0,
            bootstrapped_trusted_keys={"root"},
            trust_propagation_factor=1.0,
        )
        strategy._add_trust_relationship("root", "t1", 0.5, 1.0)
        # Exactly at threshold
        event1 = NostrEvent(kind=NostrEventKind.TEXT_NOTE, content="", created_at=2, pubkey="t1")
        res1 = strategy.evaluate_event(event1, 2.0)
        assert res1.allowed is True
        strategy._add_trust_relationship("root", "t2", 0.49, 1.0)
        event2 = NostrEvent(kind=NostrEventKind.TEXT_NOTE, content="", created_at=2, pubkey="t2")
        res2 = strategy.evaluate_event(event2, 2.0)
        assert res2.allowed is False
