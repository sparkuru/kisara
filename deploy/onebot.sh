#!/usr/bin/env bash
# Scoped OneBot forwarding entry; lifecycle implementation lives in engines.sh.
set -Eeuo pipefail

main() {
	local action=${1:-up} backend
	[[ $# -le 1 ]] || { printf 'Expected at most one command.\n' >&2; return 2; }
	backend="$(cd -- "${BASH_SOURCE[0]%/*}" && pwd)/engines.sh"
	case $action in
	--help | -h)
		printf 'Usage: onebot.sh [up|start|dev|deploy|down|logs|ps|status|pull]\n' >&2
		return 0 ;;
	dev) exec "$backend" up onebot-dev ;;
	up | start | deploy | down | logs | ps | status | pull) exec "$backend" "$action" onebot ;;
	*) printf 'Unknown OneBot command.\n' >&2; return 2 ;;
	esac
}

main "$@"
