"""Print selected Docker runtime metadata without exposing container secrets."""

import json
import subprocess
import sys


def inspect(kind: str, identifier: str) -> dict:
    return json.loads(subprocess.check_output(["docker", kind, "inspect", identifier], text=True))[
        0
    ]


def main() -> None:
    container = inspect("container", sys.argv[1])
    image = inspect("image", container["Image"])
    env = dict(item.split("=", 1) for item in container["Config"]["Env"] if "=" in item)
    allowed = (
        "SYSTEM_ONE_BACKEND",
        "SYSTEM_ONE_SLM_MODEL",
        "SYSTEM_ONE_SLM_CTX_SIZE",
        "SYSTEM_ONE_SLM_THREADS",
        "VON_DEVICE",
        "VON_NOUL_DECISION",
        "VON_CHAINS_DIR",
        "VON_MAX_STATE_TOKENS",
        "VON_ON_OVERFLOW",
        "SYSTEM_ONE_MAX_CONCURRENT",
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
    )
    print(
        json.dumps(
            {
                "image_id": container["Image"],
                "image_reference": container["Config"]["Image"],
                "image_digests": image.get("RepoDigests", []),
                "architecture": image["Architecture"],
                "os": image["Os"],
                "nano_cpus": container["HostConfig"]["NanoCpus"],
                "cpuset_cpus": container["HostConfig"]["CpusetCpus"],
                "memory_bytes": container["HostConfig"]["Memory"],
                "environment": {key: env.get(key) for key in allowed},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
