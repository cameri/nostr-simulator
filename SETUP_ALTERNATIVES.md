# Alternative Setup Instructions

If you encounter SSL issues with the main setup script, you can use these alternative approaches:

## Option 1: Using system Python and pip

If you have pip installed system-wide and working:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies (you may need to use --trusted-host flags if SSL issues persist)
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Install pre-commit hooks
pre-commit install
```

## Option 2: Using conda/mamba

If you have conda or mamba installed:

```bash
# Create conda environment
conda create -n nostr-simulator python=3.9

# Activate environment
conda activate nostr-simulator

# Install some packages via conda
conda install black isort pytest numpy pandas matplotlib seaborn networkx pyyaml

# Install remaining packages via pip
pip install pre-commit mdformat mdformat-mkdocs mdformat-gfm mdformat-frontmatter mdformat-footnote mypy ruff bandit pytest-cov mesa mkdocs mkdocs-material pydantic rich

# Install pre-commit hooks
pre-commit install
```

## Option 3: Using Poetry (Recommended for development)

If you prefer using Poetry for dependency management:

```bash
# Install poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Initialize poetry project (this will create pyproject.toml)
poetry init

# Add dependencies
poetry add --group dev pre-commit black isort mypy ruff bandit pytest pytest-cov
poetry add --group dev mdformat mdformat-mkdocs mdformat-gfm mdformat-frontmatter mdformat-footnote
poetry add mesa numpy pandas matplotlib seaborn networkx pydantic pyyaml rich
poetry add --group dev mkdocs mkdocs-material

# Install dependencies
poetry install

# Activate shell
poetry shell

# Install pre-commit hooks
pre-commit install
```

## Troubleshooting SSL Issues

If you're still having SSL issues, try:

1. **Update certificates:**

   ```bash
   # On macOS
   /Applications/Python\ 3.x/Install\ Certificates.command
   
   # On Ubuntu/Debian
   sudo apt-get update && sudo apt-get install ca-certificates
   
   # On CentOS/RHEL
   sudo yum update ca-certificates
   ```

2. **Use a different Python installation:**
   - Install Python via Homebrew on macOS: `brew install python`
   - Install Python via pyenv: `pyenv install 3.9.17 && pyenv global 3.9.17`

3. **Configure pip to use trusted hosts (temporary fix):**

   ```bash
   pip config set global.trusted-host "pypi.org files.pythonhosted.org pypi.python.org"
   ```

## Verifying Installation

After setup, verify everything works:

```bash
# Check Python version
python --version

# Check installed packages
pip list

# Test pre-commit
pre-commit run --all-files

# Run a simple test
python -c "import mesa, numpy, pandas; print('All simulation dependencies imported successfully!')"
```
