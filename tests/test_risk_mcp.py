"""The tool layer's contract: the envelope, the dispatch, and the schema parity.

No AWS, no model. Dispatch is asserted BOTH ways — Gateway-style (the tool name arrives in
the Lambda client context as `${target}___${tool}`) and direct-invoke style — because the
two paths take different branches and only one of them is exercised by a demo.
"""
import json
import pathlib
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOMAIN_TOOLS = ["risk_route", "risk_score_intake", "risk_draft_verify",
                "risk_check_policy", "risk_build_report"]


def _gateway_context(tool_name, target="riskTools"):
    cc = types.SimpleNamespace(
        custom={"bedrockAgentCoreToolName": "%s___%s" % (target, tool_name)})
    return types.SimpleNamespace(client_context=cc)


# ── schema parity: ONE definition, two readers ───────────────────────────────
def test_the_gateway_schema_and_the_lambda_implement_exactly_the_same_tools(tools):
    """This schema is easy to end up carrying in three files. A Gateway advertising a tool
    the Lambda does not implement fails at demo time with an unhelpful error."""
    schema = json.loads((ROOT / "data" / "tool_schema.json").read_text())["tools"]
    assert {t["Name"] for t in schema} == set(tools.TOOLS)


def test_every_advertised_tool_has_a_description_a_model_could_choose_from(tools):
    schema = json.loads((ROOT / "data" / "tool_schema.json").read_text())["tools"]
    for t in schema:
        assert len(t["Description"]) > 80, t["Name"]
        assert "InputSchema" in t


def test_the_tool_layer_stays_small(tools):
    """ADR-7. One tool per journey step plus a routing smoke test. A sprawling tool layer is
    harder for a model to choose from and harder to test."""
    assert len(tools.TOOLS) == 6


# ── dispatch ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("name", DOMAIN_TOOLS + ["risk_hello"])
def test_every_tool_resolves_through_the_gateway_naming(tools, name):
    out = tools.handler({}, _gateway_context(name))
    assert "error" not in out, out


@pytest.mark.parametrize("name", DOMAIN_TOOLS + ["risk_hello"])
def test_every_tool_resolves_through_a_direct_invoke(tools, name):
    out = tools.handler({"tool_name": name, "input": {"text": "x"}}, None)
    assert "error" not in out, out


def test_an_unknown_tool_returns_a_payload_and_never_raises(tools):
    out = tools.handler({"tool_name": "risk_make_it_up"}, None)
    assert "error" in out and sorted(out["available"]) == sorted(tools.TOOLS)


def test_the_handler_never_raises_even_on_nonsense(tools):
    for event in (None, {}, {"tool_name": "risk_route", "input": {"answers": "not a dict"}}):
        assert isinstance(tools.handler(event, None), dict)


def test_a_tool_name_is_not_mistaken_for_an_argument(tools):
    """`risk_hello` takes a `name` argument, and the direct-invoke path also reads `name` as
    the tool name. Only strip it when it actually carried the tool name."""
    out = tools.handler({"tool_name": "risk_hello", "name": "Ada"}, None)
    assert "Ada" in out["message"]


# ── the envelope ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("name", DOMAIN_TOOLS)
def test_every_domain_tool_returns_the_explainability_envelope(tools, name):
    """ADR-5. Every result carries what it decided, the rule that produced it, and an honest
    label. Nothing reads as more settled than it is."""
    out = tools.handler({"tool_name": name, "input": {"text": "x"}}, None)
    assert set(out) >= {"decision", "binding_rule", "disclosure"}, name
    assert out["disclosure"] and out["binding_rule"]


@pytest.mark.parametrize("name", DOMAIN_TOOLS + ["risk_hello"])
def test_every_tool_result_is_json_serialisable(tools, name):
    json.dumps(tools.handler({"tool_name": name, "input": {"text": "x"}}, None))


# ── the correctness guard this pattern needs ─────────────────────────────────
def test_a_partial_call_backfills_the_record_rather_than_reporting_an_all_clear(tools):
    """THE regression test for `_resolve_assessment`.

    A sub-agent routinely calls with only what it holds. Without the merge, the engine sees
    no answers and — because nothing activates on silence — returns "nothing applies". That
    PHANTOM CLEAN BILL OF HEALTH is worse than a phantom DECLINE,
    because a decline gets argued with and an all-clear gets believed."""
    bare = tools.handler({"tool_name": "risk_route", "input": {}}, None)
    assert bare["counts"]["paths"] > 0
    assert bare["counts"]["objectives"] > 0


def test_an_answer_overlay_is_applied_over_the_record(tools):
    """A caller passing `answers` is holding partial state mid-conversation, not proposing a
    whole new record."""
    before = tools.handler({"tool_name": "risk_route", "input": {}}, None)
    after = tools.handler({"tool_name": "risk_route",
                           "input": {"answers": {"t1_sec_1": ["internal_only"]}}}, None)
    assert after["counts"]["paths"] < before["counts"]["paths"]


def test_routing_explains_itself_without_ever_naming_an_identifier(tools, engine):
    for qid in engine.instrument()["objectives"]:
        out = tools.handler({"tool_name": "risk_route",
                             "input": {"explain_question": qid}}, None)
        blob = json.dumps(out["explanation"])
        assert qid not in blob, qid


def test_the_smoke_test_reports_instrument_health(tools):
    out = tools.handler({"tool_name": "risk_hello"}, None)
    assert out["instrument_coherent"] is True
    assert out["instrument"]["objectives"] == 51
