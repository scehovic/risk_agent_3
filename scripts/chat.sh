#!/usr/bin/env bash
# Local runtime + CLI. Needs AWS credentials for Bedrock; GATEWAY_URL optional.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/agent:$PWD/intelligence:$PWD/harness"
python3 agent/risk_agent.py &
AGENT_PID=$!
trap 'kill $AGENT_PID 2>/dev/null || true' EXIT
sleep 6
python3 harness/chat_cli.py
