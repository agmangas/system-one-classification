# Build one image per backend with `--target slm` or `--target von` (the default).

# llama.cpp release v0.5.0: prebuilt CPU server for amd64 and arm64 that picks its CPU kernels at run time.
FROM ghcr.io/ggml-org/llama.cpp:server-b11146@sha256:a94b642b3e2620749bf2ff5672df922c23a6202710e54a8f7667e58df70aba5a AS llama-cpp

# Trixie, because the llama.cpp binaries need glibc 2.39 or later (bookworm has 2.36).
FROM python:3.12-slim-trixie AS slm

LABEL org.opencontainers.image.source="https://github.com/agmangas/system-one-classification"
LABEL org.opencontainers.image.licenses="Apache-2.0"

# LD_LIBRARY_PATH lets llama-server find its shared libraries. The upstream image finds them
# only because it runs from their directory.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    SYSTEM_ONE_MAX_CONCURRENT=1 \
    SYSTEM_ONE_BACKEND=slm \
    PATH=/opt/llama:$PATH \
    LD_LIBRARY_PATH=/opt/llama

# Cap each question's prompt (rules, state, question and options) at 1,024 tokens.
# Longer requests get HTTP 422, and short prompts keep answers within about 5 s on 4 CPUs.
ENV SYSTEM_ONE_SLM_CTX_SIZE=1024
# Serve one of the bundled models, named after its manifest in model/slm/: qwen3.5-4b or bonsai-4b.
ENV SYSTEM_ONE_SLM_MODEL=qwen3.5-4b
# Match the 4 CPUs the image is tested with. llama.cpp ignores Docker's CPU limit and would
# otherwise start one thread per host core; set this to the container's CPU count.
ENV SYSTEM_ONE_SLM_THREADS=4

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libssl3t64 libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir uv==0.10.10

COPY --from=llama-cpp /app/ /opt/llama/
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
    HF_HUB_OFFLINE=1

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD .venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"
CMD [".venv/bin/uvicorn", "system_one_service.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

FROM python:3.12-slim-bookworm AS von

LABEL org.opencontainers.image.source="https://github.com/agmangas/system-one-classification"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    SYSTEM_ONE_MAX_CONCURRENT=1 \
    SYSTEM_ONE_BACKEND=von

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
RUN uv sync --frozen --no-dev --group von

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
