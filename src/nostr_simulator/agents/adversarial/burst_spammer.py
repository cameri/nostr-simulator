"""Burst spam attack implementation for Nostr simulation.

This module implements agents that can perform burst spam attacks by sending
large volumes of messages in short time periods to overwhelm defenses.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from ...protocol.events import NostrEvent, NostrEventKind
from ...protocol.keys import NostrKeyPair
from ...simulation.events import Event
from ..base import AgentType, BaseAgent, Message


@dataclass
class BurstTiming:
    """Configuration for burst timing patterns."""

    burst_duration: float = 10.0  # Duration of each burst in seconds
    burst_interval: float = 60.0  # Time between bursts in seconds
    messages_per_second: float = 5.0  # Rate during burst
    burst_count: int = 3  # Number of bursts to perform
    randomization: float = 0.2  # Random variation (0.0-1.0)


@dataclass
class BurstPattern:
    """Configuration for burst spam behavior."""

    # Timing patterns
    timing: BurstTiming = None  # type: ignore

    # Volume scaling
    initial_volume: int = 10  # Starting messages per burst
    volume_scaling: float = 1.5  # Multiplier for each subsequent burst
    max_volume: int = 100  # Maximum messages per burst

    # Coordination
    coordinated: bool = True  # Whether to coordinate with other burst agents
    coordination_delay: float = 5.0  # Seconds to wait for coordination

    # Evasion strategies
    content_variation: bool = True  # Vary message content
    timing_jitter: bool = True  # Add random timing variations
    escalation_mode: bool = False  # Increase intensity over time

    def __post_init__(self) -> None:
        """Initialize timing if not provided."""
        if self.timing is None:
            self.timing = BurstTiming()


class BurstSpammerAgent(BaseAgent):
    """Agent that performs burst spam attacks."""

    def __init__(
        self,
        agent_id: str,
        simulation_engine: Any = None,
        burst_pattern: BurstPattern | None = None,
    ) -> None:
        """Initialize burst spammer agent.

        Args:
            agent_id: Unique identifier for the agent.
            simulation_engine: Reference to simulation engine.
            burst_pattern: Configuration for burst behavior.
        """
        super().__init__(agent_id, AgentType.MALICIOUS_USER)
        self.simulation_engine = simulation_engine
        self.burst_pattern = burst_pattern or BurstPattern()

        # Attack state
        self.attack_active: bool = False
        self.current_burst: int = 0
        self.burst_start_time: float = 0.0
        self.next_burst_time: float = 0.0
        self.messages_this_burst: int = 0
        self.current_volume: int = self.burst_pattern.initial_volume

        # Agent identity
        self.keypair = NostrKeyPair.generate()

        # Content templates for variation
        self.spam_templates = [
            "🚀 URGENT: Limited time crypto offer! Act now! {}",
            "💰 You've won ${}! Claim your prize instantly!",
            "🔥 Hot investment opportunity! {} returns guaranteed!",
            "⚡ BREAKING: New crypto coin will 100x! Buy {} now!",
            "🎁 Free money alert! Get ${} in 5 minutes!",
            "🌟 Don't miss out! {} opportunity of a lifetime!",
            "💎 Diamond hands! {} to the moon!",
            "🎯 Last chance! {} investment expires soon!",
        ]

        # Metrics
        self.total_bursts: int = 0
        self.total_messages_sent: int = 0
        self.burst_start_times: list[float] = []

    def start_attack(self, current_time: float) -> None:
        """Start the burst spam attack.

        Args:
            current_time: Current simulation time.
        """
        if self.attack_active:
            return

        self.attack_active = True
        self.current_burst = 0
        self.next_burst_time = current_time
        self.current_volume = self.burst_pattern.initial_volume

    def stop_attack(self) -> None:
        """Stop the burst spam attack."""
        self.attack_active = False
        self.current_burst = 0
        self.burst_start_time = 0.0
        self.next_burst_time = 0.0
        self.messages_this_burst = 0

    def should_start_burst(self, current_time: float) -> bool:
        """Determine if a new burst should start.

        Args:
            current_time: Current simulation time.

        Returns:
            True if should start new burst, False otherwise.
        """
        if not self.attack_active:
            return False

        if self.current_burst >= self.burst_pattern.timing.burst_count:
            return False

        return current_time >= self.next_burst_time

    def should_send_message_in_burst(self, current_time: float) -> bool:
        """Determine if should send message during active burst.

        Args:
            current_time: Current simulation time.

        Returns:
            True if should send message, False otherwise.
        """
        if not self.is_in_burst(current_time):
            return False

        if self.messages_this_burst >= self.current_volume:
            return False

        # Calculate time since burst start
        time_in_burst = current_time - self.burst_start_time
        expected_messages = int(
            time_in_burst * self.burst_pattern.timing.messages_per_second
        )

        # Add jitter if enabled
        if self.burst_pattern.timing_jitter:
            jitter = random.uniform(0.8, 1.2)
            expected_messages = int(expected_messages * jitter)

        return self.messages_this_burst < expected_messages

    def is_in_burst(self, current_time: float) -> bool:
        """Check if currently in an active burst.

        Args:
            current_time: Current simulation time.

        Returns:
            True if in active burst, False otherwise.
        """
        if self.burst_start_time == 0.0:
            return False

        time_in_burst = current_time - self.burst_start_time
        return time_in_burst <= self.burst_pattern.timing.burst_duration

    def start_burst(self, current_time: float) -> None:
        """Start a new burst.

        Args:
            current_time: Current simulation time.
        """
        self.current_burst += 1
        self.burst_start_time = current_time
        self.messages_this_burst = 0
        self.burst_start_times.append(current_time)

        # Calculate next burst time with optional randomization
        base_interval = self.burst_pattern.timing.burst_interval
        if self.burst_pattern.timing_jitter:
            variation = random.uniform(
                1.0 - self.burst_pattern.timing.randomization,
                1.0 + self.burst_pattern.timing.randomization,
            )
            interval = base_interval * variation
        else:
            interval = base_interval

        self.next_burst_time = (
            current_time + self.burst_pattern.timing.burst_duration + interval
        )

        # Scale volume for next burst if escalation is enabled
        if self.burst_pattern.escalation_mode:
            self.current_volume = min(
                int(self.current_volume * self.burst_pattern.volume_scaling),
                self.burst_pattern.max_volume,
            )

    def generate_spam_content(self) -> str:
        """Generate spam message content.

        Returns:
            Spam message content.
        """
        if not self.burst_pattern.content_variation:
            return "SPAM: Buy now! Limited time offer!"

        template = random.choice(self.spam_templates)
        value = random.randint(1000, 99999)
        return template.format(value)

    def create_spam_event(self, current_time: float) -> NostrEvent | None:
        """Create a spam event.

        Args:
            current_time: Current simulation time.

        Returns:
            Created spam event or None if creation failed.
        """
        try:
            content = self.generate_spam_content()

            event = NostrEvent(
                kind=NostrEventKind.TEXT_NOTE,
                content=content,
                created_at=int(current_time),
                pubkey=self.keypair.public_key,
            )

            self.messages_this_burst += 1
            self.total_messages_sent += 1

            return event

        except Exception:
            return None

    def coordinate_with_others(self, current_time: float) -> bool:
        """Coordinate burst timing with other burst agents.

        Args:
            current_time: Current simulation time.

        Returns:
            True if coordination successful, False otherwise.
        """
        if not self.burst_pattern.coordinated:
            return True

        # In a real implementation, this would communicate with other agents
        # For now, simulate coordination delay
        coordination_delay = self.burst_pattern.coordination_delay
        if self.burst_pattern.timing_jitter:
            jitter = random.uniform(0.5, 1.5)
            coordination_delay *= jitter

        # Simulate coordination success rate
        return random.random() > 0.1  # 90% success rate

    def get_attack_metrics(self) -> dict[str, Any]:
        """Get attack performance metrics.

        Returns:
            Dictionary of attack metrics.
        """
        return {
            "total_bursts": self.total_bursts,
            "total_messages": self.total_messages_sent,
            "current_burst": self.current_burst,
            "current_volume": self.current_volume,
            "attack_active": self.attack_active,
            "burst_times": self.burst_start_times.copy(),
            "messages_this_burst": self.messages_this_burst,
        }

    def process_event(self, event: Event) -> None:
        """Process simulation events.

        Args:
            event: Event to process.
        """
        current_time = event.time

        # Check if should start new burst
        if self.should_start_burst(current_time):
            if self.coordinate_with_others(current_time):
                self.start_burst(current_time)

        # Check if should send message during burst
        if self.should_send_message_in_burst(current_time):
            spam_event = self.create_spam_event(current_time)
            if spam_event and self.simulation_engine:
                # Send to network (implementation specific)
                pass

    def update_state(self, current_time: float) -> None:
        """Update agent state.

        Args:
            current_time: Current simulation time.
        """
        # Check if burst just completed
        if (
            self.burst_start_time > 0
            and not self.is_in_burst(current_time)
            and self.current_burst > self.total_bursts
        ):
            self.total_bursts = self.current_burst

        # Check if attack is complete
        if self.current_burst >= self.burst_pattern.timing.burst_count:
            self.stop_attack()

    # Abstract method implementations from BaseAgent
    def on_activate(self, current_time: float) -> None:
        """Handle agent activation.

        Args:
            current_time: Current simulation time.
        """
        pass

    def on_deactivate(self, current_time: float) -> None:
        """Handle agent deactivation.

        Args:
            current_time: Current simulation time.
        """
        self.stop_attack()

    def on_message_received(self, message: Message) -> None:
        """Handle received messages.

        Args:
            message: The received message.
        """
        # Burst spammers typically don't respond to messages
        pass

    def on_event(self, event: Event) -> list[Event]:
        """Handle simulation events.

        Args:
            event: The event to handle.

        Returns:
            List of new events generated.
        """
        self.process_event(event)
        return []  # Burst spammers don't generate events directly
