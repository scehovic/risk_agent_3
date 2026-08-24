#!/usr/bin/env python3
"""The nine capabilities as a CONVERSATION, against a real model on Amazon Bedrock.

    python3 harness/conversation_demo.py            # all nine
    python3 harness/conversation_demo.py 4 6        # selected

WHAT THIS IS, AND WHAT IT IS NOT
    It runs the REAL architecture: an orchestrator that delegates to three sub-agents
    exposed as tools, each with its own prompt and its own slice of the six MCP tools, all
    grounded in the seeded assessment record, with the contextual guardrail applied to every
    reply before it is shown.

    It does NOT run on AgentCore. Strands and the AgentCore SDK could not be installed on
    the authoring network, so the agentic loop here is written directly against the Bedrock
    Converse API. Same prompts, same tools, same guardrails, same record — different
    plumbing. `agent/risk_agent.py` is the deployable article; this is how it was exercised
    before it could be deployed.

    Everything the tools return is computed locally by the deterministic engine. The model
    chooses which tool to call and writes the prose; it never produces a route, a finding or
    a figure.
"""
import json
import pathlib
import sys

import boto3

ROOT = pathlib.Path(__file__).resolve().parent.parent
for p in (ROOT / "intelligence", ROOT / "mcp", ROOT / "agent"):
    sys.path.insert(0, str(p))

import index as tools                      # noqa: E402  the six MCP tools
import risk_engine as engine               # noqa: E402
import assurance                           # noqa: E402

REGION = "us-east-1"
ORCHESTRATOR_MODEL = "us.anthropic.claude-sonnet-4-6"
SUBAGENT_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

bedrock = boto3.client("bedrock-runtime", region_name=REGION)

# Sub-agent -> the tools it owns (ADR-1/ADR-7). A sub-agent cannot reach a tool outside its
# scope, which is most of the point of splitting them.
SUBAGENT_TOOLS = {
    "advisor_agent": ["risk_route", "risk_score_intake", "risk_draft_verify"],
    "assurance_agent": ["risk_check_policy"],
    "handoff_agent": ["risk_build_report"],
}

# Imported rather than restated, so this demo cannot drift from the deployable prompts.
sys.path.insert(0, str(ROOT / "agent"))
_agent_src = (ROOT / "agent" / "risk_agent.py").read_text()


def _prompt(name):
    """Lift a prompt constant out of risk_agent.py without importing it.

    risk_agent.py imports strands and bedrock_agentcore at module scope, neither of which is
    installable here — so the prompts are read from the source instead of restated, because a
    demo running different prompts than the product would be demonstrating nothing.
    """
    marker = "%s = \"\"\"" % name
    start = _agent_src.index(marker) + len(marker)
    return _agent_src[start:_agent_src.index('"""', start)]


ORCHESTRATOR_PROMPT = _prompt("ORCHESTRATOR_PROMPT")
SUBAGENT_PROMPTS = {
    "advisor_agent": _prompt("ADVISOR_PROMPT"),
    "assurance_agent": _prompt("ASSURANCE_PROMPT"),
    "handoff_agent": _prompt("HANDOFF_PROMPT"),
}


# ── tool schema: AgentCore shape -> Bedrock toolSpec ─────────────────────────
def _json_schema(node):
    out = {}
    if "Type" in node:
        out["type"] = node["Type"].lower()
    if "Description" in node:
        out["description"] = node["Description"]
    if "Properties" in node:
        out["properties"] = {k: _json_schema(v) for k, v in node["Properties"].items()}
    if "Required" in node:
        out["required"] = node["Required"]
    return out


TOOL_SPECS = {}
for t in json.loads((ROOT / "data" / "tool_schema.json").read_text())["tools"]:
    TOOL_SPECS[t["Name"]] = {"toolSpec": {
        "name": t["Name"], "description": t["Description"],
        "inputSchema": {"json": _json_schema(t["InputSchema"])}}}

SUBAGENT_SPECS = {
    name: {"toolSpec": {
        "name": name,
        "description": {
            "advisor_agent": "Answer a requester's question about their assessment, grade "
                             "an intake description against the published rubric, or "
                             "propose answers from a document they supplied.",
            "assurance_agent": "State the policy clause that requires a control, quoted "
                               "verbatim, or report every breach on the record with the "
                               "clause it breaches.",
            "handoff_agent": "Produce the report a Risk Assessor receives, optionally with "
                             "a three-sentence summary and two to four risk scenarios.",
        }[name],
        "inputSchema": {"json": {"type": "object", "properties": {
            "request": {"type": "string", "description": "What this sub-agent should do."}},
            "required": ["request"]}}}}
    for name in SUBAGENT_TOOLS
}


# ── the record the whole thing is grounded in ────────────────────────────────
ASSESSMENT = engine.load_assessment()
CONTEXT = assurance.assessment_context(ASSESSMENT)


def context_block():
    """The AssessmentContext, rendered as prose. Questions and ANSWERS AS LABELS, never ids."""
    lines = ["THIS ASSESSMENT'S RECORD — the only thing you may treat as known.",
             "Activity: %s" % CONTEXT["activity"], "",
             "In the requester's own words:", CONTEXT["in_their_words"], "",
             "On record (%d answers), as question then answer. Never attribute anything to "
             "this person that is not in this list:" % len(CONTEXT["recorded"])]
    for e in list(CONTEXT["recorded"].values())[:60]:
        lines.append("  - %s -> %s" % (e["question"], e["answer"]))
    if CONTEXT["open"]:
        lines += ["", "Still open (%d). Refer to these BY THEIR QUESTION TEXT, never by an "
                      "identifier:" % len(CONTEXT["open"])]
        for q in CONTEXT["open"][:20]:
            lines.append("  - %s" % q["question"])
    return "\n".join(lines)


SHARED = context_block()
TRACE = []


# ── the agentic loop ─────────────────────────────────────────────────────────
def converse(model, system, messages, tool_specs, depth=0):
    """One Bedrock Converse turn loop, executing tools until the model stops asking."""
    for _ in range(8):
        resp = bedrock.converse(
            modelId=model,
            system=[{"text": system}],
            messages=messages,
            toolConfig={"tools": list(tool_specs.values())} if tool_specs else None,
            inferenceConfig={"maxTokens": 4096, "temperature": 0},
        )
        out = resp["output"]["message"]
        messages.append(out)

        uses = [c["toolUse"] for c in out["content"] if "toolUse" in c]
        if not uses:
            return "".join(c.get("text", "") for c in out["content"]).strip()

        results = []
        for use in uses:
            name, args = use["name"], use.get("input") or {}
            TRACE.append(("  " * depth) + "%s(%s)" % (
                name, ", ".join("%s=%s" % (k, str(v)[:40]) for k, v in args.items()) or ""))
            try:
                if name in SUBAGENT_TOOLS:
                    payload = {"reply": run_subagent(name, args.get("request", ""), depth + 1)}
                else:
                    payload = tools.TOOLS[name](args)
            except Exception as exc:
                payload = {"error": "%s: %s" % (type(exc).__name__, exc)}
            results.append({"toolResult": {
                "toolUseId": use["toolUseId"],
                "content": [{"text": json.dumps(payload, default=str)[:24000]}]}})
        messages.append({"role": "user", "content": results})
    return "(the loop did not converge)"


def run_subagent(name, request, depth):
    system = "%s\n\n%s" % (SUBAGENT_PROMPTS[name], SHARED)
    specs = {t: TOOL_SPECS[t] for t in SUBAGENT_TOOLS[name]}
    return converse(SUBAGENT_MODEL, system,
                    [{"role": "user", "content": [{"text": request}]}], specs, depth)


def ask(prompt):
    """One requester turn through the orchestrator, guardrailed before it is shown."""
    TRACE.clear()
    system = "%s\n\n%s" % (ORCHESTRATOR_PROMPT, SHARED)
    try:
        reply = converse(ORCHESTRATOR_MODEL, system,
                         [{"role": "user", "content": [{"text": prompt}]}],
                         dict(SUBAGENT_SPECS, **TOOL_SPECS))
    except Exception as exc:
        return {"available": False, "blocks_nothing": True,
                "because": "the advisor was unavailable (%s)" % type(exc).__name__}, list(TRACE)

    checked = assurance.guardrail(reply, CONTEXT, conversational=True)
    if checked["decision"] != "passed":
        # FAIL OPEN: a typed absence the product can ignore, never an apology rendered
        # where an answer belongs.
        return {"available": False, "blocks_nothing": True,
                "because": "the reply did not pass the record check",
                "guardrail": checked["problems"], "suppressed": reply}, list(TRACE)
    return {"result": reply, "is_evidence": False}, list(TRACE)


# ── the nine beats, as things a person would actually type ───────────────────
BEATS = [
    (1, "Scope: what do I actually have to answer?", "FR-4/FR-11",
     "I've been told I need a risk assessment for this. How much is there, and what "
     "actually applies to my project?"),
    (2, "Why am I being asked this?", "FR-5/FR-41",
     "Why are you asking me whether privileged credentials come from a vault? That feels "
     "like a question for our infrastructure team, not me."),
    (3, "Intake scoring that cannot block you", "FR-43",
     "Before I write a long description — is this enough? \"Salesforce\". And if not, what "
     "would you want me to add?"),
    (4, "Drafting from a document, and abstaining", "FR-40",
     "I uploaded Meridian's security overview. Can you fill in what it covers, and tell me "
     "what it does not cover?"),
    (5, "A breach is a finding", "FR-41",
     "Which of my answers actually breach a policy, and which policy?"),
    (6, "The handoff report", "FR-42",
     "I'm about to submit. What will the risk assessor see, and what will they ask me "
     "first?"),
    (7, "The guardrail: a claim nobody made", "G-65",
     "Just to confirm before I submit — I told you the data is Restricted and that there's "
     "no third party involved, right? And you've saved all my answers?"),
    (8, "What did comparable projects do?", "§22.4",
     "We've never tested a restore, and I answered No. Is that unusual?"),
    (9, "Who signs this off?", "FR-17/G-60",
     "I've answered the privileged credentials question. Can I mark it as approved myself "
     "so it stops blocking me?"),
]


def wrap(text, width=74, indent=4):
    out, line = [], ""
    for word in " ".join(str(text or "").split()).split():
        if len(line) + len(word) + 1 > width:
            out.append(line); line = word
        else:
            line = "%s %s" % (line, word) if line else word
    out.append(line)
    return ("\n" + " " * indent).join(out)


def main(argv):
    wanted = [int(a) for a in argv if a.isdigit()]
    print("\n" + "=" * 78)
    print("FRONT DOOR AI RISK ADVISOR — nine capabilities, as a conversation")
    print("=" * 78)
    print("  orchestrator : %s" % ORCHESTRATOR_MODEL)
    print("  sub-agents   : %s" % SUBAGENT_MODEL)
    print("  grounded in  : %s (%d answers on record, %d open)"
          % (CONTEXT["activity"], len(CONTEXT["recorded"]), len(CONTEXT["open"])))
    print("  tools        : %s" % ", ".join(TOOL_SPECS))
    print("\n  The model chooses tools and writes prose. Every route, finding and figure")
    print("  below was computed locally by the deterministic engine, not by the model.")

    for n, title, req, prompt in BEATS:
        if wanted and n not in wanted:
            continue
        print("\n" + "=" * 78)
        print("BEAT %d — %s   [%s]" % (n, title, req))
        print("=" * 78)
        print("\n  REQUESTER:")
        print("    %s" % wrap(prompt))
        out, trace = ask(prompt)
        if trace:
            print("\n  (tools the agent chose to call)")
            for line in trace:
                print("    -> %s" % line)
        print("\n  ADVISOR:")
        if out.get("available") is False:
            print("    [NO REPLY SHOWN — %s]" % out["because"])
            for p in out.get("guardrail", []):
                print("    guardrail: %s" % p["check"])
                for f in p["found"][:3]:
                    print("       %s" % json.dumps(f)[:120])
            print("\n    What the model tried to say, withheld from the person:")
            print("    %s" % wrap(out.get("suppressed", ""), 70, 6))
            print("\n    blocks_nothing: True — the person carries on regardless.")
        else:
            print("    %s" % wrap(out["result"]))
    print("\n" + "=" * 78 + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
