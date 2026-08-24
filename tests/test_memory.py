"""AgentCore Memory: the strategies, and the rules that fence the precedent namespace.

No AWS. `configured()` is False without a memory id, so every write and read no-ops — which
is itself the behaviour worth asserting, because a memory failure must never break a reply.

WHAT THIS FILE IS REALLY FOR
    Two mistakes in wiring AgentCore Memory produce no error at all: writing through the
    wrong call, and provisioning a resource with ZERO extraction strategies. Either way
    nothing is ever stored and every read comes back empty. These tests pin both halves.
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))


@pytest.fixture(scope="module")
def memory():
    import memory as mod
    return mod


@pytest.fixture(scope="module")
def rules():
    import assurance
    return assurance.load_precedent()["rules"]


# ── the three strategies ─────────────────────────────────────────────────────
def test_three_long_term_strategies_are_defined(memory):
    kinds = [list(s)[0] for s in memory.strategies()]
    assert kinds == ["summaryMemoryStrategy", "semanticMemoryStrategy",
                     "customMemoryStrategy"]


def test_every_strategy_declares_a_namespace_and_a_description(memory):
    for s in memory.strategies():
        body = list(s.values())[0]
        assert body["namespaces"], body["name"]
        assert len(body["description"]) > 40, body["name"]


def test_assessment_scoped_namespaces_are_scoped_by_session(memory):
    """Nothing in these may cross to another assessment."""
    assert "{sessionId}" in memory.SUMMARY_NAMESPACE
    assert "{sessionId}" in memory.SEMANTIC_NAMESPACE


def test_precedent_is_the_only_cross_assessment_namespace(memory):
    """And it carries no session variable, because it holds no individual's content."""
    assert "{sessionId}" not in memory.PRECEDENT_NAMESPACE
    cross = [s for s in memory.strategies()
             if memory.PRECEDENT_NAMESPACE in list(s.values())[0]["namespaces"]]
    assert len(cross) == 1


def test_the_custom_strategy_forbids_recording_individual_content(memory):
    """The extraction prompt is the one place a model decides what becomes long-term
    memory, so it states its own boundary."""
    custom = [s for s in memory.strategies() if "customMemoryStrategy" in s][0]
    prompt = custom["customMemoryStrategy"]["configuration"]["semanticOverride"]["extraction"]["appendToPrompt"]
    for forbidden in ("project name", "owner", "Never infer"):
        assert forbidden in prompt


# ── §22.4.1: no precedent laundering ─────────────────────────────────────────
def test_a_row_below_the_comparable_floor_is_refused_on_the_write_side(memory, rules):
    """§22.4.2. The floor is enforced at the WRITE, so the store never holds a row that
    could not be shown."""
    written, refused = memory.write_precedent(
        [{"question": "q", "attested_count": 3, "comparable_on": "x",
          "answers": {"yes": 2, "no": 1}, "most_recent": "2026-01-01",
          "oldest": "2025-01-01"}], rules)
    assert written == [] and "floor" in refused[0]["why"]


def test_a_row_carrying_identifying_content_is_refused(memory, rules):
    """§22.4.2 aggregate-never-disclose. One team's project name must never reach a
    namespace every assessment can read."""
    written, refused = memory.write_precedent(
        [{"question": "q", "attested_count": 40, "comparable_on": "x",
          "answers": {"yes": 40}, "most_recent": "2026-01-01", "oldest": "2025-01-01",
          "project": "Contact centre reply drafting"}], rules)
    assert written == [] and "aggregate never discloses" in refused[0]["why"]


def test_write_precedent_refuses_everything_when_attested_only_is_off(memory, rules):
    """The rule is not a setting to be toggled off quietly — turning it off empties the
    write, rather than letting unattested answers through."""
    written, _ = memory.write_precedent(
        [{"question": "q", "attested_count": 40, "comparable_on": "x",
          "answers": {"yes": 40}, "most_recent": "2026-01-01", "oldest": "2025-01-01"}],
        dict(rules, attested_only=False))
    assert written == []


def test_the_seeded_dropped_row_is_refused(memory, rules):
    import assurance
    cfg = assurance.load_precedent()
    written, refused = memory.write_precedent(cfg["aggregates"], rules)
    assert len(written) == len(cfg["aggregates"]) - 1
    assert len(refused) == 1


def test_a_recalled_line_that_lost_its_count_cannot_be_shown(memory, rules):
    """Enforced on BOTH sides deliberately: the write filter protects the store, this
    protects the screen, and only one of them is on the side that owns the consequence."""
    floor = rules["minimum_comparable_count"]
    assert memory._mentions_enough("of 23 attested comparable assessments, 18 answered yes",
                                   floor) is True
    assert memory._mentions_enough("of 3 attested comparable assessments, 2 answered yes",
                                   floor) is False
    assert memory._mentions_enough("most others answered yes", floor) is False


# ── §22.2: recall is context, never evidence ─────────────────────────────────
def test_status_states_plainly_that_recall_is_not_evidence(memory):
    """Recalled memory may inform the conversation. It may never become an answer's basis:
    an answer's evidence is the person's own words or a verbatim quote from their document."""
    assert memory.status()["recall_is_evidence"] is False


# ── every path is best-effort ─────────────────────────────────────────────────
def test_nothing_raises_when_memory_is_not_configured(memory):
    assert memory.configured() is False
    assert memory.write_turn("s", "a", "USER", "hello") is False
    assert memory.recall("s", "anything") == []
    assert memory.recall_precedent("anything", {"minimum_comparable_count": 5}) == []
    assert memory.forget("s") == 0


def test_an_empty_turn_is_not_written(memory):
    assert memory.write_turn("s", "a", "USER", "   ") is False
