#!/usr/bin/env python3
"""Talk to the Risk Advisor from a terminal.

    python3 agent/risk_agent.py          # in one shell (needs AWS creds for Bedrock)
    python3 harness/chat_cli.py          # in another

With no runtime reachable it says so and exits rather than pretending — but note the
product itself would carry on regardless: the assistant being absent blocks nothing (G-69).
"""
import sys

import runtime_client as rc


def main():
    warm = rc.warmup()
    if warm.get("status") != "warm" and not rc.RUNTIME_ARN:
        print("Runtime not reachable at %s" % rc.LOCAL_URL)
        print("  %s" % warm.get("error", ""))
        print("\nStart it with:  python3 agent/risk_agent.py")
        print("Or exercise everything with no model at all:")
        print("                python3 harness/demo_driver.py")
        return 1

    if warm.get("status") == "warm":
        print("Risk Advisor ready. model=%s  gateway=%s" % (warm.get("model"),
                                                            warm.get("mcp")))
        mem = warm.get("memory") or {}
        print("memory: configured=%s strategies=%s" % (mem.get("configured"),
                                                       ",".join(mem.get("strategies", []))))
        print("instrument: %s" % warm.get("instrument"))
    print("\nAsk anything about the seeded assessment. Ctrl-C to stop.\n")

    session = "cli-demo"
    while True:
        try:
            prompt = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not prompt:
            continue
        out = rc.invoke(prompt, session_id=session)
        if out.get("available") is False:
            print("\n(no assistance: %s — nothing is blocked)\n" % out.get("because"))
            continue
        print("\n%s\n" % out.get("result", ""))
        if out.get("disclosure"):
            print("  [%s]\n" % out["disclosure"])


if __name__ == "__main__":
    sys.exit(main())
