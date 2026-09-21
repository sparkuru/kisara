#!/usr/bin/env bash
set -Eeuo pipefail

readonly CONFIG_DIR="/app/napcat/config"
readonly NAPCAT_ARCHIVE="/app/NapCat.Shell.zip"
readonly ONEBOT_CONFIG_PATH="${CONFIG_DIR}/onebot11.json"

bootstrap_dir=""

cleanup() {
	if [[ -n "${bootstrap_dir}" && -d "${bootstrap_dir}" ]]; then
		rm -rf -- "${bootstrap_dir}"
	fi
}

die() {
	printf '[kisara-napcat] %s\n' "$*" >&2
	exit 1
}

trap cleanup EXIT

mkdir -p -- "${CONFIG_DIR}"

if [[ ! -f "${CONFIG_DIR}/napcat.json" ]]; then
	[[ -f "${NAPCAT_ARCHIVE}" ]] || die "NapCat.Shell.zip was not found"

	bootstrap_dir=$(mktemp -d /tmp/kisara-napcat.XXXXXXXX)
	unzip -q "${NAPCAT_ARCHIVE}" -d "${bootstrap_dir}"
	[[ -d "${bootstrap_dir}/config" ]] || {
		die "NapCat.Shell.zip has an unexpected layout"
	}
	cp -rf -- "${bootstrap_dir}/config/." "${CONFIG_DIR}/"
fi

onebot_access_token="${ONEBOT_ACCESS_TOKEN:-}"
if [[ -n "${onebot_access_token}" && ! "${onebot_access_token}" =~ ^[A-Za-z0-9._~-]+$ ]]; then
	die "ONEBOT_ACCESS_TOKEN must contain only letters, digits, dot, underscore, tilde, or hyphen"
fi

cat >"${ONEBOT_CONFIG_PATH}" <<EOF
{
  "network": {
    "httpServers": [],
    "httpSseServers": [],
    "httpClients": [],
    "websocketServers": [
      {
        "enable": true,
        "name": "ws",
        "host": "0.0.0.0",
        "port": 3001,
        "reportSelfMessage": false,
        "enableForcePushEvent": true,
        "messagePostFormat": "array",
        "token": "${onebot_access_token}",
        "debug": false,
        "heartInterval": 30000
      }
    ],
    "websocketClients": [],
    "plugins": []
  },
  "musicSignUrl": "",
  "enableLocalFile2Url": false,
  "parseMultMsg": false
}
EOF
chmod 600 "${ONEBOT_CONFIG_PATH}"

trap - EXIT
exec /app/entrypoint.sh
