# Classification examples

Start with [news topics](news_topics.md) for a text classifier. Each example includes a complete request and labelled test cases. See the [query guide](query-guide.md) for writing instructions and criteria.

| Example                                       | Type          | Focus                                        |
| --------------------------------------------- | ------------- | -------------------------------------------- |
| [News topics](news_topics.md)                 | Choice        | Define categories                            |
| [Customer requests](customer_requests.md)     | Choice        | Ask precise questions                        |
| [Materials](materials.md)                     | Choice        | Normalize terms to canonical material concepts |
| [Refund detection](refund_detection.md)       | Noul (yes/no) | Define yes and no                            |
| [Evidence and claims](evidence.md)            | Choice        | Separate contradiction from missing evidence |
| [Message specificity](message_specificity.md) | Score         | Define ordered levels                        |

## Run examples

Start the [HTTP service](../README.md), then run from the repository root. The runner needs Python 3.12 and no extra packages.

```sh
# One case
python3 scripts/run_examples.py --example news_topics --case case-01

# One example, with JSON and HTML reports
python3 scripts/run_examples.py --example news_topics --output reports/news_topics.json

# All examples, with reports in reports/examples.{json,html}
task examples
```

Use `task examples EXAMPLE=materials` to select an example. Runner options:

- `--preview`: print requests without calling the service.
- `--verbose`: print every result.
- `--base-url URL`: use another server (default: `http://127.0.0.1:8000`).

Set `SYSTEM_ONE_API_KEY` if the service requires authentication. For curl, add `-H "Authorization: Bearer $SYSTEM_ONE_API_KEY"`.

## Read and compare reports

Open the HTML report directly in your browser. Filter results by example or outcome, and expand Query details for requests and probabilities. The JSON includes inputs, expected answers, responses, timings and errors. Expected answers stay local.

Choice and Noul report accuracy; Noul uses a 0.5 probability threshold. Score reports mean absolute error, where lower is better. Wrong predictions do not fail the run; invalid fixtures, malformed responses and unexpected HTTP errors do.

Rebuild HTML from saved JSON without calling the model:

```sh
task examples-report  # Uses reports/examples.json
task examples-report REPORT=reports/news_topics.json
```

Compare runs of the same examples, one per model:

```sh
python3 scripts/render_examples_report.py reports/von.json reports/qwen3.5-4b.json \
  reports/bonsai-4b.json --output reports/comparison.html
```

## Reproduce a run

Keep the repository revision, `uv.lock` and model manifests under `model/` fixed. Build an image, record its ID, then run the examples against it:

```sh
task image-build  # Add BACKEND=slm for Qwen/Bonsai
docker image inspect system-one-classification:local --format '{{.Id}}'
sh scripts/image_smoke.sh sha256:YOUR_IMAGE_ID reports/examples.json
```

Replace `sha256:YOUR_IMAGE_ID` with the returned ID. The script starts a temporary container with four CPUs and eight GiB of memory, then runs the SDK checks, every example and a latency benchmark. Reports under `reports/` record the image ID, architecture and runtime settings. Without the report path, the script runs only the SDK checks, as CI does.

For remote servers, pass `--runtime-metadata FILE` to the runner; otherwise `server_runtime` is null. Client architecture and `expected_profile` do not verify server settings. Compare weights revisions and fixture hashes across runs.

Measure latency separately:

```sh
python3 scripts/benchmark.py --example news_topics --case case-01 \
  --count 40 --output reports/benchmark.json
```

The benchmark excludes five warmup requests and reports timed samples, p50 and p95. Add `--max-p95 SECONDS` to fail runs above that limit.

## Add an example

Copy a JSON fixture in `examples/` and add a Markdown walkthrough. Match the fixture `id` to its filename and define `questions`. Give each case a unique `id`, a `state` and `expected` answers for every question.

Check requests with `--preview`, then run against the service. Keep expected answers out of model inputs.
