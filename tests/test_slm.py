"""Check SLM prompt scoring against canned llama-server responses."""

import json
import math

import httpx
import pytest

from system_one_service import slm


def candidates(**probabilities):
    return [{"token": token, "logprob": math.log(p)} for token, p in probabilities.items()]


def completion(top_logprobs, prompt_tokens=50):
    return {
        "choices": [{"logprobs": {"content": [{"top_logprobs": top_logprobs}]}}],
        "usage": {"prompt_tokens": prompt_tokens},
    }


def test_label_probabilities_merge_spacing_and_floor_missing_labels():
    top = [*candidates(B=0.6, A=0.2, The=0.05), {"token": " B", "logprob": math.log(0.1)}]
    probabilities = slm.label_probabilities(top, "ABC")
    assert probabilities == pytest.approx([0.2 / 0.95, 0.7 / 0.95, 0.05 / 0.95])
    assert slm.label_probabilities(candidates(The=0.9), "AB") == pytest.approx([0.5, 0.5])


def test_answers_follow_von_formats():
    keys, descriptions = slm.options(
        {"type": "choice", "criteria": {"steel": "Iron alloy", "other": None}}
    )
    assert descriptions == ["Iron alloy", "other"]
    choice = slm.answer("choice", keys, descriptions, [0.25, 0.75])
    assert (choice["choice"], choice["confidence"]) == ("other", 0.5)

    keys, descriptions = slm.options(
        {"type": "score", "criteria": ["Vague", {"what": "Specific", "examples": ["a date"]}]}
    )
    score = slm.answer("score", keys, descriptions, [0.2, 0.8])
    assert score["score"] == 0.8
    assert score["legend"] == {"0": "Vague", "1": "Specific Examples: a date"}

    keys, descriptions = slm.options({"type": "noul"})
    assert descriptions == list(slm.NOUL_DEFAULTS.values())
    assert slm.answer("noul", keys, descriptions, [0.123456, 0.876544]) == {
        "type": "noul",
        "noul": 0.1235,
    }


def test_evaluate_sums_usage_and_refuses_prompts_over_the_context_window():
    requests = []

    def llama_server(request):
        body = json.loads(request.content)
        requests.append(body)
        if "long" in body["messages"][0]["content"]:
            error = {"type": "exceed_context_size_error", "n_prompt_tokens": 3091, "n_ctx": 1024}
            return httpx.Response(400, json={"error": error})
        return httpx.Response(200, json=completion(candidates(A=0.9, B=0.1)))

    adapter = slm.SlmAdapter()
    adapter._client = httpx.Client(transport=httpx.MockTransport(llama_server), base_url="http://s")
    question = {"type": "noul", "instructions": "Is it urgent?"}
    result = adapter.evaluate({"subject": "Server down"}, {"a": question, "b": question})
    assert result["answers"]["a"] == {"type": "noul", "noul": 0.9}
    assert result["usage"] == {"input_tokens": 100, "output_tokens": 2}
    assert "subject: Server down" in requests[0]["messages"][0]["content"]
    assert requests[0]["chat_template_kwargs"] == {"enable_thinking": False}
    with pytest.raises(ValueError, match="1024-token context window"):
        adapter.evaluate("long " * 10, {"a": question})
