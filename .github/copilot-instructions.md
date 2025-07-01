# Copilot Instructions

This project is a Python-based simulator for decentralized anti-spam and anti-abuse strategies on Nostr. The simulator uses agent-based modeling to test various defense mechanisms against adversarial attacks without compromising decentralization or offline capability.

## Coding Standards

- Follow PEP 8 Python style guidelines
- Use type hints for all function signatures and class attributes
- Detailed coding standards are outlined in the `python-instructions.md` file

### Test-Driven Development (TDD)

- Write tests first, then implement the functionality
- Follow the Red-Green-Refactor cycle: write failing test, make it pass, refactor
- Maintain 100% test coverage
- Use descriptive test names that clearly indicate what is being tested

### SOLID Principles

- **Single Responsibility Principle (SRP)**: Each class should have only one reason to change
- **Open/Closed Principle (OCP)**: Software entities should be open for extension but closed for modification
- **Liskov Substitution Principle (LSP)**: Objects of a superclass should be replaceable with objects of a subclass
- **Interface Segregation Principle (ISP)**: No client should be forced to depend on methods it does not use
- **Dependency Inversion Principle (DIP)**: Depend on abstractions, not concretions

### Clean Code Practices

1. **Meaningful Names**: Use intention-revealing names for variables, functions, and classes
1. **Small Functions**: Keep functions small and focused on a single task
1. **Function Arguments**: Minimize the number of function arguments (ideally 0-2)
1. **No Comments**: Write self-documenting code; use comments only when necessary
1. **Consistent Formatting**: Apply consistent indentation, spacing, and code structure
1. **Error Handling**: Handle errors gracefully with proper exception handling
1. **No Code Duplication**: Follow the DRY (Don't Repeat Yourself) principle
1. **Single Level of Abstraction**: Keep functions at a single level of abstraction
1. **Avoid Deep Nesting**: Use early returns and guard clauses to reduce complexity
1. **Use Descriptive Variable Names**: Avoid abbreviations and use searchable names

## General

- Summarize changes in the changelog.md file
- Use docstrings for all classes and functions following Google style
- Implement proper error handling and logging
- Follow the project roadmap outlined in TODO.md
- Ensure all tasks meet the definition of done criteria in `.github/definition-of-done.md`
- Mark completed tasks with \[x\] in TODO.md

### Dependency management

- Use poetry for dependency management and virtual environment handling
- Keep dependencies in `pyproject.toml`
- Use pinned versions for reproducible builds

### Build & run

- After you are done making changes, always try to check the types, lint and format code, test the simulator and ensure coverage is 90%. Use the following commands to do so:

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

## Code Graph Database Workflow

1. Update the code graph database to the latest code structure by running the code analyzer on the `src` folder.

2. Always query the code graph to understand existing structure before writing new code.

3. Validate references to code entities using Neo4j queries to ensure accuracy and prevent hallucinations.

Find more details (schemas, example queries) in the `.github/code-graph-database-instructions.md` file.

## Version Control

- Avoid using Git, use Jujutsu (jj) for version control. Use the instructions in the `using-jj-instructions.md` file.


### Evaluation Metrics

- False positives/negatives
- Relay load (bandwidth, CPU)
- Latency impact
- Spam reduction percentage
- Resilience to offline abuse
- Sybil resistance

## Documentation

- Project roadmap: `TODO.md`
- Changes: `changelog.md`
- Simulator details: `SIMULATOR.md`
- Coding standards: `.github/python-instructions.md`
- Code graph database usage: `.github/code-graph-database-instructions.md`

Keep all documentation up-to-date with the latest project changes and ensure it is clear and concise.
