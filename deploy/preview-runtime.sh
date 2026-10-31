#!/usr/bin/env bash
# Preview operations for the existing engine lifecycle; no top-level effects.
source "${BASH_SOURCE[0]%/*}/qq-login-logs.sh"

preview_capture() {
	local label=$1 status=0
	shift
	preview_log "$label"
	"$@" >"${preview_tmp}/step.log" 2>&1 || status=$?
	if [[ $status -ne 0 || $preview_verbose == true ]]; then
		preview_redact "${preview_tmp}/step.log" || preview_error 'Detailed output unavailable: redaction failed.'
	fi
	[[ $status -eq 0 ]] || preview_error "$label failed (exit $status)."
	return "$status"
}

preview_redact_values() {
	local identifiers=${1:-redact} key secret part
	local -a pieces=()
	while IFS= read -r key; do
		case $key in
		*ACCOUNT | *USERS | *GROUPS) [[ $identifiers != show ]] || continue ;;
		esac
		case $key in
		KISARA_* | ONEBOT_* | TELEGRAM_* | OFFICIAL_* | NAPCAT_* | AppID | AppSecret | SAUCENAO_API_KEY | TIANAPI_KEY)
			secret=${!key}
			[[ -n $secret ]] || continue
			case $key in
			*TOKEN* | *SECRET* | *SESSDATA* | *HASH* | *API_ID* | *KEY* | *PASSWORD* | *ACCOUNT* | *APP_ID* | *USERS* | *GROUPS* | *_URL | AppID | AppSecret)
				preview_secrets+=("$secret")
				IFS=, read -r -a pieces <<<"$secret"
				for part in "${pieces[@]}"; do [[ -z $part ]] || preview_secrets+=("$part"); done
				;;
			esac
			;;
		esac
	done < <(compgen -e)
	preview_filters=(
		-e $'s#\033\\][^\007]*(\007|\033\\\\)##g'
		-e $'s#\033\\[[0-?]*[ -/]*[@-~]##g'
		-e 's#(https?|wss?)://[^ /]+@[^ ]+#\1://[redacted]#g'
		-e 's#[Bb]earer[[:space:]]+[^[:space:]"\x27,;]+#Bearer [redacted]#g'
		-e 's#(https?://api.telegram.org/bot)[^/[:space:]]+#\1[redacted]#g'
		-e 's#([?&](token|access_token|secret|password|key|code)=)[^&[:space:]]+#\1[redacted]#Ig'
		# Match whole UTF-8 symbols even when sed uses a byte-oriented locale.
		-e '/▀|▄|█/d'
		-e 's#https://txz\.qq\.com/[^[:space:]]+#[login-qr]#g'
		-e 's/[[:cntrl:]]//g'
	)
	if [[ $identifiers != show ]]; then
		preview_filters+=(
			-e 's#((user|chat|account|app|guild|channel)([_ ]?id)?[=: ]+)[^[:space:],;:]+#\1[private-id]#Ig'
			-e 's#(Official bot is ready:).*#\1 [private-name]#g'
			-e 's/[0-9]{5,}/[private-id]/g'
		)
	fi
}

preview_filter_logs() {
	# Terminal-control ranges describe bytes, independent of caller collation.
	LC_ALL=C sed "$@" -E "${preview_filters[@]}"
}

preview_replace_secrets() {
	local LC_ALL=C
	local preserve_timestamps=${1:-false} timestamp_prefix='' timestamp
	local line secret csi=$'\033''\[[0-?]*[ -/]*[@-~]' osc=$'\033''\][^'$'\007\033'']*('$'\007''|'$'\033''\\)' qr_url='https://txz[.]qq[.]com/[^[:space:]]+'
	local bearer=$'([Bb]earer)[[:space:]]+([^[:space:]"\x27,;]+)' rest match prefix token
	while IFS= read -r line || [[ -n $line ]]; do
		timestamp_prefix=''
		if [[ $preserve_timestamps == true && $line == *' '* ]]; then
			timestamp=${line%% *}
			if qq_login_timestamp_valid "$timestamp"; then
				timestamp_prefix="$timestamp " line=${line#* }
			fi
		fi
		while [[ $line =~ $osc ]]; do line=${line/"${BASH_REMATCH[0]}"/}; done
		while [[ $line =~ $csi ]]; do line=${line/"${BASH_REMATCH[0]}"/}; done
		while [[ $line =~ $qr_url ]]; do line=${line/"${BASH_REMATCH[0]}"/'[login-qr]'}; done
		# Keep Bearer separators recognizable without consuming a split secret.
		rest=$line line=''
		while [[ $rest =~ $bearer ]]; do
			match=${BASH_REMATCH[0]} prefix=${BASH_REMATCH[1]} token=${BASH_REMATCH[2]}
			line+=${rest%%"$match"*}"$prefix $token"
			rest=${rest#*"$match"}
		done
		line+=$rest
		line=${line//[[:cntrl:]]/}
		for secret in "${preview_secrets[@]}"; do line=${line//"$secret"/[redacted]}; done
		printf '%s%s\n' "$timestamp_prefix" "$line"
	done
}

preview_redact() {
	local file=$1
	local -a preview_secrets=() preview_filters=()
	preview_redact_values
	# Failure diagnostics stay quiet; status explicitly exposes bot IO summaries.
	preview_filters+=(-e '/(Received|Replying|No reply).*message user=/d')
	preview_replace_secrets <"$file" | preview_filter_logs >"${preview_tmp}/safe.log" || return 1
	cat -- "${preview_tmp}/safe.log" >&2
}

preview_log_lines() { qq_login_log_lines "$@"; }

preview_stop_readers() {
	local pid attempt active
	for pid in "${preview_log_pids[@]}"; do kill -TERM "$pid" 2>/dev/null || :; done
	for attempt in {1..10}; do
		active=false
		for pid in "${preview_log_pids[@]}"; do if kill -0 "$pid" 2>/dev/null; then active=true; break; fi; done
		[[ $active == true ]] || break
		sleep 0.02
	done
	# Readers hold no state. Force termination also bounds cleanup of a stuck CLI.
	for pid in "${preview_log_pids[@]}"; do kill -KILL "$pid" 2>/dev/null || :; done
	for pid in "${preview_log_pids[@]}"; do wait "$pid" 2>/dev/null || :; done
	preview_log_pids=()
}

preview_start_log_readers() {
	local service id running qq_snapshot qq_boundary qq_boundary_count preserve_timestamps
	local -a log_args=()
	local -a targets=("${services[@]}") preview_secrets=() preview_filters=()
	preview_redact_values show
	for service in "${targets[@]}"; do
		case $service in
		napcat | kisara | kisara-dev | telegram | official | bot) ;;
		*) [[ ${qq_follow_auxiliary:-false} == true ]] || continue ;;
		esac
		id=${preview_ids[$service]}
		preview_owned "$id" "$service" || { preview_error "Cannot follow $service logs: ownership mismatch/unavailable."; return 1; }
		qq_snapshot='' qq_boundary='' qq_boundary_count=0 preserve_timestamps=false
		log_args=(--follow --tail "${qq_log_tail:-80}")
		if [[ $service == napcat && -t 1 && ${TERM:-} != dumb ]]; then
			running=$(timeout 5 "${preview_docker_command[@]}" inspect --format '{{.State.Running}}' "$id" 2>"${preview_tmp}/qr-error") || {
				preview_error 'Cannot inspect QQ log runtime state.'; return 1;
			}
			if [[ $running == true ]]; then
				qq_login_snapshot "$id" || return $?
				log_args=(--follow --timestamps --tail all --since "$qq_boundary")
				preserve_timestamps=true
			fi
		fi
		preview_filter_logs -u </dev/null >/dev/null 2>/dev/null || {
			preview_error 'Bot logs suppressed: streaming redaction unavailable; check sed support.'; return 1;
		}
		mkfifo -- "${preview_tmp}/$service.raw" "${preview_tmp}/$service.replaced" "${preview_tmp}/$service.safe" || {
			preview_error "Cannot create private log pipes for $service."; return 1;
		}
		preview_log "Following $(preview_platform "$service") logs (last 80 lines; Ctrl+C stops viewing only)."
		"${preview_docker_command[@]}" logs "${log_args[@]}" "$id" >"${preview_tmp}/$service.raw" 2>&1 &
		preview_log_pids+=("$!")
		preview_replace_secrets "$preserve_timestamps" <"${preview_tmp}/$service.raw" >"${preview_tmp}/$service.replaced" 2>/dev/null &
		preview_log_pids+=("$!")
		# Track sed itself so cleanup does not leave an untracked child shell.
		LC_ALL=C sed -u -E "${preview_filters[@]}" <"${preview_tmp}/$service.replaced" >"${preview_tmp}/$service.safe" 2>/dev/null &
		preview_log_pids+=("$!")
		preview_log_lines "$service" "$qq_snapshot" "$qq_boundary" "$qq_boundary_count" <"${preview_tmp}/$service.safe" 2>/dev/null &
		preview_log_pids+=("$!")
		preview_logs_started=true
	done
	return 0
}

preview_check_log_readers() {
	local pid status=0
	local -a pending=()
	for pid in "${preview_log_pids[@]}"; do
		if kill -0 "$pid" 2>/dev/null; then
			pending+=("$pid")
		else
			wait "$pid" || status=$?
		fi
	done
	preview_log_pids=("${pending[@]}")
	if [[ $status -ne 0 ]]; then
		preview_error 'Bot log stream/redaction failed; check Docker logs access and sed support. Viewing stopped; containers unchanged.'
		return 1
	fi
}

preview_wait_log_readers() {
	local status
	while [[ ${#preview_log_pids[@]} -gt 0 ]]; do
		preview_check_log_readers || return 1
		[[ ${#preview_log_pids[@]} -gt 0 ]] || break
		status=0
		wait -n || status=$?
		preview_check_log_readers || return 1
		# wait -n can report no jobs when a finite stream finished before the wait.
		if [[ $status -ne 0 && $status -ne 127 ]]; then
			preview_error 'Bot log stream/redaction failed; check Docker logs access and sed support. Viewing stopped; containers unchanged.'
			return 1
		fi
	done
}

preview_docker() { "${preview_docker_command[@]}" "$@"; }

preview_endpoint() {
	preview_docker_command=(docker)
	local context endpoint
	if [[ -n ${DOCKER_CONTEXT:-} ]]; then
		context=$DOCKER_CONTEXT
		preview_docker_command+=(--context "$context")
		preview_docker context inspect --help >"${preview_tmp}/inspect.log" 2>&1 || {
			preview_error 'Docker CLI does not support required context inspection; upgrade the CLI capability.'; return 127;
		}
		endpoint=$(preview_docker context inspect "$context" --format '{{.Endpoints.docker.Host}}' 2>"${preview_tmp}/inspect.log") || {
			preview_error 'Configured Docker context is invalid/unavailable; check docker context inspect <name>.'; return 2;
		}
	elif [[ -n ${DOCKER_HOST:-} ]]; then
		endpoint=$DOCKER_HOST
		preview_docker_command+=(--host "$endpoint")
	else
		preview_docker context inspect --help >"${preview_tmp}/inspect.log" 2>&1 || {
			preview_error 'Docker CLI does not support required current-context inspection; upgrade the CLI capability.'; return 127;
		}
		endpoint=$(preview_docker context inspect --format '{{.Endpoints.docker.Host}}' 2>"${preview_tmp}/inspect.log") || {
			preview_error 'Current Docker context is invalid/unavailable; inspect its configuration with docker context ls/inspect.'; return 2;
		}
	fi
	case $endpoint in
	unix://*) preview_local_host=true ;;
	tcp://* | ssh://* | npipe://*) preview_local_host=false ;;
	*) preview_error 'Unsupported Docker endpoint scheme; configure a supported context/host.'; return 2 ;;
	esac
	timeout 8 "${preview_docker_command[@]}" info --format '{{.ServerVersion}}' >"${preview_tmp}/inspect.log" 2>&1 || {
		preview_error 'Docker daemon is unavailable at the effective endpoint; check access/context.'; return 1;
	}
	if preview_docker compose version >"${preview_tmp}/inspect.log" 2>&1; then
		compose_command=("${preview_docker_command[@]}" compose)
	elif command -v docker-compose >/dev/null 2>&1; then
		# Legacy Compose receives the effective endpoint, without a conflicting host override.
		compose_command=(docker-compose)
		if [[ -n ${DOCKER_CONTEXT:-} ]]; then unset DOCKER_HOST; fi
	else
		preview_error 'Docker Compose plugin or docker-compose is required.'; return 127
	fi
}

preview_valid_ipv6() {
	local address=$1 part compressed=false
	local -a parts=()
	[[ $address == *:* && $address =~ ^[a-fA-F0-9:]+$ && $address != *:::* ]] || return 1
	if [[ $address == *::* ]]; then
		compressed=true
		address=${address/::/:}
		[[ $address != *::* ]] || return 1
		address=${address#:}; address=${address%:}
	else
		[[ $address != :* && $address != *: ]] || return 1
	fi
	IFS=: read -r -a parts <<<"$address"
	for part in "${parts[@]}"; do [[ ${#part} -ge 1 && ${#part} -le 4 ]] || return 1; done
	if [[ $compressed == true ]]; then [[ ${#parts[@]} -lt 8 ]]; else [[ ${#parts[@]} -eq 8 ]]; fi
}

preview_valid_ipv4() {
	local address=$1 octet
	local -a octets=()
	[[ $address =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
	IFS=. read -r -a octets <<<"$address"
	for octet in "${octets[@]}"; do
		[[ ${#octet} -le 3 && $((10#$octet)) -le 255 ]] || return 1
	done
}

preview_valid_listener_host() {
	local address=$1
	if [[ $address == \[*\] ]]; then
		address=${address#\[}; address=${address%\]}
		preview_valid_ipv6 "$address"
	else
		preview_valid_ipv4 "$address"
	fi
}

preview_addresses() {
	preview_addresses_v4=() preview_addresses_v6=()
	local row state address
	local -a fields=()
	local raw
	if [[ $preview_local_host == true ]]; then
		command -v ip >/dev/null 2>&1 || { preview_error 'Wildcard publishing requires ip on the Docker host.'; return 127; }
		raw=$(ip -br a 2>"${preview_tmp}/inspect.log") || { preview_error 'Host address discovery failed: ip -br a.'; return 1; }
	else
		[[ -n ${KISARA_PREVIEW_HOST_ADDRESSES:-} ]] || {
			preview_error 'Remote Docker wildcard publishing needs explicit KISARA_PREVIEW_HOST_ADDRESSES from the daemon host; caller addresses are not used.'; return 2;
		}
		raw="explicit UP ${KISARA_PREVIEW_HOST_ADDRESSES//,/ }"
	fi
	while IFS= read -r row; do
		read -r -a fields <<<"$row"
		[[ ${#fields[@]} -ge 3 ]] || continue
		state=${fields[1]}
		[[ $state == UP || $state == UNKNOWN ]] || continue
		for address in "${fields[@]:2}"; do
			address=${address%%/*}
			if [[ $address =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
				if ! preview_valid_ipv4 "$address"; then
					[[ $preview_local_host == true ]] || { preview_error 'Invalid explicit daemon-host IPv4 address.'; return 2; }
					continue
				fi
				[[ $address != 127.* && $address != 0.* ]] || continue
				[[ " ${preview_addresses_v4[*]} " == *" $address "* ]] || preview_addresses_v4+=("$address")
			elif preview_valid_ipv6 "$address"; then
				if [[ $address != :: && $address != ::1 && ${address,,} != fe[89ab]* ]]; then
					[[ " ${preview_addresses_v6[*]} " == *" $address "* ]] || preview_addresses_v6+=("$address")
				fi
			elif [[ $preview_local_host != true ]]; then
				preview_error 'Invalid explicit daemon-host address; supply IPv4/IPv6 literals.'; return 2
			fi
		done
	done <<<"$raw"
}

preview_compose() {
	local profile
	local -a args=()
	for profile in "${profiles[@]}"; do args+=(--profile "$profile"); done
	"${compose_command[@]}" --env-file "${REPO_ROOT}/.env" --project-name "${COMPOSE_PROJECT_NAME:-kisara}" \
		--file "$COMPOSE_FILE" --file "${preview_tmp}/override.yaml" "${args[@]}" "$@"
}

preview_override() {
	local service image
	printf 'services:\n' >"${preview_tmp}/override.yaml"
	for service in "${services[@]}"; do
		case $service in
		kisara | kisara-dev | telegram | official | telegram-bot-api)
			image="${KISARA_PREVIEW_IMAGE_PREFIX:-${COMPOSE_PROJECT_NAME:-kisara}-preview}-${service}:latest"
			[[ $image =~ ^[a-zA-Z0-9][a-zA-Z0-9._/:-]+$ ]] || { preview_error 'Invalid KISARA_PREVIEW_IMAGE_PREFIX.'; return 2; }
			preview_images[$service]=$image
			printf '  %s:\n    image: %s\n' "$service" "$image" >>"${preview_tmp}/override.yaml"
			if [[ $service != telegram-bot-api ]]; then
				printf '    environment:\n      KISARA_PREVIEW_READINESS: /tmp/kisara-preview-ready.json\n' >>"${preview_tmp}/override.yaml"
			fi
			;;
		esac
	done
	# Auxiliary-only selections need a valid empty override.
	[[ ${#preview_images[@]} -gt 0 ]] || printf 'services: {}\n' >"${preview_tmp}/override.yaml"
}

preview_find() { lifecycle_find "$1"; }
preview_owned() { lifecycle_owned "$1" "$2"; }

preview_collect() {
	local service id
	preview_ids=()
	for service in "${services[@]}"; do
		id=$(preview_find "$service") || return 1
		[[ -n $id && $id != *$'\n'* ]] || { preview_error "Selected $service container is missing/duplicated; start explicitly to reconcile it."; return 1; }
		preview_owned "$id" "$service" || { preview_error "Selected $service repository identity changed/unavailable."; return 2; }
		preview_ids[$service]=$id
	done
}

preview_prepare_image() {
	local service=$1 image=$2 extra=''
	case $service in
	telegram | official) extra=$service ;;
	kisara | kisara-dev) extra=video ;;
	esac
	if ! preview_docker image inspect "$image" >"${preview_tmp}/inspect.log" 2>&1; then
		[[ ${KISARA_PREVIEW_OFFLINE:-false} != true ]] || { preview_error "Missing image for $service; disable offline mode and run ./kisara.sh preview build $preview_target explicitly."; return 1; }
		case $service in
		napcat | music) preview_capture "Pull missing $service image" preview_docker pull "$image" || return $? ;;
		*) preview_capture "Build missing $service image" preview_compose build "$service" || return $? ;;
		esac
	fi
	case $service in
	napcat | music) return 0 ;;
	telegram-bot-api)
		preview_docker run --rm --network none "$image" --version >"${preview_tmp}/inspect.log" 2>&1 || {
			preview_error "Local Bot API binary unavailable; run ./kisara.sh preview build $preview_target explicitly before starting."; return 1;
		}
		return 0
		;;
	esac
	if ! preview_docker run --rm --network none --entrypoint python "$image" /opt/kisara/preview-deps.py check "$extra" >"${preview_tmp}/inspect.log" 2>&1; then
		[[ ${KISARA_PREVIEW_OFFLINE:-false} != true ]] || { preview_error "Missing/incompatible pinned dependencies for $service; run ./kisara.sh preview build $preview_target explicitly while online."; return 1; }
		preview_capture "Prepare pinned $service dependencies through its image build" preview_compose build "$service" || return $?
		preview_docker run --rm --network none --entrypoint python "$image" /opt/kisara/preview-deps.py check "$extra" >"${preview_tmp}/inspect.log" 2>&1 || {
			preview_error "Dependencies still unavailable for $service after preparation; no services started."; return 1;
		}
	fi
}

preview_validate_credentials() {
	local service value
	local -a targets=("${services[@]}")
	for service in "${targets[@]}"; do
		case $service in
		kisara | kisara-dev)
			[[ -n ${ONEBOT_ACCESS_TOKEN:-} && ${ONEBOT_ACCESS_TOKEN:-} != replace-with-a-secret && ${ONEBOT_ACCESS_TOKEN:-} =~ ^[A-Za-z0-9._~-]+$ ]] || {
				preview_error 'Set ONEBOT_ACCESS_TOKEN to a non-placeholder token using letters, digits, dot, underscore, tilde or hyphen before starting OneBot.'; return 2;
			}
			;;
		telegram-bot-api)
			[[ ${TELEGRAM_API_ID:-} =~ ^[1-9][0-9]*$ && ${TELEGRAM_API_HASH:-} =~ ^[[:xdigit:]]{32}$ ]] || {
				preview_error 'Set TELEGRAM_API_ID and TELEGRAM_API_HASH for the local Bot API server.'; return 2;
			}
			[[ ${TELEGRAM_API_BASE_URL:-https://api.telegram.org} == http://telegram-bot-api:8081 ]] || {
				preview_error 'Local deployment requires TELEGRAM_API_BASE_URL=http://telegram-bot-api:8081.'; return 2;
			}
			;;
		telegram)
			[[ -n ${TELEGRAM_BOT_TOKEN:-} ]] || { preview_error 'Set TELEGRAM_BOT_TOKEN from BotFather before starting Telegram.'; return 2; }
			;;
		official)
			for value in "${OFFICIAL_APP_ID-${AppID-}}" "${OFFICIAL_APP_SECRET-${AppSecret-}}"; do
				[[ -n $value && $value != replace-with-* ]] || { preview_error 'Set OFFICIAL_APP_ID and OFFICIAL_APP_SECRET from the Official platform before starting.'; return 2; }
				done
			;;
		esac
	done
}

preview_prepare() {
	local service image
	for service in "${services[@]}"; do
		case $service in
		napcat) image=${NAPCAT_IMAGE:-mlikiowa/napcat-docker:latest} ;;
		music) image=${KISARA_MUSIC_IMAGE:-moefurina/ncm-api:latest} ;;
		*) image=${preview_images[$service]} ;;
		esac
		if [[ $preview_action == build && $service != napcat && $service != music ]]; then
			preview_capture "Explicit rebuild for $service" preview_compose build "$service" || return $?
		fi
		preview_prepare_image "$service" "$image" || return $?
	done
}

preview_ready_one() {
	local service=$1 id=$2 state
	state=$(timeout 5 "${preview_docker_command[@]}" inspect --format '{{.State.Running}}' "$id" 2>"${preview_tmp}/inspect.log") || return 1
	[[ $state == true ]] || return 1
	case $service in
	telegram-bot-api)
		timeout 6 "${preview_docker_command[@]}" exec "$id" /opt/kisara/telegram-bot-api-probe.sh ready >"${preview_tmp}/probe.log" 2>&1
		;;
	napcat)
		timeout 6 "${preview_docker_command[@]}" exec "$id" python3 -c \
			"$(cat "$REPO_ROOT/deploy/preview-probe.py")" napcat >"${preview_tmp}/probe.log" 2>&1
		;;
	music)
		timeout 6 "${preview_docker_command[@]}" exec "$id" node -e 'fetch("http://127.0.0.1:3000/").then(r=>process.exit(r.ok?0:1),()=>process.exit(1))' >"${preview_tmp}/probe.log" 2>&1
		;;
	*)
		local engine=$service
		case $service in kisara | kisara-dev) engine=onebot ;; esac
		timeout 6 "${preview_docker_command[@]}" exec "$id" python /opt/kisara/preview-probe.py "$engine" >"${preview_tmp}/probe.log" 2>&1
		;;
	esac
}

preview_wait() {
	local service deadline=$((SECONDS + ${KISARA_PREVIEW_TIMEOUT:-90})) ready
	while true; do
		preview_check_log_readers || return 1
		ready=true
		for service in "${!preview_ids[@]}"; do
			if ! preview_ready_one "$service" "${preview_ids[$service]}"; then
				ready=false
				preview_failed_service=$service
				break
			fi
		done
		preview_check_log_readers || return 1
		[[ $ready != true ]] || return 0
		if [[ $preview_action == status || $SECONDS -ge $deadline ]]; then
			if [[ $preview_action == status ]]; then
				preview_warn "Service $preview_failed_service is not ready; following existing bot logs when available. Inspect credentials/login/network/application errors; status does not repair services."
			else
				preview_error "Service $preview_failed_service is not ready; inspect credentials/login/network/application errors. Retry ./kisara.sh preview start $preview_target after correcting the cause, or use preview down $preview_target to remove containers with data retained."
			fi
			if [[ " ${services[*]} " == *' napcat '* ]]; then
				preview_error 'NapCat readiness requires an available WebUI and OneBot socket. Login may need its WebUI/SSH tunnel. Stored login data is retained; resolve the unavailable endpoint before retrying.'
			fi
			return 1
		fi
		sleep 1
	done
}

preview_diagnostics() {
	local service id
	for service in "${!preview_ids[@]}"; do
		id=${preview_ids[$service]}
		preview_owned "$id" "$service" || { preview_error "Skipped $service diagnostics: ownership mismatch/unavailable."; continue; }
		preview_log "Recent bounded diagnostics for $service"
		if timeout 5 "${preview_docker_command[@]}" logs --tail 80 "$id" >"${preview_tmp}/logs.log" 2>&1; then
			preview_redact "${preview_tmp}/logs.log" || preview_error 'Diagnostics suppressed: redaction failure.'
		else
			preview_error "Logs unavailable/timed out for $service; no raw fallback."
		fi
	done
}

preview_cleanup() {
	local original_status=$? service id
	local -a targets=("${services[@]}")
	trap - EXIT INT TERM
	preview_stop_readers
	if [[ $original_status -ne 0 && ${preview_started:-false} == true &&
		! ( ${preview_cancelled:-false} == true && ${preview_logs_started:-false} == true ) ]]; then
		# Capture IDs even when Compose failed after creating a partial group.
		for service in "${targets[@]}"; do
			id=$(preview_find "$service" 2>/dev/null) || continue
			[[ -z $id || $id == *$'\n'* ]] || preview_ids[$service]=$id
		done
		preview_diagnostics || :
	fi
	if [[ -n ${preview_tmp:-} && $preview_tmp == /tmp/kisara-preview.* && -d $preview_tmp ]]; then rm -rf -- "$preview_tmp"; fi
	exit "$original_status"
}

preview_start_group() {
	local service id
	local -a auxiliary=() applications=()
	preview_capture 'Switch selected application mode' lifecycle_switch || return $?
	preview_started=true
	if [[ " ${services[*]} " == *' napcat '* ]]; then
		mkdir -p -- "$REPO_ROOT/data/napcat/config" "$REPO_ROOT/data/napcat/QQ" "$REPO_ROOT/data/kisara/setu"
		chmod 2770 -- "$REPO_ROOT/data/kisara/setu"
	fi
	if [[ " ${services[*]} " == *' telegram '* ]]; then
		mkdir -p -- "$REPO_ROOT/data/kisara/tgsetu"
		chmod 2770 -- "$REPO_ROOT/data/kisara/tgsetu"
	fi
	for service in "${services[@]}"; do
		case $service in
		kisara | kisara-dev | telegram | official) applications+=("$service") ;;
		*) auxiliary+=("$service") ;;
		esac
	done
	if [[ ${#auxiliary[@]} -gt 0 ]]; then
		preview_capture 'Start selected auxiliary services' preview_compose up --detach --no-build "${auxiliary[@]}" || return $?
	fi
	if [[ " ${services[*]} " == *' telegram-bot-api '* ]]; then
		id=$(preview_find telegram-bot-api) || return 1
		[[ -n $id && $id != *$'\n'* ]] && preview_owned "$id" telegram-bot-api || { preview_error 'Unexpected local Bot API repository identity.'; return 1; }
		preview_ids=([telegram-bot-api]="$id")
		preview_wait || return $?
	fi
	if [[ ${#applications[@]} -gt 0 ]]; then
		preview_capture 'Recreate selected applications with current settings' preview_compose up --detach --no-build --force-recreate --no-deps "${applications[@]}" || return $?
	fi
	preview_collect
}

preview_listener_info() {
	local id=$1 service=$2
	case $service in
	telegram-bot-api) timeout 5 "${preview_docker_command[@]}" exec "$id" /opt/kisara/telegram-bot-api-probe.sh listeners 2>"${preview_tmp}/inspect.log" ;;
	napcat)
		timeout 5 "${preview_docker_command[@]}" exec "$id" python3 -c \
			"$(cat "$REPO_ROOT/deploy/preview-probe.py")" listeners 2>"${preview_tmp}/inspect.log"
		;;
	music)
		timeout 5 "${preview_docker_command[@]}" exec "$id" node -e "$(cat "$REPO_ROOT/deploy/preview-listeners.js")" 0 2>"${preview_tmp}/inspect.log"
		;;
	*) timeout 5 "${preview_docker_command[@]}" exec "$id" python /opt/kisara/preview-probe.py listeners 2>"${preview_tmp}/inspect.log" ;;
	esac
}

preview_summary() {
	local service id endpoint port bind address url facts listener_host listener_port protocol
	local container_endpoint container_port mapping_active required_ui required_ws scope
	local -a open=() local_urls=() listeners=() published=() internal=() notes=() candidates=()
	local -a targets=("${services[@]}")
	for service in "${targets[@]}"; do
		id=${preview_ids[$service]}
		facts=$(preview_listener_info "$id" "$service") || { preview_error "Listener inspection unavailable for $service; no success summary is emitted."; return 1; }
		required_ui=false required_ws=false
		while IFS='|' read -r listener_host listener_port; do
			[[ -n $listener_host ]] || continue
			[[ $listener_port =~ ^[0-9]+$ ]] && preview_valid_listener_host "$listener_host" || { preview_error 'Invalid socket inspection result.'; return 1; }
			protocol='TCP; protocol unknown'
			case "$service:$listener_port" in
			napcat:6099) protocol='WebUI HTTP'; required_ui=true ;;
			napcat:3001) protocol='OneBot WebSocket'; required_ws=true ;;
			music:3000 | telegram-bot-api:8081) protocol=HTTP ;;
			esac
			scope=container
			case $listener_host in
			127.* | '[::1]' | '[0:0:0:0:0:0:0:1]') scope='container loopback only' ;;
			esac
			listeners+=("Listening $service: $listener_host:$listener_port ($scope; $protocol)")
			case $listener_host in
			127.* | '[::1]' | '[0:0:0:0:0:0:0:1]') continue ;;
			esac
			case "$service:$listener_port:$listener_host" in
			napcat:3001:0.0.0.0 | 'napcat:3001:[::]' | 'napcat:3001:[0:0:0:0:0:0:0:0]') internal+=('napcat: ws://napcat:3001 (selected Docker network only; authenticated)') ;;
			telegram-bot-api:8081:0.0.0.0) internal+=('telegram-bot-api: http://telegram-bot-api:8081/ (selected Docker network only; token required)') ;;
			music:3000:0.0.0.0 | 'music:3000:[0:0:0:0:0:0:0:0]') internal+=('music: http://music:3000/ (selected Docker network only)') ;;
			*) internal+=("$service: $listener_host:$listener_port (container namespace TCP; route/protocol not verified)") ;;
			esac
		done <<<"$facts"
		if [[ $service == napcat && ( $required_ui != true || $required_ws != true ) ]]; then
			preview_error 'NapCat required UI/OneBot sockets are absent; review data/napcat/config without resetting login data.'; return 1
		fi
		endpoint=$(timeout 5 "${preview_docker_command[@]}" port "$id" 2>"${preview_tmp}/inspect.log") || { preview_error "Cannot inspect actual published mappings for $service."; return 1; }
		if [[ -z $facts && -z $endpoint ]]; then notes+=("$service: outbound bot connection; no inbound application listener or host port."); fi
		while IFS= read -r address; do
			[[ -n $address ]] || continue
			[[ $address == *' -> '* ]] || { preview_error 'Invalid published mapping facts.'; return 1; }
			container_endpoint=${address%% -> *}
			container_port=${container_endpoint%/*}
			address=${address#* -> }
			port=${address##*:} bind=${address%:*}
			mapping_active=false
			while IFS='|' read -r listener_host listener_port; do
				[[ $listener_port == "$container_port" && $container_endpoint == */tcp ]] || continue
				case $listener_host in
				0.0.0.0 | '[::]' | '[0:0:0:0:0:0:0:0]') mapping_active=true ;;
				esac
			done <<<"$facts"
			if [[ $mapping_active != true ]]; then
				published+=("Published $service: $bind:$port -> container:$container_endpoint (listener bind absent, loopback-only or unverified; host access inactive/unverified)")
				notes+=("$service: no browser destination advertised for an inactive or unverified published listener.")
				continue
			fi
			published+=("Published $service: $bind:$port -> container:$container_endpoint (active TCP listener; host reachability unverified)")
			[[ $service == napcat && $container_endpoint == 6099/tcp ]] || continue
			candidates=()
			case $bind in
			0.0.0.0) preview_addresses || return $?; candidates=("${preview_addresses_v4[@]}"); local_urls+=("http://127.0.0.1:$port/") ;;
			'::' | '[::]') preview_addresses || return $?; for url in "${preview_addresses_v6[@]}"; do candidates+=("[$url]"); done; local_urls+=("http://[::1]:$port/"); notes+=('Link-local IPv6 addresses requiring a client-specific zone are omitted; IPv6 mappings do not imply IPv4 publication.') ;;
			127.*) local_urls+=("http://${bind}:$port/") ;;
			'::1' | '[::1]') local_urls+=("http://[::1]:$port/") ;;
			*)
				if [[ $bind == *:* ]]; then candidates+=("[${bind//[\[\]]/}]"); else candidates+=("$bind"); fi
				;;
			esac
			for url in "${candidates[@]}"; do open+=("http://$url:$port/"); done
			if [[ ${#candidates[@]} -eq 0 && ( $bind == 0.0.0.0 || $bind == '::' || $bind == '[::]' ) ]]; then notes+=('No non-loopback host address found.'); fi
		done <<<"$endpoint"
	done
	notes+=('Docker embedded DNS listeners at 127.0.0.11 are runtime infrastructure and excluded.')
	notes+=('Readiness confirms the current adapter lifecycle; feature delivery, ongoing reliability and cross-device reachability remain unverified.')
	if [[ ${#open[@]} -gt 0 ]]; then notes+=('Host addresses are candidates; firewall/routing and other-device access have not been tested.'); fi
	[[ $preview_local_host == true ]] || notes+=('Docker daemon is remote; Local only URLs refer to the preview host, not this caller.')
	preview_message success 1 'System is ready.'
	[[ ${#open[@]} -eq 0 ]] || preview_section Open 'NapCat WebUI (napcat):' "${open[@]}"
	[[ ${#local_urls[@]} -eq 0 ]] || preview_section 'Local only (preview host)' 'NapCat WebUI (napcat):' "${local_urls[@]}"
	preview_section Listeners "${listeners[@]}"
	preview_section Published "${published[@]}"
	preview_section 'Internal only' "${internal[@]}"
	preview_section Notes "${notes[@]}"
}
preview_valid_selection() {
	local selection=$1 profile seen=','
	local -a chosen=()
	[[ -n $selection && $selection != ,* && $selection != *, && $selection != *,,* ]] || {
		preview_error 'Specify a nonempty engine/profile list without empty members.'; return 2;
	}
	IFS=, read -r -a chosen <<<"$selection"
	for profile in "${chosen[@]}"; do
		case $profile in
		onebot | onebot-dev | telegram | official | music) ;;
		*) preview_error "Unknown preview engine/profile: $profile"; return 2 ;;
		esac
		[[ $seen != *",$profile,"* ]] || { preview_error "Duplicate preview engine/profile: $profile"; return 2; }
		seen+="$profile,"
	done
	[[ $seen != *,onebot,* || $seen != *,onebot-dev,* ]] || {
		preview_error 'onebot and onebot-dev cannot own the same QQ state concurrently.'; return 2;
	}
}

preview_run() {
	preview_action=start preview_verbose=false
	local arg action_seen=false target_seen=false service selection explicit_target='' readiness_status
	for arg in "$@"; do
		case $arg in
		--help | -h) preview_usage; return 0 ;;
		--verbose)
			[[ $preview_verbose == false ]] || { preview_error 'Specify --verbose once.'; return 2; }
			preview_verbose=true ;;
		start | up | status | build | down)
			[[ $action_seen == false && $target_seen == false ]] || { preview_error 'Specify one command before the engine/profile list.'; return 2; }
			preview_action=$arg action_seen=true ;;
		-*) preview_error 'Unknown preview option.'; preview_usage; return 2 ;;
		*)
			[[ $target_seen == false ]] || { preview_error 'Specify one engine/profile list.'; return 2; }
			preview_valid_selection "$arg" || return $?
			explicit_target=$arg target_seen=true ;;
		esac
	done
	case $preview_action in up) preview_action=start ;; esac
	[[ -f $REPO_ROOT/.env ]] || { preview_error 'Missing .env; copy .env.example only if absent, then edit the required selected-engine values.'; return 2; }
	DOTENV_KEYS=()
	dotenv_load "$REPO_ROOT/.env" || return $?
	selection=${COMPOSE_PROFILES-onebot}
	if [[ $target_seen == true ]]; then
		selection=$explicit_target
	fi
	services=() profiles=()
	preview_valid_selection "$selection" || return $?
	preview_target=$selection
	select_services "$selection"
	[[ $preview_action != start ]] || preview_validate_credentials || return $?
	if [[ $preview_action == start || $preview_action == status ]]; then
		[[ ${KISARA_PREVIEW_TIMEOUT:-90} =~ ^[1-9][0-9]*$ ]] || { preview_error 'KISARA_PREVIEW_TIMEOUT must be a positive integer.'; return 2; }
	fi
	for arg in docker timeout sed mktemp cat id; do
		command -v "$arg" >/dev/null 2>&1 || { preview_error "Required host command: $arg"; return 127; }
	done
	if [[ $preview_action == start || $preview_action == status ]]; then
		for arg in mkfifo flock stty; do command -v "$arg" >/dev/null 2>&1 || { preview_error "Required host command: $arg"; return 127; }; done
	fi
	preview_tmp=$(mktemp -d /tmp/kisara-preview.XXXXXXXXXX)
	preview_output_lock="${preview_tmp}/output.lock"
	preview_started=false
	preview_logs_started=false preview_cancelled=false
	preview_log_pids=()
	declare -gA preview_ids=() preview_images=() lifecycle_ids=()
	trap preview_cleanup EXIT
	trap 'preview_cancelled=true; exit 130' INT
	trap 'preview_cancelled=true; exit 143' TERM
	preview_endpoint || return $?
	if [[ $preview_action == start && " ${services[*]} " == *' napcat '* && ( ${NAPCAT_WEBUI_BIND:-127.0.0.1} == 0.0.0.0 || ${NAPCAT_WEBUI_BIND:-127.0.0.1} == '::' ) ]]; then preview_addresses || return $?; fi
	# Use host fallback inputs, leaving explicit dotenv UID/GID values intact.
	export KISARA_HOST_UID="$(id -u)" KISARA_HOST_GID="$(id -g)"
	lifecycle_docker_command=("${preview_docker_command[@]}")
	if [[ ${#services[@]} -gt 0 && ( $preview_action == start || $preview_action == build ) ]]; then
		preview_override || return $?
		preview_capture 'Validate selected Compose configuration' preview_compose config --quiet || return $?
	fi
	lifecycle_targets
	lifecycle_preflight "${lifecycle_services[@]}" || return $?
	case $preview_action in
	down)
		for service in "${lifecycle_services[@]}"; do
			preview_capture "Remove selected $service containers (preserve data)" lifecycle_remove "$service" || return $?
		done
		preview_log 'Selected repository containers removed; persistent volumes and data retained.'
		;;
	status)
		preview_collect || return $?
		readiness_status=0
		preview_wait || readiness_status=$?
		if [[ $readiness_status -eq 0 ]]; then preview_summary || return $?; fi
		preview_start_log_readers || return $?
		if [[ $readiness_status -ne 0 && $preview_logs_started != true ]]; then preview_diagnostics; return 1; fi
		preview_wait_log_readers
		;;
	build)
		[[ ${KISARA_PREVIEW_OFFLINE:-false} != true ]] || { preview_error 'Explicit build is disabled by offline mode; disable it only when downloads are permitted.'; return 2; }
		preview_prepare
		;;
	start)
		preview_prepare || return $?
		preview_start_group || return $?
		preview_start_log_readers || return $?
		preview_wait || return 1
		preview_summary || return $?
		preview_started=false
		preview_wait_log_readers
		;;
	esac
}
