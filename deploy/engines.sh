#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_NAME="${BASH_SOURCE[0]##*/}"
readonly REPO_ROOT="$(cd -- "${BASH_SOURCE[0]%/*}/.." && pwd)"
readonly COMPOSE_FILE="${REPO_ROOT}/deploy/compose.yaml"
compose_command=()
services=()
profiles=()
# shellcheck source=deploy/dotenv.sh
source "${REPO_ROOT}/deploy/dotenv.sh"
source "${REPO_ROOT}/deploy/lifecycle.sh"

usage() {
	printf 'Usage: %s [up|deploy|down|restart|logs|ps|pull|down-all] [onebot,onebot-dev,telegram,official,music]\n' "${SCRIPT_NAME}" >&2
	printf 'Default selection: COMPOSE_PROFILES from environment or .env; fallback onebot.\n' >&2
	printf 'down removes selected containers with storage retained; down-all selects the whole project.\n' >&2
}

die() { printf '[%s] %s\n' "${SCRIPT_NAME}" "$*" >&2; exit 2; }

resolve_compose() {
	command -v docker >/dev/null 2>&1 || die 'Docker is required'
	command -v timeout >/dev/null 2>&1 || die 'timeout is required for bounded container inspection'
	if docker compose version >/dev/null 2>&1; then
		compose_command=(docker compose)
	elif command -v docker-compose >/dev/null 2>&1; then
		compose_command=(docker-compose)
	else
		die 'Docker Compose is required'
	fi
}

run_compose() {
	local -a profile_args=()
	local profile
	for profile in "${profiles[@]}"; do profile_args+=(--profile "${profile}"); done
	"${compose_command[@]}" --env-file "${REPO_ROOT}/.env" \
		--project-name "${COMPOSE_PROJECT_NAME:-kisara}" --file "${COMPOSE_FILE}" \
		"${profile_args[@]}" "$@"
}

select_services() {
	local selection=$1
	local profile seen=','
	[[ -n $selection && $selection != ,* && $selection != *, && $selection != *,,* ]] || die 'select a nonempty profile list'
	IFS=, read -r -a profiles <<<"${selection}"
	for profile in "${profiles[@]}"; do
		[[ $seen != *",$profile,"* ]] || die 'duplicate profile'
		seen+="$profile,"
		case "${profile}" in
		onebot) services+=(napcat kisara) ;;
		onebot-dev) services+=(napcat kisara-dev) ;;
		telegram | official | music) services+=("${profile}") ;;
		*) die "unknown profile: ${profile}" ;;
		esac
	done
	if [[ " ${services[*]} " == *' telegram '* ]]; then
		local local_mode=${TELEGRAM_LOCAL_MODE:-false}
		case ${local_mode,,} in
		true | 1 | yes | on)
			profiles+=(telegram-local)
			services=(telegram-bot-api "${services[@]}")
			;;
		esac
	fi
	[[ ${#services[@]} -gt 0 ]] || die 'select at least one engine/profile'
	if [[ ",${selection}," == *,onebot,* && ",${selection}," == *,onebot-dev,* ]]; then
		die 'onebot and onebot-dev cannot own the same QQ state concurrently'
	fi
}

start_local_api() {
	[[ " ${services[*]} " == *' telegram-bot-api '* ]] || return 0
	[[ ${TELEGRAM_API_ID:-} =~ ^[1-9][0-9]*$ && ${TELEGRAM_API_HASH:-} =~ ^[[:xdigit:]]{32}$ ]] ||
		die 'Set TELEGRAM_API_ID and TELEGRAM_API_HASH for the local Bot API server'
	[[ ${TELEGRAM_API_BASE_URL:-https://api.telegram.org} == http://telegram-bot-api:8081 ]] ||
		die 'Local deployment requires TELEGRAM_API_BASE_URL=http://telegram-bot-api:8081'
	run_compose up --no-build --detach telegram-bot-api
	wait_local_api
}

wait_local_api() {
	local id health deadline=$((SECONDS + 90))
	id=$(run_compose ps --quiet telegram-bot-api)
	[[ -n $id && $id != *$'\n'* ]] || die 'Expected one local Bot API server container'
	while [[ $SECONDS -lt $deadline ]]; do
		health=$(timeout 5 docker inspect --format '{{.State.Health.Status}}' "$id") || die 'Cannot inspect local Bot API health'
		case $health in
		healthy) return 0 ;;
		starting) sleep 1 ;;
		*) die 'Local Bot API is not healthy; inspect its private logs before retrying' ;;
		esac
	done
	die 'Local Bot API startup timed out; persistent data retained'
}

main() {
	local action=${1:-deploy}
	if [[ $action == preview ]]; then
		shift
		source "${REPO_ROOT}/deploy/preview-console.sh"
		source "${REPO_ROOT}/deploy/preview-runtime.sh"
		preview_run "$@"
		return
	fi
	local selection=${2-${COMPOSE_PROFILES-}}
	[[ $# -le 2 ]] || { usage; return 2; }
	case "${action}" in --help | -h) usage; return 0 ;; esac
	case $action in up | start | deploy | down | restart | logs | ps | status | pull | down-all) ;; *) usage; return 2 ;; esac
	[[ -f "${REPO_ROOT}/.env" ]] || die 'missing .env; copy .env.example and configure selected engines'
	DOTENV_KEYS=()
	dotenv_load "${REPO_ROOT}/.env" || return $?
	if [[ $# -lt 2 ]]; then selection=${COMPOSE_PROFILES-onebot}; fi
	select_services "$selection"
	resolve_compose
	lifecycle_docker_command=(docker)
	declare -gA lifecycle_ids=()
	lifecycle_targets
	if [[ $action == down-all ]]; then
		lifecycle_project_preflight || return $?
	else
		lifecycle_preflight "${lifecycle_services[@]}" || return $?
	fi
	local -a bot_services=() auxiliary_services=() diagnostic_services=()
	local service
	for service in "${services[@]}"; do
		case $service in
		kisara | kisara-dev | telegram | official) bot_services+=("$service") ;;
		telegram-bot-api) ;;
		*) auxiliary_services+=("$service") ;;
		esac
	done
	for service in "${lifecycle_services[@]}"; do
		[[ $service == bot ]] || diagnostic_services+=("$service")
	done
	case "${action}" in
	up | start | deploy)
		run_compose config --quiet
		# Validate local prerequisites before switching any existing application.
		if [[ " ${services[*]} " == *' telegram-bot-api '* ]]; then
			[[ ${TELEGRAM_API_ID:-} =~ ^[1-9][0-9]*$ && ${TELEGRAM_API_HASH:-} =~ ^[[:xdigit:]]{32}$ ]] || die 'Set TELEGRAM_API_ID and TELEGRAM_API_HASH for the local Bot API server'
			[[ ${TELEGRAM_API_BASE_URL:-https://api.telegram.org} == http://telegram-bot-api:8081 ]] || die 'Local deployment requires TELEGRAM_API_BASE_URL=http://telegram-bot-api:8081'
		fi
		local -a build_services=("${bot_services[@]}")
		[[ " ${services[*]} " != *' telegram-bot-api '* ]] || build_services+=(telegram-bot-api)
		[[ ${#build_services[@]} -eq 0 ]] || run_compose build "${build_services[@]}"
		lifecycle_switch || return $?
		export KISARA_HOST_UID="$(id -u)" KISARA_HOST_GID="$(id -g)"
		if [[ " ${services[*]} " == *' telegram '* ]]; then
			mkdir -p -- "${REPO_ROOT}/data/kisara/tgsetu"
			chmod 2770 -- "${REPO_ROOT}/data/kisara/tgsetu"
		fi
		if [[ ",${profiles[*]}," == *onebot* ]]; then
			mkdir -p -- "${REPO_ROOT}/data/napcat/config" "${REPO_ROOT}/data/napcat/QQ" "${REPO_ROOT}/data/kisara/setu"
			chmod 2770 -- "${REPO_ROOT}/data/kisara/setu"
		fi
		start_local_api
		[[ ${#auxiliary_services[@]} -eq 0 ]] || run_compose up --no-build --detach "${auxiliary_services[@]}"
		[[ ${#bot_services[@]} -gt 0 ]] || return 0
		if [[ "${action}" == deploy ]]; then
			run_compose up --no-build --force-recreate --no-deps --detach "${bot_services[@]}"
		else
			run_compose up --no-build --force-recreate --no-deps "${bot_services[@]}"
		fi
		;;
	down)
		for service in "${lifecycle_services[@]}"; do lifecycle_remove "$service" || return $?; done
		;;
	restart)
		if [[ " ${services[*]} " == *' telegram-bot-api '* ]]; then
			run_compose restart telegram-bot-api
			wait_local_api
		fi
		[[ ${#auxiliary_services[@]} -eq 0 ]] || run_compose restart "${auxiliary_services[@]}"
		[[ ${#bot_services[@]} -eq 0 ]] || run_compose restart "${bot_services[@]}"
		;;
	logs) run_compose logs --follow --tail "${KISARA_LOG_TAIL:-100}" "${diagnostic_services[@]}" ;;
	ps | status) run_compose ps "${diagnostic_services[@]}" ;;
	pull) run_compose pull --ignore-buildable "${services[@]}" ;;
	down-all)
		# Scoped ID removal also covers verified old Official hako runtimes.
		for service in "${!lifecycle_ids[@]}"; do lifecycle_remove "$service" || return $?; done
		;;
	*) usage; return 2 ;;
	esac
}

main "$@"
