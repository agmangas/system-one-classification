"""Fetch and verify the pinned public weights for the backend in SYSTEM_ONE_BACKEND."""

import hashlib
import json
import os
from pathlib import Path

from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS, DEFAULT_DESTINATION = {
    "von": ([ROOT / "model/weights.json"], "checkpoints/von-1.2"),
    "slm": (sorted((ROOT / "model/slm").glob("*.json")), "checkpoints/slm"),
}[os.environ.get("SYSTEM_ONE_BACKEND", "von")]
DESTINATION = Path(os.environ.get("SYSTEM_ONE_WEIGHTS_DIR", ROOT / DEFAULT_DESTINATION))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for path in MANIFESTS:
        manifest = json.loads(path.read_text())
        for filename, expected in manifest["files"].items():
            local = Path(
                hf_hub_download(
                    repo_id=manifest["repository"],
                    revision=manifest["revision"],
                    filename=filename,
                    local_dir=DESTINATION,
                )
            )
            if sha256(local) != expected:
                raise RuntimeError(f"checksum mismatch for {filename}")
            print(f"verified {filename}")


if __name__ == "__main__":
    main()
