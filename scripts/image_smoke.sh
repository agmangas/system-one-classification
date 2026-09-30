#!/bin/sh
set -eu

image="${1:-system-one-classification:local}"
container="$(docker run --detach --rm --cpus=4 --memory=8g -p 127.0.0.1::8000 "$image")"
trap 'docker logs "$container"; docker stop "$container" >/dev/null' EXIT

address="$(docker port "$container" 8000/tcp)"
base_url="http://$address"
count=0
until curl --fail --silent "$base_url/ready" >/dev/null; do
  count=$((count + 1))
  if [ "$count" -ge 180 ]; then
    echo "model did not become ready within six minutes" >&2
    exit 1
  fi
  sleep 2
done

docker exec "$container" /app/.venv/bin/python scripts/sdk_smoke.py
python3 scripts/validate_materials.py --base-url "$base_url" --output "${REPORT_PATH:-reports/materials.json}"
python3 scripts/benchmark.py --base-url "$base_url" --max-p95 1.0
