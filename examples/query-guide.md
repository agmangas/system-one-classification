# Preparing a Von query

Put the input in `state`, the question in `instructions`, and the answer descriptions in `criteria`. Von selects or scores the supplied answers; it does not generate explanations.

```json
{
  "model": "system-one-cpu",
  "state": "The club signed a new goalkeeper.",
  "questions": {
    "topic": {
      "type": "choice",
      "instructions": "What is the main topic of this news sentence?",
      "criteria": {
        "sports": "Athletic teams, players, matches and competitions.",
        "business": "Company finances, trade, profits and commercial markets."
      }
    }
  }
}
```

The [news example](news_topics.md) expands this to four categories.

## Describe each answer clearly

Use short, concrete definitions. Write each description so it makes sense on its own. Avoid “the other category” or “none of the above.” In the pinned model, each option sees the shared input and question plus its own description. Include the category name in the description if needed; the model does not automatically add the label key. See the [domain guidance][domains] and [model source][model].

Define a fallback if you need to classify unlisted or ambiguous inputs. It still competes with the other answers, so include those inputs when checking accuracy.

## Choose a question type

| Type | Use it for | Define |
| --- | --- | --- |
| Choice | Selecting one category | Each category, including any fallback |
| Noul | Estimating whether a condition holds | Both `true` and `false` |
| Score | Rating an input on ordered levels | What qualifies for each level |

Upstream [usage guidance][usage] recommends explicit criteria for Noul. Score returns a probability-weighted average of level indices, starting at zero, so fractional results are valid. See the [response types][types].

## Keep the facts that decide the answer

Shorten irrelevant context, but preserve negations, conditions, dates, quantities, and uncertainty. Check that a shorter input still means the same thing. These examples use a 512-token state limit and refuse oversized inputs.

You can put several questions in one request, but the pinned [backend][backend] evaluates them separately.

## Translate non-English input first

Von is English-only. Translate inputs and question definitions into English before sending them. Preserve ambiguity and negation, and keep the originals outside the request so you can check the translation. The [model card][card] warns that unsupported languages can produce confident errors.

## Test a query before adopting it

Check a query on labelled inputs from your application before relying on it. Keep some inputs aside for a final check, and don't use them while you adjust the wording. More detailed descriptions do not guarantee better answers: in the [specificity example](message_specificity.md), a query with described levels returned 0.68 for an expected level of 3.

For Choice and Score, read `probabilities` for the distribution. The separate `confidence` field adjusts the highest probability for the number of options. Noul uses raw probabilities in this service. See the [backend calculation][backend].

If your application acts on a probability threshold, evaluate that threshold on representative labelled data. These small examples cannot establish a reliable threshold for your application.

[domains]: https://github.com/wfzyx/von/blob/5ea5082f67d2bfc69336ce6150f6d05393d7fd27/docs/benchmarks.md#domain-generalization--out-of-domain-tasks-eg-education-academia
[model]: https://github.com/wfzyx/von/blob/5ea5082f67d2bfc69336ce6150f6d05393d7fd27/src/von/models/option_marker.py
[backend]: https://github.com/wfzyx/von/blob/5ea5082f67d2bfc69336ce6150f6d05393d7fd27/src/von/backends/option_marker_backend.py
[usage]: https://github.com/wfzyx/von#use
[types]: https://github.com/wfzyx/von/blob/5ea5082f67d2bfc69336ce6150f6d05393d7fd27/src/von/types.py
[card]: https://huggingface.co/wfzyx/von#limitations
