#!/bin/sh
set -eu

image="${1:?Pass an image reference}"
report_path="${2:-}"
slm_model="${3:-}"
: "${REPORT_CPUSET:?}" "${REPORT_MEMORY:?}" "${REPORT_READY_ATTEMPTS:?}" "${REPORT_READY_INTERVAL:?}"

set --
if [ -n "$slm_model" ]; then
	set -- --env "SYSTEM_ONE_SLM_MODEL=$slm_model"
fi
container="$(docker run --detach --rm --cpuset-cpus="$REPORT_CPUSET" --memory="$REPORT_MEMORY" -p 127.0.0.1::8000 "$@" "$image")"
cleanup() {
	status=$?
	docker logs "$container" || true
	docker stop "$container" >/dev/null || true
	exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

address="$(docker port "$container" 8000/tcp)"
base_url="http://$address"
count=0
until curl --fail --silent "$base_url/ready" >/dev/null; do
	count=$((count + 1))
	if [ "$count" -ge "$REPORT_READY_ATTEMPTS" ]; then
		echo "model did not become ready after $REPORT_READY_ATTEMPTS checks" >&2
		exit 1
	fi
	sleep "$REPORT_READY_INTERVAL"
done

# Run the SDK check from the host: the SLM image does not install Von.
uv run --locked --group von python scripts/sdk_smoke.py --base-url "$base_url"

# With a report path as the second argument, also run every example and the latency benchmark.
[ -n "$report_path" ] || exit 0
mkdir -p "$(dirname "$report_path")"
python3 scripts/runtime_metadata.py "$container" >"${report_path%.json}-runtime.json"
python3 scripts/run_examples.py --base-url "$base_url" --output "$report_path" \
	--runtime-metadata "${report_path%.json}-runtime.json"
python3 scripts/benchmark.py --base-url "$base_url" \
	--output "${report_path%.json}-benchmark.json"
