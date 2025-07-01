"""Tests for replay attack implementation."""

import time
from unittest.mock import Mock

from ...protocol.events import NostrEvent, NostrEventKind
from ...protocol.keys import NostrKeyPair
from ...simulation.events import Event
from .replay_attacker import (
    CollectedEvent,
    ReplayAttackerAgent,
    ReplayPattern,
    ReplayStrategy,
    ReplayTiming,
)


class TestReplayTiming:
    """Test ReplayTiming configuration."""

    def test_default_values(self) -> None:
        """Test default timing configuration."""
        timing = ReplayTiming()

        assert timing.collection_duration == 300.0
        assert timing.replay_delay == 60.0
        assert timing.replay_interval == 5.0
        assert timing.replay_batch_size == 10
        assert timing.timing_jitter is True
        assert timing.randomization == 0.3

    def test_custom_values(self) -> None:
        """Test custom timing configuration."""
        timing = ReplayTiming(
            collection_duration=600.0,
            replay_delay=120.0,
            replay_interval=10.0,
            replay_batch_size=5,
            timing_jitter=False,
            randomization=0.5,
        )

        assert timing.collection_duration == 600.0
        assert timing.replay_delay == 120.0
        assert timing.replay_interval == 10.0
        assert timing.replay_batch_size == 5
        assert timing.timing_jitter is False
        assert timing.randomization == 0.5


class TestReplayStrategy:
    """Test ReplayStrategy configuration."""

    def test_default_values(self) -> None:
        """Test default strategy configuration."""
        strategy = ReplayStrategy()

        assert NostrEventKind.TEXT_NOTE in strategy.target_event_kinds
        assert NostrEventKind.SET_METADATA in strategy.target_event_kinds
        assert strategy.max_collected_events == 1000
        assert strategy.min_event_age == 60.0
        assert strategy.key_rotation is True
        assert strategy.cross_relay_replay is True
        assert strategy.content_modification is False
        assert strategy.timestamp_modification is True
        assert strategy.amplification_factor == 1
        assert strategy.max_amplification == 5
        assert strategy.detection_evasion is True
        assert strategy.relay_coordination is False

    def test_custom_values(self) -> None:
        """Test custom strategy configuration."""
        strategy = ReplayStrategy(
            target_event_kinds=[NostrEventKind.TEXT_NOTE],
            max_collected_events=500,
            min_event_age=120.0,
            key_rotation=False,
            amplification_factor=3,
        )

        assert strategy.target_event_kinds == [NostrEventKind.TEXT_NOTE]
        assert strategy.max_collected_events == 500
        assert strategy.min_event_age == 120.0
        assert strategy.key_rotation is False
        assert strategy.amplification_factor == 3


class TestReplayPattern:
    """Test ReplayPattern configuration."""

    def test_default_values(self) -> None:
        """Test default pattern configuration."""
        pattern = ReplayPattern()

        assert isinstance(pattern.timing, ReplayTiming)
        assert isinstance(pattern.strategy, ReplayStrategy)
        assert pattern.collection_phase is True
        assert pattern.replay_phase is True
        assert pattern.continuous_mode is False

    def test_custom_values(self) -> None:
        """Test custom pattern configuration."""
        timing = ReplayTiming(collection_duration=120.0)
        strategy = ReplayStrategy(amplification_factor=2)

        pattern = ReplayPattern(
            timing=timing,
            strategy=strategy,
            collection_phase=False,
            continuous_mode=True,
        )

        assert pattern.timing.collection_duration == 120.0
        assert pattern.strategy.amplification_factor == 2
        assert pattern.collection_phase is False
        assert pattern.continuous_mode is True


class TestCollectedEvent:
    """Test CollectedEvent data class."""

    def test_creation(self) -> None:
        """Test collected event creation."""
        keypair = NostrKeyPair.generate()
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test message",
            pubkey=keypair.public_key,
            created_at=int(time.time()),
        )

        collected = CollectedEvent(
            original_event=event,
            collection_time=time.time(),
            source_relay="relay1",
        )

        assert collected.original_event == event
        assert collected.replay_count == 0
        assert collected.last_replay_time == 0.0
        assert collected.source_relay == "relay1"


class TestReplayAttackerAgent:
    """Test ReplayAttackerAgent implementation."""

    def test_initialization(self) -> None:
        """Test agent initialization."""
        agent = ReplayAttackerAgent("test_agent")

        assert agent.agent_id == "test_agent"
        assert isinstance(agent.replay_pattern, ReplayPattern)
        assert agent.attack_active is False
        assert agent.collection_active is False
        assert agent.replay_active is False
        assert len(agent.replay_keys) >= 5
        assert len(agent.collected_events) == 0
        assert agent.total_events_collected == 0

    def test_initialization_with_pattern(self) -> None:
        """Test agent initialization with custom pattern."""
        timing = ReplayTiming(collection_duration=120.0)
        strategy = ReplayStrategy(amplification_factor=3)
        pattern = ReplayPattern(timing=timing, strategy=strategy)

        agent = ReplayAttackerAgent("test_agent", replay_pattern=pattern)

        assert agent.replay_pattern.timing.collection_duration == 120.0
        assert agent.replay_pattern.strategy.amplification_factor == 3

    def test_start_attack(self) -> None:
        """Test starting attack."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)

        assert agent.attack_active is True
        assert agent.attack_start_time == current_time
        assert agent.collection_active is True

    def test_start_attack_when_already_active(self) -> None:
        """Test starting attack when already active."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        original_time = agent.attack_start_time

        agent.start_attack(current_time + 10)

        assert agent.attack_start_time == original_time

    def test_stop_attack(self) -> None:
        """Test stopping attack."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        agent.stop_attack()

        assert agent.attack_active is False
        assert agent.collection_active is False
        assert agent.replay_active is False

    def test_start_collection_phase(self) -> None:
        """Test starting collection phase."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_collection_phase(current_time)

        assert agent.collection_active is True
        assert agent.collection_end_time > current_time

    def test_start_replay_phase(self) -> None:
        """Test starting replay phase."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_replay_phase(current_time)

        assert agent.replay_active is True
        assert agent.collection_active is False
        assert agent.next_replay_time > current_time

    def test_should_collect_event_when_not_collecting(self) -> None:
        """Test event collection decision when not collecting."""
        agent = ReplayAttackerAgent("test_agent")
        keypair = NostrKeyPair.generate()
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test message",
            pubkey=keypair.public_key,
            created_at=int(time.time()),
        )

        result = agent.should_collect_event(event)

        assert result is False

    def test_should_collect_event_when_collecting(self) -> None:
        """Test event collection decision when actively collecting."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_collection_phase(current_time)

        keypair = NostrKeyPair.generate()
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test message",
            pubkey=keypair.public_key,
            created_at=int(current_time),
        )

        result = agent.should_collect_event(event)

        assert result is True

    def test_should_collect_event_wrong_kind(self) -> None:
        """Test event collection with wrong event kind."""
        strategy = ReplayStrategy(target_event_kinds=[NostrEventKind.SET_METADATA])
        pattern = ReplayPattern(strategy=strategy)
        agent = ReplayAttackerAgent("test_agent", replay_pattern=pattern)
        current_time = time.time()

        agent.start_collection_phase(current_time)

        keypair = NostrKeyPair.generate()
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,  # Not in target kinds
            content="Test message",
            pubkey=keypair.public_key,
            created_at=int(current_time),
        )

        result = agent.should_collect_event(event)

        assert result is False

    def test_should_collect_event_own_key(self) -> None:
        """Test event collection with own key."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_collection_phase(current_time)

        # Use one of our own replay keys
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test message",
            pubkey=agent.replay_keys[0].public_key,
            created_at=int(current_time),
        )

        result = agent.should_collect_event(event)

        assert result is False

    def test_collect_event(self) -> None:
        """Test event collection."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_collection_phase(current_time)

        keypair = NostrKeyPair.generate()
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test message",
            pubkey=keypair.public_key,
            created_at=int(current_time),
        )

        agent.collect_event(event, current_time, "relay1")

        assert len(agent.collected_events) == 1
        assert agent.total_events_collected == 1

        collected = list(agent.collected_events.values())[0]
        assert collected.original_event == event
        assert collected.collection_time == current_time
        assert collected.source_relay == "relay1"

    def test_should_replay_now_when_not_active(self) -> None:
        """Test replay decision when not active."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        result = agent.should_replay_now(current_time)

        assert result is False

    def test_should_replay_now_when_active(self) -> None:
        """Test replay decision when active."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_replay_phase(current_time)
        agent.events_to_replay = ["event1", "event2"]
        agent.next_replay_time = current_time - 1  # Past time

        result = agent.should_replay_now(current_time)

        assert result is True

    def test_should_replay_now_no_events(self) -> None:
        """Test replay decision when no events to replay."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_replay_phase(current_time)
        agent.events_to_replay = []  # No events

        result = agent.should_replay_now(current_time)

        assert result is False

    def test_create_replayed_event(self) -> None:
        """Test creating replayed event."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        keypair = NostrKeyPair.generate()
        original_event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Original message",
            pubkey=keypair.public_key,
            created_at=int(current_time - 100),
        )

        replayed_event = agent._create_replayed_event(original_event, current_time, 0)

        assert replayed_event is not None
        assert replayed_event.kind == original_event.kind
        assert (
            replayed_event.content == original_event.content
        )  # No modification by default
        assert replayed_event.pubkey != original_event.pubkey  # Different key
        assert replayed_event.pubkey in [key.public_key for key in agent.replay_keys]

    def test_modify_content_no_modification(self) -> None:
        """Test content modification when disabled."""
        strategy = ReplayStrategy(content_modification=False)
        pattern = ReplayPattern(strategy=strategy)
        agent = ReplayAttackerAgent("test_agent", replay_pattern=pattern)

        original_content = "Test message"
        modified_content = agent._modify_content(original_content, 0)

        assert modified_content == original_content

    def test_modify_content_with_modification(self) -> None:
        """Test content modification when enabled."""
        strategy = ReplayStrategy(content_modification=True)
        pattern = ReplayPattern(strategy=strategy)
        agent = ReplayAttackerAgent("test_agent", replay_pattern=pattern)

        original_content = "Test message"

        # Test multiple times to ensure modification happens
        modified_at_least_once = False
        for i in range(10):  # Try 10 times
            modified_content = agent._modify_content(original_content, i)
            if modified_content != original_content:
                modified_at_least_once = True
                break

        assert (
            modified_at_least_once
        ), "Content should be modified at least once in 10 attempts"

    def test_modify_timestamp_no_modification(self) -> None:
        """Test timestamp modification when disabled."""
        strategy = ReplayStrategy(timestamp_modification=False)
        pattern = ReplayPattern(strategy=strategy)
        agent = ReplayAttackerAgent("test_agent", replay_pattern=pattern)

        current_time = time.time()
        original_timestamp = int(current_time - 100)
        modified_timestamp = agent._modify_timestamp(original_timestamp, current_time)

        assert modified_timestamp == int(current_time)

    def test_modify_timestamp_with_modification(self) -> None:
        """Test timestamp modification when enabled."""
        strategy = ReplayStrategy(timestamp_modification=True, detection_evasion=True)
        pattern = ReplayPattern(strategy=strategy)
        agent = ReplayAttackerAgent("test_agent", replay_pattern=pattern)

        current_time = time.time()
        original_timestamp = int(current_time - 100)
        modified_timestamp = agent._modify_timestamp(original_timestamp, current_time)

        # Should be close to current time but with random offset
        assert abs(modified_timestamp - int(current_time)) <= 300

    def test_handle_detection(self) -> None:
        """Test handling detection of replay attack."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        detected_key = agent.replay_keys[0].public_key

        agent.handle_detection(detected_key, current_time)

        assert agent.detection_events == 1
        assert detected_key not in [key.public_key for key in agent.replay_keys]
        assert len(agent.replay_keys) >= 5  # Should maintain minimum keys

    def test_update_state_collection_end(self) -> None:
        """Test state update when collection phase ends."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        agent.collection_end_time = current_time - 1  # Past time

        agent.update_state(current_time)

        assert agent.replay_active is True
        assert agent.collection_active is False

    def test_update_state_continuous_mode(self) -> None:
        """Test state update in continuous mode."""
        pattern = ReplayPattern(continuous_mode=True)
        agent = ReplayAttackerAgent("test_agent", replay_pattern=pattern)
        current_time = time.time()

        agent.attack_active = True  # Must be active
        agent.replay_active = True

        agent.update_state(current_time)

        assert agent.collection_active is True

    def test_process_event_replay(self) -> None:
        """Test event processing that triggers replay."""
        agent = ReplayAttackerAgent("test_agent")
        agent.simulation_engine = Mock()
        current_time = time.time()

        # Set up replay state
        agent.start_replay_phase(current_time)
        agent.events_to_replay = ["event1"]
        agent.next_replay_time = current_time - 1  # Past time

        # Add collected event
        keypair = NostrKeyPair.generate()
        original_event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test message",
            pubkey=keypair.public_key,
            created_at=int(current_time - 100),
        )
        agent.collected_events["event1"] = CollectedEvent(
            original_event=original_event,
            collection_time=current_time - 200,
        )

        event = Event(
            time=current_time,
            priority=1,
            event_type="test_event",
            data={},
        )

        agent.process_event(event)

        # Should have scheduled replay events
        assert agent.simulation_engine.schedule_event.called

    def test_process_event_collection(self) -> None:
        """Test event processing that triggers collection."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_collection_phase(current_time)

        keypair = NostrKeyPair.generate()
        nostr_event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test message",
            pubkey=keypair.public_key,
            created_at=int(current_time),
        )

        event = Event(
            time=current_time,
            priority=1,
            event_type="nostr_event",
            data={"event": nostr_event, "source_relay": "relay1"},
        )

        agent.on_event(event)

        assert len(agent.collected_events) == 1

    def test_get_attack_metrics(self) -> None:
        """Test getting attack metrics."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        agent.total_events_collected = 5
        agent.total_events_replayed = 3
        agent.total_amplifications = 10

        metrics = agent.get_attack_metrics()

        assert metrics["attack_active"] is True
        assert metrics["collection_active"] is True
        assert metrics["total_events_collected"] == 5
        assert metrics["total_events_replayed"] == 3
        assert metrics["total_amplifications"] == 10
        assert "active_replay_keys" in metrics
        assert "events_in_replay_queue" in metrics

    def test_on_activate(self) -> None:
        """Test agent activation."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.on_activate(current_time)

        assert agent.attack_active is True

    def test_on_deactivate(self) -> None:
        """Test agent deactivation."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        agent.on_deactivate(current_time)

        assert agent.attack_active is False

    def test_on_message_received_start_signal(self) -> None:
        """Test handling start replay coordination message."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        message = Mock()
        message.message_type = "coordination_signal"
        message.content = {"action": "start_replay"}
        message.timestamp = current_time

        agent.on_message_received(message)

        assert agent.attack_active is True

    def test_on_message_received_stop_signal(self) -> None:
        """Test handling stop replay coordination message."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)

        message = Mock()
        message.message_type = "coordination_signal"
        message.content = {"action": "stop_replay"}
        message.timestamp = current_time

        agent.on_message_received(message)

        assert agent.attack_active is False

    def test_prepare_replay_queue(self) -> None:
        """Test preparing replay queue."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        # Add some collected events
        for i in range(5):
            keypair = NostrKeyPair.generate()
            event = NostrEvent(
                kind=NostrEventKind.TEXT_NOTE,
                content=f"Message {i}",
                pubkey=keypair.public_key,
                created_at=int(current_time - 200),  # Old enough
            )
            agent.collected_events[f"event{i}"] = CollectedEvent(
                original_event=event,
                collection_time=current_time - 100,
            )

        agent._prepare_replay_queue(current_time)

        assert len(agent.events_to_replay) == 5

    def test_prepare_replay_queue_too_new(self) -> None:
        """Test preparing replay queue with events too new."""
        strategy = ReplayStrategy(min_event_age=300.0)  # 5 minutes
        pattern = ReplayPattern(strategy=strategy)
        agent = ReplayAttackerAgent("test_agent", replay_pattern=pattern)
        current_time = time.time()

        # Add recent event
        keypair = NostrKeyPair.generate()
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Recent message",
            pubkey=keypair.public_key,
            created_at=int(current_time - 10),  # Too recent
        )
        agent.collected_events["event1"] = CollectedEvent(
            original_event=event,
            collection_time=current_time - 10,
        )

        agent._prepare_replay_queue(current_time)

        assert len(agent.events_to_replay) == 0

    def test_perform_replay(self) -> None:
        """Test performing event replay."""
        agent = ReplayAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_replay_phase(current_time)
        agent.next_replay_time = current_time - 1  # Past time

        # Add collected event
        keypair = NostrKeyPair.generate()
        original_event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test message",
            pubkey=keypair.public_key,
            created_at=int(current_time - 100),
        )
        agent.collected_events["event1"] = CollectedEvent(
            original_event=original_event,
            collection_time=current_time - 200,
        )
        agent.events_to_replay = ["event1"]

        replayed_events = agent.perform_replay(current_time)

        assert len(replayed_events) > 0
        assert agent.total_events_replayed == 1
        assert agent.collected_events["event1"].replay_count > 0

    def test_perform_replay_with_amplification(self) -> None:
        """Test performing replay with amplification."""
        strategy = ReplayStrategy(amplification_factor=3)
        pattern = ReplayPattern(strategy=strategy)
        agent = ReplayAttackerAgent("test_agent", replay_pattern=pattern)
        current_time = time.time()

        agent.start_replay_phase(current_time)
        agent.next_replay_time = current_time - 1  # Past time

        # Add collected event
        keypair = NostrKeyPair.generate()
        original_event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content="Test message",
            pubkey=keypair.public_key,
            created_at=int(current_time - 100),
        )
        agent.collected_events["event1"] = CollectedEvent(
            original_event=original_event,
            collection_time=current_time - 200,
        )
        agent.events_to_replay = ["event1"]

        replayed_events = agent.perform_replay(current_time)

        assert len(replayed_events) == 3  # Amplification factor
        assert agent.total_amplifications == 3
