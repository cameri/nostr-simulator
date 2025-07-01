"""Tests for hash-link spam attack implementation."""

from unittest.mock import Mock

from ...simulation.events import Event
from ..base import AgentType
from .hash_link_spammer import (
    HashLinkSpammerAgent,
    LinkObfuscationConfig,
    LinkVariationStrategy,
)


class TestLinkObfuscationConfig:
    """Test LinkObfuscationConfig configuration."""

    def test_default_values(self) -> None:
        """Test default obfuscation configuration."""
        config = LinkObfuscationConfig()

        assert config.base_domains == ["example.com", "test.org", "malicious.net"]
        assert config.url_shorteners == ["bit.ly", "tinyurl.com", "t.co"]
        assert config.encoding_methods == ["url_encode", "base64", "hex"]
        assert config.domain_rotation_frequency == 5.0
        assert config.obfuscation_intensity == 0.7

    def test_custom_values(self) -> None:
        """Test custom obfuscation configuration."""
        config = LinkObfuscationConfig(
            base_domains=["evil.com", "bad.org"],
            url_shorteners=["short.ly"],
            encoding_methods=["rot13"],
            domain_rotation_frequency=10.0,
            obfuscation_intensity=0.9,
        )

        assert config.base_domains == ["evil.com", "bad.org"]
        assert config.url_shorteners == ["short.ly"]
        assert config.encoding_methods == ["rot13"]
        assert config.domain_rotation_frequency == 10.0
        assert config.obfuscation_intensity == 0.9


class TestLinkVariationStrategy:
    """Test LinkVariationStrategy configuration."""

    def test_default_values(self) -> None:
        """Test default strategy configuration."""
        strategy = LinkVariationStrategy()

        assert isinstance(strategy.obfuscation, LinkObfuscationConfig)
        assert strategy.payload_types == ["phishing", "malware", "scam"]
        assert strategy.evasion_techniques == [
            "subdomain_generation",
            "path_randomization",
            "parameter_injection",
            "url_shortening",
        ]
        assert strategy.messages_per_minute == 2.0
        assert strategy.coordinated_campaign is True

    def test_custom_values(self) -> None:
        """Test custom strategy configuration."""
        custom_obfuscation = LinkObfuscationConfig(
            base_domains=["custom.com"], domain_rotation_frequency=15.0
        )
        strategy = LinkVariationStrategy(
            obfuscation=custom_obfuscation,
            payload_types=["spam"],
            evasion_techniques=["encoding"],
            messages_per_minute=5.0,
            coordinated_campaign=False,
        )

        assert strategy.obfuscation == custom_obfuscation
        assert strategy.payload_types == ["spam"]
        assert strategy.evasion_techniques == ["encoding"]
        assert strategy.messages_per_minute == 5.0
        assert strategy.coordinated_campaign is False


class TestHashLinkSpammerAgent:
    """Test HashLinkSpammerAgent behavior."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.agent_id = "hash_link_spammer_1"
        self.strategy = LinkVariationStrategy()
        self.engine = Mock()
        self.engine.current_time = 0.0

        self.agent = HashLinkSpammerAgent(
            agent_id=self.agent_id,
            strategy=self.strategy,
            simulation_engine=self.engine,
        )
        self.agent.simulation_engine = self.engine

    def test_initialization(self) -> None:
        """Test agent initialization."""
        assert self.agent.agent_id == self.agent_id
        assert self.agent.agent_type == AgentType.MALICIOUS_USER
        assert self.agent.strategy == self.strategy
        assert self.agent.private_key is not None
        assert self.agent.public_key is not None

    def test_generate_obfuscated_link_basic(self) -> None:
        """Test basic link generation."""
        link = self.agent.generate_obfuscated_link("phishing")

        assert isinstance(link, str)
        assert len(link) > 0

        # Link should either contain a base domain OR be a shortened URL
        contains_base_domain = any(
            domain in link for domain in self.strategy.obfuscation.base_domains
        )
        is_shortened = any(
            shortener in link for shortener in self.strategy.obfuscation.url_shorteners
        )

        # Should be one or the other
        assert contains_base_domain or is_shortened

    def test_generate_obfuscated_link_with_shortener(self) -> None:
        """Test link generation with URL shortener."""
        # Patch random to ensure shortener is used
        import random

        original_random = random.random
        random.random = lambda: 0.1  # Force shortener usage

        try:
            link = self.agent.generate_obfuscated_link("phishing")
            # Should contain a shortener domain
            contains_shortener = any(
                shortener in link
                for shortener in self.strategy.obfuscation.url_shorteners
            )
            assert contains_shortener
        finally:
            random.random = original_random

    def test_apply_domain_rotation(self) -> None:
        """Test domain rotation functionality."""
        # Set up a configuration with at least 2 domains
        config = LinkObfuscationConfig(
            base_domains=["domain1.com", "domain2.com"], domain_rotation_frequency=5.0
        )
        strategy = LinkVariationStrategy(obfuscation=config)
        agent = HashLinkSpammerAgent("test", strategy, self.engine)

        # Set current domain to the first one
        agent.current_domain = "domain1.com"
        original_domain = agent.current_domain

        # Fast-forward time to trigger rotation (convert minutes to seconds)
        agent.last_domain_rotation = 0.0
        self.engine.current_time = (
            strategy.obfuscation.domain_rotation_frequency * 60.0 + 1.0
        )

        agent.apply_domain_rotation()

        # Domain should have changed since we have multiple domains
        assert agent.current_domain != original_domain
        assert agent.current_domain == "domain2.com"  # Should be the only other domain
        assert agent.last_domain_rotation == self.engine.current_time

    def test_apply_evasion_techniques(self) -> None:
        """Test evasion technique application."""
        base_url = "http://example.com/path"

        evasive_url = self.agent.apply_evasion_techniques(base_url)

        assert isinstance(evasive_url, str)
        assert len(evasive_url) >= len(base_url)  # Should be same or longer

    def test_generate_spam_content(self) -> None:
        """Test spam content generation."""
        content = self.agent.generate_spam_content("phishing")

        assert isinstance(content, str)
        assert len(content) > 0
        # Should contain at least one URL
        assert "http" in content.lower() or "https" in content.lower()

    def test_step_sends_messages(self) -> None:
        """Test that step method sends messages."""
        # Set up timing to trigger message sending
        self.agent.last_message_time = 0.0
        self.engine.current_time = 60.0  # 1 minute later

        self.agent.step()

        # Should have scheduled an event
        assert self.engine.schedule_event.called

        # Check the scheduled event
        call_args = self.engine.schedule_event.call_args
        event = call_args[0][0]
        assert isinstance(event, Event)
        assert event.event_type == "nostr_event"

    def test_step_respects_timing(self) -> None:
        """Test that step respects message timing."""
        # Set up timing to NOT trigger message sending
        self.agent.last_message_time = 0.0
        self.engine.current_time = 10.0  # Only 10 seconds later

        self.agent.step()

        # Should not have scheduled an event
        assert not self.engine.schedule_event.called

    def test_handle_message_basic(self) -> None:
        """Test basic message handling."""
        # Create a mock message
        message = Mock()
        message.message_type = "test_message"
        message.content = {"test": "data"}

        # Should not raise an exception
        self.agent.handle_message(message)

    def test_coordinated_campaign_behavior(self) -> None:
        """Test coordinated campaign behavior."""
        # Enable coordination
        self.agent.strategy.coordinated_campaign = True

        # Create coordination message
        message = Mock()
        message.message_type = "coordination_signal"
        message.content = {"action": "start_campaign", "target": "example.com"}

        self.agent.handle_message(message)

        # Should update coordination state
        assert hasattr(self.agent, "coordination_active")

    def test_link_encoding_methods(self) -> None:
        """Test different encoding methods."""
        base_url = "http://example.com/malicious"

        # Test URL encoding
        encoded_url = self.agent.encode_url(base_url, "url_encode")
        assert "%3A" in encoded_url or base_url == encoded_url  # : becomes %3A

        # Test Base64 encoding
        b64_url = self.agent.encode_url(base_url, "base64")
        assert b64_url != base_url

        # Test hex encoding
        hex_url = self.agent.encode_url(base_url, "hex")
        assert hex_url != base_url

    def test_subdomain_generation(self) -> None:
        """Test subdomain generation for evasion."""
        domain = "example.com"

        subdomain_url = self.agent.generate_subdomain(domain)

        assert domain in subdomain_url
        assert subdomain_url != f"http://{domain}"  # Should have subdomain

    def test_path_randomization(self) -> None:
        """Test path randomization technique."""
        base_url = "http://example.com"

        randomized_url = self.agent.randomize_path(base_url)

        assert randomized_url.startswith(base_url)
        assert len(randomized_url) > len(base_url)  # Should have added path

    def test_parameter_injection(self) -> None:
        """Test parameter injection technique."""
        base_url = "http://example.com/path"

        injected_url = self.agent.inject_parameters(base_url)

        assert "?" in injected_url or "&" in injected_url  # Should have parameters

    def test_payload_content_variation(self) -> None:
        """Test that different payload types generate different content."""
        phishing_content = self.agent.generate_spam_content("phishing")
        malware_content = self.agent.generate_spam_content("malware")
        scam_content = self.agent.generate_spam_content("scam")

        # Content should be different for different payload types
        assert phishing_content != malware_content
        assert malware_content != scam_content
        assert phishing_content != scam_content

    def test_invalid_payload_type(self) -> None:
        """Test handling of invalid payload type."""
        # Should not raise exception, should use default
        content = self.agent.generate_spam_content("invalid_type")
        assert isinstance(content, str)
        assert len(content) > 0

    def test_empty_configuration_handling(self) -> None:
        """Test handling of empty configuration lists."""
        # Create config with empty lists
        empty_config = LinkObfuscationConfig(
            base_domains=[],
            url_shorteners=[],
            encoding_methods=[],
        )
        strategy = LinkVariationStrategy(obfuscation=empty_config)

        # Should still work with fallback values
        agent = HashLinkSpammerAgent("test", strategy)
        link = agent.generate_obfuscated_link("phishing")

        assert isinstance(link, str)
        assert len(link) > 0

    def test_agent_type_property(self) -> None:
        """Test agent type property."""
        assert self.agent.agent_type == AgentType.MALICIOUS_USER

    def test_statistics_tracking(self) -> None:
        """Test that agent tracks statistics."""
        initial_count = getattr(self.agent, "messages_sent", 0)

        # Send a message
        self.agent.last_message_time = 0.0
        self.engine.current_time = 60.0
        self.agent.step()

        # Should increment message count
        current_count = getattr(self.agent, "messages_sent", 0)
        assert current_count > initial_count
