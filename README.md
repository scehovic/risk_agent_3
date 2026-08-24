# Front Door AI Risk Advisor

An agentic layer over enterprise risk intake. It takes a business activity from
*description* to *attested, exportable risk assessment* with the minimum burden on the
business user and no loss of rigour for the risk organisation — replacing a process that has
cost real projects **up to ninety hours** with a single guided session.

Built on **Amazon Bedrock AgentCore**: one Runtime, one Gateway, one Memory resource with
three long-term strategies. Deploys into your own AWS account — no account id, region
assumption or organisation-specific reference appears anywhere in this repository.

---

## The shape

```
caller + the assessment record        (the record is authoritative — never re-derived)
   └─ Risk Advisor Orchestrator       (one AgentCore Runtime)
        ├─ advisor_agent    → risk_route, risk_score_intake, risk_draft_verify
        ├─ assurance_agent  → risk_check_policy
        └─ handoff_agent    → risk_build_report
             └─ AgentCore Gateway → MCP Lambda → pure engine → data/
        └─ AgentCore Memory: summarization · semantic · custom (precedent)
```

**The agents reason. They never decide.** Every number, every route, every finding and every
figure on the report comes from a pure deterministic engine reached through a small tool
layer. The instrument and the policies are **configuration data**, not code.

## What it does — five capabilities

| Capability | What a person gets | Requirement |
| --- | --- | --- |
| **Assessment companion** | Ask anything about your own assessment and get an answer grounded only in your record | FR-39 |
| **Document drafting** | Hand it a vendor document; it *proposes* answers carrying the verbatim sentence each came from, and **abstains** where the document is silent | FR-40 |
| **Policy authority** | Every control question cites the clause requiring it, quoted verbatim; a breaching answer raises a non-compliance finding | FR-41 |
| **Handoff report** | The artifact a Risk Assessor receives, derived entirely from the record, plus at most three sentences and 2–4 scenarios worth asking about | FR-42 |
| **Intake scoring** | The first screen graded against a published rubric — and it **cannot block you** | FR-43 |

## The five rules that shape every line of this

1. **Never guess.** Any AI-produced answer states its basis — *stated* with a verbatim
   quote, *inferred* with grounding, or *not_stated*, a full abstention. **Abstention is a
   correct outcome, scored as one.** A stated answer without a verbatim quote is
   structurally impossible.
2. **Proposals are not answers.** A drafted answer arrives unconfirmed by construction and
   counts as an answer nowhere until a person accepts it, which writes a *new* record so the
   proposal stays underneath.
3. **Fail open.** No agent, a slow agent, a wrong agent, a partial answer or a thrown error
   **all pass**. A quality assistant that blocks submission has become a gate, and the
   mission is reducing friction.
4. **Grounded, or silent.** Every capability is handed the assessment's record and refuses to
   run without one. Everything it says is checked against that record: no internal
   identifier reaches a person, and no answer is attributed to somebody who did not give it.
5. **Substrate, never the decider.** The agent may never attest, declare, resolve a finding
   or accept a risk. Those are named human acts.

## Run it

```bash
# The whole demo. No model, no AWS, no network — every figure derived from data/ live.
python3 harness/demo_driver.py

# The same nine capabilities as a conversation, against a real model on Bedrock.
export AWS_PROFILE=<profile> AWS_REGION=us-east-1
python3 harness/conversation_demo.py

# The test suite (146 tests, no AWS, no model calls).
python3 -m pytest tests/ -q          # or: scripts/test.sh
```

```bash
# The runtime locally (needs AWS credentials for Bedrock; GATEWAY_URL optional).
export PYTHONPATH="$PWD/agent:$PWD/intelligence"
python3 agent/risk_agent.py          # POST :8080/invocations
python3 harness/chat_cli.py          # in another shell
```

```bash
# Deploy into YOUR AWS account. Read cdk/README.md first.
export AWS_PROFILE=<your-profile>
aws sts get-caller-identity          # confirm the account before creating anything
scripts/deploy.sh                    # add: -c region=eu-west-1 -c project=acme-risk
```

## The instrument

The real one at pilot depth, not a cut-down demo version:

| | |
| --- | --- |
| Risk areas (categories) | **11** — four carry full depth, seven are gate-only and **say on screen that they stop deliberately** |
| Risk paths | **21** |
| Severity questions | **26** — 21 path-attached, 4 always-on, 1 derived from a fact |
| Control objectives | **51** across 14 control families |
| Policy clauses | **17** across 5 policies, each quoted in its own words |
| Questions total | **129** |

Severity is never a bare band word: **the rubric anchor is the option**, so a person picks
the sentence that describes their situation.

## Layout

| Path | Role |
| --- | --- |
| `data/` | The instrument, the policies, the rubric — versioned configuration, never code |
| `intelligence/risk_engine.py` | The ONE condition engine: routing, visibility, accumulation, the verbatim matcher |
| `intelligence/assurance.py` | The never-guess gate, the contextual guardrail, findings, the report, intake scoring |
| `mcp/index.py` | Six MCP tools + the Gateway dispatch handler |
| `agent/risk_agent.py` | Orchestrator + three sub-agents; the AgentCore entrypoint |
| `agent/memory.py` | AgentCore Memory: three strategies, and the rules fencing portfolio precedent |
| `agent/session.py` | The session seam — the one module that reads and writes conversation state |
| `harness/demo_driver.py` | Nine capabilities with **no model, no AWS, no network** |
| `harness/conversation_demo.py` | The same nine as a **conversation against a real model** on Bedrock |
| `harness/chat_cli.py` | Talk to the deployed or local runtime |
| `cdk/` | Self-contained CDK stack: Runtime, Gateway, Memory, Lambda, IAM, observability |
| `deploy/template.py` | The same stack as plain CloudFormation, for where CDK cannot be installed |
| `tests/` | Engine, assurance, tool-contract, memory |

`DESIGN.md` is *how and why* (the ADRs). `IMPLEMENTATION_PLAN.md` is *in what order, and how
we know each step is done*. `CLAUDE.md` is the practical guide plus the gotchas already paid
for.

## Honest status

**Verified on this machine:** the instrument lints coherent at full pilot depth; routing,
accumulation and the ledger derive correctly over the seeded assessment; 22 findings
including 8 policy breaches computed with no model; the handoff report derives and names its
four unanswered controls; every never-guess refusal and every guardrail check fires against
the exact sentence it exists to stop; the staged Lambda bundle runs with flattened imports;
146 tests pass.

**Verified against a real model on Bedrock** (Claude Sonnet orchestrating, Claude Haiku
sub-agents, `harness/conversation_demo.py`): the full architecture runs — the orchestrator
delegates to the three sub-agents, they call the six tools, the tools compute from the
instrument, and the contextual guardrail vets every reply. Two things that run taught, which
no amount of fabricated-reply testing would have:

- **The guardrail caught a real leak.** Asked why a control was being asked, the model wrote a
  person's internal identifier into its answer. The guardrail refused the reply and the
  product failed open. That is the exact failure G-65 names, happening unprompted.
- **The orchestrator ignored its own length limit** — 452 words and markdown tables against a
  stated 120-word cap. The prompt now forbids tables and explains *why* a broad question does
  not license a report; replies came back at ~105–140 words. A prompt that states a limit
  without stating its reason is a suggestion.

**Still not verified:** no container built and no stack deployed. `pip` cannot reach PyPI from
the authoring network — including from inside the container — so `constraints.txt` carries no
pins and the runtime image has never been built. The CloudFormation path (`deploy/`) **does**
validate against CloudFormation, and all four AgentCore resource types are confirmed
registered. No eval with committed baselines exists, so **no accuracy claim** is made about
scoring, drafting or summarising. CloudWatch Transaction Search must be enabled once per
account and region before spans appear.
