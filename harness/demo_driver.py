#!/usr/bin/env python3
"""Walk every demo beat through the tool layer — NO MODEL, NO AWS, NO NETWORK.

This is the demo-truth artifact: a claim the product makes must be COMPUTED, or it is a
hope. Everything printed below is derived from `data/` by the deterministic engine on this
machine, right now. Where a beat needs the model, the beat says what the model would add
and then shows the page WITHOUT it — because the report is complete without the agent and
the intake assistant fails open.

    python3 harness/demo_driver.py            # all beats
    python3 harness/demo_driver.py 3          # one beat
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
for p in (ROOT / "intelligence", ROOT / "mcp"):
    sys.path.insert(0, str(p))

import index as tools               # noqa: E402
import risk_engine as engine        # noqa: E402
import assurance                    # noqa: E402


def head(n, title, spec):
    print("\n" + "=" * 78)
    print("BEAT %s — %s" % (n, title))
    print("  %s" % spec)
    print("=" * 78)


def beat1():
    head(1, "One front door: what does this person actually have to answer?",
         "FR-4, FR-11 · the routing engine, union with provenance")
    r = tools.risk_route({})
    print("\n  Of 11 risk areas, %d apply. Of 21 risk paths, %d are live." % (
        sum(1 for g in r["gates"].values() if g["open"]), r["counts"]["paths"]))
    print("  %d control objectives accumulated out of 51. %d questions are in the funnel."
          % (r["counts"]["objectives"], r["visible_question_count"]))
    print("\n  Three of the twenty-one paths are NOT active. Nobody is asked about them:")
    live = {p["code"] for p in r["active_paths"]}
    for code, path in engine.instrument()["paths"].items():
        if code not in live:
            print("    - %s" % path["name"])
    print("\n  And every live path says why it is live:")
    for p in r["active_paths"][:3]:
        print("    %s" % p["name"])
        for why in p["reasons"]:
            print("        because %s" % why)


def beat2():
    head(2, "Why am I being asked this? An authority, not a routing rule.",
         "FR-5, FR-41 · §22.5 policy authority")
    for qid in ("t3_iam_02", "t3_res_02"):
        r = tools.risk_route({"explain_question": qid})
        e = r["explanation"]
        print("\n  Q: %s" % e["question"])
        for why in e["because"]:
            print("     asked because %s" % why)
        for a in e["authority"]:
            print("     required by %s v%s, clause %s:" % (a["policy"], a["policy_version"],
                                                           a["clause"]))
            print('        "%s"' % _wrap(a["text"], 66, 8))


def beat3():
    head(3, "The intake assistant that cannot block you",
         "FR-43, G-69 · three layers, only one is a model")
    print("\n  The floor is local and costs nothing. No model is called for any of these:")
    for text in ("", "Salesforce", "new crm thing", "asdkjh kjhasd kjh asdkjh asdkjh"):
        r = tools.risk_score_intake({"text": text})
        print("\n    you typed: %r" % (text or "(nothing)"))
        print("    -> %s" % _wrap(r["message"], 70, 7))
        print("       model called: %s | blocks submission: %s"
              % (r["model_called"], r["blocks_submission"]))

    print("\n  A real but thin description passes the floor and IS scored. Suppose the")
    print("  model returns 2/1/0/1/2. Every sentence below comes from the rubric file:")
    r = assurance.intake_feedback({"specificity": 2, "scope": 1, "data_handling": 0,
                                   "dependencies": 1, "outcomes": 2})
    print("\n    %s — %d/%d. %s" % (r["band_label"], r["total"], r["of_possible"],
                                    r["message"]))
    for ask in r["asks"]:
        print("\n    %s" % ask["dimension"])
        print("      ask:    %s" % _wrap(ask["feedback"], 66, 14))
        print("      scored against: \"%s\"" % _wrap(ask["scored_against"], 58, 22))
    print("\n    blocks submission: %s   <- the whole point" % r["blocks_submission"])

    print("\n  And if the model returns nonsense, the nonsense is DROPPED, not clamped:")
    bad = assurance.intake_feedback({"specificity": 7, "scope": -1, "data_handling": 2,
                                     "dependencies": "two", "outcomes": 2})
    print("    dropped: %s" % [d["received"] for d in bad["dropped_scores"]])
    print("    blocks submission: %s" % bad["blocks_submission"])


def beat4():
    head(4, "Hand it a document. It proposes, and it abstains.",
         "FR-40, §5.2 never-guess · G-66 proposals are not answers")
    doc = engine.load_document_text()
    good = ("Encryption keys are held in a managed hardware security module operated by "
            "Meridian")
    print("\n  A PROPOSAL the gate accepts — the sentence is verbatim in the document:")
    r = tools.risk_draft_verify({"draft": {
        "question": "t3_dp_04", "basis": "stated", "value": "yes",
        "quote": good, "source_id": "doc.1",
        "because": "The vendor overview states the keys sit in a managed module, held "
                   "apart from the data and rotated on a schedule."}})
    print("     %s | confirmed: %s | recorded: %s"
          % (r["decision"], r["confirmed"], r["recorded"]))
    print('     quote: "%s"' % _wrap(r["quote"], 62, 12))
    print("     %s" % _wrap(r["disclosure"], 68, 5))

    print("\n  An ABSTENTION, which is a CORRECT answer and scored as one:")
    r = tools.risk_draft_verify({"draft": {
        "question": "t3_ops_03", "basis": "not_stated", "value": None,
        "because": "I looked for anything about capacity or performance monitoring and "
                   "the vendor overview does not mention it."}})
    print("     %s | value: %r" % (r["decision"], r.get("value")))
    print("     %s" % _wrap(r["because"], 68, 5))

    print("\n  And four fabrications the gate refuses. Note the second one especially:")
    stitched = ("Encryption keys are held in a managed hardware security module rotated "
                "automatically every ninety days")
    for label, draft in [
        ("a paraphrase", {"quote": "Meridian keeps keys in an HSM"}),
        ("a STITCHED quote (both halves are really in the document)", {"quote": stitched}),
        ("a citation to a document nobody supplied", {"source_id": "doc.99"}),
        ("no reason given", {"because": ""}),
    ]:
        base = {"question": "t3_dp_04", "basis": "stated", "value": "yes",
                "quote": good, "source_id": "doc.1", "because": "It says so."}
        base.update(draft)
        r = tools.risk_draft_verify({"draft": base})
        print("     %-56s -> %s" % (label, r["decision"].upper()))
        print("        %s" % r["why"])


def beat5():
    head(5, "A breach is a finding, and it names the clause it breaches",
         "FR-41, G-67 · the deterministic pass stands alone with no model")
    r = tools.risk_check_policy({})
    print("\n  %d findings, computed with no model call:" % sum(r["counts"].values()))
    print("    %d non-compliance  %d control gap  %d enhancement"
          % (r["counts"]["non_compliance"], r["counts"]["control_gap"],
             r["counts"]["enhancement"]))
    print("\n  Three of the breaches:")
    for f in [x for x in r["findings"] if x["kind"] == "non_compliance"][:3]:
        print("\n    %s" % f["objective"])
        print("      they answered: %s" % f["answer"].upper())
        print('      they wrote:    "%s"' % _wrap(f["note"], 60, 21))
        print("      breaches %s %s:" % (f["citation"]["policy"], f["citation"]["clause"]))
        print('        "%s"' % _wrap(f["citation"]["text"], 64, 9))
    print("\n  And the direction people forget — an obligation we never ask about:")
    for c in r["uncovered_clauses"]:
        print("    %s %s asks something this instrument does not:" % (c["policy"], c["clause"]))
        print('      "%s"' % _wrap(c["text"], 64, 7))
        print("      %s" % _wrap(c["note"], 66, 6))


def beat6():
    head(6, "The report a Risk Assessor is handed — derived, never stored",
         "FR-42, G-68 · complete without the agent")
    r = tools.risk_build_report({})
    print("\n  %s" % r["activity"])
    print("  %s" % _wrap(r["in_their_words"], 72, 2))
    print("\n  %d risk paths apply. %d controls answered, %d nobody answered, %d findings."
          % (r["counts"]["paths"], r["counts"]["controls_answered"],
             r["counts"]["controls_unanswered"], r["counts"]["findings"]))
    print("\n  Severity concentrates here:")
    for q in r["severity_profile"]["high"][:4]:
        print("    HIGH  %s" % _wrap(q, 66, 10))
    print("\n  Nobody answered these, and the report says so rather than implying zero:")
    for c in r["nobody_answered"]:
        print("    - %s (%s)" % (c["objective"], c["family"]))
    print("\n  Where the pilot deliberately stops, it says it is stopping deliberately:")
    for b in r["declared_boundaries"][:3]:
        print("    %s: %s" % (b["area"], _wrap(b["note"], 60, 6)))
    print("\n  Open hand-off nobody can dismiss:")
    for h in r["open_handoffs"]:
        print("    to %s: %s" % (h["to"], _wrap(h["question"], 58, 6)))
    print("\n  complete_without_agent: %s" % r["complete_without_agent"])

    print("\n  Now the two things an agent MAY add. A good scenario, and two dropped:")
    r2 = tools.risk_build_report({"scenarios": [
        {"question": "If a customer complained about a reply, could we show which of "
                     "Meridian's engineers had touched their record?",
         "cites": ["Unique named accounts", "Privileged session recording"]},
        {"question": "Could the quantum firewall be bypassed?",
         "cites": ["Quantum Firewall Hardening"]},
        {"question": "Is this risky?", "cites": []},
    ]})
    s = r2["agent_scenarios"]
    for kept in s["scenarios"]:
        print("\n    KEPT: %s" % _wrap(kept["question"], 64, 10))
        print("      read from: %s" % ", ".join(kept["cites"]))
    for dropped in s["dropped"]:
        print("\n    DROPPED: %s" % _wrap(str(dropped["scenario"]), 62, 13))
        print("      %s" % dropped["why"])


def beat7():
    head(7, "The guardrail that stops the sentence, not the category",
         "G-65 · one function, every capability, proved to fire")
    ctx = assurance.assessment_context(engine.load_assessment())
    cases = [
        ("You still need to answer t3_iam_02 before you submit.",
         "an internal identifier: our problem handed to them", False),
        ("This is being asked because TPR_LA applies.",
         "a path code", False),
        ("You said Yes to AI, and you said the data is Restricted.",
         "ONE TRUE CLAUSE MUST NOT LAUNDER A FALSE ONE — the record says Confidential",
         False),
        ("You told us there is no third party involved.",
         "an answer nobody gave, that a busy person would read as confirmation", False),
        ("Great, I have saved that for you.",
         "a claim that work was recorded. It was not. A click records.", True),
        ("You said the most sensitive data involved is Confidential. Four control "
         "questions are still open, including one about how long logs are kept.",
         "true, useful, and it passes", True),
    ]
    for text, why, conv in cases:
        r = assurance.guardrail(text, ctx, conversational=conv)
        print("\n  %s" % ("PASSED " if r["decision"] == "passed" else "REFUSED"))
        print("    said:   \"%s\"" % _wrap(text, 62, 12))
        print("    reason: %s" % _wrap(why, 64, 12))
        for p in r["problems"]:
            print("    check:  %s" % p["check"])


def beat8():
    head(8, "Portfolio memory, fenced by its own four rules",
         "§22.4, G-21 · attested-only, aggregate, floored, never pre-selected")
    p = assurance.precedent_for("t3_res_02")
    print("\n  On a question this assessment answered No:")
    print("    of %d ATTESTED comparable assessments (%s):"
          % (p["attested_count"], p["comparable_on"]))
    for row in p["pattern"]:
        print("      %-8s %d" % (row["answer"], row["count"]))
    print("    most recent %s, oldest %s" % (p["most_recent"], p["oldest"]))
    print("    never pre-selected: %s" % p["never_preselect"])
    print("    %s" % _wrap(p["disclosure"], 66, 4))

    print("\n  Below the comparable-count floor, it shows NOTHING AT ALL:")
    print("    a question with 3 attested comparables -> %r"
          % assurance.precedent_for("t3_dp_04"))
    print("    (a precedent from too few assessments is gossip, and it also leaks who)")

    print("\n  The reviewer — never the requester — sees divergence:")
    d = assurance.divergence_for("t3_iam_01", engine.load_assessment())
    print("    answered %s where %d of %d comparable assessments answered %s"
          % (d["answered"], d["majority_count"], d["of_total"], d["majority"]))
    print("    shown to: %s" % d["shown_to"])
    print("    %s" % _wrap(d["disclosure"], 66, 4))


def beat9():
    head(9, "Attestation authority is derived, never asserted by the caller",
         "FR-17, G-60 · a permission check reading a value the requester chose is not one")
    people = [("a Security assessor", {"role": "assessor", "risk_domain": "security"}),
              ("a Data Privacy assessor", {"role": "assessor", "risk_domain": "privacy"}),
              ("a generalist assessor", {"role": "assessor", "risk_domain": None}),
              ("the requester who answered it", {"role": "requester"})]
    q = engine.instrument()["questions"]["t3_iam_02"]["text"]
    print("\n  Signing: %s" % _wrap(q, 68, 11))
    for label, who in people:
        r = assurance.attestation_authority("t3_iam_02", who)
        print("\n    %-30s %s" % (label, "PERMITTED" if r["allowed"] else "REFUSED"))
        print("      %s" % _wrap(r["because"], 66, 6))


def _wrap(text, width, indent):
    text = " ".join(str(text or "").split())
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = "%s %s" % (line, word) if line else word
    out.append(line)
    return ("\n" + " " * indent).join(out)


BEATS = [beat1, beat2, beat3, beat4, beat5, beat6, beat7, beat8, beat9]

if __name__ == "__main__":
    wanted = [int(a) for a in sys.argv[1:] if a.isdigit()]
    print("\nFRONT DOOR AI RISK ADVISOR — demo walk")
    print("Everything below is derived from data/ by the engine. No model. No AWS.")
    for i, beat in enumerate(BEATS, 1):
        if not wanted or i in wanted:
            beat()
    print("\n" + "=" * 78)
    lint = engine.lint_instrument()
    print("Instrument: %s | %s" % (lint["decision"], lint["counted"]))
    print("=" * 78 + "\n")
