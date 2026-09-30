"""Fetch and verify the exact public Von checkpoint used by the image."""

import hashlib
import json
import os
from pathlib import Path

from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "model/weights.json").read_text())
DESTINATION = Path(os.environ.get("SYSTEM_ONE_WEIGHTS_DIR", ROOT / "checkpoints/von-1.2"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for filename, expected in MANIFEST["files"].items():
        local = Path(
            hf_hub_download(
                repo_id=MANIFEST["repository"],
                revision=MANIFEST["revision"],
                filename=filename,
                local_dir=DESTINATION,
            )
        )
        if sha256(local) != expected:
            raise RuntimeError(f"checksum mismatch for {filename}")
        print(f"verified {filename}")
    (DESTINATION / "REVISION").write_text(MANIFEST["revision"] + "\n")


if __name__ == "__main__":
    main()
