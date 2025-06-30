"""Tests for event system."""

from uuid import uuid4

import pytest

from .events import Event, EventDispatcher, EventHandler, EventQueue


class MockEventHandler(EventHandler):
    """Mock event handler for testing."""

    def __init__(self, handled_types: set[str]) -> None:
        self.handled_types = handled_types
        self.handled_events: list[Event] = []
        self.generated_events: list[Event] = []

    def handle_event(self, event: Event) -> list[Event]:
        """Handle an event and optionally generate new events."""
        self.handled_events.append(event)
        return self.generated_events.copy()

    def can_handle(self, event_type: str) -> bool:
        """Check if can handle event type."""
        return event_type in self.handled_types

    def set_generated_events(self, events: list[Event]) -> None:
        """Set events to generate when handling."""
        self.generated_events = events


class TestEvent:
    """Test Event class functionality."""

    def test_event_creation(self) -> None:
        """Test creating events with different parameters."""
        event = Event(
            time=10.0, priority=1, event_type="test_event", data={"key": "value"}
        )

        assert event.time == 10.0
        assert event.priority == 1
        assert event.event_type == "test_event"
        assert event.data == {"key": "value"}
        assert event.event_id is not None

    def test_event_ordering(self) -> None:
        """Test that events are ordered correctly."""
        event1 = Event(time=10.0, priority=1)
        event2 = Event(time=5.0, priority=1)
        event3 = Event(time=10.0, priority=0)

        # Earlier time comes first
        assert event2 < event1

        # Same time, lower priority comes first
        assert event3 < event1

    def test_event_equality(self) -> None:
        """Test event equality based on event_id."""
        event_id = str(uuid4())
        event1 = Event(time=10.0, priority=1, event_id=event_id)
        event2 = Event(time=20.0, priority=2, event_id=event_id)
        event3 = Event(time=10.0, priority=1)

        # Same event_id means equal
        assert event1 == event2

        # Different event_id means not equal
        assert event1 != event3


class TestEventQueue:
    """Test EventQueue functionality."""

    def test_empty_queue(self) -> None:
        """Test empty queue behavior."""
        queue = EventQueue()

        assert queue.is_empty()
        assert queue.size() == 0
        assert queue.get_next_event() is None
        assert queue.peek_next_event() is None

    def test_schedule_and_get_event(self) -> None:
        """Test scheduling and retrieving events."""
        queue = EventQueue()

        event_id = queue.schedule_event(
            time=10.0, event_type="test_event", data={"test": True}
        )

        assert not queue.is_empty()
        assert queue.size() == 1

        # Peek shouldn't remove the event
        peeked = queue.peek_next_event()
        assert peeked is not None
        assert queue.size() == 1

        # Get should remove the event
        event = queue.get_next_event()
        assert event is not None
        assert event.event_id == event_id
        assert event.time == 10.0
        assert event.event_type == "test_event"
        assert queue.is_empty()

    def test_event_ordering_in_queue(self) -> None:
        """Test that events are retrieved in correct order."""
        queue = EventQueue()

        # Schedule events out of order
        id1 = queue.schedule_event(time=20.0, event_type="event1")
        id2 = queue.schedule_event(time=10.0, event_type="event2")
        id3 = queue.schedule_event(time=15.0, event_type="event3")

        # Should retrieve in time order
        event1 = queue.get_next_event()
        assert event1 is not None
        assert event1.time == 10.0
        assert event1.event_id == id2

        event2 = queue.get_next_event()
        assert event2 is not None
        assert event2.time == 15.0
        assert event2.event_id == id3

        event3 = queue.get_next_event()
        assert event3 is not None
        assert event3.time == 20.0
        assert event3.event_id == id1

    def test_cancel_event(self) -> None:
        """Test event cancellation."""
        queue = EventQueue()

        event_id = queue.schedule_event(time=10.0, event_type="test_event")
        assert queue.size() == 1

        # Cancel the event
        assert queue.cancel_event(event_id)

        # Event should still be in queue but marked as cancelled
        assert queue.size() == 1
        event = queue.get_next_event()
        assert event is not None
        assert event.data.get("_cancelled") is True

        # Cancelling non-existent event should return False
        assert not queue.cancel_event("non_existent_id")

    def test_clear_queue(self) -> None:
        """Test clearing the queue."""
        queue = EventQueue()

        queue.schedule_event(time=10.0, event_type="event1")
        queue.schedule_event(time=20.0, event_type="event2")
        assert queue.size() == 2

        queue.clear()
        assert queue.is_empty()
        assert queue.size() == 0


class TestEventDispatcher:
    """Test EventDispatcher functionality."""

    def test_register_and_dispatch(self) -> None:
        """Test registering handlers and dispatching events."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler({"test_event"})

        dispatcher.register_handler("test_event", handler)

        event = Event(time=10.0, priority=0, event_type="test_event")
        dispatcher.dispatch_event(event)

        # Handler should have processed the event
        assert len(handler.handled_events) == 1
        assert handler.handled_events[0] == event

    def test_unregister_handler(self) -> None:
        """Test unregistering event handlers."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler({"test_event"})

        dispatcher.register_handler("test_event", handler)
        assert dispatcher.unregister_handler("test_event", handler)

        # After unregistering, handler shouldn't receive events
        event = Event(time=10.0, priority=0, event_type="test_event")
        dispatcher.dispatch_event(event)

        assert len(handler.handled_events) == 0

        # Unregistering non-existent handler should return False
        assert not dispatcher.unregister_handler("test_event", handler)

    def test_catch_all_handler(self) -> None:
        """Test catch-all event handlers."""
        dispatcher = EventDispatcher()
        catch_all_handler = MockEventHandler({"test_event", "other_event"})

        dispatcher.register_catch_all_handler(catch_all_handler)

        # Dispatch different event types
        event1 = Event(time=10.0, priority=0, event_type="test_event")
        event2 = Event(time=10.0, priority=0, event_type="other_event")

        dispatcher.dispatch_event(event1)
        dispatcher.dispatch_event(event2)

        # Catch-all handler should have received both
        assert len(catch_all_handler.handled_events) == 2

    def test_multiple_handlers(self) -> None:
        """Test multiple handlers for same event type."""
        dispatcher = EventDispatcher()
        handler1 = MockEventHandler({"test_event"})
        handler2 = MockEventHandler({"test_event"})

        dispatcher.register_handler("test_event", handler1)
        dispatcher.register_handler("test_event", handler2)

        event = Event(time=10.0, priority=0, event_type="test_event")
        dispatcher.dispatch_event(event)

        # Both handlers should have received the event
        assert len(handler1.handled_events) == 1
        assert len(handler2.handled_events) == 1

    def test_handler_generates_events(self) -> None:
        """Test handlers that generate new events."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler({"test_event"})

        # Set up handler to generate new events
        new_event = Event(time=20.0, priority=0, event_type="generated_event")
        handler.set_generated_events([new_event])

        dispatcher.register_handler("test_event", handler)

        event = Event(time=10.0, priority=0, event_type="test_event")
        new_events = dispatcher.dispatch_event(event)

        # Should return the generated events
        assert len(new_events) == 1
        assert new_events[0].event_type == "generated_event"

    def test_cancelled_event_ignored(self) -> None:
        """Test that cancelled events are ignored."""
        dispatcher = EventDispatcher()
        handler = MockEventHandler({"test_event"})

        dispatcher.register_handler("test_event", handler)

        # Create cancelled event
        event = Event(
            time=10.0, priority=0, event_type="test_event", data={"_cancelled": True}
        )

        new_events = dispatcher.dispatch_event(event)

        # Handler should not have received the cancelled event
        assert len(handler.handled_events) == 0
        assert len(new_events) == 0

    def test_handler_exception_handling(self) -> None:
        """Test that handler exceptions don't crash dispatcher."""
        dispatcher = EventDispatcher()

        class FailingHandler(EventHandler):
            def handle_event(self, event: Event) -> list[Event]:
                raise RuntimeError("Handler failed")

            def can_handle(self, event_type: str) -> bool:
                return event_type == "test_event"

        failing_handler = FailingHandler()
        working_handler = MockEventHandler({"test_event"})

        dispatcher.register_handler("test_event", failing_handler)
        dispatcher.register_handler("test_event", working_handler)

        event = Event(time=10.0, priority=0, event_type="test_event")

        # Should not raise exception, working handler should still work
        dispatcher.dispatch_event(event)

        assert len(working_handler.handled_events) == 1


if __name__ == "__main__":
    pytest.main([__file__])
