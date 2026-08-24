"""The risk instrument engine — pure, deterministic, and the ONLY evaluator.

═══════════════════════════════════════════════════════════════════════════════
 SPEC §3.2 (routing law), §3.3 (accumulation), §6.3 (the engine), §5 (invariants)
 Owner: risk-platform
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS IS
    One condition engine. Gates, path activation, conditional reveals, control
    accumulation and pre-deploy all route through `evaluate()`. There is no second
    evaluator, and adding one is a defect by definition (§5.4).

    The agent never decides anything in here. It calls tools; the tools call these
    functions; these functions read `data/`. Reasoning is the agent's, the routing is
    the engine's — the same division drawn between an LLM and a
    rating engine (ADR-2).

THE TWO LAWS THIS FILE EXISTS TO ENFORCE (§3.2.1-2)
    POSITIVE EVIDENCE ONLY. An unanswered question satisfies nothing. `not_equals` and
    `excludes` return False on a missing answer rather than True — silence never
    activates, so no risk area can be waived by omission.

    SEVERITY FAILS CLOSED. `severity_at_least` against an unknown severity is False.
    Unknown is never treated as Low.

RECOMPUTE, DON'T REMEMBER (§3.2.7, NFR-3)
    Activation and accumulation are pure functions of the current answers. Nothing
    derived is stored. Change an answer and everything downstream re-derives; answers
    to questions that are no longer visible are retained as history but leave the funnel.

NO FRAMEWORK, NO DRIVER, NO ENVIRONMENT (NFR-14, §26.1)
    Standard library only. This module is liftable into a Lambda handler with no edit
    to its body, which is exactly what `mcp/index.py` does to it.
"""
import json
import pathlib
import re

# ── the uniform envelope (ADR-5) ─────────────────────────────────────────────
# Every engine function returns at least these three. `decision` is the outcome,
# `binding_rule` is the rule that produced it, `disclosure` is the honest label on what
# the caller is holding. This is what makes the whole surface explainable by
# construction rather than by prompt instruction.


def envelope(decision, binding_rule, disclosure, **fields):
    out = {"decision": decision, "binding_rule": binding_rule, "disclosure": disclosure}
    out.update(fields)
    return out


# ── data loading (versioned instrument as config, §6.2) ──────────────────────
def _data_dir():
    """The data directory, from the source tree or from a flattened Lambda bundle."""
    here = pathlib.Path(__file__).resolve().parent
    for cand in (here.parent / "data", here / "data", pathlib.Path.cwd() / "data"):
        if cand.is_dir():
            return cand
    raise FileNotFoundError("data/ not found")


def _load_json(name):
    return json.loads((_data_dir() / name).read_text())


def load_tier1():
    return _load_json("instrument_tier1.json")


def load_tier2():
    return _load_json("instrument_tier2.json")


def load_tier3():
    return _load_json("instrument_tier3.json")


def load_reference_lists():
    return _load_json("reference_lists.json")


def load_assessment():
    return _load_json("seeded_assessment.json")


def load_document_text(filename="meridian_assist_overview.txt"):
    path = _data_dir() / filename
    return path.read_text() if path.is_file() else ""


SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}


# ── the instrument index ─────────────────────────────────────────────────────
_INDEX = None


def instrument():
    """Every question, path and objective indexed by id, built once.

    `explain()` renders question text and human option LABELS, never identifiers
    (NFR-9), so it needs this index rather than raw ids.
    """
    global _INDEX
    if _INDEX is not None:
        return _INDEX

    t1, t2, t3 = load_tier1(), load_tier2(), load_tier3()
    questions, severities, objectives = {}, {}, {}

    def _add(qid, text, options=None, **extra):
        opts = {}
        for o in options or []:
            opts[o["id"]] = o.get("label", o["id"])
        questions[qid] = dict(id=qid, text=text, options=opts, **extra)

    for section in t1["intake"]["sections"]:
        for f in section["fields"]:
            _add(f["id"], f["text"], f.get("options"), tier="intake",
                 section=section["id"], help=f.get("help", ""),
                 required=f.get("required", False), graded=f.get("graded", False),
                 display_when=f.get("display_when"))

    for cat in t1["categories"]:
        g = cat["gate"]
        _add(g["id"], g["text"], g.get("options"), tier="gate", category=cat["id"],
             help=g.get("help", ""), always_applies=cat.get("always_applies", False),
             pilot_depth=cat["pilot_depth"], boundary_note=cat.get("boundary_note"),
             prefill_from=cat.get("prefill_from"))

    for q in t1["tier1_questions"]:
        _add(q["id"], q["text"], q.get("options"), tier="t1", category=q["category"],
             help=q.get("help", ""), display_when=q.get("display_when"),
             multi=q["type"] == "multi_select")

    for q in t2["severity_questions"]:
        anchors = q.get("anchors") or {}
        options = [{"id": b, "label": anchors[b]} for b in ("low", "medium", "high") if b in anchors]
        options += q.get("options") or []
        _add(q["id"], q["text"], options, tier="t2", path=q.get("path"),
             help=q.get("help", ""), always_on=q.get("always_on", False),
             derivation=q.get("derivation"), anchors=anchors)
        severities[q["id"]] = questions[q["id"]]

    for c in t2["conditionals"]:
        _add(c["id"], c["text"], c.get("options"), tier="t2c", help=c.get("help", ""),
             kind=c["kind"], lead=c.get("lead"), threshold=c.get("threshold"),
             path=c.get("path"), requires_tier1=c.get("requires_tier1"),
             requires_sibling=c.get("requires_sibling"), capture=c.get("capture", False))

    for o in t3["objectives"]:
        _add(o["id"], o["question"], None, tier="t3", family=o["family"],
             name=o["name"], help=o.get("help", ""))
        objectives[o["id"]] = o
        for child in o.get("children") or []:
            _add(child["id"], child["question"], child.get("options"), tier="t3c",
                 parent=o["id"], help=child.get("help", ""),
                 requires_tier1=child.get("requires_tier1"))

    _INDEX = {
        "questions": questions,
        "severities": severities,
        "objectives": objectives,
        "paths": {p["code"]: p for p in t1["paths"]},
        "categories": {c["id"]: c for c in t1["categories"]},
        "conditionals": {c["id"]: c for c in t2["conditionals"]},
        "tier1": t1, "tier2": t2, "tier3": t3,
    }
    return _INDEX


def answer_map(assessment):
    """{question_id: value} from an assessment's answer records.

    Only CONFIRMED answers count. An unconfirmed draft is a proposal, and a proposal
    is an answer nowhere (G-66) — including here, which is the point: routing must
    never move because something was suggested to somebody.
    """
    out = {}
    for a in assessment.get("answers", []):
        if a.get("confirmed") is False:
            continue
        out[a["q"]] = a.get("value")
    return out


# ── the ONE condition engine (§6.3) ──────────────────────────────────────────
def evaluate(cond, answers, active=None):
    """Evaluate one condition. The only evaluator in the system (§5.4).

    `active` is the set of currently active path codes, needed by `path_active`. It is
    passed in rather than recomputed to keep this function pure and non-recursive.
    """
    if cond is None:
        return True

    if "all" in cond:
        return all(evaluate(c, answers, active) for c in cond["all"])
    if "any" in cond:
        return any(evaluate(c, answers, active) for c in cond["any"])
    if "not" in cond:
        return not evaluate(cond["not"], answers, active)

    op = cond.get("op")

    if op == "always":
        return True
    if op == "path_active":
        return cond["path"] in (active or set())

    if op == "severity_at_least":
        band = severity_of(cond["q"], answers)
        if band is None:
            return False  # SEVERITY FAILS CLOSED (§3.2.2). Unknown is never Low.
        return SEVERITY_ORDER.get(band, 0) >= SEVERITY_ORDER.get(cond["band"], 99)

    value = answers.get(cond["q"])
    present = value is not None and value != [] and value != ""

    if op == "answered":
        return present
    if op == "blank":
        # The one operator that asserts absence. Legitimate, but it may never appear in
        # an activation or accumulation rule — `lint_instrument()` enforces that, because
        # silence activating anything is how a risk area gets waived by omission.
        return not present

    # POSITIVE EVIDENCE ONLY (§3.2.1). Every operator below — including the negative
    # ones — is False on a missing answer. This single early return is the law.
    if not present:
        return False

    as_list = value if isinstance(value, list) else [value]

    if op == "equals":
        return value == cond["value"]
    if op == "not_equals":
        return value != cond["value"]
    if op == "includes":
        return cond["value"] in as_list
    if op == "excludes":
        return cond["value"] not in as_list
    if op == "any_of":
        return any(v in cond["values"] for v in as_list)
    if op == "all_of":
        return all(v in as_list for v in cond["values"])
    if op == "at_least":
        return _num(value) is not None and _num(value) >= cond["value"]
    if op == "at_most":
        return _num(value) is not None and _num(value) <= cond["value"]

    raise ValueError("unknown operator: %s" % op)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ── explainability: one English sentence, never an identifier (FR-5, NFR-9) ──
def explain(cond):
    """Render any condition as exactly one English sentence.

    Question text and human option labels only. A sentence naming `t3_iam_02` has handed
    the reader our problem instead of an answer (§24.2, NFR-9).
    """
    return _explain(cond).rstrip(".") + "."


def _explain(cond):
    if cond is None:
        return "always"
    if "all" in cond:
        return " and ".join(_explain(c) for c in cond["all"])
    if "any" in cond:
        return " or ".join(_explain(c) for c in cond["any"])
    if "not" in cond:
        return "it is not the case that " + _explain(cond["not"])

    op = cond.get("op")
    if op == "always":
        return "this applies to every activity"
    if op == "path_active":
        p = instrument()["paths"].get(cond["path"], {})
        return '"%s" applies' % p.get("name", cond["path"])
    if op == "severity_at_least":
        q = instrument()["questions"].get(cond["q"], {})
        return 'the answer to "%s" is %s or higher' % (
            q.get("text", "a severity question"), cond["band"].capitalize())

    q = instrument()["questions"].get(cond["q"], {})
    text = q.get("text", "an earlier question")
    labels = q.get("options", {})

    def lbl(v):
        return '"%s"' % labels.get(v, v)

    if op == "answered":
        return 'you answered "%s"' % text
    if op == "blank":
        return 'you have not yet answered "%s"' % text
    if op == "equals":
        return 'you answered %s to "%s"' % (lbl(cond["value"]), text)
    if op == "not_equals":
        return 'your answer to "%s" is something other than %s' % (text, lbl(cond["value"]))
    if op == "includes":
        return 'you chose %s for "%s"' % (lbl(cond["value"]), text)
    if op == "excludes":
        return 'you did not choose %s for "%s"' % (lbl(cond["value"]), text)
    if op == "any_of":
        return 'you chose %s for "%s"' % (
            " or ".join(lbl(v) for v in cond["values"]), text)
    if op == "all_of":
        return 'you chose %s for "%s"' % (
            " and ".join(lbl(v) for v in cond["values"]), text)
    if op in ("at_least", "at_most"):
        word = "at least" if op == "at_least" else "no more than"
        return 'your answer to "%s" is %s %s' % (text, word, cond["value"])
    return "an authored condition"


# ── severity, including derived bands (FR-7, §3.2.5) ─────────────────────────
def severity_of(qid, answers):
    """The severity band for a severity question, or None if it is not established.

    Two routes, both data (§3.2.5). A rubric-anchored question stores the band because
    THE ANCHOR IS THE OPTION (G-45) — the person picked a sentence, and the band is what
    that sentence means. A derived question stores a FACT, and a declared mapping turns
    it into a band. Derivations are data, never code.
    """
    q = instrument()["severities"].get(qid)
    if q is None:
        return None
    value = answers.get(qid)
    if value is None:
        return None
    derivation = q.get("derivation")
    if derivation:
        return derivation["map"].get(value)
    return value if value in SEVERITY_ORDER else None


def derived_severity_reason(qid):
    q = instrument()["severities"].get(qid) or {}
    d = q.get("derivation") or {}
    return d.get("reason")


# ── path activation: union with provenance (FR-4, §3.2.4) ────────────────────
def active_paths(answers):
    """Active paths, each retaining EVERY reason that lit it.

    Union semantics. Two satisfied rules mean one active path with two reasons — not one
    reason, and not two paths. The requester and the reviewer can always see why
    something is being asked.
    """
    out = {}
    for code, path in instrument()["paths"].items():
        reasons = [r["reason"] for r in path["activated_by"]
                   if evaluate(r["condition"], answers)]
        if reasons:
            out[code] = {"code": code, "name": path["name"],
                         "category": path["category"], "reasons": reasons}
    return out


def settled_gates(answers):
    """Which categories are open, and why. A gate of No closes its category entirely."""
    out = {}
    for cid, cat in instrument()["categories"].items():
        gate = cat["gate"]
        if cat.get("always_applies"):
            out[cid] = {"open": True, "because": "this area applies to every activity",
                        "asked": False, "pilot_depth": cat["pilot_depth"]}
            continue
        value = answers.get(gate["id"])
        prefill = cat.get("prefill_from")
        prefilled_reason = None
        if value is None and prefill and evaluate(prefill["condition"], answers):
            # FR-22: an intake answer that duplicates a gate PRE-ANSWERS it — visibly,
            # with its reason, and changeable. Offered, never silently adopted: a
            # pre-selected answer nobody looked at becomes that person's attributed
            # answer, which is the failure the platform exists to prevent (G-39a).
            prefilled_reason = prefill["reason"]
        out[cid] = {
            "open": value == "yes" or value == "not_sure",
            "answer": value,
            "suggested": None if value is not None else (prefill or {}).get("value"),
            "suggested_because": prefilled_reason,
            "asked": True,
            "pilot_depth": cat["pilot_depth"],
            "boundary_note": cat.get("boundary_note"),
        }
    return out


# ── the ONE visibility predicate (§3.2.3, NFR-2) ─────────────────────────────
def visible(qid, answers, active=None, gates=None):
    """Is this question in the funnel?

    A question is visible IFF its category/path context is active AND its own display
    condition passes. Every surface consumes this one function — the requester flow, the
    reviewer queue counts, the drafting scope, the report and the packaging gate. A
    question is in the funnel everywhere or nowhere.
    """
    active = active if active is not None else set(active_paths(answers))
    gates = gates if gates is not None else settled_gates(answers)
    q = instrument()["questions"].get(qid)
    if q is None:
        return False
    tier = q["tier"]

    if tier == "intake":
        return evaluate(q.get("display_when"), answers, active)

    if tier == "gate":
        return not q.get("always_applies", False)

    if tier == "t1":
        if not gates.get(q["category"], {}).get("open"):
            return False
        return evaluate(q.get("display_when"), answers, active)

    if tier == "t2":
        if q.get("always_on"):
            return True
        return q.get("path") in active

    if tier == "t2c":
        return _conditional_visible(q, answers, active)

    if tier == "t3":
        return qid in accumulate(answers, active)

    if tier == "t3c":
        parent = q["parent"]
        # Children never fire unless the parent is Yes (§3.4). A suppressed child is
        # INVISIBLE, not "skipped" — the distinction matters to the reviewer.
        if answers.get(parent) != "yes":
            return False
        return evaluate(q.get("requires_tier1"), answers, active)

    return False


def _conditional_visible(q, answers, active):
    """The four conditional kinds (FR-8). Each adds a requirement; none replaces one."""
    kind = q["kind"]

    if kind == "always_fired":
        return q.get("path") in active

    lead = q.get("lead")
    lead_q = instrument()["severities"].get(lead) or {}
    if lead_q.get("path") and lead_q["path"] not in active and not lead_q.get("always_on"):
        return False
    if not evaluate({"op": "severity_at_least", "q": lead, "band": q["threshold"]},
                    answers, active):
        return False

    if kind == "severity_fired":
        return True
    if kind == "cross_tier":
        return evaluate(q.get("requires_tier1"), answers, active)
    if kind == "nested":
        return evaluate(q.get("requires_sibling"), answers, active)
    return False


def visible_questions(answers):
    """Every visible question id, in instrument order. The funnel, computed."""
    active = set(active_paths(answers))
    gates = settled_gates(answers)
    return [qid for qid in instrument()["questions"]
            if visible(qid, answers, active, gates)]


# ── control accumulation (FR-10, §3.3) ───────────────────────────────────────
def accumulate(answers, active=None):
    """Accumulated control objectives, each with EVERY reason that pulled it in.

    Expressed as activation conditions over the SAME engine (§3.3) — there is no second
    evaluator. Computed per call, never stored (NFR-3, G-45).
    """
    active = active if active is not None else set(active_paths(answers))
    out = {}
    for oid, obj in instrument()["objectives"].items():
        reasons = [r["reason"] for r in obj["accumulated_by"]
                   if evaluate(r["condition"], answers, active)]
        if reasons:
            out[oid] = {"id": oid, "name": obj["name"], "family": obj["family"],
                        "question": obj["question"], "reasons": reasons}
    return out


def ledger(answers):
    """The live ledger the requester always sees (FR-11): active paths WITH REASONS,
    severities, and accumulated objectives. All three, recomputed on every read.

    FR-11 was once shipped showing only the third, so a person saw the consequence
    without the reasoning (G-57). All three or it is not the ledger.
    """
    active = active_paths(answers)
    active_codes = set(active)
    severities = {}
    for qid, q in instrument()["severities"].items():
        if not visible(qid, answers, active_codes):
            continue
        band = severity_of(qid, answers)
        severities[qid] = {
            "question": q["text"], "band": band,
            "derived_because": derived_severity_reason(qid) if band and q.get("derivation") else None,
        }
    objectives = accumulate(answers, active_codes)
    return envelope(
        "ledger_derived",
        "Paths, severities and accumulated controls are pure functions of the current "
        "answers, recomputed on every read and stored nowhere (NFR-3).",
        "This is what is being asked of you and why. It changes as your answers change.",
        active_paths=list(active.values()),
        severities=severities,
        objectives=list(objectives.values()),
        counts={"paths": len(active), "severities": len(severities),
                "objectives": len(objectives)},
    )


# ── the coherence lint (§8) ──────────────────────────────────────────────────
def lint_instrument():
    """Structural checks over the authored instrument. A defect list, never a fix.

    Changing what is asked is a governance event (§8), so this reports and stops. Named
    rather than implied: this is the checks-inside-the-validator half of the coherence
    gate, not a standalone command.
    """
    idx = instrument()
    problems = []
    qids = set(idx["questions"])

    def _refs(cond, where):
        if cond is None:
            return
        for key in ("all", "any"):
            if key in cond:
                for c in cond[key]:
                    _refs(c, where)
                return
        if "not" in cond:
            _refs(cond["not"], where)
            return
        if cond.get("op") == "blank":
            problems.append("%s uses `blank`: silence may never activate anything (§3.2.1)" % where)
        if cond.get("op") == "path_active" and cond["path"] not in idx["paths"]:
            problems.append("%s references unknown path %s" % (where, cond["path"]))
        if "q" in cond and cond["q"] not in qids:
            problems.append("%s references unknown question %s" % (where, cond["q"]))

    for code, p in idx["paths"].items():
        if not p["activated_by"]:
            problems.append("path %s can never activate" % code)
        for r in p["activated_by"]:
            _refs(r["condition"], "path %s" % code)
            if not r.get("reason"):
                problems.append("path %s has an activation with no reason (FR-4)" % code)

    for oid, o in idx["objectives"].items():
        if not o["accumulated_by"]:
            problems.append("objective %s can never accumulate" % oid)
        for r in o["accumulated_by"]:
            _refs(r["condition"], "objective %s" % oid)
            if not r.get("reason"):
                problems.append("objective %s has an accumulation with no reason (FR-10)" % oid)

    for qid, q in idx["severities"].items():
        if q.get("derivation"):
            if not q["derivation"].get("reason"):
                problems.append("derived severity %s has no reason (FR-33)" % qid)
            for band in q["derivation"]["map"].values():
                if band not in SEVERITY_ORDER:
                    problems.append("derived severity %s maps to unknown band %s" % (qid, band))
        elif set(q.get("anchors") or {}) != {"low", "medium", "high"}:
            problems.append("severity question %s lacks a full rubric (§8)" % qid)

    for cid, c in idx["conditionals"].items():
        if c["kind"] != "always_fired" and c.get("lead") not in idx["severities"]:
            problems.append("conditional %s leads on a non-severity question" % cid)
        if c["kind"] == "nested":
            _refs(c.get("requires_sibling"), "conditional %s" % cid)
        if c["kind"] == "cross_tier":
            _refs(c.get("requires_tier1"), "conditional %s" % cid)

    for qid, q in idx["questions"].items():
        # G-23: helper text teaches, never repeats the label.
        h = (q.get("help") or "").strip().lower()
        if h and h == (q.get("text") or "").strip().lower():
            problems.append("question %s has help that restates its label (G-23)" % qid)

    return envelope(
        "coherent" if not problems else "incoherent",
        "Referential integrity, reason coverage, rubric completeness, no activation on "
        "silence, and the help-text no-repeat rule (§8, G-23).",
        "A structural check over the authored instrument. It reports and never edits — "
        "changing what is asked is a governance event.",
        problems=problems, problem_count=len(problems),
        counted={"questions": len(idx["questions"]), "paths": len(idx["paths"]),
                 "severity_questions": len(idx["severities"]),
                 "objectives": len(idx["objectives"]),
                 "categories": len(idx["categories"])},
    )


# ── the ONE verbatim matcher (§5.3) ──────────────────────────────────────────
def normalise(text):
    """Whitespace-normalised, case-preserved. Defined once."""
    return re.sub(r"\s+", " ", (text or "")).strip()


def verbatim_match(quote, source):
    """Whitespace-normalised substring matching. THE matcher (§5.3).

    Used by the never-guess gate, the eval scorer and the source highlighter alike. A
    second matcher is a defect by definition — two matchers means the gate can accept a
    quote the highlighter cannot find, and the record then carries a citation nobody can
    check.
    """
    q, s = normalise(quote), normalise(source)
    return bool(q) and bool(s) and q in s
