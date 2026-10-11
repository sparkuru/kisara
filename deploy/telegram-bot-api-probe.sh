#!/usr/bin/env bash
set -Eeuo pipefail

main() {
	case ${1:-ready} in
	ready)
		timeout 3 bash -c 'exec 3<>/dev/tcp/127.0.0.1/8081'
		;;
	listeners)
		ss -H -lnt | awk '
			{ endpoint=$4; port=endpoint; sub(/^.*:/, "", port);
			  host=endpoint; sub(/:[^:]*$/, "", host);
			  if (host != "127.0.0.11") print host "|" port }'
		;;
	*) printf 'Usage: telegram-bot-api-probe.sh [ready|listeners]\n' >&2; return 2 ;;
	esac
}

main "$@"
