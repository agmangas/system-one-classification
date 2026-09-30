"""Check all example contracts through Von's HTTP SDK, plus overflow refusal."""

import argparse
import os

from example_support import (
    HTTPFailure,
    load_suites,
    prepare_request,
    request_json,
    validate_response,
)
from von import VonClient


def first_request(suite: dict) -> dict:
    """Prefer later formulations, skipping cases without a prepared input."""
    for variant in reversed(suite["variants"]):
        for case in suite["cases"]:
            payload, _ = prepare_request(suite, case, variant)
            if payload is not None:
                return payload
    raise RuntimeError(f"{suite['id']}: no runnable case for the SDK check")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    client = VonClient(
        base_url=args.base_url,
        local=False,
        timeout=120,
        api_key=os.environ.get("SYSTEM_ONE_API_KEY"),
    )
    for suite in load_suites():
        payload = first_request(suite)
        result = client.system_one(**payload)
        validate_response(payload, result.model_dump(exclude_none=True))
        print(f"Von HTTP SDK: {suite['id']} response parsed")
    overflow_request = {
        "model": payload["model"],
        "state": "irrelevant context " * 1500,
        "questions": payload["questions"],
    }
    try:
        request_json(args.base_url.rstrip("/") + "/v1/systemone", overflow_request)
    except HTTPFailure as exc:
        if exc.status != 422 or "context window" not in exc.body:
            raise
    else:
        raise RuntimeError("expected HTTP 422 for an oversized state under the refuse profile")
    print("Overflow: HTTP 422 as expected")


if __name__ == "__main__":
    main()
