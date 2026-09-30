# Evidence and claims

Check whether a short record supports, contradicts, or leaves a claim unresolved.

Start the [HTTP service](../README.md), then send this request:

```sh
curl --fail-with-body -sS http://127.0.0.1:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "model": "system-one-cpu",
  "state": {
    "record": "The parcel was delivered on Tuesday.",
    "claim": "The parcel arrived on Monday."
  },
  "questions": {
    "relation": {
      "type": "choice",
      "instructions": "Using only the record, determine whether it supports the claim.",
      "criteria": {
        "supported": "The record provides evidence that the claim is true.",
        "contradicted": "The record provides evidence that conflicts with the claim.",
        "insufficient_evidence": "The record neither establishes the claim nor contradicts it; the needed fact is missing."
      }
    }
  }
}
JSON
```

Read `answers.relation.choice` for the selected label. The expected answer is `contradicted`: the record says Tuesday and the claim says Monday.

A record of a Monday dispatch leaves a claim of Tuesday arrival unresolved. Its expected label is `insufficient_evidence`. Keep the record and claim in separate fields and ask Von to use only the record.

## Compare the descriptions

Both variants use the same three labels. The prepared version adds definitions for each one.

```sh
# Run the case above
python3 scripts/run_examples.py --example evidence --case case-02 --variant prepared

# Compare every variant on all cases
python3 scripts/run_examples.py --example evidence --output reports/evidence.json
```

See [evidence.json](evidence.json) for all inputs and expected answers.

Add `--preview` to a runner command to print requests without contacting the service. See the [collection guide](README.md) for reports and the [query guide](query-guide.md) for preparation advice.
