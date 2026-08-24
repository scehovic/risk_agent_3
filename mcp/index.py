"""Risk Advisor MCP server — the capability surface behind AgentCore Gateway.

    Orchestrator/sub-agent -> MCP Gateway -> THIS Lambda -> handler() dispatches on tool name

Gateway sends the tool name as "${target}___${tool}" in
context.client_context.custom['bedrockAgentCoreToolName']. Direct Lambda invokes pass
"tool_name" in the event. Both are handled — keep it that way.

Each tool is a thin wrapper over the pure engine in `intelligence/` plus the configured
instrument in `data/`. The reasoning lives in the engine so these tools stay stateless and
JSON-serialisable — the contract every tool must honour.

SIX TOOLS, ONE PER JOURNEY STEP (ADR-7)
    risk_route          — what applies to this activity, and why           [Advisor]
    risk_score_intake   — grade the description against the rubric         [Advisor]
    risk_draft_verify   — put a proposed answer through the never-guess gate [Advisor]
    risk_check_policy   — the clause requiring a control, and any breach    [Assurance]
    risk_build_report   — the derived handoff report, and vet scenarios     [Handoff]
    risk_hello          — smoke test: proves Gateway -> Lambda routing

    Deliberately small. Explanation is folded into `risk_route`; findings are folded into
    `risk_check_policy`; scenario vetting is folded into `risk_build_report`. A sprawling
    tool layer is harder for a model to choose from and harder to test.

WHAT IS NOT A TOOL
    The policy corpus, the instrument and the reference lists are pre-coded configuration
    (ADR-4). Fetching one is not a tool call; it is a file read inside the engine.
"""
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SEGMENT = "risk-advisor"

try:  # source tree
    from intelligence import risk_engine as engine
    from intelligence import assurance
except ImportError:  # staged/lambda layout (staging flattens intelligence/ to the root)
    import risk_engine as engine
    import assurance


# ── assessment resolution ────────────────────────────────────────────────────
def _deep_merge(base, over):
    """Recursively overlay `over` on `base` (nested dicts merged, not replaced)."""
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _resolve_assessment(args):
    """Merge any partial `assessment` from the caller OVER the seeded record.

    KEEP THIS AND ITS REGRESSION TEST. A sub-agent routinely calls a tool with only the
    fields it has in hand. Without a fallback the engine sees an assessment with no answers
    and — because positive evidence only means nothing activates on silence — returns
    "nothing applies to this activity". That is a PHANTOM CLEAN BILL OF HEALTH, and it is a
    worse failure than a phantom DECLINE, because a decline gets
    argued with and an all-clear gets believed.

    If a caller passes `answers` alone, it is treated as an answer overlay by question id
    rather than as a whole record, because that is how a sub-agent actually holds partial
    state mid-conversation.
    """
    seeded = engine.load_assessment()
    passed = args.get("assessment")
    if passed:
        return _deep_merge(seeded, passed)

    overlay = args.get("answers")
    if overlay and isinstance(overlay, dict):
        record = dict(seeded)
        record["answers"] = list(seeded["answers"]) + [
            {"q": qid, "value": v, "source": "person", "confirmed": True,
             "author": args.get("author"), "at": args.get("at")}
            for qid, v in overlay.items()
        ]
        return record
    return seeded


def _resolve_sources(assessment):
    """{source_id: extracted_text} for the documents on this assessment.

    Documents are stored as EXTRACTED TEXT and never as files (G-66). There is no download
    path and nothing in here a person did not already hand over.
    """
    out = {}
    for doc in assessment.get("documents", []):
        text = engine.load_document_text(doc["extracted_text_file"])
        if text:
            out[doc["id"]] = text
    return out


def _context(assessment):
    return assurance.assessment_context(assessment)


# ── tools ────────────────────────────────────────────────────────────────────
def risk_route(args):
    """What applies to this activity and why — the routing engine, with provenance.

    args: {assessment?, answers?, explain_question?}. Returns the live ledger (active paths
    with their reasons, established severities, accumulated control objectives), the
    visible-question count from the ONE visibility predicate, and — when
    `explain_question` is given — that question's routing rendered as one English sentence.
    """
    assessment = _resolve_assessment(args)
    answers = engine.answer_map(assessment)
    out = engine.ledger(answers)
    out["visible_question_count"] = len(engine.visible_questions(answers))
    out["gates"] = engine.settled_gates(answers)

    qid = args.get("explain_question")
    if qid:
        out["explanation"] = _explain_question(qid, answers)
    return out


def _explain_question(qid, answers):
    """Why is this being asked? An authority, in one sentence, naming no identifier."""
    idx = engine.instrument()
    q = idx["questions"].get(qid)
    if q is None:
        return {"question": None,
                "because": "That question is not part of this assessment."}
    reasons = []
    if q["tier"] == "t3":
        obj = idx["objectives"][qid]
        reasons = [r["reason"] for r in obj["accumulated_by"]
                   if engine.evaluate(r["condition"], answers, set(engine.active_paths(answers)))]
    elif q.get("path"):
        path = idx["paths"].get(q["path"])
        if path:
            reasons = [r["reason"] for r in path["activated_by"]
                       if engine.evaluate(r["condition"], answers)]
    elif q.get("display_when"):
        reasons = [engine.explain(q["display_when"])]
    return {"question": q["text"], "because": reasons or
            ["This is asked of every activity."],
            "authority": assurance.clauses_for(qid) if q["tier"] == "t3" else []}


def risk_score_intake(args):
    """Grade an intake description. THE HEURISTIC FLOOR RUNS FIRST, WITH NO MODEL CALL.

    args: {text, scores?}. With no `scores`, returns the floor verdict and the rubric the
    model should score against. With `scores` ({dimension_id: 0|1|2}), returns the
    deterministic feedback — the pass rule and every sentence come from
    intake_rubric.json, never from code.

    THIS NEVER BLOCKS SUBMISSION, whatever it returns.
    """
    text = args.get("text") or ""
    floor = assurance.intake_floor(text)
    if floor is not None:
        return floor

    scores = args.get("scores")
    if not scores:
        rubric = assurance.load_rubric()
        return engine.envelope(
            "awaiting_scores",
            "The floor passed with no model call; scoring is the model's entire job (G-69).",
            "Nothing is blocked either way.",
            model_called=False, blocks_submission=False,
            score_against=[{"dimension": d["id"], "label": d["label"],
                            "anchors": d["anchors"]} for d in rubric["dimensions"]])
    return assurance.intake_feedback(scores)


def risk_draft_verify(args):
    """Put a proposed answer through the never-guess gate. A REFUSAL IS AN ERROR EVENT.

    args: {draft: {question, basis, value, quote, source_id, because}, assessment?}.

    The gate refuses a paraphrase, a stitched quote, a citation to a source never supplied,
    an abstention still carrying an answer, an inference with nothing to point at, and a
    draft that does not say why. It never downgrades a bad answer into a
    lower-confidence one.

    A passing draft comes back UNCONFIRMED BY CONSTRUCTION. It counts as an answer nowhere
    until a person explicitly accepts it, and accepting writes a NEW row so the proposal
    stays underneath: "the assistant proposed and I accepted" is a history somebody can
    read rather than a claim they must believe.
    """
    assessment = _resolve_assessment(args)
    sources = _resolve_sources(assessment)
    draft = dict(args.get("draft") or {})
    context = _context(assessment)

    refusal = assurance.violates_never_guess(draft, sources)
    if refusal:
        return engine.envelope(
            "refused", "The never-guess rule (§5.2): every drafted answer states its "
                       "basis and, unless abstaining, carries a verbatim quote.",
            "Nothing was recorded. A refusal is an error event, never a lower-confidence "
            "answer.", why=refusal, question=draft.get("question"), recorded=False)

    # The guardrail runs over the `because` too. The specification once said it did while
    # the gate imported the function and never called it (G-65) — so this call is the
    # correction, and there is a test that fails if it is removed.
    checked = assurance.guardrail(draft.get("because") or "", context)
    if checked["decision"] != "passed":
        return engine.envelope(
            "refused", "Everything an agent says to a person is checked against that "
                       "assessment's record (G-65).",
            "Nothing was recorded.", why="the explanation failed the contextual guardrail",
            guardrail=checked["problems"], question=draft.get("question"), recorded=False)

    return engine.envelope(
        "proposed",
        "Verified verbatim against the stored document text with the ONE matcher (§5.3), "
        "and checked against the record (G-65).",
        "A PROPOSAL, not an answer. It is unconfirmed by construction and counts nowhere "
        "until a person accepts it in their own name.",
        question=draft.get("question"), basis=draft["basis"],
        value=draft.get("value"), quote=draft.get("quote"),
        source_id=draft.get("source_id"), because=draft.get("because"),
        confirmed=False, source="draft", recorded=False)


def risk_check_policy(args):
    """The clause requiring a control, and every breach on the record.

    args: {assessment?, question?}. With `question`, returns that control's authority —
    the policy clauses that require it, quoted verbatim with reference and version. With
    no question, returns the full deterministic compliance pass: every breach, every plain
    gap, every enhancement, and the clauses the pilot asks nothing about.

    THIS PASS STANDS ALONE. With no model available, a structured answer breaching a
    structured requirement is still caught — which is the guardrail §22.1 puts on this
    feature.
    """
    assessment = _resolve_assessment(args)
    qid = args.get("question")
    if qid:
        clauses = assurance.clauses_for(qid)
        answers = engine.answer_map(assessment)
        value = answers.get(qid)
        breaching = bool(clauses) and value in ("no", "partial")
        return engine.envelope(
            "breach" if breaching else "compliant" if clauses else "no_authority",
            "A breach is an answer of No or Partial on a question a ratified clause "
            "governs. Unanswered is never a breach; N-A is never a breach (G-67).",
            "The authority is authored data ratified by a human, never something a model "
            "decided while this rendered.",
            question=engine.instrument()["questions"].get(qid, {}).get("text"),
            answer=value, authority=clauses, model_called=False)
    return assurance.synthesize_findings(assessment)


def risk_build_report(args):
    """The handoff report, derived from the record — and the gate on anything added to it.

    args: {assessment?, summary?, scenarios?}.

    The report is COMPLETE WITH NO AGENT. Pass `summary` and `scenarios` and they are
    vetted as additions: the summary against the contextual guardrail plus a three-sentence
    length gate, and each scenario against the names that actually appear in the record —
    one citing anything else is DROPPED ENTIRELY rather than shown with a caveat, because
    it is not a weaker scenario, it is one built on nothing.
    """
    assessment = _resolve_assessment(args)
    report = assurance.build_handoff_report(assessment)
    context = _context(assessment)

    if args.get("summary"):
        report["agent_summary"] = assurance.vet_summary(args["summary"], context)
    if args.get("scenarios"):
        report["agent_scenarios"] = assurance.vet_scenarios(args["scenarios"], report)
    report["complete_without_agent"] = True
    return report


def risk_hello(args):
    """Smoke test: proves Gateway -> Lambda routing works for the risk-advisor segment."""
    who = args.get("name") or "world"
    lint = engine.lint_instrument()
    return {"message": "hello %s, from the risk-advisor segment MCP server" % who,
            "segment": SEGMENT, "instrument": lint["counted"],
            "instrument_coherent": lint["decision"] == "coherent",
            "source": "mcp/index.py"}


TOOLS = {
    "risk_route": risk_route,
    "risk_score_intake": risk_score_intake,
    "risk_draft_verify": risk_draft_verify,
    "risk_check_policy": risk_check_policy,
    "risk_build_report": risk_build_report,
    "risk_hello": risk_hello,
}


# ── dispatch ─────────────────────────────────────────────────────────────────
def _resolve_tool_name(event, context):
    """Returns (tool_name, from_context) — the caller needs to know which, because it
    decides whether 'name' in the event is the tool name or a tool argument."""
    try:
        cc = getattr(context, "client_context", None) if context else None
        custom = getattr(cc, "custom", None) or {}
        raw = custom.get("bedrockAgentCoreToolName", "") if isinstance(custom, dict) else ""
        if "___" in raw:
            return raw.split("___", 1)[1], True
        if raw:
            return raw, True
    except Exception:
        pass
    return (event.get("tool_name") or event.get("name", "")), False


def _resolve_args(event, from_context):
    """Only strip the tool-name keys when they actually carried the tool name.

    `name` is ambiguous: on a direct invoke it may be the tool name, but it is also a real
    argument to `risk_hello`. Strip it ONLY when nothing else carried the tool name —
    stripping it unconditionally silently discards the argument, and the tool then answers a
    question nobody asked.
    """
    if "input" in event and "tool_name" in event:
        return event.get("input") or {}
    if from_context:
        return dict(event)
    drop = {"tool_name"} if "tool_name" in event else {"tool_name", "name"}
    return {k: v for k, v in event.items() if k not in drop}


def handler(event, context):
    """Entrypoint. Never raises — returns an error payload."""
    event = event or {}
    tool_name, from_context = _resolve_tool_name(event, context)
    args = _resolve_args(event, from_context)
    logger.info(json.dumps({"action": "segment_mcp_invoke", "segment": SEGMENT,
                            "tool_name": tool_name, "input_keys": sorted(args.keys())}))
    fn = TOOLS.get(tool_name)
    if not fn:
        return {"error": "Unknown tool: %s" % tool_name, "available": sorted(TOOLS)}
    try:
        return fn(args)
    except Exception as exc:
        logger.exception("tool %s failed", tool_name)
        return {"error": "%s: %s" % (type(exc).__name__, exc), "tool": tool_name}
