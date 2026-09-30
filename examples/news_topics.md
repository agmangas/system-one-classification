# News-topic classification

Classify the main topic of a short news sentence.

Start the [HTTP service](../README.md), then send this request:

```sh
curl --fail-with-body -sS http://127.0.0.1:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "model": "system-one-cpu",
  "state": "The club signed a new goalkeeper before the season began.",
  "questions": {
    "topic": {
      "type": "choice",
      "instructions": "What is the main topic of this news sentence?",
      "criteria": {
        "sports": "Athletic teams, players, matches, competitions and sporting results.",
        "technology": "Computer hardware, software, digital products and technical inventions.",
        "business": "Company finances, trade, acquisitions, profits and commercial markets.",
        "arts": "Painting, music, theatre, literature, film and artistic performances."
      }
    }
  }
}
JSON
```

Read `answers.topic.choice` for the selected label and `answers.topic.probabilities` for each label’s probability.

The expected answer is `sports`. A sentence about a football club’s annual revenue is `business`, because the question asks what the sentence reports.

## Compare the descriptions

The original query uses topic names. The reworded query adds the definitions shown above. These four topics cover the example inputs; a broader news collection may need more categories.

```sh
# Run the case above
python3 scripts/run_examples.py --example news_topics --case case-01 --variant prepared

# Compare every variant on all cases
python3 scripts/run_examples.py --example news_topics --output reports/news_topics.json
```

See [news_topics.json](news_topics.json) for all inputs and expected answers.

Add `--preview` to a runner command to print requests without contacting the service. See the [collection guide](README.md) for reports and the [query guide](query-guide.md) for preparation advice.
