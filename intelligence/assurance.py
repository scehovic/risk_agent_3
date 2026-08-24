"""The assurance layer — gates, guardrails, findings, the report, and intake scoring.

═══════════════════════════════════════════════════════════════════════════════
 SPEC §5.2 (never-guess), G-65 (contextual guardrail), §4.3/G-67 (findings),
 §4.4-4.5/G-68 (the handoff report), §22.1/G-69 (intake scoring), §22.4 (precedent)
 Owner: risk-platform
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS IS
    Everything that stands between a model's output and the record. Pure, deterministic,
    and enforced here rather than in a prompt — a prompt instruction can be argued with
    by a clever conversation; a code contract cannot (ADR-5).

    Every function in here works with NO MODEL AVAILABLE. That is not a graceful
    degradation, it is the requirement: the deterministic pass stands alone (G-67), and
    the report is complete without the agent (G-68).

THE RULE THIS FILE WAS WRITTEN AGAINST
    A guardrail is not shipped when it is written, it is shipped when something PROVES IT
    FIRES (G-65). The specification once said these checks ran while the drafting gate
    imported the function and never called it — the import passed the type checker
    because nothing forbids an unused one. Every check below has a test that names the
    exact sentence it exists to stop.
"""
import json
import re

try:  # source tree: intelligence/ is a package. staged Lambda: flattened to the zip root.
    from intelligence.risk_engine import (accumulate, active_paths, answer_map, envelope,
                                          instrument, normalise, severity_of,
                                          verbatim_match, visible, visible_questions,
                                          _load_json)
except ImportError:
    from risk_engine import (accumulate, active_paths, answer_map, envelope, instrument,
                             normalise, severity_of, verbatim_match, visible,
                             visible_questions, _load_json)

BREACHING = ("no", "partial")


def load_policies():
    return _load_json("policies.json")


def load_rubric():
    return _load_json("intake_rubric.json")


def load_control_domains():
    return _load_json("control_domains.json")


def load_precedent():
    return _load_json("precedent_aggregates.json")


# ══════════════════════════════════════════════════════════════════════════════
#  1. THE NEVER-GUESS GATE (§5.2, G-63, G-64)
# ══════════════════════════════════════════════════════════════════════════════
def violates_never_guess(draft, sources):
    """Why this drafted answer must be refused, or None if it may pass.

    A pure function beside the gate rather than inside it, because an earlier implementation
    enforced this three times over and that is the right number — each catches what the
    others cannot (G-63).

    `sources` is {source_id: text}. Every refusal below names a specific fabricated reply
    that was used to prove it fires; a model behaving well proves nothing about what
    happens when it does not (G-64).
    """
    basis = draft.get("basis")

    if draft.get("confirmed"):
        return "a drafted answer can never arrive confirmed — only a person confirms"

    if basis not in ("stated", "inferred", "not_stated"):
        return "basis must be stated, inferred or not_stated"

    if basis == "not_stated":
        # Abstention is a CORRECT, SCOREABLE OUTCOME (§5.2), not a failure. What it may
        # not do is carry an answer anyway.
        if draft.get("value") not in (None, ""):
            return "an abstention may not carry an answer"
        if not (draft.get("because") or "").strip():
            return "an abstention must say what it looked for and did not find"
        return None

    if draft.get("value") in (None, ""):
        return "a stated or inferred answer must carry a value"

    if not (draft.get("because") or "").strip():
        return "a drafted answer must say why"

    quote = draft.get("quote")
    if not (quote or "").strip():
        # An inference with nothing to point at is a guess (G-63), so this applies to
        # `inferred` exactly as it applies to `stated`.
        article = "an" if basis == "inferred" else "a"
        return "%s %s answer must carry a verbatim quote" % (article, basis)

    source_id = draft.get("source_id")
    if source_id not in sources:
        return "the cited source was never supplied"

    if not verbatim_match(quote, sources[source_id]):
        # Catches a paraphrase AND a STITCHED QUOTE — one assembled from two real
        # fragments that never appeared together. The normalised substring test refuses
        # it because the stitched string is not contiguous in the source.
        return "the quote does not appear verbatim in the cited source"

    if draft.get("source") == "person":
        return "evidence may not ride on a person's own answer"

    return None


# ══════════════════════════════════════════════════════════════════════════════
#  2. THE CONTEXTUAL GUARDRAIL (G-65)
#     ONE function, called by EVERY capability, over EVERY human-readable output.
# ══════════════════════════════════════════════════════════════════════════════
# Widened after independent verification found each of these forms slipping through.
_ID_PATTERNS = [
    (r"\bp\.[a-z][a-z-]+\b", "a person identifier"),                       # p.okonkwo, p.requester
    (r"\b(?:t1|t2|t2c|t3|t3c)[_.][a-z0-9_]+\b", "a question identifier"),  # t3_iam_02
    (r"\b(?:v|bu|doc|ho|asm)\.[a-z0-9_.-]+\b", "a record identifier"),     # v.meridian, bu.retail_ops
    (r"\b(?:TPR|AIM|PRIV|SEC)_[A-Z]{2,}\b", "a path code"),                # TPR_LA
    (r"\b[A-Z0-9]{2,}_[A-Z0-9_]{2,}\b", "an internal code"),               # upper-cased ids
    (r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "a uuid"),
    (r"\bASM-\d{4}-\d{3,}\b", "an assessment reference"),
]

_RECORDING_CLAIMS = [
    r"\b(?:i|we)(?:'ve| have)? (?:recorded|saved|stored|submitted|signed|attested|logged|filed)\b",
    r"\b(?:has|have) been (?:recorded|saved|submitted|signed|attested|approved|accepted)\b",
    r"\byour (?:answer|assessment|submission|declaration) (?:is|has been) (?:recorded|saved|submitted|signed|complete)\b",
    r"\bthat(?:'s| is) (?:now )?(?:recorded|saved|submitted|signed|done)\b",
]


def uttered_internal_identifier(text):
    """Every internal identifier found in something a person will read (NFR-9, §24.2).

    The likeliest failure of all, because the model is handed ids in its own instructions
    and repeating one feels helpful. A requester told "t3_iam_02 is unanswered" has been
    given our problem instead of an answer.
    """
    found = []
    for pattern, what in _ID_PATTERNS:
        for m in re.findall(pattern, text or ""):
            found.append({"token": m, "kind": what})
    return found


_STOP = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "to", "of", "in",
         "on", "for", "that", "this", "it", "there", "and", "or", "we", "our", "us",
         "you", "your", "they", "their", "them", "as", "at", "by", "with", "do", "does",
         "did", "have", "has", "any", "all", "would", "will", "can", "could", "most",
         "some", "if", "so", "about", "from", "into", "than", "then", "what", "which",
         "who", "how", "when", "form", "kind", "involved"}
_BARE = {"yes", "no", "sure", "unsure", "maybe"}


def _tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t}


def claims_unrecorded_answer(text, recorded):
    """Attributions to a person of something the record does not hold (G-42).

    Catches the specific and plausible failure of a model recapping "you said the data is
    Confidential" when they said no such thing, and a busy person reading that as
    confirmation and stopping.

    CLAUSE BY CLAUSE, never whole sentences. Comparing whole sentences meant ONE TRUE
    CLAUSE LAUNDERED EVERY FALSE CLAIM BESIDE IT — "You said Yes to AI, and you said the
    data is Restricted" passed on the strength of "Yes".

    A claim is checked against the QUESTION AND ITS ANSWER TOGETHER, not against a bag of
    values. Matching a bag of values is how "You told us there is no third party involved"
    passed: some unrelated gate is answered "No", and a two-letter value is a substring of
    almost any sentence. A claim's topic must match a question and its value must match
    that question's answer.

    HONEST LIMIT, stated rather than discovered later: this catches a FABRICATED VALUE. It
    does not catch every possible rewording of a false statement, and it will occasionally
    suppress a true one. That direction is deliberate — under fail-open a false positive
    means the assistant says nothing, and a false negative means a person is told they
    said something they did not. The assessor's attestation remains the backstop.
    """
    entries = []
    for value in recorded.values():
        if isinstance(value, dict):
            entries.append((_tokens(value.get("question")), _tokens(str(value.get("answer")))))
        else:
            entries.append((set(), _tokens(str(value))))

    problems = []
    for clause in _clauses(text):
        low = clause.lower()
        if not re.search(r"\byou (?:said|told us|answered|chose|selected|confirmed|indicated)\b", low):
            continue
        claimed = _quoted_or_trailing(clause)
        if not claimed:
            continue
        if not _supported_by_record(_tokens(claimed), entries):
            problems.append({"clause": clause.strip(), "claimed": claimed})
    return problems


def _supported_by_record(claim_tokens, entries):
    """Is this claim's value present on a question its topic actually refers to?

    The claim must RESTATE an answer, not merely share a word with one. Sharing a word is
    how "you said the data is Restricted" passed: an unrelated multi-select answer contains
    the word "data", and one shared content word was treated as a match. So a substantive
    answer counts only when most of it is present in the claim.
    """
    topic = claim_tokens - _STOP - _BARE
    for question, answer in entries:
        if not (answer & claim_tokens):
            continue                        # the asserted value is not this answer at all
        substantive = answer - _BARE - _STOP
        if substantive:
            shared = substantive & claim_tokens
            if shared == substantive or len(shared) / len(substantive) >= 0.6:
                return True                 # the claim restates this answer
        if not topic:
            return True                     # the claim is only a bare value
        # A bare value ("yes"/"no") plus a topic. The topic must COVER the question, not
        # merely brush against it: {third, party} brushes against "Does the third party
        # reach our systems only through a controlled gateway" — answered No — and that let
        # "there is no third party involved" pass while a third party plainly is involved.
        substantive_question = question - _STOP
        if substantive_question and \
                len(topic & substantive_question) / len(substantive_question) >= 0.4:
            return True
    return False


def claims_work_was_recorded(text):
    """Claims that work was recorded, saved, submitted or signed (G-65).

    The conversational gate stays deliberately NARROWER than the drafting gate — holding a
    thought partner to the verbatim standard would make it impossible — and what it does
    enforce is the claim that would actually cause harm.
    """
    low = (text or "").lower()
    return [p for p in _RECORDING_CLAIMS if re.search(p, low)]


def _clauses(text):
    parts = re.split(r"(?<=[.!?])\s+", text or "")
    out = []
    for p in parts:
        out.extend(re.split(r",\s+|\s+and\s+|\s+but\s+|;\s*", p))
    return [c for c in out if c.strip()]


def _quoted_or_trailing(clause):
    m = re.search(r"[\"“']([^\"”']{2,})[\"”']", clause)
    if m:
        return normalise(m.group(1)).lower().strip(" .")
    m = re.search(r"\byou (?:said|told us|answered|chose|selected|confirmed|indicated)\b(.*)",
                  clause, re.I)
    if not m:
        return None
    tail = normalise(m.group(1)).lower().strip(" .:")
    tail = re.sub(r"^(?:that|it was|it is|the answer was)\s+", "", tail)
    return tail or None


def guardrail(text, context, conversational=False):
    """THE contextual guardrail. Both capabilities call this one function, so a new
    capability cannot ship with half the checks (G-65).

    `context` is an AssessmentContext and it is REQUIRED, not optional — the service
    refuses a request without one rather than proceeding unguarded, because an agent that
    cannot be told what is on record cannot be caught claiming something that is not.
    """
    if not context or "recorded" not in context:
        raise ValueError("guardrail requires an AssessmentContext (G-65)")

    ids = uttered_internal_identifier(text)
    unrecorded = claims_unrecorded_answer(text, context["recorded"])
    recording = claims_work_was_recorded(text) if conversational else []

    problems = []
    if ids:
        problems.append({"check": "uttered_internal_identifier", "found": ids})
    if unrecorded:
        problems.append({"check": "claims_unrecorded_answer", "found": unrecorded})
    if recording:
        problems.append({"check": "claims_work_was_recorded", "found": recording})

    return envelope(
        "passed" if not problems else "refused",
        "No internal identifier reaches a person (NFR-9); no answer is attributed to "
        "somebody who did not give it (G-42)"
        + ("; nothing claims work was recorded or signed (G-65)." if conversational else "."),
        "A refusal produces an error event, never a lower-confidence answer.",
        problems=problems, checked_chars=len(text or ""),
    )


def assessment_context(assessment):
    """What an agent is allowed to know: the activity in the person's own words, what is
    on record as LABEL AND VALUE, and what is still open (G-65).

    Nothing else. Not the whole database, and not another team's assessment.
    """
    answers = answer_map(assessment)
    idx = instrument()
    recorded, open_questions = {}, []
    for qid in visible_questions(answers):
        q = idx["questions"][qid]
        if qid in answers:
            value = answers[qid]
            label = q["options"].get(value) if not isinstance(value, list) else \
                ", ".join(q["options"].get(v, v) for v in value)
            # QUESTION AND ANSWER TOGETHER. The guardrail needs the pair: a value alone
            # cannot be checked, because "No" is recorded somewhere on almost every
            # assessment and would then justify any negative claim about any of it.
            recorded[qid] = {"question": q["text"], "answer": label or value}
        else:
            open_questions.append({"question": q["text"], "id": qid})
    return {
        "assessment_id": assessment["assessment_id"],
        "activity": answers.get("activity_name"),
        "in_their_words": answers.get("activity_description"),
        "recorded": recorded,
        "open": open_questions,
        "stage": assessment.get("stage"),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  3. POLICY AUTHORITY AND BREACH FINDINGS (§22.5, G-67, FR-41)
# ══════════════════════════════════════════════════════════════════════════════
def clauses_for(qid):
    """The policy clauses that require this control question, quoted verbatim.

    The alignment is AUTHORED DATA RATIFIED BY A HUMAN, never something a model decides
    while a page renders — a requester asking "why am I being asked this?" is owed an
    authority, and an authority a model invented is not one (G-67).
    """
    out = []
    for pol in load_policies()["policies"]:
        for c in pol["clauses"]:
            if qid in c["governs"]:
                out.append({"policy": pol["name"], "policy_version": pol["version"],
                            "clause": c["id"], "text": c["text"],
                            "in_force_from": pol["in_force_from"]})
    return out


def clause_coverage():
    """Clauses the pilot asks nothing about — named rather than dropped.

    An obligation with no question is a COVERAGE GAP IN THE INSTRUMENT, which is §22.1
    read backwards and the more useful direction.
    """
    uncovered = []
    for pol in load_policies()["policies"]:
        for c in pol["clauses"]:
            if not c["governs"]:
                uncovered.append({"policy": pol["name"], "clause": c["id"],
                                  "text": c["text"],
                                  "note": c.get("coverage_note", "")})
    return uncovered


def synthesize_findings(assessment):
    """Findings from the Tier-3 answers a person gave (§4.3, G-67, FR-15, FR-41).

    No -> control gap. Partial -> enhancement. A breaching answer on a question a policy
    governs -> NON-COMPLIANCE, which REPLACES the bare gap rather than joining it: one
    fact, one finding, and the richer of the two.

    Narrow about what counts. An UNANSWERED question is never a finding of any kind,
    because silence becoming non-compliance is the mirror image of the mistake never-guess
    exists to stop. An N-A is never a breach, because judging a control out of scope is a
    position a person took and testing it is the reviewer's job.

    Only ACCUMULATED objectives are considered — a finding on a control this assessment
    never accumulated is invisible in the reviewer's queue (G-67).
    """
    answers = answer_map(assessment)
    accumulated = accumulate(answers)
    notes = {a["q"]: a.get("note") for a in assessment.get("answers", [])}
    findings = []

    for oid, obj in accumulated.items():
        value = answers.get(oid)
        if value in (None, "", "yes", "n_a"):
            continue
        if value not in BREACHING:
            continue
        clauses = clauses_for(oid)
        note = notes.get(oid) or ""
        if clauses:
            for c in clauses:
                findings.append({
                    "kind": "non_compliance",
                    "objective": obj["name"], "question": obj["question"],
                    "answer": value, "note": note,
                    "citation": c,
                    "why": 'The clause requires it; the answer recorded is "%s".' % value,
                })
        else:
            findings.append({
                "kind": "control_gap" if value == "no" else "enhancement",
                "objective": obj["name"], "question": obj["question"],
                "answer": value, "note": note, "citation": None,
                "why": "No control exists for a requirement this activity accumulated."
                       if value == "no" else
                       "Something exists but enhancement is needed.",
            })

    return envelope(
        "findings_synthesised",
        "No becomes a control gap, Partial becomes an enhancement, and a breaching answer "
        "on a governed question becomes a non-compliance that REPLACES the bare gap "
        "(§4.3, G-67). Unanswered and N-A are never findings.",
        "Derived from the answers on record. Each resolves only through the four governed "
        "dispositions; none is resolved by rewording it.",
        findings=findings,
        counts={
            "non_compliance": sum(1 for f in findings if f["kind"] == "non_compliance"),
            "control_gap": sum(1 for f in findings if f["kind"] == "control_gap"),
            "enhancement": sum(1 for f in findings if f["kind"] == "enhancement"),
        },
        uncovered_clauses=clause_coverage(),
    )


def open_finding(finding, today):
    """The ONE rule that decides "open" everywhere — packaging, queue, obligations (§4.3).

    Open means unresolved OR accepted-but-expired. Defined once so the packaging gate and
    the reviewer's queue can never disagree about it.
    """
    if not finding.get("resolution"):
        return True
    if finding.get("disposition") == "risk_accepted":
        expiry = finding.get("expires_at")
        return bool(expiry and expiry < today)
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  4. ATTESTATION AUTHORITY (G-60, FR-17)
# ══════════════════════════════════════════════════════════════════════════════
def _article(word):
    """"a IAM control" is the kind of slip that makes a refusal screen look unread."""
    return ("an " if word[:1].upper() in "AEIOU" else "a ") + word


def attestation_authority(qid, assessor):
    """May this assessor attest THIS question? Derived from the question, server-side.

    Authority is derived from the QUESTION BEING SIGNED, never from an objective the
    caller supplied. The first implementation checked the caller's authority against a
    field in the caller's own request, which let a Data-Privacy assessor sign a Security
    control by naming a Privacy one — the check ran, passed, and protected nothing.

    GENERAL RULE: a permission check reading a value the requester chose is not a
    permission check (G-60).
    """
    cfg = load_control_domains()
    q = instrument()["questions"].get(qid)
    if q is None:
        return envelope("refused", "The question does not exist in this instrument version.",
                        "Nothing was attested.", allowed=False,
                        because="That question is not part of this assessment.")

    family = q.get("family") or (instrument()["questions"].get(q.get("parent"), {}) or {}).get("family")
    if family is None:
        return envelope("refused", "Only control questions are attested (§4.2, G-60).",
                        "Nothing was attested.", allowed=False,
                        because="This is not a control question, so no risk area owns it.")

    mapped = cfg["families"].get(family)
    if mapped is None:
        # Fails the build rather than falling through to "anyone may sign" (G-60).
        raise ValueError("control family %r is not mapped to a risk domain" % family)

    if assessor.get("role") == "admin":
        return envelope("permitted", "Administrators are exempt from domain checks (§2).",
                        "Attestation authority confirmed.", allowed=True,
                        because="You are an administrator.", domain=mapped["domain"])

    if assessor.get("role") != "assessor":
        return envelope("refused", "Only a Risk Assessor attests (§2, G-52).",
                        "Nothing was attested.", allowed=False,
                        because="A requester declares their answers accurate; attesting "
                                "them is the assessor's act, and the two are kept "
                                "distinct so four-eyes stays meaningful.")

    domain = assessor.get("risk_domain")
    if domain is None:
        # A generalist covers everything, so a question can never sit in a queue nobody
        # reads (G-60).
        return envelope("permitted", "A generalist assessor covers every risk domain (G-60).",
                        "Attestation authority confirmed.", allowed=True,
                        because="You cover every risk area.", domain=mapped["domain"])

    if domain == mapped["domain"]:
        return envelope("permitted", "Reviewer-group membership matches the control's "
                        "risk domain, derived from its family (G-60).",
                        "Attestation authority confirmed.", allowed=True,
                        because="This is %s control, and %s."
                                % (_article(family), mapped["because"]),
                        domain=mapped["domain"])

    return envelope("refused", "Authority follows control family -> risk domain (G-60).",
                    "Nothing was attested.", allowed=False,
                    domain=mapped["domain"],
                    because="This is %s control, and %s. Yours is a different risk area."
                            % (_article(family), mapped["because"]))


# ══════════════════════════════════════════════════════════════════════════════
#  5. THE REVIEW RUBRIC — ORDERS THE QUEUE AND NOTHING ELSE (G-61, FR-38)
# ══════════════════════════════════════════════════════════════════════════════
def review_band(qid, assessment):
    """A mechanical rubric over WHAT IS ON RECORD — never a model's confidence.

    A model's confidence in its own output is not evidence about the answer, and a number
    a reviewer cannot check is a number that quietly replaces their judgement. Every
    criterion here is a fact the reviewer can verify on the same screen, and each is
    stated in words next to its verdict.
    """
    cfg = load_control_domains()["review_rubric"]
    records = [a for a in assessment.get("answers", []) if a["q"] == qid]
    latest = records[-1] if records else {}
    answers = answer_map(assessment)
    idx = instrument()
    children = [c["id"] for c in (idx["objectives"].get(qid, {}).get("children") or [])]

    facts = {
        "unexplained_non_yes": latest.get("value") in ("partial", "no", "n_a")
                               and not (latest.get("note") or "").strip(),
        "churned": len(records) > 2,
        "yes_without_detail": latest.get("value") == "yes"
                              and bool(children)
                              and any(c not in answers for c in children),
        "handed_off": any(h["question"] == qid for h in assessment.get("handoffs", [])),
        "drafted_with_evidence": latest.get("source") == "draft",
    }
    score = sum(c["weight"] for c in cfg["criteria"] if facts.get(c["id"]))
    band = next(b for b in cfg["bands"] if score >= b["min_score"])

    return envelope(
        band["id"], "Every criterion is a fact on the record, verifiable on the same "
                    "screen (G-61).", cfg["disclaimer"],
        band_label=band["label"], score=score,
        checks=[{"text": c["text"], "fired": bool(facts.get(c["id"]))} for c in cfg["criteria"]],
        gates_nothing=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  6. PRECEDENT — PORTFOLIO MEMORY WITH ITS FOUR RULES (§22.4, G-21)
# ══════════════════════════════════════════════════════════════════════════════
def precedent_for(qid):
    """How comparable assessments answered — aggregate, attested-only, aged, never
    pre-selected. Returns None when the floor is not met.

    Below the minimum comparable count, show NOTHING AT ALL: a precedent drawn from one
    assessment is gossip, not evidence, and it also leaks who (§22.4.2).
    """
    cfg = load_precedent()
    floor = cfg["rules"]["minimum_comparable_count"]
    for row in cfg["aggregates"]:
        if row["question"] != qid:
            continue
        if row.get("_dropped") or row["attested_count"] < floor:
            return None
        idx = instrument()
        labels = idx["questions"].get(qid, {}).get("options", {})
        return envelope(
            "precedent_available",
            "Built only from ATTESTED answers (§22.4.1) and shown as aggregate counts "
            "with recency (§22.4.2, §22.4.4).",
            "This is how others answered, not what you should answer. Nothing is "
            "pre-selected and the click stays yours.",
            comparable_on=row["comparable_on"],
            attested_count=row["attested_count"],
            pattern=[{"answer": labels.get(k, k), "count": v}
                     for k, v in sorted(row["answers"].items(), key=lambda kv: -kv[1])],
            most_recent=row["most_recent"], oldest=row["oldest"],
            never_preselect=True,
        )
    return None


def divergence_for(qid, assessment):
    """A reviewer-side triage signal when this assessment answers materially differently.

    Shown to REVIEWERS, never as a nag to the person answering. A divergence is a triage
    signal, not a verdict — being different is often correct, and the platform must never
    pressure a requester toward the majority (§22.4, G-21).
    """
    p = precedent_for(qid)
    if p is None:
        return None
    value = answer_map(assessment).get(qid)
    if value is None:
        return None
    labels = instrument()["questions"].get(qid, {}).get("options", {})
    mine = labels.get(value, value)
    top = p["pattern"][0]
    if top["answer"] == mine:
        return None
    return envelope(
        "diverges",
        "Compared against attested answers on comparable assessments only (§22.4.1).",
        "A triage signal, not a verdict. Being different is often correct.",
        answered=mine, majority=top["answer"], majority_count=top["count"],
        of_total=p["attested_count"], most_recent=p["most_recent"],
        shown_to="reviewer",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  7. INTAKE SCORING — THREE LAYERS, ONLY ONE IS A MODEL (G-69, FR-43)
# ══════════════════════════════════════════════════════════════════════════════
def intake_floor(text):
    """The heuristic floor. No model call, no cost, and it runs first.

    Catches a product name, a fragment or keyboard noise. Returns the floor hit or None.
    """
    cfg = load_rubric()["floor"]
    t = normalise(text)
    words = [w for w in re.split(r"\s+", t) if w]
    checks = {c["id"]: c for c in cfg["checks"]}

    if not t:
        return _floor(checks["empty"])
    low = t.lower().strip(" .")
    if low in [p.lower() for p in checks["product_name_only"]["known_products"]]:
        return _floor(checks["product_name_only"])
    # Noise is judged BEFORE length, so a long string of keyboard mashing is called what it
    # is rather than called short. Threshold is data, not a magic number here.
    letters = [c for c in low if c.isalpha()]
    if len(letters) >= cfg["min_chars_to_judge_noise"]:
        ratio = sum(1 for c in letters if c in "aeiou") / len(letters)
        if ratio < cfg["min_vowel_ratio"]:
            return _floor(checks["noise"])
    if len(words) < cfg["min_words"] or len(t) < cfg["min_chars"]:
        return _floor(checks["too_short"])
    if not re.search(r"\b(?:is|are|was|were|will|would|can|does|do|use|uses|used|"
                     r"provide|provides|build|builds|run|runs|allow|allows|let|lets|"
                     r"send|sends|store|stores|draft|drafts|process|processes|replace|"
                     r"replaces|automate|automates|generate|generates|introduce|"
                     r"introduces|handle|handles|move|moves|create|creates|take|takes)\b",
                     low):
        return _floor(checks["no_verb"])
    return None


def _floor(check):
    return envelope("floor_hit", "Caught by the local heuristic floor with no model call "
                    "(G-69).", "Nothing is blocked. You can carry on.",
                    check=check["id"], message=check["message"], model_called=False,
                    # Stated on EVERY path out of this function, including this one. The
                    # floor is the layer most likely to feel like a gate, so it is the
                    # layer that most needs to say it is not one.
                    blocks_submission=False, meets_bar=True, asks=[])


def intake_feedback(scores):
    """Turn per-dimension scores into the exact sentence a person reads.

    The model's ENTIRE job is the 0/1/2 per dimension. Everything after — the pass rule
    and the copy — is deterministic and lives in `intake_rubric.json`, so the feedback is
    business copy edited in one place and never composed in code (G-69).

    A score outside the rubric is DROPPED, never clamped: clamping turns nonsense into a
    number somebody then acts on.
    """
    cfg = load_rubric()
    rule = cfg["pass_rule"]
    kept, dropped, asks = {}, [], []

    for dim in cfg["dimensions"]:
        raw = scores.get(dim["id"])
        if not isinstance(raw, int) or isinstance(raw, bool) \
                or raw < 0 or raw > rule["max_score_per_dimension"]:
            dropped.append({"dimension": dim["label"], "received": raw})
            continue
        kept[dim["id"]] = raw
        asks.append({
            "dimension": dim["label"],
            "score": raw,
            "feedback": dim["feedback"][str(raw)],
            # The rubric is VISIBLE TO THE REQUESTER: the anchor it was scored against is
            # shown alongside the ask, so the grade is never a black box (G-69).
            "scored_against": dim["anchors"][str(raw)],
        })

    total = sum(kept.values())
    band = next(b for b in cfg["pass_rule"]["bands"] if total >= b["min_total"])
    passed = total >= rule["pass_total"] and \
        not (rule["pass_requires_no_zero"] and any(v == 0 for v in kept.values()))

    return envelope(
        band["id"],
        "Scores come from the model; the pass rule and every sentence come from "
        "intake_rubric.json (G-69).",
        "This never blocks submission. No agent, a slow agent, a wrong agent, a partial "
        "answer or a thrown error all pass.",
        band_label=band["label"], message=band["message"],
        total=total, of_possible=rule["total_possible"],
        meets_bar=passed, blocks_submission=False,
        asks=[a for a in asks if a["score"] < rule["max_score_per_dimension"]],
        strengths=[a["dimension"] for a in asks if a["score"] == rule["max_score_per_dimension"]],
        dropped_scores=dropped,
        dimensions_scored=len(kept),
    )


def intake_pass_through(reason):
    """What the caller gets when there is no agent, or the agent failed. IT PASSES.

    A quality assistant that blocks submission has become a gate, and the mission is
    reducing friction. A person who wants to write two lines and move on can.
    """
    return envelope("unavailable", "Fail-open is the rule that outranks all of it (G-69).",
                    "No suggestions this time. Nothing is blocked — carry on.",
                    blocks_submission=False, meets_bar=True, asks=[], because=reason)


# ══════════════════════════════════════════════════════════════════════════════
#  8. THE HANDOFF REPORT — A READING OF THE RECORD, NEVER A NEW FACT (G-68, FR-42)
# ══════════════════════════════════════════════════════════════════════════════
def build_handoff_report(assessment):
    """The artifact a Risk Assessor is given. Derived when it is built, stored NOWHERE.

    Every figure on it is read from the record: what applies and why, the severity
    profile, each control with its answer and the clause requiring it, every finding with
    the clause it breaches, and what nobody answered. That is what lets it be shown to a
    leadership audience without a caveat.

    THE PAGE IS COMPLETE WITHOUT AN AGENT. The agent adds exactly two things on top — a
    summary of at most three sentences and two to four scenarios worth asking about — and
    neither is required for this to be a finished report.
    """
    answers = answer_map(assessment)
    idx = instrument()
    active = active_paths(answers)
    accumulated = accumulate(answers, set(active))
    notes = {a["q"]: a.get("note") for a in assessment.get("answers", [])}

    severities = []
    for qid, q in idx["severities"].items():
        if not visible(qid, answers, set(active)):
            continue
        band = severity_of(qid, answers)
        severities.append({"question": q["text"], "band": band,
                           "path": q.get("path"), "always_on": q.get("always_on", False)})

    controls, unanswered = [], []
    for oid, obj in accumulated.items():
        value = answers.get(oid)
        row = {"objective": obj["name"], "family": obj["family"],
               "question": obj["question"], "answer": value,
               "note": notes.get(oid), "required_by": clauses_for(oid),
               "accumulated_because": obj["reasons"]}
        if value is None:
            unanswered.append(row)
        else:
            controls.append(row)

    findings = synthesize_findings(assessment)
    boundaries = [{"area": c["name"], "note": c.get("boundary_note")}
                  for c in idx["categories"].values()
                  if c["pilot_depth"] == "gate_only"
                  and (c.get("always_applies") or answers.get(c["gate"]["id"]) in ("yes", "not_sure"))]

    return envelope(
        "report_derived",
        "Every figure is derived from the record when this is built and stored nowhere "
        "(G-68). A report is a reading of the record, never a new fact.",
        "Complete as it stands. Any agent-written summary or scenario is an addition to "
        "this page, not a part of it.",
        assessment_id=assessment["assessment_id"],
        activity=answers.get("activity_name"),
        in_their_words=answers.get("activity_description"),
        applies=[{"path": p["name"], "because": p["reasons"]} for p in active.values()],
        severity_profile={
            "high": [s["question"] for s in severities if s["band"] == "high"],
            "medium": [s["question"] for s in severities if s["band"] == "medium"],
            "low": [s["question"] for s in severities if s["band"] == "low"],
            "not_established": [s["question"] for s in severities if s["band"] is None],
        },
        controls=controls,
        nobody_answered=unanswered,
        findings=findings["findings"],
        finding_counts=findings["counts"],
        uncovered_clauses=findings["uncovered_clauses"],
        declared_boundaries=boundaries,
        open_handoffs=[{"question": idx["questions"].get(h["question"], {}).get("text"),
                        "to": h.get("to_domain") or h.get("to_person")}
                       for h in assessment.get("handoffs", []) if not h.get("resolved")],
        counts={"paths": len(active), "controls_answered": len(controls),
                "controls_unanswered": len(unanswered),
                "findings": len(findings["findings"])},
    )


def vet_scenarios(scenarios, report, max_sentences=3):
    """Keep only scenarios whose citations are real. A bad one is DROPPED ENTIRELY.

    A scenario is A QUESTION, NEVER A FINDING — §4.4 says a scenario counts only once an
    assessor accepts it, and the returned type carries no field that could record
    acceptance.

    Every scenario must cite the controls or areas it was read from BY THE NAMES THAT
    APPEAR IN THE RECORD. One citing anything else is dropped rather than shown with a
    caveat: it is not a weaker scenario, it is one built on nothing.
    """
    known = {c["objective"] for c in report["controls"]}
    known |= {c["objective"] for c in report["nobody_answered"]}
    known |= {a["path"] for a in report["applies"]}

    kept, dropped = [], []
    for s in scenarios or []:
        cites = s.get("cites") or []
        unknown = [c for c in cites if c not in known]
        if not cites:
            dropped.append({"scenario": s.get("question"), "why": "cited nothing"})
            continue
        if unknown:
            dropped.append({"scenario": s.get("question"),
                            "why": "cited something not in the record: %s" % ", ".join(unknown)})
            continue
        if not (s.get("question") or "").strip():
            dropped.append({"scenario": None, "why": "no question"})
            continue
        kept.append({"question": s["question"], "cites": cites})

    return envelope(
        "scenarios_vetted",
        "A scenario cites the record by the names in it, or it is dropped entirely (G-68).",
        "These are questions worth asking, not findings. A scenario counts only once an "
        "assessor accepts it.",
        scenarios=kept[:4], dropped=dropped,
        enough=len(kept) >= 2, capped_at=4,
    )


def vet_summary(text, context, max_sentences=3):
    """The agent's summary passes the same contextual guardrail as everything else said to
    a person, PLUS a length gate — because three sentences is the brief and four is
    somebody not reading it (G-68).
    """
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", normalise(text)) if s]
    checked = guardrail(text, context)
    too_long = len(sentences) > max_sentences
    ok = checked["decision"] == "passed" and not too_long
    return envelope(
        "accepted" if ok else "rejected",
        "The contextual guardrail (G-65) plus a hard length gate of %d sentences (G-68)."
        % max_sentences,
        "The report is complete without this summary.",
        summary=text if ok else None,
        sentences=len(sentences), too_long=too_long,
        guardrail=checked["problems"],
    )
