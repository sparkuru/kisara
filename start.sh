#!/usr/bin/env bash
# start.sh - Select a Kisara engine and start the development service.
set -Eeuo pipefail

SCRIPT_NAME="${BASH_SOURCE[0]##*/}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
	printf 'Usage: %s [onebot|onebot-dev|official]\n' "${SCRIPT_NAME}" >&2
	printf '\n' >&2
	printf 'Default engine: onebot\n' >&2
	printf 'Set KISARA_ENGINE or pass an engine explicitly to skip the menu.\n' >&2
}

die() {
	printf '[%s] %s\n' "${SCRIPT_NAME}" "$*" >&2
	exit 1
}

validate_engine() {
	case "$1" in
	onebot | onebot-dev | official) ;;
	*)
		die "unknown engine: $1; choose onebot, onebot-dev, or official"
		;;
	esac
}

choose_engine() {
	local selected_engine="${KISARA_ENGINE:-}"
	local choice

	if [[ -n "${selected_engine}" ]]; then
		validate_engine "${selected_engine}"
		printf '%s\n' "${selected_engine}"
		return 0
	fi

	if [[ ! -t 0 ]]; then
		printf '[%s] non-interactive input; using default engine: onebot\n' \
			"${SCRIPT_NAME}" >&2
		printf '%s\n' "onebot"
		return 0
	fi

	printf 'Select Kisara engine:\n' >&2
	printf '  1) onebot  (NapCatQQ + OneBot 11)\n' >&2
	printf '  2) onebot-dev (OneBot 11 with source hot reload)\n' >&2
	printf '  3) official (Tencent official bot platform)\n' >&2
	read -r -p 'Engine [1]: ' choice
	case "${choice}" in
	"" | 1)
		printf '%s\n' "onebot"
		;;
	2)
		printf '%s\n' "onebot-dev"
		;;
	3)
		printf '%s\n' "official"
		;;
	*)
		die "invalid selection: ${choice}"
		;;
	esac
}

main() {
	local selected_engine

	case "${1:-}" in
	--help | -h)
		usage
		return 0
		;;
	"" | onebot | onebot-dev | official)
		if [[ $# -gt 1 ]]; then
			usage
			return 1
		fi
		if [[ $# -eq 1 ]]; then
			selected_engine=$1
			validate_engine "${selected_engine}"
		else
			selected_engine=$(choose_engine)
		fi
		;;
	*)
		usage
		return 1
		;;
	esac

	export KISARA_ENGINE="${selected_engine}"
	printf '[%s] starting engine: %s\n' "${SCRIPT_NAME}" "${KISARA_ENGINE}" >&2
	exec "${REPO_ROOT}/dev.sh" start
}

main "$@"
