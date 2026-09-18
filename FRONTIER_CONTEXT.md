# SYSTEM BRIEFING & CONTEXT: UMi 17 Lite Web Controller Project

> **Target Audience:** Frontier LLM / AI Coding Agents  
> **Repository:** `/Users/zhunhao/Documents/Projects/mount-web-ui`  
> **Status:** Reverse-engineered, verified via live terminal telemetry, git-initialized.

---

## 1. System & Hardware Identification
* **Mount Model:** UMi 17 Lite (Harmonic drive / strain wave gear equatorial mount).
* **Vendor:** Proxisky (formerly MeowAstro).
* **Controller SoC:** Espressif ESP32.
* **Firmware:** `MeowAstro WiFi Server 2.1v` running on `OnStep 4.21e` core.
* **Firmware Mode:** Compiled with `OPERATIONAL_MODE = WIFI_ACCESS_POINT` (AP-Only).

---

## 2. Network Topology & Interface Matrix
* **Layer 2 / 3:**
  * Mount functions as an 802.11 b/g/n SoftAP (SSID default: `UMi_xxxx` / `OnStep`).
  * Mount IP (Gateway & DNS): `192.168.0.1`.
  * Client IP leased via DHCP: `192.168.0.100` (`/24` subnet, mask `255.255.255.0`).
  * Broadcast Address: `192.168.0.255`.
* **Port Verification Results:**
  * `TCP:80` (HTTP): **OPEN / ACTIVE** (Chunked HTTP/1.1 web server).
  * `TCP:2000` (Celestron SkyPortal AUX): **CLOSED / TIMEOUT** (Celestron protocol not used).
  * `TCP:9998 / 9999` (OnStep LX200 Raw Sockets): **CLOSED / UNREACHABLE** (Disabled in vendor build).
  * `TCP:3000` (CPWI): **CLOSED / UNREACHABLE**.
* **Key Finding:** All hardware control must be executed through **HTTP Port 80**.

---

## 3. Reverse-Engineered HTTP Protocol & Command Spec

### 3.1. Command Dispatcher
* **Method:** `GET`
* **Endpoint:** `http://192.168.0.1/controlA.txt?<key>=<value>&x=<unix_timestamp>`
* **CORS Note:** Mount does not emit CORS headers. Client-side fetch must use `{ mode: 'no-cors' }` or Image ping fallback (`new Image().src = ...`).

### 3.2. Parameter Matrix: `key=dr` (Drive / Direction / Rate / Operation)

```
+------------------+---------------+-----------------------------------------------+
| Action Category  | Value         | Description                                   |
+------------------+---------------+-----------------------------------------------+
| Emergency Halt   | qq            | Immediate hard brake on all stepper channels  |
+------------------+---------------+-----------------------------------------------+
| Manual Slewing   | n1 / n0       | North / Dec+ (Start on down / Stop on release)|
| (Press-to-move,  | s1 / s0       | South / Dec- (Start on down / Stop on release)|
| Release-to-halt) | e1 / e0       | East  / RA+  (Start on down / Stop on release)|
|                  | w1 / w0       | West  / RA-  (Start on down / Stop on release)|
+------------------+---------------+-----------------------------------------------+
| Slew Rates       | R0            | 0.25x (Fine Guide)                            |
|                  | R1            | 0.5x  (Standard Guide)                        |
|                  | R2            | 1.0x  (Centering)                             |
|                  | R5            | 4.0x  (Fast Centering)                        |
|                  | R6            | 40.0x (Find Rate)                             |
|                  | R7            | 60.0x (High-Speed Find)                       |
|                  | R8            | MAX (~5.8 deg/sec slew)                       |
+------------------+---------------+-----------------------------------------------+
| Tracking State   | T1            | Tracking ON                                   |
|                  | T0            | Tracking OFF                                  |
|                  | Ts            | Sidereal Rate                                 |
|                  | Tl            | Lunar Rate                                    |
|                  | Th            | Solar Rate                                    |
+------------------+---------------+-----------------------------------------------+
| Mount Operations | pk            | Park mount to predefined coordinates          |
|                  | pu            | Unpark mount                                  |
|                  | qh            | Find Home (optical/hall sensor index)         |
|                  | qr            | Home Reset (override current pos as Home)     |
|                  | qc            | Continue Goto (resume paused transit)         |
|                  | sy            | Sync current target to mount orientation      |
+------------------+---------------+-----------------------------------------------+
```

### 3.3. Telemetry Ingestion
1. **Button & Operational States:**
   * Endpoint: `GET http://192.168.0.1/control.txt?nocache=<rand>`
   * Format: Multi-line key-value pairs separated by pipe (`|`):
     ```text
     trk_on|disabled      <-- 'disabled' means tracking is currently ACTIVE
     trk_off|enabled     <-- 'enabled' button means it can be clicked to turn off
     park|enabled        <-- Mount is currently UNPARKED
     unpark|disabled
     c_goto|disabled
     alg1|disabled
     alg2|disabled
     alg3|disabled
     alga|disabled
     rpa|enabled
     ```
2. **Coordinates & Astronomical Telemetry:**
   * Endpoint: `GET http://192.168.0.1/index.htm`
   * Format: Server-side rendered HTML refreshed every 5s containing:
     * Current RA ($\alpha$) & Dec ($\delta$)
     * Pier side state (`East` / `West`), Meridian flip configuration
     * Tracking frequency (`60.095 Hz`), Site Lat/Long, LST

---

## 4. Vendor Constraints & Root Causes

### 4.1. Station (STA) Mode Missing in `/wifi.htm`
* **Symptom:** `/wifi.htm` only exposes AP SSID and Password fields; no fields exist to join a home Wi-Fi network.
* **Root Cause:** In OnStep `SmartWebServer/Config.h`, Proxisky compiled the binary with `OPERATIONAL_MODE WIFI_ACCESS_POINT`. Vendors do this to eliminate support liability when users enter typos in home Wi-Fi credentials and brick remote connectivity.
* **Workarounds:**
  1. *Hardware Bridge (Preferred):* GL.iNet travel router in WISP/Repeater mode bridging mount AP to home LAN.
  2. *Firmware Recompile:* Flash ESP32 via USB with `WIFI_BOTH` (high risk: overwrites factory motor/gear calibration if LittleFS/NVS is erased without backup).

---

## 5. Architectural Motivation: Why a Custom Web UI?

### 5.1. The Failure of Existing Solutions
1. **MeowGoto / UMi Mount App:**
   * Closed-source, phone-only, awkward localization, frequent connection drops.
   * Poor touch ergonomics for fine manual guiding in cold weather.
2. **Stock OnStep Web Interface (`192.168.0.1`):**
   * Designed for desktop browsers in the 1990s; non-responsive.
   * Buttons are 20px wide with tiny hitboxes, impossible to operate with thumbs.
   * Lacks modern mobile touch event handling (`pointerdown` / `pointerup`).
   * No dark-adapted night mode (blinds the astronomer in the field).

### 5.2. Requirements for the Modern Web Controller
* **Architecture:** Zero-dependency, single-file HTML5/CSS3/ES6 application.
* **Offline Resilience:** Must function with zero internet access (since mount AP provides no WAN).
* **Night Ergonomics:** Strict OLED monochrome crimson red on pure black (`#0a0a0c`).
* **Virtual Hand Controller (D-Pad):**
  * Uses `PointerEvents` (`pointerdown`, `pointerup`, `pointercancel`, `pointerleave`) to guarantee immediate halt on release.
  * Haptic vibration feedback via `navigator.vibrate`.
  * Keyboard arrow-key mapping for laptop control ($\uparrow, \downarrow, \leftarrow, \rightarrow, \text{Space} = \text{STOP}$).
* **Deployment:** Installable as a progressive web app (PWA) via browser "Add to Home Screen".
