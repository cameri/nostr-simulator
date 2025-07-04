# Nostr Simulator

[![CI](https://github.com/cameri/nostr-simulator/workflows/CI/badge.svg)](https://github.com/cameri/nostr-simulator/actions)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type Checking: mypy](https://img.shields.io/badge/type_checking-mypy-blue.svg)](https://mypy.readthedocs.io/)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)

A Python-based simulator for decentralized anti-spam and anti-abuse strategies on Nostr using agent-based modeling.

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Git
- Jujutsu (jj) for version control

### Setup

1. **Clone and setup the project:**

   ```bash
   git clone <your-repo-url>
   cd nostr-simulator
   ./setup.sh
   ```

1. **Activate the virtual environment:**

   ```bash
   source .venv/bin/activate
   ```

1. **Verify installation:**

   ```bash
   python -m pytest --version
   pre-commit --version
   ```

### Development Workflow

#### Code Quality Tools

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **Ruff**: Fast Python linter
- **MyPy**: Type checking
- **Bandit**: Security linting
- **mdformat**: Markdown formatting

#### Running Quality Checks

The project uses [poethepoet](https://github.com/nat-n/poethepoet) for centralized command management. See [`docs/commands.md`](docs/commands.md) for complete command reference.

```bash
# Run all quality checks (formatting, linting, type checking)
poetry run poe check-all

# Format code and sort imports
poetry run poe format-all

# Run individual checks
poetry run poe format-check    # Check code formatting
poetry run poe lint           # Check with Ruff linter
poetry run poe type-check     # Check types with mypy
poetry run poe security       # Security scan with Bandit
```

#### Testing

```bash
# Run tests with coverage (recommended)
poetry run poe test-cov

# Run tests without coverage (faster)
poetry run poe test

# Run full CI pipeline (quality checks + tests)
poetry run poe ci
```

#### Running the Simulator

```bash
# Run the main simulator (basic simulation)
poetry run poe simulate

# Run anti-spam strategy scenarios
poetry run poe run-scenarios help          # List available scenarios
poetry run poe run-scenarios pow           # Run Proof of Work scenario
poetry run poe run-scenarios multi         # Run multi-strategy scenario
poetry run poe run-scenarios attack        # Run attack simulation scenario
poetry run poe run-scenarios all           # Run all scenarios
```

#### Available Scenarios

The project includes several scenarios to demonstrate anti-spam strategies:

- **`pow`**: Demonstrates Proof of Work anti-spam strategy with different difficulty levels
- **`multi`**: Shows multiple strategies working together (PoW + Rate Limiting)
- **`attack`**: Simulates various attack vectors (Sybil, burst spam, hash-link spam, replay attacks)
- **`all`**: Runs all available scenarios sequentially

### Project Structure

```text
├── .github/                 # GitHub configuration and documentation
├── src/                     # Source code
├── tests/                   # Test files
├── docs/                    # Documentation
├── pyproject.toml           # Python dependencies and project configuration
├── setup.sh                 # Setup script
├── .pre-commit-config.yaml  # Pre-commit configuration
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

### Version Control

This project uses both Git and Jujutsu (jj). See `.github/using-jj-instructions.md` for detailed instructions on using jj.

### Dependencies

The project includes dependencies for:

- **Development Tools**: pre-commit, black, isort, ruff, mypy, bandit
- **Documentation**: mkdocs, mkdocs-material, mdformat with mkdocs flavor
- **Testing**: pytest, pytest-cov
- **Simulation**: mesa (agent-based modeling), numpy, pandas, matplotlib, seaborn, networkx
- **Utilities**: pydantic, pyyaml, rich

### Configuration

- **Type Checking**: Configured via `mypy.ini` or `pyproject.toml`
- **Code Formatting**: Black and isort configured to work together
- **Pre-commit**: Runs formatting, linting, and type checking on commit
- **Testing**: Configured for 100% coverage requirement

### Documentation

- Project roadmap: `TODO.md`
- Changes: `CHANGELOG.md`
- Simulator details: `SIMULATOR.md`
- Coding standards: `.github/python-instructions.md`
- Definition of done: `.github/definition-of-done.md`

## Contributing

1. Activate the virtual environment: `source .venv/bin/activate`
1. Make your changes
1. Run quality checks: `pre-commit run --all-files`
1. Run tests: `pytest --cov=src --cov-report=term`
1. Update documentation as needed
1. Commit using jj or git

## License

Ricardo Cabral's Nostr Simulator is licensed under the MIT License. See `LICENSE.md` for details.
