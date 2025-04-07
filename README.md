# uv-tidy

a simple CLI tool to query, identify, and clean up unused uv virtual environments on linux and macOS (maybe more, but tested on these)

## Features

- detects uv virtual environments in standard locations
- identifies unused venvs based on configurable criteria (age, size, activity)
- shows detailed information about each venv before removal
- defaults to a safe dry-run mode
- structured logging with human and machine-readable formats

## installation

install from source:

```bash
git clone https://github.com/yourusername/uv-tidy.git
cd uv-tidy
uv pip install -e .
```

## Usage

Basic usage (dry run):

```bash
uv-tidy
```

this will:
- scan standard uv venv locations
- identify venvs that haven't been used in 30+ days
- show what would be removed (but not actually remove anything)

Perform actual cleanup:

```bash
uv-tidy --yes
```

### usage examples of args

- `--min-age-days 90`: Only consider venvs unused after 90 days (default: 30)
- `--min-size-mb 100`: Only remove venvs larger than 100MB
- `--sort-by size`: Sort by size instead of age
- `--limit 5`: Remove at most 5 venvs
- `--venv-dir PATH`: Specify a custom directory to scan
- `--exclude "*test*"`: Skip venvs with paths matching a pattern
- `--verbose`: Show more detailed information
- `--json`: Output in JSON format for scripting

### examples

show all venvs over 100MB that haven't been used in 60+ days:

```bash
uv-tidy --min-age-days 60 --min-size-mb 100
```

clean up the 5 oldest venvs:

```bash
uv-tidy --sort-by age --limit 5 --yes
```

scan a specific directory:

```bash
uv-tidy --venv-dir ~/projects/.venvs --yes
```

machine-readable output:

```bash
uv-tidy --json > venv_report.json
```

## basic workflow

uv-tidy identifies unused environments by:

1. looking for standard uv venv directory structures
2. checking last access times of activation scripts and key files
3. measuring total directory size
4. applying configurable filters

it (should) always do a dry run first, showing what would be removed, and requires explicit confirmation or a `--yes` flag to actually delete anything

- defaults to dry-run mode
- requires confirmation for deletion
- won't remove recently accessed venvs
- detailed logging of all actions
- evaluation before suggesting removal

## project tree structure
```
uv-tidy/
├── pyproject.toml         # Project metadata and dependencies
├── README.md              # Project documentation
├── run_tests.sh           # Helper script to run tests
├── uv_tidy/               # Main package directory
│   ├── __init__.py        # Package initialization
│   ├── cli.py             # Command-line interface
│   ├── core.py            # Core functionality
│   ├── rules.py           # Criteria and rules
│   └── utils.py           # Utility functions
└── tests/                 # Test directory
    ├── conftest.py        # Common test fixtures and configuration
    ├── test_cli.py        # CLI tests
    ├── test_core.py       # Core functionality tests
    ├── test_rules.py      # Rules tests
    ├── test_utils.py      # Utility function tests
    └── fixtures/          # Additional test fixtures
        ├── __init__.py    # Make fixtures importable
        ├── mock_venvs.py  # More advanced venv mocking utilities
        ├── sample_data/   # Sample data directory
        │   ├── large_venv_structure.json  # Sample complex venv structure
        │   └── custom_configs/            # Test configuration files
        └── helpers.py     # Additional test helper functions
```

## License

Apache 2.0
