#!/usr/bin/env bash
set -Eeuo pipefail

main() {
	if [[ $# -gt 0 ]]; then
		case $1 in
		--help | --version) exec telegram-bot-api "$@" ;;
		esac
		printf 'Unsupported Bot API server argument.\n' >&2
		return 2
	fi
	[[ ${TELEGRAM_API_ID:-} =~ ^[1-9][0-9]*$ && ${TELEGRAM_API_HASH:-} =~ ^[[:xdigit:]]{32}$ ]] || {
		printf 'Set TELEGRAM_API_ID and TELEGRAM_API_HASH for the local Bot API server.\n' >&2
		return 2
	}
	# TDLib creates private cache files; the bot shares this server UID.
	umask 077
	exec telegram-bot-api --local --http-port=8081 --http-ip-address=0.0.0.0 \
		--dir=/var/lib/telegram-bot-api --verbosity=0 --memory-verbosity=0
}

main "$@"
