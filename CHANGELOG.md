# Changelog

All notable changes to the Nostr Simulator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## \[Unreleased\]

### Added (2025-01-01)

- **� Core Metrics System Implementation**
  - Implemented comprehensive Core Metrics System with false positive/negative tracking
  - Added relay load monitoring for CPU usage and bandwidth consumption
  - Created latency measurement system for processing, validation, and strategy execution
  - Implemented spam reduction calculation with effectiveness metrics
  - Added resilience metrics for offline attack detection and sybil resistance
  - Created CoreMetricsCollector as a central interface for all metrics
  - Integrated metrics system with enhanced simulation engine
  - Added comprehensive test suite with 100% coverage for all metrics classes
  - Created demo script showcasing metrics collection and reporting
  - Fixed percentile calculation algorithms for accurate statistical reporting
  - Updated TODO.md to mark all core metrics system tasks as completed

- **�🔁 Replay Attack Implementation**
  - Implemented comprehensive ReplayAttackerAgent with configurable attack patterns
  - Added event collection and replay mechanisms with timing strategies
  - Implemented cross-relay replay capabilities with amplification
  - Added detection evasion techniques including key rotation and content modification
  - Created comprehensive test suite with 41 test cases achieving high coverage
  - Added replay attack scenarios and demonstration script
  - Updated TODO.md to mark all replay attack tasks as completed

### Fixed (2025-01-25)

- **Jujutsu Command Naming**: Corrected naming convention for clarity
  - Renamed `jj-create-commit` to `jj-commit` for interactive commits
  - Renamed `jj-commit-all` to `jj-create-commit` for commits with messages
  - Updated documentation to reflect accurate command naming

### Added (2025-01-25)

- **✅ COMPLETED Centralized Command Management System**
  - Implemented poethepoet task runner for centralized project command management
  - Added comprehensive `[tool.poe.tasks]` section to `pyproject.toml` as single source of truth
  - **Command Categories:**
    - Code formatting: `format`, `format-check`, `sort-imports`, `sort-imports-check`, `format-all`
    - Linting and type checking: `lint`, `lint-fix`, `type-check`
    - Testing: `test`, `test-cov`, `test-cov-xml`, `test-fast`, `test-no-cov`, `test-watch`, `cov-report`
    - Quality workflows: `check-all`, `quality`, `ci` (full CI pipeline)
    - Application: `simulate`, `run-scenarios`
    - Documentation: `docs-serve`, `docs-build`, `docs-clean`
    - Maintenance: `clean`, `clean-all`, `update-deps`, `show-outdated`, `security`
    - Development workflows: `setup`, `pre-commit`
  - **Benefits Achieved:**
    - Single source of truth for all project commands
    - Consistent command execution across local development and CI/CD
    - Easy maintenance (e.g., coverage threshold changes in one place)
    - Built-in task composition and dependencies
    - Environment variable management (COVERAGE_THRESHOLD=90, PYTHONPATH=src)
  - Updated CI workflows to use centralized commands (`poetry run poe ci`)
  - Updated copilot instructions to reference new command structure
  - Created comprehensive documentation in `docs/commands.md`
  - **Jujutsu Version Control Integration:**
    - Added 12 common jj commands: `jj-status`, `jj-log`, `jj-diff`, `jj-commit`, `jj-push`, `jj-pull`, `jj-new`, `jj-describe`, `jj-squash`, `jj-abandon`, `jj-sync`, `jj-clean-abandoned`
    - Commands use `--no-pager` flag to output directly to console without requiring user interaction
    - Added workflow commands: `prepare-commit`, `commit-ready`, `safe-commit`, `quick-save`
    - All jj commands now accessible via consistent `poetry run poe jj-*` interface

### Changed (2025-01-25)

- **Repository Standardization**
  - Renamed `changelog.md` to `CHANGELOG.md` following standard conventions
  - Added comprehensive shields.io badges to README.md:
    - CI status badge with GitHub Actions integration
    - Python version requirement badge (3.11+)
    - Code quality tool badges (Black, Ruff, mypy, Bandit)
    - Development tool badges (pre-commit, Poetry)
    - License badge (MIT)
  - Updated all file references from `changelog.md` to `CHANGELOG.md` in documentation

### Added (2025-01-24)

- **✅ COMPLETED Phase 4 Sybil Attack Implementation**
  - Implemented comprehensive adversarial agent framework for simulating Sybil attacks
  - Added `SybilAttackerAgent` class with sophisticated attack patterns and behaviors
  - Created `SybilAttackPattern` enum for different attack strategies (COORDINATED, BURST, STEALTH, MIMICRY)
  - Implemented `SybilIdentity` management system for multiple identity handling
  - **Attack Capabilities:**
    - Multiple identity creation and management (up to 1000 identities)
    - Identity switching strategies with configurable timing and patterns
    - Coordinated attack behaviors with synchronized spam campaigns
    - Detection evasion mechanisms including dormancy and identity replacement
    - Spam event generation with realistic content variation
    - Social engineering attempts through follower relationship establishment
  - **Identity Management Features:**
    - Dynamic identity switching based on time patterns or detection risk
    - Identity dormancy periods to evade detection algorithms
    - Identity reactivation strategies for long-term attack persistence
    - Automatic identity replacement when detection threshold is exceeded
  - **Coordination and Stealth:**
    - Coordination group formation for synchronized multi-identity attacks
    - Detection handling with configurable response strategies
    - Metrics tracking for attack effectiveness and detection avoidance
    - Realistic user behavior mimicry to blend with legitimate traffic
  - **Technical Implementation:**
    - Full compliance with `BaseAgent` interface and lifecycle management
    - Comprehensive type annotations and error handling
    - Extensive test coverage with 35 test cases covering all major behaviors
    - Integration with existing simulation engine and metrics collection
    - Support for configurable attack parameters and behavior patterns
  - **Files Added:**
    - `src/nostr_simulator/agents/adversarial/__init__.py`
    - `src/nostr_simulator/agents/adversarial/sybil_attacker.py`
    - `src/nostr_simulator/agents/adversarial/test_sybil_attacker.py`
  - **Updated Files:**
    - `src/nostr_simulator/agents/__init__.py` - Added adversarial agent imports
  - All code passes type checking (mypy), linting (ruff), formatting (black, isort), and testing (pytest)
  - Ready for integration with attack simulation scenarios and metrics evaluation

### Added (2025-06-29)

- **✅ COMPLETED Hashchain and Rolling Codes Scenario Implementation**
  - Added comprehensive hashchain scenario demonstrating cryptographic rolling codes
  - Created scenarios for both HashchainRollingCodes and TimeBasedCodeRotation strategies
  - Implemented test cases for legitimate user behavior and spam attack patterns
  - Added clock skew tolerance testing with different time offsets
  - Created performance comparison between hashchain and time-based strategies
  - Added comprehensive demonstration of replay attack prevention
  - Updated scenarios package to include and export hashchain scenario
  - Fixed type annotations and code formatting for consistency
  - All tests pass with proper error handling and validation

- **✅ COMPLETED Phase 3 Proof of Work (PoW) Implementation** (Commit: 7d5655f8)
  - Implemented comprehensive anti-spam strategy framework with base classes
  - Added full Proof of Work strategy with adaptive difficulty adjustment
  - Created PoW difficulty calculation based on leading zero bits in event IDs
  - Implemented Bitcoin-style difficulty adjustment algorithm (2016 block periods)
  - Added performance metrics collection and tracking
  - Created mining utilities with timeout and attempt limits for safe operation
  - Added extensive test coverage (24 tests, 100% coverage for new modules)
  - Optimized for fast test execution (all tests run in <1 second)
  - Following TDD principles with deterministic, non-computational tests
  - **Technical Details:**
    - `AntiSpamStrategy` abstract base class with proper interfaces
    - `StrategyResult` dataclass for standardized evaluation results
    - `ProofOfWorkStrategy` with configurable min/max difficulty (8-24 bits default)
    - Adaptive difficulty adjustment based on target solve times
    - Comprehensive mining function with both timeout and attempt limits
    - Full type safety with mypy validation
    - All PoW TODO tasks marked complete ✅
  - **Files Added:**
    - `src/nostr_simulator/anti_spam/__init__.py`
    - `src/nostr_simulator/anti_spam/base.py`
    - `src/nostr_simulator/anti_spam/pow.py`
    - `src/nostr_simulator/anti_spam/test_base.py`
    - `src/nostr_simulator/anti_spam/test_pow.py`
- Enhanced coding standards in copilot-instructions.md with Test-Driven Development (TDD) requirements
- Added SOLID principles documentation (SRP, OCP, LSP, ISP, DIP)
- Added top 10 clean code practices guidelines
- **Phase 1 Completed: Foundation and Core Infrastructure**
  - Created complete project structure (src/, tests/, docs/)
  - Implemented Poetry configuration with pyproject.toml
  - Set up comprehensive logging configuration with YAML support
  - Created robust configuration management system with Pydantic validation
  - Implemented discrete event simulation engine with priority queue
  - Built advanced time management system for simulation clock
  - Created comprehensive metrics collection and monitoring system
  - Implemented base agent framework with lifecycle management and communication
- **Phase 2 Progress: Network Infrastructure and Actors**
  - Completed comprehensive Nostr protocol implementation with event structure
  - Implemented cryptographic key management and event signing/verification
  - Added event serialization/deserialization with JSON support
  - **Implemented complete Relay Agent system with:**
    - Advanced RelayFilter system for complex event filtering by ID, author, kind, tags, and time ranges
    - High-performance RelayStorage with efficient indexing by author and event kind
    - Client subscription management with configurable limits and policies
    - Event broadcasting to subscribed clients with filter matching
    - Comprehensive relay statistics and monitoring
    - Support for 96% test coverage with 35 comprehensive tests
  - **Implemented complete Client Agent system with:**
    - Multi-relay connection management with automatic failover support
    - Event publishing to multiple relays with selective targeting
    - Advanced subscription system with filter-based event matching
    - Event queue management with capacity limits and overflow handling
    - Offline/online state management and graceful reconnection logic
    - Support for 100% test coverage with comprehensive testing
  - **Implemented complete User Agent system with:**
    - HonestUserAgent class with realistic user behavior simulation
    - UserBehaviorPattern system for configurable user personalities
    - Social graph management (following/followers relationships)
    - Realistic posting behaviors with exponential distribution timing
    - Content generation system with template-based variety
    - User lifecycle management (online/offline state transitions)
    - Social interaction simulation (user discovery and following decisions)
    - Support for 100% test coverage with 45 comprehensive tests
- **✅ COMPLETED Scenario System Refactoring**
  - Refactored all demo scripts into organized scenario system in `src/nostr_simulator/scenarios/`
  - Created 5 comprehensive scenarios covering all demo functionality:
    - `pow_scenario.py` - Proof of Work anti-spam strategy demonstration
    - `multi_strategy_scenario.py` - Multi-strategy anti-spam demonstration
    - `attack_simulation_scenario.py` - Attack simulation with various spam vectors
    - `user_behavior_scenario.py` - User behavior patterns and social interactions
    - `strategy_comparison_scenario.py` - Detailed strategy comparison and analysis
  - Added scenario runner infrastructure (`runner.py`) for easy execution
  - Created root-level entry point (`run_scenarios.py`) to list and run scenarios
  - Updated `README.md` with comprehensive scenario documentation and usage examples
  - Added comprehensive test coverage for all scenarios (`test_scenarios.py`)
  - Removed legacy demo files (`demo_pow_strategy.py`, `demo_comprehensive.py`, `demo_user_agent.py`)
  - Preserved all original demo functionality while improving organization and usability
- **✅ COMPLETED Phase 3 Web of Trust (WoT) Implementation** (Commit: Current)
  - Implemented trust graph data structure with TrustNode class
  - Created trust score calculation using breadth-first search algorithm
  - Added trust propagation with configurable decay and depth limits
  - Implemented trust-based event filtering with bootstrapped trusted keys
  - Created time-based trust decay mechanisms for realistic trust evolution
  - Added comprehensive contact list processing for trust relationship building
  - Implemented trust graph statistics and metrics collection
  - Created WoT demonstration scenario with 5-user network simulation
  - Added extensive test coverage (25 tests, 98% coverage for WoT module)
  - Integrated with existing multi-strategy anti-spam framework

- **✅ COMPLETED Local Reputation Tokens Anti-Spam Strategy Implementation**
  - Implemented comprehensive reputation token system for spam prevention
  - Added `ReputationAccount` class with token balance, earning/spending tracking, and reputation scoring
  - Created `ReputationTokenStrategy` with configurable token costs, earning rates, and reputation thresholds
  - Implemented `ReputationTokenRenewal` strategy with automatic token renewal based on time intervals
  - Added token decay mechanisms to prevent indefinite accumulation
  - Created reputation-based bypass system for high-reputation users (>0.8 score)
  - Added comprehensive test suite with 35 tests covering all token mechanics and edge cases
  - Implemented token distribution analysis and account management features
  - Created demonstration scenario showing honest user behavior, spam attacks, and token dynamics
  - Added support for token penalties and manual token adjustments
  - All reputation token TODO tasks marked complete ✅
  - **Technical Details:**
    - Token earning rate configurable (default: 0.1 tokens per event)
    - Token spending cost configurable (default: 1.0 token per event)
    - Reputation score based on earned vs spent token ratio with time decay
    - High reputation users (score >= threshold) bypass token costs
    - Token decay prevents unlimited accumulation over time
    - Maximum token cap prevents excessive hoarding
    - Comprehensive validation and error handling
  - **Files Added:**
    - `src/nostr_simulator/anti_spam/reputation_tokens.py`
    - `src/nostr_simulator/anti_spam/test_reputation_tokens.py`
    - `src/nostr_simulator/scenarios/reputation_tokens_scenario.py`
  - **Files Modified:**
    - `src/nostr_simulator/anti_spam/__init__.py` (exported new strategies)
    - `TODO.md` (marked Local Reputation Tokens tasks complete)

### Fixed (2025-06-30)

- **Linting and Code Quality Improvements**
  - Fixed all ruff linting issues across the codebase
  - Replaced `assert False` with `raise AssertionError()` for better error handling
  - Fixed unused variables and loop control variables
  - Added proper exception chaining in validation module (`from err` or `from None`)
  - Updated test cases for correct signature verification expectations

### Changed (2025-06-30)

- **Project Structure Reorganization**
  - Moved `run_scenarios.py` from project root to `src/` directory
  - Updated README commands to use `python -m src.run_scenarios` instead of direct script execution
  - Updated Python version requirement from 3.8+ to 3.11+ in README
  - Simplified import structure by removing need for sys.path modifications

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
