#!/usr/bin/env bash
# dev.sh - Start and stop the selected Kisara engine.
#
# OneBot uses deploy/onebot.sh for the NapCat + Kisara Compose stack.
# Official uses the executable ./hako wrapper.
# Service:  bot (outbound protocol connection; no host port is published).
# Select the engine with KISARA_ENGINE=onebot|onebot-dev|official or use ./start.sh.
#
# The bot service has no local URL. If a future inbound service is added, keep
# its container binding on 0.0.0.0 and add an explicit mapping in ./hako.
set -Eeuo pipefail

SCRIPT_NAME="${BASH_SOURCE[0]##*/}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_LABEL="hako.repo=${REPO_ROOT}"
SCOPE_LABEL="hako.scope=dev.sh"

# Keep these values aligned with the editable block in ./hako.
HAKO_BIND_HOST="${HAKO_BIND_HOST:-127.0.0.1}"
BOT_HOST_PORT="${BOT_HOST_PORT:-0}"
BOT_CONTAINER_PORT="${BOT_CONTAINER_PORT:-0}"

service_pids=()

usage() {
	printf 'Usage: %s [start|down|stop]\n' "${SCRIPT_NAME}" >&2
	printf '       KISARA_ENGINE=onebot|onebot-dev|official %s start\n' "${SCRIPT_NAME}" >&2
}

die() {
	printf '[dev.sh] %s\n' "$*" >&2
	exit 1
}

require_command() {
	command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

down_services() {
	local mode=${1:-verbose}
	local container_ids_text
	local -a container_ids=()

	require_command docker

	if ! container_ids_text=$(docker ps -q \
		--filter "label=${PROJECT_LABEL}" \
		--filter "label=${SCOPE_LABEL}"); then
		[[ "${mode}" == quiet ]] || die "unable to inspect dev containers"
		return 1
	fi

	if [[ -z "${container_ids_text}" ]]; then
		[[ "${mode}" == quiet ]] || printf '[dev.sh] no dev containers found\n' >&2
		return 0
	fi

	mapfile -t container_ids <<<"${container_ids_text}"
	printf '[dev.sh] stopping %s bot container(s)\n' "${#container_ids[@]}" >&2
	docker stop "${container_ids[@]}" >/dev/null || true
}

cleanup() {
	local pid

	down_services quiet || true

	for pid in "${service_pids[@]}"; do
		kill "${pid}" 2>/dev/null || true
	done
}

run_service() {
	local name=$1
	shift

	printf '[dev.sh] starting %s through ./hako\n' "${name}" >&2
	HAKO_SCOPE=dev.sh \
		HAKO_SERVICE="${name}" \
		KISARA_ENGINE="${KISARA_ENGINE:-}" \
		HAKO_BIND_HOST="${HAKO_BIND_HOST}" \
		BOT_HOST_PORT="${BOT_HOST_PORT}" \
		BOT_CONTAINER_PORT="${BOT_CONTAINER_PORT}" \
		"$@" &
	service_pids+=("$!")
}

start_services() {
	local status=0
	local engine="${KISARA_ENGINE:-onebot}"

	case "${engine}" in
	onebot | onebot-dev | official) ;;
	*)
		die "unknown KISARA_ENGINE: ${engine}; choose onebot, onebot-dev, or official"
		;;
	esac

	require_command docker

	if [[ "${engine}" == onebot || "${engine}" == onebot-dev ]]; then
		[[ -x "${REPO_ROOT}/deploy/onebot.sh" ]] || {
			die "executable deploy/onebot.sh was not found"
		}
		if [[ "${engine}" == onebot-dev ]]; then
			exec "${REPO_ROOT}/deploy/onebot.sh" dev
		fi
		exec "${REPO_ROOT}/deploy/onebot.sh" up
	fi

	[[ -x "${REPO_ROOT}/hako" ]] || die "executable ./hako was not found"
	[[ -f "${REPO_ROOT}/.env" ]] || die "missing .env; copy .env.example and configure the selected engine"

	cd "${REPO_ROOT}"
	trap cleanup INT TERM EXIT

	down_services quiet

	printf '[dev.sh] selected engine: %s; no host port is published\n' "${engine}" >&2
	KISARA_ENGINE="${engine}" run_service bot ./hako python -m kisara

	wait -n "${service_pids[@]}" || status=$?
	trap - INT TERM EXIT
	cleanup
	return "${status}"
}

main() {
	local command=${1:-start}

	case "${command}" in
	start | up)
		start_services
		;;
	down | stop)
		cd "${REPO_ROOT}"
		down_services
		if [[ -x "${REPO_ROOT}/deploy/onebot.sh" ]]; then
			"${REPO_ROOT}/deploy/onebot.sh" down
		fi
		;;
	--help | -h)
		usage
		;;
	*)
		usage
		return 1
		;;
	esac
}

main "$@"
