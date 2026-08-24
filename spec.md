---
spec-version: 2026-08-23.1
---

# Front Door AI Risk Advisor — Specification

**Status:** ACCEPTED 2026-08-20. This is the spec of record; the governance log (§13) is active.
**This document is the BRAIN.** The governance log (§13), the delivery slices (§17), acceptance criteria (§19), and the requirements register (§20) all live here and nowhere else — there are no side plans. Work traces to a requirement ID; requirements trace to a slice; slices trace to done-when gates. Anything not traceable here is, by definition, not being built.
**This document is the single source of truth for the product it describes.** Settled sections are not re-opened casually; changes to them are governance events recorded in the log (§13). The instrument's *content* (questions, rubrics, mappings) is not in this document — it lives as versioned data (§6.2); this document defines the *semantics* that content must obey.

---

## 0. Build Rules — how this specification is implemented

These rules bind any implementer, human or Claude Code, before a single line is written. They are the development-side twin of the product's never-guess invariant.

**Working discipline**

1. **Do not implement the entire specification in one pass.** Work in vertical slices, in the order given in §17.
2. **Before coding, inspect the existing repository** and determine what already exists. Reuse what satisfies the spec; never rebuild it.
3. **Do not proceed to the next layer until the previous layer's tests pass.** Green gates are the permission slip, nothing else is.
4. **Do not introduce technologies, abstractions, or dependencies** unless this specification requires them.
5. **Do not implement deferred or out-of-scope capabilities** (§16, §18) — not even scaffolding for them, beyond the interfaces §18 explicitly marks "design now".
6. **After each slice, run the relevant tests and report what changed** — files, LOC delta, tests added, behavior altered.

**Do-not-invent rules**

7. Do not invent requirements. Do not infer unspecified business logic.
8. Do not silently resolve contradictions — when the spec is ambiguous or self-conflicting, **stop and name the ambiguity**; resolution is an owner decision.
9. Do not add features because they seem useful. Prefer the simplest implementation consistent with the spec.
10. Do not change settled decisions (§13) without explicitly flagging the change and obtaining a governance-log entry.
11. **Every slice ends with the review protocol (§21), and no slice begins until the prior slice's review is closed.** Silence is never approval — from either side.
12. **Every slice plans its agentic opportunity** (§22) — designed and registered, not built. Phase 1 ships no agent; it may not ship anything that forecloses one.
13. **Every question ships designed.** Before any question a person answers reaches a screen, it passes the `instrument` skill's part-1 probe: could they answer it without a glossary, what happens if it does not apply to them, and does it carry helper text that teaches. A question shipped without that pass is a defect, found later at ten times the cost.
14. **Every slice ships demo-ready UI** (§23) and obeys the experience principles (§24). A slice with working logic and unfinished interface is not done.
15. **Every slice is independently verified before it advances** — the slice-verifier subagent (§15) runs UAT and regression, and its report is attached to the review. Self-certification is not verification.
16. **Critique is owed, not optional.** The implementer must surface disagreements, weaknesses, and risks in the owner's instructions as readily as in its own work. Agreeable implementation of a flawed instruction is a failure of this specification, not a courtesy.

## 1. Mission and purpose

### 1.1 The mission

**The Front Door AI Risk Advisor modernizes enterprise risk intake by deploying an intelligent, agentic AI layer across a complex GRC ecosystem.** It replaces fragmented, high-friction processes with a centralized, guided front door — accelerating assessment timelines from months to days, enforcing data integrity through mandatory declarations and attestations, and delivering high-fidelity risk signals directly to risk analysts.

Three problem statements, owner-supplied and normative:

1. **Fragmented ecosystem & poor telemetry.** Risk data is siloed across disparate platforms, preventing a holistic view of enterprise risk and producing inconsistent telemetry.
2. **High friction for business users.** Assessment fatigue: confusing starting points, disjointed tooling, no guidance through the lifecycle. Real projects have spent **as much as 90 hours** working through the current assessments.
3. **Inconsistent analyst intake.** Decentralized manual processes fail to deliver the standardized, comprehensive data analysts need to prioritize and identify risk.

The answer to all three is one sentence:

> **One front door for the business user; every risk area's own process intact under the hood.**

The stakes are strategic: as AI accelerates delivery, siloed and slow risk processes become the binding constraint on innovating safely. A user-friendly risk process with governance embedded from the start is what lets speed and rigor coexist.

**North stars, measured — each answers one problem statement:**
1. **Time-to-complete** (answers friction) — from ≈90 hours of scattered effort toward a single guided session; the agentic layer (§7) exists to push this further still.
2. **One collection spot** (answers fragmentation) — a requester never visits a second system to be assessed; risk areas consume from the platform, not from the requester.
3. **Governance from the start** (answers inconsistent intake) — rigor embedded in the flow (routing, declaration, attestation, findings), never bolted on after.

### 1.2 The six capabilities, phased honestly

The mission is delivered as six capabilities. Each row states what exists today and what the agentic layer adds — the demo claims only the middle column (§24.8: never imply an unbuilt thing runs).

| Capability | Today (deterministic, built) | Agentic (Phase 2, Bedrock/AgentCore — G-51) |
|---|---|---|
| **Conversational intake** | Structured guided intake: conditional reveals, "I'm not sure" first-class (FR-23), teaching help text (§24.11) | A thought partner that drafts answers from evidence with verbatim citations (§7) |
| **Regulatory signaling** | The engine derives paths and pre-answers gates from evidence, each with its reason (FR-4, FR-5, FR-22) | Reasoning over inputs to surface regulatory considerations and route them to the owning office |
| **Scoping & triage** | Severity rubrics summon control objectives with the answer that pulled each in (FR-6–FR-8, §3.3) | Contradiction finding, drafted summaries, preliminary control recommendations (§22.1) |
| **Submitter declaration gateway** | S7: submission requires an explicit declaration of accuracy over named answers (FR-37, G-52) | The agent assembles the declaration record; the person still signs it |
| **Assessor review workflows** | Hand-offs with threaded conversation and derived obligations (FR-36); full review queue and attestation at S8 (FR-16–FR-18) | Divergence signals and follow-up drafting for the reviewer (§22.1) |
| **Telemetry** | Insert-only evidence trail; every answer attributed (NFR-19) | OpenTelemetry from the agent service at its birth (§6.4) |

**Structural agility is the instrument-as-data rule (§6.2):** new risk workflows are new versioned data — questions, paths, rubrics, mappings — not new code, which is how the platform incorporates emerging risk domains without overhauling GRC backends.

### 1.3 The purpose

A platform that takes a business activity from **description to attested, exportable risk assessment** with the minimum burden on the business user and zero loss of rigor for the risk organization.

Three promises, in priority order:

1. **The instrument is rigorous.** A three-tier, condition-routed assessment: what is this activity, how severe is its risk along each activated path, and do the controls that risk profile demands actually exist.
2. **People only ever see what applies to them.** Routing is evidence-driven and explainable; a project that touches nothing sees almost nothing.
3. **Every answer is accountable.** Who said it, on what basis, who declared it accurate, who attested it — and when AI assistance is active, the verbatim evidence it came from. Nothing is ever guessed.

Every requirement in §20 must serve at least one north star or one promise; anything that serves neither does not belong in the product.

## 2. Roles

| Role | Does | Does not |
|---|---|---|
| **Requester** (business owner) | Completes intake and Tiers 1–3; **declares** their answers accurate at submission (G-52); responds to reviewer questions; sees their own project only | Attest, resolve findings, change the instrument |
| **Risk Assessor** (reviewer) | Triages the queue; attests every visible answer (approve / correct / N-A-with-reason); disposes findings; accepts scenarios; runs final checks; packages | Author instrument content; approve their own four-eyes actions |
| **Admin** | Manages users, reviewer groups, scoring configuration; ratifies instrument changes | Bypass attestation or findings gates |

Attestation authority is enforced **server-side** against reviewer-group membership for the question's domain; admins are exempt. The UI is never the enforcement point.

## 3. The instrument — structural semantics

### 3.1 Shape

```
INTAKE  →  TIER 1 (per category: gate → path selection → conditionals)
        →  TIER 2 (severity per activated path + always-on block)
        →  TIER 3 (control objectives accumulated from Tiers 1–2)
```

- **Intake** — structured project metadata in ordered sections (description, ownership, categorization, compliance & data context). Intake fields may be conditional on other intake fields. Intake activates nothing by itself; it is the front door and the project's identity record.
- **Category** — a top-level risk area (third-party, solution architecture, AI/model, data & privacy, legal/regulatory, operational, security & resilience, governance, ethics & conduct, people & capacity, jurisdiction-bound execution). Each category owns exactly one **gate**: a yes/no question — *does this risk area apply at all?* Gate = No closes the category; nothing inside it is ever shown.
- **Path** — the routing currency. A named, human-readable risk thread (e.g. *Third-Party Logical Access*, *Agentic Autonomy*, *Cross-Border Data Transfer*). Tier-1 selections activate paths. The relationship is many-to-many: one selection may light several paths; one path may be lightable from several categories. **Paths, not categories, are what Tier 2 attaches to.**
- **Tier-2 severity question** — attached to a path; presents **Low / Medium / High with a written rubric anchor per band as the answer options themselves**. The anchor text is the definition; the requester self-rates against prose, never against a bare number. A small always-on block (business criticality, breadth, audience, material impact) is assessed on every project regardless of routing.
- **Conditional** — a follow-on question that reveals on a trigger:
  - *severity-fired* — reveals when its lead question's severity meets a threshold (typically Medium-or-High);
  - *always-fired* — reveals whenever its path is active (severity-independent);
  - *cross-tier* — additionally requires a specific Tier-1 selection;
  - *nested* — additionally requires a specific selection on a sibling conditional.
- **Control objective** (Tier 3) — a named control requirement with a family (IAM, Data Protection, Network & Boundary, Logging, Resilience, Ops, SDLC, AI Governance, Compliance, Privacy, Ethics, Governance, HR, Third-Party), a parent question, and optional child questions. Objectives **accumulate** from Tier-1/Tier-2 answers (§3.3) and are then **self-assessed**: does this control exist for this activity?

### 3.2 Routing rules (the engine's law)

1. **Positive evidence only.** An unanswered question satisfies nothing. Silence never activates, and negative operators (not-equals, excludes) do not pass on missing answers. No risk area can be waived by omission.
2. **Severity fails closed.** A severity comparison against an unknown severity is false. Unknown is never treated as Low.
3. **One visibility predicate.** A question is visible iff its category/path context is active AND its own display condition passes. Every surface — the requester flow, review queue counts, drafting scope (when the agentic layer is active), and the packaging gate — uses this single predicate. A question is in the funnel everywhere or nowhere.
4. **Union with provenance.** Path activation and control accumulation are unions across all satisfied triggers, and every activation retains its reasons ("lit by: …"). The requester and reviewer can always see *why* something is being asked.
5. **Derived severity.** Severity comes from anchored self-rating (the band is the answer) or is derived from a fact answer through a declared mapping (e.g. volume bands → Low/Medium/High). Derivations are data, never code.
6. **Capture vs. scoring.** Some questions exist to capture routing/registry detail without contributing severity (marked as capture). The distinction is explicit in the instrument data; capture answers never affect accumulation thresholds.
7. **Recompute, don't remember.** Activation and accumulation are pure functions of current answers. Changing an answer re-derives everything downstream; orphaned answers to no-longer-visible questions are retained as history but leave the funnel.

### 3.3 Control accumulation

Tier-1 selections and Tier-2 severities accumulate control objectives:

- a Tier-2 severity question may require objectives at **minimum severity thresholds** (e.g. *PAM required when provider access ≥ Medium*);
- specific option selections (Tier-1 or conditional) may require objectives directly, each with a stated reason.

Accumulation is expressed **as activation conditions over the same engine** (§6.3) — there is no second evaluator. The accumulated set, with reasons, is continuously visible to the requester (the ledger).

### 3.4 Tier-3 self-assessment semantics

Each accumulated objective is answered with exactly one of:

| Answer | Meaning | Consequence |
|---|---|---|
| **Yes** | Control exists and applies | Child questions reveal (subject to their own cross-tier conditions) for detail |
| **Partial** | Something exists; enhancement needed | Written note **required**; produces an enhancement finding at submit (§4.3) |
| **No** | Gap | Written note **required**; produces a control-gap finding at submit (§4.3) |
| **N-A** | Does not apply to this activity | Written justification **required**; exported explicitly as "N-A — reason", never as blank |

Child questions never fire unless the parent is Yes. Suppressed children (cross-tier condition unmet) are invisible, not "skipped".

### 3.5 Pre-deploy verification

Objectives and children may carry pre-deploy tags. The pre-deploy stage activates for build/change activities and **unlocks only when every visible assessment-stage answer is attested** — "what you built" is checked only after "what you said" is signed. Pre-deploy checks link to the claims they verify through ratified relationships.

### 3.6 Attachment retention — open, blocking

The retention posture for uploaded documents — how long bytes live, who may purge, what an export carries — is **not yet written**. It is an owner decision (§14), and S4.6 stores no byte until it exists. This subsection is the placeholder those requirements cite so the gap is a named thing, not a dangling reference.

## 4. The process

### 4.1 Stages

```
DRAFT (requester)          →  IN REVIEW (assessor)        →  EXPORTED
intake → T1 → T2 → T3 →       attest all visible →           packaged, immutable,
submit (findings synth)       findings disposed →            replayable
                              scenarios → final check →
                              package
```

Stage transitions are one-way facts (submitted-at, exported-at timestamps). Submission with open gaps is allowed but explicit: the requester confirms a named list of unanswered questions; reviewers see gaps exactly as they are.

### 4.2 Review & attestation

- Every **visible** question requires attestation before packaging: approve as-is, correct-and-attest, or N-A with reason.
- Attestation of an answer shared across assessments warns about its reach and records the confirmation.
- Attested answers are correctable only by an explicit correct-and-re-attest act — never silently re-waivable.
- Reviewer keyboard loop (next/previous, approve, edit, N-A) is a first-class requirement, and focus management across dialogs is part of its acceptance criteria.

### 4.3 Findings

At submission, Tier-3 answers synthesize findings automatically: **No → control gap**, **Partial → enhancement**. Findings — however raised — resolve only through four governed dispositions:

1. **Answer corrected** (the underlying answer was wrong);
2. **Not applicable** (with justification);
3. **Remediation planned** (owner + due date required);
4. **Risk accepted** (four-eyes: a second, named person accepts; expiry required; **expired acceptances reopen automatically**).

One rule decides "open" everywhere (packaging, queue, obligations): unresolved, or accepted-but-expired.

### 4.4 Risk scenarios

Accepted findings and evidenced answers seed proposed risk scenarios; each scenario must cite the exact answers it builds on. Scenarios count only when a Risk Assessor accepts them. Accepted scenarios ship in the package.

### 4.5 Packaging & export

Packaging requires: every visible question attested · zero open findings · zero open conflicts. The export is **insert-only and replayable**: a structured record mapping every attested value (including explicit N-A strings) to destination fields, plus accepted scenarios, plus the coverage of what was asked and why. Re-export creates a new record; nothing is overwritten.

### 4.6 Scoring — deliberately open

A frozen grade may be computed at packaging (machinery permitted) but **no composite score is displayed** anywhere in the flow. Whether a composite exists at all is an open governance question (§14) inherited from the URA's no-composite stance. This spec does not settle it.

## 5. Invariants (non-negotiable, enforced in the schema and tests — never only in UI)

1. **Evidence records are insert-only.** Drafted/AI-produced answers are never updated in place; corrections are new records.
2. **Never-guess.** Any AI-produced answer states its basis — *stated* (with a verbatim quote), *inferred* (with grounding), or *not-stated* (full abstention). A stated answer without a verbatim quote is structurally impossible (database CHECK + gate). Abstention is a correct, scoreable outcome.
3. **One verbatim matcher.** Quote verification is whitespace-normalized substring matching, defined once, used by every consumer (gate, scorer, highlighter). A second matcher is a defect by definition.
4. **One visibility predicate** (§3.2.3). **One similarity rule** for duplicate detection.
5. **Human attestation is the only path to "counts".** Nothing AI-produced is final without a named human attestation, authorized server-side (§2).
6. **Relationships go live only via propose → ratify.** Even seed data walks this path. Ratified edges carry evidence.
7. **Instrument versions are immutable once activated.** Change = new version. Answer records pin the version they were made under; history always renders.
8. **Four-eyes** on instrument activation and risk acceptance: proposer ≠ approver, enforced structurally.
9. **N-A is never blank** — always a recorded reason, exported explicitly.
10. **Routing law** (§3.2.1–2): positive evidence only; severity fails closed.

## 6. Architecture

### 6.1 The seams (do not scatter)

- **Agent access** — exactly one module knows how the agent is reached. Local transport now; AgentCore Runtime later; nothing else in the codebase may address the agent.
- **Session/conversation state** — exactly one module reads/writes it, shaped for an AgentCore Memory swap.
- **Model access** — only the agent service knows a model exists. The web application never imports a model SDK.

### 6.2 Instrument-as-data

The instrument (categories, gates, paths, questions, rubrics, conditionals, objectives, accumulation rules, destination mappings) is **versioned seed data**, validated by a coherence gate (§8) before it can activate. Prose reference documentation is *generated from* the data — the human-readable rendering can never drift from the machine truth. Changing the instrument is a data change through governance (§8), never a code change; anything the instrument cannot express in data triggers a design conversation, not a workaround.

### 6.3 The engine

One condition engine evaluates: equals / not-equals / includes / excludes / any-of / all-of (set membership on scalars) / answered / blank / numeric thresholds / severity-at-least / path aliases, with all / any / not nesting. Everything routes through it — gates, path activation, conditional reveals, control accumulation, pre-deploy. It renders any condition as one English sentence (the explainability surface) and lints authored conditions for contradictions.

### 6.4 AWS deployment — settled (G-7)

**The deployment target is the owner's AWS sandbox account, using Bedrock and AgentCore. This is settled, not aspirational.** The prototype runs locally for iteration speed; every Phase-1 decision must keep the path open by construction. The migration plan of record:

- **Tier 1 — the day-one lift.** One web container (this repository's real shape — the two-service split arrives with the agent service, not before), built from the repo root; **ECS Express Mode** on Fargate (G-62 — App Runner closed to new customers on 30 April 2026); RDS for PostgreSQL 16; deployment changes environment variables, never code. pgvector is not provisioned until a phase needs embeddings (G-53). **The runbook is `deploy/README.md` and the stack is `deploy/infra.yaml`; the architecture is drawn in `deploy/architecture.md`.**
- **Tier 2 — managed model access.** Bedrock for all model calls, behind the model seam. **Critical path: the Bedrock model-access request is owner-side and its approval time uncontrollable — it is filed before, not during, the migration (tracked in §14).**
- **Tier 3 — AgentCore as substrate.** Runtime behind the agent seam, Memory behind the session seam, Gateway for enterprise connectors, Observability for traces.

**Status of the seams (§6.1), 2026-08-23: two of the three are in code.** `src/lib/agent.ts` (transport: `none` by default, `local`, `agentcore` named but unimplemented) and `src/lib/session.ts` (Postgres now, AgentCore Memory later), with the wire contract in `src/lib/agent-contract.ts`. The third — model access — belongs to the agent service, which is the next slice; nothing under `src/` may import a model SDK, and a test asserts it. Built as interfaces with a local implementation behind them before any model call was written, exactly as this section required.

**Phase-1 obligations (firm):**

1. The web service containerized; the image builds from the repo root.
2. All environment-specific behavior flows through environment variables; zero `local vs. cloud` branches in code.
3. Postgres-only persistence, RDS-compatible; migrations as plain SQL (G-53).
4. No dependency without an AWS-managed equivalent, absent a governance-log entry accepting the exception.
5. OpenTelemetry spans from the agent service **from its first day** — the obligation attaches at the service's birth in Phase 2; the web app is exempt until then, and that exemption is stated here rather than discovered.

A Phase-1 change that violates any of these is rejected in review regardless of how well it works locally.

## 7. The agentic layer — the mission, phased (G-51)

The agentic layer is the product's stated core; Phase 1 ships the deterministic platform it will stand on, and this section is the contract every phase must honour:

- **What it does when active:** drafts answers from requester-provided evidence (documents, conversation) with verbatim citations and basis labels; renders answer choices as tappable options whose labels are quotable evidence; issues receipts naming exactly what was recorded and what failed with a next step; explains any question's routing on request; hands off (never performs) submission.
- **What it may never do:** answer from nothing; paraphrase evidence; utter internal identifiers to users; advance the interview on silence; attest, declare, resolve, or accept anything; act as an autonomous orchestrator of the governed pipeline — AgentCore is substrate, never the decider (§6.4).
- **How it is measured:** a ground-truth eval over the live instrument in which full abstention on absent evidence is a scored correct answer; per-domain accuracy baselines are committed artifacts and CI blocks regressions. Local-model runs measure the harness, never the quality bar.
- **Delivery is the Phase-2 epic** (§16, G-51) against the stable instrument — the three seams first, then conversational intake, drafting passes, and the agent-reviewed instrument-change workflow. Until a capability ships, it stays unreachable from the product UI and the demo never implies it runs (§24.8).

## 8. Governance

- **Instrument changes:** seed-data pull request → coherence gate (referential integrity; activation satisfiability; no cycles; reachability of every question and objective; rubric completeness; duplicate sweep; destination coverage; ground-truth coverage when the agentic layer is active; constraint-relaxation deny-list on any prompt text) → **parity/regression harness** → four-eyes review → merge = ratification. No runtime authoring surface: the database can never fork away from the versioned data.
- **The governance log** (in this document) records every settled decision and every deliberate deferral, numbered, dated, one paragraph each.
- **Automated gates:** the full check chain (tests, type-safety, coherence gate, eval when active) runs on every change; sensitive paths (applied migrations, instrument seeds, environment files) are write-guarded; file-size budgets are enforced mechanically.
- **Independent audits:** standing auditor roles re-verify ratified relationships against their evidence, quote provenance against sources, and coherence after any instrument change.

## 9. User experience commitments

The behavioural law lives in §24 (principles) and §23 (surface standard); this section holds only the two commitments no other section owns: the reviewer queue is **ordered by need** (findings first, then age), and the requester's **live ledger** (activated paths with reasons, severities, accumulated objectives) is always visible (FR-11).

## 10. Quality bars

The bars are stated where they are checked: engine and journey criteria in §19, test tiers in §26.4, UAT rounds in §21/G-24, the coherence gate in §8. Two bars live here because nothing else owns them: **migration safety** — schema and SQL asserted equivalent by tests applying real migrations to in-memory Postgres, and historical projects must always render — and **property/differential testing** of the engine against the instrument's reference behavior.

## 11. Clean-code charter

- No parallel implementations of anything the engine, matcher, or predicate already does.
- File budgets enforced mechanically (components ≤ 400 lines; hard ceiling 800).
- Dead code is deleted in the same change that orphans it, with accounting; an unused-export gate keeps it dead.
- Comments state constraints, not narration or history; behavior is pinned by tests, not comment archaeology.
- Documentation is short, current, and rewritten rather than appended; anything derivable from data is generated.

## 12. Out of scope (this spec version)

Composite scoring policy (§14) · framework crosswalks (planned; will anchor to control objectives) · runtime instrument authoring UI · customer-supplied framework/questionnaire import · multi-tenancy and production identity/SSO (the persona switcher is a pilot device, G-26, and the admin surface ships knowingly unrestricted until identity exists, G-25) · destination-system write-back (§27 assembles and downloads; nothing sends) · attachment bytes until the retention posture is written (§3.6). The agentic layer is no longer out of scope as a category — it is the Phase-2 epic (G-51) and excluded from Phase 1 only.

## 13. Governance log

Every settled decision and every deliberate deferral, numbered, dated, one paragraph each — the decision and its rule, not the incident (the incidents live in `uat/` and git history). Ascending order; a superseded entry stays, marked.

- **G-1 (settled):** This specification supersedes the prior platform spec; the prior instrument (placeholder catalog) is retired in full. Historical assessments remain readable via version pinning.

- **G-2 (settled):** The three-tier instrument defined in §3 — categories/gates/paths, rubric-anchored severity, threshold-based control accumulation, Tier-3 self-assessment — is the assessment model of record, transcribed from the owner's reference design and verified by differential testing.

- **G-3 (settled):** Structured intake is the front door for Phase 1. **Reopened by G-51 (2026-08-23):** conversational AI intake is the Phase-2 epic's headline capability, no longer an indefinite deferral.

- **G-4 (settled):** Tier-3 No/Partial answers synthesize findings at submission (§4.3); packaging remains blocked on open findings.

- **G-5 (settled):** No runtime instrument authoring; seed-PR governance only (§8).

- **G-6 (settled):** The agentic layer's contract (§7) is normative now, even while dormant — nothing may be built that would violate it later.

- **G-7 (settled):** AWS is the deployment target and §6.4's tiered migration is the plan of record. Phase 1 builds AWS-ready by construction (the five firm obligations in §6.4); cloud execution itself is Phase-3 work. The Bedrock model-access request is the standing critical-path item and is owner-owned.

- **G-8 (settled):** Execution route — **fresh repository, built slice by slice (§17)**. The prior repository is retained untouched as the **parts shelf**: proven components (condition engine, invariants schema, verbatim matcher, eval harness, agent service) are salvage candidates, and each salvage-or-rebuild decision is made at the slice that needs the part, recorded against that slice. The prior repository is never developed further and is decommissioned only after Phase-1 acceptance.

- **G-9 (settled):** Delivery runs under the slice review protocol (§21) — pre-flight before each slice, structured review with mandatory self-critique after it, refinements applied and re-gated before the next slice. Adopted 2026-08-21 after the intake review demonstrated its value in both directions.

- **G-10 (settled):** Intake question set refined 2026-08-21 (S1 review): AI capture with a conditional detail field; plain-language "new vs. update" replacing the acronym list, with an optional prior-work pointer; objective launch date replacing self-reported priority; lifecycle stage retired (absorbed by initiative type); procurement status softened to Yes/No/Not-sure; compliance-obligation areas and granular PII detail removed from intake — both are asked at Tier 1/2 where they route (T1-LRC-2, T2-PRIV-1.C). Consequence: intake now carries routing-relevant answers, which is why FR-22 exists.

- **G-11 (settled):** Every slice registers its agentic opportunity (§22) as a designed, guard-railed Phase-2 feature. Phase 1 builds none of it and may foreclose none of it. First entry: the intake quality assistant (rubric grading, contradiction detection, opt-in rewrite of the requester's own words).

- **G-12 (settled):** Every slice ships demo-ready UI to the §23 standard; a slice with working logic and unfinished interface is not done. Taste calls belong to the owner and are applied before the next slice begins.

- **G-13 (settled):** Independent verification is a Phase-1 capability, not a Phase-2 one: the slice-verifier subagent runs UAT and regression against every slice before it advances, cannot edit code, and its report is part of the slice review. Adopted 2026-08-21.

- **G-14 (settled):** §24 experience principles adopted 2026-08-21 — each derived from a defect found in this build, audited by the slice-verifier, and binding on every surface. The first two, in the owner's framing: never re-ask what someone said they don't know, and pace the journey rather than presenting a wall.

- **G-15 (settled):** §25 error-handling standard adopted 2026-08-21 (NFR-13): expected failures are typed values not exceptions; the user gets a sentence and a quotable reference while the log keeps the detail; every message says what happened, whether their work is safe, and what to do next; input is never lost; error paths are tested.

- **G-16 (settled):** §26 cloud-native construction rules adopted 2026-08-21 as workspace law (NFR-14 to NFR-17): pure logic separated from executors, state and persistence externalised behind one interface, configuration only through a single validated env module, and three separately-runnable test tiers. The migration guide (§26.7) is a named deliverable before production. Recorded correction: development-time subagents do not migrate; the runtime agents are the Phase-2 features in §7.

- **G-17 (settled):** The persistence engine is an open decision under standing assessment (§14.6), not a settled choice — Postgres is Phase 1's implementation behind the store interface, DynamoDB is a live candidate. Store-specific choices must be flagged in slice reviews; the implementer reports with evidence after S9 and before the AWS migration. Recorded 2026-08-21 at the owner's direction.

- **G-18 (settled):** Documentation architecture — law in SPEC (short, governed, traceable), procedure in skills (loaded on demand), teeth in tests and hooks. Skills may not carry normative rules that must always hold, because loading is probabilistic; anything always-true is stated here and routed from CLAUDE.md. Adopted 2026-08-21.

- **G-19 (superseded by G-20):** "Technology / Non-Technology" retired from intake (2026-08-21): it asked a business user to classify against our taxonomy. Its replacement question was itself removed by G-20; the surviving rule is **ask about their world and derive the taxonomy.**

- **G-20 (settled):** The intake question about what an activity introduces or changes is removed entirely (2026-08-21, owner call): intake is the identity record; routing is Tier 1's job, one gate at a time. Pre-fill (FR-22) survives on signals intake genuinely owns — vendor involvement, initiative type, data classification, the AI question.

- **G-21 (settled):** Portfolio memory registered 2026-08-21 — precedent suggestion, application profiles, and reviewer-side divergence signals — governed by §22.4's four rules: attested-only (no precedent laundering), aggregate-never-disclose with a minimum comparable count, no anchoring (never pre-selected; for binary gates prefer showing patterns after the answer), and age shown as part of the fact. Divergence is a reviewer triage signal, never pressure on the requester toward the majority.

- **G-22 (settled):** Policy grounding is a Phase-2 capability with a standing exception (2026-08-21): definitions quoted from ratified policy may be shown as help today, verbatim and cited; anything generative waits for §22.5.

- **G-23 (settled):** Helper text teaches, never repeats the label (2026-08-21, §24.11): every question carries help written for the person answering, checked mechanically for the no-repeat rule.

- **G-24 (settled):** Every finished slice carries a committed UAT record (2026-08-21, NFR-18) meeting six criteria: numbered checks with objective pass lines, negative paths, evidence per check, the spec version it ran against, findings with dispositions, and an honest "not verified" list. The record is the artifact; a walk that leaves no record did not happen.

- **G-25 (settled):** AI transparency is a product feature, not a debug screen (2026-08-21, FR-24): `/admin/agents` lists every agent with when it runs, what it can reach, guardrails, and full instructions — generated from the codebase, compared by test, prompted by hook. Admitted outside §16's Phase-1 boundary deliberately: an organisation cannot govern agents it cannot enumerate. Honest limit: no identity yet, so the page says it is unrestricted rather than implying protection.

- **G-26 (settled):** Personas built at S2.5 rather than deferred (2026-08-21): answers are insert-only, so rows written without an author can never be attributed afterwards. The switcher over seeded people is explicitly a pilot device and says so on screen; production identity (SSO, tenancy) stays out of scope (§12). Pre-S2.5 rows keep a null author — "recorded before attribution existed" beats a fabricated one.

- **G-27 (settled):** The eleven Tier-1 gates and their path questions are transcribed verbatim from the owner's reference instrument (2026-08-21): wording authority is the owner's; changes go through §8.

- **G-28 (settled):** A partial intake submission never disturbs answers outside its own scope (2026-08-21, F1, FR-2): each section submits only its own fields, and the server writes only what the submission names. Found by the owner using the product — the suite only ever filled forms front to back.

- **G-29 (settled):** A persona defines what the platform permits, not what it displays (2026-08-21, F2): every route that reads or writes an assessment decides authority server-side from the session persona in one pure module. Superseded in part by G-33, which extended the same rule to the object.

- **G-30 (settled):** Every answer and every intake change records who made it and what it replaced (2026-08-21, NFR-19): attribution is written at insert, decided by role in one pure module, never in a screen. Intake history is insert-only events; the current record is a projection.

- **G-31 (settled):** A test suite may not write to the environment a person works in (2026-08-21, F11): the E2E suite brings its own database and server via `scripts/prepare-e2e-db.mjs` — which is also the shape of a fresh environment. Honest limit: no CI exists, so "builds from scratch" rests on one laptop until a pipeline does. `pnpm db:reset` is the only way back to clean, since assessments holding answers cannot be deleted.

- **G-32 (settled):** E2E tests assert rendered DOM, never server markup (2026-08-21): a grep over HTML passes while the page is broken for a person. Playwright drives the app a person sees; the suite owns its own database (G-31).

- **G-33 (settled):** A role is what it permits **on the object**, not only in the listing (2026-08-21, N1, blocking): list rule and object rule are one function (`mayOpenAssessment`), a unit test requires them to agree for every role, and a route that skips the access helper fails an architecture test. **A fix aimed at a finding tends to stop at the finding — ask what else relied on what was missing.**

- **G-34 (settled):** Destinations registered (2026-08-21, §27, owner call): the assessment becomes a source downstream systems draw from; first instance the ServiceNow AI Use Case Record. The offer is opt-in, its "N of M already answered" count **computed, never written**; the field map is versioned data marked provisional; the write is out of scope — the payload is real and downloadable, the send labelled not connected, nothing mimicked.

- **G-35 (settled):** Intake asks whether a third party is involved rather than inferring it from a name field (2026-08-21, audit C-2, owner call): positive-evidence routing (§3.2.1) means an empty box proves nothing, so a plain Yes / No / I'm not sure question closes the area outright for in-house work, and the name field reveals on Yes. Distinguished from G-20: this asks a fact about their own project, checkable, not our taxonomy.

- **G-36 (settled):** A risk area that applies to everyone is stated, not asked (2026-08-21, audit C-8, owner call): Governance & Oversight is marked `alwaysApplies`, shown as "Applies · not asked", excluded from the to-do count, and reachable by link with an explanation. Deliberately not a pre-fill — a pre-fill invites correction and this is not the requester's to correct. People & Capacity, Security & Resilience and Ethics & Conduct examined and left alone pending real walks.

- **G-37 (settled):** Required means required, and negative paths are verified by default (2026-08-21, owner found it in use): `required: true` was decoration — nothing enforced it, and nothing wrote it down as a requirement, so no layer of checking could see it. FR-28 makes enforcement a requirement with the refusal server-side; NFR-21 makes the adversarial pass — empty submit, skipped step, URL bypass, stale re-submit — a standing verification step. **What nobody wrote down is invisible to both the suite and the verifier.**

- **G-38 (settled):** Data classification is a single choice on a named four-band scale (2026-08-21, audit C-3, owner call), rendered as the scale it is — four ordered cards, rank by position and pips, never colour alone (§23). The label asks the question ("What's the most sensitive data involved?"). `Public` became expressible and now closes the privacy area; existing rows keep their high-water mark (migration 0010). Deliberately no "I'm not sure" here — the descriptions place almost any case.

- **G-39 (settled):** Nothing a person types is discarded by the framework (2026-08-21): controlled inputs erased keystrokes typed before hydration. The form reads the DOM once on mount and adopts what it finds; every control carries a `name`. **An intermittent failure is a defect until proven otherwise** — "passes on retry" is a description, not a diagnosis.

- **G-39a (settled):** Nothing is pre-selected for a person, anywhere (2026-08-21): a pre-selected answer nobody looked at becomes that person's attributed answer — the failure the platform exists to prevent. Suggestions are dashed, labelled, and unselected; the click is the answer (see G-45, G-49).

- **G-40 (settled):** Derived state is computed, never stored (2026-08-21, S3, NFR-3): paths, settled gates and their dependencies are re-derived from answers on every read, so upstream changes propagate with no migration and no stale rows. A derived path may depend on chosen selections but never on another derived path; a gate may not pre-fill from itself. **Parts-shelf decision #1: rewrite, not salvage** — the prior engine solved a different shape; its test patterns were taken, ~150 lines written here.

- **G-40a (settled):** An operation a person experiences as one act is one transaction (2026-08-21, S3 verification, B1). The paths screen wrote four areas in a loop, so a failure partway committed the first two and then told the person *"nothing was saved"* — false, and the uncommitted ticks vanished on the next load, while the slice's own UAT record claimed "nothing is lost and the person is told". One call, one transaction, all or none; the sentence is now true because the behaviour changed to match it. Two corollaries kept: an answer is saved when it is given, not when a form is submitted, because the primary navigation on that screen used to discard ticks silently (§24.3); and a transport failure carries a per-incident reference, not a class name like `OFFLINE`, because support correlates incidents, not categories.

- **G-41 (settled):** A claim that a rule is enforced must be enforced (2026-08-21, S3, B3): the validator's chaining checks did not catch chains, so an authored rule silently never fired. Chaining is now checked instrument-wide, gate resolution runs to a fixed point, and a deliberate chain is allowed with provenance naming the real source. **When a commit says "enforced by X", the reviewer's first move is to break X.**

- **G-42 (settled):** The product may never state as the person's answer something the person was not asked (2026-08-21, S3 round two, three instances). Mechanical form: **a sentence attributing something to a person must be conditioned on the record of them saying it, not on the absence of a record.** An autosave writes only what was touched; submitting a form writes everything on it; provenance must reach every surface that renders the fact, not just the screen where it was fixed.

- **G-43 (settled):** Anything that must always happen is a hook or a test, and the hook emits the procedure rather than naming it (2026-08-21). The Stop gate blocks on stale artifacts and missing UAT sections; the agent-map parity test compares against §22.1 as an external reference; the advise hook emits the relevant skill's checklist when a governed file is edited. **Mechanism answers "did it happen"; judgement answers "was it any good."**

- **G-44 (settled):** Demo readiness is its own tracked artifact (2026-08-21, owner's question). Build completeness and demo readiness are different things; `demo/readiness.md` holds one row per beat — what the room sees, what delivers it, built or not, **walked by a person or not**, and the fallback if it breaks live — plus what will not be claimed. The Stop gate refuses to finish while `slices-covered` lags the DONE slices. **A beat nobody has used is not ready, however green the tests are.**

- **G-45 (settled):** A rubric anchor is the option, not a label on one (2026-08-21, S4, FR-6): Tier 2 shows the three anchor sentences and the person picks the one that describes their situation — never a bare band word. A derivable band is **offered, never pre-answered** (FR-7); accumulated controls carry every reason that pulled them in; accumulation is computed per render, never stored (NFR-3).

- **G-46 (settled):** Reference lists are versioned data, immutable once activated, and an answer stores the label as displayed when chosen (2026-08-21, FR-29, NFR-22) — renames must never change what a past answer says. One deliberate exception: the people directory is operational, not versioned (an IdP replaces it in production); its rename-safety comes from the stored label alone.

- **G-47 (settled):** Off-list is an answer, not an error (2026-08-21, FR-30/FR-31): every reference-backed field accepts a value not on the list, stored distinguishably; multi-selects offer an explicit "something else" with required free text stored as its own value.

- **G-48 (settled):** An off-list value binds to its assessment immediately and enters the shared list only by admin ratification with actor and timestamp (2026-08-21, FR-32) — propose→ratify (§5.6), one layer down.

- **G-49 (settled):** A value the platform worked out names its source question and keeps saying so after the person accepts it (2026-08-21, owner feedback #10, FR-33). G-39a is not reopened — nothing is pre-selected; what changed is that provenance survives the click instead of vanishing with it. A true default, if still wanted, is its own governance entry.

- **G-50 (settled):** Tier-2 depth is pilot-scoped to four risk areas (2026-08-22, owner call, recorded late). Third-Party, AI & Model Risk, Data & Privacy and Security & Resilience carry all 21 paths, 26 severity questions and 51 control objectives; the other seven areas have a gate and nothing behind it — Yes records scope for a reviewer and asks nothing further. The scope is right; the silence was the defect: an empty area and a deep one read identically. FR-35/S4.8 put the boundary on screen, and the rule stands: **a place where the product deliberately stops must say it is stopping deliberately.**

- **G-51 (settled):** G-3 reopened by owner (2026-08-23): the agentic layer is the product's stated core, not an accelerant. §1 now leads with the official mission text; structured intake remains Phase 1's delivery vehicle and the demo claims only what is built; the Bedrock/AgentCore epic (§6.4 Tiers 2–3, §7, §22.1) is the priority work after the demo. G-6's contract discipline survives unchanged: nothing may be built that the §7 guardrails would forbid.

- **G-52 (settled):** Two named acts, one word each (2026-08-23, owner mission text). The submitter makes a **declaration** at submission — an explicit, recorded statement that their answers are accurate, per key intake question (FR-37, S7). The assessor makes an **attestation** at review (FR-16–FR-18, S8, unchanged). The roles table stands: a requester still cannot attest. The pitch phrase "submitter attestation gateway" is delivered by the declaration; the vocabulary is kept distinct so four-eyes stays meaningful.

- **G-53 (settled):** The persistence engine is Postgres on RDS (2026-08-23, closes §14's engine question). Seventeen plain-SQL migrations, schema CHECKs carrying §5 invariants, and PGlite tests replaying real DDL all exist; DynamoDB would relocate the invariants into application code and slow the AWS port the owner requires. pgvector is not provisioned until a phase needs embeddings.

- **G-54 (settled):** Hand-offs legalized retroactively (2026-08-23). The "leave this to us" feature — flag, tag a person or risk domain, threaded conversation, derived obligation in the bell — was built at db6aa04 citing FR-36 and S4.7, neither of which existed in this document. The feature is right; building it untraceable violated the header's own rule. FR-36 and S4.7 now exist, and the lesson is mechanical: code may only cite requirement IDs this document defines (checked by `test/unit/spec-register.test.ts`).

- **G-69 (settled):** The intake quality assistant ships, and **it fails open** (2026-08-24, §22.1). The first screen is where friction is cheapest to remove and most expensive to leave: a thin description means every downstream question is asked cold. Three layers, and only one is a model. The **floor** is heuristic and local — it catches a product name, a fragment or keyboard noise with no model call and costs nothing. **Scoring** is the model's entire job: 0, 1 or 2 per dimension against published anchors, strictly on the presence of factual detail and never on length. **Everything after** — the pass rule, and the exact sentence a person reads for that dimension at that score — is deterministic and lives in `src/data/reference/intake-rubric.json`, so the feedback is business copy edited in one place and never composed in code. **The rubric is visible to the requester**: alongside each ask is the anchor it was scored against, so the grade is never a black box. The rule that outranks all of it: **no agent, a slow agent, a wrong agent, a partial answer or a thrown error all pass.** A quality assistant that blocks submission has become a gate, and the mission is reducing friction — the suggestions sit beside the box, never in front of the button, and a person who wants to write two lines and move on can. A score outside the rubric is **dropped rather than clamped**, because clamping turns nonsense into a number somebody then acts on. Verified against a local model: "Salesforce" caught by the floor with no call; a real but thin description scored on purpose and asked for the data, the parties and the hosting; and the Next control stayed enabled throughout.

- **G-68 (settled):** The handoff report is the artifact a Risk Assessor is given, and **a report is a reading of the record, never a new fact** (2026-08-24, §4.4, §4.5). Every figure on it — what applies and why, the severity profile, each control with its answer and the clause requiring it, every finding with the clause it breaches, and what nobody answered — is derived when the page opens and stored nowhere. That is what lets it be shown to a leadership audience without a caveat. The agent adds exactly two things on top, and **the page is complete without either**: a summary of at most three sentences, and two to four **risk scenarios worth asking about**. A scenario is a question, never a finding — §4.4 says a scenario counts only once an assessor accepts it, and the type carries no field that could record acceptance. Every scenario must cite the controls or areas it was read from, **by the names that appear in the record**, and one citing anything else is dropped entirely rather than shown with a caveat: it is not a weaker scenario, it is one built on nothing. The summary passes the same contextual guardrail as everything else said to a person (G-65) plus a length gate, because three sentences is the brief and four is somebody not reading it. Verified against a local model on the seeded assessment: three scenarios, each one specific to that activity — a shared VPN account with no gateway, admin accounts not vaulted, access never recertified — and each citing the control it came from.

- **G-67 (settled):** Policies are in the product, and **a breach is a finding** (2026-08-23, §22.1 compliance checking). Five enterprise policies with seventeen clauses live in `src/data/reference/policies.json`; each clause carries its own words and names the control questions it bears on. Three decisions shape it. **The alignment is authored data ratified by a human, never something a model decides while a page renders** — a requester asking "why am I being asked this?" is owed an authority, and an authority a model invented is not one; the agent's job here is to *propose* alignments and to read prose a table cannot express. **The deterministic pass stands alone**: with no model available, a structured answer breaching a structured requirement is still caught, which is the guardrail §22.1 puts on this feature. **A breach is not a new concept** — it is a third finding kind resolved through the same four dispositions, which is exactly the taxonomy the prior platform reached the hard way, having first called it a "conflict" and given it its own free-text resolution before renaming it (G-59). Where a policy governs a question, the breach **replaces** the bare gap rather than joining it: one fact, one finding, and the richer of the two. Two CHECKs keep it honest (migration 0024) — the citation is present exactly when the kind is a non-compliance, so a gap cannot claim an authority it does not have and a breach cannot hide the clause it breaches. Narrow about what counts: an **unanswered** question is never a breach, because silence becoming non-compliance is the mirror image of the mistake never-guess exists to stop; and an **N-A** is never a breach, because judging a control out of scope is a position a person took and testing it is the reviewer's job, not the platform's to pre-empt. **Clauses the pilot asks nothing about are named rather than dropped** — an obligation with no question is a coverage gap in the instrument, which is §22.1 read backwards and the more useful direction. Found while seeding: a finding on a control this assessment never accumulated is invisible in the reviewer's queue, so seeded data must answer only what the product would actually ask.

- **G-66 (settled):** A requester can hand the assistant a document and get **proposals**, never answers (2026-08-23, S12). The mechanism is the one the schema already had: `answers` carries `source` and `confirmed`, and already refused an unconfirmed answer from a person. A drafted answer is a third source — **an unconfirmed answer that carries the passage it came from** — rather than a second mechanism, so the ledger, the summary and the export keep working with no new concept. Four CHECKs make it true whatever calls it (migration 0023): a draft can never arrive confirmed, it cannot exist without a quote and a source, its basis must be `stated` or `inferred` because an abstention has nothing to record, and evidence may not ride on a person's own answer — which is grounded in the fact that they gave it. Accepting writes a **new row**, so insert-only leaves the proposal underneath: "the assistant proposed and I accepted" is a history somebody can read rather than a claim they must believe (FR-22). The quote is re-verified against the stored document on the web side even though the agent's gate already checked it — the two are not redundant, because the agent's check protects the wire and this one protects the record, and only one of them is on the side that owns the consequence. **Documents are stored as extracted text and never as files.** §3.6 leaves the attachment retention posture open and it blocks S4.6; text scoped to one assessment is a narrower thing than a binary store, with no download path and nothing in it a person did not already hand over. **The retention decision still gates real documents; the pilot is synthetic.** Verified against a local model: from a vendor overview it proposed three answers and abstained on six, each proposal carrying a verbatim sentence — the never-guess rule holding on questions the document simply did not address.

- **G-65 (settled):** Everything an agent says to a person is checked against **that assessment's record** (2026-08-23, S12). A capability is handed an `AssessmentContext` — the activity in the person's own words, what is on record as label and value, and what is still open — and it is **required, not optional**: the service refuses a request without one rather than proceeding unguarded, because an agent that cannot be told what is on record cannot be caught claiming something that is not. Two checks run over every human-readable output, the conversational reply and a drafted answer's `because` alike. **No internal identifier reaches a person** — the likeliest failure of all, because the model is handed ids in its own instructions and repeating one feels helpful; a requester told "t3.t3_iam_02 is unanswered" has been given our problem instead of an answer (§24.2, NFR-9). **No answer is attributed to somebody who did not give it** (G-42), which catches the specific and plausible failure of a model recapping "you said the data is Confidential" when they said no such thing, and a busy person reading that as confirmation and stopping. Both live in the shared contract as one function that both capabilities call, so a new capability cannot ship with half the checks. **Corrected 2026-08-24 after independent verification: that sentence was written before it was true.** The drafting gate imported the function and never called it — the import passed the type checker because nothing forbids an unused one — so a drafted answer's `because` went unchecked while the specification said otherwise. It is called now and tested. Two further corrections from the same pass: `utteredInternalIdentifier` claimed in its own docstring to catch the `initial.surname` form the pilot directory uses and could not match it, missing `p.requester`, path codes like `TPR_LA`, upper-cased ids and uuids; and `claimsUnrecordedAnswer` compared whole sentences, so **one true clause laundered every false claim beside it** — "You said Yes to AI, and you said the data is Restricted" passed on the strength of "Yes". Both widened, and every string the verifier reported as missed is now a test. **The rule this earns: a guardrail is not shipped when it is written, it is shipped when something proves it fires.** The conversational gate stays deliberately narrower than the drafting gate — holding a thought partner to the verbatim standard would make it impossible — and what it does enforce is the claim that would actually cause harm: that work was recorded, saved, submitted or signed. **General rule recorded: a guardrail is written against a named failure, not against a category.** Each check here names the sentence it exists to stop.

- **G-64 (settled):** The agent service exists and its gate was proved against a real model (2026-08-23, S12). Its own image, its own dependencies, its own typecheck; the web app's tsconfig excludes it, because it lives in this repository to share the wire contract and not because it is part of that build. **Verified, not asserted:** run against the owner's local Ollama (qwen3:14b, which serves `/v1/messages` in the Anthropic shape, so the provider seam is the only thing that differs), it drafted a defensible `Partial` with a verbatim quote and **abstained** on the question the source was silent about, saying what it looked for and did not find. Both outcomes are the never-guess rule working on a model that was never told about this product. Two build-time facts came out of that run rather than out of a document: a reasoning model returns `thinking` blocks before its text, so taking `content[0]` reads the model's private deliberation instead of its answer; and its thinking consumes the token budget, so `max_tokens` must be generous or the reply is empty. **A local model measures the harness and never the quality bar** — its job is to prove the gates reject what they should, and no quality conclusion or baseline may come from an Ollama run. Twelve gate tests use fabricated replies rather than real ones, because a model behaving well proves nothing about what happens when it does not: refused are a paraphrase, a **stitched quote** assembled from two real fragments that never appeared together, a citation to a source never supplied, an abstention still carrying an answer, an inference with nothing to point at, and a draft that does not say why. A refusal produces an error event, never a lower-confidence answer. OpenTelemetry is wired from this service's first day per §6.4 obligation 5, with the locked prompt's hash on every span and on `/healthz`, so a change in behaviour can be told apart from a change in the prompt.

- **G-63 (settled):** Parts-shelf decision #5, taken at S11 (2026-08-23, G-8). The prior platform's agent layer was read in full before the contract hardened, because a wire contract is a deployment boundary and changing one later is a compatibility event. **Taken now:** the three-value **basis** vocabulary — `stated` / `inferred` / `not_stated` — which is a better shape than a quote alone, because it makes abstention a first-class outcome rather than a failure, and it separates "the source says so" from "this follows in one step". An inference still carries a quote; an inference with nothing to point at is a guess, and the rule now says so in the sentence a person reads. Also `violatesNeverGuess` as a pure function beside the gate and the constraints — the prior platform enforced this three times over, which is the right number, since each catches what the others cannot. **Taken at S12, recorded here so it is not lost:** the provider seam (`AGENT_PROVIDER` selecting the Anthropic API or Bedrock through `@anthropic-ai/bedrock-sdk`, credentials resolving through the AWS chain so a task role needs no keys in the environment); the one whitespace-normalised verbatim matcher shared by the gate, the eval scorer and the source highlighter — **never a second matcher**; OpenTelemetry spans as the actual record of a run, with the trace id joinable to the row; and the eval design in which a `not_stated` ground truth passes **only** on abstention, with a false N/A failing its whole module because an accepted false N/A is a waived control question. **Declined:** the polling that stood in for streaming, the fifteen capabilities built at once, and — again — the Tailwind (G-61). The order stays one capability end to end with its eval before the next.

- **G-62 (settled):** The compute target is **ECS Express Mode**, and the deployment is a written, followable path rather than an intention (2026-08-23). AWS closed App Runner to new customers on 30 April 2026 and names Express Mode as its successor: one command produces a Fargate service, an Application Load Balancer, TLS, autoscaling and a public URL, which is the same simplicity §6.4 Tier 1 was written around. The owner caught this — the plan of record named a service his account can no longer create. **Recorded because the correction generalises: a deployment target named in a specification is a claim about the world, and the world moves.** Built with it: `deploy/infra.yaml` (registry, Postgres, security group, the two IAM roles Express Mode requires), `deploy/README.md` (the CloudShell runbook, each step saying what it should print), `deploy/codebuild.md` (the fallback for CloudShell's disk limit) and `deploy/architecture.md` (what runs now, what changes at Phase 2). Four defects in the container were found by reading it against a first deploy rather than by running one: no `.dockerignore`, so `.env` would have shipped inside the image; no `packageManager`, so corepack could pick a pnpm the lockfile was not written by; no `HOSTNAME=0.0.0.0`, so the standalone server would have bound to localhost and never answered the load balancer; and no health endpoint that avoids the database — `/` reads the people directory, so an unreachable Postgres would have failed the health check and read as a crash loop instead of a missing network rule. `/healthz` and `/readyz` now separate "the process is up" from "the database is reachable", and the second scrubs credentials out of the driver error because it is unauthenticated by design. **Not verified: no image has been built and no stack deployed — there is no Docker on the build machine and no credentials for the sandbox account.** The production artifact itself was run and both endpoints were checked against a deliberately unreachable database.

- **G-61 (settled):** Parts-shelf decision #4, taken at S8 (2026-08-23, G-8). The prior platform scored every drafted answer for "confidence" and showed it to the reviewer. **Taken:** the idea that a reviewer's queue should be ordered by something, and the shape of the strip that shows it — bars, a count, a word, and the checks themselves readable underneath. **Refused:** the thing it measured. A model's confidence in its own output is not evidence about the answer, and a number a reviewer cannot check is a number that quietly replaces their judgement. What ships is a **rubric over what is on record**: was a non-Yes explained, has the answer changed more than twice, was a Yes left with its detail questions unanswered, was it handed to somebody else, was it drafted with evidence. Every criterion is a fact the reviewer can verify on the same screen, and each is stated in words next to its verdict. **The band orders the queue and does nothing else** — it cannot gate, skip or pre-approve an attestation, and the strip says so in the first line a person reads. This is the shape the drafting layer's output will be judged by when it arrives (§7): the same rubric, with the drafted-with-evidence criterion no longer always null. Recorded as FR-38 because a hundred and seventy lines of logic and a badge on the reviewer's screen cannot be owned by nothing (Build Rule 5).

- **G-60 (settled):** Attestation happens at Tier 3, against control objectives, and authority follows a **control family → risk domain** map (2026-08-23, owner call). The question a reviewer signs is a control question; the risk area accountable for it is derived from the family that control belongs to, and the derivation carries a `because` sentence shown on the refusal screen — a person told "not yours" is owed the reason. The map lives in `src/data/reference/control-domains.json` and is validated on import: an unmapped family fails the build rather than falling through to "anyone may sign". A generalist assessor (no risk area) covers everything, so a question can never sit in a queue nobody reads. **Amended the same day, after independent verification:** authority must be derived from the question being signed, never from an objective supplied by the caller. The first implementation checked the caller's authority against a field in the caller's own request, which let a Data-Privacy assessor sign a Security control by naming a Privacy one — the check ran, passed, and protected nothing. **General rule recorded: a permission check reading a value the requester chose is not a permission check.** The same defect existed in the disposition path and is fixed the same way; both now resolve the objective from the question id server-side.

- **G-59 (settled):** Parts-shelf decision #3, taken at S7 (2026-08-23, G-8). The prior platform's submission and findings work was read at the moment this slice needed it. **Taken now:** its `projects_submission_complete` check — a submission timestamp and a submitter are one fact, and neither may exist without the other; without it a stamp with nobody's name on it is representable, which §4.1 forbids in words and now forbids in the schema (migration 0019). **Taken at S8, recorded here so it is not lost:** its four disposition constraints, which express §4.3 as CHECKs rather than application code — a disposition present exactly when a resolution is; remediation requiring an owner and a due date; and, the strongest of them, **risk acceptance enforcing four-eyes in the schema** (`accepted_by <> resolved_by`), so a person accepting their own risk is refused by the database and not by a rule someone can forget. Also its `openPolicyFinding()` predicate — open means unresolved OR accepted-but-expired, in one place — which is exactly the "one rule decides open everywhere" §4.3 asks for. **Declined:** the table itself and its taxonomy. Its findings arise from policy conflicts detected against documents; ours arise from Tier-3 answers a person gave, carrying the note they wrote. Same word, different evidence, and copying the shape would have imported a model this instrument does not have.

- **G-58 (settled):** Next.js is pinned to the 15.3 line because 15.5 breaks client-side navigation in production builds (2026-08-23). On 15.5.23 a click between assessment screens completed 3 times in 15; the browser aborted the router's RSC request while the server returned a valid 200 payload, React hydrated, and full page loads worked. It was not `output: standalone`, not prefetching, and not a shared `.next` directory — each was removed and retested. On 15.3.9, 15 of 15, twice, plus the whole demo walk end to end with no page errors. **The lesson is the one this project keeps relearning: the configuration nobody has run is the one that is broken.** The production build had never been executed once — it was named in a run sheet as an instruction to a presenter, which is a claim the product makes (G-56), and it was false. `pnpm verify:prod` now builds and walks it, so the demo's own delivery mode is exercised rather than assumed. A version bump is a governance event: the pin is deliberate and moving off it requires re-running that check.

- **G-57 (settled):** S5 closed, and one of its acceptance criteria was wrong rather than unmet (2026-08-23). §19 required that "a capture-marked answer never changes the accumulated set" — which contradicts FR-10 and §3.3, both of which say option selections may require objectives directly. The rule §3.1.6 actually draws is narrower and correct: a capture (detail) answer never affects accumulation **thresholds**. It changes no severity band, so it moves nothing that `requires.atLeast` reads; it may still add objectives of its own, each carrying the option that pulled it in. The criterion now states that, and a test asserts it across every detail question in the instrument. FR-11's ledger was genuinely incomplete: it named active paths, severities and accumulated objectives, and the panel showed only the third — so a person saw the consequence without the reasoning. All three now render, recomputed on every answer and never stored (NFR-3); this screen's severities come from live state rather than the last page load, because "live" is the requirement. General rule recorded: **when an acceptance criterion cannot be met, check whether it is the criterion that is wrong** — writing a test for a rule the specification does not actually draw would have encoded a contradiction.

- **G-56 (settled):** A builder's record of their own work is not evidence (2026-08-23, independent verification of S4.7 and S4.8, both FAIL). Two rows of `uat/S4.7.md` carried evidence never observed — a quoted screen string that exists nowhere in the product, and a citation to E2E coverage that does not exist — and those records had been offered *in place of* a verifier pass. The verifier then found three blocking defects the builder's own walk had passed: the bell's obligation was not derived at all (it read a stored `resolved_at`, while the screen promised it clears itself), `replyToHandoff` authorised the caller's project id and wrote with the caller's hand-off id without requiring the two to match, and S4.8's declaration was unreachable in the forward journey because answering navigated away from it. All fixed and re-verified. Three rules follow. **The verifier is not optional and is not satisfied by the builder walking their own work** — the Stop gate already refuses a DONE slice whose record lacks a verdict; that section may now record FAIL, never a builder's substitute. **A test that greps for an identifier is not a behaviour test** and may not be described as one in a UAT row; `declared-boundaries.test.ts` passed throughout while the feature was invisible. **Checking a screen in the state you put it in is not walking the journey** — the defect lived in the transition, so sampling after the click found nothing.

- **G-55 (settled):** The Claude Code operating layer is consolidated (2026-08-23, this level set): fourteen skills become nine, one gate-chain definition lives in `verify` and everything else cites it, the PreToolUse guard §15 promised is built, and §15 now describes only what exists. **Amended the same day:** both write-time hooks matched `Edit|Write|MultiEdit` only, so the session that rewrote this document — editing through Bash heredocs — fired neither hook once, across the SPEC rewrite, the skill merges and a whole slice. They now watch Bash and read the paths a command writes, and the Stop gate additionally compares the governance log against the last commit, because a guard whose coverage depends on which tool the work happens to use is not a guard. The four subagents named from the prior platform (contract-guard, coherence-auditor, provenance-auditor, ontology-auditor) are removed from §15 — they audit artifacts this repository does not have.

## 14. Open questions (decisions owed, not forgotten)

1. **Composite scoring** — does a composite grade exist at all, and if so where may it appear? (Inherited; owner decision.)
2. **Tier-3 audience** — requester-completes vs. control-SME persona; affects reviewer groups only, not structure. G-50's pilot depth (four areas) narrows who the SMEs would be.
3. **History posture at handoff** — keep full git history or squash to a clean initial commit.
4. **Attachment retention posture (§3.6)** — how long uploaded bytes live, who may purge, what an export carries. Owner decision; blocks S4.6. **Narrowed 2026-08-23 (G-66):** the pilot reads documents and keeps only the **extracted text**, scoped to one assessment, with no binary store and no download path — so document-assisted drafting ships without waiting on this. The decision still gates keeping **originals**, which is what an S3 bucket would hold; `src/lib/documents.ts` is the single module that would grow one.
5. ~~**The Bedrock model-access request**~~ — **closed 2026-08-23: the owner already has Bedrock access in the sandbox account.** The plan's only uncontrollable-latency dependency is gone, which is why the Phase-2 epic starts now rather than after the remaining Phase-1 slices.

*Closed since first written:* re-ask policy (settled by §24.1/§24.6/FR-22 for the deterministic flow; the agentic variant belongs to the Phase-2 epic); help text per audience (single teaching string is the standard, §24.11/G-23 — per-audience variants are a data-model addition proposed when a reviewer asks for one); persistence engine (Postgres on RDS, G-53).

## 15. Claude Code operating layer

This repository is operated with Claude Code as a first-class tool; the layer is versioned in the repo, not tribal — and this section describes **what exists**, because a §15 that promised gates nobody built is how the layer went two-thirds unenforced until the 2026-08-23 audit (G-55).

- **CLAUDE.md** — the working contract, thin: slice status, commands, the skills routing table, and the gotchas that cost real time. `test/unit/docs.test.ts` holds it to router size and keeps the routing table and the skills directory in two-way sync.
- **Hooks** (wired in `.claude/settings.json`, scripts in `scripts/hooks/`, wiring asserted by `test/unit/hooks-wired.test.ts`):
  - *guard* (PreToolUse) — refuses, before the edit lands: writes to applied migrations, environment files, and deletion of a settled governance entry. It reads the paths a call writes whether they arrive as a file path or inside a Bash command (heredoc, `sed -i`, a Python one-liner), because matching only the file-path tools let a whole slice through without a single hook firing.
  - *advise* (PostToolUse) — emits the governing skill's own checklist the instant a governed file is edited, including the instrument data under `src/data/`.
  - *stop-gate* (Stop) — refuses to conclude on: red typecheck/unit tests, stale generated artifacts, a governance entry that has vanished since the last commit (the backstop no tool choice can walk around), a DONE slice without its `uat/` record (required sections with substance, including the verifier's verdict for records from 2026-08-23), `demo/readiness.md` lagging the DONE slices, or a stated measurement that cites no existing test.
- **Skills** (`.claude/skills/`, nine): `verify` (the ONLY definition of the gate chain), `instrument` (question → set → governed path), `ui-craft` (build → walk as a person → destinations), `error-handling`, `aws-ready`, `agentic-design`, `owner-brief` (governs the format of every message to the owner), `design-mock`, `demo-truth` (a claim the product makes must be computed, or it is a hope).
- **Subagents** (`.claude/agents/`): **slice-verifier**, the only one. It is not optional: every slice is independently verified before its review — the `verify` chain, requirement-by-requirement UAT through the running app, regression over every prior slice's journey, negative cases, the §23/§24 audits, an invariant spot-check, and a scope check. It reports, never edits. A FAIL blocks the slice; the Stop gate refuses a DONE slice whose record lacks the verifier's verdict.
- **Known holes, named rather than implied:** the §8 coherence gate exists as checks inside `src/lib/instrument.ts`/`severity.ts` validators, not as a standalone `pnpm` command; nothing mechanically triggers the slice-verifier itself (the record requirement is the backstop); integration and E2E tiers are outside the Stop gate (they need a server) and are owed via `verify` before any commit.

## 16. Phase boundaries — what "build this" means

**Phase 1 (authorized — the demo-ready deterministic platform):**

Build a functioning assessment using **static seed instrument data**: structured intake with conditional fields; Tier-1 routing (gates → paths, union with provenance); Tier-2 severity (rubric-anchored + derived) with conditionals; Tier-3 control accumulation and self-assessment; full recomputation semantics (§3.2.7); the requester flow with the live ledger; the submitter declaration (G-52); reviewer attestation with the keyboard loop; findings synthesis and the four dispositions; packaging/export. Phase 1 is delivered as the §17 slices, which collectively own every FR/NFR in §20; acceptance = the full journey end to end with the gate chain green and both UAT rounds signed off.

The instrument's pilot depth is four risk areas of eleven (G-50); the demo profile is the real instrument, not a cut-down one — 11 gates, 21 paths, 26 severity questions, 51 control objectives.

**Phase 1 explicitly excludes:** model calls of any kind, AgentCore, AWS deployment execution, risk scenarios, framework mappings, runtime instrument authoring, pre-deploy verification, scoring display, and independent-auditor automation. Exclusions are binding per Build Rule 5; the list may shrink by owner decision, and any growth is recorded here, not slipped in — admitted to date: the generated agent inventory (FR-24, G-25) and the governance-inserted slices S3.5, S4.5–S4.8 (G-34, G-46–G-50, G-54).

**Phase 2 (planned, priority after the demo — G-51): the agentic epic on Bedrock + AgentCore.** First artifact is the three seams (§6.1) in code; then drafting with verbatim citations, conversational intake, receipts, eval activation, and OpenTelemetry from the agent service's first day (§6.4). Nothing in it may violate the §7 guardrails.

**Phase 3 (planned):** destination write-back (§27), production identity/SSO, pre-deploy verification, scenarios, crosswalks anchored to control objectives. Each phase begins with its own acceptance criteria added to this document.

## 17. Delivery plan — the slices

Phase 1 is delivered as **vertical slices, built strictly in order** (sixteen rows below; the decimal slices were inserted by governance events after the original ten). Each slice ends demoable and reviewable; **do not start a slice until the previous slice's done-when holds and its owned requirements (§20) pass** (Build Rule 3). Execution route per G-8: fresh repository; the prior repository is the **parts shelf** — salvage per-slice, never in advance.

| # | Slice | Status | Builds | Owns | Done when |
|---|---|---|---|---|---|
| **S1** | Intake | DONE | The four intake sections with conditional fields; project list. | FR-1, FR-2, FR-23, FR-28 · NFR-5, NFR-6, NFR-7, NFR-9 | Create a project, complete intake, close the browser, reopen: everything is there. |
| **S2** | Gates | DONE | Schema for instrument + answers with §5 CHECKs; the 11 category gates; instrument as seed data from day one; the generated agent inventory (FR-24). | FR-3, FR-22, FR-24 · NFR-1, NFR-8, NFR-11 | Gate answers persist; No closes its category; migration tests green. |
| **S2.5** | People | DONE | Role model enforced server-side; persona switcher; attribution on every answer. | FR-25 · NFR-19 | Switching persona changes what the platform permits, not only what it shows; every answer records who gave it. |
| **S3** | Paths & engine | DONE 2026-08-21 | Condition engine + one visibility predicate + recompute; Tier-1 path selection with reasons. Parts-shelf decision #1: declined (G-40). | FR-4, FR-5, FR-9 · NFR-2, NFR-3, NFR-4 | §19 engine + routing criteria pass; changing an upstream answer re-derives everything. |
| **S3.5** | Destinations · AI Use Case Record | SPEC'd, not built | The ServiceNow AI Use Case Record assembled from answers already given, field by field with provenance and gaps; payload downloadable; **the write is deliberately not built**. | FR-26, FR-27 · NFR-20 | "Yes" to AI offers registration with a real count of fields already answered; nothing claims to have been sent. |
| **S4** | Tier 2 | DONE 2026-08-21 | Severity questions with rubric anchors as options; derived severities; all four conditional kinds. | FR-6, FR-7, FR-8 · NFR-10 | §19 criteria; a Medium/High answer reveals its conditionals; a derived band routes. |
| **S4.5** | Reference data & unlisted answers | PARTIAL — searchable picker and provenance-on-accept remain | Versioned reference lists; pickers; off-list answers; the derived fourth-party path; the sign-in picker. | FR-29, FR-30, FR-31, FR-32, FR-33 · NFR-22 | List and off-list both work; a typed value appears in no other assessment until ratified; renames never change past answers; accepting a worked-out value leaves its source on screen. |
| **S4.6** | Attachments | Blocked on §3.6 | Upload, stored outside the app filesystem, classified, retained under a stated policy. | FR-34 | A document uploads, is retrievable, carries a classification, and the retention rule is written first. |
| **S4.7** | Hand-offs | DONE 2026-08-22 (legalized G-54) | "Leave this to us": flag → tag a person or risk domain → threaded conversation → derived obligation in the bell, cleared only by the answer. | FR-36 | Flag as one persona, see the pinned obligation as the recipient, land on the exact question, watch resolve refused while unanswered. |
| **S4.8** | Declared boundaries | not started | The seven pilot-scoped risk areas say on screen that they stop deliberately (G-50); the summary separates areas that produce work from areas recorded for a reviewer. | FR-35 | Yes to Ethics & Conduct says, in its own words, that nothing further is asked and why; an undeclared dead end fails a test. |
| **S5** | Ledger | DONE 2026-08-23 | Control accumulation compiled to engine conditions; live ledger with reasons. | FR-10, FR-11 | §19 accumulation criteria; ledger updates on every answer with no reload. |
| **S6** | Tier 3 | DONE 2026-08-23 · FR-21 partial | Objective self-assessment (Yes/Partial/No/N-A, required notes); children on Yes; notes attachable anywhere. | FR-12, FR-13, FR-21 | §19 criteria; suppressed children invisible; N-A without justification impossible. |
| **S7** | Submit, declaration & findings | DONE 2026-08-23 | Submission with named-gaps confirmation; the submitter declaration gateway (G-52); findings synthesis. | FR-14, FR-15, FR-37 | Submit requires the declaration and produces exactly the findings the T3 answers imply. |
| **S8** | Review & attest | DONE | Reviewer queue, attest/correct/N-A with keyboard loop, server-side authority, four dispositions with four-eyes + expiry reopen. Parts-shelf decision #2. | FR-16, FR-17, FR-18 · NFR-10 | §19 attestation + findings criteria; forged client attestation fails. |
| **S9** | Package & export | not started | Packaging gates; insert-only replayable export with explicit N-A strings. | FR-19, FR-20 | §19 packaging criteria; full-journey E2E green. |
| **S11** | Phase 2 · the seams | DONE | The three §6.1 seams in code: agent transport (`none`/`local`/`agentcore`), conversation state shaped for AgentCore Memory, and the wire contract. Nothing reachable from the product UI (§7). Deployment path and architecture written (G-62). | §6.1, §6.4 | Seams asserted by tests; no model SDK under src/; the default transport refuses in plain words. |
| **S12** | Phase 2 · the agent service and its capabilities | DONE | Its own image and Express Mode service; model access behind Bedrock; OpenTelemetry from its first day. Five capabilities: drafting from documents, the assessment companion, policy authority and breach findings, the handoff report, and intake scoring. | FR-39, FR-40, FR-41, FR-42, FR-43 · §7, §22.1 | Verbatim quotes verified against source; abstention scored correct; every capability absent or failing open with no agent. |
| **S10** | Harden & hand off | not started | Both UAT rounds; perf budgets; dead-code gate on; HANDOFF.md; generated instrument reference. | NFR-4, NFR-6, NFR-7 (final) | Owner sign-off = Phase-1 acceptance (§16). |

A timing slip cuts between slices, never through one. **Every slice is bracketed by the review protocol (§21): a pre-flight before it starts and a slice review when its done-when holds. A slice whose review is still open is not done, and the next slice does not begin.**

## 18. Now / design-now / later — the sophistication triage

The product vision includes machinery that must **not** inflate Phase 1's surface. Every sophisticated element is triaged; the implementer honors this table over any enthusiasm elsewhere in the document.

| Element | Triage | Phase-1 obligation |
|---|---|---|
| Never-guess, insert-only records, one predicate/matcher, four-eyes, N-A-with-reason | **MUST EXIST NOW** | Schema CHECKs + tests from S2. These are cheap at birth and ruinous to retrofit. |
| Recompute-don't-remember routing | **MUST EXIST NOW** | Engine semantics from S3. |
| Instrument-as-data + coherence gate | **MUST EXIST NOW** | S2 (instrument as seed data) and the coherence gate (§8). |
| The two seams (agent, session) + model-access confinement | **MUST BE DESIGNED NOW** | Interfaces exist and are the only path (the Phase-2 agentic epic, §7/G-51); nothing behind them is built. |
| Agentic contract (§7) | **MUST BE DESIGNED NOW** | The contract constrains today's design (e.g., option labels quotable); no drafting, chat, or eval activation. |
| Pre-deploy verification | **MUST BE DESIGNED NOW** | A stage field on questions; no verification flow. |
| Parity/differential harness | **NOW iff transcribing** from the reference design (it is the transcription's safety net); otherwise LATER. |
| Property-based testing beyond the harness | **BUILD LATER** | Unit + differential coverage suffices for Phase 1. |
| Constraint-relaxation deny-list | **BUILD LATER** | Meaningful only when prompt text exists (Phase 2). |
| Independent auditor automation | **BUILD LATER** | Subagent definitions may exist (§15); scheduled audit runs are Phase-2 discipline. |
| AWS readiness (§6.4's five obligations) | **MUST EXIST NOW** | Containers, env-only config, RDS-compatible persistence, dependency rule, OTel — enforced in review from S1. |
| AWS cloud execution + AgentCore substrate | **BUILD LATER** | The target is settled (G-7); the migration itself is Phase-3 work. No cloud infrastructure in Phase 1. |
| Scoring machinery | **BUILD LATER** | Open question §14.1; nothing computed or displayed in Phase 1. |

## 19. Subsystem acceptance criteria

Executable acceptance per major subsystem — each becomes a named test before its layer is called done.

**Condition engine (S3)**
- Given an unanswered question, `equals` returns false; so do `not_equals` and `excludes` (positive evidence only).
- Given unknown severity, `severity_at_least(Medium)` returns false.
- A scalar answer `"high"` satisfies `any_of ["medium","high"]` (set membership).
- Any condition renders to exactly one English sentence naming question text and human option labels, never identifiers.
- A condition requiring `includes X` and `excludes X` is flagged by the contradiction lint.

**Routing / visibility (S3)**
- Given two satisfied activation rules for one path, the path is active with **both** reasons retained.
- Gate = No hides every question in the category regardless of other answers.
- Changing an upstream answer removes downstream activation and visibility **without deleting historical answers**.
- Queue counts, wizard progress, and the packaging gate all agree with the predicate on the same project state.

**Control accumulation (S5)**
- A severity of Medium accumulates objectives with `min: Low` and `min: Medium`, not `min: High`.
- A capture (detail) answer never changes a severity band, and so never changes which thresholds fire (§3.1.6). It may still add objectives directly through its own option-adds (§3.3) — that is accumulation, not scoring.
- Every accumulated objective carries at least one human-readable reason.

**Attestation (S8)**
- Attesting requires reviewer-group membership for the question's domain, enforced server-side (a forged client request fails).
- An attested answer cannot be N-A'd; it can only be corrected-and-re-attested.
- Attesting a shared answer records the confirmed reach.

**Findings (S7/S8)**
- Submitting with a Tier-3 "No" creates exactly one control-gap finding carrying the objective's note.
- Risk acceptance by the resolver themselves is rejected (four-eyes).
- An acceptance past its expiry reopens the finding and re-blocks packaging.

**Packaging / export (S9)**
- Packaging with any visible unattested question fails, naming questions by text.
- The export contains an explicit "N-A — reason" string for every N-A attestation, never a blank.
- Re-export creates a new record; the prior export is byte-identical after.

## 20. Requirements register

The register and the slices are **synced by construction**: every Phase-1 requirement names its owning slice; a requirement whose owner is "every slice" is a standing rule verified at every slice review, not owned by one. `test/unit/spec-register.test.ts` parses this section against §17 and fails on drift. Phase-2/3 requirements are added when their phase is authorized — never before.

### 20.1 Functional requirements (Phase 1)

| ID | Requirement | Detail | Slice |
|---|---|---|---|
| FR-1 | Structured intake in four ordered sections with conditional fields (hasValue · equalsAny · includesAny) | §3.1 | S1 |
| FR-2 | Projects persist and resume; intake is the project's identity record, and a partial submission never disturbs an answer outside its own scope | §3.1, G-28 | S1 |
| FR-3 | One gate per category; No closes the category entirely | §3.1 | S2 |
| FR-4 | Tier-1 selections activate paths; union semantics with reasons retained | §3.2.4 | S3 |
| FR-5 | Any visible question can explain itself in one English sentence | §6.3 | S3 |
| FR-6 | Tier-2 severity presents Low/Medium/High rubric anchors as the answer options | §3.1 | S4 |
| FR-7 | Severity derivable from fact answers via declared mappings | §3.2.5 | S4 |
| FR-8 | Conditionals: severity-fired, always-fired, cross-tier, nested | §3.1 | S4 |
| FR-9 | Answer changes re-derive all routing; history never deleted | §3.2.7 | S3 |
| FR-10 | Control objectives accumulate from thresholds and option-adds, with reasons | §3.3 | S5 |
| FR-11 | Live ledger: active paths, severities, accumulated objectives, always visible | §23 | S5 |
| FR-12 | Tier-3 self-assessment: Yes/Partial/No/N-A; notes required on Partial/No/N-A | §3.4 | S6 |
| FR-13 | Child questions fire only on parent Yes, subject to cross-tier conditions | §3.4 | S6 |
| FR-14 | Submission allowed with gaps only via explicit, named-gaps confirmation | §4.1 | S7 |
| FR-15 | Findings synthesized at submit: No → control gap; Partial → enhancement | §4.3 | S7 |
| FR-16 | Reviewer queue + attestation: approve / correct-and-re-attest / N-A-with-reason | §4.2 | S8 |
| FR-17 | Attestation authority enforced server-side by domain reviewer-group | §2 | S8 |
| FR-18 | Four finding dispositions; four-eyes acceptance; expiry reopens | §4.3 | S8 |
| FR-19 | Packaging blocked until all visible attested, zero open findings | §4.5 | S9 |
| FR-20 | Insert-only replayable export; N-A exported as explicit reason strings | §4.5 | S9 |
| FR-21 | Notes/questions attachable at any point; travel to the reviewer | §3.4 | S6 |
| FR-22 | An intake answer that duplicates a Tier-1 gate pre-answers that gate — visibly, with its reason, and changeable | §3.1 | S2 |
| FR-23 | Where a requester may genuinely lack visibility, "I'm not sure" is a first-class answer that routes to a reviewer rather than blocking | §3.2.1 | S1 |
| FR-24 | An administration page lists every agent, when it runs, what it can see, and its full instructions — generated from the codebase, never hand-written | §22.3, G-25 | S2 |
| FR-25 | Three roles (requester · Risk Assessor · administrator), each differing in what it *permits* — including which assessments it can see and whether it may start one — enforced server-side, with a persona switcher that demonstrates them | §2, G-29 | S2.5 |
| FR-26 | When intake records AI, the requester is offered registration as an AI Use Case Record, with a real count of how many of its fields the assessment has already answered | §27, G-34 | S3.5 |
| FR-27 | An assembled destination record shows every field with where its value came from, what was derived, and what is still missing; the payload is downloadable; an unbuilt destination write says so plainly and is never mimicked | §27, §24.8, G-34 | S3.5 |
| FR-28 | A field marked required is enforced: the forward control refuses and names what is missing, the answers already given are kept, and the next stage is refused server-side — not only by the form | §3.1, G-37 | S1 (repaired 2026-08-21) |
| FR-29 | A field whose answer is a name held in a real system — a person, a business unit, a vendor — is answered by choosing from a reference list, not typed free-hand | §5, G-46 | S4.5 |
| FR-30 | Every reference-backed field accepts a value that is not on the list; the person is never blocked, and the unlisted value is stored distinguishably from a listed one | §3.2.1, G-47 | S4.5 |
| FR-31 | A multi-select that can be incomplete offers an explicit "something else" option revealing a required free-text field; the text is stored as its own value, never as an option id | §24.10, G-47 | S4.5 |
| FR-32 | A value supplied off-list is recorded against that assessment immediately and enters the shared list only when an admin ratifies it, with actor and timestamp | §5.6, G-48 | S4.5 |
| FR-33 | A value the platform worked out names the question it came from and keeps saying so after the person accepts it | §24.5, G-49 | S4.5 |
| FR-34 | Prior assessments and supporting documents attach to an assessment, are stored outside the application filesystem, and carry a classification; the retention posture (§3.6) is written before the first byte is stored | §26.2, §3.6 | S4.6 |
| FR-35 | A risk area that applies but asks nothing further says so where a person sees it — on its gate screen, in the rail, and in the summary — and the summary counts areas that produce work separately from areas recorded for a reviewer | §3.1, G-50 | S4.8 |
| FR-36 | A person who cannot answer a question hands it off — to a named person or a risk domain — with a threaded conversation; the recipient carries a derived obligation that cannot be dismissed and clears only when the question is answered | §24.1, G-54 | S4.7 |
| FR-43 | Intake descriptions are graded against a published rubric whose anchors and feedback are data a requester can read; a heuristic floor runs with no model; the assistant **never blocks submission** — no agent, a slow agent, a wrong agent or a partial answer all pass | §22.1, G-69 | S12 |
| FR-42 | Submission produces a handoff report derived entirely from the record, to which an agent may add a summary and two to four risk scenarios, each citing the answers it was read from and dropped entirely if that citation is not real; the report is complete with no agent | §4.4, §4.5, G-68 | S12 |
| FR-41 | Every control question cites the policy clause requiring it, quoted verbatim with reference and version; an answer breaching a clause raises a **non-compliance** finding carrying both quotes, resolved through the four dispositions; the deterministic pass stands alone with no model | §22.1, G-67 | S12 |
| FR-40 | A requester may hand the assistant a document; it proposes answers that are unconfirmed by construction, each carrying a verbatim quote re-verified against the stored text, and a proposal counts as an answer nowhere until an explicit accept writes one in the owner's name | §7, FR-22, G-66 | S12 |
| FR-39 | An assessment companion a requester can talk to, grounded in that assessment's record; its reply is context and never evidence, it may never claim work was recorded or signed, and it is absent from the product when no agent is connected | §22.1, §7, G-65 | S12 |
| FR-38 | The reviewer's queue is ordered by a mechanical review rubric over what is on record — never a model's confidence — which may order work and may never gate, skip or pre-approve an attestation; the checks behind a band are readable on screen | §4.2, G-61 | S8 |
| FR-37 | Submission requires a declaration: the submitter explicitly attests the accuracy of their answers, per key intake question, recorded with actor and timestamp — distinct from assessor attestation | §4.1, G-52 | S7 |

### 20.2 Non-functional requirements (Phase 1)

| ID | Requirement | Detail | Slice |
|---|---|---|---|
| NFR-1 | Evidence and export records are insert-only (schema CHECKs, not convention) | §5.1 | S2, S9 |
| NFR-2 | One visibility predicate consumed by every surface | §5.4 | S3 onward |
| NFR-3 | Positive evidence only; severity fails closed | §3.2 | S3 |
| NFR-4 | Full-instrument recompute in single-digit milliseconds | §19 | S3, re-proven S10 |
| NFR-5 | AWS-ready by construction: the §6.4 obligations | §6.4, G-7 | S1 onward, review-enforced |
| NFR-6 | File budgets (≤400 new / ≤800 hard) + dead-code gate — measured over stylesheets as well as modules | §11 | Every slice; gate on from S10 |
| NFR-7 | Every slice gated: tests green before advance; E2E on rendered DOM only | §0, §26.4 | Every slice |
| NFR-8 | Instrument entirely as versioned seed data; zero hardcoded content | §6.2 | S2 onward |
| NFR-9 | No internal identifiers in any user-facing text | §23 | S1 onward |
| NFR-10 | State never conveyed by color alone; reviewer flow fully keyboard-operable | §23 | S4, S8 |
| NFR-11 | Instrument versions immutable once activated — neither editable nor deletable; answers pin their version | §5.7 | S2 |
| NFR-12 | Agent/session/model access only through the three seams | §6.1 | Phase-2 epic (G-51); seam tests at its birth |
| NFR-13 | Errors handled to the §25 standard: typed results, no internals on screen, referenced logs, input preserved, error paths tested | §25 | Every slice |
| NFR-14 | Pure logic separated from executors; no framework/driver/env imports in logic modules | §26.1 | Every slice |
| NFR-15 | All persistence behind the store interface; no state in process memory or local files | §26.2 | Every slice |
| NFR-16 | Configuration read only via the config module, validated at the boundary | §26.3 | Every slice |
| NFR-17 | Tests in three separately-runnable tiers, each CI-container-ready | §26.4 | Every slice |
| NFR-18 | Every finished slice carries a committed UAT record meeting the six G-24 criteria | §21, G-24 | Every slice |
| NFR-19 | Every answer **and every intake change** records who made it and what it replaced; authority is decided by role in one pure module, never in a screen | §2, G-30 | S2.5 onward |
| NFR-20 | Destination field maps are versioned data, never code — a new destination is a map file, and a changed field list is a new map version | §27, §5 | S3.5 |
| NFR-21 | Every slice is verified against its negative paths — empty submit, skipped step, URL bypass, stale re-submit — whether or not a requirement names them | §21, G-37 | Every slice |
| NFR-22 | Reference lists are versioned data, immutable once activated; every answer pins the list version and stores the label as displayed when chosen | §5.7, G-46 | S4.5 onward |

## 21. Slice review protocol (the refinement gate)

Every slice is bracketed by two conversations; building without them is a Build-Rule violation (§0.11), not a shortcut. **Procedure: the slice protocol in `/verify`.**

**Pre-flight — before the first line.** The implementer restates the slice's owned requirements in its own words, names the design decisions it intends to make, and lists every ambiguity or assumption it would otherwise resolve silently. The owner confirms, corrects, or defers; unresolved ambiguity blocks the slice (§0.8).

**Slice review — when the done-when holds.** One message containing, at minimum:
1. What changed — files, requirement IDs, tests, gates with real numbers.
2. **Self-critique — at least two items.** "Nothing" is not an acceptable answer.
3. What was deliberately not done, and where it is recorded.
4. Open questions, each with a recommendation.
5. A demoable artifact — never a claim without evidence.
6. The agentic opportunity registered for Phase 2 (§22).
7. UI evidence against §23, and any §24 deferrals.
8. The slice-verifier's report (§15).

Refinements are applied and re-gated **before the next slice starts**; a refinement that changes the instrument or a requirement updates §20 and §13 first.

**Why it exists:** the two failure modes of AI-assisted delivery are an implementer that agrees too readily and an owner reviewing only the finished pile. This forces critical thinking at both ends, at the smallest reviewable unit of work.

## 22. Agentic opportunity planning

Phase 1 builds no agent (§16). It nonetheless **designs** for one, because the cheapest moment to notice that a decision forecloses an agentic feature is while making it.

**The rule:** every slice registers, in its review, what an agent would do for the work that slice just made possible — the job, the evidence it would read, the guardrails it needs, and the human decision it must never take. Registered features enter the Phase-2 backlog (§22.1) and are built only when Phase 2 is authorized. A slice may not ship a design that makes its registered feature impossible (e.g., discarding the raw text an agent would need to read).

**§22.2 The evidence line (binding on every registered feature).** An agent may use world knowledge — technology profiles, regulatory context, research — to *inform the conversation*: to explain, to suggest, to ask a better question. World knowledge may **never become an answer's evidence**. "The internet says Snowflake works this way" is a third-party assertion about a product, not a fact about this implementation. The correct pattern is: the agent proposes using world knowledge, and **the person's confirmation is the evidence** — their words, quotable, attributable. This preserves the provenance chain that the entire platform rests on.

**§22.3 The platform's own AI risk.** Any external enrichment sends project content outside the boundary, and this product asks people to classify that content as Confidential or Restricted. Before any externally-grounded feature ships: a policy for what may leave (recommended default — the technology name, never the description), a classification threshold above which nothing leaves, and the platform's own assessment of the flow. The risk platform passes its own assessment first.

**§22.4 Precedent rules (binding on any feature that learns from other assessments).** Portfolio memory is powerful and has four specific failure modes; each has a rule.

1. **No precedent laundering.** Precedent may be built only from **attested** answers — human-signed, per §4.2. Drafts, pre-fills, and unconfirmed values are invisible to it. Without this, one early mistake copied forward becomes institutional truth, and the platform industrialises an error instead of a control.
2. **Aggregate, never disclose.** Precedent surfaces *patterns* ("11 of 13 comparable assessments answered Yes"), never another team's content, project name, or owner. Below a minimum comparable count, show nothing at all — a "precedent" drawn from one assessment is gossip, not evidence, and it also leaks who.
3. **No anchoring.** A precedent is never pre-selected, never the default, and never phrased as a recommendation the person must argue with. It is context beside a choice they still make. Where anchoring risk is highest — binary gates — prefer showing precedent *after* an answer as a check rather than before it as a prompt.
4. **Age is part of the fact.** Every precedent carries how many, and how recently. A pattern from assessments two years old describes a system that may no longer exist; recency is shown, never silently weighted away.

**§22.5 Policy authority (the one legitimate exception to §22.2).** An organisation's own policies and standards are **not** world knowledge — they are authoritative internal artifacts, and they may legitimately ground *definitions and requirements*. The line moves, but it does not disappear:

- A policy may define **what a term means** and **what is required**. It may **never assert a fact about this project** — only the requester can do that.
- Therefore the chain is always three parts: the **policy** supplies the definition, the **requester** supplies the facts, and the **person's confirmation** is the answer's evidence.
- Policy text is quoted **verbatim or not at all**, with policy, clause, and version named. A paraphrased policy is not a policy.
- Policies are **versioned like the instrument** (§5.7): an answer cites the version in force when it was given, and a later revision never silently rewrites a historical assessment — it raises a finding against the current one instead.

**Standing guardrails for every registered feature:** the §7 may-never list applies at design time, plus one addition unique to this section — any rewrite is **reorganization of the requester's own words**, never addition; content the agent cannot ground in what they wrote is surfaced as a question, not inserted.

### 22.1 Phase-2 feature register

| From | Feature | What it does | Guardrails beyond the standing set |
|---|---|---|---|
| S1 Intake | **Intake quality assistant** | Grades the description against a published rubric (specificity, scope, data handling, dependencies, outcomes); flags contradictions *within* the intake (e.g. "no personal data" versus an employee-PI selection, or a vendor named while the third-party answer says none); offers a rewrite that reorganizes and tightens the requester's own words. | The rubric is data and visible to the requester — no black-box grade. A low grade never blocks submission; it routes to a reviewer with the specifics. Contradictions are *shown*, never auto-resolved. The rewrite is opt-in, diffed against the original, and rejectable; the original text is always retained. |
| S1–S2 | **Assessment companion (conversational)** | An always-available assistant a person can ask anything of while assessing: "based on my description, what do you think?", "what does this question mean?", "can you word this another way?". Proposes gate answers with its reasoning, explains routing, and drafts nothing without a human click. | World knowledge may inform the *conversation*, never the *evidence* (see §22.2). Every proposal is shown with what it was derived from. It never answers a question on the person's behalf — the click is theirs, and the record says so (source `person`). |
| S1–S2 | **Consistency & contradiction chaining** | Continuously reads everything captured so far and surfaces disagreements — across intake prose, gate answers, and later tiers. Two passes: a **deterministic** pass over structured answers (cheap, exact, testable — "no personal data" versus an employee-PI selection) and a **semantic** pass over prose (an LLM catching "the description says customer-facing but the audience answer says internal-only"). | Contradictions are *shown*, never auto-resolved. The deterministic pass must stand alone: if the model is unavailable, consistency checking still works. Every flag names both sides and quotes them. |
| S2 | **Technology profile library** | Named technologies and vendors ("Snowflake", "Databricks", a SaaS product) resolve to ratified profiles — what the technology is, and which risk areas it typically implies. The companion uses profiles to suggest gate answers and explain them. | Profiles are **seeded from research and ratified by a human**, never fetched live per turn: consistency across assessments matters more than freshness, and a reviewer must be able to see the profile that drove a suggestion and when it was ratified. Degrades gracefully — no network, no external dependency at request time. |
| S2+ | **Precedent suggestion (portfolio memory)** | While answering, the person can see how comparable assessments answered the same question — same vendor, same technology, same activity shape — and use that as a starting point. Turns 200 completed assessments from a filing cabinet into institutional memory a first-timer inherits. | Precedent draws **only on attested answers** (§4.2) — never on drafts, never on unattested pre-fills, so an unreviewed mistake cannot become institutional truth. Always aggregate, never verbatim content from another team's assessment. Never pre-selected: precedent is shown as *how others answered*, and the click stays the person's (§22.2). Always carries counts and recency. |
| S2+ | **Application profiles (our own systems)** | A system this organisation has assessed before carries a profile built from its own attested history — what it is, where it runs, what it touches. Reassessing it starts from what we already know rather than from nothing. | Profile facts are attributed to the assessment and attestation that established them, with dates. A profile is a **starting point that must be re-confirmed**, never an inherited answer: systems change, and last year's truth is this year's finding. |
| S2+ | **Divergence signal (reviewer-side)** | When an assessment answers materially differently from comparable ones, the reviewer's queue says so. "Answered No to third-party where 14 of 15 comparable assessments answered Yes." | A divergence is a **triage signal, not a verdict** — being different is often correct, and the platform must never pressure a requester toward the majority. Shown to reviewers, not as a nag to the person answering. Requires the same aggregation floor as precedent. |
| S3 | **Instrument contradiction lint (semantic half)** | Reads the authored instrument as a whole and reports rules that cannot both be satisfied, questions that mean the same thing in different words, and paths no realistic answer set can reach. The *structural* half — unsatisfiable conditions, cycles, chained derivations, unreachable options — is deterministic and belongs in the validator, not here. | Reports to a human as findings; never edits the instrument (§8 — changing what is asked is a governance event). Every finding names the two rules or questions it compares, verbatim, so the reader judges the comparison rather than the verdict. |
| S3 | **Plain-language term help on demand** | Where a question uses a term a business user may not know — "RAG", "privileged access", "fourth party" — the person can ask what it means and get an answer grounded in the organisation's own policy or the cited standard, in context, without leaving the question. | Definitions come from a named, versioned source (§22.5) and are quoted, not paraphrased; a term with no grounded definition says so rather than inventing one. Never rewrites the question itself. |
| S3.5+ | **Destination record drafting** | The agent drafts the inventory narrative from what the requester already wrote — purpose, description, what the AI does — and maps it onto the destination's fields, flagging what the destination requires that the assessment never asked (model provider, training data source, human oversight). | Every drafted field carries the assessment answer it came from, verbatim; a field with no source is left empty and named as missing, never inferred (§22.2). |
| S3.5+ | **Reverse pre-fill from a system of record** | Where a use-case record already exists for this application, the assessment pre-fills from it — the "asked twice" complaint answered from the other end. | Pre-filled values are visibly sourced to the external record with its id and date, unconfirmed until a person accepts them (FR-22), and never silently overwrite an answer a person gave. |
| S3+ | **Policy-grounded definitions** | Where a person must choose against a standard — data classification, criticality, retention — the governing policy's own words appear beside the choice, quoted verbatim with a link to the clause. Turns "Confidential" from a bare word into a decision someone can actually make. | Quotes are **verbatim** or they do not appear. Every quote names its policy, clause, and version. A policy may define a term; it may never assert a fact about this project (§22.5). |
| S3+ | **Policy-grounded suggestions** | The agent proposes an answer citing two things: the clause that defines the standard, and the requester's own words that meet it. "This looks like Confidential — §3.2 defines it as X, and you told us you hold employee wage bands." | The person confirms; their confirmation is the answer's evidence (§22.2). The policy grounds the *definition*, never the *fact*. A suggestion is never pre-selected. |
| S3+ | **Compliance checking** | An attested answer that contradicts a policy requirement raises a finding with both quotes side by side — the requirement and the answer — resolvable only through the four governed dispositions (§4.3). | Findings are raised against **attested** answers, never drafts. The finding cites the policy version in force when the answer was attested; a later policy revision does not retroactively rewrite history. |
| S3+ | **Instrument-to-obligation traceability** | Every question traces to the standard or obligation that requires it — so "why are you asking me this?" is answered with an authority, not only a routing rule. Read the other way it produces two coverage reports: obligations with **no question** (a gap in the instrument) and questions citing **no obligation** (a candidate for deletion). | Traceability edges are **proposed by the agent and ratified by a human** before they are shown as authority. An unratified mapping may inform authoring; it may never be quoted to a requester as the reason they are being asked. |
## 23. UI/UX standard — demo-ready

Every slice ships an interface that could be shown to leadership without apology. **Procedure, patterns, and checks: `/ui-craft`.**

A surface is demo-ready when: (1) colour, type, spacing, radius and motion come from named tokens, never raw values; (2) **every state is designed** — empty, loading, success, failure, disabled, overflow; (3) hierarchy reads at a glance, with one unmistakable primary action; (4) motion is explanatory and honours reduced-motion; (5) it is accessible by construction — accessible name on every control, full keyboard operation, visible focus, sufficient contrast, and state never by colour alone; (6) the words are designed too — plain language, no internal identifiers, help where a business user would hesitate; (7) it is responsive to a laptop viewport, with wide content scrolling in its own container; (8) a screenshot of each surface accompanies the slice review.

**The remaining 10%** is cross-slice work — global navigation, the progress model, final brand treatment — deferred by name in the review, never discovered later. **Taste is the owner's call:** the standard sets the floor, the owner's judgment sets the bar, and direction raised in a review is applied before the next slice starts.

## 24. Experience principles (how the product treats a person)

§23 sets the visual floor; these set the behavioural one. Each was written after a real defect in this build. **The reasoning, origins, and audit procedure: pass 2 of `/ui-craft`.** The mechanically checkable ones are enforced in `test/unit/experience.test.ts`.

1. **Never re-ask what someone just told you they don't know.** Uncertainty is absorbed by the system and routed to a human — never returned as another question. The correct response to "I'm not sure" is a reassurance naming who will find out and confirming nothing is blocked.
2. **One decision per screen; pace the journey.** Prefer stepped, carded progression over long scrolls.
3. **A control responds to the action a person takes.** Choosing from a list, toggling a switch, or picking an option *is* the action — a control that needs a second confirming press reads as broken, and a person will conclude the feature does not work before they find the extra button. Confirmation is for the irreversible, not the routine.
4. **Every wait has a state; every failure has a cause and a next step.** No silent seconds; failure is a designed state, not the absence of one.
5. **Reveal on evidence, and say why.** Conditional content always carries a plain-language reason.
6. **Never make a person repeat themselves.** An answer given once is reused where it applies, shown with its source, and remains changeable (FR-22).
7. **The system absorbs complexity; the person answers in their own words.** If a business user would need a glossary, the question is wrong — not the user.
8. **Show the whole journey honestly, including what isn't built** — future stages read as upcoming, never as broken.
9. **Progress is measured in what's left for the person**, never in internal counts.
10. **Every question tells a person what to do when it doesn't apply to them.** An optional field with no guidance leaves someone staring at an empty box deciding whether blank means "none" or "I forgot" — and the reviewer inherits that ambiguity. Say it: "leave blank if everything is in-house". Enforced in `test/unit/intake.test.ts`.
11. **Every question a person answers carries helper text that teaches**, not text that restates the label. Only a self-evident label may go without. Enforced mechanically.

## 25. Error handling standard

Failure is a designed state (§24.4); this is how it is built. Applies to every action, route, and background job. **Pattern, message-writing guide, and tests: `/error-handling`.**

1. **Expected failures are values, not exceptions** — actions return a typed result the caller must branch on, so a missing `catch` cannot swallow a failure. Unexpected failures are caught at the boundary; transport failure is its own case.
2. **The user gets a sentence; the log gets the truth.** No driver text, SQL, constraint name, or stack trace reaches a screen. The server logs the real error with a short reference, and the same reference is shown so support starts with a fact.
3. **Every user-facing error answers three questions in order** — what happened, is my work safe, what do I do now. "Something went wrong" answers none and is not acceptable.
4. **Retryable is distinguished from permanent**, and the person's input is never lost or cleared to reach a clean state.
5. **Errors are announced, not merely displayed** (live region, no stranded focus), and **every error path has a test** proving the message is safe, the reference present, and the input preserved.

## 26. Cloud-native construction rules (workspace law)

AWS is settled (§6.4, G-7). This section makes it a **construction** rule rather than a deployment plan: every feature, utility, and test is written so it can move to a serverless target without redesign. It binds all code, starting now.

**26.1 Pure logic, separate executors.** Business rules live in modules that import no framework, no database driver, and no environment. The thing that *executes* — a server action, a route handler, later a Lambda handler or AgentCore task — reads the request, calls the pure function, calls the store, and returns. Any pure module must be liftable into a standalone function with no edit to its body. Web-specific shapes (`FormData`, `Request`) are converted at the boundary, never passed inward.

**26.2 State is external; persistence is behind one interface.** No feature state lives in process memory, on the local filesystem, or in a hardcoded path. All reads and writes go through the store interface; no route, action, or component touches the driver. *Honest limit:* this makes a store swap **contained**, not free — a different query model still needs a real implementation. What is guaranteed is that only the store module and its wiring change.

**The engine choice is open and under standing assessment (§14.6).** Postgres is the Phase-1 implementation, not a settled destination. Two obligations follow: (a) no slice may adopt a store-specific feature without flagging it in its review as a constraint on the choice; (b) the implementer reports on the choice at the checkpoints in §14.6 with evidence from the data model as it actually exists, not from preference.

**26.3 Configuration only through the environment, read in one place.** No hardcoded secrets, hosts, or connection strings. Env is read in the config module alone, validated at the boundary, and fails with a message naming both the local fix and the AWS source (Secrets Manager / Parameter Store).

**26.4 Lego-block tests.** Three tiers, separately runnable, each a candidate CI step: **unit** (pure logic, mocks everything external, needs nothing but Node), **integration** (real SQL against in-process Postgres, no daemon or local setup), **e2e** (the running app). Tests are grouped by feature domain, never a single tangled runner, and every tier must run inside an isolated CI container with no local terminal setup.

**26.5 Migrations are a task, not a request path.** Schema changes are plain SQL applied by a standalone runner that can execute as a one-off ECS task or CodeBuild step.

**26.6 Serverless-shaped defaults.** Connection pools stay small because serverless scales instances rather than connections (RDS Proxy fronts the database on AWS); containers build from the repo root; nothing assumes a warm process, local disk, or a long-lived server.

**26.7 The migration guide is a deliverable.** Before production, a step-by-step guide is written plainly enough to be followed without prior AWS knowledge, covering: infrastructure and IAM; how the product's agentic layer (§7) becomes AgentCore runtimes, wired through AgentCore Gateway using **OpenAPI** schemas; how features map to Lambda or container tasks; and a checklist for running all three test tiers in the cloud to prove parity with local. **Terminology note:** the `.claude/agents/*.md` subagents are *development-time* tooling and do not migrate; the runtime agents are the Phase-2 product features in §7 and §22.1.

## 27. Destinations — the assessment as a source for systems of record

The loudest complaint about assessment programmes is being asked the same
thing by different teams. The answer is not a better form; it is for the
assessment to become the **source** other systems draw from. A destination is
a downstream system of record needing facts this assessment already holds.
**First destination:** the ServiceNow **AI Use Case Record**, offered when intake records that an activity uses AI.

1. **A destination is a versioned map, not code** (NFR-20). One file per
   destination: target field, label, whether it is required, and where the
   value comes from — an answer, a derivation, or nothing. When the real
   field list arrives it is a file edit. Unconfirmed field names are marked
   provisional **on screen**: a demo implying a live mapping it does not have
   is the kind of claim this specification exists to prevent.
2. **The offer is opt-in and never blocks.** When AI is recorded, the
   requester is offered registration with a real, computed count ("24 of 29
   fields are already answered"). One click, changeable later, stored as an
   ordinary answer — insert-only, attributed, no new machinery.
3. **The assembled record is shown in three parts** (FR-27): already
   answered, each with the question its value came from; derived; and still
   needed. The third is the honest part and is never hidden.
4. **The write is out of scope and says so** (§12). The payload is real and
   downloadable; the send is labelled not connected, and nothing mimics a
   successful one. A connector, when built, goes behind the same interface as
   everything else external (§26.2) and does not change the map.
5. **Destinations are a pattern, not a feature.** Vendor records, privacy and
   security reviews have the same shape; the second one must be a map file
   plus wiring. If it needs new mechanism, this section was built wrong.