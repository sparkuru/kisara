#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_NAME="${BASH_SOURCE[0]##*/}"

usage() {
	printf 'Usage: %s [--test [pytest arguments...] | --all [pytest arguments...]]\n' "${SCRIPT_NAME}" >&2
	printf 'Open an offline interactive bot console by default. Exit with /quit or Ctrl-D.\n' >&2
	printf 'Requires Docker. Automated tests also require the .[dev] dependencies.\n' >&2
}

main() {
	local repo_root
	local -a command=(python -m kisara.bot.console)
	case "${1:-}" in
	--help | -h)
		usage
		return 0
		;;
	--all)
		shift
		command=(python -m pytest tests "$@")
		;;
	--test)
		shift
		command=(python -m pytest tests/unit/test_offline_commands.py "$@")
		;;
	"")
		;;
	*) usage; return 2 ;;
	esac
	repo_root=$(cd -- "${BASH_SOURCE[0]%/*}" && pwd)
	[[ -x "${repo_root}/hako" ]] || {
		printf 'Error: executable hako was not found\n' >&2
		return 1
	}
	# Offline commands must not inherit the bot service's credential-loading mode.
	export HAKO_SERVICE="" HAKO_SCOPE=dev.sh
	exec "${repo_root}/hako" "${command[@]}"
}

main "$@"
