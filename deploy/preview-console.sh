#!/usr/bin/env bash
# Project-authored presentation helpers; source without side effects.
readonly STYLE_PREVIEW_TITLE=$'\033[1;36m'
readonly STYLE_PREVIEW_SECTION=$'\033[1;32m'
readonly STYLE_PREVIEW_LOG=$'\033[0;36m'
readonly STYLE_PREVIEW_SUCCESS=$'\033[0;32m'
readonly STYLE_PREVIEW_WARNING=$'\033[0;33m'
readonly STYLE_PREVIEW_ERROR=$'\033[0;31m'
readonly STYLE_PREVIEW_RESET=$'\033[0m'

preview_message() {
	local role=$1 fd=$2 text=$3 style=''
	if [[ ! -v NO_COLOR && ${TERM:-} != dumb && -t $fd ]]; then
		case $role in
		title) style=$STYLE_PREVIEW_TITLE ;;
		section) style=$STYLE_PREVIEW_SECTION ;;
		log) style=$STYLE_PREVIEW_LOG ;;
		success) style=$STYLE_PREVIEW_SUCCESS ;;
		warn) style=$STYLE_PREVIEW_WARNING ;;
		error) style=$STYLE_PREVIEW_ERROR ;;
		esac
	fi
	if [[ -n $style ]]; then
		printf '%s%s%s\n' "$style" "$text" "$STYLE_PREVIEW_RESET" >&"$fd"
	else
		printf '%s\n' "$text" >&"$fd"
	fi
}

preview_log() { preview_message log 2 "[log] $*"; }
preview_error() { preview_message error 2 "[error] $*"; }

preview_usage() {
	preview_message title 2 'Usage: ./preview.sh [start|stop|down|status|build] [--verbose]'
	preview_message section 2 'Commands:'
	printf '%s\n' \
		'  start    Prepare only missing resources, start detached, wait for readiness.' \
		'  status   Inspect readiness; never build/install/start.' \
		'  build    Explicit rebuild/preparation; never start the service group.' \
		'  stop/down Stop and remove only owned preview containers; preserve volumes/data.' \
		'  --verbose Show captured, redacted details after each step (not streaming).' \
		'  --help    Read no configuration and perform no Docker operations.' >&2
	preview_message section 2 'First use:'
	printf '%s\n' \
		'  cp .env.example .env (only if absent); edit selected engine credentials/access lists.' \
		'  OneBot: ONEBOT_ALLOWED_USERS, ONEBOT_ACCESS_TOKEN, NAPCAT_WEBUI_TOKEN; log into NapCat.' \
		'  Telegram: TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS. Official: OFFICIAL_APP_ID/SECRET.' \
		'  Required host tools: Bash 4.4+, Docker/Compose, timeout, sha256sum, sed, awk; ip for wildcard local publishing.' \
		'  Root .env is data; inherited environment wins by presence, including empty values.' \
		'  First start may download missing images and pinned Python 3.12 packages; no host Python required.' \
		'  KISARA_PREVIEW_OFFLINE=true forbids automatic build/pull/install; prepare explicitly when online.' \
		'  Rebuild after dependency/image source changes: ./preview.sh build; stop first if a group exists.' \
		'  Loopback/SSH-tunnel and internal-only boundaries remain; bot engines have no inbound listener.' \
		'  stdout contains one ready access summary; help/progress/errors use stderr. NO_COLOR disables color.' >&2
}

preview_section() {
	local heading=$1
	shift
	[[ $# -gt 0 ]] || return 0
	printf '\n'
	preview_message section 1 "$heading:"
	printf '%s\n' "$@"
}
