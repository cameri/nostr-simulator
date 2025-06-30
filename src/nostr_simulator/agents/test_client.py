"""Tests for client agent implementation."""

import time
from unittest.mock import Mock

import pytest

from ..protocol.events import NostrEvent, NostrEventKind
from ..simulation.events import Event
from .base import AgentState, AgentType
from .client import ClientAgent
from .relay import RelayFilter


class TestClientAgent:
    """Test ClientAgent functionality."""

    def test_client_initialization(self) -> None:
        """Test client agent initialization."""
        client = ClientAgent("client1")

        assert client.agent_id == "client1"
        assert client.agent_type == AgentType.CLIENT
        assert client.state == AgentState.INACTIVE
        assert len(client.connected_relays) == 0
        assert len(client.subscriptions) == 0
        assert len(client.event_queue) == 0

    def test_client_handles_event_types(self) -> None:
        """Test that client handles appropriate event types."""
        client = ClientAgent("client1")

        assert client.can_handle("relay_response")
        assert client.can_handle("event_notification")
        assert client.can_handle("subscription_eose")
        assert client.can_handle("network_event")

    def test_connect_to_relay(self) -> None:
        """Test connecting to a relay."""
        mock_engine = Mock()
        client = ClientAgent("client1", mock_engine)
        client.activate(10.0)

        # Connect to relay
        result = client.connect_to_relay("relay1")
        assert result is True
        assert "relay1" in client.connected_relays

        # Should schedule connection event
        mock_engine.schedule_event.assert_called()

    def test_connect_to_relay_while_inactive(self) -> None:
        """Test that connection fails when client is inactive."""
        client = ClientAgent("client1")
        # Don't activate the client

        result = client.connect_to_relay("relay1")
        assert result is False
        assert len(client.connected_relays) == 0

    def test_disconnect_from_relay(self) -> None:
        """Test disconnecting from a relay."""
        mock_engine = Mock()
        client = ClientAgent("client1", mock_engine)
        client.activate(10.0)

        # First connect
        client.connect_to_relay("relay1")
        assert "relay1" in client.connected_relays

        # Then disconnect
        result = client.disconnect_from_relay("relay1")
        assert result is True
        assert "relay1" not in client.connected_relays

        # Should schedule disconnection event
        assert mock_engine.schedule_event.call_count >= 2

    def test_disconnect_from_nonexistent_relay(self) -> None:
        """Test disconnecting from relay that's not connected."""
        client = ClientAgent("client1")
        client.activate(10.0)

        result = client.disconnect_from_relay("relay1")
        assert result is False

    def test_publish_event(self) -> None:
        """Test publishing an event."""
        mock_engine = Mock()
        mock_engine.current_time = 100.0

        client = ClientAgent("client1", mock_engine)
        client.activate(10.0)

        # Connect to relay first
        client.connect_to_relay("relay1")

        # Create and publish event
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello, Nostr!",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        result = client.publish_event(event, ["relay1"])
        assert result is True

        # Should schedule publication events
        mock_engine.schedule_event.assert_called()

    def test_publish_event_to_disconnected_relay(self) -> None:
        """Test publishing to a relay that's not connected."""
        mock_engine = Mock()
        client = ClientAgent("client1", mock_engine)
        client.activate(10.0)

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello, Nostr!",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        # Try to publish without connecting to relay
        result = client.publish_event(event, ["relay1"])
        assert result is False

    def test_publish_event_while_inactive(self) -> None:
        """Test that publishing fails when client is inactive."""
        client = ClientAgent("client1")
        # Don't activate the client

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello, Nostr!",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        result = client.publish_event(event, ["relay1"])
        assert result is False

    def test_subscribe_to_events(self) -> None:
        """Test subscribing to events."""
        mock_engine = Mock()
        client = ClientAgent("client1", mock_engine)
        client.activate(10.0)

        # Connect to relay first
        client.connect_to_relay("relay1")

        # Subscribe to events
        filters = [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
        subscription_id = client.subscribe_to_events("relay1", filters)

        assert subscription_id is not None
        assert subscription_id in client.subscriptions
        assert client.subscriptions[subscription_id]["relay_id"] == "relay1"
        assert client.subscriptions[subscription_id]["filters"] == filters

        # Should schedule subscription event
        mock_engine.schedule_event.assert_called()

    def test_subscribe_to_disconnected_relay(self) -> None:
        """Test subscribing to a relay that's not connected."""
        client = ClientAgent("client1")
        client.activate(10.0)

        filters = [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
        subscription_id = client.subscribe_to_events("relay1", filters)

        assert subscription_id is None

    def test_unsubscribe_from_events(self) -> None:
        """Test unsubscribing from events."""
        mock_engine = Mock()
        client = ClientAgent("client1", mock_engine)
        client.activate(10.0)

        # Connect and subscribe first
        client.connect_to_relay("relay1")
        filters = [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
        subscription_id = client.subscribe_to_events("relay1", filters)

        assert subscription_id is not None

        # Then unsubscribe
        result = client.unsubscribe_from_events(subscription_id)
        assert result is True
        assert subscription_id not in client.subscriptions

        # Should schedule unsubscription event
        assert mock_engine.schedule_event.call_count >= 3

    def test_unsubscribe_from_nonexistent_subscription(self) -> None:
        """Test unsubscribing from non-existent subscription."""
        client = ClientAgent("client1")
        client.activate(10.0)

        result = client.unsubscribe_from_events("non_existent")
        assert result is False

    def test_queue_event(self) -> None:
        """Test queuing events for processing."""
        client = ClientAgent("client1")
        client.activate(10.0)

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        client.queue_event(event)
        assert len(client.event_queue) == 1
        assert client.event_queue[0] == event

    def test_process_event_queue(self) -> None:
        """Test processing queued events."""
        client = ClientAgent("client1")
        client.activate(10.0)

        # Queue some events
        event1 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test1",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        event2 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test2",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        client.queue_event(event1)
        client.queue_event(event2)
        assert len(client.event_queue) == 2

        # Process the queue
        processed_events = client.process_event_queue()
        assert len(processed_events) == 2
        assert event1 in processed_events
        assert event2 in processed_events
        assert len(client.event_queue) == 0

    def test_client_lifecycle_callbacks(self) -> None:
        """Test client lifecycle callback methods."""
        client = ClientAgent("client1")

        # Test activation
        client.on_activate(10.0)
        # Should not raise exceptions

        # Test deactivation
        client.on_deactivate(20.0)
        # Should not raise exceptions

        # Test message received
        message = Mock()
        message.message_type = "test_message"
        client.on_message_received(message)
        # Should not raise exceptions

    def test_handle_relay_response_event(self) -> None:
        """Test handling relay response events."""
        client = ClientAgent("client1")
        client.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="relay_response",
            data={
                "relay_id": "relay1",
                "response_type": "ok",
                "event_id": "test_event_id",
                "accepted": True,
                "message": "Event accepted",
            },
        )

        result = client.on_event(event)
        assert isinstance(result, list)

    def test_handle_event_notification(self) -> None:
        """Test handling event notification from relay."""
        client = ClientAgent("client1")
        client.activate(10.0)

        nostr_event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        event = Event(
            time=10.0,
            priority=0,
            event_type="event_notification",
            data={"subscription_id": "sub1", "event": nostr_event.to_dict()},
        )

        result = client.on_event(event)
        assert isinstance(result, list)

        # Event should be queued
        assert len(client.event_queue) == 1

    def test_handle_subscription_eose(self) -> None:
        """Test handling end-of-stored-events notification."""
        client = ClientAgent("client1")
        client.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="subscription_eose",
            data={"subscription_id": "sub1"},
        )

        result = client.on_event(event)
        assert isinstance(result, list)

    def test_get_stats(self) -> None:
        """Test client statistics."""
        client = ClientAgent("client1")
        client.activate(10.0)

        # Connect to relays and create subscriptions
        client.connect_to_relay("relay1")
        client.connect_to_relay("relay2")

        filters = [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
        client.subscribe_to_events("relay1", filters)

        # Queue some events
        event1 = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="test1",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )
        client.queue_event(event1)

        stats = client.get_stats()

        assert stats["connected_relays"] == 2
        assert stats["active_subscriptions"] == 1
        assert stats["queued_events"] == 1

    def test_max_subscriptions_limit(self) -> None:
        """Test maximum subscriptions limit."""
        client = ClientAgent("client1")
        client.activate(10.0)
        client.connect_to_relay("relay1")

        # Create max allowed subscriptions
        for _ in range(client.max_subscriptions):
            filters = [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
            subscription_id = client.subscribe_to_events("relay1", filters)
            assert subscription_id is not None

        # Next subscription should fail
        filters = [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
        subscription_id = client.subscribe_to_events("relay1", filters)
        assert subscription_id is None

    def test_max_event_queue_limit(self) -> None:
        """Test maximum event queue limit."""
        client = ClientAgent("client1")
        client.activate(10.0)

        # Queue max allowed events
        for i in range(client.max_queued_events):
            event = NostrEvent(
                kind=NostrEventKind.TEXT_NOTE,
                content=f"test{i}",
                created_at=int(time.time()),
                pubkey="test_pubkey",
            )
            client.queue_event(event)

        assert len(client.event_queue) == client.max_queued_events

        # Next event should be dropped (oldest first)
        overflow_event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="overflow",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )
        client.queue_event(overflow_event)

        assert len(client.event_queue) == client.max_queued_events
        # The last event should be the overflow event
        assert client.event_queue[-1] == overflow_event

    def test_connect_to_already_connected_relay(self) -> None:
        """Test connecting to a relay that's already connected."""
        mock_engine = Mock()
        client = ClientAgent("client1", mock_engine)
        client.activate(10.0)

        # Connect once
        result1 = client.connect_to_relay("relay1")
        assert result1 is True
        assert "relay1" in client.connected_relays

        # Connect again - should return True but not duplicate
        result2 = client.connect_to_relay("relay1")
        assert result2 is True
        assert len(client.connected_relays) == 1

    def test_publish_event_to_all_relays(self) -> None:
        """Test publishing event to all connected relays when no specific relays given."""
        mock_engine = Mock()
        mock_engine.current_time = 100.0

        client = ClientAgent("client1", mock_engine)
        client.activate(10.0)

        # Connect to multiple relays
        client.connect_to_relay("relay1")
        client.connect_to_relay("relay2")

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello, Nostr!",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        # Publish without specifying target relays
        result = client.publish_event(event)
        assert result is True

        # Should schedule events for both relays
        expected_calls = 2 + 2  # 2 for connections, 2 for publishing
        assert mock_engine.schedule_event.call_count == expected_calls

    def test_client_without_simulation_engine(self) -> None:
        """Test client operations without simulation engine."""
        client = ClientAgent("client1")  # No simulation engine
        client.activate(10.0)

        # Connect to relay - should work but not schedule events
        result = client.connect_to_relay("relay1")
        assert result is True
        assert "relay1" in client.connected_relays

        # Publish event - should work but not schedule events
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello, Nostr!",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )
        result = client.publish_event(event, ["relay1"])
        assert result is True

        # Subscribe - should work but not schedule events
        filters = [RelayFilter(kinds=[NostrEventKind.TEXT_NOTE])]
        subscription_id = client.subscribe_to_events("relay1", filters)
        assert subscription_id is not None

    def test_handle_unknown_event_type(self) -> None:
        """Test handling unknown event types."""
        client = ClientAgent("client1")
        client.activate(10.0)

        event = Event(time=10.0, priority=0, event_type="unknown_event", data={})

        result = client.on_event(event)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_handle_malformed_event_notification(self) -> None:
        """Test handling malformed event notifications."""
        client = ClientAgent("client1")
        client.activate(10.0)

        # Event notification without event data
        event = Event(
            time=10.0,
            priority=0,
            event_type="event_notification",
            data={"subscription_id": "sub1"},  # No event data
        )

        result = client.on_event(event)
        assert isinstance(result, list)
        assert len(client.event_queue) == 0  # No event should be queued

    def test_handle_malformed_relay_response(self) -> None:
        """Test handling malformed relay responses."""
        client = ClientAgent("client1")
        client.activate(10.0)

        # Response with missing data
        event = Event(
            time=10.0,
            priority=0,
            event_type="relay_response",
            data={},  # Missing required fields
        )

        result = client.on_event(event)
        assert isinstance(result, list)

    def test_publish_event_with_filtered_relays(self) -> None:
        """Test publishing to specific relays, some connected and some not."""
        mock_engine = Mock()
        mock_engine.current_time = 100.0

        client = ClientAgent("client1", mock_engine)
        client.activate(10.0)

        # Connect to only one relay
        client.connect_to_relay("relay1")

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Hello, Nostr!",
            created_at=int(time.time()),
            pubkey="test_pubkey",
        )

        # Try to publish to connected and non-connected relays
        result = client.publish_event(event, ["relay1", "relay2", "relay3"])
        assert result is True

        # Should only publish to relay1 (the connected one)
        # 1 call for connection + 1 call for publishing
        assert mock_engine.schedule_event.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__])
