# CLAUDE.md — Front Door AI Risk Advisor

The practical working guide. `spec.md` is the law, `DESIGN.md` is the architecture and the
ADRs, `IMPLEMENTATION_PLAN.md` is the sequence. This file is what you need in hand to change
something without breaking it, plus the gotchas already paid for.

This build follows an established AgentCore reference shape deliberately: one runtime, an
orchestrator over in-process sub-agents, a deterministic engine behind a small tool layer,
and policy as configuration. Read the **memory** section below before touching
`agent/memory.py` — that is the one place this build deliberately departs from the shape it
was modelled on, and the reason matters.

---

## The architecture (the invariant — do NOT change casually)

One AgentCore **Runtime** = an **orchestrator** composing **three in-process sub-agents**
(Advisor, Assurance, Handoff) as Strands `tool()`s. The agents reason; **they never route,
score a risk, or decide**. Everything deterministic comes from a **pure engine** reached
through a small **MCP tool layer** behind the **Gateway**. The instrument and the policies are
**configuration data**, not code. The runtime emits **OpenTelemetry spans**.

```
caller + the assessment record  (required — the agent refuses without one)
   └─ Orchestrator (one runtime)
        ├─ advisor_agent    → risk_route, risk_score_intake, risk_draft_verify
        ├─ assurance_agent  → risk_check_policy
        └─ handoff_agent    → risk_build_report
             └─ MCP tools (stateless Lambda) → pure engine → data/
        └─ Memory: summarization · semantic · custom precedent
```

Rules that must hold:

- **Deterministic engine behind tools.** No route, finding or report figure is model-produced.
- **Uniform envelope.** Every engine and tool return carries `decision`, `binding_rule`,
  `disclosure`.
- **The record is required.** No `AssessmentContext` → the guardrail *raises* and the
  entrypoint returns the typed pass-through. Never proceed unguarded.
- **Fail open, as a type.** `{available: false, blocks_nothing: true, result: ""}` — never an
  apology rendered where an answer goes.
- **Proposals are never answers.** `answer_map()` ignores unconfirmed answers, so routing
  cannot move on a suggestion.
- **One matcher, one predicate, one engine.** A second one is a defect by definition.

## Folder map

| Path | Role | Domain-specific? |
| --- | --- | --- |
| `data/instrument_tier1/2/3.json` | Intake, gates, 21 paths, 26 severity questions, 51 objectives | **Yes** — this is the instrument |
| `data/policies.json` | 5 policies, 17 clauses, each naming the controls it governs | **Yes** |
| `data/intake_rubric.json` | Floor thresholds, anchors, and every sentence a person reads | **Yes** — business copy |
| `data/control_domains.json` | Family → risk domain (authority) + the queue rubric | **Yes** |
| `data/tool_schema.json` | The Gateway tool schema — **one definition, two readers** | Pattern |
| `intelligence/risk_engine.py` | The condition engine, visibility, accumulation, the lint, the matcher | Pattern reusable |
| `intelligence/assurance.py` | Gates, guardrails, findings, report, scoring, precedent, authority | Pattern reusable |
| `mcp/index.py` | 6 tools + Gateway/direct dispatch | Pattern reusable |
| `agent/risk_agent.py` | Orchestrator + 3 sub-agents; AgentCore entrypoint | Pattern reusable |
| `agent/memory.py` | 3 strategies, event-append write, floored recall | **Read the warning below** |
| `agent/session.py` | The session seam — the only module holding conversation state | Pattern reusable |
| `cdk/` | Self-contained stack + staging | Reusable; change names/region |
| `harness/` | No-model demo driver + CLI | Reusable |

## Commands

```bash
# Everything, with no model, no AWS, no network. Nine beats, all derived live from data/.
python3 harness/demo_driver.py            # or one beat: ... 5

# Tests (146). Prefer pytest; scripts/test.sh falls back where PyPI is unreachable.
python3 -m pytest tests/ -q
scripts/test.sh

# The runtime locally (needs AWS creds for Bedrock; GATEWAY_URL optional)
export PYTHONPATH="$PWD/agent:$PWD/intelligence"
python3 agent/risk_agent.py               # POST :8080/invocations
python3 harness/chat_cli.py               # in another shell

# Deploy into whichever account your credentials point at — read cdk/README.md first
export AWS_PROFILE=<your-profile>
aws sts get-caller-identity                        # confirm the account FIRST
scripts/deploy.sh                                  # -c region=... -c project=... to override
```

## Changing the instrument

It is **data**. Edit `data/`, then:

1. `python3 -c "import sys;sys.path.insert(0,'intelligence');import risk_engine as e;print(e.lint_instrument())"`
2. `scripts/test.sh` — the count test will fail; update it deliberately, never reflexively.
3. `python3 harness/demo_driver.py` — the beats read the new instrument.

The lint enforces: referential integrity, every activation and accumulation carries a
**reason**, rubric completeness, no `blank` in an activation rule, and help text that does not
restate its label. If you cannot express something as data, that is a design conversation, not
a workaround.

---

## Gotchas already paid for

### Memory — two mistakes that are easy to make and silent to miss
This module was written from scratch rather than adapted, because the common way of wiring
AgentCore Memory contains two defects that produce **no error at all**:

1. `create_memory_record` is **not** the write path for conversational memory. The write is
   an **event append** (`create_event`); the strategies then extract long-term records from
   those events.
2. A Memory resource provisioned with **no extraction strategies** stores nothing, however
   correct the write is.

Get either wrong and reads, listing and deletion all still work — they just always return
empty. A memory layer that silently stores nothing fails exactly like an unreachable table.

- The strategy definitions live in `agent/memory.py` and the **CDK imports them**, so
  infrastructure and code cannot drift.
- The **attested-only guarantee for precedent lives in `write_precedent()`**, not in the
  strategy prompt. "Attested" is a structured predicate; a model cannot infer it from a
  transcript. Pointing a semantic strategy at raw conversation and calling the result
  precedent would launder unattested content into institutional memory *and look like it was
  working*.
- The floor is enforced on **both** sides — the write protects the store, `_mentions_enough()`
  protects the screen, and only one of them is on the side that owns the consequence.

### AgentCore / naming
- Runtime/Gateway/Memory names are `a-zA-Z{0,47}` — **alphanumeric only**; hyphens are
  rejected outright. `cdk/risk_stack.py:alphanumeric()` derives them from the project name in
  one place, so a hyphenated project prefix is safe.
- Gateway target `Name` is `${SegmentName}Tools` — keep `SegmentName` hyphen-free (`risk`).
- The entrypoint parameter **must** be named `context` with a default. AgentCore inspects the
  signature to decide whether to pass its `RequestContext`; renaming it 500s delegations.
- No DynamoDB tables are needed. Do not provision any.

### Observability — the part with the most traps
- Installing `aws-opentelemetry-distro` is **not enough**. The container **must** launch under
  `opentelemetry-instrument` (see the Dockerfile `CMD`) or **zero spans** are emitted, and the
  failure is silent: the agent works perfectly and the dashboard stays empty.
- Set `AGENT_OBSERVABILITY_ENABLED=true` and
  `OTEL_RESOURCE_ATTRIBUTES=service.name=risk-advisor-agent`.
- The role needs `xray:PutTraceSegments`/`PutTelemetryRecords`, `cloudwatch:PutMetricData`,
  the CloudWatch Logs actions, **and `logs:PutResourcePolicy`** — the last is required to
  deliver spans to the agent's own log group.
- **CloudWatch Transaction Search must be enabled once per account+region.** It is an account
  setting, not code. Verify with `aws xray get-trace-segment-destination` (want
  `CloudWatchLogs` / `ACTIVE`).
- Spans land in the runtime's **own** log group `/aws/bedrock-agentcore/runtimes/<id>-DEFAULT`
  (streams `spans` / `otel-rt-logs`), **not** the shared `aws/spans`. Classic
  `aws xray get-trace-summaries` returns **0** by design once Transaction Search routes to
  CloudWatch Logs — use the CloudWatch **GenAI Observability** page.

### `mcp/` shadows the PyPI `mcp` package
This repo has a folder called `mcp/`, and `agent/risk_agent.py` imports the PyPI package of
the same name. So the repo root is deliberately **not** on `sys.path` in tests — the `mcp/`
directory itself is, which makes `index` importable without shadowing. In the built image the
question does not arise: `cdk/staging.py` flattens everything into one directory.

### Correctness — the partial-call guard
`_resolve_assessment()` merges a partial `assessment` (or an `answers` overlay) **over** the
seeded record. Without it, a sub-agent calling with only what it holds routes against an empty
record and — because nothing activates on silence — gets *"nothing applies to this activity."*
That **phantom clean bill of health** is worse than a phantom DECLINE: a
decline gets argued with, an all-clear gets believed. Keep it and its regression test.

### Guardrails are only shipped once something proves they fire
The spec records the failure this rule came from: the drafting gate **imported** the guardrail
and never called it, and the import passed the type checker because nothing forbids an unused
one. `tests/test_assurance.py` has a test whose only job is to fail if that call is removed.
When adding a check, add the sentence it exists to stop — a guardrail is written against a
named failure, not against a category.

### CDK / deploy
- The region comes from `cdk deploy -c region=...` with an explicit default in `app.py`,
  **never** from `CDK_DEFAULT_REGION` — leaving it to the environment lets a profile default
  silently redirect a deploy somewhere you did not intend. Account is deliberately unset so
  CDK resolves it from the credentials in use.
- Deploy a second copy into one account with `-c project=<name>`: it prefixes the IAM roles
  and the Lambda, and the AgentCore resource names are derived from it.
- Confirm the target account with `aws sts get-caller-identity` before every deploy. This
  stack creates IAM roles and a Bedrock-invoking runtime wherever your credentials point.
  **No account id is written anywhere in this repository.**

### Not verified here — say so, do not assume
No container built, no stack deployed, **no model ever called**: there is no Docker and no
route to PyPI on the authoring machine. `constraints.txt` therefore carries **no pins** — an
empty constraints file is a no-op, and a version somebody guessed would be worse than a
documented gap. Every model-dependent path is proved with **fabricated** replies, which is
deliberate; it also means **no quality claim** is made about scoring, drafting or summarising.

---

## Running it against a real model without AgentCore

`harness/conversation_demo.py` runs the **real topology** — orchestrator delegating to the
three sub-agents, which call the six tools, grounded in the seeded record, with the
contextual guardrail applied to every reply — directly against the Bedrock Converse API. It
exists because Strands and the AgentCore SDK could not be installed on the authoring network,
and it is the only way the architecture was exercised end to end before deployment.

It lifts the prompts out of `agent/risk_agent.py` **by reading the source** rather than
restating them, so the demo cannot drift from the product. If you rename a prompt constant,
this breaks loudly — which is the intent.

```bash
export AWS_PROFILE=<profile> AWS_REGION=us-east-1
python3 harness/conversation_demo.py          # nine capabilities as a conversation
python3 harness/conversation_demo.py 4 7      # selected beats
```

**Re-run it after any prompt change.** Two defects came out of the first run that fabricated
replies could never have surfaced: the model wrote a person's internal identifier into an
answer (the guardrail refused the reply and the product failed open — working as designed),
and the orchestrator ignored its 120-word limit until the prompt explained *why* the limit
exists. A prompt that states a rule without its reason is a suggestion.

## The plain-CloudFormation deploy path

`deploy/template.py` emits the stack as CloudFormation, for environments where the CDK Python
library cannot be installed. It is **not** a second hand-maintained copy: the two things that
would actually drift — the Gateway tool schema and the memory strategies — are read from
`data/tool_schema.json` and `agent/memory.py` respectively, the same sources the CDK stack
reads. Property shapes came from the live resource schemas
(`aws cloudformation describe-type --type-name AWS::BedrockAgentCore::*`), which caught two
bugs before they cost a failed deploy.
