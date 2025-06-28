# Copilot Instructions

This project is a Python-based simulator for decentralized anti-spam and anti-abuse strategies on Nostr. The simulator uses agent-based modeling to test various defense mechanisms against adversarial attacks without compromising decentralization or offline capability.

## Coding Standards

- Follow PEP 8 Python style guidelines
- Use type hints for all function signatures and class attributes
- Detailed coding standards are outlined in the `python-instructions.md` file

## General

- Summarize changes in the changelog.md file
- Use docstrings for all classes and functions following Google style
- Implement proper error handling and logging
- Follow the project roadmap outlined in TODO.md
- Ensure all tasks meet the definition of done criteria in `.github/definition-of-done.md`
- Mark completed tasks with [x] in TODO.md

### Dependency management

- Use poetry for dependency management and virtual environment handling
- Keep dependencies in `pyproject.toml`
- Use pinned versions for reproducible builds

### Build & run

- After you are done making changes, always try to check the types, lint and format code, test the simulator and ensure coverage is 100%. Use the following commands to do so:

To install dependencies:
poetry install

To run type checks:
poetry run mypy .

To lint:
poetry run ruff check --fix .

To format:
poetry run black .
poetry run isort .

To run tests:
poetry run pytest

To run tests with coverage:
poetry run pytest --cov=src --cov-report=html --cov-report=term

To run the simulator:
poetry run python -m src.main


## Version Control

- USe `jj` for version control. Detailed instructions are in the `using-jj-instructions.md` file.

### Simulation Framework

- Use discrete event simulation principles
- Implement agent-based models for different actor types:
  - Honest users
  - Malicious actors (spammers, attackers)
  - Relays
  - Clients
- All strategies must preserve offline capability and decentralization
- Support pluggable anti-spam strategies and attack vectors

### Anti-Spam Strategies to Implement

- Proof of Work (PoW)
- Web of Trust (WoT)
- Hashchain / Rolling Codes
- Local reputation tokens
- Rate limiting
- Event age proof
- Group signature schemes

### Attack Vectors to Model

- Sybil spam attacks
- Burst spam
- Hash-link spam
- Replay attacks
- Offline abuse

### Evaluation Metrics

- False positives/negatives
- Relay load (bandwidth, CPU)
- Latency impact
- Spam reduction percentage
- Resilience to offline abuse
- Sybil resistance
