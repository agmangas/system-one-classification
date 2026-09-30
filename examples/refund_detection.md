# Explicit refund request detection

Use Noul to estimate whether the author explicitly asks for money back.

Start the [HTTP service](../README.md), then send this request:

```sh
curl --fail-with-body -sS http://127.0.0.1:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "model": "system-one-cpu",
  "state": "Please return my payment.",
  "questions": {
    "refund_requested": {
      "type": "noul",
      "instructions": "Does the author explicitly request a refund?",
      "criteria": {
        "true": "The author asks to have a payment returned or a charge reversed.",
        "false": "The author does not ask for money back; they may discuss refunds, ask about policy, or explicitly decline a refund."
      }
    }
  }
}
JSON
```

Read `answers.refund_requested.noul` for the probability of an explicit refund request. The report counts values of 0.5 or higher as `true`; choose a threshold using your own data before using it in an application.

“Please return my payment” has an expected answer of `true`. “Do not refund me. Please repair the item” is `false`. Here, `false` means the message contains no explicit request for money back.

## Compare the criteria

The original query omits criteria. The reworded query describes both `true` and `false`, as shown above.

```sh
# Run the case above
python3 scripts/run_examples.py --example refund_detection --case case-01 --variant prepared

# Compare every variant on all cases
python3 scripts/run_examples.py --example refund_detection --output reports/refund_detection.json
```

See [refund_detection.json](refund_detection.json) for all inputs and expected answers.

Add `--preview` to a runner command to print requests without contacting the service. See the [collection guide](README.md) for reports and the [query guide](query-guide.md) for preparation advice.
