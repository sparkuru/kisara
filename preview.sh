#!/usr/bin/env bash
# Thin preview entry; the installed engine lifecycle owns configuration and Docker.
set -Eeuo pipefail
readonly REPO_ROOT="$(cd -- "${BASH_SOURCE[0]%/*}" && pwd -P)"
exec "${REPO_ROOT}/deploy/engines.sh" preview "$@"
