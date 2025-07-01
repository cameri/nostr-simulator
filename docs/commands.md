# Project Commands Reference

This project uses [poethepoet](https://github.com/nat-n/poethepoet) to manage all project commands and scripts. This provides a single source of truth for all development tasks and ensures consistency across environments.

## Usage

All commands are run using: `poetry run poe <task_name>`

If you have poethepoet installed globally, you can also use: `poe <task_name>`

## Available Commands

### Code Quality and Formatting

- `poetry run poe format` - Format code with Black
- `poetry run poe format-check` - Check if code is properly formatted
- `poetry run poe sort-imports` - Sort imports with isort
- `poetry run poe sort-imports-check` - Check if imports are properly sorted
- `poetry run poe format-all` - Format code and sort imports

### Linting and Type Checking

- `poetry run poe lint` - Check code with Ruff linter
- `poetry run poe lint-fix` - Fix linting issues automatically
- `poetry run poe type-check` - Run type checking with mypy

### Testing

- `poetry run poe test` - Run tests without coverage
- `poetry run poe test-no-cov` - Run tests explicitly without coverage (faster)
- `poetry run poe test-cov` - Run tests with coverage reporting (HTML and terminal)
- `poetry run poe test-cov-xml` - Run tests with XML coverage output (for CI)
- `poetry run poe test-fast` - Run tests with fail-fast and last-failed-first options
- `poetry run poe test-watch` - Automatically run tests when files change (requires `entr`)
- `poetry run poe cov-report` - Generate and open coverage report in browser

### Quality Assurance Workflows

- `poetry run poe check-all` - Run all quality checks (format, imports, lint, type-check)
- `poetry run poe quality` - Alias for check-all
- `poetry run poe ci` - Full CI pipeline (quality checks + tests with XML coverage)

### Application Commands

- `poetry run poe simulate` - Run the main simulator
- `poetry run poe run-scenarios` - Run simulation scenarios

### Documentation

- `poetry run poe docs-serve` - Serve documentation locally
- `poetry run poe docs-build` - Build documentation
- `poetry run poe docs-clean` - Clean documentation build artifacts

### Maintenance

- `poetry run poe clean` - Clean Python cache files and test artifacts
- `poetry run poe clean-all` - Clean all cache and build artifacts
- `poetry run poe update-deps` - Update all dependencies
- `poetry run poe show-outdated` - Show outdated dependencies
- `poetry run poe security` - Run security checks with Bandit

### Development Workflows

- `poetry run poe setup` - Full development setup (clean, update deps, quality check, test)
- `poetry run poe pre-commit` - Run pre-commit checks (format, lint-fix, type-check, fast tests)
- `poetry run poe prepare-commit` - Prepare for commit with quality checks and status
- `poetry run poe commit-ready` - Check if ready to commit (includes diff)
- `poetry run poe safe-commit` - Run all quality checks before committing
- `poetry run poe quick-save` - Quick save work in progress with formatting

### Version Control (Jujutsu)

**Basic Operations:**

- `poetry run poe jj-status` - Show working copy status
- `poetry run poe jj-log` - Show recent commit history (last 10, no pager)
- `poetry run poe jj-diff` - Show changes in working copy (git-style format, no pager)

**Commit Operations:**

- `poetry run poe jj-commit` - Commit changes interactively
- `poetry run poe jj-commit-all --message "Your message"` - Commit all changes with a message
- `poetry run poe jj-describe` - Edit commit description
- `poetry run poe jj-new` - Create new change
- `poetry run poe jj-branch --message "Branch description"` - Create new branch with description

**History Operations:**

- `poetry run poe jj-squash` - Squash changes
- `poetry run poe jj-abandon` - Abandon current change
- `poetry run poe jj-clean-abandoned` - Clean up abandoned empty commits

**Remote Operations:**

- `poetry run poe jj-push` - Push changes to remote
- `poetry run poe jj-pull` - Fetch and rebase against remote
- `poetry run poe jj-sync` - Sync with remote main branch

**Bookmark Management:**

- `poetry run poe jj-bookmark-list` - List all bookmarks
- `poetry run poe jj-bookmark --bookmark name --revision abc123` - Set bookmark to specific revision
- `poetry run poe jj-bookmark-delete --bookmark name` - Delete a bookmark

## Benefits of Centralized Commands

1. **Single Source of Truth**: All commands are defined in `pyproject.toml`
2. **Consistency**: Same commands work across all environments (local, CI, etc.)
3. **Easy Maintenance**: Change coverage thresholds or command options in one place
4. **Documentation**: Built-in help and clear command structure
5. **Composability**: Tasks can reference other tasks and run in sequence
6. **No Pager Issues**: Jujutsu commands configured to output directly to console
7. **Git-Style Formatting**: Diff commands use familiar git-style output format

## Configuration

All task definitions are in the `[tool.poe.tasks]` section of `pyproject.toml`. Key settings:

- **Coverage Threshold**: 90% (configured in pytest and coverage settings)
- **Python Path**: `src` directory is automatically added to PYTHONPATH
- **Environment Variables**: Coverage threshold is available as `COVERAGE_THRESHOLD=90`

## CI/CD Integration

The CI pipeline uses the centralized commands:

- GitHub Actions runs `poetry run poe ci` for the complete pipeline
- Dependency updates use `poetry run poe update-deps` and `poetry run poe test-cov`

This ensures that CI uses exactly the same commands as local development.
