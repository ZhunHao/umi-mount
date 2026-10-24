# UMi 17 Lite Web Controller

A local control page for the **UMi 17 Lite** harmonic mount (MeowAstro WiFi server, OnStep 4.21e), to use instead of the UMi Mount / MeowGoto apps.

---

## Features

- **3D mount view:** a model of the mount that turns on its RA and Dec axes from the mount's own readings, with the polar axis set to your latitude. Drag to turn it, scroll to zoom. The axis you are moving lights up.
- **Sky plot:** hour angle against declination, with the recent trail, the target, and arrows for the direction you are holding.
- **Press-and-hold Move pad:** N, S, E, W, with East on the left as on the mount's own page. Start and stop commands are sent in order, and a held direction is released if the page loses focus.
- **Stop:** always at the top. The space bar does the same.
- **Speed, tracking, park and home**, plus target, goto and sync over LX200, and the mount's settings, auxiliary and configuration pages.
- **Arrow keys:** up north, down south, left east, right west.
- **No dependencies:** Python standard library and plain JavaScript, so it runs offline.

---

## How to Use

The page talks to the mount through a small local server. A browser page can't read the mount's replies directly, because the mount sends no CORS headers.

1. Join the mount's Wi-Fi.
2. From this folder, start the server:

   ```bash
   python3 mount_ui/server.py
   ```

3. Open http://127.0.0.1:8080.

To use a phone on the same Wi-Fi, start it with `--lan` and open `http://<this computer's IP>:8080` on the phone. Anyone on that Wi-Fi can then drive the mount, because the mount has no login.

### Tests

These run against a fake mount and never contact the real one:

```bash
python3 mount_ui/test_server.py
node mount_ui/test_mount3d.js
```

---

## Documentation
See `API_AND_HARDWARE_DISCOVERY.md` for the HTTP API, LX200 commands, and telemetry found on the mount.
