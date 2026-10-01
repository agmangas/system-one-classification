"""Run reproducible Von examples. Semantic mistakes are results, not runner errors."""

import argparse
import json
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from example_support import (
    ROOT,
    evaluate_answers,
    fixture_hash,
    load_suites,
    prepare_request,
    request_json,
    selected_cases,
    summarize,
    validate_response,
)
from render_examples_report import write_report


def run_case(suite: dict, case: dict, base_url: str) -> dict:
    payload = prepare_request(suite, case)
    row = {"suite": suite["id"], "case": case["id"], "source": case, "request": payload}
    start = time.perf_counter()
    try:
        response = request_json(base_url.rstrip("/") + "/v1/systemone", payload)
        row["response"] = response
        validate_response(payload, response)
        row.update(status="ok", outcomes=evaluate_answers(case["expected"], response))
    except (RuntimeError, ValueError, TypeError, KeyError) as exc:
        row.update(status="error", error=str(exc))
    row["elapsed_s"] = time.perf_counter() - start
    return row


def print_case(row: dict) -> None:
    detail = row.get("error", "")
    if row["status"] == "ok":
        detail = "; ".join(
            f"{name}={outcome['actual']} (expected {outcome['expected']})"
            for name, outcome in row["outcomes"].items()
        )
    print(f"{row['suite']}/{row['case']}: {row['status']} {detail}", flush=True)


def run_cases(selections, base_url: str, *, verbose: bool = False) -> list[dict]:
    rows = []
    current_suite = None
    for suite, case in selections:
        if suite["id"] != current_suite:
            current_suite = suite["id"]
            print(f"Running {suite['title']}...", flush=True)
        row = run_case(suite, case, base_url)
        rows.append(row)
        if verbose or len(selections) == 1 or row["status"] != "ok":
            print_case(row)
    return rows


def print_preview(selections) -> int:
    previews = [
        {"example": suite["id"], "case": case["id"], "request": prepare_request(suite, case)}
        for suite, case in selections
    ]
    # A single selection is directly pipeable to curl --data-binary @-.
    output = previews[0]["request"] if len(previews) == 1 else previews
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


# The image settings each backend is expected to run with, as set in the Dockerfile.
EXPECTED_PROFILES = {
    "von": {
        "VON_NOUL_DECISION": "raw",
        "VON_CHAINS_DIR": "off",
        "VON_MAX_STATE_TOKENS": "512",
        "VON_ON_OVERFLOW": "refuse",
    },
    "slm": {
        "SYSTEM_ONE_SLM_MODEL": "qwen3.5-4b",
        "SYSTEM_ONE_SLM_CTX_SIZE": "1024",
        "SYSTEM_ONE_SLM_THREADS": "4",
    },
}


def collect_metadata(suites: list[dict], base_url: str, runtime_path: Path | None) -> dict:
    runtime = json.loads(runtime_path.read_text()) if runtime_path else None
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL, text=True
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, stderr=subprocess.DEVNULL, text=True
            )
        )
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = None, None
    return {
        "schema_version": 2,
        "created_at": datetime.now(UTC).isoformat(),
        "repository_revision": revision,
        "working_tree_dirty": dirty,
        "client": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
        },
        "server_runtime": runtime,
        "expected_profile": None,
        "fixtures": {suite["id"]: fixture_hash(suite) for suite in suites},
        "base_url": base_url,
    }


def print_summary(report: dict) -> None:
    print("\nResults by example:")
    for group in report["metrics"]:
        metrics = "; ".join(
            f"{name}: MAE {metric['mae']:.3f}"
            if metric["type"] == "score"
            else f"{name}: {metric['accuracy']:.1%} accuracy"
            for name, metric in group["questions"].items()
        )
        print(
            f"{group['suite']}: {group['ok']}/{group['total']} answered, "
            f"{group['error']} errors; {metrics or 'no predictions'}"
        )
    for error in report["errors"]:
        print(f"ERROR: {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example", default="all")
    parser.add_argument("--case")
    parser.add_argument("--verbose", action="store_true", help="Print every case outcome")
    parser.add_argument("--preview", action="store_true", help="Print wire requests without HTTP")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--runtime-metadata", type=Path, help="JSON describing the actual server runtime"
    )
    args = parser.parse_args(argv)
    try:
        suites = load_suites(args.example)
        selections = selected_cases(suites, args.case)
        if args.preview:
            return print_preview(selections)
        if args.output and args.output.with_suffix(".html") == args.output:
            raise ValueError("--output must differ from its sibling .html report")
        report = collect_metadata(suites, args.base_url, args.runtime_metadata)
        errors = []
        try:
            report["server_models"] = request_json(args.base_url.rstrip("/") + "/v1/models")
            backend = report["server_models"]["data"][0]["metadata"].get("backend")
            report["expected_profile"] = EXPECTED_PROFILES.get(backend)
        except (RuntimeError, ValueError) as exc:
            errors.append(f"model metadata: {exc}")
        rows = run_cases(selections, args.base_url, verbose=args.verbose)
        report.update(
            cases=rows,
            metrics=summarize(rows),
            errors=errors,
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            write_report([report], args.output.with_suffix(".html"))
        print_summary(report)
        if args.output:
            print(f"\nFull report: {args.output}")
            print(f"HTML report: {args.output.with_suffix('.html')}")
        return int(bool(errors) or any(row["status"] == "error" for row in rows))
    except (ValueError, OSError) as exc:
        print(f"examples: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
