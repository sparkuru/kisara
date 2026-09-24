#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_NAME="${BASH_SOURCE[0]##*/}"
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${DEPLOY_DIR}/.." && pwd)"
COMPOSE_FILE="${DEPLOY_DIR}/compose.yaml"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-kisara}"

compose_command=()

usage() {
	printf 'Usage: %s [up|dev|deploy|down|logs|ps|pull]\n' "${SCRIPT_NAME}" >&2
	printf '       up and dev require a configured repository .env file.\n' >&2
}

die() {
	printf '[%s] %s\n' "${SCRIPT_NAME}" "$*" >&2
	exit 1
}

require_command() {
	command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

resolve_compose() {
	if docker compose version >/dev/null 2>&1; then
		compose_command=(docker compose)
		return 0
	fi

	if command -v docker-compose >/dev/null 2>&1; then
		compose_command=(docker-compose)
		return 0
	fi

	die "Docker Compose is required (docker compose or docker-compose)"
}

run_compose() {
	(
		cd "${REPO_ROOT}"
		"${compose_command[@]}" \
			--env-file "${REPO_ROOT}/.env" \
			--project-name "${PROJECT_NAME}" \
			--file "${COMPOSE_FILE}" \
			"$@"
	)
}

stop_service_if_present() {
	local service_name=$1
	local container_ids

	container_ids=$(run_compose ps -q "${service_name}")
	if [[ -n "${container_ids}" ]]; then
		run_compose stop "${service_name}"
	fi
}

prepare_data_directories() {
	mkdir -p -- \
		"${REPO_ROOT}/data/napcat/config" \
		"${REPO_ROOT}/data/napcat/QQ" \
		"${REPO_ROOT}/data/kisara/setu"
	chmod 2770 -- "${REPO_ROOT}/data/kisara/setu"
}

start_stack() {
	[[ -f "${REPO_ROOT}/.env" ]] || {
		die "missing .env; copy .env.example and configure OneBot"
	}

	local napcat_uid="${NAPCAT_UID:-$(id -u)}"
	local napcat_gid="${NAPCAT_GID:-$(id -g)}"
	local setu_gid="${KISARA_SETU_GID:-$(id -g)}"
	export NAPCAT_UID="${napcat_uid}"
	export NAPCAT_GID="${napcat_gid}"
	export KISARA_SETU_GID="${setu_gid}"

	prepare_data_directories
	stop_service_if_present kisara-dev
	run_compose up --build "$@" napcat kisara
}

start_dev_stack() {
	[[ -f "${REPO_ROOT}/.env" ]] || {
		die "missing .env; copy .env.example and configure OneBot"
	}

	local napcat_uid="${NAPCAT_UID:-$(id -u)}"
	local napcat_gid="${NAPCAT_GID:-$(id -g)}"
	local setu_gid="${KISARA_SETU_GID:-$(id -g)}"
	export NAPCAT_UID="${napcat_uid}"
	export NAPCAT_GID="${napcat_gid}"
	export KISARA_SETU_GID="${setu_gid}"

	prepare_data_directories
	stop_service_if_present kisara
	run_compose up --build napcat kisara-dev
}

main() {
	local command="${1:-up}"

	[[ $# -le 1 ]] || die "expected at most one command"
	if [[ "${command}" == --help || "${command}" == -h ]]; then
		usage
		return 0
	fi
	set -- "${command}"
	require_command docker
	resolve_compose

	case "${command}" in
	up | start)
		[[ $# -eq 1 ]] || die "up accepts no additional arguments"
		start_stack
		;;
	deploy)
		start_stack --detach
		;;
	dev)
		[[ $# -eq 1 ]] || die "dev accepts no additional arguments"
		start_dev_stack
		;;
	down | stop)
		[[ $# -eq 1 ]] || die "down accepts no additional arguments"
		run_compose down
		;;
	logs)
		[[ $# -eq 1 ]] || die "logs accepts no additional arguments"
		run_compose logs --follow --tail "${KISARA_LOG_TAIL:-100}"
		;;
	ps | status)
		[[ $# -eq 1 ]] || die "ps accepts no additional arguments"
		run_compose ps
		;;
	pull)
		[[ $# -eq 1 ]] || die "pull accepts no additional arguments"
		run_compose pull napcat
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
