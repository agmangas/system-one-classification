FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/agmangas/system-one-classification"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    SYSTEM_ONE_MAX_CONCURRENT=1

# Run the model on the CPU through OpenVINO,
# which Von's authors report is about 1.6x faster than PyTorch on the same cores.
ENV VON_DEVICE=openvino:cpu
# Return the calibrated yes/no (Noul) probability unchanged so callers
# can pick their own threshold (Von's default moves every answer below 0.2 or above 0.8).
ENV VON_NOUL_DECISION=raw
# Turn off Von's chains, the extra calculation steps it runs on inputs containing numbers,
# so every answer comes from one calibrated model pass.
ENV VON_CHAINS_DIR=off
# Cap each request's `state` at 512 tokens (the model accepts 8,192), because answers get less
# accurate as inputs grow and a long input delays every request queued behind it.
ENV VON_MAX_STATE_TOKENS=512
# Reject a `state` longer than that limit with HTTP 422 instead of cutting out its middle,
# so every answer uses the full input.
ENV VON_ON_OVERFLOW=refuse

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir uv==0.10.10

COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev

COPY scripts/download_weights.py ./scripts/download_weights.py
COPY model ./model
RUN .venv/bin/python scripts/download_weights.py

COPY scripts ./scripts
COPY examples ./examples
COPY LICENSE THIRD_PARTY_NOTICES.md ./
COPY licenses ./licenses

RUN useradd --create-home --uid 10001 app

ENV HOME=/home/app \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD .venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"
CMD [".venv/bin/uvicorn", "system_one_service.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
