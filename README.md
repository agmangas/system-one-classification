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

```sh
python3 scripts/run_examples.py --example news_topics --case case-01
```

Use `--preview` to inspect the exact request without a running model. See the [query preparation guide](examples/query-guide.md) for descriptive options, explicit yes/no criteria, score interpretation and English-only input preparation.
