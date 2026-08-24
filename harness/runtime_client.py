"""Talk to the Risk Advisor runtime — locally on :8080, or deployed via AgentCore.

Throwaway harness. The production UI is somebody else's job; this exists so the runtime can
be exercised end to end without one.
"""
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOCAL_URL = os.environ.get("LOCAL_AGENT_URL", "http://127.0.0.1:8080/invocations")
RUNTIME_ARN = os.environ.get("RUNTIME_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")


def load_assessment():
    """The assessment record the caller MUST supply. The agent refuses without one (G-65)."""
    return json.loads((ROOT / "data" / "seeded_assessment.json").read_text())


def invoke_local(prompt, session_id="demo", assessment=None):
    body = json.dumps({"prompt": prompt, "session_id": session_id,
                       "assessment": assessment or load_assessment()}).encode()
    req = urllib.request.Request(LOCAL_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def invoke_deployed(prompt, session_id="demo", assessment=None):
    import boto3
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": prompt, "session_id": session_id,
                            "assessment": assessment or load_assessment()}).encode())
    raw = resp["response"].read() if hasattr(resp["response"], "read") else resp["response"]
    return json.loads(raw)


def invoke(prompt, session_id="demo", assessment=None):
    """Deployed if RUNTIME_ARN is set, otherwise local."""
    fn = invoke_deployed if RUNTIME_ARN else invoke_local
    try:
        return fn(prompt, session_id, assessment)
    except Exception as exc:
        # The harness fails open too, so a demo never dies on a transport error.
        return {"result": "", "available": False, "blocks_nothing": True,
                "because": "could not reach the runtime (%s: %s)"
                           % (type(exc).__name__, exc)}


def warmup():
    try:
        body = json.dumps({"type": "warmup"}).encode()
        req = urllib.request.Request(LOCAL_URL, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        return {"status": "unreachable", "error": str(exc)}


if __name__ == "__main__":
    print(json.dumps(invoke(" ".join(sys.argv[1:]) or "What still needs answering?"),
                     indent=2))
