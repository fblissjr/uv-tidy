# uv-tidy/run_tests.sh
# Simple script to run tests with pytest

# First install dev requirements if needed
if [ ! -f .dev-reqs-installed ]; then
  echo "Installing dev requirements..."
  pip install pytest pytest-cov
  touch .dev-reqs-installed
fi

# Run tests with coverage
pytest -xvs --cov=uv_tidy tests/

# Show coverage report
echo ""
echo "Coverage report:"
coverage report -m