"""Fixture loading, request and HTTP helpers; standard library only."""

import copy
import hashlib
import json
import math
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MODEL = "system-one-cpu"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_questions(questions: dict) -> None:
    require(isinstance(questions, dict) and bool(questions), "questions must be a nonempty object")
    for name, question in questions.items():
        require(isinstance(question, dict), f"{name}: question must be an object")
        require(
            isinstance(question.get("instructions"), str)
            and bool(question["instructions"].strip()),
            f"{name}: instructions must be nonempty English text",
        )
        kind, criteria = question.get("type"), question.get("criteria")
        require(kind in {"choice", "noul", "score"}, f"{name}: invalid question type")
        if kind == "choice":
            require(isinstance(criteria, dict) and 2 <= len(criteria) <= 32, "invalid choices")
        elif kind == "score":
            require(isinstance(criteria, list) and 2 <= len(criteria) <= 10, "invalid score levels")
        elif criteria is not None:
            require(
                isinstance(criteria, dict) and set(criteria) == {"true", "false"},
                "noul criteria must contain true and false",
            )
        if criteria is not None:
            values = criteria.values() if isinstance(criteria, dict) else criteria
            require(
                all(isinstance(v, str) and v.strip() for v in values),
                "criteria must contain nonempty descriptions",
            )


def validate_suite(suite: dict) -> None:
    require(isinstance(suite, dict), "fixture must be an object")
    require(suite.get("schema_version") == 2, "unsupported fixture schema")
    require(isinstance(suite.get("id"), str) and bool(suite["id"]), "missing suite id")
    questions = suite.get("questions")
    validate_questions(questions)
    require(isinstance(suite.get("cases"), list) and bool(suite["cases"]), "missing cases")
    ids = set()
    for case in suite["cases"]:
        require(isinstance(case, dict), "case must be an object")
        require(isinstance(case.get("id"), str) and bool(case["id"]), "missing case id")
        require(case["id"] not in ids, f"duplicate case id: {case['id']}")
        ids.add(case["id"])
        require(isinstance(case.get("state"), (str, dict)), "state must be text or an object")
        expected = case.get("expected")
        require(
            isinstance(expected, dict) and set(expected) == set(questions),
            f"{case['id']}: expected answers must match question names",
        )
        validate_expected(questions, expected)


def validate_expected(questions: dict, expected: dict) -> None:
    for name, question in questions.items():
        gold = expected[name]
        if question["type"] == "choice":
            require(
                isinstance(gold, str) and gold in question["criteria"],
                "invalid gold choice",
            )
        elif question["type"] == "noul":
            require(type(gold) is bool, "noul gold must be boolean")
        else:
            require(
                type(gold) is int and 0 <= gold < len(question["criteria"]),
                "score gold must be a level index",
            )


def load_suites(selection: str = "all") -> list[dict]:
    paths = sorted((ROOT / "examples").glob("*.json"))
    suites = []
    for path in paths:
        if selection != "all" and path.stem != selection:
            continue
        suite = json.loads(path.read_text(encoding="utf-8"))
        validate_suite(suite)
        require(suite["id"] == path.stem, f"{path}: id must match filename")
        suites.append(suite)
    require(bool(suites), f"no examples match {selection!r}")
    return suites


def prepare_request(suite: dict, case: dict) -> dict:
    # Whitelist wire fields. Gold labels and IDs stay local.
    return {
        "model": MODEL,
        "state": copy.deepcopy(case["state"]),
        "questions": copy.deepcopy(suite["questions"]),
    }


def selected_cases(suites: list[dict], case_id: str | None) -> list[tuple[dict, dict]]:
    selections = [
        (suite, case)
        for suite in suites
        for case in suite["cases"]
        if not case_id or case["id"] == case_id
    ]
    require(bool(selections), "no cases match the requested case")
    return selections


class HTTPFailure(RuntimeError):
    def __init__(self, status: int, body: str):
        self.status, self.body = status, body
        super().__init__(f"HTTP {status}: {body}")


def request_json(url: str, payload: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if key := os.environ.get("SYSTEM_ONE_API_KEY"):
        headers["Authorization"] = f"Bearer {key}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = Request(url, data=data, headers=headers)
    try:
        with urlopen(request, timeout=120) as response:
            return json.load(response)
    except HTTPError as exc:
        raise HTTPFailure(exc.code, exc.read().decode("utf-8", errors="replace")) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"request failed: {exc}") from exc


def number(value, low: float, high: float) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def validate_response(payload: dict, response: dict) -> None:
    require(isinstance(response, dict), "response must be an object")
    require(response.get("model") == payload["model"], "unexpected response model")
    answers = response.get("answers")
    require(
        isinstance(answers, dict) and set(answers) == set(payload["questions"]),
        "answer identifiers differ from request",
    )
    usage = response.get("usage", {})
    require(
        isinstance(usage, dict)
        and all(
            type(usage.get(k)) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens")
        ),
        "invalid usage",
    )
    require(not response.get("truncation"), "unexpected truncation under the refuse profile")
    for name, question in payload["questions"].items():
        answer = answers[name]
        require(
            isinstance(answer, dict) and answer.get("type") == question["type"], "wrong answer type"
        )
        if question["type"] == "noul":
            require(number(answer.get("noul"), 0, 1), "invalid noul probability")
            continue
        if question["type"] == "choice":
            keys = set(question["criteria"])
        else:
            keys = {str(i) for i in range(len(question["criteria"]))}
        probs = answer.get("probabilities")
        require(isinstance(probs, dict) and set(probs) == keys, "invalid probability keys")
        require(all(number(p, 0, 1) for p in probs.values()), "invalid probabilities")
        probability_tolerance = len(keys) * 0.00005 + 1e-6
        require(
            abs(sum(probs.values()) - 1) <= probability_tolerance,
            "probabilities do not sum to one within rounding tolerance",
        )
        require(number(answer.get("confidence"), 0, 1), "invalid confidence")
        if question["type"] == "choice":
            require(answer.get("choice") in keys, "invalid chosen label")
            require(
                probs[answer["choice"]] >= max(probs.values()) - 0.0001,
                "chosen label is not a highest-probability option",
            )
            continue
        require(number(answer.get("score"), 0, len(keys) - 1), "invalid score")
        require(
            answer.get("legend") == {str(i): v for i, v in enumerate(question["criteria"])},
            "invalid score legend",
        )
        expectation = sum(int(i) * p for i, p in probs.items())
        score_tolerance = 0.0051 + len(keys) ** 2 * 0.00005
        require(
            abs(answer["score"] - expectation) <= score_tolerance,
            "score differs from probability-weighted level",
        )


def evaluate_answers(expected: dict, response: dict) -> dict:
    outcomes = {}
    for name, gold in expected.items():
        answer = response["answers"][name]
        kind = answer["type"]
        if kind == "choice":
            actual = answer["choice"]
        elif kind == "noul":
            actual = answer["noul"] >= 0.5
        else:
            actual = answer["score"]
        outcomes[name] = {"type": kind, "expected": gold, "actual": actual}
        if kind == "score":
            outcomes[name]["absolute_error"] = abs(actual - gold)
        else:
            outcomes[name]["correct"] = actual == gold
    return outcomes


def summarize(rows: list[dict]) -> list[dict]:
    groups = {}
    for row in rows:
        group = groups.setdefault(
            row["suite"],
            {"suite": row["suite"], "total": 0, "ok": 0, "error": 0, "questions": {}},
        )
        group["total"] += 1
        group[row["status"]] += 1
        for name, outcome in row.get("outcomes", {}).items():
            metric = group["questions"].setdefault(
                name, {"type": outcome["type"], "count": 0, "sum": 0}
            )
            metric["count"] += 1
            if outcome["type"] == "score":
                metric["sum"] += outcome["absolute_error"]
            else:
                metric["sum"] += outcome["correct"]
    for group in groups.values():
        for metric in group["questions"].values():
            name = "mae" if metric["type"] == "score" else "accuracy"
            metric[name] = metric.pop("sum") / metric["count"]
    return list(groups.values())


def fixture_hash(suite: dict) -> str:
    return hashlib.sha256(
        json.dumps(suite, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
