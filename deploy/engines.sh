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

usage() {
	printf 'Usage: %s [up|deploy|stop|restart|logs|ps|pull|down-all] [onebot,onebot-dev,telegram,official,music]\n' "${SCRIPT_NAME}" >&2
	printf 'Default selection: COMPOSE_PROFILES from environment or .env; fallback onebot.\n' >&2
	printf 'stop/down target selected engines; down-all explicitly stops the whole project.\n' >&2
}

die() { printf '[%s] %s\n' "${SCRIPT_NAME}" "$*" >&2; exit 2; }

resolve_compose() {
	command -v docker >/dev/null 2>&1 || die 'Docker is required'
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
	local profile
	IFS=, read -r -a profiles <<<"${selection}"
	for profile in "${profiles[@]}"; do
		case "${profile}" in
		onebot) services+=(napcat kisara) ;;
		onebot-dev) services+=(napcat kisara-dev) ;;
		telegram | official | music) services+=("${profile}") ;;
		*) die "unknown profile: ${profile}" ;;
		esac
	done
	[[ ${#services[@]} -gt 0 ]] || die 'select at least one engine/profile'
	if [[ ",${selection}," == *,onebot,* && ",${selection}," == *,onebot-dev,* ]]; then
		die 'onebot and onebot-dev cannot own the same QQ state concurrently'
	fi
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
	local selection=${2:-${COMPOSE_PROFILES:-}}
	[[ $# -le 2 ]] || { usage; return 2; }
	case "${action}" in --help | -h) usage; return 0 ;; esac
	[[ -f "${REPO_ROOT}/.env" ]] || die 'missing .env; copy .env.example and configure selected engines'
	DOTENV_KEYS=()
	dotenv_load "${REPO_ROOT}/.env" || return $?
	if [[ $# -lt 2 || -z $2 ]]; then selection=${COMPOSE_PROFILES-onebot}; fi
	select_services "$selection"
	resolve_compose
	case "${action}" in
	up | start | deploy)
		if [[ ",${profiles[*]}," == *onebot* ]]; then
			export KISARA_HOST_UID="$(id -u)" KISARA_HOST_GID="$(id -g)"
			mkdir -p -- "${REPO_ROOT}/data/napcat/config" "${REPO_ROOT}/data/napcat/QQ" "${REPO_ROOT}/data/kisara/setu"
			chmod 2770 -- "${REPO_ROOT}/data/kisara/setu"
			if [[ " ${profiles[*]} " == *' onebot-dev '* ]]; then
				run_compose stop kisara
			else
				run_compose stop kisara-dev
			fi
		fi
		if [[ "${action}" == deploy ]]; then
			run_compose up --build --detach "${services[@]}"
		else
			run_compose up --build "${services[@]}"
		fi
		;;
	stop | down) run_compose stop "${services[@]}" ;;
	restart) run_compose restart "${services[@]}" ;;
	logs) run_compose logs --follow --tail "${KISARA_LOG_TAIL:-100}" "${services[@]}" ;;
	ps | status) run_compose ps "${services[@]}" ;;
	pull) run_compose pull --ignore-buildable "${services[@]}" ;;
	down-all) run_compose down ;;
	*) usage; return 2 ;;
	esac
}

main "$@"
