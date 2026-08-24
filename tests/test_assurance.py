"""The gates and guardrails, proved to FIRE.

THE RULE THIS FILE EXISTS FOR (G-65)
    A guardrail is not shipped when it is written, it is shipped when something proves it
    fires. The specification once claimed these checks ran while the drafting gate imported
    the function and never called it — the import passed the type checker because nothing
    forbids an unused one.

    So every test below names THE EXACT SENTENCE it exists to stop. A guardrail is written
    against a named failure, not against a category.

Every reply used here is FABRICATED, deliberately. A model behaving well proves nothing
about what happens when it does not (G-64).
"""
import pytest

REAL_QUOTE = "Encryption keys are held in a managed hardware security module operated by Meridian"


@pytest.fixture
def sources(engine):
    return {"doc.1": engine.load_document_text()}


def _draft(**kw):
    base = {"basis": "stated", "value": "yes", "because": "The overview says so.",
            "quote": REAL_QUOTE, "source_id": "doc.1"}
    base.update(kw)
    return base


# ══ 1. THE NEVER-GUESS GATE (§5.2, G-63, G-64) ═══════════════════════════════
def test_a_valid_stated_draft_passes(assurance, sources):
    assert assurance.violates_never_guess(_draft(), sources) is None


def test_a_paraphrase_is_refused(assurance, sources):
    """"Meridian keeps keys in an HSM" — true, tidier, and not what the document says."""
    v = assurance.violates_never_guess(
        _draft(quote="Meridian keeps keys in an HSM"), sources)
    assert v and "verbatim" in v


def test_a_stitched_quote_is_refused(assurance, sources, engine):
    """Two REAL fragments that never appeared together. The most dangerous failure of the
    lot, because every word of it is genuinely in the source."""
    stitched = ("Encryption keys are held in a managed hardware security module "
                "rotated automatically every ninety days")
    flat = engine.normalise(sources["doc.1"])   # the document wraps; the matcher normalises
    assert "Encryption keys are held in a managed hardware security module" in flat
    assert "rotated automatically every ninety days" in flat
    v = assurance.violates_never_guess(_draft(quote=stitched), sources)
    assert v and "verbatim" in v


def test_a_citation_to_a_source_never_supplied_is_refused(assurance, sources):
    v = assurance.violates_never_guess(_draft(source_id="doc.99"), sources)
    assert v and "never supplied" in v


def test_an_abstention_carrying_an_answer_is_refused(assurance, sources):
    v = assurance.violates_never_guess(
        {"basis": "not_stated", "value": "yes", "because": "nothing found"}, sources)
    assert v and "abstention may not carry an answer" in v


def test_an_inference_with_nothing_to_point_at_is_refused(assurance, sources):
    """"This follows in one step" is not evidence. An inference with nothing to point at is
    a guess, and the rule says so in the sentence a person reads (G-63)."""
    v = assurance.violates_never_guess(
        {"basis": "inferred", "value": "yes", "because": "seems likely", "quote": ""},
        sources)
    assert v and "verbatim quote" in v


def test_a_draft_that_does_not_say_why_is_refused(assurance, sources):
    v = assurance.violates_never_guess(_draft(because=""), sources)
    assert v and "must say why" in v


def test_a_draft_can_never_arrive_confirmed(assurance, sources):
    """G-66, and a schema CHECK in the real product. Only a person confirms."""
    v = assurance.violates_never_guess(_draft(confirmed=True), sources)
    assert v and "confirmed" in v


def test_evidence_may_not_ride_on_a_persons_own_answer(assurance, sources):
    """G-66. A person's answer is grounded in the fact that they gave it; attaching a
    document quote to it would make their own words look like they needed corroborating."""
    v = assurance.violates_never_guess(_draft(source="person"), sources)
    assert v and "own answer" in v


def test_an_unknown_basis_is_refused(assurance, sources):
    assert assurance.violates_never_guess(_draft(basis="probably"), sources)


def test_abstention_is_a_correct_outcome_and_passes(assurance, sources):
    """§5.2: abstention is a correct, SCOREABLE outcome — not a failure to be retried."""
    assert assurance.violates_never_guess({
        "basis": "not_stated", "value": None,
        "because": "I looked for anything about capacity or performance monitoring and the "
                   "overview does not mention it."}, sources) is None


def test_a_refusal_is_never_downgraded_into_a_lower_confidence_answer(tools):
    """G-64. A refusal produces an error event. There is no 'probably yes' path out of the
    gate, because a lower-confidence answer is still an answer in the record."""
    out = tools.risk_draft_verify({"draft": _draft(quote="not in the document at all")})
    assert out["decision"] == "refused"
    assert out["recorded"] is False
    assert "value" not in out or out.get("value") is None


# ══ 2. THE CONTEXTUAL GUARDRAIL (G-65) ═══════════════════════════════════════
def test_the_guardrail_refuses_a_request_without_a_context(assurance):
    """It is REQUIRED, not optional. An agent that cannot be told what is on record cannot
    be caught claiming something that is not."""
    with pytest.raises(ValueError, match="AssessmentContext"):
        assurance.guardrail("anything at all", None)


@pytest.mark.parametrize("text,token", [
    ("You still need to answer t3_iam_02 before you submit.", "t3_iam_02"),
    ("I have asked p.requester to look at this.", "p.requester"),
    ("I have asked p.okonkwo to look at this.", "p.okonkwo"),
    ("This is being asked because TPR_LA applies.", "TPR_LA"),
    ("See record 3f2a1b4c-5d6e-7f80-91a2-b3c4d5e6f708 for detail.", "uuid"),
    ("Your assessment ASM-2026-0417 is in draft.", "ASM-2026-0417"),
    ("The vendor is recorded as v.meridian.", "v.meridian"),
])
def test_every_identifier_form_the_verifier_reported_as_missed_is_now_caught(
        assurance, context, text, token):
    """G-65 names each of these. `p.requester`, path codes, upper-cased ids and uuids all
    slipped through the first implementation, whose own docstring claimed to catch them."""
    r = assurance.guardrail(text, context)
    assert r["decision"] == "refused", token
    assert any(p["check"] == "uttered_internal_identifier" for p in r["problems"])


def test_one_true_clause_does_not_launder_a_false_claim_beside_it(assurance, context):
    """THE laundering failure, verbatim from G-65: "You said Yes to AI, and you said the
    data is Restricted" passed on the strength of "Yes". The record says Confidential."""
    r = assurance.guardrail(
        "You said Yes to AI, and you said the data is Restricted.", context)
    assert r["decision"] == "refused"
    problems = [p for p in r["problems"] if p["check"] == "claims_unrecorded_answer"]
    assert problems and "Restricted" in str(problems)


def test_attributing_an_answer_nobody_gave_is_refused(assurance, context):
    """The busy-person failure: a recap that reads as confirmation, so they stop reading."""
    r = assurance.guardrail("You told us there is no third party involved.", context)
    assert r["decision"] == "refused"


def test_a_true_attribution_passes(assurance, context):
    r = assurance.guardrail("You said the most sensitive data involved is Confidential.",
                            context)
    assert r["decision"] == "passed", r["problems"]


@pytest.mark.parametrize("text", [
    "Great - I have saved that for you.",
    "Your answer has been recorded.",
    "That's now submitted.",
    "I've attested that on your behalf.",
])
def test_the_conversational_gate_refuses_any_claim_that_work_was_recorded(
        assurance, context, text):
    """The narrower conversational check (G-65). Holding a thought partner to the verbatim
    standard would make it impossible; what it DOES enforce is the claim that would
    actually cause harm — that work was recorded, saved, submitted or signed."""
    r = assurance.guardrail(text, context, conversational=True)
    assert r["decision"] == "refused"
    assert any(p["check"] == "claims_work_was_recorded" for p in r["problems"])


def test_a_clean_reply_passes_both_gates(assurance, context):
    text = ("Four control questions are still open, including one about how long logs are "
            "kept. Answering those would let this go to a reviewer.")
    assert assurance.guardrail(text, context, conversational=True)["decision"] == "passed"


def test_the_drafting_path_actually_calls_the_guardrail(tools, engine):
    """THE REGRESSION TEST FOR G-65's OWN CORRECTION. The gate imported this function and
    never called it, so a drafted answer's `because` went unchecked while the specification
    said otherwise. If someone removes the call, this fails."""
    out = tools.risk_draft_verify({"draft": _draft(
        because="I checked t3_dp_04 and the answer is there.")})
    assert out["decision"] == "refused"
    assert "guardrail" in out


# ══ 3. FINDINGS (§4.3, G-67) ═════════════════════════════════════════════════
def test_no_becomes_a_control_gap_and_partial_an_enhancement(assurance, assessment):
    f = assurance.synthesize_findings(assessment)
    kinds = {(x["objective"], x["kind"]) for x in f["findings"]}
    assert ("Third-party access through a controlled gateway", "control_gap") in kinds
    assert ("Leaver deprovisioning", "enhancement") in kinds


def test_a_breach_replaces_the_bare_gap_rather_than_joining_it(assurance, assessment):
    """G-67: one fact, one finding, and the richer of the two."""
    f = assurance.synthesize_findings(assessment)
    for name in ("Unique named accounts", "Privileged credentials vaulted"):
        kinds = [x["kind"] for x in f["findings"] if x["objective"] == name]
        assert kinds == ["non_compliance"], (name, kinds)


def test_every_non_compliance_carries_the_clause_it_breaches(assurance, assessment):
    """The schema CHECK in the real product: the citation is present exactly when the kind
    is a non-compliance, so a gap cannot claim an authority it does not have and a breach
    cannot hide the clause it breaches."""
    for f in assurance.synthesize_findings(assessment)["findings"]:
        if f["kind"] == "non_compliance":
            assert f["citation"] and f["citation"]["text"] and f["citation"]["clause"]
        else:
            assert f["citation"] is None


def test_an_unanswered_question_is_never_a_finding(assurance, assessment, engine):
    """G-67. Silence becoming non-compliance is the mirror image of the mistake never-guess
    exists to stop."""
    unanswered = set(assessment["_deliberately_unanswered"]["questions"])
    accumulated = engine.accumulate(engine.answer_map(assessment))
    assert unanswered <= set(accumulated), "these must be accumulated to be a real test"
    names = {engine.instrument()["objectives"][q]["name"] for q in unanswered}
    found = {f["objective"] for f in assurance.synthesize_findings(assessment)["findings"]}
    assert not (names & found)


def test_an_n_a_is_never_a_breach(assurance, assessment, engine):
    """G-67. Judging a control out of scope is a position a person took; testing it is the
    reviewer's job, not the platform's to pre-empt."""
    assert engine.answer_map(assessment)["t3_sdlc_03"] == "n_a"
    found = {f["objective"] for f in assurance.synthesize_findings(assessment)["findings"]}
    assert "Dependency and secret scanning" not in found


def test_a_clause_the_pilot_asks_nothing_about_is_named_not_dropped(assurance):
    """§22.1 read backwards, and the more useful direction: an obligation with no question
    is a coverage gap in the instrument."""
    uncovered = assurance.clause_coverage()
    assert [c["clause"] for c in uncovered] == ["DP-8.5"]
    assert uncovered[0]["note"]


def test_findings_only_arise_on_accumulated_objectives(assurance, assessment, engine):
    """G-67, found while seeding: a finding on a control this assessment never accumulated
    is invisible in the reviewer's queue."""
    accumulated = {o["name"] for o in engine.accumulate(engine.answer_map(assessment)).values()}
    for f in assurance.synthesize_findings(assessment)["findings"]:
        assert f["objective"] in accumulated


def test_open_means_unresolved_or_accepted_but_expired(assurance):
    """§4.3: ONE rule decides open everywhere."""
    assert assurance.open_finding({}, "2026-08-24") is True
    assert assurance.open_finding({"resolution": "fixed", "disposition": "answer_corrected"},
                                  "2026-08-24") is False
    expired = {"resolution": "accepted", "disposition": "risk_accepted",
               "expires_at": "2026-01-01"}
    assert assurance.open_finding(expired, "2026-08-24") is True
    live = dict(expired, expires_at="2027-01-01")
    assert assurance.open_finding(live, "2026-08-24") is False


# ══ 4. ATTESTATION AUTHORITY (G-60) ══════════════════════════════════════════
def test_authority_is_derived_from_the_question_not_from_the_callers_own_field(assurance):
    """G-60's amendment, and the general rule it earned: A PERMISSION CHECK READING A VALUE
    THE REQUESTER CHOSE IS NOT A PERMISSION CHECK. A privacy assessor may not sign a
    security control, and there is no argument they can pass in that changes it."""
    privacy = {"role": "assessor", "risk_domain": "privacy"}
    r = assurance.attestation_authority("t3_iam_02", privacy)
    assert r["allowed"] is False and r["because"]
    assert assurance.attestation_authority("t3_priv_03", privacy)["allowed"] is True


def test_a_refusal_says_why(assurance):
    """A person told "not yours" is owed the reason."""
    r = assurance.attestation_authority("t3_iam_02",
                                        {"role": "assessor", "risk_domain": "privacy"})
    assert "IAM" in r["because"] and "security office" in r["because"]


def test_a_generalist_covers_everything_so_nothing_sits_unread(assurance, engine):
    generalist = {"role": "assessor", "risk_domain": None}
    for oid in engine.instrument()["objectives"]:
        assert assurance.attestation_authority(oid, generalist)["allowed"] is True


def test_a_requester_can_never_attest(assurance):
    """§2 and G-52: the roles table stands. A requester DECLARES; an assessor ATTESTS."""
    r = assurance.attestation_authority("t3_iam_02", {"role": "requester"})
    assert r["allowed"] is False and "declare" in r["because"]


def test_every_control_family_is_mapped_or_the_build_fails(assurance, engine):
    """G-60: an unmapped family must fail rather than fall through to "anyone may sign"."""
    mapped = set(assurance.load_control_domains()["families"])
    used = {o["family"] for o in engine.instrument()["objectives"].values()}
    assert used <= mapped, used - mapped


# ══ 5. THE REVIEW RUBRIC — ORDERS, NEVER GATES (G-61) ════════════════════════
def test_the_band_orders_the_queue_and_does_nothing_else(assurance, assessment):
    r = assurance.review_band("t3_iam_01", assessment)
    assert r["gates_nothing"] is True
    assert "does not gate" in r["disclosure"]
    assert all("text" in c and "fired" in c for c in r["checks"])


def test_an_unexplained_non_yes_raises_the_band(assurance, assessment):
    """Every criterion is a fact the reviewer can verify on the same screen — never a
    model's confidence in its own output (G-61)."""
    record = dict(assessment)
    record["answers"] = [a for a in assessment["answers"] if a["q"] != "t3_iam_01"] + [
        {"q": "t3_iam_01", "value": "no", "source": "person", "confirmed": True}]
    explained = assurance.review_band("t3_iam_01", assessment)["score"]
    assert assurance.review_band("t3_iam_01", record)["score"] > explained


# ══ 6. PRECEDENT — THE FOUR RULES (§22.4) ════════════════════════════════════
def test_precedent_below_the_comparable_floor_shows_nothing_at_all(assurance):
    """§22.4.2. A precedent drawn from too few assessments is gossip, not evidence, and it
    also leaks who."""
    assert assurance.precedent_for("t3_dp_04") is None


def test_precedent_is_aggregate_carries_age_and_is_never_preselected(assurance):
    p = assurance.precedent_for("t3_iam_01")
    assert p["never_preselect"] is True
    assert p["most_recent"] and p["oldest"] and p["attested_count"] >= 5
    assert "not what you should answer" in p["disclosure"]
    blob = str(p)
    for leak in ("Meridian", "Okonkwo", "ASM-", "Retail Operations"):
        assert leak not in blob


def test_divergence_is_a_reviewer_signal_and_never_a_verdict(assurance, assessment):
    """§22.4 / G-21. Being different is often correct, and the platform must never pressure
    a requester toward the majority."""
    d = assurance.divergence_for("t3_iam_01", assessment)
    assert d and d["shown_to"] == "reviewer"
    assert "not a verdict" in d["disclosure"]
    assert assurance.divergence_for("t3_tp_01", assessment) is None   # agrees with majority


# ══ 7. INTAKE SCORING (G-69) ═════════════════════════════════════════════════
@pytest.mark.parametrize("text,check", [
    ("", "empty"),
    ("Salesforce", "product_name_only"),
    ("ServiceNow", "product_name_only"),
    ("new crm thing", "too_short"),
    ("asdkjhasd kjhasd kjh asdkjh asdkjh", "noise"),
])
def test_the_floor_catches_these_with_no_model_call(assurance, text, check):
    r = assurance.intake_floor(text)
    assert r is not None and r["check"] == check
    assert r["model_called"] is False


def test_a_real_description_passes_the_floor_and_reaches_the_model(assurance, answers):
    assert assurance.intake_floor(answers["activity_description"]) is None


def test_a_score_outside_the_rubric_is_dropped_never_clamped(assurance):
    """G-69. Clamping turns nonsense into a number somebody then acts on."""
    r = assurance.intake_feedback({"specificity": 7, "scope": -1, "data_handling": 2,
                                   "dependencies": "two", "outcomes": 2})
    assert r["dimensions_scored"] == 2 and r["total"] == 4
    assert {d["received"] for d in r["dropped_scores"]} == {7, -1, "two"}


def test_the_sentence_a_person_reads_comes_from_the_rubric_file_not_from_code(assurance):
    r = assurance.intake_feedback({"specificity": 2, "scope": 1, "data_handling": 0,
                                   "dependencies": 1, "outcomes": 2})
    rubric = assurance.load_rubric()
    authored = {d["feedback"][s] for d in rubric["dimensions"] for s in ("0", "1", "2")}
    for ask in r["asks"]:
        assert ask["feedback"] in authored
        assert ask["scored_against"]        # the anchor is shown: no black-box grade


@pytest.mark.parametrize("scores", [
    {"specificity": 0, "scope": 0, "data_handling": 0, "dependencies": 0, "outcomes": 0},
    {"specificity": 2, "scope": 2, "data_handling": 2, "dependencies": 2, "outcomes": 2},
    {},
    {"specificity": "nonsense"},
])
def test_nothing_the_scorer_returns_can_ever_block_submission(assurance, scores):
    """THE rule that outranks all of it. Including a total of zero."""
    assert assurance.intake_feedback(scores)["blocks_submission"] is False


def test_with_no_agent_at_all_it_passes(assurance):
    r = assurance.intake_pass_through("no agent connected")
    assert r["blocks_submission"] is False and r["meets_bar"] is True


# ══ 8. THE HANDOFF REPORT (G-68) ═════════════════════════════════════════════
def test_the_report_is_complete_with_no_agent(assurance, assessment):
    r = assurance.build_handoff_report(assessment)
    for key in ("applies", "severity_profile", "controls", "nobody_answered", "findings",
                "declared_boundaries"):
        assert r[key] or key == "declared_boundaries"
    assert "agent_summary" not in r and "agent_scenarios" not in r


def test_every_figure_on_the_report_is_derived_and_stored_nowhere(assurance, assessment):
    """G-68. This is what lets it be shown to a leadership audience without a caveat."""
    a = assurance.build_handoff_report(assessment)
    b = assurance.build_handoff_report(assessment)
    assert a["counts"] == b["counts"]
    assert "derived" in a["binding_rule"]


def test_the_report_names_what_nobody_answered(assurance, assessment):
    r = assurance.build_handoff_report(assessment)
    assert len(r["nobody_answered"]) == 4
    assert all(c["answer"] is None for c in r["nobody_answered"])


def test_each_control_carries_the_clause_requiring_it(assurance, assessment):
    r = assurance.build_handoff_report(assessment)
    governed = [c for c in r["controls"] if c["required_by"]]
    assert governed
    for c in governed:
        assert all(x["text"] and x["clause"] and x["policy_version"] for x in c["required_by"])


def test_a_scenario_citing_something_not_in_the_record_is_dropped_entirely(
        assurance, assessment):
    """G-68. Not shown with a caveat — dropped. It is not a weaker scenario, it is one
    built on nothing."""
    report = assurance.build_handoff_report(assessment)
    r = assurance.vet_scenarios([
        {"question": "Could a shared vendor account be used without anyone knowing which "
                     "engineer used it?", "cites": ["Unique named accounts"]},
        {"question": "Made up.", "cites": ["Quantum Firewall Hardening"]},
        {"question": "Cites nothing.", "cites": []},
    ], report)
    assert [s["question"][:9] for s in r["scenarios"]] == ["Could a s"]
    assert len(r["dropped"]) == 2


def test_a_scenario_carries_no_field_that_could_record_acceptance(assurance, assessment):
    """§4.4: a scenario counts only once an assessor accepts it, so the TYPE cannot express
    acceptance. If it could, something would eventually set it."""
    report = assurance.build_handoff_report(assessment)
    r = assurance.vet_scenarios([{"question": "Q?", "cites": ["Unique named accounts"],
                                  "accepted": True, "accepted_by": "p.novak"}], report)
    assert set(r["scenarios"][0]) == {"question", "cites"}


def test_a_summary_of_four_sentences_is_rejected(assurance, assessment, context):
    """Three sentences is the brief and four is somebody not reading it (G-68)."""
    long = "One. Two. Three. Four."
    r = assurance.vet_summary(long, context)
    assert r["decision"] == "rejected" and r["too_long"] is True and r["summary"] is None


def test_a_summary_passes_the_same_guardrail_as_everything_else(assurance, context):
    r = assurance.vet_summary("You said the data is Restricted.", context)
    assert r["decision"] == "rejected" and r["guardrail"]


def test_a_good_summary_is_accepted(assurance, context):
    r = assurance.vet_summary(
        "A vendor drafts customer replies using account history. The risk concentrates in "
        "third-party privileged access and in model transparency. Look at the shared "
        "vendor account first.", context)
    assert r["decision"] == "accepted" and r["sentences"] == 3
