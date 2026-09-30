FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/agmangas/system-one-classification"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    VON_DEVICE=openvino:cpu \
    VON_NOUL_DECISION=raw \
    VON_CHAINS_DIR=off \
    VON_ON_OVERFLOW=refuse \
    VON_MAX_STATE_TOKENS=512 \
    SYSTEM_ONE_MAX_CONCURRENT=1

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

COPY scripts/validate_materials.py scripts/benchmark.py scripts/sdk_smoke.py ./scripts/
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
