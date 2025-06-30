"""Tests for agent framework."""

from unittest.mock import Mock

import pytest

from ..simulation.events import Event
from .base import AgentManager, AgentState, AgentType, BaseAgent, Message


class TestAgent(BaseAgent):
    """Test agent implementation for testing."""

    def __init__(self, agent_id: str, simulation_engine: object = None) -> None:
        super().__init__(agent_id, AgentType.HONEST_USER, simulation_engine)
        self.handled_event_types = {"test_event", "message_delivery"}
        self.activation_called = False
        self.deactivation_called = False
        self.messages_received: list[Message] = []
        self.events_handled: list[Event] = []

    def on_activate(self, current_time: float) -> None:
        """Track activation."""
        self.activation_called = True

    def on_deactivate(self, current_time: float) -> None:
        """Track deactivation."""
        self.deactivation_called = True

    def on_message_received(self, message: Message) -> None:
        """Track received messages."""
        self.messages_received.append(message)

    def on_event(self, event: Event) -> list[Event]:
        """Track handled events."""
        self.events_handled.append(event)
        return []


class TestMessage:
    """Test Message class functionality."""

    def test_message_creation(self) -> None:
        """Test creating messages."""
        message = Message(
            message_type="test_message",
            sender_id="agent1",
            receiver_id="agent2",
            content={"data": "test"},
            timestamp=10.0,
        )

        assert message.message_type == "test_message"
        assert message.sender_id == "agent1"
        assert message.receiver_id == "agent2"
        assert message.content == {"data": "test"}
        assert message.timestamp == 10.0
        assert message.message_id is not None

    def test_message_with_custom_id(self) -> None:
        """Test creating message with custom ID."""
        custom_id = "custom_message_id"
        message = Message(
            message_type="test",
            sender_id="agent1",
            receiver_id="agent2",
            content={},
            timestamp=0.0,
            message_id=custom_id,
        )

        assert message.message_id == custom_id


class TestBaseAgent:
    """Test BaseAgent functionality."""

    def test_agent_initialization(self) -> None:
        """Test agent initialization."""
        agent = TestAgent("test_agent")

        assert agent.agent_id == "test_agent"
        assert agent.agent_type == AgentType.HONEST_USER
        assert agent.state == AgentState.INACTIVE
        assert len(agent.connections) == 0
        assert len(agent.message_queue) == 0

    def test_agent_lifecycle(self) -> None:
        """Test agent lifecycle state transitions."""
        agent = TestAgent("test_agent")
        current_time = 10.0

        # Test activation
        agent.activate(current_time)
        assert agent.state == AgentState.ACTIVE
        assert agent.is_active()
        assert agent.is_online()
        assert agent.activation_called
        assert agent.created_at == current_time

        # Test going offline
        agent.go_offline(current_time + 5)
        # Explicitly check the state to avoid mypy type narrowing issues
        offline_state = agent.state
        assert offline_state == AgentState.OFFLINE  # type: ignore[comparison-overlap]
        assert not agent.is_online()
        assert agent.is_offline()

        # Test going back online
        agent.go_online(current_time + 10)
        assert agent.state == AgentState.ACTIVE
        assert agent.is_online()
        assert not agent.is_offline()

        # Test deactivation
        agent.deactivate(current_time + 15)
        assert agent.state == AgentState.INACTIVE
        assert not agent.is_active()
        assert agent.deactivation_called

        # Test termination
        agent.terminate(current_time + 20)
        assert agent.state == AgentState.TERMINATED

    def test_agent_connections(self) -> None:
        """Test agent connection management."""
        agent = TestAgent("test_agent")

        # Test connecting to other agents
        agent.connect_to("agent2")
        agent.connect_to("agent3")

        assert agent.is_connected_to("agent2")
        assert agent.is_connected_to("agent3")
        assert not agent.is_connected_to("agent4")
        assert len(agent.connections) == 2

        # Test disconnecting
        agent.disconnect_from("agent2")
        assert not agent.is_connected_to("agent2")
        assert agent.is_connected_to("agent3")
        assert len(agent.connections) == 1

    def test_agent_properties(self) -> None:
        """Test agent property management."""
        agent = TestAgent("test_agent")

        # Test setting and getting properties
        agent.set_property("test_key", "test_value")
        assert agent.get_property("test_key") == "test_value"

        # Test getting non-existent property with default
        assert agent.get_property("non_existent", "default") == "default"
        assert agent.get_property("non_existent") is None

    def test_message_sending(self) -> None:
        """Test message sending functionality."""
        mock_engine = Mock()
        mock_engine.get_current_time.return_value = 10.0

        agent = TestAgent("sender", mock_engine)
        agent.activate(10.0)

        # Send a message
        agent.send_message(
            receiver_id="receiver",
            message_type="test_message",
            content={"data": "test"},
            delay=5.0,
        )

        # Verify simulation engine was called to schedule event
        mock_engine.schedule_event.assert_called_once()
        call_args = mock_engine.schedule_event.call_args
        assert call_args[1]["delay"] == 5.0
        assert call_args[1]["event_type"] == "message_delivery"

    def test_message_sending_while_offline(self) -> None:
        """Test that offline agents can't send messages."""
        mock_engine = Mock()
        agent = TestAgent("test_agent", mock_engine)
        agent.go_offline(10.0)

        # Try to send message while offline
        agent.send_message("receiver", "test_message", {})

        # Should not have called simulation engine
        mock_engine.schedule_event.assert_not_called()

    def test_message_receiving(self) -> None:
        """Test message receiving functionality."""
        agent = TestAgent("test_agent")
        agent.activate(10.0)

        message = Message(
            message_type="test_message",
            sender_id="sender",
            receiver_id="test_agent",
            content={"data": "test"},
            timestamp=10.0,
        )

        # Receive message while online
        agent.receive_message(message)
        assert len(agent.messages_received) == 1
        assert agent.messages_received[0] == message

    def test_message_queuing_while_offline(self) -> None:
        """Test that messages are queued when agent is offline."""
        agent = TestAgent("test_agent")
        agent.go_offline(10.0)

        message = Message(
            message_type="test_message",
            sender_id="sender",
            receiver_id="test_agent",
            content={"data": "test"},
            timestamp=10.0,
        )

        # Receive message while offline
        agent.receive_message(message)

        # Message should be queued, not processed
        assert len(agent.message_queue) == 1
        assert len(agent.messages_received) == 0

        # Go online and process queued messages
        agent.go_online(15.0)
        assert len(agent.message_queue) == 0
        assert len(agent.messages_received) == 1

    def test_event_handling(self) -> None:
        """Test event handling functionality."""
        agent = TestAgent("test_agent")
        agent.activate(10.0)

        event = Event(
            time=10.0, priority=0, event_type="test_event", data={"test": True}
        )

        # Test can_handle
        assert agent.can_handle("test_event")
        assert not agent.can_handle("unknown_event")

        # Handle event
        agent.handle_event(event)
        assert len(agent.events_handled) == 1
        assert agent.events_handled[0] == event

    def test_event_handling_while_offline(self) -> None:
        """Test that offline agents don't handle events."""
        agent = TestAgent("test_agent")
        agent.go_offline(10.0)

        event = Event(time=10.0, priority=0, event_type="test_event")

        # Should return empty list and not process event
        new_events = agent.handle_event(event)
        assert len(new_events) == 0
        assert len(agent.events_handled) == 0


class TestAgentManager:
    """Test AgentManager functionality."""

    def test_agent_registration(self) -> None:
        """Test registering agents."""
        manager = AgentManager()
        agent = TestAgent("test_agent")

        manager.register_agent(agent)

        assert manager.get_agent_count() == 1
        assert manager.get_agent("test_agent") == agent
        assert agent in manager.get_agents_by_type(AgentType.HONEST_USER)

    def test_duplicate_agent_registration(self) -> None:
        """Test that registering duplicate agent raises error."""
        manager = AgentManager()
        agent1 = TestAgent("test_agent")
        agent2 = TestAgent("test_agent")  # Same ID

        manager.register_agent(agent1)

        with pytest.raises(ValueError, match="already registered"):
            manager.register_agent(agent2)

    def test_agent_unregistration(self) -> None:
        """Test unregistering agents."""
        manager = AgentManager()
        agent = TestAgent("test_agent")

        manager.register_agent(agent)
        assert manager.get_agent_count() == 1

        # Unregister existing agent
        assert manager.unregister_agent("test_agent")
        assert manager.get_agent_count() == 0
        assert manager.get_agent("test_agent") is None

        # Unregister non-existent agent
        assert not manager.unregister_agent("non_existent")

    def test_get_agents_by_type(self) -> None:
        """Test getting agents by type."""
        manager = AgentManager()

        # Create agents of different types
        honest_agent = TestAgent("honest")
        malicious_agent = TestAgent("malicious")
        malicious_agent.agent_type = AgentType.MALICIOUS_USER

        manager.register_agent(honest_agent)
        manager.register_agent(malicious_agent)

        honest_agents = manager.get_agents_by_type(AgentType.HONEST_USER)
        malicious_agents = manager.get_agents_by_type(AgentType.MALICIOUS_USER)

        assert len(honest_agents) == 1
        assert len(malicious_agents) == 1
        assert honest_agent in honest_agents
        assert malicious_agent in malicious_agents

    def test_activate_all_agents(self) -> None:
        """Test activating all agents."""
        manager = AgentManager()

        agent1 = TestAgent("agent1")
        agent2 = TestAgent("agent2")

        manager.register_agent(agent1)
        manager.register_agent(agent2)

        manager.activate_all_agents(10.0)

        assert agent1.is_active()
        assert agent2.is_active()
        assert agent1.activation_called
        assert agent2.activation_called

    def test_terminate_all_agents(self) -> None:
        """Test terminating all agents."""
        manager = AgentManager()

        agent1 = TestAgent("agent1")
        agent2 = TestAgent("agent2")
        agent1.activate(10.0)
        agent2.activate(10.0)

        manager.register_agent(agent1)
        manager.register_agent(agent2)

        manager.terminate_all_agents(20.0)

        assert agent1.state == AgentState.TERMINATED
        assert agent2.state == AgentState.TERMINATED

    def test_get_active_agents(self) -> None:
        """Test getting only active agents."""
        manager = AgentManager()

        agent1 = TestAgent("agent1")
        agent2 = TestAgent("agent2")
        agent3 = TestAgent("agent3")

        agent1.activate(10.0)
        agent2.activate(10.0)
        # agent3 remains inactive

        manager.register_agent(agent1)
        manager.register_agent(agent2)
        manager.register_agent(agent3)

        active_agents = manager.get_active_agents()
        assert len(active_agents) == 2
        assert agent1 in active_agents
        assert agent2 in active_agents
        assert agent3 not in active_agents

    def test_get_online_agents(self) -> None:
        """Test getting only online agents."""
        manager = AgentManager()

        agent1 = TestAgent("agent1")
        agent2 = TestAgent("agent2")
        agent3 = TestAgent("agent3")

        agent1.activate(10.0)
        agent2.activate(10.0)
        agent2.go_offline(15.0)  # Take agent2 offline
        agent3.activate(10.0)

        manager.register_agent(agent1)
        manager.register_agent(agent2)
        manager.register_agent(agent3)

        online_agents = manager.get_online_agents()
        assert len(online_agents) == 2
        assert agent1 in online_agents
        assert agent2 not in online_agents  # offline
        assert agent3 in online_agents


if __name__ == "__main__":
    pytest.main([__file__])
