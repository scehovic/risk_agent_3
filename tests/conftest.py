"""Pytest setup. No AWS, no network, no model calls in any tier below e2e.

    intelligence/risk_engine.py   the pure instrument engine
    intelligence/assurance.py     the gates, guardrails, findings, report, scoring
    mcp/index.py                  the tool layer (imports the engine)
    agent/risk_agent.py           the orchestrator (bedrock_agentcore stubbed)
    data/*.json,*.txt             the configured instrument

ONE TRAP WORTH KNOWING: this repo has a folder called `mcp/`, and the agent imports the
PyPI package also called `mcp`. So the repo root is deliberately NOT on sys.path — the
`mcp/` directory itself is, which makes `index` importable as a top-level module without
shadowing the real package. In the built image the question does not arise: staging
flattens everything into one directory and no `mcp/` folder exists.
"""
import pathlib
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

for p in (ROOT / "intelligence", ROOT / "mcp", ROOT / "agent"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture(scope="session")
def engine():
    import risk_engine
    return risk_engine


@pytest.fixture(scope="session")
def assurance():
    import assurance as mod
    return mod


@pytest.fixture(scope="session")
def tools():
    import index
    return index


@pytest.fixture(scope="session")
def assessment(engine):
    return engine.load_assessment()


@pytest.fixture(scope="session")
def answers(engine, assessment):
    return engine.answer_map(assessment)


@pytest.fixture(scope="session")
def context(assurance, assessment):
    return assurance.assessment_context(assessment)


def install_bedrock_stub():
    """A minimal bedrock_agentcore so importing the agent does not require the SDK."""
    if "bedrock_agentcore" in sys.modules:
        return
    mod = types.ModuleType("bedrock_agentcore")

    class BedrockAgentCoreApp:
        def entrypoint(self, fn):   # the @app.entrypoint decorator — identity
            self._entry = fn
            return fn

        def run(self):              # pragma: no cover — never called under test
            raise RuntimeError("app.run() not available under test")

    mod.BedrockAgentCoreApp = BedrockAgentCoreApp
    sys.modules["bedrock_agentcore"] = mod
