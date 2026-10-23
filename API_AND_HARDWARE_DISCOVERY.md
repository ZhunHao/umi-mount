# UMi 17 Lite Mount (MeowAstro / OnStep) Discovery & API Reference

This document records the hardware, network configuration, and HTTP API discovered from the **UMi 17 Lite** harmonic drive mount.

---

## 1. Hardware & System Identification

* **Device:** UMi 17 Lite (Proxisky / MeowAstro Harmonic Drive Mount)
* **Controller:** ESP32 Microcontroller
* **Firmware:** `MeowAstro WiFi Server 2.1v (OnStep 4.21e)`
* **Active Web Interface:** HTTP Port 80
* **Network Mode:** Access Point (SoftAP) by default; supports Station (STA) mode

---

## 2. Network Specifications

| Parameter | Value | Notes |
| :--- | :--- | :--- |
| **Mount IP (Gateway)** | `192.168.0.1` | Static internal IP in AP mode |
| **Client IP** | `192.168.0.100` | Assigned automatically to Mac / Phone via DHCP |
| **Subnet Mask** | `255.255.255.0` | Broadcast: `192.168.0.255` |
| **HTTP Web Server** | **Port 80 [OPEN]** | Fast HTTP/1.1 web server (`Transfer-Encoding: chunked`) |
| **Celestron AUX / SkyPortal** | Port 2000 | Closed / Timed out (Uses OnStep architecture) |
| **LX200 Command Port** | Port 9999 / 9998 | Available over serial / IP depending on firmware config |

---

## 3. Discovered Web Pages & Endpoints

The mount web server exposes the following pages:

* `/index.htm` — Status Dashboard (Live coordinates, site info, tracking status, polar alignment error, workload)
* `/control.htm` — Mount Motion & Operations (Directional guide, tracking toggle, slew rates, parking, alignment)
* `/auxiliary.htm` — Auxiliary Features (Focuser, rotator, dew heater if configured)
* `/settings.htm` — Mount Settings (Backlash, limits, guide rates)
* `/configuration.htm` — Motor and Gear Ratio Configuration
* `/wifi.htm` — Network Configuration (Station mode setup to connect to home Wi-Fi)

---

## 4. HTTP Control API (`/controlA.txt`)

All control actions are dispatched as HTTP GET requests to:
```http
GET http://192.168.0.1/controlA.txt?<key>=<value>&x=<timestamp>
```

### 4.1. Manual Slewing (D-Pad)
The mount implements a **press-to-move, release-to-stop** pattern:

| Direction | Pointer Down (Start Move) | Pointer Up (Halt Move) |
| :--- | :--- | :--- |
| **North (Dec +)** | `GET /controlA.txt?dr=n1` | `GET /controlA.txt?dr=n0` |
| **South (Dec -)** | `GET /controlA.txt?dr=s1` | `GET /controlA.txt?dr=s0` |
| **East (RA +)** | `GET /controlA.txt?dr=e1` | `GET /controlA.txt?dr=e0` |
| **West (RA -)** | `GET /controlA.txt?dr=w1` | `GET /controlA.txt?dr=w0` |

### 4.2. Slew Rates

| Speed Code | Rate | Description |
| :--- | :--- | :--- |
| `R0` | 0.25x | Fine Guiding |
| `R1` | 0.5x | Standard Guiding |
| `R2` | 1.0x | Centering Speed |
| `R5` | 4.0x | Fast Centering |
| `R6` | 40x | Find Rate |
| `R7` | 60x | High Speed Find |
| `R8` | MAX (~5.8°/s) | Maximum Slew Speed |

*Command format:* `GET /controlA.txt?dr=R<number>`

### 4.3. Mount Operations & Safety

| Function | Command | Notes |
| :--- | :--- | :--- |
| **Emergency STOP** | `GET /controlA.txt?dr=qq` | Instantly stops all motor rotation |
| **Find Home** | `GET /controlA.txt?dr=qh` | Slews to index / home sensor |
| **Home (Reset)** | `GET /controlA.txt?dr=qr` | Sets current position as Home |
| **Continue Goto** | `GET /controlA.txt?dr=qc` | Resumes a paused goto |
| **Park Mount** | `GET /controlA.txt?dr=pk` | Parks telescope in safe orientation |
| **Unpark Mount** | `GET /controlA.txt?dr=pu` | Unparks telescope for observing |
| **Sync Coordinates** | `GET /controlA.txt?dr=sy` | Synchronizes mount position with target |

### 4.4. Tracking Control

| State / Rate | Command |
| :--- | :--- |
| **Tracking ON** | `GET /controlA.txt?dr=T1` |
| **Tracking OFF** | `GET /controlA.txt?dr=T0` |
| **Sidereal Rate** | `GET /controlA.txt?dr=Ts` |
| **Lunar Rate** | `GET /controlA.txt?dr=Tl` |
| **Solar Rate** | `GET /controlA.txt?dr=Th` |

---

## 5. Telemetry & Polling Endpoint (`/control.txt`)

The web UI polls `http://192.168.0.1/control.txt` to update the enabled/disabled state of buttons:

```text
trk_on|disabled
trk_off|enabled
park|enabled
unpark|disabled
c_goto|disabled
alg1|disabled
alg2|disabled
alg3|disabled
alga|disabled
rpa|enabled
```

*Interpretation:*
* If `trk_on` is `disabled`, tracking is currently **ACTIVE (ON)**. This matches the dashboard in both samples.
* Don't read `park`/`unpark` as the parking state. Both samples show **Not Parked** on the dashboard, with opposite button states:
  * `park|enabled`, `unpark|disabled` (stock dump in `raw_stock_ui/`): dashboard "Not Parked", tracking On.
  * `park|disabled`, `unpark|enabled` (2026-10-23 probe): dashboard "Not Parked (At Home)", tracking Off.
* To check parking, read the `Parking:` line on `index.htm`, or the `:GU#` status letter: `P` = parked, `p` = not parked ([OnStep command reference](https://onstep.groups.io/g/main/wiki/23755)).

---

## 6. Project Directory Contents

* `index.html` — The new modern, mobile-friendly, dark-mode touch web controller.
* `raw_stock_ui/index.htm` — The original stock status webpage from the mount.
* `raw_stock_ui/control.htm` — The original stock control webpage from the mount.
* `raw_stock_ui/control.txt` — The original stock telemetry dump.
* `API_AND_HARDWARE_DISCOVERY.md` — This documentation file.
* `README.md` — Quick start guide.
