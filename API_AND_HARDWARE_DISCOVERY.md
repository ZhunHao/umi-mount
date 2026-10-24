# UMi 17 Lite (MeowAstro / OnStep): Hardware and API Reference

What the mount exposes over Wi-Fi, from the stock web pages and the probes on 2026-10-23 (raw results in `probe_output/`), plus the [OnStep command reference](https://onstep.groups.io/g/main/wiki/23755) for the LX200 commands.

---

## 1. Identification

* **Device:** UMi 17 Lite harmonic mount (Proxisky).
* **Firmware:** `MeowAstro WiFi Server 2.1v (OnStep 4.21e)`. Over LX200: `:GVP#` On-Step, `:GVN#` 4.21e, `:GVD#` Nov 2 2023, `:GVT#` 20:46:24.
* **Wi-Fi side:** an OnStep "Smart Web Server" style add-on (web pages plus LX200 on 9999 and 9998). The board inside isn't identified.
* **Back panel:** Camera (3.5 mm jack, driven by the intervalometer in section 4.3), Guide (RJ, ST-4), USB-B, DC 12–15 V. One check on the Mac listed no USB serial device, but it isn't confirmed the cable was connected.

---

## 2. Network

| Item | Value | Notes |
| :--- | :--- | :--- |
| Mount address | `192.168.0.1` | Access-point mode, subnet `255.255.255.0` (from `wifi.htm` after login) |
| Station mode | Not set up | Station SSID empty, so the mount's network has no internet |
| HTTP | Port 80 | `.htm` pages are `Transfer-Encoding: chunked`; `.txt` files send `Content-Length`; every reply has `Connection: close` |
| CORS | None | No `Access-Control-*` headers, so a page from another origin can send requests but can't read replies |
| LX200 | Ports 9999 and 9998 | Both answer. OnStep docs: 9999 is the command channel, 9998 the persistent one |
| Port 2000 | Closed | Celestron AUX is not used |

---

## 3. Stock pages

| Page | Holds | Polls |
| :--- | :--- | :--- |
| `/index.htm` | Status: UT and LST, site, current and target coordinates, pier side and meridian-flip setting, polar alignment error, parking, tracking, tracking rate, maximum slew speed, last error, workload, Wi-Fi signal | Nothing (server-rendered) |
| `/control.htm` | Move pad, speeds, tracking, park and home, alignment, sync, set date/time | `control.txt` |
| `/settings.htm` | Maximum slew speed, compensated tracking, tracking rate trim, set park, goto buzzer, meridian-flip options | `settings.txt` |
| `/auxiliary.htm` | Camera-port intervalometer, ALTAZM (Alt-Az mode) | `auxiliary.txt` |
| `/configuration.htm` | Site, horizon and overhead limits, backlash, meridian limits | Nothing (values are in the inputs; `configuration.txt` is 404) |
| `/wifi.htm` | Login form; after login, access-point and station settings | Nothing |

---

## 4. Commands

Every write is `GET /<page>A.txt?<key>=<value>&x=<timestamp>`. There is no login. A `200` with an empty body means the mount accepted the request, not that anything happened.

### 4.1. `controlA.txt` (stock `control.htm`)

| Button (stock label) | Request | Notes |
| :--- | :--- | :--- |
| Move N, S, E, W | `dr=n1`, `s1`, `e1`, `w1` on press; `n0`, `s0`, `e0`, `w0` on release | The stock pad has East on the left, West on the right |
| Speed `0.25`, `0.5`, `1x`, `4x`, `40x`, `60x`, `Max` | `dr=R0`, `R1`, `R2`, `R5`, `R6`, `R7`, `R8` | No `R3`, `R4` or `R9` buttons |
| Emergency Stop! | `dr=qq` | |
| Find Home | `dr=qh` | Moves to the home position |
| Home (Reset) | `dr=qr` | Behind `confirm()`. Tells the mount it is at home now |
| Continue Goto (when paused at home) | `dr=qc` | Button `c_goto` |
| Park / Un-Park | `dr=pk` / `dr=pu` | Buttons `park` / `unpark` |
| Tracking on / off | `dr=T1` / `dr=T0` | Buttons `trk_on` / `trk_off` |
| Sidereal / Lunar / Solar Rate | `dr=Ts` / `Tl` / `Th` | |
| Sync | `dr=sy` | Syncs to the **target**. See the warning below |
| `1★`, `3★`, `9★`, `Accept` | `al=1`, `al=3`, `al=9`, `al=n` | Star alignment. Buttons `alg1`, `alg2`, `alg3`, `alga` |
| `Refine PA` | `rp=a` | Behind `confirm()`. Refines polar alignment; button `rpa` was disabled (not available) throughout 2026-10-23 |
| Set Date/Time | `GET /control.htm?qb=st&dd=…&dm=…&dy=…&th=…&tm=…&ts=…` | A form submit, not `controlA.txt`. `dm` is the 0-based month. Accepted on 2026-10-23 |

* The stock pages have **no goto button**. Goto is LX200 only (section 4.5).
* **Sync warning:** `dr=sy` and `:CS#` take the current *target* as where the telescope points, and the stock page can't set the target. On 2026-10-23 the target was `00:00:00 +00*00:00`, so Sync wrote RA 0h, Dec 0° into the pointing model while the tube was near the pole. Set the target first (`:SrHH:MM:SS#`, `:SdsDD:MM:SS#`), centre that object, then sync.

### 4.2. `settingsA.txt` (stock `settings.htm`)

| Setting (stock label) | Request | Reported in `settings.txt` as |
| :--- | :--- | :--- |
| Maximum Slew Speed: VFast (2x), Fast (1.5x), Normal (1x), Slow (0.75x), VSlow (0.5x) | `ss=vf`, `f`, `n`, `s`, `vs` | `sr_vf` … `sr_vs` |
| Compensated Tracking Rate (Pointing Model/Refraction): Full, Refraction Only, Off | `rr=otk`, `on`, `off` | `ot_on`, `ot_ref`, `ot_off` |
| … Dual Axis, Single Axis | `rr=don`, `doff` | `ot_dul`, `ot_sgl` |
| Tracking Rate: + (0.02Hz faster), - (0.02Hz slower), Reset (default) | `tk=f`, `tk=-`, `tk=r` | Not reported |
| Park: Set-Park | `pk=s` | Not reported. Makes the current position the park position |
| Goto Alert, Buzzer: On, Off | `ab=on`, `off` | `bzr_on`, `bzr_off` |
| Automatic Meridian Flip at Limit: On, Off | `ma=on`, `off` | `mfa_on`, `mfa_off` |
| Meridian Flip, Pause at Home: On, Off | `mp=on`, `off` | `mfp_on`, `mfp_off` |
| Language (page script, not tested) | `lang=0` Chinese, `lang=1` English | Takes effect after a restart |

`index.htm`'s "Maximum slew speed" followed `ss` on 2026-10-23: 5.8, 4.4, 2.9, 1.9 and 1.5 °/s for `vf`, `f`, `n`, `s` and `vs`.

### 4.3. `auxiliaryA.txt` (stock `auxiliary.htm`)

| Control (stock label) | Request | Reported in `auxiliary.txt` as |
| :--- | :--- | :--- |
| •CAMERA• Start / Stop (intervalometer on the Camera jack) | `x1v1=1` / `x1v1=0` | `x1v1` (`-` when idle) |
| Count (slider 1–255) | `x1v4=<position>` | `x1v4`, the count |
| Exposure (slider 0–255) | `x1v2=<position>` | `x1v2`, in seconds (0.016 at the stock default) |
| Delay (slider 10–255) | `x1v3=<position>` | `x1v3`, in seconds (0.02 at the stock default) |
| •ALTAZM• On / Off (Alt-Az mode) | `x4v1=1` / `x4v1=0` | `sw4_on` / `sw4_off` |

* The sliders send raw positions and the mount converts them. Decimal seconds (`x1v2=0.030`) were ignored on 2026-10-23.
* Turning ALTAZM on made `settings.txt` stop reporting `mfa`, `mfp` and `ot`, and `configuration.htm` stop showing `el` and `wl`.

### 4.4. `configurationA.txt` (stock `configuration.htm`)

| Input | Meaning | Range |
| :--- | :--- | :--- |
| `g1`, `g2`, `g3` | Longitude degrees, minutes, seconds. **W is +** | ±180° |
| `t1`, `t2`, `t3` | Latitude degrees, minutes, seconds. N is + | ±90° |
| `u1`, `u2` | UTC offset hours and minutes (`0`, `30`, `45`). The opposite of a time-zone value, for standard time | −14 to +12 h |
| `hl` | Horizon limit, minimum altitude | ±30° |
| `ol` | Overhead limit, maximum altitude | 60–90° |
| `b1`, `b2` | Backlash, axis 1 (RA/Azm) and axis 2 (Dec/Alt) | 0–3600″ |
| `el`, `wl` | Past the meridian when east / west of the pier | ±270°. Hidden in Alt-Az mode |

`hl`, `ol`, `b1` and `b2` were each changed and restored on 2026-10-23, and the page showed the new values.

### 4.5. LX200 on TCP 9999 / 9998

* **Reads that answered:** `:GVP#` `:GVN#` `:GVD#` `:GVT#` `:GU#` `:GC#` `:Ga#` `:GL#` `:GS#` `:GG#` `:Gt#` `:Gg#` `:Gm#` `:GT#` `:Gh#` `:Go#` `:GM#`–`:GP#` `:GR#` `:GD#` `:GA#` `:Gr#` `:Gd#` `:D#` `:VR#`. The focuser queries (`:FA#` and so on) answer `0`: no focuser.
* **`:GU#` status letters:** `P` parked, `p` not parked, `H` at home, `N` not slewing (OnStep reference).
* **Writes used:** `:SrHH:MM:SS#` and `:SdsDD:MM:SS#` reply `1` (accepted). `:MS#` goto, `:CS#` sync, `:hC#` go home, `:hF#` set home and `:Q#` stop reply nothing.
* **Don't send:** `:ERESET#`, `:ENVRESET#` (reset, erase settings), `:SBn#` (serial speed), `:$QZ!#` (PEC to EEPROM), `:LW…#`, `:LL#`, `:L!#` (catalog writes). `mount_lx200.py` refuses these unless given `--force`.

---

## 5. Telemetry files

`control.txt`, `settings.txt` and `auxiliary.txt` are `id|enabled` or `id|disabled` lines, one per stock button. The stock pages poll them and enable or disable the buttons with those ids.

* **In a choice group** (`trk_on`/`trk_off`, `sr_*`, `ot_on`/`ot_ref`/`ot_off`, `bzr_*`, `mfa_*`, `mfp_*`, `sw4_*`) the disabled button is the current choice. So `trk_on|disabled` means tracking is on.
* **Elsewhere** (`park`, `unpark`, `c_goto`, `alg1`–`alga`, `rpa`, `ot_dul`/`ot_sgl`) disabled just means not available now.
* **Don't read `park`/`unpark` as the parking state.** Both samples showed Not Parked on `index.htm` with opposite button states:
  * `park|enabled`, `unpark|disabled` (stock dump in `raw_stock_ui/`): "Not Parked", tracking on.
  * `park|disabled`, `unpark|enabled` (2026-10-23): "Not Parked ( At Home )", tracking off.

  Use the `Parking:` line on `index.htm`, or `:GU#`.

```text
control.txt                 settings.txt (equatorial)     auxiliary.txt
trk_on|enabled              bzr_on|disabled               x1v1|-
trk_off|disabled            bzr_off|enabled               x1v2|0.016
park|disabled               mfa_on|enabled                x1v3|0.02
unpark|enabled              mfa_off|disabled              x1v4|0
c_goto|disabled             mfp_on|enabled                sw4_on|enabled
alg1|enabled                mfp_off|disabled              sw4_off|disabled
alg2|enabled                ot_on|enabled
alg3|enabled                ot_ref|enabled
alga|disabled               ot_off|disabled
rpa|disabled                ot_dul|disabled
                            ot_sgl|disabled
                            sr_vf|disabled
                            sr_f|enabled  (… sr_n, sr_s, sr_vs enabled)
```

---

## 6. Wi-Fi page

`POST /wifi.htm` with `login=<web password>` returns the configuration form. Fields: `stssid`, `stpwd` (station), `webpwd` (web password), `apen` (access point on), `apip1`–`4`, `apgw1`–`4`, `apsn1`–`4`, `apmac`, and `ccto` / `wcto` (command and web serial read time-outs, ms).

On 2026-10-23 the access point was on at `192.168.0.1`, the station SSID and password were empty, and both time-outs were 60. Writing this form wasn't tested. A wrong station setting can cut off Wi-Fi access, though OnStep's docs say the access point comes back if station mode can't connect.

---

## 7. Files in this repo

* `mount_ui/`: the control page (`server.py`, `index.html`, `mount3d.js`) and its tests. See `README.md`.
* `probe_mount.sh`: read-only probe; results in `probe_output/<timestamp>/`. `--sweep` searches the local network.
* `mount_cmd.sh`: sends one HTTP command and logs it to `probe_output/mount-actions.log`.
* `mount_lx200.py`: sends LX200 commands on port 9999 and prints the replies.
* `probe_output/`: probe runs, command logs and saved stock pages from 2026-10-23.
* `raw_stock_ui/`: stock pages saved in an earlier session.
