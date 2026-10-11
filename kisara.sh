#!/usr/bin/env bash
# Public command dispatcher; runtime ownership stays in hako and deploy/engines.sh.
set -Eeuo pipefail

readonly SCRIPT_NAME="${BASH_SOURCE[0]##*/}"
readonly STYLE_RESET=$'\033[0m'
readonly STYLE_TITLE=$'\033[1;36m'
readonly STYLE_OPTION=$'\033[1;32m'
readonly STYLE_ERROR=$'\033[1;31m'

style_text() {
	local style=$1 text=$2
	if [[ ! -t 2 || -v NO_COLOR || ${TERM:-} == dumb ]]; then
		printf '%s' "$text"
	else
		printf '%s%s%s' "$style" "$text" "$STYLE_RESET"
	fi
}

usage() {
	printf '%s\n' "$(style_text "$STYLE_TITLE" "Usage: ./${SCRIPT_NAME} <command> [arguments...]")" >&2
	printf '\n%s\n' "$(style_text "$STYLE_OPTION" 'Offline commands:')" >&2
	printf '  console                         Open the interactive bot console\n' >&2
	printf '  test [pytest arguments...]      Run all tests, or selected tests\n' >&2
	printf '\n%s\n' "$(style_text "$STYLE_OPTION" 'Online commands:')" >&2
	printf '  preview [start|stop|down|status|build] [engine,...] [--verbose]\n' >&2
	printf '  up [engine,...]                 Build/recreate in the background\n' >&2
	printf '  down|stop|restart|logs|ps|status|pull [engine,...]\n' >&2
	printf '  down-all                        Stop the whole Compose project\n' >&2
	printf '\nEngines/profiles: onebot, onebot-dev, telegram, official, music\n' >&2
	printf 'Omitted online targets use the configured selection. Preview defaults to start.\n' >&2
	printf 'Offline commands do not load .env. Configure .env before online startup.\n' >&2
	printf '\n%s\n' "$(style_text "$STYLE_OPTION" 'Examples:')" >&2
	printf '  ./%s test tests/unit/test_settings.py -q\n' "$SCRIPT_NAME" >&2
	printf '  ./%s preview start telegram\n' "$SCRIPT_NAME" >&2
	printf '  ./%s up telegram\n' "$SCRIPT_NAME" >&2
}

input_error() {
	printf '%s\n' "$(style_text "$STYLE_ERROR" "Error: $*")" >&2
	usage
	return 2
}

validate_target() {
	local target=$1 profile
	local -a selected_profiles=()
	local seen=,
	[[ $target =~ ^(onebot|onebot-dev|telegram|official|music)(,(onebot|onebot-dev|telegram|official|music))*$ ]] ||
		{ input_error 'invalid engine/profile list'; return 2; }
	IFS=, read -r -a selected_profiles <<<"$target"
	for profile in "${selected_profiles[@]}"; do
		[[ $seen != *",${profile},"* ]] || { input_error 'duplicate engine/profile'; return 2; }
		seen+="${profile},"
	done
	[[ $seen != *,onebot,* || $seen != *,onebot-dev,* ]] ||
		{ input_error 'onebot and onebot-dev cannot own the same QQ state concurrently'; return 2; }
}

main() {
	local action=${1:-help} repo_root backend
	[[ $# -eq 0 ]] || shift
	case "$action" in
	help | --help | -h)
		[[ $# -eq 0 ]] || { input_error 'help accepts no arguments'; return 2; }
		usage
		return 0
		;;
	console)
		[[ $# -eq 0 ]] || { input_error 'console accepts no arguments'; return 2; }
		;;
	test) ;;
	preview) ;;
	up | down | stop | restart | logs | ps | status | pull)
		[[ $# -le 1 ]] || { input_error 'expected at most one engine/profile list'; return 2; }
		[[ $# -eq 0 ]] || validate_target "$1" || return $?
		;;
	down-all)
		[[ $# -eq 0 ]] || { input_error 'down-all accepts no target'; return 2; }
		;;
	*) input_error 'unknown command'; return 2 ;;
	esac
	repo_root=$(cd -- "${BASH_SOURCE[0]%/*}" && pwd -P)
	case "$action" in
	console | test) backend="${repo_root}/hako" ;;
	*) backend="${repo_root}/deploy/engines.sh" ;;
	esac
	[[ -x $backend ]] || { printf 'Error: executable backend was not found: %s\n' "$backend" >&2; return 1; }
	case "$action" in
	console | test)
		# Clear the credential-loading mode even when inherited from an online shell.
		export HAKO_SERVICE="" HAKO_SCOPE=kisara.sh
		if [[ $action == console ]]; then
			exec "$backend" python -m kisara.bot.console
		fi
		exec "$backend" python -m pytest "$@"
		;;
	up) exec "$backend" deploy "$@" ;;
	*) exec "$backend" "$action" "$@" ;;
	esac
}

main "$@"
