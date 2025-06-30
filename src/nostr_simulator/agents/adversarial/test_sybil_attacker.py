"""Tests for sybil attacker agent."""

import time
from unittest.mock import Mock

from ...protocol.events import NostrEvent, NostrEventKind
from ...protocol.keys import NostrKeyPair
from ...simulation.events import Event
from ..base import AgentType
from .sybil_attacker import SybilAttackerAgent, SybilAttackPattern, SybilIdentity


class TestSybilIdentity:
    """Test SybilIdentity dataclass."""

    def test_sybil_identity_creation(self) -> None:
        """Test creating a sybil identity."""
        private_key = NostrKeyPair.generate()
        current_time = time.time()

        identity = SybilIdentity(
            identity_id="test_identity",
            private_key=private_key,
            public_key=private_key.public_key,
            creation_time=current_time,
            last_active=current_time,
        )

        assert identity.identity_id == "test_identity"
        assert identity.private_key == private_key
        assert identity.public_key == private_key.public_key
        assert identity.creation_time == current_time
        assert identity.last_active == current_time
        assert identity.message_count == 0
        assert not identity.dormant

    def test_sybil_identity_auto_public_key(self) -> None:
        """Test automatic public key derivation."""
        private_key = NostrKeyPair.generate()
        current_time = time.time()

        identity = SybilIdentity(
            identity_id="test_identity",
            private_key=private_key,
            public_key="",  # Empty, should be auto-derived
            creation_time=current_time,
            last_active=current_time,
        )

        assert identity.public_key == private_key.public_key


class TestSybilAttackPattern:
    """Test SybilAttackPattern configuration."""

    def test_default_pattern(self) -> None:
        """Test default attack pattern values."""
        pattern = SybilAttackPattern()

        assert pattern.identity_count == 10
        assert pattern.identity_creation_rate == 1.0
        assert pattern.identity_switching_frequency == 5.0
        assert pattern.spam_frequency == 10.0
        assert pattern.coordinated_timing is True
        assert pattern.burst_mode is False
        assert pattern.behavior_variation == 0.3
        assert pattern.dormancy_periods is True
        assert pattern.mimetic_behavior is True

    def test_custom_pattern(self) -> None:
        """Test custom attack pattern values."""
        pattern = SybilAttackPattern(
            identity_count=5,
            spam_frequency=20.0,
            coordinated_timing=False,
            behavior_variation=0.5,
        )

        assert pattern.identity_count == 5
        assert pattern.spam_frequency == 20.0
        assert pattern.coordinated_timing is False
        assert pattern.behavior_variation == 0.5


class TestSybilAttackerAgent:
    """Test SybilAttackerAgent implementation."""

    def test_init(self) -> None:
        """Test agent initialization."""
        agent = SybilAttackerAgent("test_agent")

        assert agent.agent_id == "test_agent"
        assert agent.agent_type == AgentType.MALICIOUS_USER
        assert isinstance(agent.attack_pattern, SybilAttackPattern)
        assert len(agent.identities) == 0
        assert agent.active_identity is None
        assert not agent.attack_active
        assert agent.total_messages_sent == 0

    def test_init_with_custom_pattern(self) -> None:
        """Test agent initialization with custom attack pattern."""
        pattern = SybilAttackPattern(identity_count=5, spam_frequency=20.0)
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)

        assert agent.attack_pattern.identity_count == 5
        assert agent.attack_pattern.spam_frequency == 20.0

    def test_initialize_identities(self) -> None:
        """Test identity initialization."""
        pattern = SybilAttackPattern(identity_count=3)
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.initialize_identities(current_time)

        assert len(agent.identities) == 3
        assert agent.active_identity is not None

        # Check identity structure
        for identity in agent.identities.values():
            assert identity.identity_id.startswith("test_agent_identity_")
            assert identity.private_key is not None
            assert len(identity.public_key) > 0
            assert identity.creation_time == current_time
            assert identity.message_count == 0
            assert not identity.dormant

    def test_start_attack(self) -> None:
        """Test starting the attack."""
        agent = SybilAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)

        assert agent.attack_active
        assert len(agent.identities) > 0
        assert agent.active_identity is not None
        assert agent.last_identity_switch == current_time

    def test_stop_attack(self) -> None:
        """Test stopping the attack."""
        agent = SybilAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        assert agent.attack_active

        agent.stop_attack()
        assert not agent.attack_active

    def test_switch_identity(self) -> None:
        """Test identity switching."""
        pattern = SybilAttackPattern(identity_count=3)
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.initialize_identities(current_time)
        original_identity = agent.active_identity

        agent.switch_identity(current_time)

        # Should switch to different identity
        assert agent.active_identity != original_identity
        assert agent.last_identity_switch == current_time

    def test_switch_identity_with_dormant(self) -> None:
        """Test identity switching when some identities are dormant."""
        pattern = SybilAttackPattern(identity_count=2)
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.initialize_identities(current_time)

        # Make one identity dormant
        identities = list(agent.identities.values())
        identities[0].dormant = True

        agent.switch_identity(current_time)

        # Should switch to non-dormant identity
        assert agent.active_identity is not None
        assert not agent.active_identity.dormant

    def test_add_identity(self) -> None:
        """Test adding new identity."""
        agent = SybilAttackerAgent("test_agent")
        current_time = time.time()

        identity = agent.add_identity(current_time)

        assert identity.identity_id in agent.identities
        assert identity.creation_time == current_time
        assert not identity.dormant

    def test_remove_identity(self) -> None:
        """Test removing identity."""
        pattern = SybilAttackPattern(identity_count=2)
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.initialize_identities(current_time)
        identity_id = list(agent.identities.keys())[0]

        result = agent.remove_identity(identity_id)

        assert result
        assert identity_id not in agent.identities
        assert len(agent.identities) == 1

    def test_remove_active_identity(self) -> None:
        """Test removing the currently active identity."""
        pattern = SybilAttackPattern(identity_count=2)
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.initialize_identities(current_time)
        assert agent.active_identity is not None
        active_identity_id = agent.active_identity.identity_id

        result = agent.remove_identity(active_identity_id)

        assert result
        assert active_identity_id not in agent.identities
        assert agent.active_identity is not None  # Should switch to remaining identity

    def test_remove_nonexistent_identity(self) -> None:
        """Test removing non-existent identity."""
        agent = SybilAttackerAgent("test_agent")

        result = agent.remove_identity("nonexistent")

        assert not result

    def test_coordinate_with_identity(self) -> None:
        """Test identity coordination."""
        agent = SybilAttackerAgent("test_agent")

        agent.coordinate_with_identity("identity_1")
        agent.coordinate_with_identity("identity_2")

        assert "identity_1" in agent.coordinated_identities
        assert "identity_2" in agent.coordinated_identities

    def test_generate_spam_content(self) -> None:
        """Test spam content generation."""
        agent = SybilAttackerAgent("test_agent")

        content = agent.generate_spam_content()

        assert len(content) > 0
        assert isinstance(content, str)

        # Generate multiple to ensure variety
        contents = [agent.generate_spam_content() for _ in range(10)]
        assert len(set(contents)) > 1  # Should have some variety

    def test_should_send_message_when_inactive(self) -> None:
        """Test message sending decision when attack is inactive."""
        agent = SybilAttackerAgent("test_agent")
        current_time = time.time()

        result = agent.should_send_message(current_time)

        assert not result

    def test_should_send_message_when_active(self) -> None:
        """Test message sending decision when attack is active."""
        pattern = SybilAttackPattern(spam_frequency=3600.0)  # 1 message per second
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        agent.last_message_time = current_time - 2.0  # 2 seconds ago

        result = agent.should_send_message(current_time)

        assert result

    def test_should_send_message_too_soon(self) -> None:
        """Test message sending when it's too soon since last message."""
        pattern = SybilAttackPattern(spam_frequency=10.0)  # 6 seconds between messages
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        agent.last_message_time = current_time - 1.0  # 1 second ago

        result = agent.should_send_message(current_time)

        assert not result

    def test_should_send_message_dormant_identity(self) -> None:
        """Test message sending with dormant active identity."""
        agent = SybilAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        assert agent.active_identity is not None
        agent.active_identity.dormant = True

        result = agent.should_send_message(current_time)

        assert not result

    def test_should_switch_identity(self) -> None:
        """Test identity switching decision."""
        pattern = SybilAttackPattern(
            identity_count=2, identity_switching_frequency=1.0
        )  # 1 minute
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.initialize_identities(current_time)
        agent.last_identity_switch = current_time - 120.0  # 2 minutes ago

        result = agent.should_switch_identity(current_time)

        assert result

    def test_should_switch_identity_too_soon(self) -> None:
        """Test identity switching when it's too soon."""
        pattern = SybilAttackPattern(
            identity_count=2, identity_switching_frequency=5.0
        )  # 5 minutes
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.initialize_identities(current_time)
        agent.last_identity_switch = current_time - 60.0  # 1 minute ago

        result = agent.should_switch_identity(current_time)

        assert not result

    def test_should_switch_identity_single_identity(self) -> None:
        """Test identity switching with only one identity."""
        pattern = SybilAttackPattern(identity_count=1)
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.initialize_identities(current_time)

        result = agent.should_switch_identity(current_time)

        assert not result

    def test_create_spam_event(self) -> None:
        """Test spam event creation."""
        agent = SybilAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        assert agent.active_identity is not None
        original_count = agent.active_identity.message_count

        event = agent.create_spam_event(current_time)

        assert event is not None
        assert isinstance(event, NostrEvent)
        assert event.kind == NostrEventKind.TEXT_NOTE
        assert len(event.content) > 0
        assert event.created_at == int(current_time)
        assert event.pubkey == agent.active_identity.public_key
        assert agent.active_identity.message_count == original_count + 1
        assert agent.active_identity.last_active == current_time

    def test_create_spam_event_no_active_identity(self) -> None:
        """Test spam event creation with no active identity."""
        agent = SybilAttackerAgent("test_agent")
        current_time = time.time()

        event = agent.create_spam_event(current_time)

        assert event is None

    def test_activate_dormancy(self) -> None:
        """Test putting identity into dormancy."""
        agent = SybilAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        assert agent.active_identity is not None
        identity_id = agent.active_identity.identity_id

        agent.activate_dormancy(identity_id)

        assert agent.identities[identity_id].dormant
        # Should switch away from dormant identity
        assert agent.active_identity is not None
        assert agent.active_identity.identity_id != identity_id

    def test_reactivate_identity(self) -> None:
        """Test reactivating dormant identity."""
        agent = SybilAttackerAgent("test_agent")
        current_time = time.time()

        agent.start_attack(current_time)
        identity_id = list(agent.identities.keys())[0]

        agent.activate_dormancy(identity_id)
        assert agent.identities[identity_id].dormant

        agent.reactivate_identity(identity_id)
        assert not agent.identities[identity_id].dormant

    def test_handle_detection(self) -> None:
        """Test handling identity detection."""
        pattern = SybilAttackPattern(identity_count=2)
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        identity_id = list(agent.identities.keys())[0]
        original_count = len(agent.identities)

        agent.handle_detection(identity_id, current_time)

        assert agent.detection_events == 1
        assert agent.identities[identity_id].dormant
        # Should create new identity to replace detected one
        assert len(agent.identities) >= original_count

    def test_handle_detection_nonexistent(self) -> None:
        """Test handling detection of non-existent identity."""
        agent = SybilAttackerAgent("test_agent")
        current_time = time.time()

        agent.handle_detection("nonexistent", current_time)

        assert agent.detection_events == 1

    def test_get_attack_metrics(self) -> None:
        """Test getting attack metrics."""
        pattern = SybilAttackPattern(identity_count=3)
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)

        # Make one identity dormant and add some messages
        identity_id = list(agent.identities.keys())[0]
        agent.handle_detection(
            identity_id, current_time
        )  # This should increment detection_events
        agent.identities[list(agent.identities.keys())[1]].message_count = 5

        metrics = agent.get_attack_metrics()

        assert metrics["total_identities"] == 3
        assert metrics["active_identities"] == 2
        assert metrics["dormant_identities"] == 1
        assert metrics["total_messages_sent"] >= 5
        assert metrics["detection_events"] == 1
        assert metrics["attack_active"] is True

    def test_process_event_switches_identity(self) -> None:
        """Test event processing that triggers identity switch."""
        pattern = SybilAttackPattern(
            identity_count=2, identity_switching_frequency=0.01
        )  # Very short
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        current_time = time.time()

        agent.start_attack(current_time)
        original_identity = agent.active_identity

        # Create event with time that should trigger switch
        event = Event(
            time=current_time + 120,  # 2 minutes later
            priority=1,
            event_type="test_event",
            data={},
        )

        agent.process_event(event)

        # Identity should have switched
        assert agent.active_identity is not None
        assert agent.active_identity != original_identity

    def test_process_event_sends_message(self) -> None:
        """Test event processing that triggers message sending."""
        pattern = SybilAttackPattern(spam_frequency=3600.0)  # Very frequent
        agent = SybilAttackerAgent("test_agent", attack_pattern=pattern)
        agent.simulation_engine = Mock()
        current_time = time.time()

        agent.start_attack(current_time)
        agent.last_message_time = current_time - 10.0  # Long enough ago

        event = Event(
            time=current_time,
            priority=1,
            event_type="test_event",
            data={},
        )

        original_count = agent.total_messages_sent
        agent.process_event(event)

        assert agent.total_messages_sent > original_count
        assert agent.last_message_time == current_time

    def test_update_state(self) -> None:
        """Test state update."""
        agent = SybilAttackerAgent("test_agent")
        current_time = time.time()

        # Start with no identities
        agent.attack_active = True
        agent.update_state(current_time)

        # Should initialize identities
        assert len(agent.identities) > 0

    def test_update_state_inactive(self) -> None:
        """Test state update when attack is inactive."""
        agent = SybilAttackerAgent("test_agent")
        current_time = time.time()

        agent.update_state(current_time)

        # Should not initialize identities when inactive
        assert len(agent.identities) == 0
