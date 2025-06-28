"""Relay agent implementation for Nostr simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..logging_config import get_logger
from ..protocol.events import NostrEvent, NostrEventKind
from ..simulation.events import Event
from .base import AgentType, BaseAgent


@dataclass
class RelayFilter:
    """Filter for querying Nostr events."""

    ids: list[str] | None = None
    authors: list[str] | None = None
    kinds: list[NostrEventKind] | None = None
    tags: dict[str, list[str]] | None = None
    since: int | None = None
    until: int | None = None
    limit: int | None = None

    def matches(self, event: NostrEvent) -> bool:
        """Check if an event matches this filter.

        Args:
            event: The Nostr event to check.

        Returns:
            True if the event matches the filter criteria.
        """
        # Check ID filter
        if self.ids is not None and event.id not in self.ids:
            return False

        # Check author filter
        if self.authors is not None and event.pubkey not in self.authors:
            return False

        # Check kind filter
        if self.kinds is not None and event.kind not in self.kinds:
            return False

        # Check time range filters
        if self.since is not None and event.created_at < self.since:
            return False

        if self.until is not None and event.created_at > self.until:
            return False

        # Check tag filters
        if self.tags is not None:
            for tag_name, tag_values in self.tags.items():
                # Find tags with matching name
                matching_tags = [tag for tag in event.tags if tag.name == tag_name]

                # Check if any matching tag has one of the required values
                found_match = False
                for tag in matching_tags:
                    if any(value in tag.values for value in tag_values):
                        found_match = True
                        break

                if not found_match:
                    return False

        return True


class RelayStorage:
    """Storage system for relay events."""

    def __init__(self) -> None:
        """Initialize the storage system."""
        self.events: dict[str, NostrEvent] = {}
        self.events_by_author: dict[str, set[str]] = {}
        self.events_by_kind: dict[NostrEventKind, set[str]] = {}
        self.logger = get_logger(f"{__name__}.storage")

    def store_event(self, event: NostrEvent) -> bool:
        """Store an event in the relay.

        Args:
            event: The Nostr event to store.

        Returns:
            True if the event was stored successfully, False if it already exists.
        """
        if event.id in self.events:
            self.logger.debug(f"Event {event.id} already exists")
            return False

        # Store the event
        self.events[event.id] = event

        # Index by author
        if event.pubkey not in self.events_by_author:
            self.events_by_author[event.pubkey] = set()
        self.events_by_author[event.pubkey].add(event.id)

        # Index by kind
        if event.kind not in self.events_by_kind:
            self.events_by_kind[event.kind] = set()
        self.events_by_kind[event.kind].add(event.id)

        self.logger.debug(f"Stored event {event.id} from {event.pubkey}")
        return True

    def get_event(self, event_id: str) -> NostrEvent | None:
        """Retrieve an event by ID.

        Args:
            event_id: The ID of the event to retrieve.

        Returns:
            The event if found, None otherwise.
        """
        return self.events.get(event_id)

    def delete_event(self, event_id: str) -> bool:
        """Delete an event from storage.

        Args:
            event_id: The ID of the event to delete.

        Returns:
            True if the event was deleted, False if it didn't exist.
        """
        if event_id not in self.events:
            return False

        event = self.events[event_id]

        # Remove from main storage
        del self.events[event_id]

        # Remove from author index
        if event.pubkey in self.events_by_author:
            self.events_by_author[event.pubkey].discard(event_id)
            if not self.events_by_author[event.pubkey]:
                del self.events_by_author[event.pubkey]

        # Remove from kind index
        if event.kind in self.events_by_kind:
            self.events_by_kind[event.kind].discard(event_id)
            if not self.events_by_kind[event.kind]:
                del self.events_by_kind[event.kind]

        self.logger.debug(f"Deleted event {event_id}")
        return True

    def query_events(self, filter_obj: RelayFilter) -> list[NostrEvent]:
        """Query events based on a filter.

        Args:
            filter_obj: The filter to apply.

        Returns:
            List of events matching the filter, sorted by creation time (newest first).
        """
        # Start with all events if no efficient filter is possible
        candidate_events = set(self.events.keys())

        # Apply efficient filters first to reduce candidate set
        if filter_obj.authors is not None:
            author_events = set()
            for author in filter_obj.authors:
                if author in self.events_by_author:
                    author_events.update(self.events_by_author[author])
            candidate_events &= author_events

        if filter_obj.kinds is not None:
            kind_events = set()
            for kind in filter_obj.kinds:
                if kind in self.events_by_kind:
                    kind_events.update(self.events_by_kind[kind])
            candidate_events &= kind_events

        # Apply detailed filters
        matching_events = []
        for event_id in candidate_events:
            event = self.events[event_id]
            if filter_obj.matches(event):
                matching_events.append(event)

        # Sort by creation time (newest first)
        matching_events.sort(key=lambda e: e.created_at, reverse=True)

        # Apply limit
        if filter_obj.limit is not None:
            matching_events = matching_events[: filter_obj.limit]

        return matching_events


@dataclass
class RelaySubscription:
    """Represents a client subscription."""

    client_id: str
    subscription_id: str
    filters: list[RelayFilter]
    active: bool = True


class RelayAgent(BaseAgent):
    """Relay agent that stores and serves Nostr events."""

    def __init__(self, agent_id: str, simulation_engine: Any = None) -> None:
        """Initialize the relay agent.

        Args:
            agent_id: Unique identifier for the relay.
            simulation_engine: Reference to the simulation engine.
        """
        super().__init__(agent_id, AgentType.RELAY, simulation_engine)

        # Storage system
        self.storage = RelayStorage()

        # Client management
        self.connected_clients: set[str] = set()
        self.subscriptions: dict[str, dict[str, Any]] = {}

        # Event handling configuration
        self.handled_event_types = {
            "nostr_event",
            "client_subscribe",
            "client_unsubscribe",
            "relay_sync",
        }

        # Relay policies
        self.max_events_per_client = 1000
        self.max_subscriptions_per_client = 10
        self.max_filters_per_subscription = 10

        self.logger.info(f"Initialized relay {agent_id}")

    def on_activate(self, current_time: float) -> None:
        """Called when the relay is activated."""
        self.logger.info(f"Relay {self.agent_id} is now active")

    def on_deactivate(self, current_time: float) -> None:
        """Called when the relay is deactivated."""
        self.logger.info(f"Relay {self.agent_id} is now inactive")

    def on_message_received(self, message: Any) -> None:
        """Process incoming messages."""
        self.logger.debug(f"Received message: {message.message_type}")

    def on_event(self, event: Event) -> list[Event]:
        """Handle simulation events."""
        events_generated = []

        if event.event_type == "nostr_event":
            events_generated.extend(self._handle_nostr_event(event))
        elif event.event_type == "client_subscribe":
            events_generated.extend(self._handle_client_subscribe(event))
        elif event.event_type == "client_unsubscribe":
            events_generated.extend(self._handle_client_unsubscribe(event))
        elif event.event_type == "relay_sync":
            events_generated.extend(self._handle_relay_sync(event))

        return events_generated

    def accept_event(self, nostr_event: NostrEvent) -> bool:
        """Accept and store a Nostr event.

        Args:
            nostr_event: The Nostr event to store.

        Returns:
            True if the event was accepted and stored.
        """
        if not self.is_active():
            self.logger.warning("Cannot accept event while relay is inactive")
            return False

        # Store the event
        if not self.storage.store_event(nostr_event):
            return False

        # Broadcast to subscribed clients
        self._broadcast_event_to_subscribers(nostr_event)

        self.logger.info(f"Accepted event {nostr_event.id} from {nostr_event.pubkey}")
        return True

    def query_events(self, filter_obj: RelayFilter) -> list[NostrEvent]:
        """Query stored events.

        Args:
            filter_obj: The filter to apply.

        Returns:
            List of matching events.
        """
        return self.storage.query_events(filter_obj)

    def subscribe_client(
        self, client_id: str, subscription_id: str, filters: list[RelayFilter]
    ) -> bool:
        """Subscribe a client to receive events.

        Args:
            client_id: ID of the subscribing client.
            subscription_id: Unique subscription ID.
            filters: List of filters for the subscription.

        Returns:
            True if subscription was successful.
        """
        if not self.is_active():
            return False

        # Check limits
        client_subscriptions = [
            sub for sub in self.subscriptions.values() if sub["client_id"] == client_id
        ]

        if len(client_subscriptions) >= self.max_subscriptions_per_client:
            self.logger.warning(f"Client {client_id} exceeded subscription limit")
            return False

        if len(filters) > self.max_filters_per_subscription:
            self.logger.warning(f"Subscription {subscription_id} exceeded filter limit")
            return False

        # Store subscription
        self.connected_clients.add(client_id)
        self.subscriptions[subscription_id] = {
            "client_id": client_id,
            "filters": filters,
            "active": True,
        }

        self.logger.info(f"Client {client_id} subscribed with ID {subscription_id}")
        return True

    def unsubscribe_client(self, subscription_id: str) -> bool:
        """Unsubscribe a client.

        Args:
            subscription_id: The subscription ID to remove.

        Returns:
            True if unsubscription was successful.
        """
        if subscription_id not in self.subscriptions:
            return False

        del self.subscriptions[subscription_id]
        self.logger.info(f"Unsubscribed {subscription_id}")
        return True

    def _handle_nostr_event(self, event: Event) -> list[Event]:
        """Handle incoming Nostr events."""
        nostr_event = event.data.get("nostr_event")
        if nostr_event:
            self.accept_event(nostr_event)
        return []

    def _handle_client_subscribe(self, event: Event) -> list[Event]:
        """Handle client subscription requests."""
        client_id = event.data.get("client_id")
        subscription_id = event.data.get("subscription_id")
        filters = event.data.get("filters", [])

        if client_id and subscription_id:
            self.subscribe_client(client_id, subscription_id, filters)
        return []

    def _handle_client_unsubscribe(self, event: Event) -> list[Event]:
        """Handle client unsubscription requests."""
        subscription_id = event.data.get("subscription_id")
        if subscription_id:
            self.unsubscribe_client(subscription_id)
        return []

    def _handle_relay_sync(self, event: Event) -> list[Event]:
        """Handle relay synchronization events."""
        # TODO: Implement relay-to-relay synchronization
        return []

    def _broadcast_event_to_subscribers(self, nostr_event: NostrEvent) -> None:
        """Broadcast an event to matching subscribers."""
        for subscription_id, subscription in self.subscriptions.items():
            if not subscription["active"]:
                continue

            # Check if event matches any of the subscription filters
            for filter_obj in subscription["filters"]:
                if filter_obj.matches(nostr_event):
                    self._send_event_to_client(
                        subscription["client_id"], subscription_id, nostr_event
                    )
                    break

    def _send_event_to_client(
        self, client_id: str, subscription_id: str, nostr_event: NostrEvent
    ) -> None:
        """Send an event to a specific client."""
        if self.simulation_engine:
            # Schedule a message delivery event
            event = Event(
                time=self.simulation_engine.current_time,
                priority=1,
                event_type="message_delivery",
                data={
                    "sender_id": self.agent_id,
                    "receiver_id": client_id,
                    "message_type": "event_notification",
                    "content": {
                        "subscription_id": subscription_id,
                        "event": nostr_event.to_dict(),
                    },
                },
            )
            self.simulation_engine.schedule_event(event)

    def get_stats(self) -> dict[str, Any]:
        """Get relay statistics.

        Returns:
            Dictionary containing relay statistics.
        """
        return {
            "total_events": len(self.storage.events),
            "connected_clients": len(self.connected_clients),
            "active_subscriptions": len(self.subscriptions),
            "events_by_kind": {
                kind.name: len(event_ids)
                for kind, event_ids in self.storage.events_by_kind.items()
            },
        }
