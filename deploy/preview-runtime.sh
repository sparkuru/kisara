#!/usr/bin/env bash
# Preview operations for the existing engine lifecycle; no top-level effects.

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

preview_redact() {
	local file=$1 line key secret part
	local -a values=() pieces=()
	while IFS= read -r key; do
		case $key in
		KISARA_* | ONEBOT_* | TELEGRAM_* | OFFICIAL_* | NAPCAT_* | AppID | AppSecret | SAUCENAO_API_KEY | TIANAPI_KEY)
			secret=${!key}
			[[ -n $secret ]] || continue
			case $key in
			*TOKEN* | *SECRET* | *KEY* | *PASSWORD* | *ACCOUNT* | *APP_ID* | *USERS* | *GROUPS* | *URL* | AppID | AppSecret)
				values+=("$secret")
				IFS=, read -r -a pieces <<<"$secret"
				for part in "${pieces[@]}"; do [[ -z $part ]] || values+=("$part"); done
				;;
			esac
			;;
		esac
	done < <(compgen -e)
	: >"${preview_tmp}/safe.log"
	while IFS= read -r line || [[ -n $line ]]; do
		for secret in "${values[@]}"; do line=${line//"$secret"/[redacted]}; done
		printf '%s\n' "$line"
	done <"$file" | sed -E \
		-e 's#(https?|wss?)://[^ /]+@[^ ]+#\1://[redacted]#g' \
		-e 's#[Bb]earer[[:space:]]+[^[:space:]"\x27,;]+#Bearer [redacted]#g' \
		-e 's#(https?://api.telegram.org/bot)[^/[:space:]]+#\1[redacted]#g' \
		-e 's#([?&](token|access_token|secret|password|key|code)=)[^&[:space:]]+#\1[redacted]#Ig' \
		-e 's#((user|chat|account|app|guild|channel)([_ ]?id)?[=: ]+)[^[:space:],;]+#\1[private-id]#Ig' \
		-e 's#(Official bot is ready:).*#\1 [private-name]#g' \
		-e '/(Received|Replying|No reply).*message user=/d' \
		-e 's/[0-9]{5,}/[private-id]/g' \
		-e '/[▀▄█]/d' \
		-e 's/[[:cntrl:]]//g' >"${preview_tmp}/safe.log" || return 1
	cat -- "${preview_tmp}/safe.log" >&2
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

preview_fingerprint() {
	local key
	{
		printf '%s\0' "${profiles[@]}" "${services[@]}" "$preview_official" "$(id -u)" "$(id -g)"
		while IFS= read -r key; do
			case $key in
			KISARA_* | ONEBOT_* | TELEGRAM_* | OFFICIAL_* | NAPCAT_* | COMPOSE_* | HAKO_IMAGE | DOCKER_* | AppID | AppSecret | SAUCENAO_API_KEY | TIANAPI_KEY)
				printf '%s\0%s\0' "$key" "${!key}" ;;
			esac
		done < <(compgen -e | LC_ALL=C sort)
		for key in "${REPO_ROOT}/deploy/compose.yaml" "${REPO_ROOT}/deploy/Dockerfile" "${REPO_ROOT}/pyproject.toml" "${REPO_ROOT}/deploy/preview-constraints-py312.txt"; do
			cat -- "$key" 2>"${preview_tmp}/inspect.log" || {
				preview_error "Required fingerprint input ${key##*/} is missing/unreadable; restore it before preview preparation."; return 1;
			}
		done
		while IFS= read -r -d '' key; do sha256sum -- "$key"; done < <(find "${REPO_ROOT}/config" -type f \( -name '*.toml' -o -name '*.json' \) -print0 2>/dev/null | sort -z)
	} | sha256sum | awk '{print $1}'
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
		printf '  %s:\n    labels:\n      hako.repo: %s\n      hako.scope: preview.sh\n      hako.service: %s\n      hako.config: %s\n      hako.attempt: %s\n' \
			"$service" "\"${REPO_ROOT//\"/\\\"}\"" "$service" "$preview_config" "${preview_tmp##*/}" >>"${preview_tmp}/override.yaml"
		case $service in
		kisara | kisara-dev | telegram | official)
			image="${KISARA_PREVIEW_IMAGE_PREFIX:-${COMPOSE_PROJECT_NAME:-kisara}-preview}-${service}:latest"
			[[ $image =~ ^[a-zA-Z0-9][a-zA-Z0-9._/:-]+$ ]] || { preview_error 'Invalid KISARA_PREVIEW_IMAGE_PREFIX.'; return 2; }
			preview_images[$service]=$image
			printf '    image: %s\n    environment:\n      KISARA_PREVIEW_READINESS: /tmp/kisara-preview-ready.json\n' "$image" >>"${preview_tmp}/override.yaml"
			;;
		esac
	done
}

preview_find() {
	local service=$1
	if [[ $service == bot ]]; then
		timeout 5 "${preview_docker_command[@]}" ps -aq --filter "label=hako.repo=${REPO_ROOT}" --filter label=hako.scope=preview.sh --filter label=hako.service=bot
	else
		timeout 5 "${preview_docker_command[@]}" ps -aq --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME:-kisara}" --filter "label=com.docker.compose.service=$service"
	fi
}

preview_owned() {
	local id=$1 service=$2 facts
	facts=$(timeout 5 "${preview_docker_command[@]}" inspect --format '{{index .Config.Labels "hako.repo"}}|{{index .Config.Labels "hako.scope"}}|{{index .Config.Labels "hako.service"}}' "$id" 2>"${preview_tmp}/inspect.log") || return 1
	[[ $facts == "${REPO_ROOT}|preview.sh|${service}" ]]
}

preview_existing() {
	local service id text count=0 found=0 fingerprint other
	preview_ids=()
	local -a targets=("${services[@]}")
	[[ $preview_official != true ]] || targets+=(bot)
	# Sharing the same QQ login/state concurrently would violate the existing lifecycle.
	for service in "${services[@]}"; do
		[[ $preview_action != stop ]] || break
		case $service in
		kisara) other=kisara-dev ;;
		kisara-dev) other=kisara ;;
		*) continue ;;
		esac
		text=$(preview_find "$other" 2>"${preview_tmp}/inspect.log") || return 1
		[[ -z $text ]] || { preview_error "Conflicting $other group exists; stop it explicitly before changing the OneBot mode."; return 2; }
	done
	for service in "${targets[@]}"; do
		text=$(preview_find "$service" 2>"${preview_tmp}/inspect.log") || { preview_error 'Cannot inspect selected services.'; return 1; }
		count=0
		while IFS= read -r id; do
			[[ -n $id ]] || continue
			count=$((count + 1))
			preview_owned "$id" "$service" || { preview_error "Selected $service container is not owned by preview; use its existing deployment lifecycle explicitly."; return 2; }
			fingerprint=$(preview_docker inspect --format '{{index .Config.Labels "hako.config"}}' "$id" 2>"${preview_tmp}/inspect.log") || return 1
			if [[ $fingerprint != "$preview_config" && $preview_action != stop ]]; then
				preview_error "Configuration changed for $service. Run ./preview.sh stop, then ./preview.sh start (build first for source/dependency changes)."; return 2
			fi
			preview_ids[$service]=$id
		done <<<"$text"
		[[ $count -le 1 ]] || { preview_error "Duplicate $service containers; inspect and recover explicitly."; return 2; }
		[[ $count -eq 0 ]] || found=$((found + 1))
	done
	if [[ $preview_action != stop && $found -gt 0 && $found -ne ${#targets[@]} ]]; then
		preview_error 'Incomplete preview group; run ./preview.sh stop then start. No automatic repair was performed.'; return 2
	fi
	preview_reuse=false
	[[ $found -eq 0 ]] || preview_reuse=true
}

preview_prepare_image() {
	local service=$1 image=$2 extra=''
	case $service in telegram | official) extra=$service ;; esac
	if ! preview_docker image inspect "$image" >"${preview_tmp}/inspect.log" 2>&1; then
		[[ ${KISARA_PREVIEW_OFFLINE:-false} != true ]] || { preview_error "Missing image for $service; disable offline mode and run build/pull explicitly."; return 1; }
		case $service in
		napcat | music) preview_capture "Pull missing $service image" preview_docker pull "$image" || return $? ;;
		*) preview_capture "Build missing $service image" preview_compose build "$service" || return $? ;;
		esac
	fi
	case $service in napcat | music) return 0 ;; esac
	if ! preview_docker run --rm --network none --entrypoint python "$image" /opt/kisara/preview-deps.py check "$extra" >"${preview_tmp}/inspect.log" 2>&1; then
		[[ ${KISARA_PREVIEW_OFFLINE:-false} != true ]] || { preview_error "Missing/incompatible pinned dependencies for $service; rebuild explicitly while online."; return 1; }
		preview_capture "Prepare pinned $service dependencies through its image build" preview_compose build "$service" || return $?
		preview_docker run --rm --network none --entrypoint python "$image" /opt/kisara/preview-deps.py check "$extra" >"${preview_tmp}/inspect.log" 2>&1 || {
			preview_error "Dependencies still unavailable for $service after preparation; no services started."; return 1;
		}
	fi
}

preview_hako() {
	HAKO_IMAGE="${HAKO_IMAGE:-python:3.12-slim}" "$REPO_ROOT/hako" "$@"
}

preview_validate_credentials() {
	local service value
	local -a targets=("${services[@]}")
	[[ $preview_official != true ]] || targets+=(official)
	for service in "${targets[@]}"; do
		case $service in
		kisara | kisara-dev)
			[[ -n ${ONEBOT_ACCESS_TOKEN:-} && ${ONEBOT_ACCESS_TOKEN:-} != replace-with-a-secret && ${ONEBOT_ACCESS_TOKEN:-} =~ ^[A-Za-z0-9._~-]+$ ]] || {
				preview_error 'Set ONEBOT_ACCESS_TOKEN to a non-placeholder token using letters, digits, dot, underscore, tilde or hyphen before starting OneBot.'; return 2;
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
	[[ $preview_official == true ]] || return 0
	image=${HAKO_IMAGE:-python:3.12-slim}
	if ! preview_docker image inspect "$image" >"${preview_tmp}/inspect.log" 2>&1; then
		[[ ${KISARA_PREVIEW_OFFLINE:-false} != true ]] || { preview_error 'Missing hako image in offline mode.'; return 1; }
		preview_capture 'Pull missing hako runtime image' preview_docker pull "$image" || return $?
	fi
	if ! HAKO_SERVICE= HAKO_DETACH=false preview_hako python /app/deploy/preview-deps.py check official >"${preview_tmp}/inspect.log" 2>&1; then
		[[ ${KISARA_PREVIEW_OFFLINE:-false} != true ]] || { preview_error 'Missing pinned Official dependencies in offline mode; run build while online.'; return 1; }
		preview_capture 'Install missing pinned Official runtime dependencies' env HAKO_SERVICE= HAKO_DETACH=false "$REPO_ROOT/hako" python /app/deploy/preview-deps.py install official || return $?
		HAKO_SERVICE= HAKO_DETACH=false preview_hako python /app/deploy/preview-deps.py check official >"${preview_tmp}/inspect.log" 2>&1 || {
			preview_error 'Official dependencies remain unavailable after installation; no service started.'; return 1;
		}
	fi
}

preview_ready_one() {
	local service=$1 id=$2 state
	state=$(timeout 5 "${preview_docker_command[@]}" inspect --format '{{.State.Running}}' "$id" 2>"${preview_tmp}/inspect.log") || return 1
	[[ $state == true ]] || return 1
	case $service in
	napcat)
		timeout 6 "${preview_docker_command[@]}" exec "$id" node -e \
			'Promise.all([fetch("http://127.0.0.1:6099").then(r=>{if(!r.ok)throw Error("UI unavailable")}),new Promise((resolve,reject)=>{let s=require("net").connect(3001,"127.0.0.1",()=>{s.end();resolve()});s.on("error",reject)})]).then(()=>process.exit(0),()=>process.exit(1))' >"${preview_tmp}/probe.log" 2>&1
		;;
	music)
		timeout 6 "${preview_docker_command[@]}" exec "$id" node -e 'fetch("http://127.0.0.1:3000/").then(r=>process.exit(r.ok?0:1),()=>process.exit(1))' >"${preview_tmp}/probe.log" 2>&1
		;;
	bot)
		timeout 6 "${preview_docker_command[@]}" exec "$id" python /app/deploy/preview-probe.py official >"${preview_tmp}/probe.log" 2>&1
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
		ready=true
		for service in "${!preview_ids[@]}"; do
			if ! preview_ready_one "$service" "${preview_ids[$service]}"; then
				ready=false
				preview_failed_service=$service
				break
			fi
		done
		[[ $ready != true ]] || return 0
		if [[ $preview_action == status || $SECONDS -ge $deadline || $preview_reuse == true ]]; then
			preview_error "Service $preview_failed_service is not ready; inspect credentials/login/network/application errors. Run stop then start for explicit recovery."
			if [[ " ${services[*]} " == *' napcat '* ]]; then
				preview_error 'NapCat login must be prepared via its WebUI/SSH tunnel within the configured timeout. Stored login data is retained; retry after preparation or increase KISARA_PREVIEW_TIMEOUT.'
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
	[[ ${preview_official:-false} != true ]] || targets+=(bot)
	trap - EXIT INT TERM
	if [[ $original_status -ne 0 && ${preview_started:-false} == true ]]; then
		# Capture IDs even when Compose failed after creating a partial group.
		for service in "${targets[@]}"; do
			id=$(preview_find "$service" 2>/dev/null) || continue
			[[ -z $id || $id == *$'\n'* ]] || preview_ids[$service]=$id
			done
		preview_diagnostics || :
		for service in "${!preview_ids[@]}"; do
			id=${preview_ids[$service]}
			preview_owned "$id" "$service" || continue
			[[ $(preview_docker inspect --format '{{index .Config.Labels "hako.attempt"}}' "$id" 2>/dev/null) == "${preview_tmp##*/}" ]] || continue
			preview_docker rm --force "$id" >"${preview_tmp}/cleanup.log" 2>&1 || preview_error "Cleanup failed for newly created $service; recover explicitly."
			done
	fi
	if [[ -n ${preview_tmp:-} && $preview_tmp == /tmp/kisara-preview.* && -d $preview_tmp ]]; then rm -rf -- "$preview_tmp"; fi
	exit "$original_status"
}

preview_start_group() {
	local service id
	preview_started=true
	if [[ ${#services[@]} -gt 0 ]]; then
		if [[ " ${services[*]} " == *' napcat '* ]]; then
			mkdir -p -- "$REPO_ROOT/data/napcat/config" "$REPO_ROOT/data/napcat/QQ" "$REPO_ROOT/data/kisara/setu"
			chmod 2770 -- "$REPO_ROOT/data/kisara/setu"
		fi
		preview_capture 'Start selected services in background' preview_compose up --detach --no-build --no-recreate "${services[@]}" || return $?
		for service in "${services[@]}"; do
			id=$(preview_find "$service" 2>"${preview_tmp}/inspect.log") || return 1
			[[ -n $id && $id != *$'\n'* ]] || { preview_error "Expected exactly one $service container after startup."; return 1; }
			preview_owned "$id" "$service" || { preview_error "Unexpected $service ownership after startup."; return 1; }
			preview_ids[$service]=$id
		done
	fi
	if [[ $preview_official == true ]]; then
		preview_capture 'Start Official in background through hako' env HAKO_SCOPE=preview.sh HAKO_SERVICE=bot HAKO_DETACH=true \
			HAKO_CONFIG="$preview_config" HAKO_ATTEMPT="${preview_tmp##*/}" KISARA_ENGINE=official KISARA_PREVIEW_READINESS=/tmp/kisara-preview-ready.json \
			"$REPO_ROOT/hako" python -m kisara || return $?
		id=$(preview_find bot 2>"${preview_tmp}/inspect.log") || return 1
		[[ -n $id && $id != *$'\n'* ]] || return 1
		preview_ids[bot]=$id
	fi
}

preview_listener_info() {
	local id=$1 service=$2
	case $service in
	napcat | music)
		timeout 5 "${preview_docker_command[@]}" exec "$id" node -e "$(cat "$REPO_ROOT/deploy/preview-listeners.js")" 0 2>"${preview_tmp}/inspect.log"
		;;
	bot) timeout 5 "${preview_docker_command[@]}" exec "$id" python /app/deploy/preview-probe.py listeners 2>"${preview_tmp}/inspect.log" ;;
	*) timeout 5 "${preview_docker_command[@]}" exec "$id" python /opt/kisara/preview-probe.py listeners 2>"${preview_tmp}/inspect.log" ;;
	esac
}

preview_summary() {
	local service id endpoint port bind address url facts listener_host listener_port protocol
	local container_endpoint container_port mapping_active required_ui required_ws scope
	local -a open=() local_urls=() listeners=() published=() internal=() notes=() candidates=()
	local -a targets=("${services[@]}")
	[[ $preview_official != true ]] || targets+=(bot)
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
			music:3000) protocol=HTTP ;;
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
			napcat:3001:0.0.0.0 | 'napcat:3001:[0:0:0:0:0:0:0:0]') internal+=('napcat: ws://napcat:3001 (selected Docker network only; authenticated)') ;;
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
preview_run() {
	preview_action=start preview_verbose=false
	local arg action_seen=false service id engine selection
	for arg in "$@"; do
		case $arg in
		--help | -h) preview_usage; return 0 ;;
		--verbose) preview_verbose=true ;;
		start | up | status | build | stop | down)
			[[ $action_seen == false ]] || { preview_error 'Specify one command.'; return 2; }
			preview_action=$arg action_seen=true ;;
		*) preview_error 'Unknown preview argument.'; preview_usage; return 2 ;;
		esac
	done
	case $preview_action in up) preview_action=start ;; down) preview_action=stop ;; esac
	[[ -f $REPO_ROOT/.env ]] || { preview_error 'Missing .env; copy .env.example only if absent, then edit the required selected-engine values.'; return 2; }
	DOTENV_KEYS=()
	dotenv_load "$REPO_ROOT/.env" || return $?
	preview_official=false
	engine=${KISARA_ENGINE-selected}
	selection=${COMPOSE_PROFILES-onebot}
	case $engine in
	onebot | onebot-dev | telegram) selection=$engine ;;
	official) preview_official=true; selection='' ;;
	selected) ;;
	*) preview_error 'Invalid/empty KISARA_ENGINE selection.'; return 2 ;;
	esac
	services=() profiles=()
	[[ -z $selection && $preview_official == true ]] || select_services "$selection"
	[[ $preview_action != start ]] || preview_validate_credentials || return $?
	[[ ${KISARA_PREVIEW_TIMEOUT:-90} =~ ^[1-9][0-9]*$ ]] || { preview_error 'KISARA_PREVIEW_TIMEOUT must be a positive integer.'; return 2; }
	for arg in docker timeout sha256sum sed awk sort find mktemp cat id; do
		command -v "$arg" >/dev/null 2>&1 || { preview_error "Required host command: $arg"; return 127; }
	done
	preview_tmp=$(mktemp -d /tmp/kisara-preview.XXXXXXXXXX)
	preview_started=false
	declare -gA preview_ids=() preview_images=()
	trap preview_cleanup EXIT
	trap 'exit 130' INT
	trap 'exit 143' TERM
	preview_endpoint || return $?
	if [[ $preview_action == start && " ${services[*]} " == *' napcat '* && ( ${NAPCAT_WEBUI_BIND:-127.0.0.1} == 0.0.0.0 || ${NAPCAT_WEBUI_BIND:-127.0.0.1} == '::' ) ]]; then preview_addresses || return $?; fi
	# Use host fallback inputs, leaving explicit dotenv UID/GID values intact.
	export KISARA_HOST_UID="$(id -u)" KISARA_HOST_GID="$(id -g)"
	preview_config=$(preview_fingerprint) || return 1
	preview_override || return $?
	if [[ ${#services[@]} -gt 0 && ( $preview_action == start || $preview_action == build ) ]]; then
		preview_capture 'Validate selected Compose configuration' preview_compose config --quiet || return $?
	fi
	preview_existing || return $?
	case $preview_action in
	stop)
		for service in "${!preview_ids[@]}"; do
			id=${preview_ids[$service]}
			preview_capture "Stop owned $service" preview_docker stop "$id" || return $?
			preview_capture "Remove stopped $service container (preserve data)" preview_docker rm "$id" || return $?
			done
		preview_log 'Selected preview containers stopped; persistent volumes and data retained.'
		;;
	status)
		[[ $preview_reuse == true ]] || { preview_error 'Selected preview group is absent; no resources were prepared.'; return 1; }
		preview_wait || { preview_diagnostics; return 1; }
		preview_summary
		;;
	build)
		[[ $preview_reuse == false ]] || { preview_error 'Stop the selected preview before rebuilding; no running resources changed.'; return 2; }
		[[ ${KISARA_PREVIEW_OFFLINE:-false} != true ]] || { preview_error 'Explicit build is disabled by offline mode; disable it only when downloads are permitted.'; return 2; }
		preview_prepare
		;;
	start)
		if [[ $preview_reuse == false ]]; then
			preview_prepare || return $?
			preview_start_group || return $?
		else
			preview_log 'Reuse the matching existing preview group.'
		fi
		preview_wait || { [[ $preview_started == true ]] || preview_diagnostics; return 1; }
		preview_summary || return $?
		preview_started=false
		;;
	esac
}
