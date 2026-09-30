# Message specificity

Rate how much useful detail a customer message contains, from 0 to 3.

Start the [HTTP service](../README.md), then send this request:

```sh
curl --fail-with-body -sS http://127.0.0.1:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "model": "system-one-cpu",
  "state": "In the calendar app, create an event, set it to repeat daily, then click Save. The app closes.",
  "questions": {
    "specificity": {
      "type": "score",
      "instructions": "Rate the specificity of the message. Choose the highest level whose description is satisfied.",
      "criteria": [
        "Generic enquiry; no product is named and no concrete issue or request is stated.",
        "A product is named, but there is no concrete issue or requested action.",
        "A concrete issue or requested action is stated, but details needed to act are missing.",
        "A concrete issue or requested action includes useful details such as reproduction steps, an order identifier or an exact requested change."
      ]
    }
  }
}
JSON
```

Read `answers.specificity.score`. It is a probability-weighted average of the level indices, so a value such as 2.4 is valid. `legend` lists the levels and `probabilities` shows their probabilities.

The expected level is `3` because the message includes steps to reproduce the crash. A message that only says the app crashes is level `2`.

## Compare the level descriptions

The baseline uses short level names. The prepared version describes what each level requires. The report measures mean absolute error from the expected level; lower is better.

The prepared version had a larger error in the [recorded run](results.md). The request above returned 0.68 against an expected level of 3.

```sh
# Run the case above
python3 scripts/run_examples.py --example message_specificity --case case-07 --variant prepared

# Compare every variant on all cases
python3 scripts/run_examples.py --example message_specificity --output reports/message_specificity.json
```

See [message_specificity.json](message_specificity.json) for all inputs and expected levels.

Add `--preview` to a runner command to print requests without contacting the service. See the [collection guide](README.md) for reports and the [query guide](query-guide.md) for preparation advice.
