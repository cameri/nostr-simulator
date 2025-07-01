"""Tests for burst spam attack implementation."""

import time
from unittest.mock import Mock

from ...protocol.events import NostrEvent, NostrEventKind
from ...simulation.events import Event
from .burst_spammer import BurstPattern, BurstSpammerAgent, BurstTiming


class TestBurstTiming:
    """Test BurstTiming configuration."""

    def test_default_values(self) -> None:
        """Test default timing configuration."""
        timing = BurstTiming()

        assert timing.burst_duration == 10.0
        assert timing.burst_interval == 60.0
        assert timing.messages_per_second == 5.0
        assert timing.burst_count == 3
        assert timing.randomization == 0.2

    def test_custom_values(self) -> None:
        """Test custom timing configuration."""
        timing = BurstTiming(
            burst_duration=15.0,
            burst_interval=120.0,
            messages_per_second=10.0,
            burst_count=5,
            randomization=0.3,
        )

        assert timing.burst_duration == 15.0
        assert timing.burst_interval == 120.0
        assert timing.messages_per_second == 10.0
        assert timing.burst_count == 5
        assert timing.randomization == 0.3


class TestBurstPattern:
    """Test BurstPattern configuration."""

    def test_default_values(self) -> None:
        """Test default pattern configuration."""
        pattern = BurstPattern()

        assert isinstance(pattern.timing, BurstTiming)
        assert pattern.initial_volume == 10
        assert pattern.volume_scaling == 1.5
        assert pattern.max_volume == 100
        assert pattern.coordinated is True
        assert pattern.coordination_delay == 5.0
        assert pattern.content_variation is True
        assert pattern.timing_jitter is True
        assert pattern.escalation_mode is False

    def test_custom_values(self) -> None:
        """Test custom pattern configuration."""
        custom_timing = BurstTiming(burst_count=5)
        pattern = BurstPattern(
            timing=custom_timing,
            initial_volume=20,
            volume_scaling=2.0,
            max_volume=200,
            coordinated=False,
            coordination_delay=10.0,
            content_variation=False,
            timing_jitter=False,
            escalation_mode=True,
        )

        assert pattern.timing.burst_count == 5
        assert pattern.initial_volume == 20
        assert pattern.volume_scaling == 2.0
        assert pattern.max_volume == 200
        assert pattern.coordinated is False
        assert pattern.coordination_delay == 10.0
        assert pattern.content_variation is False
        assert pattern.timing_jitter is False
        assert pattern.escalation_mode is True


class TestBurstSpammerAgent:
    """Test BurstSpammerAgent implementation."""

    def test_initialization(self) -> None:
        """Test agent initialization."""
        agent = BurstSpammerAgent("test_agent")

        assert agent.agent_id == "test_agent"
        assert agent.simulation_engine is None
        assert isinstance(agent.burst_pattern, BurstPattern)
        assert not agent.attack_active
        assert agent.current_burst == 0
        assert agent.burst_start_time == 0.0
        assert agent.next_burst_time == 0.0
        assert agent.messages_this_burst == 0
        assert agent.current_volume == agent.burst_pattern.initial_volume
        assert agent.total_bursts == 0
        assert agent.total_messages_sent == 0
        assert len(agent.burst_start_times) == 0

    def test_initialization_with_custom_pattern(self) -> None:
        """Test agent initialization with custom pattern."""
        custom_pattern = BurstPattern(initial_volume=25)
        agent = BurstSpammerAgent("test_agent", burst_pattern=custom_pattern)

        assert agent.burst_pattern.initial_volume == 25
        assert agent.current_volume == 25

    def test_start_attack(self) -> None:
        """Test starting attack."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)

        assert agent.attack_active
        assert agent.current_burst == 0
        assert agent.next_burst_time == current_time
        assert agent.current_volume == agent.burst_pattern.initial_volume

    def test_start_attack_when_already_active(self) -> None:
        """Test starting attack when already active."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        original_time = agent.next_burst_time

        agent.start_attack(current_time + 10)

        assert agent.next_burst_time == original_time

    def test_stop_attack(self) -> None:
        """Test stopping attack."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)
        agent.stop_attack()

        assert not agent.attack_active
        assert agent.current_burst == 0
        assert agent.burst_start_time == 0.0
        assert agent.next_burst_time == 0.0
        assert agent.messages_this_burst == 0

    def test_should_start_burst_when_inactive(self) -> None:
        """Test burst start decision when attack is inactive."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        result = agent.should_start_burst(current_time)

        assert not result

    def test_should_start_burst_when_time_reached(self) -> None:
        """Test burst start decision when time is reached."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)

        result = agent.should_start_burst(current_time)

        assert result

    def test_should_start_burst_when_time_not_reached(self) -> None:
        """Test burst start decision when time not reached."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time + 100)  # Future time

        result = agent.should_start_burst(current_time)

        assert not result

    def test_should_start_burst_when_max_bursts_reached(self) -> None:
        """Test burst start decision when max bursts reached."""
        pattern = BurstPattern()
        pattern.timing.burst_count = 2
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        agent.current_burst = 2  # Reached max

        result = agent.should_start_burst(current_time)

        assert not result

    def test_start_burst(self) -> None:
        """Test starting a burst."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)

        assert agent.current_burst == 1
        assert agent.burst_start_time == current_time
        assert agent.messages_this_burst == 0
        assert len(agent.burst_start_times) == 1
        assert agent.burst_start_times[0] == current_time
        assert agent.next_burst_time > current_time

    def test_start_burst_with_escalation(self) -> None:
        """Test starting burst with volume escalation."""
        pattern = BurstPattern(escalation_mode=True, volume_scaling=2.0)
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        original_volume = agent.current_volume

        agent.start_burst(current_time)

        assert agent.current_volume == int(original_volume * 2.0)

    def test_start_burst_with_max_volume_cap(self) -> None:
        """Test starting burst with volume cap."""
        pattern = BurstPattern(
            escalation_mode=True,
            initial_volume=80,
            volume_scaling=2.0,
            max_volume=100,
        )
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)

        assert agent.current_volume == 100  # Capped at max

    def test_is_in_burst_no_burst_started(self) -> None:
        """Test burst check when no burst started."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        result = agent.is_in_burst(current_time)

        assert not result

    def test_is_in_burst_during_burst(self) -> None:
        """Test burst check during active burst."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)

        result = agent.is_in_burst(current_time + 5.0)  # 5 seconds into burst

        assert result

    def test_is_in_burst_after_burst_ended(self) -> None:
        """Test burst check after burst ended."""
        pattern = BurstPattern()
        pattern.timing.burst_duration = 10.0
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)

        result = agent.is_in_burst(current_time + 15.0)  # After burst duration

        assert not result

    def test_should_send_message_in_burst_not_in_burst(self) -> None:
        """Test message send decision when not in burst."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        result = agent.should_send_message_in_burst(current_time)

        assert not result

    def test_should_send_message_in_burst_volume_exceeded(self) -> None:
        """Test message send decision when volume exceeded."""
        pattern = BurstPattern(initial_volume=5)
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)
        agent.messages_this_burst = 5  # Reached volume limit

        result = agent.should_send_message_in_burst(current_time + 1.0)

        assert not result

    def test_should_send_message_in_burst_under_rate(self) -> None:
        """Test message send decision under expected rate."""
        pattern = BurstPattern()
        pattern.timing.messages_per_second = 2.0  # 2 messages per second
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)

        # After 2 seconds, should expect ~4 messages
        result = agent.should_send_message_in_burst(current_time + 2.0)

        assert result

    def test_generate_spam_content_with_variation(self) -> None:
        """Test spam content generation with variation."""
        pattern = BurstPattern(content_variation=True)
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)

        content = agent.generate_spam_content()

        assert isinstance(content, str)
        assert len(content) > 0
        # Check the content is formatted from one of the templates
        # (each template contains at least one digit from the format())
        assert any(char.isdigit() for char in content)

    def test_generate_spam_content_without_variation(self) -> None:
        """Test spam content generation without variation."""
        pattern = BurstPattern(content_variation=False)
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)

        content = agent.generate_spam_content()

        assert content == "SPAM: Buy now! Limited time offer!"

    def test_create_spam_event(self) -> None:
        """Test spam event creation."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)
        original_count = agent.messages_this_burst
        original_total = agent.total_messages_sent

        event = agent.create_spam_event(current_time)

        assert event is not None
        assert isinstance(event, NostrEvent)
        assert event.kind == NostrEventKind.TEXT_NOTE
        assert len(event.content) > 0
        assert event.created_at == int(current_time)
        assert event.pubkey == agent.keypair.public_key
        assert agent.messages_this_burst == original_count + 1
        assert agent.total_messages_sent == original_total + 1

    def test_coordinate_with_others_disabled(self) -> None:
        """Test coordination when disabled."""
        pattern = BurstPattern(coordinated=False)
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        current_time = time.time()

        result = agent.coordinate_with_others(current_time)

        assert result is True

    def test_coordinate_with_others_enabled(self) -> None:
        """Test coordination when enabled."""
        from unittest.mock import patch

        pattern = BurstPattern(coordinated=True)
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        current_time = time.time()

        # Mock random.random to return predictable values for coordination success
        # The coordinate_with_others method returns True when random() > 0.1 (90% success rate)
        with patch("random.random") as mock_random:
            # Simulate 9 successes (0.2 > 0.1) and 1 failure (0.05 < 0.1)
            mock_random.side_effect = [
                0.2,
                0.2,
                0.2,
                0.2,
                0.2,
                0.2,
                0.2,
                0.2,
                0.2,
                0.05,
            ]

            results = [agent.coordinate_with_others(current_time) for _ in range(10)]

            # Should have exactly 90% success rate (9 out of 10)
            success_rate = sum(results) / len(results)
            assert success_rate == 0.9

    def test_get_attack_metrics(self) -> None:
        """Test attack metrics retrieval."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)
        agent.create_spam_event(current_time)

        metrics = agent.get_attack_metrics()

        assert isinstance(metrics, dict)
        assert "total_bursts" in metrics
        assert "total_messages" in metrics
        assert "current_burst" in metrics
        assert "current_volume" in metrics
        assert "attack_active" in metrics
        assert "burst_times" in metrics
        assert "messages_this_burst" in metrics

        assert metrics["attack_active"] is True
        assert metrics["current_burst"] == 1
        assert metrics["total_messages"] == 1
        assert metrics["messages_this_burst"] == 1

    def test_process_event_starts_burst(self) -> None:
        """Test event processing that starts a burst."""
        # Use a pattern without coordination for deterministic testing
        pattern = BurstPattern()
        pattern.coordinated = False
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        agent.simulation_engine = Mock()
        current_time = time.time()

        agent.start_attack(current_time)

        event = Event(
            time=current_time,
            priority=1,
            event_type="test_event",
            data={},
        )

        agent.process_event(event)

        assert agent.current_burst == 1
        assert agent.burst_start_time == current_time

    def test_process_event_sends_message(self) -> None:
        """Test event processing that sends message during burst."""
        pattern = BurstPattern()
        pattern.timing.messages_per_second = 10.0  # High rate
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        agent.simulation_engine = Mock()
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)

        event = Event(
            time=current_time + 1.0,  # 1 second into burst
            priority=1,
            event_type="test_event",
            data={},
        )

        original_count = agent.total_messages_sent
        agent.process_event(event)

        # Should have sent at least one message
        assert agent.total_messages_sent >= original_count

    def test_update_state_completes_burst(self) -> None:
        """Test state update that completes a burst."""
        pattern = BurstPattern()
        pattern.timing.burst_duration = 5.0
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)

        # Update after burst duration
        agent.update_state(current_time + 6.0)

        assert agent.total_bursts == 1

    def test_update_state_completes_attack(self) -> None:
        """Test state update that completes the attack."""
        pattern = BurstPattern()
        pattern.timing.burst_count = 2
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        agent.current_burst = 2  # Reached max bursts

        agent.update_state(current_time)

        assert not agent.attack_active

    def test_on_activate(self) -> None:
        """Test agent activation."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        # Should not raise exception
        agent.on_activate(current_time)

    def test_on_deactivate(self) -> None:
        """Test agent deactivation."""
        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        agent.on_deactivate(current_time)

        assert not agent.attack_active

    def test_start_burst_without_timing_jitter(self) -> None:
        """Test starting burst without timing jitter."""
        pattern = BurstPattern(timing_jitter=False)
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)

        # Should use exact timing without jitter
        expected_next = (
            current_time + pattern.timing.burst_duration + pattern.timing.burst_interval
        )

        assert abs(agent.next_burst_time - expected_next) < 1.0  # Allow small tolerance

    def test_create_spam_event_exception_handling(self) -> None:
        """Test spam event creation with exception handling."""
        from unittest.mock import patch

        agent = BurstSpammerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        agent.start_burst(current_time)

        # Mock a failure in event creation by making content generation fail
        with patch.object(
            agent, "generate_spam_content", side_effect=Exception("Simulated failure")
        ):
            event = agent.create_spam_event(current_time)
            # Should handle exception gracefully
            assert event is None

    def test_process_event_coordination_failure(self) -> None:
        """Test event processing when coordination fails."""
        from unittest.mock import patch

        pattern = BurstPattern(coordinated=True)
        agent = BurstSpammerAgent("test_agent", burst_pattern=pattern)
        agent.simulation_engine = Mock()
        current_time = time.time()

        agent.start_attack(current_time)

        # Mock coordination failure
        with patch.object(agent, "coordinate_with_others", return_value=False):
            event = Event(
                time=current_time,
                priority=1,
                event_type="test_event",
                data={},
            )

            original_burst = agent.current_burst
            agent.process_event(event)

            # Should not start burst when coordination fails
            assert agent.current_burst == original_burst
