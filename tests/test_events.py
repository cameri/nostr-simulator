"""Tests for the simulation events module."""

from nostr_simulator.simulation.events import (
    Event,
    EventDispatcher,
    EventHandler,
    EventQueue,
)


class TestEvent:
    """Test Event class."""

    def test_event_creation(self) -> None:
        """Test creating an event."""
        event = Event(
            time=10.0, priority=1, event_type="test_event", data={"key": "value"}
        )

        assert event.time == 10.0
        assert event.priority == 1
        assert event.event_type == "test_event"
        assert event.data == {"key": "value"}
        assert event.event_id is not None

    def test_event_ordering(self):
        """Test event ordering for priority queue."""
        event1 = Event(time=10.0, priority=1)
        event2 = Event(time=5.0, priority=2)
        event3 = Event(time=10.0, priority=0)

        # Earlier time comes first
        assert event2 < event1

        # Same time, lower priority comes first
        assert event3 < event1

    def test_event_equality(self):
        """Test event equality."""
        event1 = Event(time=10.0, priority=1)
        event2 = Event(time=10.0, priority=1)

        # Different events with same content are not equal
        assert event1 != event2

        # Same event is equal to itself
        assert event1 == event1


class TestEventQueue:
    """Test EventQueue class."""

    def test_empty_queue(self):
        """Test empty queue behavior."""
        queue = EventQueue()

        assert queue.is_empty()
        assert queue.size() == 0
        assert queue.get_next_event() is None
        assert queue.peek_next_event() is None

    def test_schedule_and_get_event(self):
        """Test scheduling and getting events."""
        queue = EventQueue()

        event_id = queue.schedule_event(
            time=10.0, event_type="test", priority=1, data={"test": True}
        )

        assert not queue.is_empty()
        assert queue.size() == 1
        assert event_id is not None

        event = queue.get_next_event()
        assert event is not None
        assert event.time == 10.0
        assert event.event_type == "test"
        assert event.priority == 1
        assert event.data == {"test": True}

        assert queue.is_empty()

    def test_event_ordering_in_queue(self):
        """Test that events are returned in correct order."""
        queue = EventQueue()

        # Schedule events out of order
        queue.schedule_event(time=20.0, event_type="second")
        queue.schedule_event(time=10.0, event_type="first")
        queue.schedule_event(time=30.0, event_type="third")

        # Should get them in time order
        event1 = queue.get_next_event()
        event2 = queue.get_next_event()
        event3 = queue.get_next_event()

        assert event1.event_type == "first"
        assert event2.event_type == "second"
        assert event3.event_type == "third"

    def test_peek_event(self):
        """Test peeking at next event without removing it."""
        queue = EventQueue()
        queue.schedule_event(time=10.0, event_type="test")

        # Peek should return event but not remove it
        peeked = queue.peek_next_event()
        assert peeked is not None
        assert peeked.event_type == "test"
        assert queue.size() == 1

        # Get should return same event and remove it
        got = queue.get_next_event()
        assert got.event_id == peeked.event_id
        assert queue.size() == 0

    def test_cancel_event(self):
        """Test canceling events."""
        queue = EventQueue()

        event_id = queue.schedule_event(time=10.0, event_type="test")
        assert queue.size() == 1

        # Cancel the event
        result = queue.cancel_event(event_id)
        assert result is True

        # Event should still be in queue but marked as cancelled
        assert queue.size() == 1
        event = queue.get_next_event()
        assert event.data.get("_cancelled") is True

        # Canceling non-existent event should return False
        result = queue.cancel_event("nonexistent")
        assert result is False

    def test_clear_queue(self):
        """Test clearing the queue."""
        queue = EventQueue()

        queue.schedule_event(time=10.0, event_type="test1")
        queue.schedule_event(time=20.0, event_type="test2")
        assert queue.size() == 2

        queue.clear()
        assert queue.is_empty()
        assert queue.size() == 0


class MockEventHandler(EventHandler):
    """Mock event handler for testing."""

    def __init__(self, handled_types=None):
        self.handled_types = handled_types or set()
        self.handled_events = []

    def handle_event(self, event):
        self.handled_events.append(event)
        return []

    def can_handle(self, event_type):
        return event_type in self.handled_types


class TestEventDispatcher:
    """Test EventDispatcher class."""

    def test_register_and_dispatch(self):
        """Test registering handlers and dispatching events."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler({"test_event"})

        dispatcher.register_handler("test_event", handler)

        event = Event(time=10.0, priority=1, event_type="test_event")
        new_events = dispatcher.dispatch_event(event)

        assert len(handler.handled_events) == 1
        assert handler.handled_events[0] == event
        assert new_events == []

    def test_catch_all_handler(self):
        """Test catch-all event handlers."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler({"any_event"})

        dispatcher.register_catch_all_handler(handler)

        event = Event(time=10.0, priority=1, event_type="any_event")
        dispatcher.dispatch_event(event)

        assert len(handler.handled_events) == 1

    def test_unregister_handler(self):
        """Test unregistering event handlers."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler({"test_event"})

        dispatcher.register_handler("test_event", handler)

        # Unregister existing handler
        result = dispatcher.unregister_handler("test_event", handler)
        assert result is True

        # Try to unregister again
        result = dispatcher.unregister_handler("test_event", handler)
        assert result is False

        # Event should not be handled now
        event = Event(time=10.0, priority=1, event_type="test_event")
        dispatcher.dispatch_event(event)
        assert len(handler.handled_events) == 0

    def test_cancelled_event_not_dispatched(self):
        """Test that cancelled events are not dispatched."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler({"test_event"})

        dispatcher.register_handler("test_event", handler)

        event = Event(
            time=10.0, priority=1, event_type="test_event", data={"_cancelled": True}
        )
        dispatcher.dispatch_event(event)

        assert len(handler.handled_events) == 0
