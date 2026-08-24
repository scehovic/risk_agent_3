# Front Door AI Risk Advisor — Technical Design

**Companion to `spec.md`.** The spec defines *what* to build — the mission, the instrument
semantics, the invariants, the guardrails. This document does not repeat them. It defines
*how* it is built: the architecture and the decisions behind it, the component contracts,
the interaction flow, the rules the spec leaves implicit, and where each guardrail is
*enforced* rather than merely stated.

**Domain / phase:** enterprise risk intake, Phase-2 agentic layer (spec G-51) over the
Phase-1 instrument. Journey: describe → route → assess → submit → review → handoff.

---

## 0. What this document adds beyond the spec

| The spec already specifies | This design adds |
| --- | --- |
| Mission, the three problem statements, the north stars | Which component delivers each, and how it is measured |
| Instrument semantics (§3), routing law (§3.2) | The operator set, the visibility predicate's actual branches, and the derivation rules |
| The invariants (§5) and the agentic contract (§7) | The **enforcement point** for each one, in code, not in a prompt |
| Five capabilities in the Phase-2 register (§22.1) | How they package into three sub-agents and six tools, and why |
| "AgentCore Runtime, Gateway, Memory" | The three memory strategies, their namespaces, and where the attested-only guarantee actually lives |

---

## 1. Design goals & constraints

| Goal | Why it drives the design |
| --- | --- |
| **Auditable, reproducible routing** | A person asking "why am I being asked this?" is owed an authority. Identical answers must give identical routing, so no route may be model-generated. |
| **Explainability by construction** | Every activation, accumulation and finding carries its reason — structurally, not as a prompt hope. |
| **No false answer** | Nothing the agent produces may read as the person's answer. Enforced at a code boundary, because a prompt instruction can be argued past. |
| **Config owns the instrument** | Questions, rubrics, policies and mappings change on a governance cadence, not a release cadence. |
| **Friction reduction cannot become friction** | The assistant must be *incapable* of blocking the journey. |
| **Self-contained & discoverable** | Deployable alone; an upstream assistant or a UI calls it as one specialist. |

### 1.1 Functional scope

| # | In scope | Note |
| --- | --- | --- |
| **FR-39** | Assessment companion | Grounded in one assessment's record; reply is context, never evidence |
| **FR-40** | Document-assisted drafting | Proposals only, verbatim-quoted, abstention first-class |
| **FR-41** | Policy authority & breach findings | Deterministic pass stands alone with no model |
| **FR-42** | Handoff report | Derived from the record; complete without the agent |
| **FR-43** | Intake scoring | Heuristic floor, model scores, deterministic copy; never blocks |
| **—** | Attestation authority, review ordering, precedent | Supporting engine functions the capabilities lean on |

**Explicitly out:** the requester-facing UI (this exposes a backend contract and a test
harness), destination write-back, production identity, attachment *binaries* (documents are
stored as extracted text only), and any composite risk score.

---

## 2. Architecture decisions (ADRs)

The core value of this document. Each records the decision, why, and what was rejected.

### ADR-1 — Orchestrator + three in-process sub-agents (not one agent, not five services)
**Decision.** One orchestrator sequences the work and delegates to three sub-agents —
Advisor, Assurance, Handoff — running **in the same runtime**, exposed as tools.

**Why.** The spec names five capabilities, but they group cleanly by *audience and failure
mode*: three serve the requester mid-journey (companion, drafting, intake scoring), one is an
authority lookup, one produces the assessor's artifact. Three prompts, three scopes, one
interface upstream. In-process keeps latency low and state simple.

**Rejected.** *Five separate runtimes* — five images, five deploys and five cold starts for
capabilities that share one record. *One mega-agent* — a single prompt owning drafting *and*
policy quotation *and* report writing is impossible to constrain, and the drafting rules
(quote verbatim, abstain freely) actively conflict with the report rules (summarise in three
sentences).

### ADR-2 — A deterministic engine behind tools; the agent never routes or decides
**Decision.** All routing, accumulation, findings and report derivation live in a **pure,
side-effect-free engine**. Agents reach it only through stateless tools. The model handles
language, scoring against published anchors, and orchestration — never a route or a verdict.

**Why.** The spec's own words: AgentCore is *substrate, never the decider*. A route a model
reasoned to is not defensible to a requester or a regulator; a route the engine derived from
authored conditions is. It also makes the whole surface testable without a model.

**Rejected.** *Let the model read the instrument and decide what applies* —
non-deterministic, unverifiable, and it would make "why am I being asked this?"
unanswerable.

### ADR-3 — The instrument and the policies are configuration, not code
**Decision.** Categories, gates, paths, severity questions, rubric anchors, conditionals,
control objectives, accumulation rules, policy clauses, the intake rubric and the control
family map are **data files** the engine reads. The engine carries no authored content.

**Why.** New risk workflows become new versioned data rather than new code, which is how the
platform absorbs an emerging risk domain without touching a GRC backend. The rubric being
data is what lets the feedback a person reads be business copy edited in one place.

**Consequence.** A coherence lint (`lint_instrument()`) is part of the suite: referential
integrity, reason coverage, rubric completeness, and a rule that nothing may activate on
silence.

### ADR-4 — The record arrives in the request; it is never fetched or re-derived
**Decision.** The caller supplies the assessment record. Tools hold no per-assessment state,
and facts in the record are authoritative.

**Why.** Horizontal scale, no cross-assessment leakage, and one source of truth across three
sub-agents. It is also what makes the agent deployable before a database exists.

**Consequence, and the trap it creates.** A sub-agent calling a tool with only what it holds
would otherwise be routed against an empty record — and because nothing activates on
silence, the engine would return *"nothing applies to this activity."* That **phantom clean
bill of health** is worse than a phantom DECLINE, because a decline gets
argued with and an all-clear gets believed. `_resolve_assessment()` merges partial input over
the record, and it has a named regression test.

### ADR-5 — Guardrails at the tool boundary, in one shared function
**Decision.** Every engine and tool result carries a uniform envelope: `decision`, the
`binding_rule` that produced it, and an honest `disclosure`. The never-guess gate and the
contextual guardrail are pure functions **both capabilities call**, so a new capability
cannot ship with half the checks.

**Why.** "Never guess" and "nothing reads as recorded" must be structural. The spec records
what happens otherwise: the drafting gate once *imported* the guardrail and never called it,
and the import passed the type checker because nothing forbids an unused one.

**Consequence.** Each check has a test naming the exact sentence it exists to stop. A
guardrail is written against a named failure, not against a category — and it is not shipped
when written, it is shipped when something proves it fires.

### ADR-6 — Fail open is a response type, not a message
**Decision.** Every failure path returns a typed pass-through — `available: False`,
`blocks_nothing: True`, an empty `result` and a `because` — rather than an apologetic
sentence in the place an answer goes.

**Why.** The mission is reducing friction. If the failure mode renders as text where an
answer belongs, a person reads it as the product being broken. A typed absence lets the
calling screen simply show nothing.

**Rejected.** A degrade-to-a-message approach, which is right for a
triggered specialist composing one answer and wrong for an assistant sitting beside a form.

### ADR-7 — Six tools, one per journey step
**Decision.** `risk_route`, `risk_score_intake`, `risk_draft_verify`, `risk_check_policy`,
`risk_build_report`, plus `risk_hello` as a routing smoke test. Explanation folds into
routing; findings fold into the policy check; scenario vetting folds into the report.

**Why.** A sprawling tool layer is harder for a model to choose from and harder to test. One
tool per step keeps orchestration deterministic.

**Not tools.** The instrument, the policies and the reference lists are configuration read
inside the engine. Fetching one is a file read, not a tool call.

### ADR-8 — Three memory strategies, and the precedent guarantee lives on the write side
**Decision.** One Memory resource with three long-term strategies:

| Strategy | Namespace | Holds |
| --- | --- | --- |
| Summarization | `/assessment/{sessionId}/summary` | The companion conversation for one assessment |
| Semantic | `/assessment/{sessionId}/facts` | Facts the requester stated about their own activity |
| Custom | `/precedent/portfolio` | Attested-only aggregates — the one cross-assessment namespace |

**Why.** The first two are per-assessment continuity and cost nothing in governance terms.
The third is portfolio memory, which the spec fences with four rules: attested-only,
aggregate-never-disclose above a comparable-count floor, never pre-selected, and age shown as
part of the fact.

**The decision that matters.** "Attested" is a *structured predicate over the record*, not
something a language model can infer from a transcript. So the guarantee is enforced in
`write_precedent()`, which refuses a row that is not already an attested aggregate above the
floor. The custom strategy's extraction prompt only shapes what that filter lets through; it
is **not** what makes the rule true. Stated plainly because the opposite is the easy mistake:
pointing a semantic strategy at raw conversation and calling the result precedent would
launder unattested content into institutional memory, **and it would look like it was
working.**

**Rejected.** A `userPreference` strategy over answer content. A remembered answer offered
back is a pre-selection, and a pre-selected answer nobody looked at becomes that person's
attributed answer — the exact failure this platform exists to prevent.

**Also rejected: adapting a conventional memory helper.** Two mistakes in wiring AgentCore
Memory raise **no error**: `create_memory_record` is not the write path for conversational
memory (an **event append** is), and a resource carrying **zero extraction strategies** stores
nothing however correct the write. Either way reads, listing and deletion all keep working and
simply return empty — which fails exactly like an unreachable table. Written from scratch, with
both halves pinned by tests.

---

## 3. Component contracts

### 3.1 Capability invocation (the external contract)

| | Shape |
| --- | --- |
| Request | `{ "prompt": <text>, "session_id": <string>, "assessment": <the record> }` |
| Response | `{ "result": <text>, "session_id": <string>, "basis": "context", "is_evidence": false, "disclosure": <string> }` |
| Fail open | `{ "result": "", "available": false, "blocks_nothing": true, "because": <string> }` |
| Warmup | `{ "type": "warmup" }` → readiness, model id, gateway status, memory status, instrument counts — without a model call |

`assessment` is **required**. The service refuses without it rather than proceeding
unguarded, because an agent that cannot be told what is on record cannot be caught claiming
something that is not.

### 3.2 Tool layer (agent ↔ engine)

All stateless, all returning the uniform envelope.

| Tool | Input (key fields) | Output (key fields) | Owner sub-agent |
| --- | --- | --- | --- |
| `risk_route` | assessment?, answers?, explain_question? | active_paths[] **with reasons**, severities, objectives, gates, visible_question_count, explanation{because[], authority[]} | Advisor |
| `risk_score_intake` | text, scores? | floor verdict *or* anchors to score against *or* deterministic feedback; always `blocks_submission: false` | Advisor |
| `risk_draft_verify` | draft{basis,value,quote,source_id,because} | `proposed` (unconfirmed) or `refused` + why | Advisor |
| `risk_check_policy` | assessment?, question? | authority[] quoted verbatim, *or* findings[] + uncovered_clauses[] | Assurance |
| `risk_build_report` | assessment?, summary?, scenarios? | the derived report; vetted agent additions | Handoff |

### 3.3 Engine return contract (invariant)

Every engine function returns at least `decision`, `binding_rule` and `disclosure`. That is
what makes the surface explainable and audit-ready rather than merely correct.

---

## 4. Interaction & data flow

```
caller + the assessment record        (authoritative — ADR-4)
      │
      ▼  [Orchestrator] session.adopt()  — REFUSES if no record (G-65)
      │                 build AssessmentContext: their words, question→answer, what is open
      │
      ├─▶ [Advisor]   risk_route          ─▶ what applies, why, and the clause behind it
      │               risk_score_intake   ─▶ floor (no model) → scores → deterministic copy
      │               risk_draft_verify   ─▶ proposal, unconfirmed, or a refusal
      │
      ├─▶ [Assurance] risk_check_policy   ─▶ verbatim clause; breaches with both quotes
      │
      └─▶ [Handoff]   risk_build_report   ─▶ derived report (+ vetted summary & scenarios)
      │
      ▼  [Orchestrator] contextual guardrail over the reply  ─▶ pass, or FAIL OPEN
      ▼  memory: append the turn (best-effort, never blocks)
```

**Failure isolation.** A tool error degrades to a sentence inside the composed answer; an
orchestrator or model failure returns the typed pass-through. A memory failure is logged and
ignored. Nothing in this path can return a hard error to the caller, and nothing in it can
stop a person submitting.

---

## 5. Rules the spec leaves implicit

These are the decisions needed to turn the spec's semantics into deterministic behaviour.

| Rule | Definition |
| --- | --- |
| **Operator set** | `equals`, `not_equals`, `includes`, `excludes`, `any_of`, `all_of`, `answered`, `blank`, `at_least`, `at_most`, `severity_at_least`, `path_active`, `always`, with `all`/`any`/`not` nesting |
| **Positive evidence** | One early return: every operator except `answered`/`blank` is **False** on a missing answer, including the negative ones |
| **`blank`'s boundary** | The one operator that asserts absence. Legitimate, but the lint **forbids it in any activation or accumulation rule**, since silence activating anything is how an area gets waived by omission |
| **Severity source** | An anchored question stores the *band* (the anchor is the option); a derived question stores a *fact* and a declared map converts it |
| **Unknown severity** | `severity_at_least` is False against `None`. Never treated as Low |
| **Visibility** | intake→display condition · gate→not always-applies · T1→category open + condition · T2→path active or always-on · T2c→the four kinds · T3→accumulated · T3c→**parent is Yes** + cross-tier condition |
| **Conditional kinds** | `severity_fired` (lead ≥ threshold) · `always_fired` (path active, severity-independent) · `cross_tier` (+ a Tier-1 selection) · `nested` (+ a sibling's answer) |
| **Accumulation** | Union over the same engine; every objective retains **every** reason that pulled it in |
| **Breach** | A clause governs the question **and** the answer is No or Partial. It **replaces** the bare gap. Unanswered is never a breach; N-A is never a breach |
| **Open finding** | Unresolved **or** accepted-but-expired. One rule, one place |
| **Verbatim match** | Whitespace-normalised substring, case-sensitive. One matcher, shared by the gate, the scorer and any highlighter |
| **Attestation authority** | control family → risk domain, derived from the question id **server-side**; generalist covers all; admin exempt; requester never |
| **Intake pass** | total ≥ 6 of 10 **and** no dimension at 0 — read from the rubric file, never computed in code |
| **Out-of-range score** | **Dropped**, never clamped. Clamping turns nonsense into a number somebody then acts on |

---

## 6. Guardrail enforcement points

Where each rule is *enforced*, not merely stated:

| Requirement | Enforcement point |
| --- | --- |
| Never guess (§5.2) | `violates_never_guess()`, called by `risk_draft_verify` before anything is returned |
| Paraphrase and **stitched quotes** refused | `verbatim_match()` — normalised substring, so a quote assembled from two real fragments is not contiguous and fails |
| Abstention is a correct outcome | `basis: not_stated` with no value passes the gate; carrying a value refuses |
| A proposal is not an answer | Gate returns `confirmed: False, recorded: False`; `answer_map()` **ignores unconfirmed answers**, so routing cannot move on a suggestion |
| No internal identifier reaches a person | `uttered_internal_identifier()` over every human-readable output; seven patterns, each with a test |
| No answer attributed to somebody who did not give it | `claims_unrecorded_answer()`, **clause by clause**, matching the claim's topic against the question and its value against that question's answer |
| Nothing claims work was recorded | `claims_work_was_recorded()` on the conversational path |
| The guardrail cannot be skipped | It raises without an `AssessmentContext`; the drafting path's call has its own regression test |
| Fail open | `_pass_through()` and `intake_pass_through()`; every scoring return carries `blocks_submission: False` |
| Findings only on accumulated controls | `synthesize_findings()` iterates `accumulate()`, never the whole objective set |
| Precedent is attested-only and floored | `write_precedent()` on the way in, `_mentions_enough()` on the way out |
| A scenario built on nothing | `vet_scenarios()` drops it entirely rather than showing it with a caveat |
| A summary nobody will read | `vet_summary()` — the guardrail plus a hard three-sentence gate |
| Authority cannot be self-asserted | `attestation_authority()` resolves the family from the question id, never from caller input |

---

## 7. Non-functional design

| Area | Design choice |
| --- | --- |
| Latency | Sub-agents run the fast model; the engine is sub-millisecond; the model does no routing |
| Reproducibility | Pure engine + versioned data → identical outputs for identical inputs |
| Resilience | Tool failures degrade to a message, agent failures to a typed absence, memory failures to a log line |
| Security | Own runtime and isolated tool Lambda, least privilege; documents held as extracted text with no download path; no assessment content in the cross-assessment namespace |
| Observability | OpenTelemetry from the service's first day, via `opentelemetry-instrument` in the image; spans land in the runtime's own log group |
| Testability | 146 tests, no AWS and no model. Every model-dependent gate is proved with **fabricated** replies |

---

## 8. Risks & open questions

| Item | Note |
| --- | --- |
| **No model has been called** | Every gate is proved against fabricated replies, deliberately. But no claim is made about the *quality* of scoring, drafting or summarising until a real run happens — and a local model would measure the harness, never the quality bar |
| **Nothing deployed** | No Docker and no PyPI on the authoring machine: `constraints.txt` carries no pins and `cdk synth` has not run |
| `claims_unrecorded_answer` limits | Catches a fabricated *value*; will not catch every rewording, and will occasionally suppress a true statement. That direction is deliberate under fail-open, and the assessor's attestation is the backstop |
| Attachment retention | Still open in the spec (§3.6). Documents are extracted text only; keeping originals stays blocked |
| Seven gate-only risk areas | Pilot depth (G-50). Each says on screen that it stops deliberately; adding depth is a data change |
| Composite score | Deliberately absent. Whether one exists at all is an open governance question |
| Precedent seed is synthetic | The rules are real and tested; the aggregates are invented until real attested history exists |
