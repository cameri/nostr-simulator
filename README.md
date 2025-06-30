# Nostr Simulator

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

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Individual tools
black .
isort .
ruff check --fix .
mypy .
bandit -r src/
```

#### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term
```

#### Running the Simulator

```bash
# Run the main simulator (basic simulation)
python -m src.nostr_simulator.main

# Run anti-spam strategy scenarios
python -m src.run_scenarios help          # List available scenarios
python -m src.run_scenarios pow           # Run Proof of Work scenario
python -m src.run_scenarios multi         # Run multi-strategy scenario
python -m src.run_scenarios attack        # Run attack simulation scenario
python -m src.run_scenarios all           # Run all scenarios
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
- Changes: `changelog.md`
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
