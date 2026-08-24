#!/usr/bin/env bash
# Prefer real pytest. Fall back to the zero-dependency runner where PyPI is unreachable.
set -euo pipefail
cd "$(dirname "$0")/.."
if python3 -c "import pytest" 2>/dev/null; then
  exec python3 -m pytest tests/ -q "$@"
fi
echo "pytest unavailable — using the zero-dependency runner (scripts/run_tests.py)"
exec python3 scripts/run_tests.py "$@"
