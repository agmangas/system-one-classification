# Materials classification

Classify a material name or short description into six catalogue groups or `unknown`. For example, `wood` and `oak floorboards` both belong to `timber`, while `plastic` is outside the catalogue.

Put the text entered by the user directly in `state`. The app does not need to know its material group or whether it contains a typo.

Start the [HTTP service](../README.md), then send this request:

```sh
curl --fail-with-body -sS http://127.0.0.1:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "model": "system-one-cpu",
  "state": "oak floorboards",
  "questions": {
    "material": {
      "type": "choice",
      "instructions": "Which catalogue group matches this material? This catalogue groups cement with concrete.",
      "criteria": {
        "concrete": "Concrete, made from cement, sand and aggregate. This group also includes cement.",
        "steel": "Steel, an iron alloy used for beams and reinforcement bars.",
        "timber": "Timber or wood, used for boards, flooring and furniture.",
        "brick": "Brick, a fired clay block used to build walls.",
        "glass": "Glass, used for window panes and bottles.",
        "stone": "Natural stone, such as granite, marble and limestone.",
        "unknown": "A material outside the concrete, steel, timber, brick, glass and stone groups, such as plastic, copper or aluminum."
      }
    }
  }
}
JSON
```

Read `answers.material.choice` for the selected label. The expected answer here is `timber`, because oak is wood.

## Example inputs

| Input (`state`) | Expected label | Why |
| --- | --- | --- |
| `wood` | `timber` | A common name for the material. |
| `oak floorboards` | `timber` | A product description naming a type of wood. |
| `steel reinforcement bars` | `steel` | The description names the material. |
| `granite` | `stone` | Granite is a natural stone. |
| `cement` | `concrete` | This catalogue explicitly groups cement with concrete. |
| `plastic` | `unknown` | Plastic is outside the six catalogue groups. |
| `copper pipe` | `unknown` | Copper is also outside the catalogue. |
| `brik` | `brick` | A simple typo for brick. |

These are expected answers for checking the model, not guaranteed predictions. `unknown` means the material is outside this catalogue; it does not mean the input is misspelled.

## About the descriptions

Each group has a definition with examples, and the question states the cement-to-concrete catalogue rule.

The fixture has 16 cases. Most are ordinary names and descriptions; only two contain simple typos.

```sh
# Run the case above
python3 scripts/run_examples.py --example materials --case case-11

# Run all cases
python3 scripts/run_examples.py --example materials --output reports/materials.json
```

See [materials.json](materials.json) for all inputs and expected answers.

Add `--preview` to a runner command to print requests without contacting the service. See the [collection guide](README.md) for reports and the [query guide](query-guide.md) for preparation advice.
