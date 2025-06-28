"""Base agent classes for the simulation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from uuid import uuid4

from ..logging_config import get_logger
from ..simulation.events import Event, EventHandler


class AgentState(Enum):
    """Agent lifecycle states."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    OFFLINE = "offline"
    TERMINATED = "terminated"


class AgentType(Enum):
    """Types of agents in the simulation."""

    HONEST_USER = "honest_user"
    MALICIOUS_USER = "malicious_user"
    RELAY = "relay"
    CLIENT = "client"
    USER = "user"


class Message:
    """Represents a message between agents."""

    def __init__(
        self,
        message_type: str,
        sender_id: str,
        receiver_id: str,
        content: dict[str, Any],
        timestamp: float,
        message_id: str | None = None,
    ) -> None:
        """Initialize a message.

        Args:
            message_type: Type of the message.
            sender_id: ID of the sending agent.
            receiver_id: ID of the receiving agent.
            content: Message content.
            timestamp: Message timestamp.
            message_id: Unique message ID.
        """
        self.message_id = message_id or str(uuid4())
        self.message_type = message_type
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.content = content
        self.timestamp = timestamp


class BaseAgent(EventHandler, ABC):
    """Abstract base class for all agents in the simulation."""

    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        simulation_engine: Any = None,  # Avoid circular import
    ) -> None:
        """Initialize the base agent.

        Args:
            agent_id: Unique identifier for the agent.
            agent_type: Type of the agent.
            simulation_engine: Reference to the simulation engine.
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.simulation_engine = simulation_engine
        self.logger = get_logger(f"{__name__}.{agent_type.value}.{agent_id}")

        # Agent state
        self.state = AgentState.INACTIVE
        self.created_at = 0.0
        self.last_activity = 0.0

        # Agent properties
        self.properties: dict[str, Any] = {}

        # Communication
        self.connections: set[str] = set()
        self.message_queue: list[Message] = []

        # Event handling
        self.handled_event_types: set[str] = set()

        self.logger.debug(f"Created agent {agent_id} of type {agent_type.value}")

    def activate(self, current_time: float) -> None:
        """Activate the agent.

        Args:
            current_time: Current simulation time.
        """
        if self.state == AgentState.INACTIVE:
            self.state = AgentState.ACTIVE
            self.created_at = current_time
            self.last_activity = current_time
            self.on_activate(current_time)
            self.logger.info(f"Agent {self.agent_id} activated at time {current_time}")

    def deactivate(self, current_time: float) -> None:
        """Deactivate the agent.

        Args:
            current_time: Current simulation time.
        """
        if self.state == AgentState.ACTIVE:
            self.state = AgentState.INACTIVE
            self.on_deactivate(current_time)
            self.logger.info(
                f"Agent {self.agent_id} deactivated at time {current_time}"
            )

    def go_offline(self, current_time: float) -> None:
        """Take the agent offline.

        Args:
            current_time: Current simulation time.
        """
        if self.state == AgentState.ACTIVE:
            self.state = AgentState.OFFLINE
            self.on_go_offline(current_time)
            self.logger.info(
                f"Agent {self.agent_id} went offline at time {current_time}"
            )

    def go_online(self, current_time: float) -> None:
        """Bring the agent online.

        Args:
            current_time: Current simulation time.
        """
        if self.state == AgentState.OFFLINE:
            self.state = AgentState.ACTIVE
            self.last_activity = current_time
            self.on_go_online(current_time)
            self.logger.info(
                f"Agent {self.agent_id} came online at time {current_time}"
            )

    def terminate(self, current_time: float) -> None:
        """Terminate the agent.

        Args:
            current_time: Current simulation time.
        """
        self.state = AgentState.TERMINATED
        self.on_terminate(current_time)
        self.logger.info(f"Agent {self.agent_id} terminated at time {current_time}")

    def is_active(self) -> bool:
        """Check if agent is active.

        Returns:
            True if agent is active.
        """
        return self.state == AgentState.ACTIVE

    def is_online(self) -> bool:
        """Check if agent is online.

        Returns:
            True if agent is online (active and not offline).
        """
        return self.state == AgentState.ACTIVE

    def is_offline(self) -> bool:
        """Check if agent is offline.

        Returns:
            True if agent is offline.
        """
        return self.state == AgentState.OFFLINE

    def connect_to(self, other_agent_id: str) -> None:
        """Establish a connection to another agent.

        Args:
            other_agent_id: ID of the agent to connect to.
        """
        self.connections.add(other_agent_id)
        self.logger.debug(f"Connected to agent {other_agent_id}")

    def disconnect_from(self, other_agent_id: str) -> None:
        """Remove connection to another agent.

        Args:
            other_agent_id: ID of the agent to disconnect from.
        """
        self.connections.discard(other_agent_id)
        self.logger.debug(f"Disconnected from agent {other_agent_id}")

    def is_connected_to(self, other_agent_id: str) -> bool:
        """Check if connected to another agent.

        Args:
            other_agent_id: ID of the agent to check.

        Returns:
            True if connected to the agent.
        """
        return other_agent_id in self.connections

    def send_message(
        self,
        receiver_id: str,
        message_type: str,
        content: dict[str, Any],
        delay: float = 0.0,
    ) -> None:
        """Send a message to another agent.

        Args:
            receiver_id: ID of the receiving agent.
            message_type: Type of the message.
            content: Message content.
            delay: Delay before message delivery.
        """
        if not self.is_online():
            self.logger.warning("Cannot send message while offline")
            return

        if self.simulation_engine:
            current_time = self.simulation_engine.get_current_time()
            message = Message(
                message_type=message_type,
                sender_id=self.agent_id,
                receiver_id=receiver_id,
                content=content,
                timestamp=current_time,
            )

            # Schedule message delivery
            self.simulation_engine.schedule_event(
                delay=delay,
                event_type="message_delivery",
                data={
                    "message": message,
                    "sender_id": self.agent_id,
                    "receiver_id": receiver_id,
                },
                source_id=self.agent_id,
                target_id=receiver_id,
            )

            self.logger.debug(
                f"Scheduled message {message.message_id} to {receiver_id} "
                f"for delivery at time {current_time + delay}"
            )

    def receive_message(self, message: Message) -> None:
        """Receive a message from another agent.

        Args:
            message: The received message.
        """
        if not self.is_online():
            # Queue message for later delivery
            self.message_queue.append(message)
            self.logger.debug(f"Queued message {message.message_id} while offline")
            return

        self.on_message_received(message)
        self.logger.debug(
            f"Received message {message.message_id} from {message.sender_id}"
        )

    def process_queued_messages(self, current_time: float) -> None:
        """Process any queued messages when coming online.

        Args:
            current_time: Current simulation time.
        """
        while self.message_queue:
            message = self.message_queue.pop(0)
            self.on_message_received(message)
            self.logger.debug(f"Processed queued message {message.message_id}")

    def update_activity(self, current_time: float) -> None:
        """Update the last activity timestamp.

        Args:
            current_time: Current simulation time.
        """
        self.last_activity = current_time

    def get_property(self, key: str, default: Any = None) -> Any:
        """Get an agent property.

        Args:
            key: Property key.
            default: Default value if key not found.

        Returns:
            Property value or default.
        """
        return self.properties.get(key, default)

    def set_property(self, key: str, value: Any) -> None:
        """Set an agent property.

        Args:
            key: Property key.
            value: Property value.
        """
        self.properties[key] = value

    # EventHandler implementation
    def can_handle(self, event_type: str) -> bool:
        """Check if this agent can handle the given event type.

        Args:
            event_type: The event type to check.

        Returns:
            True if this agent can handle the event type.
        """
        return event_type in self.handled_event_types

    def handle_event(self, event: Event) -> list[Event]:
        """Handle an event.

        Args:
            event: The event to handle.

        Returns:
            List of new events generated by handling this event.
        """
        if not self.is_online():
            return []

        self.update_activity(event.time)
        return self.on_event(event)

    # Abstract methods for subclasses to implement
    @abstractmethod
    def on_activate(self, current_time: float) -> None:
        """Called when agent is activated.

        Args:
            current_time: Current simulation time.
        """
        pass

    @abstractmethod
    def on_deactivate(self, current_time: float) -> None:
        """Called when agent is deactivated.

        Args:
            current_time: Current simulation time.
        """
        pass

    def on_go_offline(self, current_time: float) -> None:
        """Called when agent goes offline.

        Args:
            current_time: Current simulation time.
        """
        pass

    def on_go_online(self, current_time: float) -> None:
        """Called when agent comes online.

        Args:
            current_time: Current simulation time.
        """
        self.process_queued_messages(current_time)

    def on_terminate(self, current_time: float) -> None:
        """Called when agent is terminated.

        Args:
            current_time: Current simulation time.
        """
        pass

    @abstractmethod
    def on_message_received(self, message: Message) -> None:
        """Called when a message is received.

        Args:
            message: The received message.
        """
        pass

    @abstractmethod
    def on_event(self, event: Event) -> list[Event]:
        """Called when an event is handled.

        Args:
            event: The event to handle.

        Returns:
            List of new events generated.
        """
        pass


class AgentManager:
    """Manages all agents in the simulation."""

    def __init__(self, simulation_engine: Any = None) -> None:
        """Initialize the agent manager.

        Args:
            simulation_engine: Reference to the simulation engine.
        """
        self.simulation_engine = simulation_engine
        self.agents: dict[str, BaseAgent] = {}
        self.agents_by_type: dict[AgentType, list[BaseAgent]] = {
            agent_type: [] for agent_type in AgentType
        }
        self.logger = get_logger(__name__)

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the manager.

        Args:
            agent: The agent to register.
        """
        if agent.agent_id in self.agents:
            raise ValueError(f"Agent {agent.agent_id} already registered")

        self.agents[agent.agent_id] = agent
        self.agents_by_type[agent.agent_type].append(agent)

        # Register agent as event handler if it has handled events
        if agent.handled_event_types and self.simulation_engine:
            for event_type in agent.handled_event_types:
                self.simulation_engine.register_event_handler(event_type, agent)

        self.logger.debug(
            f"Registered agent {agent.agent_id} of type {agent.agent_type.value}"
        )

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the manager.

        Args:
            agent_id: ID of the agent to unregister.

        Returns:
            True if agent was found and removed.
        """
        if agent_id not in self.agents:
            return False

        agent = self.agents[agent_id]
        del self.agents[agent_id]
        self.agents_by_type[agent.agent_type].remove(agent)

        self.logger.debug(f"Unregistered agent {agent_id}")
        return True

    def get_agent(self, agent_id: str) -> BaseAgent | None:
        """Get an agent by ID.

        Args:
            agent_id: ID of the agent to get.

        Returns:
            The agent or None if not found.
        """
        return self.agents.get(agent_id)

    def get_agents_by_type(self, agent_type: AgentType) -> list[BaseAgent]:
        """Get all agents of a specific type.

        Args:
            agent_type: Type of agents to get.

        Returns:
            List of agents of the specified type.
        """
        return self.agents_by_type[agent_type].copy()

    def get_all_agents(self) -> list[BaseAgent]:
        """Get all registered agents.

        Returns:
            List of all agents.
        """
        return list(self.agents.values())

    def activate_all_agents(self, current_time: float) -> None:
        """Activate all registered agents.

        Args:
            current_time: Current simulation time.
        """
        for agent in self.agents.values():
            if agent.state == AgentState.INACTIVE:
                agent.activate(current_time)

        self.logger.info(f"Activated {len(self.agents)} agents at time {current_time}")

    def terminate_all_agents(self, current_time: float) -> None:
        """Terminate all registered agents.

        Args:
            current_time: Current simulation time.
        """
        for agent in self.agents.values():
            if agent.state != AgentState.TERMINATED:
                agent.terminate(current_time)

        self.logger.info(f"Terminated {len(self.agents)} agents at time {current_time}")

    def get_agent_count(self) -> int:
        """Get the total number of registered agents.

        Returns:
            Number of registered agents.
        """
        return len(self.agents)

    def get_agent_count_by_type(self, agent_type: AgentType) -> int:
        """Get the number of agents of a specific type.

        Args:
            agent_type: Type of agents to count.

        Returns:
            Number of agents of the specified type.
        """
        return len(self.agents_by_type[agent_type])

    def get_active_agents(self) -> list[BaseAgent]:
        """Get all currently active agents.

        Returns:
            List of active agents.
        """
        return [agent for agent in self.agents.values() if agent.is_active()]

    def get_online_agents(self) -> list[BaseAgent]:
        """Get all currently online agents.

        Returns:
            List of online agents.
        """
        return [agent for agent in self.agents.values() if agent.is_online()]
