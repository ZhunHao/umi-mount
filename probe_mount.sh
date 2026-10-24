#!/usr/bin/env bash
# Read-only probe for the UMi 17 Lite / MeowAstro (OnStep) mount.
#
# Usage:  ./probe_mount.sh [--sweep] [mount-ip]
#   --sweep  if the mount isn't at its usual addresses, try every address on this /24.
#            Off by default: on someone else's network that is a port scan.
#
# Sends only:
#   - HTTP GETs for the mount's pages and telemetry
#   - LX200 read commands (":G..#" and ":F..#" queries) on TCP 9999 / 9998
#   - TCP connect checks on ports 80, 2000, 9998, 9999
# Never sends dr= motion commands, park/unpark/sync/tracking changes, or
# LX200 set/move/sync commands. Results go to probe_output/<timestamp>/.

set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$ROOT/probe_output/$STAMP"
mkdir -p "$OUT"
ln -sfn "$OUT" "$ROOT/probe_output/latest"
SUMMARY="$OUT/summary.txt"

log() { printf '%s\n' "$*" | tee -a "$SUMMARY"; }

# The mount's /control.txt always has trk_on/trk_off lines
# (API_AND_HARDWARE_DISCOVERY.md, section 5). Use that as the signature.
is_mount() {
  curl -s -m 2 "http://$1/control.txt" 2>/dev/null | grep -qE '^trk_(on|off)\|'
}

# 1. Find the mount ---------------------------------------------------------
SWEEP=0
if [ "${1:-}" = "--sweep" ]; then SWEEP=1; shift; fi
MOUNT="${1:-}"

if [ -z "$MOUNT" ]; then
  log "Looking for the mount..."
  CANDIDATES="192.168.0.1"
  for name in onstep.local meowastro.local; do
    ip="$(dscacheutil -q host -a name "$name" 2>/dev/null | awk '/ip_address/{print $2; exit}')"
    [ -n "$ip" ] && CANDIDATES="$CANDIDATES $ip"
  done
  GW="$(route -n get default 2>/dev/null | awk '/gateway/{print $2}')"
  [ -n "$GW" ] && CANDIDATES="$CANDIDATES $GW"

  for ip in $CANDIDATES; do
    if is_mount "$ip"; then MOUNT="$ip"; break; fi
  done
fi

if [ -z "$MOUNT" ] && [ "$SWEEP" = 1 ]; then
  MY_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)"
  if [ -n "$MY_IP" ]; then
    PREFIX="${MY_IP%.*}"
    log "Not at the usual addresses. Sweeping $PREFIX.1-254 on port 80..."
    MOUNT="$(seq 1 254 | sed "s/^/$PREFIX./" \
      | xargs -P 64 -I{} sh -c 'curl -s -m 2 "http://{}/control.txt" | grep -qE "^trk_(on|off)\|" && echo {}' \
      | head -1)"
  fi
fi

if [ -z "$MOUNT" ]; then
  log "Mount not found. Join the 6semount Wi-Fi, or re-run with the IP:"
  log "  ./probe_mount.sh <mount-ip>"
  log "or try every address on this network: ./probe_mount.sh --sweep"
  exit 1
fi

log "Mount:   $MOUNT"
log "Output:  $OUT"
log "Started: $(date)"
log ""

# 2. HTTP pages and telemetry -----------------------------------------------
probe_http() {
  local path="$1"
  local name="${path//\//_}"
  [ -z "$name" ] && name="root"
  local status
  status="$(curl -s -m 5 -D "$OUT/$name.headers" -o "$OUT/$name" \
    -w '%{http_code} %{size_download}B %{time_total}s' "http://$MOUNT/$path" 2>/dev/null)"
  log "GET /$path -> ${status:-no response}"
}

log "== HTTP: documented pages and telemetry =="
for p in "" index.htm control.htm auxiliary.htm settings.htm configuration.htm wifi.htm control.txt; do
  probe_http "$p"
done

log ""
log "== HTTP: guessed names (404 is fine, it shows what exists) =="
for p in index.txt status.txt settings.txt configuration.txt auxiliary.txt wifi.txt favicon.ico; do
  probe_http "$p"
done

# 3. TCP ports --------------------------------------------------------------
log ""
log "== TCP ports =="
for port in 80 2000 9998 9999; do
  if nc -z -w 2 "$MOUNT" "$port" 2>/dev/null; then
    log "TCP $port open"
  else
    log "TCP $port closed or filtered"
  fi
done

# 4. LX200 read commands ----------------------------------------------------
# Read-only queries from the OnStep command protocol:
# https://onstep.groups.io/g/main/wiki/23755
# Set/move/sync commands are deliberately not in this list.
# Each query gets its own socket and waits up to 1.5 s for a reply. The old
# `nc` loop dropped replies when stdin closed early, so a "<no reply>" from it
# meant nothing. Needs python3.
LX200_READS="GVP GVN GVD GVT GU GC Ga GL GS GG Gt Gg Gm GT Gh Go GM GN GO GP GR GD GA Gr Gd FA Fa FT FG FM Fe Ft Fu FB FC Fc FD FP"
LX200_PORTS="${LX200_PORTS:-9999 9998}"

for port in $LX200_PORTS; do
  file="$OUT/lx200_$port.txt"
  log ""
  log "== LX200 read commands on TCP $port =="
  python3 - "$MOUNT" "$port" $LX200_READS <<'PY' | tee -a "$SUMMARY" "$file"
import socket, sys, time

host, port, cmds = sys.argv[1], int(sys.argv[2]), sys.argv[3:]

def ask(cmd, wait=1.5):
    with socket.create_connection((host, port), timeout=wait) as s:
        s.sendall(f":{cmd}#".encode())
        buf, end = b"", time.time() + wait
        while b"#" not in buf and time.time() < end:
            try:
                chunk = s.recv(256)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
    return buf.decode(errors="replace").strip() or "<no reply>"

for cmd in cmds:
    try:
        reply = ask(cmd)
    except OSError as e:
        reply = f"<error: {e}>"
    print(f":{cmd}# -> {reply}")
PY
done

log ""
log "Done: $(date)"
log "Saved files are in $OUT"
