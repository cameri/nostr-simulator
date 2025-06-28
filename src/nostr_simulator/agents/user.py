"""User agent implementations for Nostr simulation."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any

from ..protocol.events import NostrEvent, NostrEventKind
from ..simulation.events import Event
from .base import AgentType, BaseAgent


@dataclass
class UserBehaviorPattern:
    """Defines user behavior patterns for simulation."""

    posting_frequency: float = 1.0  # posts per hour
    online_duration: float = 1.0  # hours online per session
    social_activity: float = 0.5  # 0.0 = lurker, 1.0 = very social
    follow_ratio: float = 0.05  # percentage of discovered users to follow


class HonestUserAgent(BaseAgent):
    """Honest user agent that simulates normal Nostr user behavior."""

    def __init__(
        self,
        agent_id: str,
        simulation_engine: Any = None,
        behavior_pattern: UserBehaviorPattern | None = None,
    ) -> None:
        """Initialize the honest user agent.

        Args:
            agent_id: Unique identifier for the user.
            simulation_engine: Reference to the simulation engine.
            behavior_pattern: User behavior configuration.
        """
        super().__init__(agent_id, AgentType.USER, simulation_engine)

        # Behavior configuration
        self.behavior_pattern = behavior_pattern or UserBehaviorPattern()

        # Social graph
        self.following: set[str] = set()
        self.followers: set[str] = set()

        # Network connections (simplified - user manages own relays)
        self.connected_relays: set[str] = set()

        # User state
        self.posts_made = 0
        self.last_post_time = 0.0

        # Event handling configuration
        self.handled_event_types = {
            "post_scheduled",
            "social_interaction",
            "follow_user",
            "user_lifecycle",
        }

        # Content generation
        self.post_templates = [
            "Just thinking about the future of decentralized social media...",
            "Good morning Nostr! How's everyone doing today?",
            "Working on some interesting projects. More details soon!",
            "The beauty of censorship-resistant communication cannot be overstated.",
            "Sometimes the simple moments are the most meaningful.",
            "Exploring new ideas and connecting with amazing people.",
            "What are you all working on today?",
            "Grateful for this decentralized community.",
            "Testing out new features and loving the experience!",
            "The future is bright when we build it together.",
        ]

        self.logger.info(f"Initialized honest user {agent_id}")

    def on_activate(self, current_time: float) -> None:
        """Called when the user comes online."""
        self.logger.info(f"User {self.agent_id} is now online")

        # Schedule first post if we have relays
        if self.connected_relays and self.simulation_engine:
            self.schedule_next_post()

    def on_deactivate(self, current_time: float) -> None:
        """Called when the user goes offline."""
        self.logger.info(f"User {self.agent_id} is now offline")

    def on_message_received(self, message: Any) -> None:
        """Process incoming messages."""
        self.logger.debug(f"User received message: {message.message_type}")

    def on_event(self, event: Event) -> list[Event]:
        """Handle simulation events."""
        events_generated = []

        if event.event_type == "post_scheduled":
            events_generated.extend(self._handle_post_scheduled(event))
        elif event.event_type == "social_interaction":
            events_generated.extend(self._handle_social_interaction(event))
        elif event.event_type == "follow_user":
            events_generated.extend(self._handle_follow_user(event))
        elif event.event_type == "user_lifecycle":
            events_generated.extend(self._handle_user_lifecycle(event))

        return events_generated

    def connect_to_relays(self, relay_ids: list[str]) -> bool:
        """Connect to multiple relays.

        Args:
            relay_ids: List of relay IDs to connect to.

        Returns:
            True if connection was successful.
        """
        if not self.is_active():
            self.logger.warning("Cannot connect to relays while user is inactive")
            return False

        for relay_id in relay_ids:
            self.connected_relays.add(relay_id)

        self.logger.info(f"User {self.agent_id} connected to {len(relay_ids)} relays")
        return True

    def post_text_note(self, content: str) -> bool:
        """Post a text note to connected relays.

        Args:
            content: The content to post.

        Returns:
            True if the post was scheduled successfully.
        """
        if not self.is_active():
            self.logger.warning("Cannot post while user is inactive")
            return False

        if not self.connected_relays:
            self.logger.warning("No connected relays to post to")
            return False

        # Create Nostr event
        nostr_event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content=content,
            created_at=int(time.time()),
            pubkey=f"{self.agent_id}_pubkey",  # Simplified pubkey
        )

        # Schedule publishing to all connected relays
        if self.simulation_engine:
            for relay_id in self.connected_relays:
                publish_event = Event(
                    time=self.simulation_engine.current_time,
                    priority=1,
                    event_type="nostr_event",
                    data={
                        "sender_id": self.agent_id,
                        "relay_id": relay_id,
                        "nostr_event": nostr_event,
                    },
                )
                self.simulation_engine.schedule_event(publish_event)

        self.posts_made += 1
        self.last_post_time = (
            self.simulation_engine.current_time
            if self.simulation_engine
            else time.time()
        )

        self.logger.info(f"User {self.agent_id} posted: {content[:50]}...")
        return True

    def follow_user(self, user_id: str) -> bool:
        """Follow another user.

        Args:
            user_id: ID of the user to follow.

        Returns:
            True if successful.
        """
        if not self.is_active():
            self.logger.warning("Cannot follow user while inactive")
            return False

        self.following.add(user_id)
        self.logger.info(f"User {self.agent_id} is now following {user_id}")
        return True

    def unfollow_user(self, user_id: str) -> bool:
        """Unfollow a user.

        Args:
            user_id: ID of the user to unfollow.

        Returns:
            True if successful.
        """
        if user_id not in self.following:
            return False

        self.following.remove(user_id)
        self.logger.info(f"User {self.agent_id} unfollowed {user_id}")
        return True

    def add_follower(self, user_id: str) -> None:
        """Add a follower (when another user follows this user).

        Args:
            user_id: ID of the user who is following.
        """
        self.followers.add(user_id)
        self.logger.debug(f"User {user_id} is now following {self.agent_id}")

    def remove_follower(self, user_id: str) -> None:
        """Remove a follower (when another user unfollows this user).

        Args:
            user_id: ID of the user who unfollowed.
        """
        self.followers.discard(user_id)
        self.logger.debug(f"User {user_id} unfollowed {self.agent_id}")

    def schedule_next_post(self) -> None:
        """Schedule the next post based on behavior pattern."""
        if not self.simulation_engine:
            return

        # Calculate time until next post (exponential distribution)
        hours_per_post = 1.0 / self.behavior_pattern.posting_frequency
        time_until_next = (
            random.expovariate(1.0 / hours_per_post) * 3600
        )  # Convert to seconds

        next_post_time = self.simulation_engine.current_time + time_until_next

        post_event = Event(
            time=next_post_time,
            priority=2,
            event_type="post_scheduled",
            data={"user_id": self.agent_id},
        )

        self.simulation_engine.schedule_event(post_event)
        self.logger.debug(
            f"Scheduled next post for user {self.agent_id} at {next_post_time}"
        )

    def generate_post_content(self) -> str:
        """Generate content for a post.

        Returns:
            Generated post content.
        """
        # Simple content generation - could be enhanced with more sophisticated methods
        base_content = random.choice(self.post_templates)

        # Add some variation
        if random.random() < 0.3:  # 30% chance to add timestamp reference
            base_content += f" #{int(time.time())}"

        return base_content

    def should_follow_user(self, user_id: str) -> bool:
        """Determine if this user should follow another user.

        Args:
            user_id: ID of the potential user to follow.

        Returns:
            True if should follow.
        """
        # Already following?
        if user_id in self.following:
            return False

        # Decision based on follow ratio
        return random.random() < self.behavior_pattern.follow_ratio

    def _handle_post_scheduled(self, event: Event) -> list[Event]:
        """Handle scheduled post events."""
        user_id = event.data.get("user_id")

        if user_id == self.agent_id and self.connected_relays:
            # Generate and post content
            content = self.generate_post_content()
            self.post_text_note(content)

            # Schedule next post
            self.schedule_next_post()

        return []

    def _handle_social_interaction(self, event: Event) -> list[Event]:
        """Handle social interaction events."""
        interaction_type = event.data.get("interaction_type")
        target_user = event.data.get("target_user")

        if interaction_type == "discover_user" and target_user:
            # Consider following the discovered user
            if self.should_follow_user(target_user):
                self.follow_user(target_user)

        return []

    def _handle_follow_user(self, event: Event) -> list[Event]:
        """Handle follow user events."""
        target_user = event.data.get("target_user")

        if target_user:
            self.follow_user(target_user)

        return []

    def _handle_user_lifecycle(self, event: Event) -> list[Event]:
        """Handle user lifecycle events."""
        action = event.data.get("action")

        if action == "go_offline":
            self.deactivate(
                self.simulation_engine.current_time if self.simulation_engine else 0.0
            )
        elif action == "go_online":
            self.activate(
                self.simulation_engine.current_time if self.simulation_engine else 0.0
            )

        return []

    def get_stats(self) -> dict[str, Any]:
        """Get user statistics.

        Returns:
            Dictionary containing user statistics.
        """
        return {
            "following_count": len(self.following),
            "followers_count": len(self.followers),
            "connected_relays": len(self.connected_relays),
            "posts_made": self.posts_made,
            "last_post_time": self.last_post_time,
            "behavior_pattern": {
                "posting_frequency": self.behavior_pattern.posting_frequency,
                "online_duration": self.behavior_pattern.online_duration,
                "social_activity": self.behavior_pattern.social_activity,
                "follow_ratio": self.behavior_pattern.follow_ratio,
            },
        }
