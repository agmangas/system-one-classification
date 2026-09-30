"""Check that the public endpoint works through Von's System One HTTP client."""

import argparse

from von import VonClient, choice, noul, score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    client = VonClient(base_url=args.base_url, local=False, timeout=120)
    result = client.system_one(
        state={"material": "brik", "condition": "broken"},
        questions={
            "material": choice(
                instructions="Which material is named?",
                criteria={"brick": "brick", "steel": "steel"},
            ),
            "is_broken": noul(
                instructions="Is the item broken?",
                criteria={"true": "The item is broken", "false": "The item is intact"},
            ),
            "severity": score(
                instructions="Rate the damage.",
                criteria=["No damage", "Minor damage", "Major damage"],
            ),
        },
        model="system-one-cpu",
    )
    assert result.model == "system-one-cpu"
    assert set(result.answers) == {"material", "is_broken", "severity"}
    assert result.answers["material"].choice in {"brick", "steel"}
    assert 0 <= result.answers["is_broken"].noul <= 1
    assert 0 <= result.answers["severity"].score <= 2
    print("Von HTTP SDK: choice, noul, and score responses parsed")


if __name__ == "__main__":
    main()
