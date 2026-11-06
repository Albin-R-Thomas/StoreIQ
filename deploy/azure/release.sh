#!/usr/bin/env bash
# Usage: release.sh /opt/storeiq/releases/RELEASE RELEASE
set -euo pipefail
umask 077
release_dir="$(realpath "${1:?release directory required}")"
release="${2:?release name required}"
case "$release_dir" in /opt/storeiq/releases/*) ;; *) echo 'Invalid release directory' >&2; exit 1 ;; esac
[[ "$release" =~ ^[A-Za-z0-9_.-]+$ ]] || exit 1
exec 9>/opt/storeiq/deployment.lock
flock -n 9 || { echo 'Another deployment is running' >&2; exit 1; }
test -s /opt/storeiq/.env
export STOREIQ_RELEASE="$release"
cd "$release_dir"
docker compose -f compose.azure.yaml config --quiet
docker compose -f compose.azure.yaml build
if [[ -f /opt/storeiq/data/store-iq.db ]]; then
  python3 - <<'PY'
import datetime, sqlite3
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
with sqlite3.connect('/opt/storeiq/data/store-iq.db') as source:
    with sqlite3.connect(f'/opt/storeiq/backups/predeploy-{stamp}.db') as target:
        source.backup(target)
PY
fi
docker compose -f compose.azure.yaml up -d --wait --wait-timeout 180
curl --fail --silent --show-error http://127.0.0.1:8000/health/ready
ln -sfn "$release_dir" /opt/storeiq/current
printf '\nDeployed %s\n' "$release"
