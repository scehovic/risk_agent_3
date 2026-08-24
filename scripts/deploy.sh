#!/usr/bin/env bash
# Deploy the self-contained AgentCore stack to us-east-1. See cdk/README.md first.
set -euo pipefail
cd "$(dirname "$0")/../cdk"
: "${AWS_PROFILE:?set AWS_PROFILE to the target account's profile}"
aws sts get-caller-identity --profile "$AWS_PROFILE"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
npx --yes aws-cdk@2 deploy --require-approval never "$@"
