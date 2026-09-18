# UMi 17 Lite Modern Web Controller

A clean, responsive, dark-mode Web UI designed specifically to replace the clunky UMi Mount / MeowGoto mobile apps for the **UMi 17 Lite** telescope mount.

---

## Features

- **Astro Night Mode:** High-contrast OLED pure black and crimson red to preserve night vision.
- **Responsive D-Pad:** Smooth press-and-hold directional slewing (North, South, East, West) with instant halt on finger release.
- **Speed Selector:** 1-tap rates from 0.25x fine guiding to MAX slew speed.
- **Prominent Emergency STOP:** Impossible-to-miss red button at the top.
- **Tracking & Mount Actions:** Sidereal, Lunar, Solar tracking toggles, plus Park, Unpark, Find Home, and Sync.
- **Laptop Keyboard Shortcuts:** Use Arrow Keys to slew and Spacebar to Emergency Stop.
- **Phone Haptic Feedback:** Vibrates on button press for tactile feedback in the dark.
- **Zero Dependencies:** Single-file HTML5/CSS/JS, no build step, no npm, runs offline.

---

## How to Use

### On Mac / Laptop
1. Connect your Wi-Fi to the mount's network.
2. Double-click `index.html` (or run `open index.html`).
3. The controller will open in your default browser.

### On iPhone / iPad / Android Phone (Field Use Without a PC)
1. **AirDrop** or send `index.html` to your phone.
2. Open it in **Safari** (iOS) or **Chrome** (Android).
3. Tap **Share $\rightarrow$ Add to Home Screen**.
4. Whenever you're in the field, connect to the mount's Wi-Fi, tap the home screen icon, and control your mount directly!

---

## Documentation
See `API_AND_HARDWARE_DISCOVERY.md` for the full HTTP API, query parameters, and telemetry specifications discovered from the mount.
