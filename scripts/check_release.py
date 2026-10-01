"""Check that the README versions table lists a release with every pinned weights revision."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    version = sys.argv[1]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    row = next((line for line in readme.splitlines() if line.startswith(f"| {version} ")), None)

    if row is None:
        sys.exit(f"README.md: add a {version} row to the versions table")

    for manifest in [
        ROOT / "model/weights.json",
        *sorted((ROOT / "model/slm").glob("*.json")),
    ]:
        revision = json.loads(manifest.read_text())["revision"][:7]
        if revision not in row:
            name = manifest.relative_to(ROOT)
            sys.exit(f"README.md: the {version} row lacks revision {revision} from {name}")


if __name__ == "__main__":
    main()
