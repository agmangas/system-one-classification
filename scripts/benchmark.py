"""Measure warm HTTP latency for any prepared example request."""

import argparse
import json
import math
import statistics
import time
from pathlib import Path

from example_support import (
    fixture_hash,
    load_suites,
    prepare_request,
    request_json,
    selected_cases,
    validate_response,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--example", default="news_topics")
    parser.add_argument("--case", default="case-01")
    parser.add_argument("--variant", default="prepared")
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--max-p95", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.count < 1 or (args.max_p95 is not None and args.max_p95 <= 0):
        parser.error("count and max-p95 must be positive")
    try:
        selections = selected_cases(load_suites(args.example), args.case, args.variant)
        if len(selections) != 1:
            raise ValueError("select exactly one example, case and variant to benchmark")
        suite, case, variant = selections[0]
        payload, reason = prepare_request(suite, case, variant)
        if reason:
            raise ValueError(reason)
        timings = []
        for index in range(args.count + 5):
            start = time.perf_counter()
            response = request_json(args.base_url.rstrip("/") + "/v1/systemone", payload)
            elapsed = time.perf_counter() - start
            validate_response(payload, response)
            if index >= 5:
                timings.append(elapsed)
        p95 = sorted(timings)[math.ceil(0.95 * len(timings)) - 1]
        report = {
            "example": suite["id"],
            "case": case["id"],
            "variant": variant,
            "fixture_hash": fixture_hash(suite),
            "request": payload,
            "server_models": request_json(args.base_url.rstrip("/") + "/v1/models"),
            "warmup_requests": 5,
            "requests": len(timings),
            "timings_s": timings,
            "p50_s": statistics.median(timings),
            "p95_s": p95,
            "target_s": args.max_p95,
        }
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return int(args.max_p95 is not None and p95 >= args.max_p95)
    except (RuntimeError, ValueError) as exc:
        parser.exit(1, f"benchmark: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
