# Von examples

Start with [news topics](news_topics.md) for a small text classifier. Each walkthrough includes a complete request you can copy.

| Example | Type | Focus |
| --- | --- | --- |
| [News topics](news_topics.md) | Choice | Define categories clearly |
| [Customer requests](customer_requests.md) | Choice | Ask a precise question |
| [Materials](materials.md) | Choice | Classify material names and descriptions, including unlisted materials |
| [Refund detection](refund_detection.md) | Noul | Describe both yes and no |
| [Evidence and claims](evidence.md) | Choice | Separate contradiction from missing evidence |
| [Message specificity](message_specificity.md) | Score | Define ordered levels |

Each example sends one query written with the [query guide](query-guide.md) advice.

## Run an example

Start the [HTTP service](../README.md), then run these commands from the repository root. The runner needs Python 3.12 and no extra packages.

```sh
# One case
python3 scripts/run_examples.py --example news_topics --case case-01

# All news cases
python3 scripts/run_examples.py --example news_topics --output reports/news_topics.json

# All examples
task examples
```

Use `--base-url` for another server and `SYSTEM_ONE_API_KEY` for authentication. For curl requests, add `-H "Authorization: Bearer $SYSTEM_ONE_API_KEY"` if needed.

Add `--preview` to inspect requests without HTTP calls. A single case prints its request as JSON you can pipe to curl; a wider selection prints a list.

Use `task examples EXAMPLE=materials` to run the materials example through the shared task.

## Read the report

`task examples` writes `reports/examples.html` alongside `reports/examples.json`.
Open the HTML file in your browser: it works offline and needs no web server.
Any runner command with `--output` creates both files.

The report shows an overview, then each input, expected answer, and actual answer.
Open **Query details** to see the wording and probabilities. Filter by example,
answers differing from expected, or failed requests.

To turn an existing JSON report into HTML without calling the model:

```sh
task examples-report
task examples-report REPORT=reports/examples-amd64.json
```

The overview counts all inputs in the run; search and the **Show** filter apply
to individual results.

The terminal prints summaries; `--verbose` prints every outcome. The JSON report includes inputs, expected answers, requests, responses, timings, and errors. Expected answers stay local and are never sent to Von.

The JSON and terminal group results by example:

- Choice reports accuracy.
- Noul reports accuracy using a probability threshold of 0.5.
- Score reports mean absolute error from the expected level. Lower is better.

Wrong predictions appear in the report without failing the run. Invalid fixtures, malformed responses, and unexpected HTTP errors cause a nonzero exit status.

## Reproduce a run

Keep the repository revision, `uv.lock`, and `model/weights.json` fixed. After [building the image](../README.md), get its ID and run the smoke check:

```sh
docker image inspect system-one-classification:local --format '{{.Id}}'
# Replace sha256:YOUR_IMAGE_ID with the returned value
sh scripts/image_smoke.sh sha256:YOUR_IMAGE_ID
```

The smoke check runs all examples, checks SDK compatibility and overflow refusal, and measures warm latency. It creates and removes its own container with four CPUs and eight GiB of memory. Reports under `reports/` record the image ID, architecture, resource limits, and settings. CI uploads reports for amd64 and arm64.

Keep the bundled settings: raw Noul probabilities, chains off, a 512-token state limit, and overflow refusal. Oversized states receive HTTP 422.

For a remote server, supply `--runtime-metadata FILE` to record its runtime. Otherwise, `server_runtime` is null. The report’s client architecture and `expected_profile` do not verify the server’s settings. Use the reported weights revision and fixture hashes when comparing runs.

To measure latency after warmup:

```sh
python3 scripts/benchmark.py --example news_topics --case case-01 \
  --count 40 --output reports/benchmark.json
```

The benchmark excludes five warmup requests and reports all timed samples, p50, and p95. Use `--max-p95 SECONDS` if you want a latency limit that fails the run.

## Add an example

Copy an existing JSON fixture and add a Markdown walkthrough. Give the fixture an `id` matching its filename. Each fixture needs complete `questions`; each case needs an `id`, a `state` and `expected` answers.

Preview the requests, then run them against the pinned service. Keep expected answers out of model inputs.
