# Materials concept normalization

Normalize a material name or short description to a canonical concept in a small Wikidata vocabulary. For example, `timber` and `oak floorboards` both map to the wood concept, `Q287`.

The vocabulary contains six concepts, with names and short definitions supplied in the request. Keep the question short and put the definitions in the choices. Put the user's text directly in `state`; no spelling correction or Wikidata lookup is needed before calling the service.

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
      "instructions": "Which material is named or described in the input?",
      "criteria": {
        "Q22657": "Concrete, a mixture of cement, sand and aggregate.",
        "Q45190": "Cement, a binder for mortar and concrete.",
        "Q11427": "Steel, an iron-carbon alloy.",
        "Q287": "Wood or timber, the material from trees.",
        "Q41177": "Granite, an igneous rock.",
        "Q40861": "Marble, a metamorphic rock.",
        "unknown": "A clearly identified material outside this vocabulary of concrete, cement, steel, wood, granite and marble.",
        "ambiguous": "Insufficient information to identify one material, or more than one distinct material is named."
      }
    }
  }
}
JSON
```

Read `answers.material.choice` for the selected concept ID. The expected answer here is `Q287` (wood): this vocabulary identifies the base material, ignoring product form and wood species.

## Example inputs

| Input (`state`) | Expected concept or fallback | Why |
| --- | --- | --- |
| `concrete` | [Q22657](https://www.wikidata.org/wiki/Q22657) (concrete) | A canonical material name. |
| `cement` | [Q45190](https://www.wikidata.org/wiki/Q45190) (cement) | Cement and concrete are distinct concepts. |
| `timber` | [Q287](https://www.wikidata.org/wiki/Q287) (wood) | An alternative name for the material. |
| `oak floorboards` | `Q287` (wood) | Species and product form do not change the base material. |
| `steel reinforcement bars` | [Q11427](https://www.wikidata.org/wiki/Q11427) (steel) | A product description naming its material. |
| `steeel` | `Q11427` (steel) | A simple typo. |
| `granite` | [Q41177](https://www.wikidata.org/wiki/Q41177) (granite) | A specific stone, with its own concept. |
| `marble tiles` | [Q40861](https://www.wikidata.org/wiki/Q40861) (marble) | Marble stays distinct from granite. |
| `limestone slab` | `unknown` | A named stone outside this vocabulary. |
| `plastic` | `unknown` | This vocabulary contains no plastics. |
| `stone tiles` | `ambiguous` | The stone could be granite, marble or an unlisted material. |
| `steel or wood` | `ambiguous` | No single material is identified. |

`unknown` means a material is outside this selected vocabulary; `ambiguous` means the input does not identify one material. These are application outcomes, not Wikidata concepts.

The twelve cases illustrate normalization, not benchmark performance. Expected answers are supplied for checking predictions and are not guaranteed model outputs.

## Run the example

```sh
# Run the case above
python3 scripts/run_examples.py --example materials --case case-04

# Run all cases
python3 scripts/run_examples.py --example materials --output reports/materials.json
```

See [materials.json](materials.json) for all inputs and expected answers.

Add `--preview` to a runner command to print requests without contacting the service. See the [collection guide](README.md) for reports and the [query guide](query-guide.md) for preparation advice.
