# `data/` — the instrument and its policy, as configuration

Everything the engine reasons over is here, and **nothing here is code**. This is the
risk-domain equivalent of an insurer's rate tables and underwriting rules:
filed content owned by a different function, changing on a different cadence than the
software (SPEC §6.2, ADR-3).

Changing a file in this folder is a **governance event** (SPEC §8), not a code change.
Anything the instrument cannot express as data triggers a design conversation, not a
workaround.

| File | Holds | Authority |
| --- | --- | --- |
| `instrument_tier1.json` | Intake (4 sections), the 11 category gates, 11 Tier-1 questions, and the 21 path activation rules with their reasons | Owner; wording transcribed verbatim (G-27) |
| `instrument_tier2.json` | 26 severity questions — 21 path-attached, 4 always-on, 1 derived — with the rubric anchor **as the option**, plus 8 conditionals covering all four kinds | Owner (G-45) |
| `instrument_tier3.json` | 51 control objectives across 14 families, their accumulation conditions, and their child questions | Owner |
| `policies.json` | 5 enterprise policies, 17 clauses, each in **its own words**, each naming the control questions it bears on | Policy owners named per file (G-67) |
| `intake_rubric.json` | The heuristic floor, the 5 scoring dimensions with 0/1/2 anchors, and the exact sentence a person reads per dimension per score | Business copy (G-69) |
| `control_domains.json` | Control family → risk domain map for attestation authority, and the reviewer queue rubric | Risk organisation (G-60, G-61) |
| `reference_lists.json` | People, business units, vendors — versioned, with one off-list value awaiting ratification | Admin (G-46 to G-48) |
| `seeded_assessment.json` | The demo assessment record — the `AssessmentContext` every capability is grounded in | Synthetic |
| `meridian_assist_overview.txt` | The vendor document the drafting capability reads, stored as **extracted text only** | Synthetic (G-66) |
| `precedent_aggregates.json` | Portfolio-memory seed: attested-only, aggregate-only rows for the custom memory strategy | Synthetic (§22.4) |

## Three properties the data must keep

**Immutable once activated.** Every file carries `version` and `activated`. A change is a
new version; answers pin the version they were made under, so history always renders
(§5.7, NFR-11).

**Positive evidence only.** Nothing in an activation or accumulation condition may fire on
a *missing* answer. Negative operators (`not_equals`, `excludes`) do not pass on silence,
and `severity_at_least` against an unknown severity is false. No risk area can be waived
by omission (§3.2.1–2).

**Every activation carries its reason.** Each entry in `activated_by` and `accumulated_by`
has a human-readable `reason` written for the person answering. A path or an objective
that appears without one is a defect — the requester and the reviewer can always see *why*
something is being asked (FR-10, §3.2.4).

## Deliberate gaps, named rather than hidden

- `policies.json` clause **DP-8.5** governs nothing. That is a **coverage gap in the
  instrument**, not an error: an obligation with no question is §22.1 read backwards, and
  the more useful direction. It is named so it is a fact, not an omission.
- Seven of the eleven risk areas are **gate-only** in the pilot (G-50), each carrying a
  `boundary_note` that says on screen that it stops deliberately. A place where the product
  deliberately stops must say it is stopping deliberately.
- Four accumulated Tier-3 objectives in `seeded_assessment.json` are **unanswered on
  purpose**, so the handoff report's "nobody answered this" section reads from something
  real and the drafting capability has somewhere to propose.
- One precedent row in `precedent_aggregates.json` sits **below the comparable-count
  floor** and is marked dropped, so the floor is visible and testable rather than implicit.
