# Changelog

All notable changes to the Nostr Simulator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## \[Unreleased\]

### Added

- Enhanced coding standards in copilot-instructions.md with Test-Driven Development (TDD) requirements
- Added SOLID principles documentation (SRP, OCP, LSP, ISP, DIP)
- Added top 10 clean code practices guidelines
- **Phase 1 Completed: Foundation and Core Infrastructure**
  - Created complete project structure (src/, tests/, docs/)
  - Implemented Poetry configuration with pyproject.toml
  - Set up comprehensive logging configuration with YAML support
  - Created robust configuration management system with Pydantic validation
  - Implemented discrete event simulation engine with priority queue
  - Designed and implemented base agent framework with lifecycle management
  - Created comprehensive CI/CD pipeline with GitHub Actions
  - Implemented development tools: mypy, ruff, black, isort, pytest
  - Added pre-commit hooks for code quality enforcement
  - Set up automated dependency updates and release workflows

### Fixed

- Resolved type checking issues in Event.__eq__ method for proper LSP compliance
- Fixed missing type annotations for generic Dict types
- Updated ruff configuration to use new lint section format
- Installed types-PyYAML for proper YAML typing support

### Validated

- All 27 tests passing successfully
- Linting and formatting checks passing
- Type checking operational (with expected development-phase warnings)
- Simulator runs successfully and creates proper log files
- CI/CD workflows properly configured and tested

## [0.1.0] - 2025-06-15

### Added

- Initial project setup with Python-based simulator framework
- Copilot instructions for Python development workflow
- Python coding standards and guidelines
- Comprehensive TODO.md with 7-phase development roadmap
- Definition of done criteria in `.github/definition-of-done.md`
- Project structure with clear task breakdown and completion tracking
- Development environment setup with pyproject.toml and setup.sh script
- Pre-commit hooks configuration with code formatting, linting, and type checking
- Comprehensive .gitignore for Python projects
- README.md with quick start guide and development workflow documentation
- SETUP_ALTERNATIVES.md with alternative installation methods for SSL issues
- Git and Jujutsu version control initialization

### Changed

- Converted project from TypeScript/NestJS to Python-based simulator
- Updated all dependencies to latest versions (June 2025):
  - pre-commit: 3.8.0 → 4.0.1
  - black: 24.8.0 → 24.10.0
  - mypy: 1.11.2 → 1.13.0
  - ruff: 0.6.8 → 0.8.4
  - pytest: 8.3.3 → 8.3.4
  - pytest-cov: 5.0.0 → 6.0.0
  - mesa: 2.4.0 → 3.0.0
  - numpy: 2.1.1 → 2.2.0
  - pandas: 2.2.3 → 2.3.0
  - matplotlib: 3.9.2 → 3.10.0
  - pydantic: 2.9.2 → 2.10.0
  - rich: 13.8.1 → 13.9.0

### Deprecated

### Removed

### Fixed

### Security
