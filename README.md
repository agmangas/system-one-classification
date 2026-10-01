# System One CPU classification

Run pinned [Von](https://github.com/wfzyx/von) weights on a CPU and answer classification, yes/no and scoring questions over HTTP. The Docker image bundles the weights, so startup needs no model download.

Start with the [news-topic walkthrough](examples/news_topics.md), or explore all [six self-contained examples](examples/README.md): materials, news topics, customer requests, refund detection, evidence checks and message scoring. Each includes a complete request and a set of labelled cases.

## Run the service

```sh
docker run --rm -p 8000:8000 --cpus=4 --memory=8g \
  ghcr.io/agmangas/system-one-classification:latest
```

The image supports `linux/amd64` and `linux/arm64`. For reproducible evaluation, replace `latest` with a recorded image digest; see the [reproduction instructions](examples/README.md#reproduce-a-run).

- `GET /ready`: ready after the model loads.
- `GET /health`: application liveness.
- `GET /v1/models`: model and backend version metadata.
- `/docs`: OpenAPI documentation.
- Set `SYSTEM_ONE_API_KEY` to require bearer authentication.

Send `model`, `state` and `questions` to `POST /v1/systemone`. The model ID is `system-one-cpu`; responses contain `answers` and `usage`.

## Choose a model

Each release ships two images with the same API. Clients send the same requests to either and get the same response shape; only the `/v1/models` metadata differs.

| Tags | Model | Runtime |
|---|---|---|
| `latest`, `<version>` | Von 1.2, a ModernBERT-large encoder | PyTorch and OpenVINO |
| `latest-slm`, `<version>-slm` | Qwen3.5-4B (Q4_K_M GGUF) or Bonsai-4B (1-bit GGUF), small language models | llama.cpp |

The SLM image bundles both models, and `SYSTEM_ONE_SLM_MODEL` picks one: `qwen3.5-4b` (the default) or `bonsai-4b`. On 4 arm64 CPUs, Bonsai-4B answered in about half the time with a model a quarter the size, but it was less accurate on most bundled examples.

The SLM image shows the model the state, the question and options labelled `A`, `B`, …, then reads the probability of each label as the model's next token. It never generates text, so every answer is a valid label with a full probability distribution. Differences from Von:

- Probabilities are not calibrated.
- Each question's whole prompt (rules, state, question and options) must fit in `SYSTEM_ONE_SLM_CTX_SIZE` tokens (default 1,024). A longer request gets HTTP 422.
- `SYSTEM_ONE_SLM_THREADS` should match the container's CPU count (the image sets 4). llama.cpp does not see Docker's `--cpus` limit.

To serve the SLM locally, install llama.cpp (for example `brew install llama.cpp`), then run `SYSTEM_ONE_BACKEND=slm task weights` and `task serve SYSTEM_ONE_BACKEND=slm`. To build its image, run `task image-build BACKEND=slm`.

```sh
python3 scripts/run_examples.py --example news_topics --case case-01
```

Use `--preview` to inspect the exact request without a running model. See the [query preparation guide](examples/query-guide.md) for descriptive options, explicit yes/no criteria, score interpretation and English-only input preparation.
