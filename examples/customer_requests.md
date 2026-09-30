# Customer request classification

Classify the main purpose of a customer message.

Start the [HTTP service](../README.md), then send this request:

```sh
curl --fail-with-body -sS http://127.0.0.1:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "model": "system-one-cpu",
  "state": "Please refund the duplicate charge on my account.",
  "questions": {
    "category": {
      "type": "choice",
      "instructions": "Classify the main purpose of the customer message.",
      "criteria": {
        "billing": "Payments, duplicate charges, invoices and requests to return money.",
        "technical_support": "An existing product feature fails, crashes or does not work.",
        "product_feedback": "Suggestions for a new feature or a change to product behaviour.",
        "general_enquiry": "Questions about opening hours, contact details or general service information, without a billing problem, broken feature or feature suggestion."
      }
    }
  }
}
JSON
```

Read `answers.category.choice` for the selected label. The expected answer is `billing`.

“I am not asking for a new feature: the search box stopped working today” belongs to `technical_support`. Keep the negation when preparing the input.

## About the instruction

The instruction names the decision and the text to classify: “Classify the main purpose of the customer message.”

```sh
# Run the case above
python3 scripts/run_examples.py --example customer_requests --case case-01

# Run all cases
python3 scripts/run_examples.py --example customer_requests --output reports/customer_requests.json
```

See [customer_requests.json](customer_requests.json) for all inputs and expected answers.

Add `--preview` to a runner command to print requests without contacting the service. See the [collection guide](README.md) for reports and the [query guide](query-guide.md) for preparation advice.
