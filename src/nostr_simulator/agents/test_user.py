"""Tests for user agent implementations."""

from unittest.mock import Mock

import pytest

from ..simulation.events import Event
from .base import AgentState, AgentType
from .user import HonestUserAgent, UserBehaviorPattern


class TestUserBehaviorPattern:
    """Test UserBehaviorPattern functionality."""

    def test_behavior_pattern_creation(self) -> None:
        """Test creating user behavior patterns."""
        pattern = UserBehaviorPattern(
            posting_frequency=5.0,  # posts per hour
            online_duration=2.0,  # hours
            social_activity=0.7,  # 70% social
            follow_ratio=0.1,  # follows 10% of discovered users
        )

        assert pattern.posting_frequency == 5.0
        assert pattern.online_duration == 2.0
        assert pattern.social_activity == 0.7
        assert pattern.follow_ratio == 0.1

    def test_default_behavior_pattern(self) -> None:
        """Test default behavior pattern values."""
        pattern = UserBehaviorPattern()

        assert pattern.posting_frequency == 1.0
        assert pattern.online_duration == 1.0
        assert pattern.social_activity == 0.5
        assert pattern.follow_ratio == 0.05

    def test_behavior_pattern_validation(self) -> None:
        """Test behavior pattern validation."""
        # Valid pattern
        pattern = UserBehaviorPattern(
            posting_frequency=1.0,
            online_duration=1.0,
            social_activity=0.5,
            follow_ratio=0.1,
        )
        assert pattern.posting_frequency == 1.0

        # Test boundary values
        pattern = UserBehaviorPattern(
            posting_frequency=0.1,
            online_duration=0.1,
            social_activity=0.0,
            follow_ratio=0.0,
        )
        assert pattern.social_activity == 0.0
        assert pattern.follow_ratio == 0.0


class TestHonestUserAgent:
    """Test HonestUserAgent functionality."""

    def test_user_agent_initialization(self) -> None:
        """Test honest user agent initialization."""
        user = HonestUserAgent("user1")

        assert user.agent_id == "user1"
        assert user.agent_type == AgentType.USER
        assert user.state == AgentState.INACTIVE
        assert isinstance(user.behavior_pattern, UserBehaviorPattern)
        assert isinstance(user.following, set)
        assert isinstance(user.followers, set)
        assert len(user.connected_relays) == 0

    def test_user_agent_with_custom_behavior(self) -> None:
        """Test user agent with custom behavior pattern."""
        behavior = UserBehaviorPattern(
            posting_frequency=10.0,
            online_duration=3.0,
            social_activity=0.8,
            follow_ratio=0.2,
        )

        user = HonestUserAgent("user1", behavior_pattern=behavior)

        assert user.behavior_pattern.posting_frequency == 10.0
        assert user.behavior_pattern.online_duration == 3.0
        assert user.behavior_pattern.social_activity == 0.8
        assert user.behavior_pattern.follow_ratio == 0.2

    def test_user_agent_handles_event_types(self) -> None:
        """Test that user agent handles appropriate event types."""
        user = HonestUserAgent("user1")

        assert user.can_handle("post_scheduled")
        assert user.can_handle("social_interaction")
        assert user.can_handle("follow_user")
        assert user.can_handle("user_lifecycle")

    def test_connect_to_relays(self) -> None:
        """Test connecting to multiple relays."""
        mock_engine = Mock()
        user = HonestUserAgent("user1", simulation_engine=mock_engine)
        user.activate(10.0)

        relay_ids = ["relay1", "relay2", "relay3"]
        result = user.connect_to_relays(relay_ids)

        assert result is True
        assert len(user.connected_relays) == 3
        assert all(relay_id in user.connected_relays for relay_id in relay_ids)

    def test_connect_to_relays_while_inactive(self) -> None:
        """Test that connection fails when user is inactive."""
        user = HonestUserAgent("user1")
        # Don't activate

        result = user.connect_to_relays(["relay1"])
        assert result is False
        assert len(user.connected_relays) == 0

    def test_post_text_note(self) -> None:
        """Test posting a text note."""
        mock_engine = Mock()
        mock_engine.current_time = 100.0

        user = HonestUserAgent("user1", simulation_engine=mock_engine)
        user.activate(10.0)
        user.connect_to_relays(["relay1"])

        result = user.post_text_note("Hello, Nostr!")
        assert result is True

        # Should schedule publishing event
        mock_engine.schedule_event.assert_called()

    def test_post_text_note_without_relays(self) -> None:
        """Test posting without connected relays."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        result = user.post_text_note("Hello, Nostr!")
        assert result is False

    def test_post_text_note_while_inactive(self) -> None:
        """Test posting while inactive."""
        user = HonestUserAgent("user1")
        # Don't activate

        result = user.post_text_note("Hello, Nostr!")
        assert result is False

    def test_follow_user(self) -> None:
        """Test following another user."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        result = user.follow_user("user2")
        assert result is True
        assert "user2" in user.following

    def test_follow_user_while_inactive(self) -> None:
        """Test following while inactive."""
        user = HonestUserAgent("user1")
        # Don't activate

        result = user.follow_user("user2")
        assert result is False
        assert "user2" not in user.following

    def test_follow_already_followed_user(self) -> None:
        """Test following a user that's already followed."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        # Follow once
        result1 = user.follow_user("user2")
        assert result1 is True
        assert len(user.following) == 1

        # Follow again
        result2 = user.follow_user("user2")
        assert result2 is True
        assert len(user.following) == 1  # Should not duplicate

    def test_unfollow_user(self) -> None:
        """Test unfollowing a user."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        # First follow
        user.follow_user("user2")
        assert "user2" in user.following

        # Then unfollow
        result = user.unfollow_user("user2")
        assert result is True
        assert "user2" not in user.following

    def test_unfollow_not_followed_user(self) -> None:
        """Test unfollowing a user that's not followed."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        result = user.unfollow_user("user2")
        assert result is False

    def test_add_follower(self) -> None:
        """Test adding a follower."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        user.add_follower("user2")
        assert "user2" in user.followers

    def test_remove_follower(self) -> None:
        """Test removing a follower."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        # Add then remove
        user.add_follower("user2")
        assert "user2" in user.followers

        user.remove_follower("user2")
        assert "user2" not in user.followers

    def test_schedule_next_post(self) -> None:
        """Test scheduling the next post."""
        mock_engine = Mock()
        mock_engine.current_time = 100.0

        user = HonestUserAgent("user1", simulation_engine=mock_engine)
        user.activate(10.0)

        user.schedule_next_post()

        # Should schedule a post event
        mock_engine.schedule_event.assert_called()

    def test_schedule_next_post_without_engine(self) -> None:
        """Test scheduling post without simulation engine."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        # Should not crash
        user.schedule_next_post()

    def test_generate_post_content(self) -> None:
        """Test generating post content."""
        user = HonestUserAgent("user1")

        content = user.generate_post_content()

        assert isinstance(content, str)
        assert len(content) > 0
        assert len(content) <= 280  # Should be reasonable length

    def test_should_follow_user(self) -> None:
        """Test follow decision logic."""
        # High follow ratio user
        behavior = UserBehaviorPattern(follow_ratio=0.9)
        user = HonestUserAgent("user1", behavior_pattern=behavior)

        # Should follow most users
        follow_decisions = [user.should_follow_user("user2") for _ in range(100)]
        follow_rate = sum(follow_decisions) / len(follow_decisions)
        assert follow_rate > 0.8  # Should follow most users

        # Low follow ratio user
        behavior = UserBehaviorPattern(follow_ratio=0.1)
        user = HonestUserAgent("user1", behavior_pattern=behavior)

        follow_decisions = [user.should_follow_user("user2") for _ in range(100)]
        follow_rate = sum(follow_decisions) / len(follow_decisions)
        assert follow_rate < 0.2  # Should follow few users

    def test_handle_post_scheduled_event(self) -> None:
        """Test handling post scheduled events."""
        mock_engine = Mock()
        mock_engine.current_time = 100.0
        user = HonestUserAgent("user1", mock_engine)
        user.activate(10.0)
        user.connect_to_relays(["relay1"])

        event = Event(
            time=10.0,
            priority=0,
            event_type="post_scheduled",
            data={"user_id": "user1"},
        )

        result = user.on_event(event)
        assert isinstance(result, list)

    def test_handle_social_interaction_event(self) -> None:
        """Test handling social interaction events."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="social_interaction",
            data={
                "interaction_type": "discover_user",
                "target_user": "user2",
                "pubkey": "user2_pubkey",
            },
        )

        result = user.on_event(event)
        assert isinstance(result, list)

    def test_handle_follow_user_event(self) -> None:
        """Test handling follow user events."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="follow_user",
            data={"target_user": "user2"},
        )

        result = user.on_event(event)
        assert isinstance(result, list)

    def test_handle_user_lifecycle_event(self) -> None:
        """Test handling user lifecycle events."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="user_lifecycle",
            data={"action": "go_offline"},
        )

        result = user.on_event(event)
        assert isinstance(result, list)

    def test_handle_unknown_event_type(self) -> None:
        """Test handling unknown event types."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="unknown_event",
            data={},
        )

        result = user.on_event(event)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_user_lifecycle_callbacks(self) -> None:
        """Test user lifecycle callback methods."""
        user = HonestUserAgent("user1")

        # Test activation
        user.on_activate(10.0)
        # Should not raise exceptions

        # Test deactivation
        user.on_deactivate(20.0)
        # Should not raise exceptions

        # Test message received
        message = Mock()
        message.message_type = "test_message"
        user.on_message_received(message)
        # Should not raise exceptions

    def test_get_stats(self) -> None:
        """Test user statistics."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        # Add some data
        user.follow_user("user2")
        user.follow_user("user3")
        user.add_follower("user4")
        user.connect_to_relays(["relay1", "relay2"])

        stats = user.get_stats()

        assert stats["following_count"] == 2
        assert stats["followers_count"] == 1
        assert stats["connected_relays"] == 2
        assert "behavior_pattern" in stats
        assert "posts_made" in stats

    def test_user_with_simulation_engine(self) -> None:
        """Test user operations with simulation engine."""
        mock_engine = Mock()
        mock_engine.current_time = 100.0

        user = HonestUserAgent("user1", simulation_engine=mock_engine)
        user.activate(10.0)
        user.connect_to_relays(["relay1"])

        # Post a note
        user.post_text_note("Test message")

        # Should have scheduled events
        assert mock_engine.schedule_event.called

    def test_user_without_simulation_engine(self) -> None:
        """Test user operations without simulation engine."""
        user = HonestUserAgent("user1")
        user.activate(10.0)
        user.connect_to_relays(["relay1"])

        # Should not crash
        user.post_text_note("Test message")
        user.schedule_next_post()

    def test_user_activation_with_relays_and_engine(self) -> None:
        """Test user activation when connected to relays with simulation engine."""
        mock_engine = Mock()
        mock_engine.current_time = 100.0

        user = HonestUserAgent("user1", simulation_engine=mock_engine)
        user.activate(10.0)  # Activate first
        user.connect_to_relays(["relay1"])  # Then connect to relays
        user.deactivate(20.0)  # Deactivate
        user.activate(30.0)  # Reactivate - this should trigger schedule_next_post

        # Should schedule a post event during reactivation since relays are connected
        mock_engine.schedule_event.assert_called()

    def test_user_activation_without_relays(self) -> None:
        """Test user activation when not connected to relays."""
        mock_engine = Mock()
        mock_engine.current_time = 100.0

        user = HonestUserAgent("user1", simulation_engine=mock_engine)
        user.activate(10.0)  # No relays connected

        # Should not schedule post event
        mock_engine.schedule_event.assert_not_called()

    def test_follow_self_user(self) -> None:
        """Test following yourself (edge case)."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        result = user.follow_user("user1")  # Follow self
        assert result is True
        assert "user1" in user.following

    def test_social_interaction_discover_already_following(self) -> None:
        """Test discovering a user already being followed."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        # First follow the user
        user.follow_user("user2")

        # Then discover them again
        event = Event(
            time=10.0,
            priority=0,
            event_type="social_interaction",
            data={
                "interaction_type": "discover_user",
                "target_user": "user2",
                "pubkey": "user2_pubkey",
            },
        )

        result = user.on_event(event)
        assert isinstance(result, list)
        assert len(user.following) == 1  # Should not duplicate

    def test_social_interaction_follow_decision_yes(self) -> None:
        """Test social interaction where user decides to follow."""
        # Create user with 100% follow ratio to guarantee follow decision
        behavior = UserBehaviorPattern(follow_ratio=1.0)
        user = HonestUserAgent("user1", behavior_pattern=behavior)
        user.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="social_interaction",
            data={
                "interaction_type": "discover_user",
                "target_user": "user2",
                "pubkey": "user2_pubkey",
            },
        )

        result = user.on_event(event)
        assert isinstance(result, list)
        assert "user2" in user.following  # Should follow the user

    def test_social_interaction_unknown_type(self) -> None:
        """Test handling unknown social interaction types."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="social_interaction",
            data={
                "interaction_type": "unknown_type",
                "target_user": "user2",
            },
        )

        result = user.on_event(event)
        assert isinstance(result, list)

    def test_user_lifecycle_go_online(self) -> None:
        """Test user lifecycle go online event."""
        mock_engine = Mock()
        mock_engine.current_time = 100.0

        user = HonestUserAgent("user1", simulation_engine=mock_engine)
        user.deactivate(10.0)  # Start offline

        event = Event(
            time=10.0,
            priority=0,
            event_type="user_lifecycle",
            data={"action": "go_online"},
        )

        result = user.on_event(event)
        assert isinstance(result, list)
        assert user.is_active()

    def test_user_lifecycle_unknown_action(self) -> None:
        """Test user lifecycle with unknown action."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="user_lifecycle",
            data={"action": "unknown_action"},
        )

        result = user.on_event(event)
        assert isinstance(result, list)

    def test_post_content_generation_variations(self) -> None:
        """Test that post content generation produces varied content."""
        user = HonestUserAgent("user1")

        # Generate multiple posts to test variety
        contents = [user.generate_post_content() for _ in range(10)]

        # Should get some variety (not all identical)
        unique_contents = set(contents)
        assert len(unique_contents) > 1  # Should have some variety

    def test_should_follow_user_edge_cases(self) -> None:
        """Test edge cases for follow decision logic."""
        # Zero follow ratio
        behavior = UserBehaviorPattern(follow_ratio=0.0)
        user = HonestUserAgent("user1", behavior_pattern=behavior)

        # Should never follow
        decisions = [user.should_follow_user("user2") for _ in range(20)]
        assert not any(decisions)

        # 100% follow ratio
        behavior = UserBehaviorPattern(follow_ratio=1.0)
        user = HonestUserAgent("user1", behavior_pattern=behavior)

        # Should always follow (if not already following)
        decisions = [user.should_follow_user("user2") for _ in range(20)]
        assert all(decisions)

    def test_post_scheduled_event_wrong_user(self) -> None:
        """Test handling post scheduled event for wrong user."""
        mock_engine = Mock()
        mock_engine.current_time = 100.0

        user = HonestUserAgent("user1", mock_engine)
        user.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="post_scheduled",
            data={"user_id": "user2"},  # Different user
        )

        result = user.on_event(event)
        assert isinstance(result, list)

        # Should not schedule any new events since it's not for this user
        assert mock_engine.schedule_event.call_count == 0

    def test_post_scheduled_event_no_relays(self) -> None:
        """Test handling post scheduled event when no relays connected."""
        mock_engine = Mock()
        mock_engine.current_time = 100.0

        user = HonestUserAgent("user1", mock_engine)
        user.activate(10.0)
        # Don't connect to any relays

        event = Event(
            time=10.0,
            priority=0,
            event_type="post_scheduled",
            data={"user_id": "user1"},
        )

        result = user.on_event(event)
        assert isinstance(result, list)

        # Should not post or schedule next post since no relays
        assert mock_engine.schedule_event.call_count == 0

    def test_social_interaction_no_target_user(self) -> None:
        """Test social interaction event without target user."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="social_interaction",
            data={
                "interaction_type": "discover_user",
                # No target_user field
            },
        )

        result = user.on_event(event)
        assert isinstance(result, list)

    def test_follow_user_event_no_target(self) -> None:
        """Test follow user event without target user."""
        user = HonestUserAgent("user1")
        user.activate(10.0)

        event = Event(
            time=10.0,
            priority=0,
            event_type="follow_user",
            data={
                # No target_user field
            },
        )

        result = user.on_event(event)
        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__])
