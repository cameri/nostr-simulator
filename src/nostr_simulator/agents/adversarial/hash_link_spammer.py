"""Hash-link spam attack implementation for Nostr simulation.

This module implements agents that can perform hash-link spam attacks by posting
obfuscated malicious links through various evasion techniques.
"""

from __future__ import annotations

import base64
import random
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from ...protocol.events import NostrEvent, NostrEventKind
from ...protocol.keys import NostrKeyPair
from ...simulation.events import Event
from ..base import AgentType, BaseAgent, Message


@dataclass
class LinkObfuscationConfig:
    """Configuration for link obfuscation techniques."""

    base_domains: list[str] = field(
        default_factory=lambda: ["example.com", "test.org", "malicious.net"]
    )
    url_shorteners: list[str] = field(
        default_factory=lambda: ["bit.ly", "tinyurl.com", "t.co"]
    )
    encoding_methods: list[str] = field(
        default_factory=lambda: ["url_encode", "base64", "hex"]
    )
    domain_rotation_frequency: float = 5.0  # Minutes between domain changes
    obfuscation_intensity: float = 0.7  # How aggressive obfuscation is (0.0-1.0)


@dataclass
class LinkVariationStrategy:
    """Configuration for hash-link spam behavior."""

    # Obfuscation settings
    obfuscation: LinkObfuscationConfig = field(default_factory=LinkObfuscationConfig)

    # Attack patterns
    payload_types: list[str] = field(
        default_factory=lambda: ["phishing", "malware", "scam"]
    )
    evasion_techniques: list[str] = field(
        default_factory=lambda: [
            "subdomain_generation",
            "path_randomization",
            "parameter_injection",
            "url_shortening",
        ]
    )

    # Timing and coordination
    messages_per_minute: float = 2.0  # Slower rate to avoid detection
    coordinated_campaign: bool = True  # Coordinate with other agents


class HashLinkSpammerAgent(BaseAgent):
    """Agent that performs hash-link spam attacks using obfuscated malicious links."""

    def __init__(
        self,
        agent_id: str,
        strategy: LinkVariationStrategy,
        simulation_engine: Any = None,
    ) -> None:
        """Initialize the hash-link spammer agent.

        Args:
            agent_id: Unique identifier for this agent
            strategy: Configuration for link variation and obfuscation
            simulation_engine: Reference to simulation engine
        """
        super().__init__(agent_id, AgentType.MALICIOUS_USER, simulation_engine)
        self.strategy = strategy
        self.private_key = NostrKeyPair.generate()
        self.public_key = self.private_key.public_key

        # State tracking
        self.messages_sent = 0
        self.last_message_time = 0.0
        self.current_domain = random.choice(
            self.strategy.obfuscation.base_domains or ["fallback.com"]
        )
        self.last_domain_rotation = 0.0
        self.coordination_active = False
        self.current_campaign_target: str | None = None

    def step(self) -> None:
        """Execute one simulation step."""
        if not self.simulation_engine:
            return

        current_time = self.simulation_engine.current_time

        # Check if it's time to rotate domain
        self.apply_domain_rotation()

        # Check if it's time to send a message
        message_interval = 60.0 / self.strategy.messages_per_minute
        if current_time - self.last_message_time >= message_interval:
            self.send_hash_link_spam()
            self.last_message_time = current_time

    def apply_domain_rotation(self) -> None:
        """Rotate to a new domain if enough time has passed."""
        if not self.simulation_engine:
            return

        current_time = self.simulation_engine.current_time
        rotation_interval = self.strategy.obfuscation.domain_rotation_frequency * 60.0

        if current_time - self.last_domain_rotation >= rotation_interval:
            available_domains = self.strategy.obfuscation.base_domains or [
                "fallback.com"
            ]
            if len(available_domains) > 1:
                # Choose a different domain
                other_domains = [
                    d for d in available_domains if d != self.current_domain
                ]
                new_domain = random.choice(other_domains)
            else:
                # Only one domain available, keep the same one
                new_domain = available_domains[0]
            self.current_domain = new_domain
            self.last_domain_rotation = current_time

    def send_hash_link_spam(self) -> None:
        """Send a hash-link spam message."""
        if not self.simulation_engine:
            return

        # Choose a random payload type
        payload_type = random.choice(self.strategy.payload_types or ["generic"])

        # Generate spam content with obfuscated links
        content = self.generate_spam_content(payload_type)

        # Create and sign the event
        event = NostrEvent(
            kind=NostrEventKind.TEXT_NOTE,
            content=content,
            pubkey=self.public_key,
            created_at=int(self.simulation_engine.current_time),
            tags=[],
        )

        # Sign the event
        event_dict = {
            "kind": event.kind.value,
            "content": event.content,
            "created_at": event.created_at,
            "pubkey": event.pubkey,
            "tags": [tag.to_list() for tag in event.tags],
        }
        import json

        event.sig = self.private_key.sign_event(
            json.dumps(event_dict, separators=(",", ":"), ensure_ascii=False)
        )

        # Schedule the event to be broadcast
        simulation_event = Event(
            time=self.simulation_engine.current_time,
            priority=1,
            event_type="nostr_event",
            data={"event": event, "source_agent": self.agent_id},
        )

        self.simulation_engine.schedule_event(simulation_event)
        self.messages_sent += 1

    def generate_spam_content(self, payload_type: str) -> str:
        """Generate spam content with obfuscated links.

        Args:
            payload_type: Type of malicious payload to generate

        Returns:
            Content string with obfuscated malicious links
        """
        # Generate base link
        obfuscated_link = self.generate_obfuscated_link(payload_type)

        # Create contextual message based on payload type
        content_templates = {
            "phishing": [
                f"Urgent security update required! Verify your account: {obfuscated_link}",
                f"Your account will be suspended. Click here to prevent: {obfuscated_link}",
                f"Important notification waiting for you: {obfuscated_link}",
            ],
            "malware": [
                f"Amazing new software download: {obfuscated_link}",
                f"Free premium tools available here: {obfuscated_link}",
                f"Latest updates and patches: {obfuscated_link}",
            ],
            "scam": [
                f"You've won a prize! Claim it here: {obfuscated_link}",
                f"Limited time offer - act now: {obfuscated_link}",
                f"Exclusive deal just for you: {obfuscated_link}",
            ],
        }

        templates = content_templates.get(
            payload_type,
            [
                f"Check this out: {obfuscated_link}",
                f"Interesting link: {obfuscated_link}",
            ],
        )

        return random.choice(templates)

    def generate_obfuscated_link(self, payload_type: str) -> str:
        """Generate an obfuscated malicious link.

        Args:
            payload_type: Type of payload for the link

        Returns:
            Obfuscated URL string
        """
        # Start with base domain
        base_url = f"http://{self.current_domain}"

        # Add payload-specific path
        payload_paths = {
            "phishing": ["/login", "/verify", "/secure", "/account"],
            "malware": ["/download", "/update", "/install", "/tools"],
            "scam": ["/claim", "/winner", "/offer", "/prize"],
        }

        paths = payload_paths.get(payload_type, ["/content"])
        base_url += random.choice(paths)

        # Apply evasion techniques
        obfuscated_url = self.apply_evasion_techniques(base_url)

        # Potentially use URL shortener
        if (
            self.strategy.obfuscation.url_shorteners
            and random.random() < 0.3  # 30% chance
        ):
            shortener = random.choice(self.strategy.obfuscation.url_shorteners)
            # Simulate shortened URL
            short_id = "".join(
                random.choices(
                    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                    k=6,
                )
            )
            obfuscated_url = f"http://{shortener}/{short_id}"

        return obfuscated_url

    def apply_evasion_techniques(self, base_url: str) -> str:
        """Apply various evasion techniques to a URL.

        Args:
            base_url: Base URL to obfuscate

        Returns:
            URL with evasion techniques applied
        """
        url = base_url

        # Apply random subset of evasion techniques
        techniques = self.strategy.evasion_techniques[:]
        random.shuffle(techniques)

        # Apply techniques based on obfuscation intensity
        num_techniques = max(
            1, int(len(techniques) * self.strategy.obfuscation.obfuscation_intensity)
        )

        for technique in techniques[:num_techniques]:
            if technique == "subdomain_generation":
                # Extract domain and add subdomain
                if "://" in url:
                    protocol, rest = url.split("://", 1)
                    if "/" in rest:
                        domain, path = rest.split("/", 1)
                        url = f"{protocol}://{self.generate_subdomain(domain)}/{path}"
                    else:
                        url = f"{protocol}://{self.generate_subdomain(rest)}"

            elif technique == "path_randomization":
                url = self.randomize_path(url)

            elif technique == "parameter_injection":
                url = self.inject_parameters(url)

            elif technique == "url_shortening":
                # Already handled in generate_obfuscated_link
                pass

        return url

    def generate_subdomain(self, domain: str) -> str:
        """Generate a subdomain for evasion.

        Args:
            domain: Base domain

        Returns:
            Domain with subdomain prepended
        """
        subdomains = ["www", "secure", "login", "app", "api", "cdn", "static"]
        subdomain = random.choice(subdomains)

        # Add random characters sometimes
        if random.random() < 0.3:
            random_suffix = "".join(random.choices("0123456789", k=2))
            subdomain += random_suffix

        return f"{subdomain}.{domain}"

    def randomize_path(self, url: str) -> str:
        """Add randomized path components to URL.

        Args:
            url: URL to modify

        Returns:
            URL with randomized path
        """
        # Add random path components
        random_paths = ["data", "api", "v1", "v2", "files", "assets", "public"]
        random_path = random.choice(random_paths)

        # Add random identifier
        random_id = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=8))

        if url.endswith("/"):
            return f"{url}{random_path}/{random_id}"
        else:
            return f"{url}/{random_path}/{random_id}"

    def inject_parameters(self, url: str) -> str:
        """Inject random parameters into URL.

        Args:
            url: URL to modify

        Returns:
            URL with injected parameters
        """
        params = {
            "ref": "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6)),
            "src": random.choice(["email", "social", "ad", "organic"]),
            "utm_source": random.choice(["campaign1", "campaign2", "direct"]),
            "t": str(int(random.random() * 1000000)),
        }

        # Add 1-3 random parameters
        num_params = random.randint(1, 3)
        selected_params = dict(random.sample(list(params.items()), num_params))

        if "?" in url:
            separator = "&"
        else:
            separator = "?"

        param_string = "&".join(f"{k}={v}" for k, v in selected_params.items())
        return f"{url}{separator}{param_string}"

    def encode_url(self, url: str, method: str) -> str:
        """Encode URL using specified method.

        Args:
            url: URL to encode
            method: Encoding method to use

        Returns:
            Encoded URL
        """
        if method == "url_encode":
            return urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=")
        elif method == "base64":
            encoded_bytes = base64.b64encode(url.encode("utf-8"))
            return encoded_bytes.decode("utf-8")
        elif method == "hex":
            return url.encode("utf-8").hex()
        else:
            return url  # Fallback to original

    def handle_message(self, message: Message) -> None:
        """Handle incoming messages from other agents.

        Args:
            message: Message to handle
        """
        if message.message_type == "coordination_signal":
            content = message.content
            if content.get("action") == "start_campaign":
                self.coordination_active = True
                self.current_campaign_target = content.get("target")
            elif content.get("action") == "stop_campaign":
                self.coordination_active = False
                self.current_campaign_target = None

    # Abstract methods implementation
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
        pass

    def on_message_received(self, message: Message) -> None:
        """Handle received messages.

        Args:
            message: The received message.
        """
        self.handle_message(message)

    def on_event(self, event: Event) -> list[Event]:
        """Handle simulation events.

        Args:
            event: The event to handle.

        Returns:
            List of new events generated.
        """
        # Hash-link spammers typically don't generate events directly
        return []
