"""AgentCore Memory — three long-term strategies, and the rules that fence them.

═══════════════════════════════════════════════════════════════════════════════
 SPEC §6.1 (the session seam), G-21 / §22.4 (portfolio memory's four rules),
 §22.2 (the evidence line), §7 (what the agent may never do)
 Owner: risk-platform
═══════════════════════════════════════════════════════════════════════════════

WHY THIS IS WRITTEN FROM SCRATCH
    The common way of wiring AgentCore Memory contains two defects that raise NO ERROR:

      1. `create_memory_record` is not the write path for conversational memory. THE WRITE
         IS AN EVENT APPEND (`create_event`); the strategies extract long-term records from
         those events afterwards.
      2. A Memory resource provisioned with ZERO EXTRACTION STRATEGIES stores nothing,
         however correct the write is.

    Get either wrong and reads, listing and deletion all still work — they just always come
    back empty, which fails exactly like an unreachable table. Both are pinned by tests.

THE THREE STRATEGIES, AND WHAT EACH IS FOR
    SUMMARIZATION  /assessment/{sessionId}/summary
        The conversation so far on ONE assessment, condensed. This is what lets a requester
        come back tomorrow to a companion that knows where they left off.

    SEMANTIC       /assessment/{sessionId}/facts
        Facts the requester stated in conversation about THEIR OWN activity, retrievable by
        meaning. Scoped to one assessment: nothing here crosses to another.

    CUSTOM         /precedent/portfolio
        Portfolio memory — how comparable assessments answered. The only cross-assessment
        namespace, and the only one with rules of its own.

WHERE THE ATTESTED-ONLY GUARANTEE ACTUALLY LIVES — read this before changing anything
    §22.4.1 forbids precedent laundering: precedent may be built ONLY from attested,
    human-signed answers, because without that one early mistake copied forward becomes
    institutional truth and the platform industrialises an error instead of a control.

    "Attested" is a STRUCTURED PREDICATE over the record, not something a language model can
    infer from a transcript. So the guarantee is enforced on the WRITE SIDE, in
    `write_precedent()`, which refuses a row that is not already an attested aggregate above
    the comparable-count floor. The custom strategy's extraction consolidates what that
    filter lets through; it is not what makes the rule true.

    Stated plainly because the opposite is the easy mistake: pointing a semantic strategy at
    raw conversation and calling the result precedent would launder unattested content into
    institutional memory, and it would look like it was working.

RECALL IS CONTEXT AND NEVER EVIDENCE (§22.2, §7)
    Everything this module returns is tagged `evidence=False`. Recalled memory may inform
    the conversation — to explain, to suggest, to ask a better question. It may never become
    an answer's basis. An answer's evidence is the person's own words, quotable and
    attributable, or a verbatim quote from a document they supplied. A recalled summary is
    neither.

EVERY WRITE IS BEST-EFFORT AND NEVER BLOCKS A RESPONSE.
"""
import json
import logging
import os

logger = logging.getLogger("risk-memory")

MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"

_client = None


# ── the strategy definitions ─────────────────────────────────────────────────
# ONE definition, imported by the CDK stack so infrastructure and code cannot drift. The
# same value living in two hand-maintained places is how a gateway ends up advertising a
# namespace the code does not read.
SUMMARY_NAMESPACE = "/assessment/{sessionId}/summary"
SEMANTIC_NAMESPACE = "/assessment/{sessionId}/facts"
PRECEDENT_NAMESPACE = "/precedent/portfolio"

PRECEDENT_ACTOR = "portfolio"
PRECEDENT_SESSION = "attested-aggregates"


DEFAULT_EXTRACTION_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def strategies(extraction_model_id=None):
    """The `memoryStrategies` payload for creating the Memory resource.

    Consumed by the CDK stack and by `deploy/template.py`, so the namespaces the code reads
    are exactly the namespaces the resource extracts into.

    `extraction_model_id` is REQUIRED by the API for a custom strategy's override, and it is
    taken as an argument rather than read from the environment: this function runs at
    template-build time, where the runtime's env vars do not exist, so reading one would
    silently produce an empty ModelId and fail validation at create time.
    """
    extraction_model_id = extraction_model_id or DEFAULT_EXTRACTION_MODEL
    return [
        {"summaryMemoryStrategy": {
            "name": "assessmentConversation",
            "description": "Condenses the companion conversation for one assessment so a "
                           "requester returning later is not started from nothing.",
            "namespaces": [SUMMARY_NAMESPACE],
        }},
        {"semanticMemoryStrategy": {
            "name": "assessmentFacts",
            "description": "Facts the requester stated about their own activity, "
                           "retrievable by meaning, scoped to this assessment only.",
            "namespaces": [SEMANTIC_NAMESPACE],
        }},
        {"customMemoryStrategy": {
            "name": "portfolioPrecedent",
            "description": "How comparable assessments answered, as aggregates. Written "
                           "only through write_precedent(), which enforces attested-only "
                           "and the comparable-count floor before anything reaches here.",
            "namespaces": [PRECEDENT_NAMESPACE],
            "configuration": {"semanticOverride": {"extraction": {"appendToPrompt": (
                "Record ONLY aggregate patterns that are already present in the input: how "
                "many attested assessments answered each way, and how recently. Never "
                "record a project name, an owner, a team, or any content from an individual "
                "assessment. Never infer a count that is not stated. If the input names an "
                "individual assessment, record nothing."
            ), "modelId": extraction_model_id}}},
        }},
    ]


def _get_client():
    """Lazy boto3 client. Absent boto3 or credentials, every function no-ops."""
    global _client
    if _client is None:
        try:
            import boto3
            _client = boto3.client("bedrock-agentcore", region_name=REGION)
        except Exception as exc:
            logger.warning("memory client unavailable: %s", exc)
            _client = False
    return _client or None


def configured():
    return bool(MEMORY_ID) and _get_client() is not None


def _resolve(template, session_id):
    return template.replace("{sessionId}", session_id)


# ── writes: an EVENT APPEND, which is the actual write path ──────────────────
def write_turn(session_id, actor_id, role, text):
    """Append one conversational turn. The strategies extract from this; nothing else does.

    `role` is USER or ASSISTANT. Best-effort: a memory failure must never break a reply.
    """
    if not configured() or not (text or "").strip():
        return False
    try:
        import datetime
        _get_client().create_event(
            memoryId=MEMORY_ID,
            actorId=actor_id,
            sessionId=session_id,
            eventTimestamp=datetime.datetime.now(datetime.timezone.utc),
            payload=[{"conversational": {"role": role.upper(),
                                         "content": {"text": text[:8000]}}}],
        )
        logger.info(json.dumps({"action": "memory_event", "session": session_id,
                                "role": role, "chars": len(text)}))
        return True
    except Exception as exc:
        logger.warning(json.dumps({"action": "memory_event_error",
                                   "error": "%s: %s" % (type(exc).__name__, exc)}))
        return False


def write_precedent(rows, rules):
    """Write attested aggregates to the ONE cross-assessment namespace.

    REFUSES anything that is not already an attested aggregate above the floor. This
    function is where §22.4.1 and §22.4.2 are actually enforced — not in the strategy
    prompt, which only shapes what it consolidates.

    Returns (written, refused) so a caller can log what was dropped rather than assume
    everything landed. A silent drop reads as "covered everything" when it did not.
    """
    floor = rules["minimum_comparable_count"]
    written, refused = [], []

    for row in rows or []:
        if not rules.get("attested_only"):
            refused.append({"question": row.get("question"),
                            "why": "precedent may only be built from attested answers"})
            continue
        if row.get("_dropped"):
            refused.append({"question": row.get("question"),
                            "why": "row is marked dropped in the seed"})
            continue
        if row.get("attested_count", 0) < floor:
            refused.append({"question": row.get("question"),
                            "why": "below the comparable-count floor of %d" % floor})
            continue
        if any(k in row for k in ("project", "owner", "team", "assessment_id")):
            refused.append({"question": row.get("question"),
                            "why": "carries identifying content; aggregate never discloses"})
            continue
        written.append(row)

    if not written or not configured():
        return written, refused

    text = "\n".join(
        "%s: of %d attested comparable assessments (%s), %s. Most recent %s, oldest %s."
        % (r["question"], r["attested_count"], r["comparable_on"],
           ", ".join("%s answered %s" % (v, k) for k, v in r["answers"].items()),
           r["most_recent"], r["oldest"])
        for r in written)
    write_turn(PRECEDENT_SESSION, PRECEDENT_ACTOR, "USER", text)
    return written, refused


# ── reads: retrieval over the extracted long-term records ────────────────────
def recall(session_id, query, kind="facts", top_k=5):
    """Recall from one assessment's own long-term memory.

    `kind` is "facts" (semantic) or "summary" (summarization). Returns a list of
    {text, evidence: False} — CONTEXT, NEVER EVIDENCE (§22.2).
    """
    if not configured():
        return []
    namespace = _resolve(SEMANTIC_NAMESPACE if kind == "facts" else SUMMARY_NAMESPACE,
                         session_id)
    try:
        resp = _get_client().retrieve_memory_records(
            memoryId=MEMORY_ID, namespace=namespace,
            searchCriteria={"searchQuery": query, "topK": top_k})
        return [{"text": _text_of(r), "namespace": namespace, "evidence": False}
                for r in resp.get("memoryRecordSummaries", []) if _text_of(r)]
    except Exception as exc:
        logger.warning(json.dumps({"action": "memory_recall_error", "kind": kind,
                                   "error": "%s: %s" % (type(exc).__name__, exc)}))
        return []


def recall_precedent(query, rules, top_k=3):
    """Recall portfolio precedent. Enforces the floor AGAIN on the way out.

    Enforced on both sides deliberately. The write filter protects the store; this
    protects the screen, and only one of them is on the side that owns the consequence.
    """
    if not configured():
        return []
    try:
        resp = _get_client().retrieve_memory_records(
            memoryId=MEMORY_ID, namespace=PRECEDENT_NAMESPACE,
            searchCriteria={"searchQuery": query, "topK": top_k})
        out = []
        for r in resp.get("memoryRecordSummaries", []):
            text = _text_of(r)
            if not text or not _mentions_enough(text, rules["minimum_comparable_count"]):
                continue
            out.append({"text": text, "evidence": False, "never_preselect": True,
                        "shown_as": "how others answered, not what you should answer"})
        return out
    except Exception as exc:
        logger.warning(json.dumps({"action": "precedent_recall_error",
                                   "error": "%s: %s" % (type(exc).__name__, exc)}))
        return []


def _mentions_enough(text, floor):
    """A recalled precedent line must state a count at or above the floor to be shown.

    A row that lost its count in consolidation cannot be shown, because "others answered
    Yes" without a number is the gossip §22.4.2 forbids.
    """
    import re
    counts = [int(n) for n in re.findall(r"\bof (\d+) attested\b", text)]
    return bool(counts) and max(counts) >= floor


def _text_of(record):
    content = record.get("content") or {}
    if isinstance(content, dict):
        return (content.get("text") or "").strip()
    return str(content).strip()


def forget(session_id, kinds=("facts", "summary")):
    """Delete one assessment's long-term records, so "it forgets on request" is a fact
    rather than achieved by stopping the runtime.

    The precedent namespace is deliberately NOT deletable from here: it holds no individual
    assessment's content, so there is nothing in it belonging to one requester to erase.
    """
    if not configured():
        return 0
    removed = 0
    client = _get_client()
    for kind in kinds:
        namespace = _resolve(SEMANTIC_NAMESPACE if kind == "facts" else SUMMARY_NAMESPACE,
                             session_id)
        try:
            resp = client.list_memory_records(memoryId=MEMORY_ID, namespace=namespace,
                                              maxResults=100)
            ids = [r["memoryRecordId"] for r in resp.get("memoryRecordSummaries", [])]
            if ids:
                client.batch_delete_memory_records(memoryId=MEMORY_ID, recordIds=ids)
                removed += len(ids)
        except Exception as exc:
            logger.warning(json.dumps({"action": "memory_forget_error", "kind": kind,
                                       "error": "%s: %s" % (type(exc).__name__, exc)}))
    return removed


def status():
    """What a health endpoint should say about memory — honestly."""
    return {"configured": configured(), "memory_id": MEMORY_ID or None,
            "region": REGION,
            "strategies": ["summarization", "semantic", "custom_precedent"],
            "namespaces": {"summary": SUMMARY_NAMESPACE, "facts": SEMANTIC_NAMESPACE,
                           "precedent": PRECEDENT_NAMESPACE},
            "recall_is_evidence": False}
