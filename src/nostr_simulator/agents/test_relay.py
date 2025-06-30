"""Tests for relay agent implementation."""

import time
from unittest.mock import Mock

import pytest

from ..protocol.events import NostrEvent, NostrEventKind, NostrTag
from ..simulation.events import Event
from .base import AgentState, AgentType
from .relay import RelayAgent, RelayFilter, RelayStorage


class TestRelayFilter:
    """Test RelayFilter functionality."""

    def test_filter_initialization(self) -> None:
        """Test filter initialization with various parameters."""
        # Empty filter
        filter1 = RelayFilter()
        assert filter1.ids is None
        assert filter1.authors is None
        assert filter1.kinds is None
        assert filter1.tags is None
        assert filter1.since is None
        assert filter1.until is None
        assert filter1.limit is None

        # Filter with specific parameters
        filter2 = RelayFilter(
            ids=["abc123"],
            authors=["pubkey1"],
            kinds=[NostrEventKind.TEXT_NOTE, NostrEventKind.CONTACTS],
            since=1000,
            until=2000,
            limit=10,
        )
        assert filter2.ids == ["abc123"]
        assert filter2.authors == ["pubkey1"]
        assert filter2.kinds == [1, 3]
        assert filter2.since == 1000
        assert filter2.until == 2000
        assert filter2.limit == 10

    def test_matches_empty_filter(self) -> None:
        """Test that empty filter matches all events."""
        filter_obj = RelayFilter()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        assert filter_obj.matches(event)

    def test_matches_by_id(self) -> None:
        """Test filtering by event ID."""
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        # Should match when ID is in filter
        filter_match = RelayFilter(ids=[event.id])
        assert filter_match.matches(event)

        # Should not match when ID is not in filter
        filter_no_match = RelayFilter(ids=["different_id"])
        assert not filter_no_match.matches(event)

    def test_matches_by_author(self) -> None:
        """Test filtering by author pubkey."""
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        # Should match when pubkey is in filter
        filter_match = RelayFilter(authors=["test_pubkey"])
        assert filter_match.matches(event)

        # Should not match when pubkey is not in filter
        filter_no_match = RelayFilter(authors=["different_pubkey"])
        assert not filter_no_match.matches(event)

    def test_matches_by_kind(self) -> None:
        """Test filtering by event kind."""
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        # Should match when kind is in filter
        filter_match = RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])
        assert filter_match.matches(event)

        # Should not match when kind is not in filter
        filter_no_match = RelayFilter(kinds=[NostrEventKind.SET_METADATA])
        assert not filter_no_match.matches(event)

    def test_matches_by_time_range(self) -> None:
        """Test filtering by time range."""
        current_time = int(time.time())

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=current_time,
            pubkey="test_pubkey",
        )

        # Should match when time is in range
        filter_match = RelayFilter(since=current_time - 100, until=current_time + 100)
        assert filter_match.matches(event)

        # Should not match when time is before range
        filter_before = RelayFilter(since=current_time + 100)
        assert not filter_before.matches(event)

        # Should not match when time is after range
        filter_after = RelayFilter(until=current_time - 100)
        assert not filter_after.matches(event)

    def test_matches_by_tags(self) -> None:
        """Test filtering by tags."""
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
            tags=[NostrTag("e", ["event_id"]), NostrTag("p", ["pubkey1", "pubkey2"])],
        )

        # Should match when tag exists
        filter_match = RelayFilter(tags={"e": ["event_id"]})
        assert filter_match.matches(event)

        # Should match when one of multiple tag values exists
        filter_match_multi = RelayFilter(tags={"p": ["pubkey1"]})
        assert filter_match_multi.matches(event)

        # Should not match when tag doesn't exist
        filter_no_match = RelayFilter(tags={"e": ["different_id"]})
        assert not filter_no_match.matches(event)


class TestRelayStorage:
    """Test RelayStorage functionality."""

    def test_storage_initialization(self) -> None:
        """Test storage initialization."""
        storage = RelayStorage()
        assert len(storage.events) == 0
        assert len(storage.events_by_author) == 0
        assert len(storage.events_by_kind) == 0

    def test_store_event(self) -> None:
        """Test storing an event."""
        storage = RelayStorage()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        result = storage.store_event(event)
        assert result is True
        assert event.id in storage.events
        assert storage.events[event.id] == event
        assert event.id in storage.events_by_author["test_pubkey"]
        assert event.id in storage.events_by_kind[NostrEventKind.TEXT_NOTE]

    def test_store_duplicate_event(self) -> None:
        """Test storing the same event twice."""
        storage = RelayStorage()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        # First store should succeed
        result1 = storage.store_event(event)
        assert result1 is True

        # Second store should fail (duplicate)
        result2 = storage.store_event(event)
        assert result2 is False

        # Should still only have one event
        assert len(storage.events) == 1

    def test_get_event(self) -> None:
        """Test retrieving an event by ID."""
        storage = RelayStorage()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        storage.store_event(event)

        # Should retrieve the event
        retrieved = storage.get_event(event.id)
        assert retrieved == event

        # Should return None for non-existent event
        assert storage.get_event("non_existent") is None

    def test_query_events_with_filter(self) -> None:
        """Test querying events with filters."""
        storage = RelayStorage()

        # Store multiple events
        event1 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="first",
            created_at=1000,
            pubkey="author1",
        )

        event2 = NostrEvent(
            kind=NostrEventKind.SET_METADATA,
            content="second",
            created_at=2000,
            pubkey="author2",
        )

        event3 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="third",
            created_at=3000,
            pubkey="author1",
        )

        storage.store_event(event1)
        storage.store_event(event2)
        storage.store_event(event3)

        # Query by author
        filter_author = RelayFilter(authors=["author1"])
        results = storage.query_events(filter_author)
        assert len(results) == 2
        assert event1 in results
        assert event3 in results

        # Query by kind
        filter_kind = RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])
        results = storage.query_events(filter_kind)
        assert len(results) == 2
        assert event1 in results
        assert event3 in results

        # Query with limit
        filter_limit = RelayFilter(limit=1)
        results = storage.query_events(filter_limit)
        assert len(results) == 1

    def test_delete_event(self) -> None:
        """Test deleting an event."""
        storage = RelayStorage()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        storage.store_event(event)
        assert event.id in storage.events

        # Delete the event
        result = storage.delete_event(event.id)
        assert result is True
        assert event.id not in storage.events
        # Since it was the only event for this author, the author key should be removed
        assert "test_pubkey" not in storage.events_by_author
        # Since it was the only event of this kind, the kind key should be removed
        assert NostrEventKind.TEXT_NOTE not in storage.events_by_kind

        # Try to delete non-existent event
        result = storage.delete_event("non_existent")
        assert result is False


class TestRelayAgent:
    """Test RelayAgent functionality."""

    def test_relay_initialization(self) -> None:
        """Test relay agent initialization."""
        relay = RelayAgent("relay1")

        assert relay.agent_id == "relay1"
        assert relay.agent_type == AgentType.RELAY
        assert relay.state == AgentState.INACTIVE
        assert isinstance(relay.storage, RelayStorage)
        assert len(relay.connected_clients) == 0
        assert len(relay.subscriptions) == 0

    def test_relay_handles_event_types(self) -> None:
        """Test that relay handles appropriate event types."""
        relay = RelayAgent("relay1")

        assert relay.can_handle("nostr_event")
        assert relay.can_handle("client_subscribe")
        assert relay.can_handle("client_unsubscribe")
        assert relay.can_handle("relay_sync")

    def test_accept_event(self) -> None:
        """Test accepting and storing a Nostr event."""
        relay = RelayAgent("relay1")
        relay.activate(10.0)

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test message",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        result = relay.accept_event(event)
        assert result is True

        # Event should be stored
        stored_event = relay.storage.get_event(event.id)
        assert stored_event == event

    def test_accept_duplicate_event(self) -> None:
        """Test rejecting duplicate events."""
        relay = RelayAgent("relay1")
        relay.activate(10.0)

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test message",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        # First acceptance should succeed
        result1 = relay.accept_event(event)
        assert result1 is True

        # Second acceptance should fail
        result2 = relay.accept_event(event)
        assert result2 is False

    def test_accept_event_while_inactive(self) -> None:
        """Test rejecting events when relay is inactive."""
        relay = RelayAgent("relay1")
        # Don't activate the relay

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test message",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        result = relay.accept_event(event)
        assert result is False

    def test_relay_lifecycle_callbacks(self) -> None:
        """Test relay lifecycle callback methods."""
        relay = RelayAgent("relay1")

        # Test activation
        relay.on_activate(10.0)
        # Should not raise exceptions

        # Test deactivation
        relay.on_deactivate(20.0)
        # Should not raise exceptions

        # Test message received
        message = Mock()
        message.message_type = "test_message"
        relay.on_message_received(message)
        # Should not raise exceptions

    def test_relay_event_handling(self) -> None:
        """Test relay event handling methods."""
        mock_engine = Mock()
        relay = RelayAgent("relay1", mock_engine)
        relay.activate(10.0)

        # Test nostr_event handling
        nostr_event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        event = Event(
            time=10.0,
            priority=0,
            event_type="nostr_event",
            data={"nostr_event": nostr_event},
        )

        result = relay.on_event(event)
        assert isinstance(result, list)

    def test_relay_subscription_limits(self) -> None:
        """Test relay subscription and filter limits."""
        relay = RelayAgent("relay1")
        relay.activate(10.0)

        # Test max subscriptions per client
        client_id = "client1"

        # Create max allowed subscriptions
        for i in range(relay.max_subscriptions_per_client):
            result = relay.subscribe_client(
                client_id, f"sub{i}", [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
            )
            assert result is True

        # Next subscription should fail
        result = relay.subscribe_client(
            client_id, "sub_overflow", [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
        )
        assert result is False

    def test_relay_filter_limits(self) -> None:
        """Test relay filter limits per subscription."""
        relay = RelayAgent("relay1")
        relay.activate(10.0)

        # Create too many filters
        too_many_filters = [
            RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])
            for _ in range(relay.max_filters_per_subscription + 1)
        ]

        result = relay.subscribe_client("client1", "sub1", too_many_filters)
        assert result is False

    def test_relay_subscription_while_inactive(self) -> None:
        """Test that subscriptions fail when relay is inactive."""
        relay = RelayAgent("relay1")
        # Don't activate the relay

        result = relay.subscribe_client(
            "client1", "sub1", [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
        )
        assert result is False

    def test_unsubscribe_nonexistent(self) -> None:
        """Test unsubscribing from non-existent subscription."""
        relay = RelayAgent("relay1")
        relay.activate(10.0)

        result = relay.unsubscribe_client("non_existent_sub")
        assert result is False

    def test_get_stats(self) -> None:
        """Test relay statistics."""
        relay = RelayAgent("relay1")
        relay.activate(10.0)

        # Add some events and subscriptions
        event1 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test1",
            created_at=int(time.time()),
            pubkey="author1",
        )

        event2 = NostrEvent(
            kind=NostrEventKind.SET_METADATA,
            content="test2",
            created_at=int(time.time()),
            pubkey="author2",
        )

        relay.accept_event(event1)
        relay.accept_event(event2)

        relay.subscribe_client(
            "client1", "sub1", [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
        )

        stats = relay.get_stats()

        assert stats["total_events"] == 2
        assert stats["connected_clients"] == 1
        assert stats["active_subscriptions"] == 1
        assert "events_by_kind" in stats
        assert stats["events_by_kind"]["TEXT_NOTE"] == 1
        assert stats["events_by_kind"]["SET_METADATA"] == 1

    def test_handle_client_subscribe_event(self) -> None:
        """Test handling client subscribe simulation events."""
        relay = RelayAgent("relay1")
        relay.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="client_subscribe",
            data={
                "client_id": "client1",
                "subscription_id": "sub1",
                "filters": [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])],
            },
        )

        result = relay.on_event(event)
        assert isinstance(result, list)
        assert "sub1" in relay.subscriptions

    def test_handle_client_unsubscribe_event(self) -> None:
        """Test handling client unsubscribe simulation events."""
        relay = RelayAgent("relay1")
        relay.activate(10.0)

        # First subscribe
        relay.subscribe_client(
            "client1", "sub1", [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
        )

        # Then unsubscribe
        event = Event(
            time=10.0,
            priority=0,
            event_type="client_unsubscribe",
            data={"subscription_id": "sub1"},
        )

        result = relay.on_event(event)
        assert isinstance(result, list)
        assert "sub1" not in relay.subscriptions

    def test_handle_relay_sync_event(self) -> None:
        """Test handling relay sync simulation events."""
        relay = RelayAgent("relay1")
        relay.activate(10.0)

        event = Event(time=10.0, priority=0, event_type="relay_sync", data={})

        result = relay.on_event(event)
        assert isinstance(result, list)

    def test_handle_unknown_event_type(self) -> None:
        """Test handling unknown event types."""
        relay = RelayAgent("relay1")
        relay.activate(10.0)

        event = Event(time=10.0, priority=0, event_type="unknown_event", data={})

        result = relay.on_event(event)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_handle_malformed_events(self) -> None:
        """Test handling malformed simulation events."""
        relay = RelayAgent("relay1")
        relay.activate(10.0)

        # Event without required data
        event1 = Event(time=10.0, priority=0, event_type="client_subscribe", data={})

        result1 = relay.on_event(event1)
        assert isinstance(result1, list)

        # Event with partial data
        event2 = Event(
            time=10.0,
            priority=0,
            event_type="client_subscribe",
            data={"client_id": "client1"},
        )

        result2 = relay.on_event(event2)
        assert isinstance(result2, list)

    def test_event_broadcast_with_no_subscribers(self) -> None:
        """Test event broadcasting when no clients are subscribed."""
        mock_engine = Mock()
        relay = RelayAgent("relay1", mock_engine)
        relay.activate(10.0)

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        # No subscriptions, should still accept event
        result = relay.accept_event(event)
        assert result is True

        # Should not schedule any delivery events
        mock_engine.schedule_event.assert_not_called()

    def test_event_broadcast_with_non_matching_subscribers(self) -> None:
        """Test event broadcasting when no subscriptions match."""
        mock_engine = Mock()
        relay = RelayAgent("relay1", mock_engine)
        relay.activate(10.0)

        # Subscribe to metadata events only
        relay.subscribe_client(
            "client1", "sub1", [RelayFilter(kinds=[NostrEventKind.SET_METADATA])]
        )

        # Send a text note (different kind)
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        relay.accept_event(event)

        # Should not schedule delivery since filter doesn't match
        mock_engine.schedule_event.assert_not_called()

    def test_send_event_without_simulation_engine(self) -> None:
        """Test sending event to client when no simulation engine is available."""
        relay = RelayAgent("relay1")  # No simulation engine
        relay.activate(10.0)

        # Subscribe a client
        relay.subscribe_client(
            "client1", "sub1", [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
        )

        # Accept matching event - should not crash
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        result = relay.accept_event(event)
        assert result is True

    def test_inactive_subscription_filtering(self) -> None:
        """Test that inactive subscriptions don't receive events."""
        mock_engine = Mock()
        relay = RelayAgent("relay1", mock_engine)
        relay.activate(10.0)

        # Subscribe a client
        relay.subscribe_client(
            "client1", "sub1", [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
        )

        # Manually mark subscription as inactive
        relay.subscriptions["sub1"]["active"] = False

        # Accept matching event
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        relay.accept_event(event)

        # Should not schedule delivery to inactive subscription
        mock_engine.schedule_event.assert_not_called()

    def test_handle_nostr_event_without_event_data(self) -> None:
        """Test handling nostr_event without actual event in data."""
        relay = RelayAgent("relay1")
        relay.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="nostr_event",
            data={},  # No nostr_event in data
        )

        result = relay.on_event(event)
        assert isinstance(result, list)
        assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__])
