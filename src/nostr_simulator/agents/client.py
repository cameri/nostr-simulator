"""Client agent implementation for Nostr simulation."""

from __future__ import annotations

import uuid
from typing import Any

from ..protocol.events import NostrEvent
from ..simulation.events import Event
from .base import AgentType, BaseAgent
from .relay import RelayFilter


class ClientAgent(BaseAgent):
    """Client agent that connects to relays and publishes/subscribes to events."""

    def __init__(self, agent_id: str, simulation_engine: Any = None) -> None:
        """Initialize the client agent.

        Args:
            agent_id: Unique identifier for the client.
            simulation_engine: Reference to the simulation engine.
        """
        super().__init__(agent_id, AgentType.CLIENT, simulation_engine)

        # Connection management
        self.connected_relays: set[str] = set()

        # Subscription management
        self.subscriptions: dict[str, dict[str, Any]] = {}
        self.max_subscriptions = 20

        # Event processing
        self.event_queue: list[NostrEvent] = []
        self.max_queued_events = 1000

        # Event handling configuration
        self.handled_event_types = {
            "relay_response",
            "event_notification",
            "subscription_eose",
            "network_event",
        }

        self.logger.info(f"Initialized client {agent_id}")

    def on_activate(self, current_time: float) -> None:
        """Called when the client is activated."""
        self.logger.info(f"Client {self.agent_id} is now active")

    def on_deactivate(self, current_time: float) -> None:
        """Called when the client is deactivated."""
        self.logger.info(f"Client {self.agent_id} is now inactive")

    def on_message_received(self, message: Any) -> None:
        """Process incoming messages."""
        self.logger.debug(f"Received message: {message.message_type}")

    def on_event(self, event: Event) -> list[Event]:
        """Handle simulation events."""
        events_generated = []

        if event.event_type == "relay_response":
            events_generated.extend(self._handle_relay_response(event))
        elif event.event_type == "event_notification":
            events_generated.extend(self._handle_event_notification(event))
        elif event.event_type == "subscription_eose":
            events_generated.extend(self._handle_subscription_eose(event))
        elif event.event_type == "network_event":
            events_generated.extend(self._handle_network_event(event))

        return events_generated

    def connect_to_relay(self, relay_id: str) -> bool:
        """Connect to a relay.

        Args:
            relay_id: ID of the relay to connect to.

        Returns:
            True if connection was successful.
        """
        if not self.is_active():
            self.logger.warning("Cannot connect to relay while client is inactive")
            return False

        if relay_id in self.connected_relays:
            self.logger.debug(f"Already connected to relay {relay_id}")
            return True

        # Add to connected relays
        self.connected_relays.add(relay_id)

        # Schedule connection event
        if self.simulation_engine:
            connection_event = Event(
                time=self.simulation_engine.current_time,
                priority=1,
                event_type="client_connection",
                data={
                    "client_id": self.agent_id,
                    "relay_id": relay_id,
                    "action": "connect",
                },
            )
            self.simulation_engine.schedule_event(connection_event)

        self.logger.info(f"Connected to relay {relay_id}")
        return True

    def disconnect_from_relay(self, relay_id: str) -> bool:
        """Disconnect from a relay.

        Args:
            relay_id: ID of the relay to disconnect from.

        Returns:
            True if disconnection was successful.
        """
        if relay_id not in self.connected_relays:
            return False

        # Remove from connected relays
        self.connected_relays.remove(relay_id)

        # Cancel all subscriptions for this relay
        subscriptions_to_remove = [
            sub_id
            for sub_id, sub_data in self.subscriptions.items()
            if sub_data["relay_id"] == relay_id
        ]

        for sub_id in subscriptions_to_remove:
            del self.subscriptions[sub_id]

        # Schedule disconnection event
        if self.simulation_engine:
            disconnection_event = Event(
                time=self.simulation_engine.current_time,
                priority=1,
                event_type="client_connection",
                data={
                    "client_id": self.agent_id,
                    "relay_id": relay_id,
                    "action": "disconnect",
                },
            )
            self.simulation_engine.schedule_event(disconnection_event)

        self.logger.info(f"Disconnected from relay {relay_id}")
        return True

    def publish_event(
        self, nostr_event: NostrEvent, target_relays: list[str] | None = None
    ) -> bool:
        """Publish an event to relays.

        Args:
            nostr_event: The Nostr event to publish.
            target_relays: List of relay IDs to publish to. If None, publishes to all connected relays.

        Returns:
            True if the event was queued for publishing.
        """
        if not self.is_active():
            self.logger.warning("Cannot publish event while client is inactive")
            return False

        # Determine target relays
        if target_relays is None:
            target_relays = list(self.connected_relays)
        else:
            # Filter to only connected relays
            target_relays = [
                relay_id
                for relay_id in target_relays
                if relay_id in self.connected_relays
            ]

        if not target_relays:
            self.logger.warning("No connected relays to publish to")
            return False

        # Schedule publication events for each relay
        if self.simulation_engine:
            for relay_id in target_relays:
                publish_event = Event(
                    time=self.simulation_engine.current_time,
                    priority=1,
                    event_type="nostr_event",
                    data={
                        "sender_id": self.agent_id,
                        "relay_id": relay_id,
                        "nostr_event": nostr_event,
                    },
                )
                self.simulation_engine.schedule_event(publish_event)

        self.logger.info(
            f"Published event {nostr_event.id} to {len(target_relays)} relays"
        )
        return True

    def subscribe_to_events(
        self, relay_id: str, filters: list[RelayFilter]
    ) -> str | None:
        """Subscribe to events from a relay.

        Args:
            relay_id: ID of the relay to subscribe to.
            filters: List of filters for the subscription.

        Returns:
            Subscription ID if successful, None otherwise.
        """
        if not self.is_active():
            self.logger.warning("Cannot subscribe while client is inactive")
            return None

        if relay_id not in self.connected_relays:
            self.logger.warning(f"Not connected to relay {relay_id}")
            return None

        if len(self.subscriptions) >= self.max_subscriptions:
            self.logger.warning("Maximum subscriptions limit reached")
            return None

        # Generate unique subscription ID
        subscription_id = str(uuid.uuid4())

        # Store subscription
        self.subscriptions[subscription_id] = {
            "relay_id": relay_id,
            "filters": filters,
            "active": True,
        }

        # Schedule subscription event
        if self.simulation_engine:
            subscribe_event = Event(
                time=self.simulation_engine.current_time,
                priority=1,
                event_type="client_subscribe",
                data={
                    "client_id": self.agent_id,
                    "relay_id": relay_id,
                    "subscription_id": subscription_id,
                    "filters": filters,
                },
            )
            self.simulation_engine.schedule_event(subscribe_event)

        self.logger.info(f"Subscribed to relay {relay_id} with ID {subscription_id}")
        return subscription_id

    def unsubscribe_from_events(self, subscription_id: str) -> bool:
        """Unsubscribe from events.

        Args:
            subscription_id: ID of the subscription to cancel.

        Returns:
            True if unsubscription was successful.
        """
        if subscription_id not in self.subscriptions:
            return False

        subscription = self.subscriptions[subscription_id]
        relay_id = subscription["relay_id"]

        # Remove subscription
        del self.subscriptions[subscription_id]

        # Schedule unsubscription event
        if self.simulation_engine:
            unsubscribe_event = Event(
                time=self.simulation_engine.current_time,
                priority=1,
                event_type="client_unsubscribe",
                data={
                    "client_id": self.agent_id,
                    "relay_id": relay_id,
                    "subscription_id": subscription_id,
                },
            )
            self.simulation_engine.schedule_event(unsubscribe_event)

        self.logger.info(f"Unsubscribed from {subscription_id}")
        return True

    def queue_event(self, nostr_event: NostrEvent) -> None:
        """Queue an event for processing.

        Args:
            nostr_event: The Nostr event to queue.
        """
        # Check queue limit
        if len(self.event_queue) >= self.max_queued_events:
            # Remove oldest event
            removed_event = self.event_queue.pop(0)
            self.logger.debug(f"Queue full, removed event {removed_event.id}")

        # Add new event
        self.event_queue.append(nostr_event)
        self.logger.debug(f"Queued event {nostr_event.id}")

    def process_event_queue(self) -> list[NostrEvent]:
        """Process all queued events.

        Returns:
            List of processed events.
        """
        processed_events = self.event_queue.copy()
        self.event_queue.clear()

        self.logger.debug(f"Processed {len(processed_events)} queued events")
        return processed_events

    def _handle_relay_response(self, event: Event) -> list[Event]:
        """Handle relay response events."""
        relay_id = event.data.get("relay_id")
        response_type = event.data.get("response_type")
        event_id = event.data.get("event_id")
        accepted = event.data.get("accepted", False)
        message = event.data.get("message", "")

        self.logger.debug(
            f"Relay {relay_id} response for event {event_id}: {response_type} - {message}"
        )

        # Could generate events based on response (e.g., retry on failure)
        return []

    def _handle_event_notification(self, event: Event) -> list[Event]:
        """Handle event notifications from relays."""
        subscription_id = event.data.get("subscription_id")
        event_data = event.data.get("event")

        if event_data:
            # Convert dict back to NostrEvent
            nostr_event = NostrEvent.from_dict(event_data)
            self.queue_event(nostr_event)

            self.logger.debug(
                f"Received event {nostr_event.id} for subscription {subscription_id}"
            )

        return []

    def _handle_subscription_eose(self, event: Event) -> list[Event]:
        """Handle end-of-stored-events notifications."""
        subscription_id = event.data.get("subscription_id")

        self.logger.debug(f"End of stored events for subscription {subscription_id}")

        # Could generate events to trigger further actions
        return []

    def _handle_network_event(self, event: Event) -> list[Event]:
        """Handle network-related events."""
        event_type = event.data.get("event_type")

        self.logger.debug(f"Network event: {event_type}")

        # Could handle connection issues, relay failures, etc.
        return []

    def get_stats(self) -> dict[str, Any]:
        """Get client statistics.

        Returns:
            Dictionary containing client statistics.
        """
        return {
            "connected_relays": len(self.connected_relays),
            "active_subscriptions": len(self.subscriptions),
            "queued_events": len(self.event_queue),
            "relay_list": list(self.connected_relays),
            "subscription_list": list(self.subscriptions.keys()),
        }
