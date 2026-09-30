"""Run the material fixture through the public HTTP API and report every result."""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def post_json(url: str, payload: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    if key := os.environ.get("SYSTEM_ONE_API_KEY"):
        headers["Authorization"] = f"Bearer {key}"
    request = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=120) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode()}") from exc
    except URLError as exc:
        raise RuntimeError(f"request failed: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-english-accuracy", type=float)
    args = parser.parse_args()
    fixture = json.loads((ROOT / "examples/materials.json").read_text())
    results = []
    for case in fixture["cases"]:
        payload = {
            "model": "system-one-cpu",
            "state": f"Misspelled material name: {case['input']}",
            "questions": {
                "material": {
                    "type": "choice",
                    "instructions": fixture["instructions"],
                    "criteria": fixture["criteria"],
                }
            },
        }
        answer = post_json(args.base_url.rstrip("/") + "/v1/systemone", payload)["answers"][
            "material"
        ]
        if answer["choice"] not in fixture["criteria"] or set(answer["probabilities"]) != set(
            fixture["criteria"]
        ):
            raise RuntimeError(f"invalid choice response for {case['id']}")
        result = {
            **case,
            "actual": answer["choice"],
            "correct": answer["choice"] == case["expected"],
            "probabilities": answer["probabilities"],
        }
        results.append(result)
        print(f"{case['id']}: {case['input']} -> {answer['choice']} (expected {case['expected']})")
    metrics = {}
    for language in ("en", "it"):
        subset = [item for item in results if item["language"] == language]
        correct = sum(item["correct"] for item in subset)
        metrics[language] = {
            "correct": correct,
            "total": len(subset),
            "accuracy": correct / len(subset),
        }
        print(f"{language}: {correct}/{len(subset)} ({metrics[language]['accuracy']:.1%})")
    for kind in ("typo", "out_of_set", "related"):
        subset = [item for item in results if item["language"] == "en" and item["kind"] == kind]
        if subset:
            correct = sum(item["correct"] for item in subset)
            metrics[kind] = {
                "correct": correct,
                "total": len(subset),
                "accuracy": correct / len(subset),
            }
            print(f"en {kind}: {correct}/{len(subset)}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"metrics": metrics, "cases": results}, indent=2) + "\n")
    if (
        args.min_english_accuracy is not None
        and metrics["en"]["accuracy"] < args.min_english_accuracy
    ):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
