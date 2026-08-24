#!/usr/bin/env bash
# The whole demo, with no model, no AWS and no network. Nothing here is mocked —
# every figure is derived from data/ by the engine at the moment it prints.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 harness/demo_driver.py "$@"
