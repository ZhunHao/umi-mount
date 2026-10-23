#!/usr/bin/env bash
# Usage: ./mount_cmd.sh 'controlA.txt?dr=qq'
# One GET to the mount. Appends time, request and reply to probe_output/mount-actions.log.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)/probe_output"
mkdir -p "$DIR"
LOG="$DIR/mount-actions.log"
REQ="$1"
case "$REQ" in *\?*) SEP="&" ;; *) SEP="?" ;; esac
RESP="$(curl -s -m 3 -w ' [http %{http_code}]' "http://192.168.0.1/${REQ}${SEP}x=$(date +%s)")"
echo "$(date '+%Y-%m-%d %H:%M:%S')  GET /${REQ} -> ${RESP}" | tee -a "$LOG"
