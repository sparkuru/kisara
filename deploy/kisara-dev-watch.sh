#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_NAME="${BASH_SOURCE[0]##*/}"
WATCH_ROOT="${KISARA_WATCH_ROOT:-/app/src}"
WATCH_INTERVAL="${KISARA_WATCH_INTERVAL:-0.5}"
RELOAD_EXIT_CODE=75
child_pid=""

usage() {
	printf 'Usage: %s\n' "${SCRIPT_NAME}" >&2
	printf 'Watch %s and restart the Kisara process after source changes.\n' \
		"${WATCH_ROOT}" >&2
}

die() {
	printf '[%s] %s\n' "${SCRIPT_NAME}" "$*" >&2
	exit 1
}

require_command() {
	command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

source_snapshot() {
	find -- "${WATCH_ROOT}" -type f -name '*.py' -printf '%p %T@ %s\n' |
		LC_ALL=C sort |
		sha256sum |
		awk '{print $1}'
}

stop_child() {
	if [[ -n "${child_pid}" ]] && kill -0 "${child_pid}" 2>/dev/null; then
		kill -TERM "${child_pid}" 2>/dev/null || true
		wait "${child_pid}" 2>/dev/null || true
	fi
	child_pid=""
}

shutdown() {
	stop_child
	exit 0
}

run_child() {
	local initial_snapshot=$1
	local current_snapshot
	local child_status

	python -m kisara &
	child_pid=$!

	while kill -0 "${child_pid}" 2>/dev/null; do
		sleep "${WATCH_INTERVAL}"
		current_snapshot=$(source_snapshot)
		if [[ "${current_snapshot}" != "${initial_snapshot}" ]]; then
			printf '[%s] source changed; restarting Kisara\n' "${SCRIPT_NAME}" >&2
			stop_child
			return "${RELOAD_EXIT_CODE}"
		fi
	done

	if wait "${child_pid}"; then
		child_status=0
	else
		child_status=$?
	fi
	child_pid=""
	return "${child_status}"
}

main() {
	local current_snapshot
	local child_status

	case "${1:-}" in
	"") ;;
	--help | -h)
		usage
		return 0
		;;
	*)
		usage
		return 1
		;;
	esac

	for command_name in find sort sha256sum awk sleep python; do
		require_command "${command_name}"
	done
	[[ -d "${WATCH_ROOT}" ]] || die "watch root does not exist: ${WATCH_ROOT}"
	[[ "${WATCH_INTERVAL}" =~ ^[0-9]+([.][0-9]+)?$ ]] || {
		die "KISARA_WATCH_INTERVAL must be a non-negative number"
	}

	trap shutdown INT TERM
	trap stop_child EXIT
	current_snapshot=$(source_snapshot)

	while true; do
		if run_child "${current_snapshot}"; then
			child_status=0
		else
			child_status=$?
		fi

		if [[ "${child_status}" -ne "${RELOAD_EXIT_CODE}" ]]; then
			return "${child_status}"
		fi
		current_snapshot=$(source_snapshot)
	done
}

main "$@"
