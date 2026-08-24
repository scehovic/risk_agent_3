"""Front Door AI Risk Advisor — its OWN AgentCore Runtime.

═══════════════════════════════════════════════════════════════════════════════
 SPEC §7 (the agentic contract), §6.1 (the three seams), §22.1 (the feature register),
 FR-39 to FR-43. Owner: risk-platform
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS IS
    One runtime for the risk intake journey. Internally it is an ORCHESTRATOR composing
    three in-process SUB-AGENTS as Strands tools, while presenting a single agent to the
    platform. The five capabilities of §22.1 are packaged into those three:

        advisor_agent    — the companion (FR-39), document drafting (FR-40),
                           intake scoring (FR-43)
        assurance_agent  — policy authority and breach findings (FR-41)
        handoff_agent    — the handoff report and its scenarios (FR-42)

    Each reaches the segment's own MCP tools over the Gateway, where the deterministic
    engine lives. Reasoning is the agent's; the routing, the findings and the report are
    the engine's.

WHAT THIS AGENT MAY NEVER DO (§7 — normative, not aspirational)
    Answer from nothing. Paraphrase evidence. Utter an internal identifier to a person.
    Advance the interview on silence. Attest, declare, resolve or accept anything. Act as
    an autonomous orchestrator of the governed pipeline — AgentCore is SUBSTRATE, NEVER THE
    DECIDER. It hands off submission; it never performs it.

THE RULE THAT OUTRANKS EVERYTHING ELSE HERE (G-69)
    NO AGENT, A SLOW AGENT, A WRONG AGENT, A PARTIAL ANSWER OR A THROWN ERROR ALL PASS.
    Every failure path below returns a typed pass-through the product can ignore, never an
    error sentence rendered where an answer goes. A quality assistant that blocks
    submission has become a gate, and the mission is reducing friction.

CONTRACT WITH THE CALLER — DO NOT CHANGE
    Invoked with {"prompt", "session_id", "assessment"|"shared_context", "capability"?};
    returns {"result": "<text>", "session_id": "...", ...}. Never re-derive figures that
    arrive in the assessment record — they are authoritative (ADR-6).
"""
import json
import logging
import os

from functools import partial

from strands import Agent, tool
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore import BedrockAgentCoreApp

# NOT `as context`: AgentCore's entrypoint receives a RequestContext parameter named
# `context`, which would shadow this module inside invoke().
import session as session_state
import memory
import assurance
import risk_engine as engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("risk-advisor")

app = BedrockAgentCoreApp()

SEGMENT = "risk-advisor"
PROMPT_VERSION = "2026-08-24.1"


def _fast_model_default():
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or ""
    prefix = {"us": "us", "eu": "eu", "ap": "apac"}.get(region.split("-")[0], "us")
    return "%s.anthropic.claude-haiku-4-5-20251001-v1:0" % prefix


# The sub-agents run the FAST model: narrow reasoning over figures that arrive
# authoritative, so the frontier model buys nothing but latency. Scoring an intake
# description against published anchors is not a frontier-model task.
MODEL_ID = (os.environ.get("SEGMENT_MODEL_ID")
            or os.environ.get("BEDROCK_MODEL_ID_FAST")
            or _fast_model_default())
GATEWAY_URL = os.environ.get("GATEWAY_URL", "")


# ── prompts ──────────────────────────────────────────────────────────────────
ORCHESTRATOR_PROMPT = """You are the Front Door Risk Advisor for an enterprise risk intake platform.

WHO YOU ARE TALKING TO
  A business person describing an activity they want to launch — a project, a vendor
  purchase, a new use of AI. They are not a risk specialist and should never need to be.
  If they would need a glossary, the question is wrong, not the person.

WHAT YOU ARE FOR
  Removing friction from an assessment that has historically taken up to ninety hours,
  without losing any rigour. You explain, you suggest, you draft from evidence they gave
  you, and you assemble. You never decide.

YOUR SUB-AGENTS (call them as tools)
  1. advisor_agent   — answers a requester's question about their assessment, grades an
                       intake description, and proposes answers from a document they
                       supplied.
  2. assurance_agent — states the policy clause that requires a control, and reports
                       breaches against what is on record.
  3. handoff_agent   — produces the report a Risk Assessor receives.

HARD GUARDRAILS — these are not style preferences
  • NEVER state something as this person's answer unless it is in the record you were
    given. If it is not there, ask; do not assume.
  • NEVER say an answer, a submission or a declaration has been recorded, saved or
    signed. You do not record anything. A person clicking is what records.
  • NEVER use an internal identifier. Refer to a question by its words.
  • NEVER attest, declare, resolve a finding or accept a risk. Those are named human acts.
  • A drafted answer is a PROPOSAL until the person accepts it. Say so.
  • If you do not know, say you do not know and say who would. Abstaining is a correct
    answer here, not a failure.

STYLE
  Plain business English. No greetings, no restating the question back. Short.
  NO markdown tables, NO headings, NO bullet lists longer than four items, NO emoji.
  A person reading this is mid-form on a screen, not reading a document.

LENGTH — HARD LIMIT: 120 WORDS
  Measured, not estimated. This is the whole answer, not an introduction to one.

  A question that sounds like it wants everything — "how much is there?", "what applies?"
  — does NOT license a report. It licenses the two or three sentences that let a person
  decide what to do next, and an offer to go deeper on one thing. Answering it with
  eighteen rows of table is how a person stops reading and starts guessing, which is the
  failure this product exists to prevent.

  The ONLY exception is an explicit request for the handoff report, which has its own
  format. If you cannot answer inside 120 words, say the one thing that matters most and
  ask which part they want next.
"""

ADVISOR_PROMPT = """You are the Advisor sub-agent: the requester's thought partner.

You do three jobs, and your tools do the work in all three:

1. ANSWERING A QUESTION ABOUT THEIR ASSESSMENT
   Call risk_route. It returns what applies to this activity and why, and — given a
   question — that question's routing in one sentence plus the policy clause behind it.
   Answer from what it returns and from the record in your context. Nothing else.

2. GRADING AN INTAKE DESCRIPTION
   Call risk_score_intake with the text. If it returns a floor verdict, relay that message
   and stop — no scoring needed. If it returns anchors to score against, score each
   dimension 0, 1 or 2 STRICTLY ON WHETHER THE FACTUAL DETAIL IS PRESENT — never on
   length, never on writing style, never on how impressive the activity sounds — then call
   it again with your scores. The sentence a person reads comes back from the tool. Relay
   it; do not write your own.

3. PROPOSING ANSWERS FROM A DOCUMENT
   For each question you can support, call risk_draft_verify with a basis of "stated" or
   "inferred", the VERBATIM sentence from the document, its source id, and why. Quote
   EXACTLY — copy the characters, do not tidy them. If the document does not address a
   question, submit a basis of "not_stated" with no value and say what you looked for and
   did not find. THAT IS A CORRECT ANSWER, not a failure, and it is scored as one.
   Never propose an answer the document does not support.

Everything you produce is indicative and unconfirmed until the person accepts it.
"""

ASSURANCE_PROMPT = """You are the Assurance sub-agent: the authority behind a question.

Call risk_check_policy. With a question, it returns the policy clauses requiring that
control, quoted verbatim with reference and version. With no question, it returns the full
deterministic compliance pass — every breach, every gap, every enhancement, and the
clauses this instrument asks nothing about.

QUOTE POLICY VERBATIM OR NOT AT ALL. Name the policy, the clause and the version every
time. A paraphrased policy is not a policy.

A policy defines what a term means and what is required. IT MAY NEVER ASSERT A FACT ABOUT
THIS PROJECT — only the requester can do that. So: the policy supplies the requirement,
the record supplies the answer, and you report where the two disagree.

A breach is a finding, resolved only through the four governed dispositions. You do not
resolve it, waive it, or soften it. Report it and say which clause it breaches.
"""

HANDOFF_PROMPT = """You are the Handoff sub-agent: you prepare what a Risk Assessor receives.

Call risk_build_report. What it returns is COMPLETE ALREADY — every figure on it is read
from the record. You add exactly two things, and the page is finished without either:

1. A SUMMARY OF AT MOST THREE SENTENCES. What this activity is, where the risk
   concentrates, and what a reviewer should look at first. Three sentences is the brief;
   four is somebody not reading it.

2. TWO TO FOUR RISK SCENARIOS WORTH ASKING ABOUT. A scenario is A QUESTION, never a
   finding. Each must cite the controls or risk areas it was read from, BY THE EXACT NAMES
   THAT APPEAR IN THE REPORT. A scenario citing anything else is dropped entirely — not
   shown with a caveat, dropped, because it is not a weaker scenario, it is one built on
   nothing.

Pass both back through risk_build_report to be vetted. If either is rejected, say so
plainly and present the report as it stands.
"""


# ── sub-agent tools ──────────────────────────────────────────────────────────
def _new_mcp_client():
    """A fresh Gateway MCP client, or None when the Gateway isn't configured.

    One per sub-agent: they run sequentially under the orchestrator, but a dedicated client
    keeps each one's tool session self-contained rather than sharing one across four agents.
    """
    if not GATEWAY_URL:
        return None
    try:
        transport = partial(streamablehttp_client, url=GATEWAY_URL)
        return MCPClient(transport_callable=transport)
    except Exception as exc:
        logger.warning("MCP client init failed: %s", exc)
        return None


def _make_subagent(name, base_prompt, doc, context_fn):
    """Wrap an inner Agent as a Strands tool the orchestrator can call.

    The context is resolved via a CALLABLE AT CALL TIME, never captured — this Agent is
    cached across requests, and a captured context would leak one assessment's figures into
    the next person's conversation.
    """
    holder = {"agent": None}

    def _run(request):
        if holder["agent"] is None:
            mcp = _new_mcp_client()
            holder["agent"] = Agent(model=MODEL_ID, system_prompt=base_prompt,
                                    tools=[mcp] if mcp else [])
        shared = context_fn() if callable(context_fn) else ""
        holder["agent"].system_prompt = "%s\n\n%s" % (base_prompt, shared) if shared \
            else base_prompt
        try:
            return str(holder["agent"](request)).strip()
        except Exception as exc:
            logger.warning("%s failed: %s", name, exc)
            # Degrades to a sentence INSIDE the composed answer. The caller still gets a
            # response, and the product's own fail-open handling decides what to show.
            return "%s unavailable: %s" % (name, type(exc).__name__)

    _run.__name__ = name
    _run.__doc__ = doc
    return tool(_run)


_agent = None
_mcp_status = "not_initialized"


def _get_agent():
    """Cached orchestrator: its own Gateway MCP client plus the three sub-agent tools.

    Degrades rather than fails — with no Gateway it still reasons from the assessment
    record, which already carries the authoritative answers.
    """
    global _agent, _mcp_status
    if _agent is not None:
        return _agent

    subagents = [
        _make_subagent("advisor_agent", ADVISOR_PROMPT,
                       "Answer a requester's question about their assessment, grade an "
                       "intake description against the published rubric, or propose "
                       "answers from a document they supplied. Pass the requester's "
                       "request and any text or question ids involved.",
                       session_state.context_block),
        _make_subagent("assurance_agent", ASSURANCE_PROMPT,
                       "State the policy clause that requires a control, quoted verbatim, "
                       "or report every breach on the record with the clause it breaches.",
                       session_state.context_block),
        _make_subagent("handoff_agent", HANDOFF_PROMPT,
                       "Produce the report a Risk Assessor receives, optionally adding a "
                       "three-sentence summary and two to four risk scenarios worth "
                       "asking about.",
                       session_state.context_block),
    ]

    mcp = _new_mcp_client()
    if mcp:
        _mcp_status = "connected"
    else:
        _mcp_status = "no GATEWAY_URL — reasoning from the record only" if not GATEWAY_URL \
            else "MCP init failed — reasoning from the record only"
        logger.warning(_mcp_status)

    tools = ([mcp] if mcp else []) + subagents
    _agent = Agent(model=MODEL_ID, system_prompt=ORCHESTRATOR_PROMPT, tools=tools)
    logger.info("risk advisor ready with %d sub-agents, mcp=%s", len(subagents), _mcp_status)
    return _agent


# ── the entrypoint ───────────────────────────────────────────────────────────
@app.entrypoint
def invoke(payload, context=None):
    # The parameter MUST be named `context` with a default — AgentCore inspects the
    # signature to decide whether to pass its RequestContext. Renaming it 500s delegations.
    """Entrypoint. Fails open on every path (G-69)."""
    if payload.get("type") == "warmup":
        _get_agent()
        return {"status": "warm", "segment": SEGMENT, "model": MODEL_ID,
                "mcp": _mcp_status, "prompt_version": PROMPT_VERSION,
                "memory": memory.status(), "instrument": engine.lint_instrument()["counted"]}

    prompt = payload.get("prompt", "")
    session_id = payload.get("session_id", "demo")
    record = payload.get("assessment") or payload.get("shared_context")

    # Adopt the record BEFORE reasoning. This is the hand-off, and it is REQUIRED: a
    # capability that cannot be told what is on record cannot be caught claiming something
    # that is not (G-65). The service refuses rather than proceeding unguarded.
    session_state.reset()
    ctx = session_state.adopt(record, session_id)
    if ctx is None:
        return _pass_through(session_id, "no assessment record was supplied, and this "
                                         "agent will not answer without one")

    session_state.remember_turn("USER", prompt)

    try:
        agent = _get_agent()
        shared = session_state.context_block()
        agent.system_prompt = "%s\n\n%s" % (ORCHESTRATOR_PROMPT, shared) if shared \
            else ORCHESTRATOR_PROMPT
        result = str(agent(prompt)).strip()
    except Exception as exc:
        logger.warning("risk advisor failed: %s: %s", type(exc).__name__, exc)
        return _pass_through(session_id, "the advisor was unavailable (%s)"
                                         % type(exc).__name__)

    # Everything said to a person is checked against that assessment's record, and the
    # conversational gate additionally refuses any claim that work was recorded or signed.
    checked = assurance.guardrail(result, ctx, conversational=True)
    if checked["decision"] != "passed":
        logger.warning("guardrail refused a reply: %s", json.dumps(checked["problems"]))
        return _pass_through(session_id, "the reply did not pass the record check",
                             guardrail=checked["problems"])

    session_state.remember_turn("ASSISTANT", result)

    return {"result": result, "session_id": session_id,
            "basis": "context", "is_evidence": False,
            "disclosure": "This is context to help you answer. It is not evidence, "
                          "nothing here has been recorded, and the answer stays yours.",
            "prompt_version": PROMPT_VERSION}


def _pass_through(session_id, because, **extra):
    """The fail-open response. TYPED, so the product can ignore it rather than render it.

    Not an error sentence in the place an answer goes. `available: False` is what the
    calling screen branches on; `result` is empty on purpose.
    """
    out = {"result": "", "session_id": session_id, "available": False,
           "blocks_nothing": True, "because": because,
           "disclosure": "No assistance this time. Nothing is blocked — carry on."}
    out.update(extra)
    return out


if __name__ == "__main__":
    app.run()
