# Materials classification

Classify a misspelled material name into six catalogue groups or `unknown`.

Start the [HTTP service](../README.md), then send this request:

```sh
curl --fail-with-body -sS http://127.0.0.1:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "model": "system-one-cpu",
  "state": "Misspelled material name: timbr",
  "questions": {
    "material": {
      "type": "choice",
      "instructions": "Classify the material named by the input.",
      "criteria": {
        "concrete": "Concrete, a mixture of cement, sand and aggregate. This catalogue also groups cement here.",
        "steel": "Steel, an iron alloy used for metal beams, bars and reinforcement.",
        "timber": "Timber or wood, including wooden boards and structural lumber.",
        "brick": "Brick, a fired clay block used to build walls.",
        "glass": "Glass, the hard transparent material used for window panes.",
        "stone": "Natural stone or rock, including granite, marble and limestone.",
        "unknown": "A material outside the catalogue: aluminum, plastic, copper, asphalt, gypsum, rubber, or another material that is not concrete, cement, steel, timber, brick, glass or stone."
      }
    }
  }
}
JSON
```

Read `answers.material.choice` for the selected label. The expected answer for `timbr` is `timber`. For `plasstic`, it is `unknown`, because plastic is outside the catalogue. Von can still choose the wrong label even with an explicit fallback.

## Compare the descriptions

The original query uses short labels. The reworded query describes each material and the fallback. This catalogue groups cement under concrete as a business rule.

All 37 materials cases belong to the evaluation set, including six Italian inputs that probe Von’s English-only limitation. The reworded descriptions reduced English accuracy from 24/31 to 9/31 in the [recorded run](results.md).

```sh
# Run the case above
python3 scripts/run_examples.py --example materials --case en-timber-1 --variant prepared

# Compare every variant on all cases
python3 scripts/run_examples.py --example materials --output reports/materials.json
```

See [materials.json](materials.json) for all inputs and expected answers.

Add `--preview` to a runner command to print requests without contacting the service. See the [collection guide](README.md) for reports and the [query guide](query-guide.md) for preparation advice.
