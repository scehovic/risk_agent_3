#!/usr/bin/env python3
"""CDK app for the self-contained Front Door Risk Advisor AgentCore stack.

DEPLOYS INTO WHICHEVER ACCOUNT'S CREDENTIALS YOU RUN IT WITH. No account id appears
anywhere in this repository — CDK resolves the account from the ambient credentials, and the
IAM policies use a token that resolves at deploy time.

Two things are configurable, both through cdk context so the choice is deliberate and
recorded in the command rather than picked up from a stray environment variable:

    npx aws-cdk@2 deploy -c region=eu-west-1 -c project=acme-risk

  region   default us-east-1. Set it explicitly; do not rely on a shell default.
  project  default risk-advisor. Prefixes the IAM roles, the Lambda and the stack, and is
           used to derive the AgentCore resource names. Change it if you deploy more than
           one copy into the same account, or to match your own naming standard.
  model    optional Bedrock inference-profile id override.
  modelFast optional fast-model override, used by the sub-agents.
"""
import aws_cdk as cdk

from risk_stack import RiskAdvisorStack

app = cdk.App()

# Region comes from context with an explicit default, NOT from CDK_DEFAULT_REGION. Leaving
# it to the environment lets a profile default silently redirect a deploy to a region you
# did not intend, which is an afternoon nobody enjoys. Account is intentionally unset so it
# resolves from the credentials in use.
region = app.node.try_get_context("region") or "us-east-1"
project = app.node.try_get_context("project") or "risk-advisor"

RiskAdvisorStack(
    app, "%s-agentcore" % project,
    env=cdk.Environment(region=region),
    project=project,
    model_id=app.node.try_get_context("model"),
    model_id_fast=app.node.try_get_context("modelFast"),
    description="Front Door AI Risk Advisor - AgentCore runtime, gateway, memory and "
                "observability",
)

app.synth()
