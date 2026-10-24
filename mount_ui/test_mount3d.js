#!/usr/bin/env node
// Checks for mount3d.js: the pointing math against the standard alt/az formula, the pier side
// rule, and a render into a stub canvas. Run: node mount_ui/test_mount3d.js
'use strict';
const { mountPose, altAzPose, horizontal, altAz, MountView } = require('./mount3d.js');

const DEG = Math.PI / 180;
let failures = 0;
function check(name, cond, detail = '') {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (!cond && detail ? '  ' + detail : ''));
  if (!cond) failures++;
}

// Standard conversion from hour angle and declination to altitude and azimuth.
function expectedAltAz(haHours, decDeg, latDeg) {
  const H = haHours * 15 * DEG;
  const d = decDeg * DEG;
  const f = latDeg * DEG;
  const alt = Math.asin(Math.sin(f) * Math.sin(d) + Math.cos(f) * Math.cos(d) * Math.cos(H));
  const az = Math.atan2(-Math.cos(d) * Math.sin(H), Math.sin(d) * Math.cos(f) - Math.cos(d) * Math.cos(H) * Math.sin(f));
  return { alt: alt / DEG, az: ((az / DEG) + 360) % 360 };
}
const angleGap = (a, b) => Math.abs(((a - b + 540) % 360) - 180);
const dotp = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

// 1. Where the tube points matches alt/az for many positions and latitudes, on both pier sides.
let worst = 0;
let seed = 7;
const rand = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
for (let i = 0; i < 2000; i++) {
  const ha = rand() * 24 - 12;
  const dec = rand() * 170 - 85;
  const lat = rand() * 120 - 60;
  const pier = [1, -1, null][i % 3];
  const pose = mountPose(ha, dec, lat, pier);
  const got = altAz(pose.d);
  const want = expectedAltAz(ha, dec, lat);
  let err = Math.abs(got.alt - want.alt);
  if (Math.abs(want.alt) < 89) err = Math.max(err, angleGap(got.az, want.az) * Math.cos(want.alt * DEG));
  worst = Math.max(worst, err);
}
check('tube direction matches alt/az (2000 random poses)', worst < 1e-6, 'worst error ' + worst + ' deg');

// 2. Known positions at this site (latitude +1.33).
const lat = 1 + 20 / 60;
let a = altAz(mountPose(0, 90, lat).d);
check('Dec +90 points at the pole: altitude = latitude, due north', Math.abs(a.alt - lat) < 1e-9 && angleGap(a.az, 0) < 1e-6, JSON.stringify(a));
a = altAz(mountPose(0, 0, lat).d);
check('HA 0, Dec 0 is on the meridian, 90 - latitude high, due south', Math.abs(a.alt - (90 - lat)) < 1e-9 && angleGap(a.az, 180) < 1e-6, JSON.stringify(a));
a = altAz(mountPose(6, 0, lat).d);
check('HA +6h, Dec 0 is the west point of the horizon', Math.abs(a.alt) < 1e-9 && angleGap(a.az, 270) < 1e-6, JSON.stringify(a));
a = altAz(mountPose(-6, 0, lat).d);
check('HA -6h, Dec 0 is the east point of the horizon', Math.abs(a.alt) < 1e-9 && angleGap(a.az, 90) < 1e-6, JSON.stringify(a));

// 3. Axes stay perpendicular, and the default pier side keeps the tube above the RA axis.
let ok = true;
for (let i = 0; i < 500; i++) {
  const pose = mountPose(rand() * 24 - 12, rand() * 170 - 85, rand() * 120 - 60);
  if (Math.abs(dotp(pose.u, pose.d)) > 1e-9 || Math.abs(dotp(pose.u, pose.p)) > 1e-9 || pose.u[2] < -1e-12) ok = false;
}
check('Dec axis is perpendicular to the tube and the polar axis; tube stays above by default', ok);
const east = mountPose(2, 30, lat, 1);
const west = mountPose(2, 30, lat, -1);
check('pier side flips the Dec axis but not the pointing',
  Math.abs(dotp(east.u, west.u) + 1) < 1e-9 && Math.abs(dotp(east.d, west.d) - 1) < 1e-9);

// 3b. Alt-Az mode: same pointing as the equatorial pose, but the first axis stands vertical.
let altazWorst = 0;
let vertical = true;
for (let i = 0; i < 500; i++) {
  const ha = rand() * 24 - 12;
  const dec = rand() * 170 - 85;
  const la = rand() * 120 - 60;
  const h = horizontal(ha, dec, la);
  const want = expectedAltAz(ha, dec, la);
  altazWorst = Math.max(altazWorst, Math.abs(h.alt - want.alt), Math.abs(want.alt) < 89 ? angleGap(h.az, want.az) : 0);
  const pose = altAzPose(h.alt, h.az);
  const got = altAz(pose.d);
  altazWorst = Math.max(altazWorst, Math.abs(got.alt - h.alt), Math.abs(h.alt) < 89 ? angleGap(got.az, h.az) : 0);
  if (Math.abs(pose.p[2] - 1) > 1e-9) vertical = false;
}
check('Alt-Az mode points the same way, with the first axis vertical', altazWorst < 1e-6 && vertical, 'worst ' + altazWorst);

// 4. Render into a stub canvas: no exceptions, faces drawn, and the picture changes with the pose.
function stubCanvas() {
  const calls = [];
  const ctx = new Proxy({}, {
    get: (target, prop) => (prop in target ? target[prop] : (...args) => { calls.push([prop, ...args]); }),
    set: (target, prop, value) => { target[prop] = value; return true; },
  });
  return { canvas: { width: 600, height: 400, clientWidth: 600, clientHeight: 400, getContext: () => ctx }, calls };
}
const s1 = stubCanvas();
const view = new MountView(s1.canvas, { interactive: false });
const faces = view.render();
check('renders without a position yet', faces > 50, 'faces drawn ' + faces);
view.setPose({ ha: -2, dec: 20, lat, pier: null });
const firstMoves = s1.calls.filter((c) => c[0] === 'moveTo').slice(-40).map((c) => c.slice(1).join(',')).join(';');
view.setPose({ ha: 3, dec: 60, lat, pier: null });
const secondMoves = s1.calls.filter((c) => c[0] === 'moveTo').slice(-40).map((c) => c.slice(1).join(',')).join(';');
check('a new pose changes the drawing', firstMoves !== secondMoves);
view.setPose({ ha: NaN, dec: 20, lat });
check('a bad reading is ignored', view.pose.ha === 3);
view.setMoving(['e']);
check('holding east highlights the RA axis without errors', view.moving.has('e'));
view.setPose({ ha: 1, dec: 30, lat, mode: 'altaz' });
check('renders in Alt-Az mode', view.pose.mode === 'altaz' && view.render() > 50);

console.log(failures ? `\n${failures} failed` : '\nall checks passed');
process.exit(failures ? 1 : 0);
