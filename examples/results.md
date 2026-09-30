# Observed example results

Reworded queries improved news and evidence classification, but worsened materials classification and message specificity in this historical run. The materials fixture has since been replaced with ordinary names and descriptions; its results below do not measure the current example.

| English example | Cases | Original query | Reworded query |
| --- | ---: | ---: | ---: |
| News topics | 8 | 5/8 correct | 8/8 correct |
| Customer requests | 8 | 8/8 correct | 8/8 correct |
| Refund detection | 8 | 8/8 correct | 8/8 correct |
| Evidence and claims | 8 | 5/8 correct | 6/8 correct |
| Message specificity | 8 | MAE 1.137 | MAE 1.354 |
| Materials (previous fixture) | 31 | 24/31 correct | 9/31 correct |

Lower mean absolute error (MAE) is better for Score. All other rows count correct classifications. Each example used its eight evaluation cases, except materials, which used the 31 English cases from the previous 37-case, typo-heavy fixture. These small sets give examples of model behaviour, not general accuracy estimates. No results for the replacement materials fixture are recorded here.

The specificity request in the walkthrough returned 0.68 against an expected level of 3. Longer descriptions did not guarantee better answers.

For the Italian input `legno`, direct classification returned `unclear`. Translation and glossary lookup both sent `wood` and returned `timber`. Von remains English-only; this example uses a fixed translation and does not measure a live translator.

## Run the current examples

The first complete run used the pinned model with OpenVINO CPU on Linux arm64, four CPUs, and eight GiB of memory. All 291 requests returned valid responses. Nine preparations lacked a translation or glossary match and sent no request. These totals describe the original fixtures, including the previous materials cases. Inputs and query variants were fixed before measurement.

Run `task examples` to measure the current fixtures and write `reports/examples.json`. This does not reproduce the historical materials scores or request totals above. Use `task image-smoke` to also record runtime metadata, SDK checks, and warm latency. See [reproduction instructions](README.md#reproduce-a-run).

The recorded run used:

- Weights revision: `411c44401cccddd792f341edfe033ea834557d13`
- Local image ID: `sha256:81da2b4765505e70851f7bed1f3652967296fc89d3baaf8c8fa4474d7109fe38`

The image ID identifies a local build. For comparisons, check the fixture hashes and runtime settings in the JSON reports. Probabilities and timings may differ across architectures and runtime versions.
