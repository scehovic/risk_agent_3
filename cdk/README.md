# Deploying the Front Door Risk Advisor

Self-contained stack. One `cdk deploy` stands up everything the capability needs in one
account and region: IAM, AgentCore Memory (three strategies), AgentCore Gateway plus a tools
target, the MCP Lambda, and the AgentCore Runtime.

**It deploys into whichever account's credentials you run it with.** No account id, and no
organisation-specific value, appears anywhere in this repository — CDK resolves the account
from the ambient credentials and the IAM policies use a token resolved at deploy time.

Two things are configurable, through cdk **context** so the choice is recorded in the command
rather than picked up from a stray environment variable:

```bash
npx --yes aws-cdk@2 deploy -c region=eu-west-1 -c project=acme-risk
```

| Context | Default | Effect |
| --- | --- | --- |
| `region` | `us-east-1` | The deploy region. Set it explicitly; it is deliberately **not** read from `CDK_DEFAULT_REGION`. |
| `project` | `risk-advisor` | Prefixes the stack, the IAM roles and the Lambda, and the AgentCore resource names are derived from it. Change it to deploy a second copy into one account, or to match your naming standard. |
| `model` / `modelFast` | Claude Sonnet / Haiku inference profiles | Override the Bedrock model ids — needed if you deploy outside a `us-*` region, where the geography prefix differs (`eu.`, `apac.`). |

> **Not yet run.** This stack is authored and its Lambda bundle is verified to execute with the
> flattened imports, but `cdk synth` has not been run and no image has been built — there is
> no Docker and no route to PyPI on the machine it was written on. Treat every step below as
> written-but-unexercised, and expect to fix something on the first pass.

## What it creates

Names below assume the default `project` of `risk-advisor`; substitute your own.

| Resource | Name | Notes |
| --- | --- | --- |
| IAM role | `<project>-agentcore-role` | Shared by Gateway, Memory and Runtime; carries the X-Ray/CloudWatch permissions |
| IAM role | `<project>-mcp-role` | The tool Lambda's execution role |
| AgentCore Memory | `RiskAdvisorMemory` | **Three** strategies, imported from `agent/memory.py`; name derived from `project` |
| AgentCore Gateway | `RiskAdvisorGateway` | MCP, `AuthorizerType: NONE` — acceptable for a sandbox, **not for production** |
| Gateway target | `riskTools` | Tool schema read from `data/tool_schema.json` |
| Lambda | `<project>-mcp` | Python 3.12, ARM64, the six tools |
| AgentCore Runtime | `RiskAdvisorAgent` | The orchestrator image; the alphanumeric-only name is derived, not hand-written |
| SSM parameter | `/<project>/specialists/risk` | Runtime ARN, for discovery |

**Before production**, revisit two things this stack leaves open for a sandbox: the Gateway's
`AuthorizerType: NONE`, and the IAM statements that use `resources=["*"]` for Bedrock model
invocation, ECR pulls and X-Ray. Both are noted in `risk_stack.py` at the line they occur.

## Prerequisites

1. **Credentials for the target account.**
   ```bash
   export AWS_PROFILE=<your-profile>
   aws sts get-caller-identity --profile "$AWS_PROFILE"     # confirm the account
   ```
   Whatever issues your credentials, confirm the account before deploying — this stack
   creates IAM roles and a Bedrock-invoking runtime, and it creates them wherever those
   credentials point. **No account id appears anywhere in this repository**; CDK resolves it
   from the credentials in use.

2. **Bedrock model access in your deploy region** for the inference profiles in
   `risk_stack.py` (Claude Sonnet and Claude Haiku). Outside a `us-*` region the geography
   prefix differs — pass `-c model=` / `-c modelFast=` with the right ids.

3. **Docker running** — the runtime image is built locally by `DockerImageAsset` for
   `linux/arm64`.

4. **Resolve `constraints.txt` first.** It ships with no pins on purpose. Run the command in
   the file's header on an arm64 container and paste the output in, so the image you deploy is
   the image somebody tested.

5. **CloudWatch Transaction Search, once per account+region.** An account setting, not code:
   ```bash
   aws xray update-trace-segment-destination --destination CloudWatchLogs
   aws xray get-trace-segment-destination      # want CloudWatchLogs / ACTIVE
   ```
   Skip it and the deploy still succeeds — you just get no traces, which is a much more
   confusing problem to debug later.

## Deploy

```bash
cd cdk
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

npx --yes aws-cdk@2 bootstrap        # first time in this account/region only
npx --yes aws-cdk@2 deploy --require-approval never
# with overrides:
# npx --yes aws-cdk@2 deploy -c region=eu-west-1 -c project=acme-risk
```

Or from the repo root: `scripts/deploy.sh`.

Expect outputs named `RuntimeArn`, `GatewayUrl`, `MemoryId`, `McpFunctionArn` and
`ObservabilityConsole`.

## Verify, in this order — each step says what it should print

**1. The Lambda answers at all.**
```bash
aws lambda invoke --function-name <project>-mcp \
  --payload '{"tool_name":"risk_hello","name":"deploy check"}' /dev/stdout
```
Expect `"instrument_coherent": true` and `"objectives": 51`. If the instrument counts are
wrong, `cdk/staging.py` did not copy a data file — that is a `FileNotFoundError` at synth, so
you would not get this far.

**2. The Gateway routes to it.** Same tool, through the Gateway URL from the outputs, as an
MCP `tools/call`. Expect the same payload. A failure here is routing or IAM, not code.

**3. The Runtime is warm.**
```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn <RuntimeArn> --runtime-session-id warm-1 \
  --payload '{"type":"warmup"}' /dev/stdout
```
Expect `"status": "warm"`, the model id, `"mcp": "connected"`, and
`"memory": {"configured": true, "strategies": [...]}` with three entries. `"mcp"` reporting
*reasoning from the record only* means `GATEWAY_URL` did not reach the container.

**4. A real invocation.**
```bash
RUNTIME_ARN=<RuntimeArn> python3 harness/runtime_client.py "What still needs answering?"
```
Expect a reply naming questions **by their words**. If it comes back
`{"available": false}`, read `because` — the guardrail refusing a reply is a *correct* outcome,
not a failure.

**5. Traces.** Open the `ObservabilityConsole` output. Spans land in the runtime's own log
group `/aws/bedrock-agentcore/runtimes/<id>-DEFAULT`, streams `spans` and `otel-rt-logs` —
**not** the shared `aws/spans`. `aws xray get-trace-summaries` returns **0 by design** once
Transaction Search routes to CloudWatch Logs; that is not a fault.

## Things that will bite

| Symptom | Cause |
| --- | --- |
| Runtime create rejects the name | AgentCore names are alphanumeric only, no hyphens. `alphanumeric()` in `risk_stack.py` derives them; if you bypassed it, that is why. |
| Gateway target create fails | The target name must be hyphen-free (`riskTools`). |
| Zero traces, agent working fine | The container did not launch under `opentelemetry-instrument`, or Transaction Search is off, or the role lacks `logs:PutResourcePolicy`. |
| Deploy lands in the wrong region | Region comes from `-c region=...` with an explicit default, never from `CDK_DEFAULT_REGION`. If it moved, someone passed a different context value. |
| Memory is configured but recall is always empty | Strategies extract asynchronously; a just-written event has nothing extracted from it yet. Check `list_events` first — if events exist, the write path is fine. |
| `ResolutionImpossible` during the image build | Somebody hand-edited a pin in `constraints.txt`. `strands-agents` constrains `mcp` (`>=1.11.0`). Re-resolve, do not guess. |

## Teardown

```bash
cd cdk && npx --yes aws-cdk@2 destroy
```

Removes everything the stack created, including the Memory resource and **every long-term
memory record in it**. Check what else reads the SSM specialist parameter before running it
against a shared account.
