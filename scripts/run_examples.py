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
    compare_pairs,
    evaluate_answers,
    fixture_hash,
    load_suites,
    prepare_request,
    request_json,
    selected_cases,
    summarize,
    validate_response,
)


def run_case(suite: dict, case: dict, variant: str, base_url: str) -> dict:
    preparation = suite["variants"][variant]["preparation"]
    payload, reason = prepare_request(suite, case, variant)
    row = {
        "suite": suite["id"],
        "case": case["id"],
        "variant": variant,
        "language": case["language"],
        "split": case["split"],
        "preparation": preparation,
        "unsupported_language_input": case["language"] != "en" and preparation == "original",
        "source": case,
        "request": payload,
    }
    if reason:
        row.update(status="skipped", reason=reason)
        return row
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
    detail = row.get("reason", row.get("error", ""))
    if row["status"] == "ok":
        detail = "; ".join(
            f"{name}={outcome['actual']} (expected {outcome['expected']})"
            for name, outcome in row["outcomes"].items()
        )
    print(f"{row['suite']}/{row['case']}/{row['variant']}: {row['status']} {detail}", flush=True)


def run_cases(selections, base_url: str, *, verbose: bool = False) -> list[dict]:
    rows = []
    current_suite = None
    for suite, case, variant in selections:
        if suite["id"] != current_suite:
            current_suite = suite["id"]
            print(f"Running {suite['title']}...", flush=True)
        row = run_case(suite, case, variant, base_url)
        rows.append(row)
        if verbose or len(selections) == 1 or row["status"] != "ok":
            print_case(row)
    return rows


def print_preview(selections) -> int:
    previews = []
    for suite, case, variant in selections:
        payload, reason = prepare_request(suite, case, variant)
        previews.append(
            {
                "example": suite["id"],
                "case": case["id"],
                "variant": variant,
                "request": payload,
                "skipped": reason,
            }
        )
    # A single resolved selection is directly pipeable to curl --data-binary @-.
    if len(previews) == 1 and previews[0]["request"] is not None:
        print(json.dumps(previews[0]["request"], ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(previews, ensure_ascii=False, indent=2))
    return 1 if len(previews) == 1 and previews[0]["skipped"] else 0


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
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "repository_revision": revision,
        "working_tree_dirty": dirty,
        "client": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
        },
        "server_runtime": runtime,
        "expected_profile": {
            "VON_NOUL_DECISION": "raw",
            "VON_CHAINS_DIR": "off",
            "VON_MAX_STATE_TOKENS": "512",
            "VON_ON_OVERFLOW": "refuse",
        },
        "fixtures": {suite["id"]: fixture_hash(suite) for suite in suites},
        "base_url": base_url,
    }


def print_summary(report: dict) -> None:
    print("\nResults by example / variant / split / source language:")
    for group in report["metrics"]:
        metrics = "; ".join(
            f"{name}: MAE {metric['mae']:.3f}"
            if metric["type"] == "score"
            else f"{name}: {metric['accuracy']:.1%} accuracy"
            for name, metric in group["questions"].items()
        )
        print(
            f"{group['suite']} / {group['variant']} / {group['split']} / {group['language']}: "
            f"{group['ok']}/{group['total']} answered, {group['skipped']} unresolved, "
            f"{group['error']} errors; {metrics or 'no predictions'}"
        )
    if report["comparisons"]:
        print("\nPaired preparation changes (wins / regressions / ties):")
        for group in report["comparisons"]:
            print(
                f"{group['suite']} {group['baseline']} -> {group['prepared']} "
                f"[{group['split']}, {group['language']}, {group['question']}]: "
                f"{group['wins']} / {group['regressions']} / {group['ties']}"
            )
    for error in report["errors"]:
        print(f"ERROR: {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example", default="all")
    parser.add_argument("--case")
    parser.add_argument("--variant")
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
        selections = selected_cases(suites, args.case, args.variant)
        if args.preview:
            return print_preview(selections)
        report = collect_metadata(suites, args.base_url, args.runtime_metadata)
        errors = []
        try:
            report["server_models"] = request_json(args.base_url.rstrip("/") + "/v1/models")
        except (RuntimeError, ValueError) as exc:
            errors.append(f"model metadata: {exc}")
        rows = run_cases(selections, args.base_url, verbose=args.verbose)
        report.update(
            cases=rows,
            metrics=summarize(rows),
            comparisons=compare_pairs(rows, suites),
            errors=errors,
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print_summary(report)
        if args.output:
            print(f"\nFull report: {args.output}")
        return int(bool(errors) or any(row["status"] == "error" for row in rows))
    except (ValueError, OSError) as exc:
        print(f"examples: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
