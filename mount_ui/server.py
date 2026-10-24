#!/usr/bin/env python3
"""Local web UI for the UMi 17 Lite (MeowAstro / OnStep) mount.

Serves index.html and forwards a whitelist of requests to the mount.
Standard library only.

  python3 mount_ui/server.py          # http://127.0.0.1:8080, this Mac only
  python3 mount_ui/server.py --lan    # also reachable from other devices on the mount Wi-Fi

Every mount write goes through the whitelist below. Anything not listed is refused.
"""
import argparse
import html
import json
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMG_DIR = HERE / "img"
IMG_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
STATIC = {"mount3d.js": "application/javascript; charset=utf-8"}

# Set from the command line in main().
MOUNT_BASE = "http://192.168.0.1"
LX_HOST = "192.168.0.1"
LX_PORT = 9999
LAN = False

# Values the stock pages send (API_AND_HARDWARE_DISCOVERY.md, sections 4.5 and 5).
# A set lists the allowed values. A tuple (low, high, integer_only) is a numeric range.
WRITES = {
    "controlA.txt": {
        "dr": {"n1", "n0", "s1", "s0", "e1", "e0", "w1", "w0", "qq", "qh", "qr", "qc", "pk", "pu", "sy",
               "T1", "T0", "Ts", "Tl", "Th", "R0", "R1", "R2", "R5", "R6", "R7", "R8"},
        "al": {"1", "3", "9", "n"},
        "rp": {"a"},
    },
    "settingsA.txt": {
        "ab": {"on", "off"}, "ma": {"on", "off"}, "mp": {"on", "off"}, "pk": {"s"},
        "rr": {"on", "off", "don", "doff", "otk"}, "ss": {"f", "n", "s", "vf", "vs"}, "tk": {"-", "f", "r"},
    },
    # auxiliary.htm: x1v1 starts/stops the Camera-port intervalometer; x1v4 count, x1v2 exposure and
    # x1v3 delay are raw slider positions (the mount turns them into seconds); x4v1 is Alt-Az mode.
    "auxiliaryA.txt": {
        "x1v1": {"0", "1"}, "x4v1": {"0", "1"},
        "x1v4": (1, 255, True), "x1v2": (0, 255, True), "x1v3": (10, 255, True),
    },
    "configurationA.txt": {
        "b1": (0, 3600, True), "b2": (0, 3600, True), "el": (-270, 270, True), "wl": (-270, 270, True),
        "hl": (-30, 30, True), "ol": (60, 90, True),
    },
}

# LX200 reads the status page uses (OnStep command reference).
LX_READS = {
    "ra": "GR", "dec": "GD", "alt": "GA", "lst": "GS", "status": "GU", "pier": "Gm",
    "target_ra": "Gr", "target_dec": "Gd", "lat": "Gt", "lon": "Gg", "utc_offset": "GG",
}

# LX200 commands the UI may send: set target, sync, goto, stop, home, set home.
LX_WRITES = [
    r"Sr\d{2}:\d{2}:\d{2}",
    r"Sd[+-]\d{2}:\d{2}:\d{2}",
    r"CS", r"MS", r"Q", r"hC", r"hF",
]


def mount_get(path, timeout=3.0):
    """GET a mount page with a cache-busting parameter, like the stock pages do."""
    sep = "&" if "?" in path else "?"
    url = f"{MOUNT_BASE}/{path}{sep}x={time.time_ns() // 1_000_000}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        return err.code, ""
    except OSError as err:
        return 0, str(err)


LX_LOCK = threading.Lock()


def lx200(cmd, wait=1.5):
    """Send one LX200 command. Returns (reply without the trailing '#' or None, error or None).

    Commands go one at a time so a status read and a command never share the port. Stop (:Q#)
    skips the queue: it must not wait behind a slow read.
    """
    if cmd == "Q":
        return _lx200_send(cmd, wait)
    with LX_LOCK:
        return _lx200_send(cmd, wait)


def _lx200_send(cmd, wait):
    try:
        with socket.create_connection((LX_HOST, LX_PORT), timeout=wait) as sock:
            sock.sendall(f":{cmd}#".encode())
            buf, end = b"", time.time() + wait
            while b"#" not in buf and time.time() < end:
                try:
                    chunk = sock.recv(256)
                except socket.timeout:
                    break
                if not chunk:
                    break
                buf += chunk
    except OSError as err:
        return None, str(err)
    text = buf.decode(errors="replace").strip().rstrip("#")
    return (text or None), None


def parse_pairs(text):
    """'key|value' lines from control.txt, settings.txt and auxiliary.txt."""
    out = {}
    for line in text.splitlines():
        if "|" in line:
            key, value = line.split("|", 1)
            out[key.strip()] = value.strip()
    return out


INPUT_RE = re.compile(r"<input[^>]*>", re.IGNORECASE)
ATTR_RE = re.compile(r"(\w+)='([^']*)'")


def page_inputs(html):
    """name -> value for every named <input> on a stock page."""
    out = {}
    for tag in INPUT_RE.findall(html):
        attrs = dict(ATTR_RE.findall(tag))
        if "name" in attrs:
            out[attrs["name"]] = attrs.get("value", "")
    return out


def read_status():
    # One request at a time: the mount's web server is a small ESP32. If control.txt doesn't
    # answer, the mount is unreachable, so skip the rest instead of waiting out every timeout.
    pages = {"control.txt": mount_get("control.txt")}
    online = pages["control.txt"][0] == 200
    for name in ("settings.txt", "auxiliary.txt"):
        pages[name] = mount_get(name) if online else (0, "")
    reply = {key: (lx200(cmd)[0] if online else None) for key, cmd in LX_READS.items()}

    def text_of(name):
        status, body = pages[name]
        return parse_pairs(body) if status == 200 else {}

    gu = reply["status"] or ""
    return {
        "time": datetime.now().isoformat(timespec="seconds"),
        "online": online,
        "control": text_of("control.txt"),
        "settings": text_of("settings.txt"),
        "auxiliary": text_of("auxiliary.txt"),
        "position": {k: reply[k] for k in ("ra", "dec", "alt", "lst", "pier")},
        "target": {"ra": reply["target_ra"], "dec": reply["target_dec"]},
        "site": {k: reply[k] for k in ("lat", "lon", "utc_offset")},
        # Status letters from the OnStep :GU# reference: P parked, p not parked, H at home, N not slewing.
        "status": {
            "raw": gu or None,
            "parked": ("P" in gu) if gu else None,
            "not_parked": ("p" in gu) if gu else None,
            "at_home": ("H" in gu) if gu else None,
            "slewing": ("N" not in gu) if gu else None,
        },
    }


DASHBOARD = {
    "polar_alignment": r"Polar Alignment:\s*◄\s*(-?[\d.]+)\s*\"?\s*▲\s*(-?[\d.]+)",
    "workload": r"Workload:\s*([\d.]+%)",
    "signal": r"Wireless signal strength:\s*(-?\d+\s*dBm\s*\(\d+%\))",
    "last_error": r"Last General \(Background\) Error:\s*(.+?)\s+Workload",
    "max_slew": r"Maximum slew speed:\s*([\d.]+)",
    "tracking_rate": r"Tracking Rate:\s*([\d.]+)\s*Hz",
    "meridian_flips": r"meridian flips\s+(On|Off)",
    "pier_side": r"Pier Side=\s*(\w+)",
    "parking": r"Parking:\s*(.+?)\s+Tracking:",
}


def read_dashboard():
    """Readings that only the stock status page (index.htm) shows."""
    status, page = mount_get("index.htm")
    if status != 200:
        return {"ok": False, "error": f"index.htm returned {status}"}
    text = re.sub(r"<script.*?</script>", " ", page, flags=re.S | re.I)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))
    out = {}
    for key, pattern in DASHBOARD.items():
        m = re.search(pattern, text)
        out[key] = (list(m.groups()) if len(m.groups()) > 1 else m.group(1).strip()) if m else None
    return {"ok": True, "values": out}


def read_config():
    status, html = mount_get("configuration.htm")
    if status != 200:
        return {"ok": False, "error": f"configuration.htm returned {status}"}
    return {"ok": True, "values": page_inputs(html)}


def check_write(file, key, value):
    rules = WRITES.get(file)
    if rules is None:
        return f"{file} is not a writable endpoint"
    rule = rules.get(key)
    if rule is None:
        return f"{key} is not an allowed key for {file}"
    if isinstance(rule, set):
        return None if value in rule else f"{value!r} is not an allowed value for {key}"
    low, high, integer = rule
    pattern = r"-?\d+" if integer else r"-?\d+(\.\d+)?"
    if not re.fullmatch(pattern, value):
        return f"{value!r} is not a number for {key}"
    if not low <= float(value) <= high:
        return f"{key} must be between {low} and {high}"
    return None


def result_of(status):
    return {"ok": status == 200, "code": status, "error": None if status == 200 else f"HTTP {status}"}


def mount_write(file, key, value):
    error = check_write(file, key, value)
    if error:
        return {"ok": False, "code": None, "error": error}
    status, _ = mount_get(f"{file}?{urllib.parse.urlencode({key: value})}")
    return result_of(status)


def set_clock():
    """Same request the stock Set Date/Time button sends: month is 0-based."""
    now = datetime.now()
    query = urllib.parse.urlencode({
        "qb": "st", "dd": now.day, "dm": now.month - 1, "dy": now.year,
        "th": now.hour, "tm": now.minute, "ts": now.second,
    })
    status, _ = mount_get(f"control.htm?{query}")
    return result_of(status)


def lx200_command(cmd):
    if not any(re.fullmatch(pattern, cmd) for pattern in LX_WRITES):
        return {"ok": False, "reply": None, "error": f"{cmd!r} is not an allowed LX200 command"}
    reply, err = lx200(cmd)
    return {"ok": err is None, "reply": reply, "error": err}


class Handler(BaseHTTPRequestHandler):
    server_version = "MountUI/1.0"

    def log_message(self, fmt, *args):
        return  # the page has its own log

    def send_bytes(self, code, data, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, code, payload):
        self.send_bytes(code, json.dumps(payload).encode(), "application/json")

    def host_allowed(self):
        if LAN:
            return True
        host = self.headers.get("Host", "").rsplit(":", 1)[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self.host_allowed():
            return self.send_json(403, {"error": "host not allowed"})
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self.send_bytes(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/status":
            return self.send_json(200, read_status())
        if path == "/api/config":
            return self.send_json(200, read_config())
        if path == "/api/dashboard":
            return self.send_json(200, read_dashboard())
        if path.startswith("/img/"):
            return self.send_image(path[len("/img/"):])
        if path.lstrip("/") in STATIC:
            name = path.lstrip("/")
            return self.send_bytes(200, (HERE / name).read_bytes(), STATIC[name])
        self.send_json(404, {"error": "not found"})

    def send_image(self, name):
        # Only plain file names directly inside mount_ui/img/. No subfolders, no "..".
        target = IMG_DIR / name
        if (Path(name).name != name or target.suffix.lower() not in IMG_TYPES
                or not target.is_file()):
            return self.send_json(404, {"error": "not found"})
        self.send_bytes(200, target.read_bytes(), IMG_TYPES[target.suffix.lower()])

    def do_POST(self):
        if not self.host_allowed():
            return self.send_json(403, {"error": "host not allowed"})
        # Browsers can't send application/json cross-site without a preflight, which this server
        # does not answer. Requiring the header blocks drive-by form posts from other pages.
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self.send_json(415, {"error": "send application/json"})
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self.send_json(400, {"error": "bad json"})
        path = self.path.split("?")[0]
        if path == "/api/mount":
            return self.send_json(200, mount_write(str(body.get("file", "")), str(body.get("key", "")),
                                                   str(body.get("value", ""))))
        if path == "/api/lx200":
            return self.send_json(200, lx200_command(str(body.get("cmd", ""))))
        if path == "/api/clock":
            return self.send_json(200, set_clock())
        self.send_json(404, {"error": "not found"})


def main():
    global MOUNT_BASE, LX_HOST, LX_PORT, LAN
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mount", default="http://192.168.0.1", help="mount web address")
    parser.add_argument("--lx-host", default=None, help="LX200 host (default: the mount's host)")
    parser.add_argument("--lx-port", type=int, default=9999, help="LX200 port")
    parser.add_argument("--port", type=int, default=8080, help="port for this UI")
    parser.add_argument("--lan", action="store_true",
                        help="listen on all interfaces. Anyone on the mount Wi-Fi can then drive the mount")
    args = parser.parse_args()
    MOUNT_BASE = args.mount.rstrip("/")
    LX_HOST = args.lx_host or urllib.parse.urlsplit(MOUNT_BASE).hostname
    LX_PORT = args.lx_port
    LAN = args.lan
    bind = "0.0.0.0" if LAN else "127.0.0.1"
    print(f"Mount UI: http://{bind}:{args.port}   mount {MOUNT_BASE}   LX200 {LX_HOST}:{LX_PORT}")
    ThreadingHTTPServer((bind, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
