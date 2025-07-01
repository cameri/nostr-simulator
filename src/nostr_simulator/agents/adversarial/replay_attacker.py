"""Replay attack implementation for Nostr simulation.

This module implements agents that can perform replay attacks by collecting
legitimate events and replaying them with different keys or across different relays.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any

from ...protocol.events import NostrEvent, NostrEventKind
from ...protocol.keys import NostrKeyPair
from ...simulation.events import Event
from ..base import AgentType, BaseAgent, Message


@dataclass
class ReplayTiming:
    """Configuration for replay timing patterns."""

    collection_duration: float = 300.0  # Time to collect events (seconds)
    replay_delay: float = 60.0  # Delay before starting replay (seconds)
    replay_interval: float = 5.0  # Time between replayed events (seconds)
    replay_batch_size: int = 10  # Events replayed per batch
    timing_jitter: bool = True  # Add randomness to timing
    randomization: float = 0.3  # Amount of timing randomization (0.0-1.0)


@dataclass
class ReplayStrategy:
    """Configuration for replay attack strategy."""

    # Event collection
    target_event_kinds: list[NostrEventKind] = field(
        default_factory=lambda: [NostrEventKind.TEXT_NOTE, NostrEventKind.SET_METADATA]
    )
    max_collected_events: int = 1000  # Maximum events to store
    min_event_age: float = 60.0  # Minimum age of events to replay (seconds)

    # Replay patterns
    key_rotation: bool = True  # Use different keys for replay
    cross_relay_replay: bool = True  # Replay across multiple relays
    content_modification: bool = False  # Slightly modify content
    timestamp_modification: bool = True  # Modify timestamps

    # Amplification
    amplification_factor: int = 1  # How many times to replay each event
    max_amplification: int = 5  # Maximum replay count per event

    # Evasion
    detection_evasion: bool = True  # Apply evasion techniques
    relay_coordination: bool = False  # Coordinate across relays


@dataclass
class ReplayPattern:
    """Configuration for replay attack behavior."""

    timing: ReplayTiming = field(default_factory=ReplayTiming)
    strategy: ReplayStrategy = field(default_factory=ReplayStrategy)

    # Attack phases
    collection_phase: bool = True  # Start by collecting events
    replay_phase: bool = True  # Then replay collected events
    continuous_mode: bool = False  # Continuously collect and replay


@dataclass
class CollectedEvent:
    """Represents an event collected for replay."""

    original_event: NostrEvent
    collection_time: float
    replay_count: int = 0
    last_replay_time: float = 0.0
    source_relay: str | None = None


class ReplayAttackerAgent(BaseAgent):
    """Agent that performs replay attacks by collecting and replaying events."""

    def __init__(
        self,
        agent_id: str,
        simulation_engine: Any = None,
        replay_pattern: ReplayPattern | None = None,
    ) -> None:
        """Initialize replay attacker agent.

        Args:
            agent_id: Unique identifier for the agent.
            simulation_engine: Reference to simulation engine.
            replay_pattern: Configuration for replay behavior.
        """
        super().__init__(agent_id, AgentType.MALICIOUS_USER, simulation_engine)
        self.replay_pattern = replay_pattern or ReplayPattern()

        # Attack state
        self.attack_active: bool = False
        self.collection_active: bool = False
        self.replay_active: bool = False
        self.attack_start_time: float = 0.0
        self.collection_end_time: float = 0.0
        self.next_replay_time: float = 0.0

        # Event collection
        self.collected_events: dict[str, CollectedEvent] = {}
        self.events_to_replay: list[str] = []  # Queue of event IDs to replay

        # Replay keys
        self.replay_keys: list[NostrKeyPair] = []
        self.current_key_index: int = 0

        # Metrics
        self.total_events_collected: int = 0
        self.total_events_replayed: int = 0
        self.total_amplifications: int = 0
        self.cross_relay_replays: int = 0
        self.detection_events: int = 0

        # Initialize replay keys
        self._initialize_replay_keys()

    def _initialize_replay_keys(self) -> None:
        """Initialize multiple keypairs for replay attacks."""
        # Create 5-20 different keys for rotation
        num_keys = random.randint(5, 20)
        for _ in range(num_keys):
            self.replay_keys.append(NostrKeyPair.generate())

    def start_attack(self, current_time: float) -> None:
        """Start the replay attack.

        Args:
            current_time: Current simulation time.
        """
        if self.attack_active:
            return

        self.attack_active = True
        self.attack_start_time = current_time

        if self.replay_pattern.collection_phase:
            self.start_collection_phase(current_time)
        else:
            self.start_replay_phase(current_time)

        self.logger.info(f"Replay attack started by {self.agent_id}")

    def stop_attack(self) -> None:
        """Stop the replay attack."""
        self.attack_active = False
        self.collection_active = False
        self.replay_active = False
        self.logger.info(f"Replay attack stopped by {self.agent_id}")

    def start_collection_phase(self, current_time: float) -> None:
        """Start collecting events for later replay.

        Args:
            current_time: Current simulation time.
        """
        self.collection_active = True
        self.collection_end_time = (
            current_time + self.replay_pattern.timing.collection_duration
        )
        self.logger.info(
            f"Event collection phase started, will collect for "
            f"{self.replay_pattern.timing.collection_duration} seconds"
        )

    def start_replay_phase(self, current_time: float) -> None:
        """Start replaying collected events.

        Args:
            current_time: Current simulation time.
        """
        self.replay_active = True
        self.collection_active = False

        # Prepare events for replay
        self._prepare_replay_queue(current_time)

        # Schedule first replay
        delay = self.replay_pattern.timing.replay_delay
        if self.replay_pattern.timing.timing_jitter:
            jitter = random.uniform(0.5, 1.5)
            delay *= jitter

        self.next_replay_time = current_time + delay
        self.logger.info(
            f"Replay phase started, first replay scheduled in {delay:.1f} seconds"
        )

    def _prepare_replay_queue(self, current_time: float) -> None:
        """Prepare queue of events to replay.

        Args:
            current_time: Current simulation time.
        """
        self.events_to_replay.clear()

        # Filter events that are old enough and haven't been over-replayed
        for event_id, collected_event in self.collected_events.items():
            event_age = current_time - collected_event.collection_time

            if (
                event_age >= self.replay_pattern.strategy.min_event_age
                and collected_event.replay_count
                < self.replay_pattern.strategy.max_amplification
            ):
                self.events_to_replay.append(event_id)

        # Shuffle for randomness
        random.shuffle(self.events_to_replay)

        self.logger.info(f"Prepared {len(self.events_to_replay)} events for replay")

    def should_collect_event(self, event: NostrEvent) -> bool:
        """Determine if an event should be collected for replay.

        Args:
            event: Event to evaluate.

        Returns:
            True if event should be collected, False otherwise.
        """
        if not self.collection_active:
            return False

        if (
            len(self.collected_events)
            >= self.replay_pattern.strategy.max_collected_events
        ):
            return False

        # Check if event kind is targeted
        if event.kind not in self.replay_pattern.strategy.target_event_kinds:
            return False

        # Don't collect our own events
        our_keys = {key.public_key for key in self.replay_keys}
        if event.pubkey in our_keys:
            return False

        # Additional filtering logic can be added here
        return True

    def collect_event(
        self, event: NostrEvent, current_time: float, source_relay: str | None = None
    ) -> None:
        """Collect an event for later replay.

        Args:
            event: Event to collect.
            current_time: Current simulation time.
            source_relay: Source relay identifier.
        """
        if not self.should_collect_event(event):
            return

        event_id = event.id or f"temp_{len(self.collected_events)}"

        collected_event = CollectedEvent(
            original_event=event,
            collection_time=current_time,
            source_relay=source_relay,
        )

        self.collected_events[event_id] = collected_event
        self.total_events_collected += 1

        self.logger.debug(f"Collected event {event_id} for replay")

    def should_replay_now(self, current_time: float) -> bool:
        """Determine if should replay events now.

        Args:
            current_time: Current simulation time.

        Returns:
            True if should replay, False otherwise.
        """
        if not self.replay_active:
            return False

        if not self.events_to_replay:
            return False

        return current_time >= self.next_replay_time

    def perform_replay(self, current_time: float) -> list[NostrEvent]:
        """Perform event replay.

        Args:
            current_time: Current simulation time.

        Returns:
            List of replayed events.
        """
        if not self.should_replay_now(current_time):
            return []

        replayed_events = []
        batch_size = min(
            self.replay_pattern.timing.replay_batch_size, len(self.events_to_replay)
        )

        for _ in range(batch_size):
            if not self.events_to_replay:
                break

            event_id = self.events_to_replay.pop(0)
            collected_event = self.collected_events.get(event_id)

            if not collected_event:
                continue

            # Create replayed events with amplification
            amplification = min(
                self.replay_pattern.strategy.amplification_factor,
                self.replay_pattern.strategy.max_amplification
                - collected_event.replay_count,
            )

            for i in range(amplification):
                replayed_event = self._create_replayed_event(
                    collected_event.original_event, current_time, i
                )
                if replayed_event:
                    replayed_events.append(replayed_event)
                    self.total_amplifications += 1

            # Update replay tracking
            collected_event.replay_count += amplification
            collected_event.last_replay_time = current_time
            self.total_events_replayed += 1

        # Schedule next replay
        self._schedule_next_replay(current_time)

        return replayed_events

    def _create_replayed_event(
        self, original_event: NostrEvent, current_time: float, amplification_index: int
    ) -> NostrEvent | None:
        """Create a replayed version of an event.

        Args:
            original_event: Original event to replay.
            current_time: Current simulation time.
            amplification_index: Index for amplification (0, 1, 2, ...)

        Returns:
            Replayed event or None if creation failed.
        """
        try:
            # Select replay key
            if self.replay_pattern.strategy.key_rotation:
                self.current_key_index = (self.current_key_index + 1) % len(
                    self.replay_keys
                )
            replay_key = self.replay_keys[self.current_key_index]

            # Create replayed event
            replayed_event = NostrEvent(
                kind=original_event.kind,
                content=self._modify_content(
                    original_event.content, amplification_index
                ),
                pubkey=replay_key.public_key,
                created_at=self._modify_timestamp(
                    original_event.created_at, current_time
                ),
                tags=original_event.tags.copy(),
            )

            # Sign the event
            event_dict = {
                "kind": replayed_event.kind.value,
                "content": replayed_event.content,
                "created_at": replayed_event.created_at,
                "pubkey": replayed_event.pubkey,
                "tags": [tag.to_list() for tag in replayed_event.tags],
            }

            replayed_event.sig = replay_key.sign_event(
                json.dumps(event_dict, separators=(",", ":"), ensure_ascii=False)
            )

            return replayed_event

        except Exception as e:
            self.logger.error(f"Failed to create replayed event: {e}")
            return None

    def _modify_content(self, original_content: str, amplification_index: int) -> str:
        """Modify event content for replay.

        Args:
            original_content: Original event content.
            amplification_index: Amplification index.

        Returns:
            Modified content.
        """
        if not self.replay_pattern.strategy.content_modification:
            return original_content

        # Apply subtle modifications to avoid detection
        modifications: list[str] = [
            original_content + " ",  # Add trailing space
            original_content.replace(" ", "  "),  # Double spaces
            original_content + f" #{amplification_index}",  # Add index
            original_content.replace(".", ".\u200b"),  # Add zero-width space
        ]

        return random.choice(modifications)

    def _modify_timestamp(self, original_timestamp: int, current_time: float) -> int:
        """Modify event timestamp for replay.

        Args:
            original_timestamp: Original timestamp.
            current_time: Current simulation time.

        Returns:
            Modified timestamp.
        """
        if not self.replay_pattern.strategy.timestamp_modification:
            return int(current_time)

        # Apply timestamp modifications for evasion
        if self.replay_pattern.strategy.detection_evasion:
            # Add small random offset
            offset = random.randint(-300, 300)  # ±5 minutes
            return int(current_time) + offset

        return int(current_time)

    def _schedule_next_replay(self, current_time: float) -> None:
        """Schedule the next replay event.

        Args:
            current_time: Current simulation time.
        """
        base_interval = self.replay_pattern.timing.replay_interval

        if self.replay_pattern.timing.timing_jitter:
            jitter = random.uniform(
                1.0 - self.replay_pattern.timing.randomization,
                1.0 + self.replay_pattern.timing.randomization,
            )
            interval = base_interval * jitter
        else:
            interval = base_interval

        self.next_replay_time = current_time + interval

    def handle_detection(self, detected_key: str, current_time: float) -> None:
        """Handle detection of replay attack.

        Args:
            detected_key: Public key that was detected.
            current_time: Current simulation time.
        """
        self.detection_events += 1

        # Remove detected key from rotation
        self.replay_keys = [
            key for key in self.replay_keys if key.public_key != detected_key
        ]

        # Reset key index if needed
        if self.current_key_index >= len(self.replay_keys):
            self.current_key_index = 0

        # Add new key to maintain pool size
        if len(self.replay_keys) < 5:
            self.replay_keys.append(NostrKeyPair.generate())

        self.logger.warning(f"Replay key {detected_key[:16]}... was detected")

    def update_state(self, current_time: float) -> None:
        """Update agent state.

        Args:
            current_time: Current simulation time.
        """
        if not self.attack_active:
            return

        # Check if collection phase should end
        if self.collection_active and current_time >= self.collection_end_time:
            if self.replay_pattern.replay_phase:
                self.start_replay_phase(current_time)
            else:
                self.stop_attack()

        # Perform continuous collection if enabled
        if (
            self.replay_pattern.continuous_mode
            and self.replay_active
            and len(self.collected_events)
            < self.replay_pattern.strategy.max_collected_events
        ):
            self.collection_active = True

    def process_event(self, event: Event) -> None:
        """Process simulation events.

        Args:
            event: Event to process.
        """
        current_time = event.time

        # Update state
        self.update_state(current_time)

        # Perform replay if it's time
        if self.should_replay_now(current_time):
            replayed_events = self.perform_replay(current_time)

            # Send replayed events to simulation
            for replayed_event in replayed_events:
                if self.simulation_engine:
                    simulation_event = Event(
                        time=current_time,
                        priority=1,
                        event_type="nostr_event",
                        data={"event": replayed_event, "source_agent": self.agent_id},
                    )
                    self.simulation_engine.schedule_event(simulation_event)

    def get_attack_metrics(self) -> dict[str, Any]:
        """Get attack performance metrics.

        Returns:
            Dictionary of attack metrics.
        """
        return {
            "attack_active": self.attack_active,
            "collection_active": self.collection_active,
            "replay_active": self.replay_active,
            "total_events_collected": self.total_events_collected,
            "total_events_replayed": self.total_events_replayed,
            "total_amplifications": self.total_amplifications,
            "cross_relay_replays": self.cross_relay_replays,
            "detection_events": self.detection_events,
            "collected_events_count": len(self.collected_events),
            "events_in_replay_queue": len(self.events_to_replay),
            "active_replay_keys": len(self.replay_keys),
        }

    # Abstract method implementations from BaseAgent
    def on_activate(self, current_time: float) -> None:
        """Handle agent activation.

        Args:
            current_time: Current simulation time.
        """
        self.logger.info(f"Replay attacker {self.agent_id} activated")
        if not self.attack_active:
            self.start_attack(current_time)

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
        if message.message_type == "coordination_signal":
            content = message.content
            if content.get("action") == "start_replay":
                if not self.attack_active:
                    self.start_attack(message.timestamp)
            elif content.get("action") == "stop_replay":
                self.stop_attack()
            elif content.get("action") == "collected_event":
                # Receive event from coordinated collector
                event_data = content.get("event")
                if event_data:
                    # This would need proper event deserialization
                    pass

    def on_event(self, event: Event) -> list[Event]:
        """Handle simulation events.

        Args:
            event: The event to handle.

        Returns:
            List of new events generated.
        """
        self.process_event(event)

        # Check if we should collect this event
        if event.event_type == "nostr_event" and self.collection_active:
            event_data = event.data.get("event")
            if event_data and isinstance(event_data, NostrEvent):
                self.collect_event(
                    event_data, event.time, event.data.get("source_relay")
                )

        return []  # Don't generate events directly, use scheduled events instead
