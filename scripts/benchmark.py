"""Measure warm HTTP p95 for one short material classification request."""

import argparse
import json
import math
import os
import statistics
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--max-p95", type=float, default=1.0)
    args = parser.parse_args()
    fixture = json.loads((ROOT / "examples/materials.json").read_text())
    body = json.dumps(
        {
            "model": "system-one-cpu",
            "state": "concreet",
            "questions": {
                "material": {
                    "type": "choice",
                    "instructions": fixture["instructions"],
                    "criteria": fixture["criteria"],
                }
            },
        }
    ).encode()
    headers = {"Content-Type": "application/json"}
    if key := os.environ.get("SYSTEM_ONE_API_KEY"):
        headers["Authorization"] = f"Bearer {key}"
    timings = []
    for index in range(args.count + 5):
        request = Request(args.base_url.rstrip("/") + "/v1/systemone", data=body, headers=headers)
        start = time.perf_counter()
        with urlopen(request, timeout=120) as response:
            json.load(response)
        if index >= 5:
            timings.append(time.perf_counter() - start)
    p95 = sorted(timings)[math.ceil(0.95 * len(timings)) - 1]
    print(
        json.dumps(
            {
                "requests": len(timings),
                "p50_s": round(statistics.median(timings), 4),
                "p95_s": round(p95, 4),
                "target_s": args.max_p95,
            }
        )
    )
    return 0 if p95 < args.max_p95 else 1


if __name__ == "__main__":
    raise SystemExit(main())
