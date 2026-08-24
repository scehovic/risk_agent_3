"""Assemble the build contexts the CDK stack needs, at synth time.

Two artefacts:
  .build/agent/  — the Docker build context for the AgentCore Runtime image: the agent
                   modules, the pure engine, the data files and constraints.txt, all
                   FLATTENED into one directory so the agent's flat imports resolve inside
                   the container.
  .build/mcp/    — the MCP Lambda asset: index.py + the engine + the data files.

Pure file assembly — no AWS, no Docker, no network.

WHY FLATTENING MATTERS: the agent imports `session`, `memory`, `assurance` and
`risk_engine` as top-level modules. In the source tree they live in `agent/` and
`intelligence/`. Flattening is what makes one import style work in both places, and it is
also why the container has no `mcp/` directory to shadow the PyPI package of that name.
"""
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
BUILD = HERE / ".build"

DATA_FILES = [
    "instrument_tier1.json", "instrument_tier2.json", "instrument_tier3.json",
    "policies.json", "intake_rubric.json", "control_domains.json",
    "reference_lists.json", "seeded_assessment.json", "precedent_aggregates.json",
    "tool_schema.json", "meridian_assist_overview.txt",
]


def _reset(path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def _copy_data(dst):
    (dst / "data").mkdir(exist_ok=True)
    for name in DATA_FILES:
        src = ROOT / "data" / name
        if not src.is_file():
            raise FileNotFoundError("data/%s is missing; the instrument is incomplete" % name)
        shutil.copy(src, dst / "data" / name)


def stage_agent():
    """Docker build context for the agent runtime image."""
    dst = BUILD / "agent"
    _reset(dst)
    for f in (ROOT / "agent").glob("*"):
        if f.is_file():
            shutil.copy(f, dst / f.name)
    for f in (ROOT / "intelligence").glob("*.py"):
        if f.name != "__init__.py":
            shutil.copy(f, dst / f.name)
    shutil.copy(ROOT / "constraints.txt", dst / "constraints.txt")
    _copy_data(dst)
    return dst


def stage_mcp():
    """Lambda code asset for the MCP tool server."""
    dst = BUILD / "mcp"
    _reset(dst)
    shutil.copy(ROOT / "mcp" / "index.py", dst / "index.py")
    for f in (ROOT / "intelligence").glob("*.py"):
        if f.name != "__init__.py":
            shutil.copy(f, dst / f.name)
    _copy_data(dst)
    return dst
