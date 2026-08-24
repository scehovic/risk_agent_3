"""The session seam — the ONE module that reads and writes conversation state (§6.1).

Exactly one module knows how session state is held. Nothing else in the codebase may
address it, and it is shaped for AgentCore Memory rather than adapted to it later.

WHAT ARRIVES IS AUTHORITATIVE (ADR-6)
    `adopt()` takes the assessment record handed in by the caller and treats it as the
    truth. Facts established upstream are never re-derived here — that is the single
    source of truth for the figures every sub-agent reasons over, and it is why the tools
    can stay stateless.

WHAT THE AGENT IS ALLOWED TO KNOW (G-65)
    `context_block()` renders an AssessmentContext and nothing wider: the activity in the
    person's own words, what is on record as label and value, and what is still open. Not
    the whole database, and never another team's assessment. The service REFUSES a request
    without one rather than proceeding unguarded, because an agent that cannot be told what
    is on record cannot be caught claiming something that is not.
"""
import json
import logging

import memory

logger = logging.getLogger("risk-session")

_STATE = {"assessment": None, "context": None, "session_id": None}


def adopt(assessment, session_id):
    """Take the caller's assessment record as authoritative. Returns the context or None."""
    _STATE["session_id"] = session_id
    if not assessment:
        _STATE["assessment"] = None
        _STATE["context"] = None
        return None
    try:
        import assurance
        _STATE["assessment"] = assessment
        _STATE["context"] = assurance.assessment_context(assessment)
        return _STATE["context"]
    except Exception as exc:
        logger.warning("could not build assessment context: %s", exc)
        _STATE["assessment"] = assessment
        _STATE["context"] = None
        return None


def assessment():
    return _STATE["assessment"]


def context():
    return _STATE["context"]


def session_id():
    return _STATE["session_id"] or "unknown"


def context_block():
    """The context injected into every sub-agent's system prompt, as prose.

    Deliberately renders ANSWERS AS LABELS and never as identifiers, because whatever is
    put in front of a model is what the model repeats back — and a requester told
    "t3_iam_02 is unanswered" has been handed our problem instead of an answer (NFR-9).
    """
    ctx = _STATE["context"]
    if not ctx:
        return ""
    lines = [
        "THIS ASSESSMENT'S RECORD — the only thing you may treat as known.",
        "Activity: %s" % (ctx.get("activity") or "not yet named"),
        "",
        "In the requester's own words:",
        (ctx.get("in_their_words") or "(nothing written yet)"),
        "",
        "On record (%d answers), as question then answer. Never attribute anything to this "
        "person that is not in this list:" % len(ctx.get("recorded") or {}),
    ]
    for entry in list((ctx.get("recorded") or {}).values())[:60]:
        lines.append("  - %s -> %s" % (entry["question"], entry["answer"]))
    open_qs = ctx.get("open") or []
    if open_qs:
        lines.append("")
        lines.append("Still open (%d). Refer to these BY THEIR QUESTION TEXT, never by an "
                     "identifier:" % len(open_qs))
        for q in open_qs[:20]:
            lines.append("  - %s" % q["question"])
    return "\n".join(lines)


def remember_turn(role, text):
    """Append a turn to long-term memory. Best-effort; never blocks a reply."""
    actor = (_STATE.get("context") or {}).get("assessment_id") or "unknown"
    return memory.write_turn(session_id(), actor, role, text)


def recall(query, kind="facts"):
    """Recall from this assessment's memory. CONTEXT, NEVER EVIDENCE (§22.2)."""
    return memory.recall(session_id(), query, kind=kind)


def recall_precedent(query, rules):
    """Recall portfolio precedent, aggregate and floored (§22.4)."""
    return memory.recall_precedent(query, rules)


def status():
    return {"session_id": _STATE["session_id"],
            "has_context": _STATE["context"] is not None,
            "recorded_answers": len((_STATE.get("context") or {}).get("recorded") or {}),
            "memory": memory.status()}


def reset():
    """Clear process state between requests. A cached agent must never leak one
    assessment's figures into the next."""
    _STATE.update({"assessment": None, "context": None, "session_id": None})


def dumps():
    return json.dumps(_STATE["context"] or {}, default=str)
