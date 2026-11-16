#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SOURCE_DIR="${SCRIPT_DIR}/repo"
readonly DEFAULT_IMAGE='kisara/napcat:local'
readonly DEFAULT_BUILDER_IMAGE='node:22.22.0-bookworm'
readonly DEFAULT_RUNTIME_IMAGE='mlikiowa/napcat-docker:latest'
readonly SEMVER_PATTERN='^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-((0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)(\.(0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*))?(\+([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?$'

usage() {
	cat <<'EOF'
Usage: ./docker/napcat/build.sh [--help]

Build a local NapCat image from docker/napcat/repo. Builder and runtime
images must already exist locally; this script does not pull them.

Environment:
  NAPCAT_BUILD_IMAGE          Result image (default: kisara/napcat:local)
  NAPCAT_BUILDER_IMAGE        Local Node build image
  NAPCAT_RUNTIME_IMAGE        Local NapCat/QQ runtime image
  NAPCAT_BUILD_VERSION        Version embedded in NapCat (default: git describe)
EOF
}

die() {
	printf 'Error: %s\n' "$*" >&2
	exit 1
}

main() {
	if [[ ${1:-} == '--help' || ${1:-} == '-h' ]]; then
		[[ $# -eq 1 ]] || die '--help does not accept additional arguments'
		usage
		return 0
	fi
	[[ $# -eq 0 ]] || die 'unexpected argument; use --help for usage'
	command -v git >/dev/null 2>&1 || die 'git is required'
	command -v docker >/dev/null 2>&1 || die 'docker is required'
	[[ -f "${SOURCE_DIR}/pnpm-lock.yaml" ]] || die "NapCat source not found at ${SOURCE_DIR}"
	[[ -e "${SOURCE_DIR}/.git" ]] || die 'NapCat source must be a Git checkout'
	git -C "$SOURCE_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die 'NapCat source must be a Git checkout'

	local image=${NAPCAT_BUILD_IMAGE:-$DEFAULT_IMAGE}
	local builder_image=${NAPCAT_BUILDER_IMAGE:-$DEFAULT_BUILDER_IMAGE}
	local runtime_image=${NAPCAT_RUNTIME_IMAGE:-$DEFAULT_RUNTIME_IMAGE}
	local version=${NAPCAT_BUILD_VERSION:-}
	local revision source_state=clean
	revision=$(git -C "$SOURCE_DIR" rev-parse HEAD)
	if [[ -n $(git -C "$SOURCE_DIR" status --porcelain --untracked-files=normal) ]]; then
		source_state=dirty
	fi
	if [[ -z $version ]]; then
		version=$(git -C "$SOURCE_DIR" describe --tags --match 'v[0-9]*' --dirty) || \
			die 'cannot determine a version; set NAPCAT_BUILD_VERSION'
	fi
	[[ $version =~ $SEMVER_PATTERN ]] || \
		die 'NAPCAT_BUILD_VERSION must be a semantic version'

	docker image inspect "$builder_image" >/dev/null || die "local builder image unavailable: ${builder_image}"
	docker image inspect "$runtime_image" >/dev/null || die "local runtime image unavailable: ${runtime_image}"
	printf 'Building %s from %s (%s)\n' "$image" "$revision" "$version"
	docker build --pull=false \
		--build-arg "NAPCAT_BUILDER_IMAGE=${builder_image}" \
		--build-arg "NAPCAT_RUNTIME_IMAGE=${runtime_image}" \
		--build-arg "NAPCAT_VERSION=${version}" \
		--build-arg "NAPCAT_REVISION=${revision}" \
		--build-arg "NAPCAT_SOURCE_STATE=${source_state}" \
		--tag "$image" "$SCRIPT_DIR"
}

main "$@"
