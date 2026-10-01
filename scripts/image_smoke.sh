#!/bin/sh
set -eu

image="${1:-system-one-classification:local}"
container="$(docker run --detach --rm --cpuset-cpus=0-3 --memory=8g -p 127.0.0.1::8000 "$image")"
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

# Run the SDK check from the host: the SLM image does not install Von.
uv run --locked python scripts/sdk_smoke.py --base-url "$base_url"

# With a report path as the second argument, also run every example and the latency benchmark.
[ "$#" -ge 2 ] || exit 0
report_path="$2"
mkdir -p "$(dirname "$report_path")"
python3 scripts/runtime_metadata.py "$container" >"${report_path%.json}-runtime.json"
python3 scripts/run_examples.py --base-url "$base_url" --output "$report_path" \
	--runtime-metadata "${report_path%.json}-runtime.json"
python3 scripts/benchmark.py --base-url "$base_url" \
	--output "${report_path%.json}-benchmark.json"
