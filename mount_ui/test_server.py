#!/usr/bin/env python3
"""Tests for server.py against a fake mount. Never contacts the real mount.

    python3 mount_ui/test_server.py
"""
import http.client
import json
import socket
import socketserver
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAKE_HTTP_PORT, FAKE_LX_PORT, UI_PORT = 18080, 19999, 18090
received = []  # every request the fake mount got, e.g. "/controlA.txt?dr=n1"

CONTROL = "trk_on|enabled\ntrk_off|disabled\npark|enabled\nunpark|disabled\nc_goto|disabled\n" \
          "alg1|disabled\nalg2|disabled\nalg3|disabled\nalga|disabled\nrpa|disabled\n"
SETTINGS = "bzr_on|disabled\nbzr_off|enabled\nsr_vf|disabled\nsr_f|enabled\nsr_n|enabled\n" \
           "sr_s|enabled\nsr_vs|enabled\n"
AUXILIARY = "x1v1|-\nx1v2|0.016\nx1v3|0.02\nx1v4|0\nsw4_on|enabled\nsw4_off|disabled\n"
# Note: no el/wl inputs, matching the live page as read on 2026-10-23.
CONFIG_PAGE = ("<input value='0' type='number' name='b1' min='0' max='3600'>"
               "<input value='0' type='number' name='b2' min='0' max='3600'>"
               "<input value='0' type='number' name='hl' min='-30' max='30'>"
               "<input value='90' type='number' name='ol' min='60' max='90'>"
               "<input style='width: 4em;' value='-103' type='number' name='g1' min='-180' max='180'>")
INDEX_PAGE = ("<html><body>Site: UT (web browser) 10/23/26 13:13:24 UT ( 22:15:58 LST) "
              "Coordinates: Current: &alpha;= 00:04:34 , &delta;= +00*00:00 "
              "Pier Side= West (meridian flips On ) Polar Alignment: &#x25c4; 12 &quot; &#x25b2; -3 &quot; "
              "(Mount relative to NCP) Operations: Parking: Not Parked &nbsp;&nbsp;Tracking: Off "
              "&nbsp;&nbsp;Tracking Rate: 0.000 Hz &nbsp;&nbsp;Maximum slew speed: 5.8 &deg;/s State: "
              "Last General (Background) Error: None &nbsp;&nbsp;Workload: 11% "
              "&nbsp;&nbsp;Wireless signal strength: 31dBm (100%)</body></html>")
PAGES = {"/index.htm": INDEX_PAGE, "/control.txt": CONTROL, "/settings.txt": SETTINGS, "/auxiliary.txt": AUXILIARY,
         "/configuration.htm": CONFIG_PAGE}
LX_REPLIES = {"GR": "07:46:01#", "GD": "+89*36:40#", "GU": "nNpHz/Eo260#", "GA": "+01*20:02#",
              "GS": "21:12:24#", "Gm": "N#", "Gr": "00:00:00#", "Gd": "+00*00:00#", "Gt": "+01*20#",
              "Gg": "-103*40#", "GG": "-08#", "MS": "0"}


class FakeMount(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        received.append(self.path)
        base = self.path.split("?")[0]
        body = PAGES.get(base, "") if base in PAGES else ""
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class ReusableLX(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


class FakeLX200(socketserver.BaseRequestHandler):
    def handle(self):
        buf = b""
        self.request.settimeout(2)
        while b"#" not in buf:
            try:
                chunk = self.request.recv(256)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
        cmd = buf.decode().strip(":#")
        if cmd.startswith(("Sr", "Sd")):
            reply = "1"  # set commands answer 1 with no '#'
        else:
            reply = LX_REPLIES.get(cmd, "")
        if reply:
            self.request.sendall(reply.encode())


def ui_request(method, path, body=None, content_type="application/json", host=None):
    conn = http.client.HTTPConnection("127.0.0.1", UI_PORT, timeout=10)
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    if host:
        headers["Host"] = host
    payload = body if isinstance(body, bytes) else (json.dumps(body).encode() if body is not None else None)
    conn.request(method, path, body=payload, headers=headers)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp.status, data


def post(path, body, **kw):
    status, data = ui_request("POST", path, body, **kw)
    return status, json.loads(data) if data and data[:1] == b"{" else data


def wait_port(port, seconds=8):
    end = time.time() + seconds
    while time.time() < end:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            return True
        except OSError:
            time.sleep(0.1)
    return False


failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(detail)) if not cond and detail else ""))
    if not cond:
        failures.append(name)


def main():
    fake_http = ThreadingHTTPServer(("127.0.0.1", FAKE_HTTP_PORT), FakeMount)
    fake_lx = ReusableLX(("127.0.0.1", FAKE_LX_PORT), FakeLX200)
    for srv in (fake_http, fake_lx):
        threading.Thread(target=srv.serve_forever, daemon=True).start()

    server = subprocess.Popen([sys.executable, str(HERE / "server.py"), "--mount", f"http://127.0.0.1:{FAKE_HTTP_PORT}",
                               "--lx-port", str(FAKE_LX_PORT), "--port", str(UI_PORT)],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        check("server starts", wait_port(UI_PORT), server.stdout.read1(500) if server.poll() else "")

        status, page = ui_request("GET", "/")
        check("GET / serves the page", status == 200 and b'id="stop"' in page, status)

        status, data = ui_request("GET", "/api/status")
        s = json.loads(data)
        check("status: online and control parsed", s["online"] and s["control"].get("trk_on") == "enabled", s.get("control"))
        check("status: settings and aux parsed", s["settings"].get("sr_vf") == "disabled" and s["auxiliary"].get("sw4_off") == "disabled")
        check("status: RA/Dec from LX200", s["position"]["ra"] == "07:46:01" and s["position"]["dec"] == "+89*36:40", s["position"])
        check("status: GU decoded (not parked, at home, idle)",
              s["status"]["not_parked"] is True and s["status"]["parked"] is False and s["status"]["at_home"] is True
              and s["status"]["slewing"] is False, s["status"])

        received.clear()
        st, r = post("/api/mount", {"file": "controlA.txt", "key": "dr", "value": "n1"})
        check("mount write: dr=n1 accepted and forwarded",
              st == 200 and r["ok"] and any(p.startswith("/controlA.txt?dr=n1") for p in received), (r, received))

        received.clear()
        st, r = post("/api/mount", {"file": "controlA.txt", "key": "dr", "value": "xx"})
        check("mount write: unknown dr value refused, not forwarded", not r["ok"] and not received, (r, received))

        st, r = post("/api/mount", {"file": "controlA.txt", "key": "zz", "value": "1"})
        check("mount write: unknown key refused", not r["ok"] and "not an allowed key" in r["error"], r)

        st, r = post("/api/mount", {"file": "evil.txt", "key": "dr", "value": "qq"})
        check("mount write: unknown file refused", not r["ok"], r)

        received.clear()
        st, r = post("/api/mount", {"file": "configurationA.txt", "key": "b1", "value": "9999"})
        check("config write: out of range refused, not forwarded", not r["ok"] and not received, (r, received))

        received.clear()
        st, r = post("/api/mount", {"file": "configurationA.txt", "key": "b1", "value": "10"})
        check("config write: in range forwarded", r["ok"] and any("configurationA.txt?b1=10" in p for p in received), (r, received))

        st, r = post("/api/mount", {"file": "auxiliaryA.txt", "key": "x1v2", "value": "0.030"})
        check("aux write: exposure as seconds is refused (it takes a 0-255 slider position)", not r["ok"], r)
        st, r = post("/api/mount", {"file": "auxiliaryA.txt", "key": "x1v2", "value": "40"})
        check("aux write: exposure slider position forwarded", r["ok"], r)
        st, r = post("/api/mount", {"file": "auxiliaryA.txt", "key": "x1v3", "value": "5"})
        check("aux write: delay below the slider minimum (10) refused", not r["ok"], r)

        st, data = ui_request("GET", "/api/dashboard")
        dash = json.loads(data)
        v = dash.get("values", {})
        check("dashboard: parses the status page",
              dash["ok"] and v["polar_alignment"] == ["12", "-3"] and v["workload"] == "11%"
              and v["signal"] == "31dBm (100%)" and v["last_error"] == "None" and v["tracking_rate"] == "0.000"
              and v["pier_side"] == "West" and v["meridian_flips"] == "On" and v["parking"] == "Not Parked", v)

        st, _ = ui_request("POST", "/api/mount", json.dumps({"file": "controlA.txt", "key": "dr", "value": "qq"}).encode(),
                           content_type="text/plain")
        check("POST without application/json refused (drive-by form post)", st == 415, st)

        st, js = ui_request("GET", "/mount3d.js")
        check("serves the 3D view script", st == 200 and b"MountView" in js, st)

        # An unreachable mount: status must come back fast, marked offline, with no position.
        offline = subprocess.Popen([sys.executable, str(HERE / "server.py"), "--mount", "http://127.0.0.1:9",
                                    "--lx-port", "9", "--port", str(UI_PORT + 1)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            wait_port(UI_PORT + 1)
            conn = http.client.HTTPConnection("127.0.0.1", UI_PORT + 1, timeout=10)
            started = time.time()
            conn.request("GET", "/api/status")
            o = json.loads(conn.getresponse().read())
            elapsed = time.time() - started
            check("offline mount: status returns quickly and says offline",
                  o["online"] is False and o["position"]["ra"] is None and elapsed < 2.5, (elapsed, o["online"]))
        finally:
            offline.terminate()
            offline.wait(timeout=5)

        st, _ = ui_request("GET", "/img/does-not-exist.jpg")
        check("image route: missing file is 404", st == 404, st)
        st, _ = ui_request("GET", "/img/..%2Fserver.py")
        check("image route: path tricks refused", st == 404, st)
        st, _ = ui_request("GET", "/api/status", host="evil.example:18090")
        check("request with a foreign Host header refused", st == 403, st)

        st, r = post("/api/lx200", {"cmd": "GR"})
        check("LX200 reads go through /api/status, not /api/lx200", not r["ok"], r)

        st, r = post("/api/lx200", {"cmd": "Sr12:30:00"})
        check("LX200 set target RA accepted", r["ok"] and r["reply"] == "1", r)

        st, r = post("/api/lx200", {"cmd": "Sd+10:00:00"})
        check("LX200 set target Dec accepted", r["ok"] and r["reply"] == "1", r)

        st, r = post("/api/lx200", {"cmd": "XX"})
        check("LX200 unknown command refused", not r["ok"], r)

        st, r = post("/api/lx200", {"cmd": "Sr99:99"})
        check("LX200 malformed set refused", not r["ok"], r)

        st, r = post("/api/lx200", {"cmd": "MS"})
        check("LX200 goto is allowed (reply passed through)", r["ok"] and r["reply"] == "0", r)

        received.clear()
        st, r = post("/api/clock", {})
        check("clock: sends qb=st to control.htm",
              r["ok"] and any(p.startswith("/control.htm?qb=st&dd=") and "&dm=" in p for p in received), (r, received))

        st, data = ui_request("GET", "/api/config")
        c = json.loads(data)
        check("config read: parses inputs", c["ok"] and c["values"].get("b1") == "0" and c["values"].get("ol") == "90",
              c)
        check("config read: missing el/wl are absent, not invented", "el" not in c["values"] and "wl" not in c["values"])
    finally:
        server.terminate()
        server.wait(timeout=5)
        fake_http.shutdown()
        fake_lx.shutdown()

    print()
    if failures:
        print(f"{len(failures)} failed: " + ", ".join(failures))
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
