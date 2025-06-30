"""Sybil attack implementation for Nostr simulation.

This module implements agents that can perform sybil attacks by creating
multiple identities and coordinating their behavior to spam or abuse the network.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from typing import Any

from ...protocol.events import NostrEvent, NostrEventKind
from ...protocol.keys import NostrKeyPair
from ...simulation.events import Event
from ..base import AgentType, BaseAgent, Message


@dataclass
class SybilAttackPattern:
    """Configuration for sybil attack behavior."""

    # Identity management
    identity_count: int = 10  # Number of sybil identities to create
    identity_creation_rate: float = 1.0  # Identities per minute
    identity_switching_frequency: float = 5.0  # Minutes between switches

    # Attack patterns
    spam_frequency: float = 10.0  # Messages per minute per identity
    coordinated_timing: bool = True  # Whether to coordinate timing
    burst_mode: bool = False  # Send messages in bursts

    # Evasion strategies
    behavior_variation: float = 0.3  # Random variation in behavior (0.0-1.0)
    dormancy_periods: bool = True  # Use dormancy to avoid detection
    mimetic_behavior: bool = True  # Copy honest user patterns


@dataclass
class SybilIdentity:
    """Represents a single sybil identity."""

    identity_id: str
    private_key: NostrKeyPair
    public_key: str
    creation_time: float
    last_active: float
    message_count: int = 0
    dormant: bool = False

    def __post_init__(self) -> None:
        """Initialize derived attributes."""
        if not hasattr(self, "public_key") or not self.public_key:
            self.public_key = self.private_key.public_key


class SybilAttackerAgent(BaseAgent):
    """Agent that performs sybil attacks by managing multiple identities."""

    def __init__(
        self,
        agent_id: str,
        simulation_engine: Any = None,
        attack_pattern: SybilAttackPattern | None = None,
    ) -> None:
        """Initialize the sybil attacker agent.

        Args:
            agent_id: Unique identifier for the attacker.
            simulation_engine: Reference to the simulation engine.
            attack_pattern: Attack behavior configuration.
        """
        super().__init__(agent_id, AgentType.MALICIOUS_USER, simulation_engine)

        self.attack_pattern = attack_pattern or SybilAttackPattern()

        # Identity management
        self.identities: dict[str, SybilIdentity] = {}
        self.active_identity: SybilIdentity | None = None

        # Attack state
        self.attack_active: bool = False
        self.total_messages_sent: int = 0
        self.last_identity_switch: float = 0.0
        self.last_message_time: float = 0.0

        # Coordination
        self.coordinator_mode: bool = False
        self.coordinated_identities: set[str] = set()

        # Metrics
        self.detection_events: int = 0
        self.successful_messages: int = 0

    def initialize_identities(self, current_time: float) -> None:
        """Create initial set of sybil identities.

        Args:
            current_time: Current simulation time.
        """
        for i in range(self.attack_pattern.identity_count):
            identity_id = f"{self.agent_id}_identity_{i}"
            private_key = NostrKeyPair.generate()

            identity = SybilIdentity(
                identity_id=identity_id,
                private_key=private_key,
                public_key=private_key.public_key,
                creation_time=current_time,
                last_active=current_time,
            )

            self.identities[identity_id] = identity

        # Set first identity as active
        if self.identities:
            self.active_identity = next(iter(self.identities.values()))

    def start_attack(self, current_time: float) -> None:
        """Begin the sybil attack.

        Args:
            current_time: Current simulation time.
        """
        if not self.identities:
            self.initialize_identities(current_time)

        self.attack_active = True
        self.last_identity_switch = current_time
        self.logger.info(f"Sybil attack started with {len(self.identities)} identities")

    def stop_attack(self) -> None:
        """Stop the sybil attack."""
        self.attack_active = False
        self.logger.info("Sybil attack stopped")

    def switch_identity(self, current_time: float) -> None:
        """Switch to a different sybil identity.

        Args:
            current_time: Current simulation time.
        """
        if not self.identities:
            return

        # Filter out dormant identities
        available_identities = [
            identity for identity in self.identities.values() if not identity.dormant
        ]

        if not available_identities:
            # Reactivate a dormant identity if none available
            dormant_identities = [
                identity for identity in self.identities.values() if identity.dormant
            ]
            if dormant_identities:
                identity = random.choice(dormant_identities)
                identity.dormant = False
                available_identities = [identity]

        if available_identities:
            # Choose different identity from current
            choices = [
                identity
                for identity in available_identities
                if identity != self.active_identity
            ]
            if choices:
                self.active_identity = random.choice(choices)
                self.last_identity_switch = current_time
                self.logger.debug(
                    f"Switched to identity {self.active_identity.identity_id}"
                )

    def add_identity(self, current_time: float) -> SybilIdentity:
        """Create and add a new sybil identity.

        Args:
            current_time: Current simulation time.

        Returns:
            The newly created identity.
        """
        identity_id = f"{self.agent_id}_identity_{len(self.identities)}"
        private_key = NostrKeyPair.generate()

        identity = SybilIdentity(
            identity_id=identity_id,
            private_key=private_key,
            public_key=private_key.public_key,
            creation_time=current_time,
            last_active=current_time,
        )

        self.identities[identity_id] = identity
        self.logger.debug(f"Created new identity {identity_id}")
        return identity

    def remove_identity(self, identity_id: str) -> bool:
        """Remove a sybil identity.

        Args:
            identity_id: ID of the identity to remove.

        Returns:
            True if identity was removed, False if not found.
        """
        if identity_id in self.identities:
            identity = self.identities[identity_id]

            # If removing active identity, switch to another
            if self.active_identity == identity:
                remaining = [id for id in self.identities.keys() if id != identity_id]
                if remaining:
                    self.active_identity = self.identities[remaining[0]]
                else:
                    self.active_identity = None

            del self.identities[identity_id]
            self.logger.debug(f"Removed identity {identity_id}")
            return True

        return False

    def coordinate_with_identity(self, identity_id: str) -> None:
        """Add identity to coordination group.

        Args:
            identity_id: ID of identity to coordinate with.
        """
        self.coordinated_identities.add(identity_id)

    def generate_spam_content(self) -> str:
        """Generate spam content for attack messages.

        Returns:
            Generated spam content.
        """
        # Simple spam content generation
        spam_templates = [
            "Check out this amazing offer: {}",
            "You won't believe this secret: {}",
            "Click here for instant results: {}",
            "Limited time offer: {}",
            "Don't miss out on: {}",
        ]

        filler_words = [
            "crypto",
            "bitcoin",
            "investment",
            "trading",
            "profit",
            "money",
            "wealth",
            "success",
            "opportunity",
            "freedom",
        ]

        template = random.choice(spam_templates)
        filler = " ".join(random.choices(filler_words, k=random.randint(2, 5)))

        return template.format(filler)

    def should_send_message(self, current_time: float) -> bool:
        """Determine if agent should send a message now.

        Args:
            current_time: Current simulation time.

        Returns:
            True if should send message, False otherwise.
        """
        if not self.attack_active or not self.active_identity:
            return False

        # Check dormancy
        if self.active_identity.dormant:
            return False

        # Calculate time since last message
        time_since_last = current_time - self.last_message_time

        # Base frequency with variation
        base_interval = 60.0 / self.attack_pattern.spam_frequency  # seconds
        variation = random.uniform(
            1.0 - self.attack_pattern.behavior_variation,
            1.0 + self.attack_pattern.behavior_variation,
        )
        interval = base_interval * variation

        return time_since_last >= interval

    def should_switch_identity(self, current_time: float) -> bool:
        """Determine if agent should switch identity.

        Args:
            current_time: Current simulation time.

        Returns:
            True if should switch identity, False otherwise.
        """
        if len(self.identities) <= 1:
            return False

        time_since_switch = current_time - self.last_identity_switch
        switch_interval = (
            self.attack_pattern.identity_switching_frequency * 60
        )  # minutes to seconds

        return time_since_switch >= switch_interval

    def create_spam_event(self, current_time: float) -> NostrEvent | None:
        """Create a spam event using the current active identity.

        Args:
            current_time: Current simulation time.

        Returns:
            Created spam event or None if no active identity.
        """
        if not self.active_identity:
            return None

        content = self.generate_spam_content()

        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content=content,
            created_at=int(current_time),
            pubkey=self.active_identity.public_key,
        )

        # Sign the event with the identity's private key
        event_dict = {
            "kind": event.kind.value,
            "content": event.content,
            "created_at": event.created_at,
            "pubkey": event.pubkey,
            "tags": [tag.to_list() for tag in event.tags],
        }
        event.sig = self.active_identity.private_key.sign_event(
            json.dumps(event_dict, separators=(",", ":"), ensure_ascii=False)
        )

        # Update identity stats
        self.active_identity.message_count += 1
        self.active_identity.last_active = current_time

        return event

    def activate_dormancy(self, identity_id: str) -> None:
        """Put an identity into dormancy to avoid detection.

        Args:
            identity_id: ID of identity to make dormant.
        """
        if identity_id in self.identities:
            self.identities[identity_id].dormant = True

            # Switch away from dormant identity if it's active
            if self.active_identity and self.active_identity.identity_id == identity_id:
                self.switch_identity(time.time())

    def reactivate_identity(self, identity_id: str) -> None:
        """Reactivate a dormant identity.

        Args:
            identity_id: ID of identity to reactivate.
        """
        if identity_id in self.identities:
            self.identities[identity_id].dormant = False

    def handle_detection(self, detected_identity: str, current_time: float) -> None:
        """Handle detection of one of the sybil identities.

        Args:
            detected_identity: ID of detected identity.
            current_time: Current simulation time.
        """
        self.detection_events += 1

        if detected_identity in self.identities:
            # Put detected identity into dormancy
            self.activate_dormancy(detected_identity)

            # Create new identity to replace it
            if len(self.identities) < self.attack_pattern.identity_count:
                self.add_identity(current_time)

        self.logger.warning(f"Identity {detected_identity} detected and made dormant")

    def get_attack_metrics(self) -> dict[str, Any]:
        """Get metrics about the attack performance.

        Returns:
            Dictionary containing attack metrics.
        """
        active_identities = sum(1 for id in self.identities.values() if not id.dormant)
        total_messages = sum(id.message_count for id in self.identities.values())

        return {
            "total_identities": len(self.identities),
            "active_identities": active_identities,
            "dormant_identities": len(self.identities) - active_identities,
            "total_messages_sent": total_messages,
            "detection_events": self.detection_events,
            "successful_messages": self.successful_messages,
            "attack_active": self.attack_active,
        }

    def process_event(self, event: Event) -> None:
        """Process simulation events.

        Args:
            event: Event to process.
        """
        current_time = event.time

        # Check if should switch identity
        if self.should_switch_identity(current_time):
            self.switch_identity(current_time)

        # Check if should send spam message
        if self.should_send_message(current_time):
            spam_event = self.create_spam_event(current_time)
            if spam_event and self.simulation_engine:
                # Send to network (this would be implementation specific)
                self.last_message_time = current_time
                self.total_messages_sent += 1

    def update_state(self, current_time: float) -> None:
        """Update agent state.

        Args:
            current_time: Current simulation time.
        """
        # Periodic maintenance
        if not self.attack_active:
            return

        # Check if we need to start attack
        if not self.identities:
            self.initialize_identities(current_time)

    # Abstract method implementations from BaseAgent
    def on_activate(self, current_time: float) -> None:
        """Called when agent is activated.

        Args:
            current_time: Current simulation time.
        """
        self.logger.info(f"Sybil attacker {self.agent_id} activated")
        if not self.attack_active:
            self.start_attack(current_time)

    def on_deactivate(self, current_time: float) -> None:
        """Called when agent is deactivated.

        Args:
            current_time: Current simulation time.
        """
        self.logger.info(f"Sybil attacker {self.agent_id} deactivated")
        self.stop_attack()

    def on_message_received(self, message: Message) -> None:
        """Called when a message is received.

        Args:
            message: The received message.
        """
        # Process coordination messages from other attackers
        if message.message_type == "coordination_request":
            self.coordinate_with_identity(message.content.get("identity_id", ""))
        elif message.message_type == "detection_alert":
            detected_identity = message.content.get("detected_identity", "")
            if detected_identity:
                self.handle_detection(detected_identity, message.timestamp)

    def on_event(self, event: Event) -> list[Event]:
        """Called when an event is handled.

        Args:
            event: The event to handle.

        Returns:
            List of new events generated.
        """
        # Process the event for attack behavior
        self.process_event(event)

        # Return empty list for now - could generate coordination events
        return []
