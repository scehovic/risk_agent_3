# Front Door AI Risk Advisor — Implementation Plan

**Companion to** `DESIGN.md` and `spec.md`. The design says *how* it is built and *why*; this
plan says *in what order*, *with what dependencies*, *what the deliverables are*, and *how we
know each step is done*.

## Approach

Build the deterministic layer first and the agent on top of it, for one reason: the engine is
what the agent's output is judged against, so it cannot come second. Configuration before
engine, engine before tools, tools before prompts.

**Status legend:** ✅ done · ◐ in progress · ☐ not started.

**Current state:** M1–M6 are implemented and verified on this machine. M7 is authored and its
Lambda bundle proven, but **not deployed** — no Docker and no route to PyPI here.

## Milestones

Critical path: **M1 → M2 → {M3, M4}**. M5 runs alongside M2–M4; M6 needs M3; M7 needs M3+M4.

| # | Milestone | Depends on | Exit criteria | Status |
| --- | --- | --- | --- | --- |
| **M1** | Configuration & data — the instrument at full pilot depth, 5 policies/17 clauses, the intake rubric, the control-domain map, reference lists, the seeded assessment and its document | — | Lint reports coherent; counts are 11/21/26/51; every activation and accumulation carries a reason | ✅ |
| **M2** | The engine — one condition engine, one visibility predicate, accumulation, one verbatim matcher, the never-guess gate, the contextual guardrail, findings, the report, intake scoring | M1 | §19 acceptance criteria pass; positive-evidence and fail-closed asserted; guardrails proved to fire | ✅ |
| **M3** | Tool layer — 6 stateless tools behind the Gateway schema | M2 | Every tool returns the envelope and is JSON-serialisable; dispatch works Gateway-style *and* direct; schema parity asserted | ✅ |
| **M4** | Orchestrator + 3 sub-agents + the memory layer | M2 | Entrypoint contract honoured; three memory strategies defined; every failure path returns the typed pass-through | ✅ |
| **M5** | Test suite — engine, assurance, tool contract, memory | M2–M4 | Green with no AWS and no model call | ✅ 146 |
| **M6** | Runnable end to end — the no-model demo driver and a CLI | M3 | Every capability demonstrable on a laptop with no network | ✅ |
| **M7** | Cloud deployment — Runtime, Gateway, Memory, Lambda, IAM, observability | M3, M4 | Invocable in the target account and region; spans on the GenAI Observability page | ◐ authored; staged bundle verified; **not deployed** |

### Sequencing

```
M1 ─▶ M2 ─┬─▶ M3 ─┬─▶ M6 (local demo)
          └─▶ M4 ─┴─▶ M7 (cloud)
M5 (tests) runs alongside M2–M4
```

## Deliverables

| Deliverable | State |
| --- | --- |
| Instrument at pilot depth — 11 gates, 21 paths, 26 severity questions, 51 objectives, 129 questions | ✅ |
| 5 enterprise policies, 17 clauses, each in its own words, one deliberately uncovered | ✅ |
| Intake rubric: heuristic floor, 5 dimensions × 3 anchors, per-score copy, pass rule | ✅ |
| Condition engine + visibility predicate + accumulation + coherence lint | ✅ |
| Never-guess gate, contextual guardrail, findings synthesis, handoff report | ✅ |
| Attestation authority, review-ordering rubric, precedent with its four rules | ✅ |
| MCP tool layer (6 tools) + the Gateway schema as data | ✅ |
| Orchestrator + Advisor / Assurance / Handoff sub-agents | ✅ |
| AgentCore Memory: 3 strategies, event-append write, floored recall, forget | ✅ |
| Test suite (146) | ✅ |
| No-model demo driver (9 beats) + CLI harness | ✅ |
| CDK stack + runbook | ✅ authored; deploy not run |
| `README.md`, `DESIGN.md`, this plan, `CLAUDE.md` | ✅ |

## Test & acceptance

- **Engine** — positive evidence only, severity fails closed, set membership, one-sentence
  explanation with no identifiers, union with provenance, gate-No closes a category,
  recompute without deleting history, all four conditional kinds, children on Yes only,
  derived bands, the coherence lint over the real instrument.
- **Assurance** — every never-guess refusal (paraphrase, **stitched quote**, unsupplied
  source, abstention with an answer, inference with no quote, no reason, pre-confirmed,
  riding on a person's answer); every guardrail form the spec names as previously missed;
  the laundering case; findings taxonomy including "unanswered is never a breach" and "N-A is
  never a breach"; authority derived from the question; precedent's floor; drop-not-clamp;
  scenario and summary vetting.
- **Tool contract** — envelope on every tool, JSON-serialisable, both dispatch paths, the
  handler never raises, and the partial-call guard against a phantom all-clear.
- **Memory** — three strategies with namespaces, precedent write filter, floored recall,
  every path best-effort when unconfigured.

**Release acceptance.** For the seeded assessment, end to end: 18 of 21 paths active each
with its reasons, 45 of 51 objectives accumulated, 22 findings of which 8 are policy breaches
with the clause quoted, a derived handoff report naming its 4 unanswered controls and its 5
declared boundaries — **all computed with no model** — plus every gate and guardrail proved
to refuse the sentence it exists to stop.

## What is deliberately not built

| Not built | Where that is recorded |
| --- | --- |
| The requester-facing UI | This exposes a backend contract and a harness; the UI is a separate effort |
| Destination write-back (ServiceNow AI Use Case Record) | Spec §27 — the payload is assemblable, the send is out of scope |
| Attachment binaries | Spec §3.6 retention posture is still open; documents are extracted text only |
| A composite risk score | Spec §14.1 — open governance question; nothing computed or displayed |
| A `userPreference` memory strategy over answer content | ADR-8 — it would be a pre-selection, which G-39a forbids |
| Depth behind the seven gate-only risk areas | Pilot scope (G-50); each says on screen it stops deliberately |
| An eval harness with committed baselines | The architecture is now proven against a real model, but scoring accuracy is unmeasured — that needs a ground-truth set, not another demo run |

## Next steps, in order

1. **Resolve `constraints.txt`** on a machine with Docker — one command, in the file.
2. **`cdk synth`, then deploy** into the target account (`scripts/deploy.sh`, region and
   project via `-c`), and enable CloudWatch Transaction Search once for that account and
   region.
3. **Warm up and smoke test** — `risk_hello` through the Gateway proves Lambda routing;
   `{"type":"warmup"}` proves the runtime, the model id and the memory wiring.
4. ~~**First real model run**~~ — **done** via `harness/conversation_demo.py`, which runs the
   real topology (orchestrator + three sub-agents + six tools + the guardrail) directly on
   the Bedrock Converse API, because Strands and the AgentCore SDK could not be installed.
   It found two defects: the model leaked a person identifier into a reply (the guardrail
   caught it and the product failed open), and the orchestrator ignored its 120-word limit
   until the prompt explained *why* the limit exists. Re-run it after any prompt change.
5. **Then, and only then, an eval** with committed per-capability baselines in which full
   abstention on absent evidence is a scored correct answer.
