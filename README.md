# System One CPU classification

System One is a CPU-only HTTP service for classification, yes/no questions and scoring. Send data with instructions and criteria, and get structured answers with probabilities or scores. Choose [Von](https://github.com/wfzyx/von), Qwen3.5-4B or Bonsai-4B behind the same API; the Docker images bundle the model weights for offline use.

The [examples](examples/README.md) include complete requests and labelled cases for testing predictions and comparing models.

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

| Tags                          | Model                                                                     | Runtime              |
| ----------------------------- | ------------------------------------------------------------------------- | -------------------- |
| `latest`, `<version>`         | Von 1.2, a ModernBERT-large encoder                                       | PyTorch and OpenVINO |
| `latest-slm`, `<version>-slm` | Qwen3.5-4B (Q4_K_M GGUF) or Bonsai-4B (1-bit GGUF), small language models | llama.cpp            |

The SLM image includes both models. Select which to use with `SYSTEM_ONE_SLM_MODEL` (`qwen3.5-4b`, default, or `bonsai-4b`). Bonsai-4B tends to run faster and is smaller.

In SLM mode, questions are mapped to label tokens (`A`, `B`, etc.) and the model picks probabilities for each, never plain text. Key differences from Von:

- Probabilities aren’t calibrated.
- The whole prompt (everything including rules and options) must fit in `SYSTEM_ONE_SLM_CTX_SIZE` tokens (default 1,024), or you’ll get HTTP 422.
- Set `SYSTEM_ONE_SLM_THREADS` to match CPU count (default 4). Note: llama.cpp ignores Docker’s `--cpus` flag.

> [!TIP]
> To run SLM locally, install llama.cpp, then run `SYSTEM_ONE_BACKEND=slm task weights` and `task serve SYSTEM_ONE_BACKEND=slm`. Build the SLM Docker image with: `task image-build BACKEND=slm`.
