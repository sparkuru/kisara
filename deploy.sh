#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_NAME="${BASH_SOURCE[0]##*/}"

usage() {
	printf 'Usage: %s [up|down|logs|ps|pull]\n' "${SCRIPT_NAME}" >&2
	printf 'Start the NapCat + Kisara Docker stack in the background (default: up).\n' >&2
	printf 'Configure .env before starting; use logs to follow console output.\n' >&2
}

main() {
	local repo_root
	local action=${1:-up}
	[[ $# -le 1 ]] || { usage; return 2; }
	case "${action}" in
	--help | -h)
		usage
		return 0
		;;
	up | start) action=deploy ;;
	down | stop | logs | ps | status | pull) ;;
	*) usage; return 2 ;;
	esac
	repo_root=$(cd -- "${BASH_SOURCE[0]%/*}" && pwd)
	[[ -x "${repo_root}/deploy/onebot.sh" ]] || {
		printf 'Error: executable deploy/onebot.sh was not found\n' >&2
		return 1
	}
	exec "${repo_root}/deploy/onebot.sh" "${action}"
}

main "$@"
