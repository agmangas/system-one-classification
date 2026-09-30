# System One CPU classification

This service runs pinned [Von](https://github.com/wfzyx/von) weights on a CPU and answers choice, yes/no, and score questions over HTTP. The Docker image includes the weights, so startup needs no model download.

## Run the image

```sh
docker run --rm -p 8000:8000 --cpus=4 --memory=8g \
  ghcr.io/agmangas/system-one-classification:latest
```

The image targets `linux/amd64` and `linux/arm64`. `GET /ready` returns 200 after the model loads and OpenVINO compiles. `GET /health` checks the process, `GET /v1/models` shows the model alias and backend version, and `/docs` serves OpenAPI. Set `SYSTEM_ONE_API_KEY` to require a bearer token for decisions.

Send `model`, `state`, and `questions` to `POST /v1/systemone`. The response contains `answers` and `usage`. The public model ID is `system-one-cpu`; `GET /v1/models` carries the Von and weight revisions. Choice and score take one model pass per question. A yes/no (`noul`) question takes one pass when you describe both `true` and `false`; without criteria, Von runs a second pass to correct bias. This image disables Von's optional chains.

This example uses six material labels and an `unknown` rejection result:

```sh
curl -sS http://localhost:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "system-one-cpu",
    "state": "Misspelled material name: alumnium",
    "questions": {
      "material": {
        "type": "choice",
        "instructions": "Classify the material named by the input.",
        "criteria": {
          "concrete": "concrete",
          "steel": "steel",
          "timber": "timber",
          "brick": "brick",
          "glass": "glass",
          "stone": "stone",
          "unknown": "Aluminum, plastic, copper, or other unlisted materials"
        }
      }
    }
  }'
```

The model scores `unknown` alongside the six labels in one pass. Von's probabilities are model estimates; this service has not calibrated them for your domain. English is the supported language. Italian inputs are included in the fixture to measure the compromise.

## Develop

All local entry points use [Task](https://taskfile.dev/):

```sh
task setup             # Install pinned dependencies
task weights           # Download and verify pinned local weights
task serve             # Start the local HTTP API
task check             # Ruff lint and format checks plus pytest
task fmt               # Apply Ruff formatting and import sorting
task materials         # Run the HTTP material fixture and save every result
task benchmark         # Warm short-request p95 check
task image-build       # Build the local bundled image
task image-smoke       # Check the image with 4 CPUs and 8 GiB
task image-up          # Start the image on localhost:18080
task image-down        # Stop the local image
task sdk-smoke          # Check Von HTTP SDK compatibility
```

The [material fixture](examples/materials.json) has 24 English typos of the six labels, six misspelled names outside the list, one `cemant` case scored as concrete for this practical grouping, and six Italian typos. The example sends each name unchanged after the prefix `Misspelled material name:`. `task materials` writes predictions and probabilities to `reports/materials.json`.

On the local ARM64 image, Von scored 24/31 English cases (77.4%): 22/24 label typos, 1/6 out-of-set names, and the `cemant` case. It scored 1/6 Italian cases. These numbers describe this small fixture, not general accuracy. The workflow uploads the result from each architecture and checks the API contract and latency before publishing; accuracy is reported without a release threshold.

Use at least 8 GiB of memory. Startup used about 5 GiB when sampled on the local ARM64 container. The short example measured 0.29 seconds p95 over 40 warm requests with four CPUs; the workflow requires p95 below one second. The service refuses states above its configured 512-token limit.

## Publish

GitHub Actions runs checks and native `amd64` and `arm64` image builds on main, version tags, pull requests, and manual runs. It validates both images before pushing main and version tags to GHCR. Docker metadata generates branch, commit, semantic version, and `latest` tags; the final job combines the two architectures and checks an anonymous pull. Pull requests build and test without publishing.

The image includes the [Von license](licenses/VON-LICENSE.md), [ModernBERT license](licenses/MODERNBERT-LICENSE), and [third-party notices](THIRD_PARTY_NOTICES.md). Both upstream model cards list the weights under Apache 2.0. This project is independently maintained.
