# Multilingual preparation

Von is English-only. This example prepares Italian and Spanish material descriptions in English before classification.

Start the [HTTP service](../README.md), then send this request:

```sh
curl --fail-with-body -sS http://127.0.0.1:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "model": "system-one-cpu",
  "state": "wood",
  "questions": {
    "material": {
      "type": "choice",
      "instructions": "Identify the single material described by the text.",
      "criteria": {
        "concrete": "Concrete, a building material made of cement, sand and aggregate.",
        "steel": "Steel, an iron alloy used for metal beams, bars and reinforcement.",
        "timber": "Timber or wood, including wooden boards and structural lumber.",
        "brick": "Brick, a fired clay block used to build walls.",
        "glass": "Glass, the hard transparent material used for window panes.",
        "stone": "Natural stone or rock, including granite, marble and limestone.",
        "unknown": "An explicitly named material outside this catalogue, such as copper, plastic, aluminum or rubber.",
        "unclear": "No single material can be identified: the material is unspecified or several alternatives remain possible."
      }
    }
  }
}
JSON
```

The original input is Italian `legno`. Its fixed English translation is `wood`, and its expected label is `timber`. Read the selected label from `answers.material.choice`.

## Compare three ways to prepare the input

All three variants use the same question and categories:

- `direct` sends the original text to show what happens with unsupported languages.
- `translated` sends a fixed English translation stored with the case.
- `glossary` looks up the original term and sends its English equivalent.

The fixture contains every translation and glossary entry, so no translation service is needed. A missing translation or glossary match causes the runner to skip the request and record why.

```sh
# Run the case above
python3 scripts/run_examples.py --example multilingual --case it-wood --variant translated

# Compare every variant on all cases
python3 scripts/run_examples.py --example multilingual --output reports/multilingual.json
```

## What the glossary handles

The glossary ignores case and extra whitespace and normalizes Unicode while preserving accents. Spanish `HORMIGÓN` therefore matches `hormigón` and becomes `concrete`.

Spelling aliases must be listed: Italian `legnno` is included, but other misspellings are not guessed. `rame` becomes `copper`, which Von must then classify as outside the catalogue.

Use translations for sentences, negations, or ambiguous alternatives. For example, “Il pannello è di vetro, non di acciaio” becomes “The panel is glass, not steel.”

Compare how many inputs each method can prepare as well as its classification accuracy. Correct answers on direct non-English inputs do not establish language support. These fixed translations also tell us nothing about the quality of a live translator.

See [multilingual.json](multilingual.json) for all inputs, translations, and glossary entries.

Add `--preview` to a runner command to print requests without contacting the service. See the [collection guide](README.md) for reports and the [query guide](query-guide.md) for preparation advice.
