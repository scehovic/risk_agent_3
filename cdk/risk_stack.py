"""Self-contained Front Door Risk Advisor AgentCore stack, with observability.

Stands up, in one account/region, everything the capability needs:

  - IAM role (shared by Gateway, Memory and Runtime), WITH X-Ray + CloudWatch perms
  - AgentCore Memory        (THREE long-term strategies: summarization, semantic, custom)
  - AgentCore Gateway (MCP) + a tools target backed by the MCP Lambda
  - MCP Lambda              (the 6 risk tools, including a routing smoke test)
  - AgentCore Runtime       (the orchestrator + 3 sub-agents container image)

AgentCore resources use the CfnResource escape hatch so the stack does not depend on a
particular aws-cdk-lib version shipping the L1 constructs.

TWO THINGS DELIBERATELY NOT DUPLICATED HERE
  The tool schema is read from `data/tool_schema.json`, and the memory strategies are
  imported from `agent/memory.py`. Both are the kind of value that gets copy-pasted into a stack,
  and a Gateway advertising a tool the Lambda does not implement fails at demo time with an
  unhelpful error. One definition, two readers.
"""
import json
import pathlib
import sys

from aws_cdk import (
    Stack, CfnResource, CfnOutput, Duration, Fn,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_ecr_assets as ecr_assets,
)
from constructs import Construct

import staging

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))
import memory as memory_module            # noqa: E402  — the ONE strategy definition

DEFAULT_PROJECT = "risk-advisor"
SEGMENT = "risk"

TOOL_SCHEMA = json.loads((ROOT / "data" / "tool_schema.json").read_text())["tools"]


def alphanumeric(project, suffix):
    """AgentCore Runtime/Gateway/Memory names must match `a-zA-Z{0,47}` — ALPHANUMERIC ONLY.

    Hyphens are rejected outright, so a project prefix cannot be used raw. Derived here in
    one place rather than hand-written per resource, because getting one of these wrong
    fails at create time with a message that does not mention the naming rule.
    """
    base = "".join(c for c in project.title().replace("-", "").replace("_", "")
                   if c.isalnum())
    return (base + suffix)[:48]


class RiskAdvisorStack(Stack):
    def __init__(self, scope: Construct, cid: str, project=None, model_id=None,
                 model_id_fast=None, **kw):
        super().__init__(scope, cid, **kw)
        region, account = self.region, self.account

        # Nothing about the deploying account is written into this file. `self.account` is a
        # CDK token resolved from whoever runs the deploy, so the same source deploys into
        # any account without an edit.
        project = project or DEFAULT_PROJECT
        runtime_name = alphanumeric(project, "Agent")
        gateway_name = alphanumeric(project, "Gateway")
        memory_name = alphanumeric(project, "Memory")
        tools_target_name = "%sTools" % SEGMENT       # keep the segment hyphen-free

        # Bedrock inference-profile ids. The `us.` geography prefix suits us-* regions; for
        # eu-* or ap-* pass the matching prefix (`eu.`, `apac.`) via cdk context.
        MODEL_ID = model_id or "us.anthropic.claude-sonnet-4-6"
        MODEL_ID_FAST = model_id_fast or "us.anthropic.claude-haiku-4-5-20251001-v1:0"
        PROJECT = project
        RUNTIME_NAME, GATEWAY_NAME = runtime_name, gateway_name
        MEMORY_NAME, TOOLS_TARGET_NAME = memory_name, tools_target_name

        # ── IAM role: shared by Gateway, Memory and Runtime ──────────────────
        role = iam.Role(
            self, "AgentCoreRole",
            role_name="%s-agentcore-role" % PROJECT,
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
        )
        # BEFORE PRODUCTION: scope this to the specific inference-profile ARNs in use. `*`
        # is acceptable in a sandbox and is called out in cdk/README.md rather than left to be
        # discovered in a security review.
        role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream",
                     "bedrock:ApplyGuardrail"],
            resources=["*"]))
        # Memory read/write, scoped to this deployment's memory. CreateEvent is the WRITE
        # path. CreateMemoryRecord is NOT the write path for conversational memory.
        role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock-agentcore:CreateEvent", "bedrock-agentcore:ListEvents",
                     "bedrock-agentcore:GetEvent",
                     "bedrock-agentcore:RetrieveMemoryRecords",
                     "bedrock-agentcore:ListMemoryRecords",
                     "bedrock-agentcore:GetMemoryRecord",
                     "bedrock-agentcore:BatchDeleteMemoryRecords"],
            resources=["arn:aws:bedrock-agentcore:%s:%s:memory/%s*"
                       % (region, account, MEMORY_NAME)]))
        role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock-agentcore:InvokeAgentRuntime"],
            resources=["arn:aws:bedrock-agentcore:%s:%s:runtime/%s*"
                       % (region, account, RUNTIME_NAME)]))
        role.add_to_policy(iam.PolicyStatement(
            actions=["lambda:InvokeFunction"],
            resources=["arn:aws:lambda:%s:%s:function:%s-*" % (region, account, PROJECT)]))
        role.add_to_policy(iam.PolicyStatement(
            actions=["ecr:GetAuthorizationToken", "ecr:BatchGetImage",
                     "ecr:GetDownloadUrlForLayer"],
            resources=["*"]))

        # ── OBSERVABILITY: X-Ray tracing + CloudWatch logs/metrics ───────────
        # Without these the agent works perfectly and the GenAI Observability page stays
        # empty, which is the worst kind of failure to debug at a demo.
        role.add_to_policy(iam.PolicyStatement(
            actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords",
                     "xray:GetSamplingRules", "xray:GetSamplingTargets",
                     "xray:GetSamplingStatisticSummaries"],
            resources=["*"]))
        role.add_to_policy(iam.PolicyStatement(
            actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
                     "logs:DescribeLogGroups", "logs:DescribeLogStreams",
                     "cloudwatch:PutMetricData",
                     # logs:PutResourcePolicy is REQUIRED for AgentCore to deliver spans to
                     # the agent's own log group. Omit it and zero spans arrive.
                     "logs:PutResourcePolicy", "logs:DescribeResourcePolicies"],
            resources=["*"]))

        # ── AgentCore Memory — THREE long-term strategies ────────────────────
        # Imported from agent/memory.py so the namespaces the code reads are exactly the
        # namespaces the resource extracts into. Without strategies, nothing is ever
        # extracted no matter how correct the write is — the defect this stack exists to
        # not repeat.
        memory = CfnResource(self, "Memory", type="AWS::BedrockAgentCore::Memory",
                             properties={
            "Name": MEMORY_NAME,
            "Description": "Risk Advisor: per-assessment conversation and facts, plus "
                           "attested-only portfolio precedent",
            "EventExpiryDuration": 90,
            "MemoryExecutionRoleArn": role.role_arn,
            "MemoryStrategies": _pascal(memory_module.strategies(MODEL_ID_FAST)),
        })

        # ── AgentCore Gateway (MCP) ──────────────────────────────────────────
        gateway = CfnResource(self, "Gateway", type="AWS::BedrockAgentCore::Gateway",
                              properties={
            "Name": GATEWAY_NAME,
            "Description": "Risk Advisor instrument and assurance tools",
            # BEFORE PRODUCTION: NONE means anyone who can reach the Gateway URL can call
            # these tools. Fine for a sandbox demo; replace with a JWT authorizer for real use.
            "AuthorizerType": "NONE",
            "ProtocolType": "MCP",
            "RoleArn": role.role_arn,
            "ProtocolConfiguration": {"Mcp": {
                "SupportedVersions": ["2025-03-26"],
                "Instructions": "Risk intake routing, policy authority and assurance tools",
                "SearchType": "SEMANTIC",
            }},
        })
        gateway_id = gateway.ref
        gateway_url = ("https://%s.gateway.bedrock-agentcore.%s.amazonaws.com/mcp"
                       % (gateway_id, region))

        # ── MCP Lambda (the 6 tools) ─────────────────────────────────────────
        mcp_dir = staging.stage_mcp()
        mcp_role = iam.Role(
            self, "McpRole", role_name="%s-mcp-role" % PROJECT,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole")])
        mcp_fn = _lambda.Function(
            self, "McpFunction", function_name="%s-mcp" % PROJECT,
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.ARM_64,
            handler="index.handler", code=_lambda.Code.from_asset(str(mcp_dir)),
            role=mcp_role, timeout=Duration.seconds(30), memory_size=512,
            environment={"PROJECT_NAME": PROJECT, "SEGMENT_NAME": SEGMENT})
        mcp_fn.add_permission(
            "GatewayInvoke",
            principal=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            action="lambda:InvokeFunction", source_account=account)

        tools_target = CfnResource(self, "ToolsTarget",
                                   type="AWS::BedrockAgentCore::GatewayTarget",
                                   properties={
            "GatewayIdentifier": gateway_id,
            "Name": TOOLS_TARGET_NAME,
            "Description": "Risk instrument, policy and assurance tools",
            "TargetConfiguration": {"Mcp": {"Lambda": {
                "LambdaArn": mcp_fn.function_arn,
                "ToolSchema": {"InlinePayload": TOOL_SCHEMA},
            }}},
            "CredentialProviderConfigurations": [
                {"CredentialProviderType": "GATEWAY_IAM_ROLE"}],
        })
        tools_target.node.add_dependency(mcp_fn)

        # ── Agent image (ARM64) ──────────────────────────────────────────────
        agent_dir = staging.stage_agent()
        image = ecr_assets.DockerImageAsset(
            self, "AgentImage", directory=str(agent_dir),
            platform=ecr_assets.Platform.LINUX_ARM64)

        # ── AgentCore Runtime (orchestrator + 3 sub-agents) ──────────────────
        runtime = CfnResource(self, "Runtime", type="AWS::BedrockAgentCore::Runtime",
                              properties={
            "AgentRuntimeName": RUNTIME_NAME,
            "Description": "Front Door Risk Advisor - intake, drafting, policy, handoff",
            "RoleArn": role.role_arn,
            "NetworkConfiguration": {"NetworkMode": "PUBLIC"},
            "AgentRuntimeArtifact": {
                "ContainerConfiguration": {"ContainerUri": image.image_uri}},
            "EnvironmentVariables": {
                "PROJECT_NAME": PROJECT,
                "SEGMENT": SEGMENT,
                "BEDROCK_MODEL_ID": MODEL_ID,
                "BEDROCK_MODEL_ID_FAST": MODEL_ID_FAST,
                "AGENTCORE_MEMORY_ID": memory.ref,
                "GATEWAY_URL": gateway_url,
                "AGENT_OBSERVABILITY_ENABLED": "true",
                "OTEL_RESOURCE_ATTRIBUTES": "service.name=risk-advisor-agent",
            },
        })
        runtime.node.add_dependency(memory)
        runtime.node.add_dependency(gateway)

        reg = CfnResource(self, "SpecialistRegistration", type="AWS::SSM::Parameter",
                          properties={
            "Name": "/%s/specialists/%s" % (PROJECT, SEGMENT),
            "Type": "String",
            "Value": Fn.sub(
                '{"runtime_arn":"${arn}","description":"Front Door Risk Advisor"}',
                {"arn": runtime.get_att("AgentRuntimeArn").to_string()}),
        })
        reg.node.add_dependency(runtime)

        # ── Outputs ──────────────────────────────────────────────────────────
        CfnOutput(self, "RuntimeArn",
                  value=runtime.get_att("AgentRuntimeArn").to_string())
        CfnOutput(self, "GatewayUrl", value=gateway_url)
        CfnOutput(self, "MemoryId", value=memory.ref)
        CfnOutput(self, "McpFunctionArn", value=mcp_fn.function_arn)
        CfnOutput(self, "ObservabilityConsole",
                  value="https://%s.console.aws.amazon.com/cloudwatch/home?region=%s"
                        "#gen-ai-observability" % (region, region))


def _pascal(value):
    """boto3-style camelCase keys -> CloudFormation PascalCase.

    `agent/memory.py` writes the strategies in the shape the data-plane SDK uses, because
    that is the shape a developer reading the runtime code expects. CloudFormation wants
    PascalCase, so the conversion happens here rather than keeping two hand-maintained
    copies of the same definition.
    """
    if isinstance(value, dict):
        return {k[0].upper() + k[1:]: _pascal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_pascal(v) for v in value]
    return value
