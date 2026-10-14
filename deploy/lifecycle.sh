#!/usr/bin/env bash
# Repository-scoped container operations; sourcing performs no runtime work.

lifecycle_error() { printf '[error] %s\n' "$*" >&2; }

lifecycle_find() {
	if [[ $1 == bot ]]; then
		timeout 5 "${lifecycle_docker_command[@]}" ps -aq --filter "label=hako.repo=$REPO_ROOT" --filter label=hako.scope=preview.sh --filter label=hako.service=bot
	else
		timeout 5 "${lifecycle_docker_command[@]}" ps -aq --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME:-kisara}" --filter "label=com.docker.compose.service=$1"
	fi
}

lifecycle_owned() {
	local id=$1 expected=$2 facts project service directory files repo scope tagged entry base=false
	facts=$(timeout 5 "${lifecycle_docker_command[@]}" inspect --format '{{with index .Config.Labels "com.docker.compose.project"}}{{.}}{{end}}|{{with index .Config.Labels "com.docker.compose.service"}}{{.}}{{end}}|{{with index .Config.Labels "com.docker.compose.project.working_dir"}}{{.}}{{end}}|{{with index .Config.Labels "com.docker.compose.project.config_files"}}{{.}}{{end}}|{{with index .Config.Labels "hako.repo"}}{{.}}{{end}}|{{with index .Config.Labels "hako.scope"}}{{.}}{{end}}|{{with index .Config.Labels "hako.service"}}{{.}}{{end}}' "$id" 2>/dev/null) || return 1
	[[ $facts != *$'\n'* && ${facts//[^|]/} == '||||||' ]] || return 1
	IFS='|' read -r project service directory files repo scope tagged <<<"$facts"
	[[ -z $repo || $repo == "$REPO_ROOT" ]] || return 1
	[[ -z $directory || $directory == "${COMPOSE_FILE%/*}" ]] || return 1
	if [[ -n $files ]]; then
		local -a entries=()
		IFS=, read -r -a entries <<<"$files"
		for entry in "${entries[@]}"; do [[ $entry != "$COMPOSE_FILE" ]] || base=true; done
		[[ $base == true ]] || return 1
	fi
	if [[ $expected == bot ]]; then
		[[ -z $project && -z $service && $repo == "$REPO_ROOT" && $scope == preview.sh && $tagged == bot ]] || return 1
		[[ $(timeout 5 "${lifecycle_docker_command[@]}" inspect --format '{{range .Config.Env}}{{if eq . "KISARA_ENGINE=official"}}official{{end}}{{end}}' "$id" 2>/dev/null) == official ]]
		return
	fi
	[[ $project == "${COMPOSE_PROJECT_NAME:-kisara}" && $service == "$expected" ]] || return 1
	# Explicit legacy fields cannot override contradictory source/service identity.
	[[ -z $tagged || $tagged == "$expected" ]] || return 1
	[[ -z $scope || $scope == preview.sh ]] || return 1
	if [[ -n $directory && $base == true ]]; then return 0; fi
	[[ $repo == "$REPO_ROOT" && $scope == preview.sh && $tagged == "$expected" ]]
}

lifecycle_preflight() {
	local service text id
	lifecycle_ids=()
	for service in "$@"; do
		text=$(lifecycle_find "$service") || { lifecycle_error "Cannot inspect selected $service containers."; return 1; }
		[[ $text != *$'\n'* ]] || { lifecycle_error "Duplicate $service containers; inspect their repository identity."; return 2; }
		[[ -n $text ]] || continue
		id=$text
		lifecycle_owned "$id" "$service" || { lifecycle_error "Selected $service container has foreign or unverifiable repository identity; use its originating deployment."; return 2; }
		lifecycle_ids[$service]=$id
	done
}

lifecycle_targets() {
	lifecycle_services=("${services[@]}")
	if [[ " ${services[*]} " == *' napcat '* ]]; then
		[[ " ${services[*]} " == *' kisara '* ]] || lifecycle_services+=(kisara)
		[[ " ${services[*]} " == *' kisara-dev '* ]] || lifecycle_services+=(kisara-dev)
	fi
	[[ " ${services[*]} " != *' official '* ]] || lifecycle_services+=(bot)
}

lifecycle_remove() {
	local service=$1 id=${lifecycle_ids[$1]:-} present
	[[ -n $id ]] || return 0
	lifecycle_owned "$id" "$service" || { lifecycle_error "Cannot remove $service: repository identity changed/unavailable."; return 2; }
	"${lifecycle_docker_command[@]}" stop "$id" || return $?
	# The old Official hako runtime used --rm and disappears on stop.
	present=$(timeout 5 "${lifecycle_docker_command[@]}" ps -aq --filter "id=$id") || return 1
	if [[ -n $present ]]; then
		[[ $present == "$id" ]] && lifecycle_owned "$id" "$service" || { lifecycle_error "Cannot remove stopped $service: repository identity changed/unavailable."; return 2; }
		"${lifecycle_docker_command[@]}" rm "$id" || return $?
	fi
	unset 'lifecycle_ids[$service]'
}

lifecycle_switch() {
	local other=''
	case " ${services[*]} " in
	*' kisara '*) other=kisara-dev ;;
	*' kisara-dev '*) other=kisara ;;
	esac
	[[ -z $other ]] || lifecycle_remove "$other" || return $?
	[[ " ${services[*]} " != *' official '* ]] || lifecycle_remove bot
}

lifecycle_project_preflight() {
	local text id facts service seen=','
	lifecycle_ids=()
	text=$(timeout 5 "${lifecycle_docker_command[@]}" ps -aq --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME:-kisara}") || return 1
	while IFS= read -r id; do
		[[ -n $id ]] || continue
		facts=$(timeout 5 "${lifecycle_docker_command[@]}" inspect --format '{{with index .Config.Labels "com.docker.compose.service"}}{{.}}{{end}}' "$id" 2>/dev/null) || return 1
		service=$facts
		[[ -n $service && $service != '<no value>' && $seen != *",$service,"* ]] && lifecycle_owned "$id" "$service" || {
			lifecycle_error 'Whole-project down refused: foreign, duplicate or unverifiable container identity.'; return 2;
		}
		seen+="$service,"
		lifecycle_ids[$service]=$id
	done <<<"$text"
	text=$(lifecycle_find bot) || return 1
	[[ $text != *$'\n'* ]] || { lifecycle_error 'Duplicate legacy Official containers.'; return 2; }
	if [[ -n $text ]]; then
		lifecycle_owned "$text" bot || { lifecycle_error 'Unverified legacy Official container.'; return 2; }
		lifecycle_ids[bot]=$text
	fi
}
