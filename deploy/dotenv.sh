#!/usr/bin/env bash
# Shared data parser; sourcing this file has no shell-option or runtime effects.

dotenv_load() {
	local path=$1 line key value suffix
	local -A seen=()
	[[ -f $path ]] || return 1
	while IFS= read -r line || [[ -n $line ]]; do
		line=${line%$'\r'}
		[[ $line =~ ^[[:space:]]*(#.*)?$ ]] && continue
		if [[ ! $line =~ ^[[:space:]]*(export[[:space:]]+)?([a-zA-Z_][a-zA-Z_0-9]*)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
			printf '[error] Invalid dotenv assignment; use KEY=value, not shell code.\n' >&2
			return 2
		fi
		key=${BASH_REMATCH[2]}
		value=${BASH_REMATCH[3]}
		case $key in
		KISARA_* | ONEBOT_* | NAPCAT_* | TELEGRAM_* | OFFICIAL_* | HAKO_* | BOT_* | COMPOSE_PROFILES | COMPOSE_PROJECT_NAME | DOCKER_CONTEXT | DOCKER_HOST | AppID | AppSecret | SAUCENAO_API_KEY | TIANAPI_KEY) ;;
		*) printf '[error] Unsupported configuration key: %s\n' "$key" >&2; return 2 ;;
		esac
		if [[ -v seen[$key] ]]; then
			printf '[error] Duplicate dotenv key: %s\n' "$key" >&2
			return 2
		fi
		seen[$key]=1
		case $value in
		\"* | \'*)
			local quote=${value:0:1}
			value=${value:1}
			[[ $value == *"$quote"* ]] || { printf '[error] Unclosed dotenv quote: %s\n' "$key" >&2; return 2; }
			suffix=${value#*"$quote"}
			value=${value%%"$quote"*}
			[[ $suffix =~ ^[[:space:]]*(#.*)?$ ]] || { printf '[error] Unsupported dotenv quoting: %s\n' "$key" >&2; return 2; }
			;;
		*)
			value=${value%%[[:space:]]#*}
			value="${value%"${value##*[![:space:]]}"}"
			;;
		esac
		# Environment wins by presence, including an explicitly empty value.
		if ! [[ -v $key ]]; then
			printf -v "$key" '%s' "$value"
			export "${key?}"
		fi
		DOTENV_KEYS+=("$key")
	done <"$path"
}
