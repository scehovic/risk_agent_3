#!/usr/bin/env python3
"""Emit the CloudFormation template for the Risk Advisor AgentCore stack.

WHY THIS EXISTS ALONGSIDE `cdk/`
    `cdk/` is the primary, readable definition. This is a **plain-CloudFormation path** for
    environments where the CDK Python library cannot be installed — which is exactly the
    situation this was first deployed from, and is also true of plenty of customer networks.

    It is NOT a second hand-maintained copy of the infrastructure. The two things that would
    actually drift — the **Gateway tool schema** and the **memory strategies** — are read
    from the same single sources the CDK stack reads (`data/tool_schema.json` and
    `agent/memory.py:strategies()`). Everything else here is IAM and wiring.

    Property shapes below were taken from the live resource schemas
    (`aws cloudformation describe-type --type-name AWS::BedrockAgentCore::*`), not from
    documentation or from guesswork. Two mistakes were caught that way before they cost a
    failed deploy: the custom strategy's override is `Configuration.SemanticOverride`
    (CloudFormation) rather than the SDK's lowercase shape, and its `ModelId` is REQUIRED, so
    it cannot be read from a runtime environment variable that does not exist at build time.

    python3 deploy/template.py --project risk-advisor > /tmp/template.json
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))
import memory as memory_module            # noqa: E402  — the ONE strategy definition

MODEL_ID = "us.anthropic.claude-sonnet-4-6"
MODEL_ID_FAST = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def pascal(value):
    """SDK camelCase -> CloudFormation PascalCase.

    `agent/memory.py` writes the strategies in the shape the data-plane SDK uses, because
    that is what a developer reading the runtime code expects. CloudFormation wants
    PascalCase, so the conversion happens here rather than keeping two copies.
    """
    if isinstance(value, dict):
        return {k[0].upper() + k[1:]: pascal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [pascal(v) for v in value]
    return value


def alphanumeric(project, suffix):
    """AgentCore names must match `a-zA-Z{0,47}` — alphanumeric only; hyphens are rejected."""
    base = "".join(c for c in project.title().replace("-", "").replace("_", "")
                   if c.isalnum())
    return (base + suffix)[:48]


def build(project, model_id, model_fast):
    tools = json.loads((ROOT / "data" / "tool_schema.json").read_text())["tools"]
    strategies = pascal(memory_module.strategies(model_fast))

    runtime_name = alphanumeric(project, "Agent")
    gateway_name = alphanumeric(project, "Gateway")
    memory_name = alphanumeric(project, "Memory")

    # No account id appears anywhere in this file. Every ARN is built from the pseudo
    # parameters CloudFormation resolves at deploy time, so the same template deploys into
    # any account unchanged.
    acct = {"Ref": "AWS::AccountId"}
    region = {"Ref": "AWS::Region"}

    def arn(*parts):
        return {"Fn::Sub": "".join(parts)}

    role_statements = [
        # BEFORE PRODUCTION: scope to the specific inference-profile ARNs in use.
        {"Effect": "Allow",
         "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream",
                    "bedrock:ApplyGuardrail"],
         "Resource": "*"},
        {"Effect": "Allow",
         "Action": ["bedrock-agentcore:CreateEvent", "bedrock-agentcore:ListEvents",
                    "bedrock-agentcore:GetEvent",
                    "bedrock-agentcore:RetrieveMemoryRecords",
                    "bedrock-agentcore:ListMemoryRecords",
                    "bedrock-agentcore:GetMemoryRecord",
                    "bedrock-agentcore:BatchDeleteMemoryRecords"],
         "Resource": arn("arn:aws:bedrock-agentcore:${AWS::Region}:${AWS::AccountId}:memory/",
                         memory_name, "*")},
        {"Effect": "Allow",
         "Action": ["bedrock-agentcore:InvokeAgentRuntime"],
         "Resource": arn("arn:aws:bedrock-agentcore:${AWS::Region}:${AWS::AccountId}:runtime/",
                         runtime_name, "*")},
        {"Effect": "Allow", "Action": ["lambda:InvokeFunction"],
         "Resource": arn("arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:",
                         project, "-*")},
        {"Effect": "Allow",
         "Action": ["ecr:GetAuthorizationToken", "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"],
         "Resource": "*"},
        # OBSERVABILITY. Omit logs:PutResourcePolicy and AgentCore cannot deliver spans to
        # the agent's own log group — the agent then works perfectly and emits nothing.
        {"Effect": "Allow",
         "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords",
                    "xray:GetSamplingRules", "xray:GetSamplingTargets",
                    "xray:GetSamplingStatisticSummaries"],
         "Resource": "*"},
        {"Effect": "Allow",
         "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
                    "logs:DescribeLogGroups", "logs:DescribeLogStreams",
                    "cloudwatch:PutMetricData",
                    "logs:PutResourcePolicy", "logs:DescribeResourcePolicies"],
         "Resource": "*"},
    ]

    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Front Door AI Risk Advisor - AgentCore runtime, gateway, memory "
                       "and observability",
        "Parameters": {
            "ContainerUri": {"Type": "String",
                             "Description": "ECR image URI for the agent runtime"},
            "LambdaBucket": {"Type": "String",
                             "Description": "S3 bucket holding the MCP tool Lambda zip"},
            "LambdaKey": {"Type": "String", "Description": "S3 key of the Lambda zip"},
        },
        "Resources": {
            "AgentCoreRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "RoleName": {"Fn::Sub": "%s-agentcore-role" % project},
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [{
                            "Effect": "Allow",
                            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                            "Action": "sts:AssumeRole"}]},
                    "Policies": [{
                        "PolicyName": "agentcore",
                        "PolicyDocument": {"Version": "2012-10-17",
                                           "Statement": role_statements}}],
                },
            },
            "McpRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "RoleName": {"Fn::Sub": "%s-mcp-role" % project},
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [{
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Action": "sts:AssumeRole"}]},
                    "ManagedPolicyArns": [
                        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
                },
            },
            "McpFunction": {
                "Type": "AWS::Lambda::Function",
                "Properties": {
                    "FunctionName": "%s-mcp" % project,
                    "Runtime": "python3.12",
                    "Architectures": ["arm64"],
                    "Handler": "index.handler",
                    "Role": {"Fn::GetAtt": ["McpRole", "Arn"]},
                    "Timeout": 30,
                    "MemorySize": 512,
                    "Code": {"S3Bucket": {"Ref": "LambdaBucket"},
                             "S3Key": {"Ref": "LambdaKey"}},
                    "Environment": {"Variables": {"PROJECT_NAME": project,
                                                  "SEGMENT_NAME": "risk"}},
                },
            },
            "McpPermission": {
                "Type": "AWS::Lambda::Permission",
                "Properties": {
                    "FunctionName": {"Fn::GetAtt": ["McpFunction", "Arn"]},
                    "Action": "lambda:InvokeFunction",
                    "Principal": "bedrock-agentcore.amazonaws.com",
                    "SourceAccount": acct,
                },
            },
            "Memory": {
                "Type": "AWS::BedrockAgentCore::Memory",
                "Properties": {
                    "Name": memory_name,
                    "Description": "Risk Advisor: per-assessment conversation and facts, "
                                   "plus attested-only portfolio precedent",
                    "EventExpiryDuration": 90,
                    "MemoryExecutionRoleArn": {"Fn::GetAtt": ["AgentCoreRole", "Arn"]},
                    # THREE long-term strategies, read from agent/memory.py so the
                    # namespaces the code queries are the namespaces that get extracted into.
                    "MemoryStrategies": strategies,
                },
            },
            "Gateway": {
                "Type": "AWS::BedrockAgentCore::Gateway",
                "Properties": {
                    "Name": gateway_name,
                    "Description": "Risk Advisor instrument and assurance tools",
                    # BEFORE PRODUCTION: NONE means anyone who can reach the Gateway URL can
                    # call these tools. Replace with a JWT authorizer for real use.
                    "AuthorizerType": "NONE",
                    "ProtocolType": "MCP",
                    "RoleArn": {"Fn::GetAtt": ["AgentCoreRole", "Arn"]},
                    "ProtocolConfiguration": {"Mcp": {
                        "SupportedVersions": ["2025-03-26"],
                        "Instructions": "Risk intake routing, policy authority and "
                                        "assurance tools",
                        "SearchType": "SEMANTIC"}},
                },
            },
            "ToolsTarget": {
                "Type": "AWS::BedrockAgentCore::GatewayTarget",
                "DependsOn": ["McpPermission"],
                "Properties": {
                    "GatewayIdentifier": {"Fn::GetAtt": ["Gateway", "GatewayIdentifier"]},
                    "Name": "riskTools",
                    "Description": "Risk instrument, policy and assurance tools",
                    "TargetConfiguration": {"Mcp": {"Lambda": {
                        "LambdaArn": {"Fn::GetAtt": ["McpFunction", "Arn"]},
                        "ToolSchema": {"InlinePayload": tools}}}},
                    "CredentialProviderConfigurations": [
                        {"CredentialProviderType": "GATEWAY_IAM_ROLE"}],
                },
            },
            "Runtime": {
                "Type": "AWS::BedrockAgentCore::Runtime",
                "DependsOn": ["Memory", "Gateway"],
                "Properties": {
                    "AgentRuntimeName": runtime_name,
                    "Description": "Front Door Risk Advisor - intake, drafting, policy, "
                                   "handoff",
                    "RoleArn": {"Fn::GetAtt": ["AgentCoreRole", "Arn"]},
                    "NetworkConfiguration": {"NetworkMode": "PUBLIC"},
                    "AgentRuntimeArtifact": {
                        "ContainerConfiguration": {
                            "ContainerUri": {"Ref": "ContainerUri"}}},
                    "EnvironmentVariables": {
                        "PROJECT_NAME": project,
                        "SEGMENT": "risk",
                        "BEDROCK_MODEL_ID": model_id,
                        "BEDROCK_MODEL_ID_FAST": model_fast,
                        "AGENTCORE_MEMORY_ID": {"Fn::GetAtt": ["Memory", "MemoryId"]},
                        "GATEWAY_URL": {"Fn::Sub": [
                            "https://${Id}.gateway.bedrock-agentcore.${AWS::Region}"
                            ".amazonaws.com/mcp",
                            {"Id": {"Fn::GetAtt": ["Gateway", "GatewayIdentifier"]}}]},
                        "AGENT_OBSERVABILITY_ENABLED": "true",
                        "OTEL_RESOURCE_ATTRIBUTES":
                            "service.name=risk-advisor-agent",
                    },
                },
            },
            "SpecialistRegistration": {
                "Type": "AWS::SSM::Parameter",
                "Properties": {
                    "Name": "/%s/specialists/risk" % project,
                    "Type": "String",
                    "Value": {"Fn::Sub": [
                        '{"runtime_arn":"${Arn}",'
                        '"description":"Front Door Risk Advisor"}',
                        {"Arn": {"Fn::GetAtt": ["Runtime", "AgentRuntimeArn"]}}]},
                },
            },
        },
        "Outputs": {
            "RuntimeArn": {"Value": {"Fn::GetAtt": ["Runtime", "AgentRuntimeArn"]}},
            "GatewayUrl": {"Value": {"Fn::Sub": [
                "https://${Id}.gateway.bedrock-agentcore.${AWS::Region}.amazonaws.com/mcp",
                {"Id": {"Fn::GetAtt": ["Gateway", "GatewayIdentifier"]}}]}},
            "MemoryId": {"Value": {"Fn::GetAtt": ["Memory", "MemoryId"]}},
            "McpFunctionName": {"Value": {"Ref": "McpFunction"}},
            "ObservabilityConsole": {"Value": {"Fn::Sub":
                "https://${AWS::Region}.console.aws.amazon.com/cloudwatch/home"
                "?region=${AWS::Region}#gen-ai-observability"}},
        },
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="risk-advisor")
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--model-fast", default=MODEL_ID_FAST)
    a = ap.parse_args()
    print(json.dumps(build(a.project, a.model, a.model_fast), indent=1))
