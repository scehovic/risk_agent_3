"""The engine's law, asserted. SPEC §19 (subsystem acceptance criteria).

Every test here is a criterion from §19 or an invariant from §5, named so a failure says
which rule broke rather than which function did.
"""
import pytest


# ── §19: positive evidence only ──────────────────────────────────────────────
def test_unanswered_question_satisfies_equals_nothing(engine):
    assert engine.evaluate({"op": "equals", "q": "nope", "value": "yes"}, {}) is False


@pytest.mark.parametrize("op", ["not_equals", "excludes"])
def test_negative_operators_do_not_pass_on_a_missing_answer(engine, op):
    """§3.2.1. If these returned True on silence, a risk area could be waived by omission —
    an unanswered question would prove the absence of the thing it asks about."""
    assert engine.evaluate({"op": op, "q": "nope", "value": "x"}, {}) is False


def test_empty_list_and_empty_string_are_not_answers(engine):
    for empty in ([], ""):
        assert engine.evaluate({"op": "answered", "q": "q"}, {"q": empty}) is False


# ── §19: severity fails closed ───────────────────────────────────────────────
def test_severity_at_least_is_false_against_an_unknown_severity(engine):
    """§3.2.2. Unknown is never treated as Low."""
    cond = {"op": "severity_at_least", "q": "t2_sec_pa_1", "band": "medium"}
    assert engine.evaluate(cond, {}) is False


def test_a_medium_severity_meets_low_and_medium_but_not_high(engine):
    answers = {"t2_sec_pa_1": "medium"}
    at = lambda b: engine.evaluate(
        {"op": "severity_at_least", "q": "t2_sec_pa_1", "band": b}, answers)
    assert at("low") and at("medium") and not at("high")


# ── §19: set membership ──────────────────────────────────────────────────────
def test_a_scalar_answer_satisfies_any_of(engine):
    """§19: a scalar "high" satisfies any_of ["medium","high"]."""
    assert engine.evaluate(
        {"op": "any_of", "q": "q", "values": ["medium", "high"]}, {"q": "high"}) is True


def test_nesting(engine):
    a = {"x": "yes", "y": ["b"]}
    assert engine.evaluate({"all": [{"op": "equals", "q": "x", "value": "yes"},
                                    {"op": "includes", "q": "y", "value": "b"}]}, a)
    assert engine.evaluate({"any": [{"op": "equals", "q": "x", "value": "no"},
                                    {"op": "includes", "q": "y", "value": "b"}]}, a)
    assert engine.evaluate({"not": {"op": "equals", "q": "x", "value": "no"}}, a)


# ── §19: explainability, and no identifiers anywhere near a person ───────────
def test_a_condition_renders_as_one_english_sentence(engine):
    s = engine.explain({"op": "includes", "q": "t1_tpr_1", "value": "hosts_data"})
    assert s.count(".") == 1 and s.endswith(".")
    assert "Hosts or stores our data" in s
    assert "t1_tpr_1" not in s and "hosts_data" not in s


def test_no_activation_reason_in_the_whole_instrument_leaks_an_identifier(engine):
    """NFR-9. Checked over every authored reason, not a sample — this is the string that
    reaches a requester's screen."""
    idx = engine.instrument()
    reasons = [r["reason"] for p in idx["paths"].values() for r in p["activated_by"]]
    reasons += [r["reason"] for o in idx["objectives"].values() for r in o["accumulated_by"]]
    for text in reasons:
        assert "_" not in text.replace("non-", ""), text
        assert not any(text.startswith(p) for p in ("t1", "t2", "t3")), text


# ── §19: routing, union with provenance ──────────────────────────────────────
def test_two_satisfied_rules_give_one_path_with_both_reasons(engine):
    """§19: given two satisfied activation rules for one path, the path is active with
    BOTH reasons retained."""
    answers = {"t1_tpr_1": ["accesses_systems"], "t1_sec_2": ["vendor_staff"]}
    paths = engine.active_paths(answers)
    assert len(paths["TPR_LA"]["reasons"]) == 2


def test_gate_no_hides_every_question_in_the_category(engine, answers):
    closed = dict(answers, t1_tpr_gate="no")
    for qid in ("t1_tpr_1", "t1_tpr_2"):
        assert engine.visible(qid, closed) is False


def test_changing_an_upstream_answer_re_derives_without_deleting_history(engine, answers):
    """§19 + §3.2.7. The orphaned answer is still IN the record; it has just left the
    funnel. That distinction is what lets history always render.

    Uses a single-trigger path deliberately. On a path with two satisfied triggers, removing
    one leaves it active with one fewer reason rather than deactivating it — asserted
    separately below, because conflating the two would let a real regression hide."""
    before = engine.active_paths(answers)
    after = engine.active_paths(dict(answers, t1_sec_1=["internal_only"]))
    assert "SEC_IE" in before and "SEC_IE" not in after
    assert answers["t1_sec_1"] == ["public_internet"]


def test_removing_one_of_two_triggers_drops_a_reason_not_the_path(engine, answers):
    """§3.2.4. Union semantics cut both ways: PRIV_XB is lit by the transfer answer AND by
    offshore delivery, so answering No to one keeps the path with the other's reason."""
    before = engine.active_paths(answers)["PRIV_XB"]
    after = engine.active_paths(dict(answers, t1_priv_3="no"))["PRIV_XB"]
    assert len(before["reasons"]) == 2 and len(after["reasons"]) == 1


def test_every_surface_agrees_with_the_one_predicate(engine, answers):
    """§19 + NFR-2. The ledger, the visible-question list and accumulation are all read
    through `visible`; if they disagreed, a question would be in the funnel on one screen
    and absent on another."""
    visible = set(engine.visible_questions(answers))
    ledger = engine.ledger(answers)
    assert set(ledger["severities"]) <= visible
    assert {o["id"] for o in ledger["objectives"]} <= visible


# ── §19: accumulation ────────────────────────────────────────────────────────
def test_medium_accumulates_min_low_and_min_medium_but_not_min_high(engine):
    """§19, stated over the real instrument: a Medium severity fires thresholds at Low and
    Medium and leaves High alone."""
    base = {"t1_sec_gate": "yes", "t1_sec_2": ["vendor_staff"]}
    med = engine.accumulate(dict(base, t2_sec_pa_1="medium"))
    high = engine.accumulate(dict(base, t2_sec_pa_1="high"))
    assert "t3_iam_02" in med           # min medium — fires
    assert "t3_dp_04" not in med        # requires a High elsewhere — does not
    assert "t3_iam_02" in high


def test_a_capture_answer_never_changes_a_severity_band(engine, answers):
    """§19 as CORRECTED by G-57. The rule is narrower than it was first written: a capture
    answer changes no severity band, so it moves nothing that a threshold reads. It may
    still add objectives of its own — that is accumulation, not scoring."""
    idx = engine.instrument()
    capture = [c for c in idx["conditionals"].values() if c.get("capture")]
    assert capture, "the instrument should exercise at least one capture question"
    for c in capture:
        for band in ("low", "high"):
            changed = dict(answers, **{c["id"]: "anything"})
            for qid in idx["severities"]:
                assert engine.severity_of(qid, changed) == engine.severity_of(qid, answers)


def test_every_accumulated_objective_carries_a_reason(engine, answers):
    for obj in engine.accumulate(answers).values():
        assert obj["reasons"], obj["id"]


# ── §3.4: children ───────────────────────────────────────────────────────────
def test_a_child_never_fires_unless_the_parent_is_yes(engine, answers):
    assert engine.visible("t3_log_03_c1", answers) is True            # parent is Yes
    assert engine.visible("t3_log_03_c1", dict(answers, t3_log_03="no")) is False


def test_a_child_with_an_unmet_cross_tier_condition_is_invisible_not_skipped(engine, answers):
    """§3.4. Suppressed children are INVISIBLE. The seeded record selects offshore
    delivery, so this one shows; remove that selection and it disappears entirely."""
    assert engine.visible("t3_tp_01_c1", answers) is True
    without = dict(answers, t1_tpr_1=["hosts_data", "accesses_systems"])
    assert engine.visible("t3_tp_01_c1", without) is False


def test_a_child_of_a_partial_parent_never_fires(engine, answers):
    """§3.4. Children reveal on Yes and only Yes. Detail under a Partial lives in the note
    the person had to write, which is why that note is required."""
    assert answers["t3_tp_03"] == "partial"
    assert engine.visible("t3_tp_03_c1", answers) is False
    assert engine.visible("t3_tp_03_c2", answers) is False


# ── FR-7: derived severity ───────────────────────────────────────────────────
def test_a_band_derived_from_a_fact_routes_like_any_other(engine):
    assert engine.severity_of("t2_priv_pi_2", {"t2_priv_pi_2": "under_100"}) == "low"
    assert engine.severity_of("t2_priv_pi_2", {"t2_priv_pi_2": "over_1m"}) == "high"
    assert engine.severity_of("t2_priv_pi_2", {}) is None
    assert engine.derived_severity_reason("t2_priv_pi_2")


# ── FR-8: all four conditional kinds ─────────────────────────────────────────
def test_all_four_conditional_kinds_exist_and_each_gates_correctly(engine, answers):
    kinds = {c["kind"] for c in engine.instrument()["conditionals"].values()}
    assert kinds == {"severity_fired", "always_fired", "cross_tier", "nested"}

    assert engine.visible("t2c_sec_pa_2", answers)                       # severity_fired
    assert not engine.visible("t2c_sec_pa_2", dict(answers, t2_sec_pa_1="low"))
    assert engine.visible("t2c_priv_xb_2", answers)                      # always_fired
    assert engine.visible("t2c_tpr_la_3", answers)                       # nested
    assert not engine.visible("t2c_tpr_la_3",
                              dict(answers, t2c_tpr_la_2="automatic"))   # sibling unmet
    assert not engine.visible("t2c_priv_sc_2", answers)                  # cross_tier unmet


# ── FR-22: a gate pre-answered from intake ───────────────────────────────────
def test_a_gate_is_suggested_from_intake_with_its_reason_and_never_preselected(engine):
    """FR-22 + G-39a. The suggestion exists; it is not the answer. A pre-selected answer
    nobody looked at becomes that person's attributed answer, which is the failure the
    platform exists to prevent."""
    gates = engine.settled_gates({"uses_ai": "yes"})
    aim = gates["aim"]
    assert aim["answer"] is None
    assert aim["suggested"] == "yes"
    assert "you told us this activity uses ai" in aim["suggested_because"].lower()
    assert aim["open"] is False        # suggested is NOT answered


def test_an_always_applies_area_is_stated_not_asked(engine, answers):
    """G-36. Shown as applying, excluded from what is left for the person to do, and
    deliberately not a pre-fill — a pre-fill invites correction and this is not the
    requester's to correct."""
    gov = engine.settled_gates(answers)["gov"]
    assert gov["open"] is True and gov["asked"] is False
    assert engine.visible("t1_gov_gate", answers) is False


# ── §5.3: the ONE matcher ────────────────────────────────────────────────────
def test_the_matcher_normalises_whitespace_and_nothing_else(engine):
    src = "Encryption keys are held in a managed\n  hardware security module."
    assert engine.verbatim_match("keys are held in a managed hardware security module", src)
    assert not engine.verbatim_match("keys are stored in an HSM", src)
    assert not engine.verbatim_match("KEYS ARE HELD", src)      # case is not normalised
    assert not engine.verbatim_match("", src)


# ── §8: the coherence lint, over the real instrument ─────────────────────────
def test_the_authored_instrument_is_coherent(engine):
    lint = engine.lint_instrument()
    assert lint["problems"] == [], lint["problems"]


def test_the_instrument_is_the_real_one_at_pilot_depth(engine):
    """§16: the demo profile is the real instrument, not a cut-down one. G-50 sets the
    pilot depth, and these are the numbers it names."""
    c = engine.lint_instrument()["counted"]
    assert c == {"questions": 129, "paths": 21, "severity_questions": 26,
                 "objectives": 51, "categories": 11}


def test_no_activation_or_accumulation_rule_fires_on_silence(engine):
    """The lint enforces this; asserted separately because it is the invariant, and a lint
    can be edited by the same change that breaks the rule."""
    idx = engine.instrument()
    empty_paths = engine.active_paths({})
    assert empty_paths == {}, "nothing may activate from an empty record"
    empty_objectives = {k: v for k, v in engine.accumulate({}).items()}
    for oid, obj in empty_objectives.items():
        conds = [r["condition"] for r in idx["objectives"][oid]["accumulated_by"]]
        assert any(c.get("op") == "always" for c in conds), \
            "%s accumulated from an empty record without an `always` rule" % oid


# ── ADR-5: the envelope ──────────────────────────────────────────────────────
def test_every_engine_return_carries_the_explainability_envelope(engine, answers):
    for result in (engine.ledger(answers), engine.lint_instrument()):
        assert set(result) >= {"decision", "binding_rule", "disclosure"}
        assert result["disclosure"]


def test_an_unconfirmed_draft_is_invisible_to_routing(engine, assessment):
    """G-66. A proposal counts as an answer nowhere — including in the engine. Routing must
    never move because something was merely suggested to somebody."""
    record = dict(assessment)
    record["answers"] = list(assessment["answers"]) + [
        {"q": "t1_priv_3", "value": "no", "source": "draft", "confirmed": False}]
    assert engine.answer_map(record)["t1_priv_3"] == "yes"
