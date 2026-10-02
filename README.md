# Classification and Scoring Service

The *Classification and Scoring Service* is a CPU-only HTTP service for classification, yes/no questions, and scoring. Submit data with instructions and criteria to receive structured answers that include probabilities or scores. You can choose from three different models:

* [Von](https://github.com/wfzyx/von)
* Qwen3.5-4B
* Bonsai-4B

All models are accessed through the same API. The Docker images include the model weights for offline use.

The [examples](examples/README.md) include complete requests and labelled cases for testing predictions and comparing models.

> [!NOTE]
> **Why this project?** I often want to add small-scale features powered by language models to existing workflows in our services, especially for processing and interpreting user-provided data. For example, a common need is vocabulary normalization (mapping arbitrary concepts to an ontology). Cloud-based providers are not viable due to cost or data sovereignty, and running a GPU-based model locally is too expensive and overkill. This service provides an off-the-shelf solution that works within typical computational constraints: CPU-only environments, limited memory and few cores.

## TypeSafe protocol compatibility

[TypeSafe calls its approach “System One”](https://docs.typesafe.ai/concepts/system-one): models answer focused questions with structured decisions and probabilities. The name draws on the idea of fast, intuitive thinking popularized by Daniel Kahneman. The API supports selecting an option (`choice`), estimating the probability of “yes” (`noul`), and scoring against defined levels (`score`).

We implement [TypeSafe’s System One HTTP protocol](https://docs.typesafe.ai/api) for interoperability with clients that use this request and response format. Send `model`, `state`, and `questions` to `POST /v1/systemone`; responses contain `answers` and `usage`. To connect, use this service’s base URL and the model ID `system-one-cpu`.

## Run the service

```sh
docker run --rm -p 8000:8000 --cpuset-cpus=0-3 --memory=8g \
  ghcr.io/agmangas/system-one-classification:latest
```

Once `GET /ready` responds with a 200, you can test the service using this example:

```sh
curl --fail-with-body -sS http://127.0.0.1:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "model": "system-one-cpu",
  "state": "The track builds slowly over a steady four-on-the-floor groove, adding synth layers and subtle melodic changes without a big euphoric breakdown.",
  "questions": {
    "style": {
      "type": "choice",
      "instructions": "Which trance style best matches this track description?",
      "criteria": {
        "uplifting_trance": "Energetic trance with soaring melodies, dramatic breakdowns and euphoric peaks.",
        "progressive_trance": "Trance with a steady groove, gradually evolving layers and subtle melodic development."
      }
    }
  }
}
JSON
```

A response might look like this:

```json
{
  "model": "system-one-cpu",
  "answers": {
    "style": {
      "type": "choice",
      "choice": "progressive_trance",
      "probabilities": {
        "uplifting_trance": 0.0693,
        "progressive_trance": 0.9307
      },
      "confidence": 0.861
    }
  },
  "usage": {
    "input_tokens": 85,
    "output_tokens": 1
  }
}
```

The image supports `linux/amd64` and `linux/arm64`. `latest` is the newest release; to keep the same models across releases, replace it with a [version](#versions) such as `0.1`.

- `GET /ready`: ready after the model loads.
- `GET /health`: application liveness.
- `GET /v1/models`: model and backend version metadata.
- `/docs`: OpenAPI documentation.
- Set `SYSTEM_ONE_API_KEY` to require bearer authentication.

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

> [!TIP]
> To run SLM locally, install llama.cpp, then run `SYSTEM_ONE_BACKEND=slm task weights` and `task serve SYSTEM_ONE_BACKEND=slm`. Build the SLM Docker image with: `task image-build BACKEND=slm`.

## Versions

Each release publishes `<version>` and `<version>-slm` images and moves the `<major>.<minor>` and `latest` tags (and their `-slm` variants) to it. Patch releases keep the same models and API.

| Release | Von             | Qwen3.5-4B         | Bonsai-4B        |
| ------- | --------------- | ------------------ | ---------------- |
| 0.1.0   | 1.2 (`411c444`) | Q4_K_M (`e87f176`) | Q1_0 (`78f2c2b`) |

The hashes are the Hugging Face weights revisions pinned in `model/`.

## Scale up

Each container runs one copy of the model and serves one request at a time. On a bigger machine:

- Von gains little from more than 4 cores at its default 512-token input cap. Run more containers instead.
- The SLM gets faster with more threads, though not in proportion. Set `SYSTEM_ONE_SLM_THREADS` to the container's CPU count.
- Leave `SYSTEM_ONE_MAX_CONCURRENT` at 1. Neither backend runs inferences in parallel, so raising it doesn't add throughput.

Give each container its CPUs with `--cpuset-cpus` instead of `--cpus`. OpenVINO starts one thread per core it can see, so under `--cpus` on a larger host the kernel throttles Von and requests take several times longer.

For more requests per second, run several containers on separate cores (`--cpuset-cpus=0-3`, `--cpuset-cpus=4-7`, and so on) behind a load balancer that checks `GET /ready`. Each container loads its own copy of the model, so memory decides how many fit.

For example, an SLM container on 16 cores:

```sh
docker run --rm -p 8000:8000 --cpuset-cpus=0-15 --memory=8g \
  -e SYSTEM_ONE_SLM_THREADS=16 \
  ghcr.io/agmangas/system-one-classification:latest-slm
```
