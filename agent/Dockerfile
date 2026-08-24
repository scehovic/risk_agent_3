# AgentCore Runtime image for the Front Door Risk Advisor.
#
# ARM64 to match the runtime's platform. The build context is assembled by
# `cdk/staging.py`, which flattens the agent module, the pure engine and the data files
# into one directory so the flat imports resolve inside the container.
FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# AgentCore invokes the container on 8080.
EXPOSE 8080

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    AGENT_OBSERVABILITY_ENABLED=true

# THE OBSERVABILITY GOTCHA, PAID FOR ONCE ALREADY:
# installing `aws-opentelemetry-distro` is NOT enough. The container MUST launch under
# `opentelemetry-instrument` or ZERO SPANS are emitted, and the failure is silent — the
# agent works perfectly and the GenAI Observability page stays empty.
CMD ["opentelemetry-instrument", "python", "-u", "risk_agent.py"]
