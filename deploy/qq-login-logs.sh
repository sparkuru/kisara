#!/usr/bin/env bash
# Shared login-aware consumer for existing QQ log views; sourcing has no effects.

qq_login_hint() {
	preview_write 1 "onebot | QQ login QR unavailable ($1); use the NapCat WebUI /webui through the configured loopback address or SSH tunnel."
}

qq_login_timestamp_valid() {
	[[ $1 =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,9})?Z$ ]]
}

qq_login_snapshot() {
	local id=$1 line stamp
	qq_snapshot="${preview_tmp}/napcat.snapshot"
	qq_boundary='' qq_boundary_count=0
	preview_owned "$id" napcat || { preview_error 'Cannot read QQ login logs: ownership mismatch.'; return 1; }
	qq_boundary=$(timeout 5 "${preview_docker_command[@]}" exec "$id" python3 -c \
		'import datetime; print(datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"))' 2>"${preview_tmp}/qr-error") || return 1
	[[ $qq_boundary =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T.*Z$ ]] || { preview_error 'Cannot establish a bounded QQ log snapshot.'; return 1; }
	if ! timeout 5 "${preview_docker_command[@]}" logs --timestamps --tail "${qq_log_tail:-80}" "$id" >"${preview_tmp}/napcat.history" 2>&1; then
		preview_error 'QQ recent logs unavailable; no raw fallback.'; return 1
	fi
	preview_replace_secrets true <"${preview_tmp}/napcat.history" | preview_filter_logs >"$qq_snapshot" || return 1
	while IFS= read -r line; do
		stamp=${line%% *}
		[[ $stamp =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T.*Z$ ]] && qq_boundary=$stamp
	done <"${preview_tmp}/napcat.history"
	[[ -n $qq_boundary ]] || return 0
	while IFS= read -r line; do
		[[ ${line%% *} != "$qq_boundary" ]] || qq_boundary_count=$((qq_boundary_count + 1))
	done <"$qq_snapshot"
}

qq_login_png_reader_source() {
	cat <<'PY'
import datetime, os, re, stat, sys
try:
    event = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.([0-9]{1,9}))?Z", sys.argv[1])
    if event is None:
        sys.exit(5)
    seconds = datetime.datetime.fromisoformat(event[1] + "+00:00").timestamp()
    event_ns = int(seconds) * 1000000000 + int((event[2] or "0").ljust(9, "0"))
except (ValueError, OverflowError):
    sys.exit(5)
try:
    fd = os.open("/app/napcat/cache/qrcode.png", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        facts = os.fstat(stream.fileno())
        if not stat.S_ISREG(facts.st_mode) or not 0 < facts.st_size <= 1048576:
            sys.exit(3)
        if facts.st_mtime_ns > event_ns + 1000 or event_ns - facts.st_mtime_ns > 2000000000:
            sys.exit(4)
        data = stream.read(1048577)
        if len(data) != facts.st_size or os.fstat(stream.fileno()).st_mtime_ns != facts.st_mtime_ns:
            sys.exit(4)
        sys.stdout.buffer.write(data)
except FileNotFoundError:
    sys.exit(2)
except PermissionError:
    sys.exit(6)
except OSError:
    sys.exit(7)
PY
}

qq_login_render() {
	local napcat_id=${preview_ids[napcat]:-} app_id='' app_service='' service dimensions columns rows tty_fd mode=plain digest line block='' status=0
	[[ $qq_pending == true ]] || return 0
	if [[ ! -t 1 || ${TERM:-} == dumb ]]; then
		qq_login_hint terminal-output-required; return 0
	fi
	[[ -n $qq_saved_stamp ]] || { qq_login_hint event-timestamp-unavailable; return 0; }
	for service in kisara kisara-dev; do
		if [[ -n ${preview_ids[$service]:-} ]] && [[ $(timeout 5 "${preview_docker_command[@]}" inspect --format '{{.State.Running}}' "${preview_ids[$service]}" 2>"${preview_tmp}/qr-error") == true ]]; then
			app_service=$service app_id=${preview_ids[$service]}; break
		fi
	done
	if [[ -z $app_id ]]; then qq_login_hint application-runtime-unavailable; return 0; fi
	preview_owned "$napcat_id" napcat && preview_owned "$app_id" "$app_service" || {
		preview_error 'Cannot display QQ login QR: ownership mismatch.'; return 1;
	}
	if qq_login_command timeout 5 "${preview_docker_command[@]}" exec "$napcat_id" python3 -c "$(qq_login_png_reader_source)" "$qq_saved_stamp" \
		>"${preview_tmp}/qq-login.png" 2>"${preview_tmp}/qr-error"; then :; else
		status=$?
		case $status in
		2) qq_login_hint png-unavailable ;;
		3) qq_login_hint png-size-or-type ;;
		4) qq_login_hint stale-png ;;
		5) qq_login_hint event-timestamp-invalid ;;
		6) qq_login_hint png-permission-denied ;;
		124 | 137) qq_login_hint png-read-timeout ;;
		*) qq_login_hint png-read-failed ;;
		esac
		return 0
	fi
	exec {tty_fd}<&1
	dimensions=$(stty size <&"$tty_fd" 2>/dev/null) || dimensions='24 80'
	exec {tty_fd}<&-
	read -r rows columns <<<"$dimensions"
	[[ $rows =~ ^[1-9][0-9]*$ && $columns =~ ^[1-9][0-9]*$ ]] || { rows=24; columns=80; }
	[[ -v NO_COLOR ]] || mode=color
	if ! qq_login_command timeout 5 "${preview_docker_command[@]}" exec -i "$app_id" python -c "$(cat "$REPO_ROOT/deploy/qq-login-png.py")" "$columns" "$((rows - 2))" "$mode" \
		<"${preview_tmp}/qq-login.png" >"${preview_tmp}/qq-login.block" 2>"${preview_tmp}/qr-error"; then
		qq_login_hint png-render-or-terminal-size; return 0
	fi
	{
		IFS= read -r digest
		while IFS= read -r line || [[ -n $line ]]; do block+="$line"$'\n'; done
	} <"${preview_tmp}/qq-login.block"
	[[ $digest =~ ^[a-f0-9]{64}$ && -n $block ]] || { qq_login_hint png-render-failed; return 0; }
	[[ $digest != "$qq_last_digest" ]] || return 0
	qq_last_digest=$digest
	block=${block%$'\n'}
	preview_write 1 $'onebot | Scan this QR with mobile QQ and authorize login:\n'"$block"
}

qq_login_command() {
	local command_pid status=0
	"$@" <&0 &
	command_pid=$!
	trap 'kill -TERM "$command_pid" 2>/dev/null || :; wait "$command_pid" 2>/dev/null || :; exit 143' TERM
	trap 'kill -TERM "$command_pid" 2>/dev/null || :; wait "$command_pid" 2>/dev/null || :; exit 130' INT
	wait "$command_pid" || status=$?
	trap - TERM INT
	return "$status"
}

qq_login_event() {
	local text=$1 pattern='^[0-9]{2}-[0-9]{2}[[:space:]]+[0-9]{2}:[0-9]{2}:[0-9]{2}[[:space:]]+\[(warn|info|log|error)\][[:space:]]+(.+)$' body
	qq_new_saved=false
	[[ $text =~ $pattern ]] || return 0
	body=${BASH_REMATCH[2]}
	body=${body#* | }
	case $body in
	"$qq_prompt") qq_pending=true qq_saved_stamp='' ;;
	"$qq_saved /app/napcat/cache/qrcode.png")
		qq_pending=true qq_saved_stamp=$qq_stamp qq_new_saved=true ;;
	'[Core] [Login] '*"$qq_scanned"* | '[Core] [Login] '*"$qq_expired"* | '[NapCat] '*"$qq_success"* | '[Core] [Login] Login Error'*)
		qq_pending=false qq_saved_stamp='' qq_last_digest='' ;;
	esac
}

qq_login_log_lines() {
	local service=$1 snapshot=${2:-} boundary=${3:-} skip=${4:-0} line text platform qq_stamp=''
	local qq_pending=false qq_saved_stamp='' qq_last_digest='' qq_new_saved=false
	local qq_prompt=$'\xE8\xAF\xB7\xE6\x89\xAB\xE6\x8F\x8F\xE4\xB8\x8B\xE9\x9D\xA2\xE7\x9A\x84\xE4\xBA\x8C\xE7\xBB\xB4\xE7\xA0\x81\xEF\xBC\x8C\xE7\x84\xB6\xE5\x90\x8E\xE5\x9C\xA8\xE6\x89\x8BQ\xE4\xB8\x8A\xE6\x8E\x88\xE6\x9D\x83\xE7\x99\xBB\xE5\xBD\x95\xEF\xBC\x9A'
	local qq_saved=$'\xE4\xBA\x8C\xE7\xBB\xB4\xE7\xA0\x81\xE5\xB7\xB2\xE4\xBF\x9D\xE5\xAD\x98\xE5\x88\xB0' qq_scanned=$'\xE4\xBA\x8C\xE7\xBB\xB4\xE7\xA0\x81\xE5\xB7\xB2\xE8\xA2\xAB\xE6\x89\xAB\xE6\x8F\x8F'
	local qq_expired=$'\xE4\xBA\x8C\xE7\xBB\xB4\xE7\xA0\x81\xE5\xB7\xB2\xE8\xBF\x87\xE6\x9C\x9F' qq_success=$'\xE7\x99\xBB\xE5\xBD\x95\xE6\x88\x90\xE5\x8A\x9F'
	platform=$(preview_platform "$service")
	if [[ -n $snapshot ]]; then
		while IFS= read -r line || [[ -n $line ]]; do
			qq_login_record "$line" "$service" "$platform" || return $?
		done <"$snapshot"
		qq_login_render || return $?
	fi
	while IFS= read -r line || [[ -n $line ]]; do
		if [[ -n $boundary && ${line%% *} == "$boundary" && $skip -gt 0 ]]; then skip=$((skip - 1)); continue; fi
		qq_login_record "$line" "$service" "$platform" || return $?
		if [[ $service == napcat && $qq_new_saved == true ]]; then qq_login_render || return $?; fi
	done
}

qq_login_record() {
	local line=$1 service=$2 platform=$3 text=$1
	qq_stamp=''
	if qq_login_timestamp_valid "${line%% *}"; then
		qq_stamp=${line%% *}; text=${line#* }
	fi
	if [[ $service == napcat ]]; then qq_login_event "$text"; fi
	preview_write 1 "$platform | $text"
}

qq_login_attached_logs() {
	local service id
	source "$REPO_ROOT/deploy/preview-console.sh"
	source "$REPO_ROOT/deploy/preview-runtime.sh"
	qq_log_tail=${KISARA_LOG_TAIL:-100}
	[[ $qq_log_tail =~ ^[0-9]+$ ]] || { preview_error 'KISARA_LOG_TAIL must be a nonnegative integer.'; return 2; }
	for service in sed mktemp cat mkfifo flock stty; do command -v "$service" >/dev/null 2>&1 || { preview_error "Required host command: $service"; return 127; }; done
	preview_tmp=$(mktemp -d /tmp/kisara-preview.XXXXXXXXXX)
	preview_output_lock="${preview_tmp}/output.lock"
	preview_log_pids=() preview_started=false preview_logs_started=false preview_cancelled=false
	preview_docker_command=("${lifecycle_docker_command[@]}")
	declare -gA preview_ids=()
	for service in "${diagnostic_services[@]}"; do
		id=${lifecycle_ids[$service]:-}
		[[ -z $id ]] || preview_ids[$service]=$id
	done
	services=("${!preview_ids[@]}")
	qq_follow_auxiliary=true
	trap preview_cleanup EXIT
	trap 'preview_cancelled=true; exit 130' INT
	trap 'preview_cancelled=true; exit 143' TERM
	preview_start_log_readers || return $?
	preview_wait_log_readers
}
