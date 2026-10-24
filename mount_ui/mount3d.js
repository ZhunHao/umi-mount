/* 3D view of the UMi 17 Lite for the control page.
 *
 * Geometry is a hand-built model matched to photos of the mount: black RA housing with a red
 * end cap on a red latitude base, black Dec housing, dovetail saddle with a red knob, and a
 * small white refractor with a camera. It is not a scan.
 *
 * The pose comes from the mount's own readings (hour angle, declination, site latitude), so the
 * view shows where the mount believes the tube points. Plain Canvas 2D, no libraries, so the
 * page keeps working offline.
 */
(function (root) {
  'use strict';

  const DEG = Math.PI / 180;
  const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const mul = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const unit = (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };

  // ---- Kinematics ----------------------------------------------------------------------------
  // World frame: x east, y north, z up, in centimetres.
  // Equatorial frame for latitude lat, in world coordinates:
  //   z: north celestial pole, x: where the meridian crosses the equator, y: east.
  function eqFrame(latDeg) {
    const f = latDeg * DEG;
    return { x: [0, -Math.sin(f), Math.cos(f)], y: [1, 0, 0], z: [0, Math.cos(f), Math.sin(f)] };
  }

  /* Pose of a German equatorial mount.
   *   haHours: hour angle, west positive. decDeg: declination. latDeg: site latitude.
   *   pierSign: +1 tube east of the pier, -1 tube west of it, null to keep the tube above the axis.
   * Returns unit vectors in world coordinates:
   *   p polar axis, d where the tube points, u Dec axis toward the tube side, s the side used.
   */
  function mountPose(haHours, decDeg, latDeg, pierSign = null) {
    const F = eqFrame(latDeg);
    const h = haHours * 15 * DEG;
    const dl = decDeg * DEG;
    const inEq = (v) => add(add(mul(F.x, v[0]), mul(F.y, v[1])), mul(F.z, v[2]));
    const p = F.z;
    // The Dec axis turns with the RA axis and always lies in the equatorial plane.
    const m = inEq([Math.cos(h), -Math.sin(h), 0]);
    const u0 = inEq([Math.sin(h), Math.cos(h), 0]);
    const d = unit(add(mul(m, Math.cos(dl)), mul(p, Math.sin(dl))));
    let s = pierSign;
    if (s !== 1 && s !== -1) s = u0[2] >= 0 ? 1 : -1;
    return { p, d, u: mul(u0, s), s };
  }

  // Hour angle and declination to altitude and azimuth (degrees, azimuth from north through east).
  function horizontal(haHours, decDeg, latDeg) {
    const H = haHours * 15 * DEG;
    const d = decDeg * DEG;
    const f = latDeg * DEG;
    const alt = Math.asin(Math.max(-1, Math.min(1, Math.sin(f) * Math.sin(d) + Math.cos(f) * Math.cos(d) * Math.cos(H))));
    const az = Math.atan2(-Math.cos(d) * Math.sin(H), Math.sin(d) * Math.cos(f) - Math.cos(d) * Math.cos(H) * Math.sin(f));
    return { alt: alt / DEG, az: ((az / DEG) + 360) % 360 };
  }

  /* Pose of the mount in Alt-Az mode: the first axis stands vertical and turns in azimuth, the
   * second tilts in altitude. That is the equatorial geometry at latitude 90, with the hour angle
   * standing in for azimuth (az = HA - 180 degrees there). */
  function altAzPose(altDeg, azDeg) {
    return mountPose((azDeg + 180) / 15, altDeg, 90, null);
  }

  // Altitude and azimuth (degrees, azimuth from north through east) of a world direction.
  function altAz(v) {
    return { alt: Math.asin(Math.max(-1, Math.min(1, v[2]))) / DEG, az: ((Math.atan2(v[0], v[1]) / DEG) + 360) % 360 };
  }

  // ---- Mesh building ------------------------------------------------------------------------
  // A frame is an origin and a right-handed set of unit axes a, b, c.
  const toWorld = (fr, v) => add(fr.o, add(add(mul(fr.a, v[0]), mul(fr.b, v[1])), mul(fr.c, v[2])));

  function frameAlong(o, c, hint) {
    c = unit(c);
    let ref = hint || (Math.abs(c[2]) < 0.9 ? [0, 0, 1] : [1, 0, 0]);
    if (Math.abs(dot(unit(ref), c)) > 0.98) ref = Math.abs(c[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0];
    const a = unit(cross(ref, c));
    return { o, a, b: cross(c, a), c };
  }

  // Cylinder along the frame's c axis from z0 to z1. Faces wind outward.
  function cylinder(mesh, fr, r, z0, z1, n, side, cap0 = side, cap1 = side, part = null) {
    const base = mesh.verts.length;
    for (let i = 0; i < n; i++) {
      const t = (i / n) * 2 * Math.PI;
      const x = Math.cos(t) * r;
      const y = Math.sin(t) * r;
      mesh.verts.push(toWorld(fr, [x, y, z0]), toWorld(fr, [x, y, z1]));
    }
    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n;
      mesh.faces.push({ idx: [base + 2 * i, base + 2 * j, base + 2 * j + 1, base + 2 * i + 1], color: side, part, smooth: true });
    }
    const ring0 = [];
    const ring1 = [];
    for (let i = 0; i < n; i++) { ring0.push(base + 2 * i); ring1.push(base + 2 * i + 1); }
    mesh.faces.push({ idx: ring0.reverse(), color: cap0, part });
    mesh.faces.push({ idx: ring1, color: cap1, part });
  }

  // Box centred on the frame origin with half sizes along a, b, c. Faces wind outward.
  function box(mesh, fr, hx, hy, hz, color, part = null) {
    const b = mesh.verts.length;
    for (const z of [-hz, hz]) for (const y of [-hy, hy]) for (const x of [-hx, hx]) mesh.verts.push(toWorld(fr, [x, y, z]));
    for (const q of [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]) {
      mesh.faces.push({ idx: q.map((k) => b + k), color, part });
    }
  }

  // ---- The mount ----------------------------------------------------------------------------
  const C = {
    body: [38, 38, 42],      // black anodised housings
    bodyEnd: [58, 58, 64],
    red: [196, 64, 40],      // UMi / William Optics red
    steel: [150, 150, 158],
    leg: [70, 70, 76],
    tube: [226, 226, 232],   // white refractor
    shield: [30, 30, 34],
    lens: [40, 60, 90],
    camera: [44, 44, 50],
  };
  const H = 64;              // height of the latitude base top above the ground (short pier)

  function buildMount(pose) {
    const mesh = { verts: [], faces: [] };
    const up = [0, 0, 1];

    // Tripod: centre column and three legs, one pointing north.
    cylinder(mesh, frameAlong([0, 0, 40], up), 3.2, 0, H - 40, 14, C.leg, C.leg, C.leg);
    for (const deg of [0, 120, 240]) {
      const a = deg * DEG;
      const top = [Math.sin(a) * 4, Math.cos(a) * 4, 46];
      const foot = [Math.sin(a) * 44, Math.cos(a) * 44, 0];
      const len = Math.hypot(...sub(foot, top));
      box(mesh, frameAlong(mul(add(top, foot), 0.5), sub(foot, top)), 1.3, 1.3, len / 2, C.leg);
    }

    // Latitude base: red block with a steel clamp ring.
    cylinder(mesh, frameAlong([0, 0, H - 4], up), 5.6, 0, 2, 18, C.steel, C.steel, C.steel);
    box(mesh, frameAlong([0, 0, H + 2.5], up, [1, 0, 0]), 4.6, 5.2, 3.5, C.red);

    // RA housing along the polar axis, red cap on the lower end.
    const pivot = [0, 0, H + 11];
    cylinder(mesh, frameAlong(pivot, pose.p), 5.6, -7, 6, 22, C.body, C.red, C.bodyEnd, 'ra');

    // Dec housing on the upper end of the RA housing, along the Dec axis.
    const head = add(pivot, mul(pose.p, 6 + 5.2));
    cylinder(mesh, frameAlong(head, pose.u), 5.2, -5, 7, 22, C.body, C.bodyEnd, C.body, 'dec');

    // Saddle on the tube side, long axis along the tube, with the red clamp knob.
    const saddle = add(head, mul(pose.u, 7 + 1.4));
    const side = cross(pose.u, pose.d);
    box(mesh, { o: saddle, a: pose.d, b: side, c: pose.u }, 8, 3.4, 1.4, C.shield, 'dec');
    cylinder(mesh, frameAlong(add(saddle, mul(side, 3.4)), side), 1.3, 0, 2.2, 12, C.red, C.red, C.red, 'dec');

    // Refractor: white tube, black dew shield, dark lens at the front, camera at the back.
    const tubeAt = add(saddle, mul(pose.u, 1.4 + 4.8));
    const tf = frameAlong(tubeAt, pose.d);
    cylinder(mesh, tf, 4.6, -16, 12, 20, C.tube, C.tube, C.tube, 'tube');
    cylinder(mesh, tf, 5.0, 12, 22, 20, C.shield, C.shield, C.lens, 'tube');
    cylinder(mesh, tf, 3.8, -25, -16, 16, C.camera, C.camera, C.camera, 'tube');
    for (const z of [-8, 5]) cylinder(mesh, tf, 5.0, z, z + 1.6, 20, C.shield, C.shield, C.shield, 'tube');

    return { mesh, pivot, head, front: toWorld(tf, [0, 0, 22]) };
  }

  // ---- Renderer -----------------------------------------------------------------------------
  const LIGHT = unit([-0.35, -0.55, 0.75]);
  // Look at the mount head from east-south-east, a little above, so the tube is seen side-on.
  const TARGET = [0, 0, H + 14];
  const DEFAULT_VIEW = { az: 118, el: 16, dist: 150 };

  class MountView {
    constructor(canvas, opts = {}) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      this.view = { ...DEFAULT_VIEW };
      this.pose = { ha: 0, dec: 90, lat: 0, pier: null, mode: 'eq' };
      this.moving = new Set();
      this.known = false;
      this.colors = { ink: '#ffffff', label: '#8e8e98', hair: '#2a2a2f', highlight: [255, 255, 255], ...opts.colors };
      if (opts.interactive !== false && canvas.addEventListener) this._bindInput();
    }

    // mode 'eq' (German equatorial) or 'altaz' (first axis vertical).
    setPose({ ha, dec, lat, pier = null, mode = 'eq' }) {
      if ([ha, dec, lat].some((v) => typeof v !== 'number' || !isFinite(v))) return;
      this.pose = { ha, dec, lat, pier, mode: mode === 'altaz' ? 'altaz' : 'eq' };
      this.known = true;
      this.render();
    }

    setMoving(dirs) { this.moving = new Set(dirs); this.render(); }

    resetView() { this.view = { ...DEFAULT_VIEW }; this.render(); }

    _bindInput() {
      let drag = null;
      const c = this.canvas;
      c.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY }; c.setPointerCapture && c.setPointerCapture(e.pointerId); });
      c.addEventListener('pointermove', (e) => {
        if (!drag) return;
        this.view.az -= (e.clientX - drag.x) * 0.5;
        this.view.el = Math.max(-5, Math.min(85, this.view.el + (e.clientY - drag.y) * 0.35));
        drag = { x: e.clientX, y: e.clientY };
        this.render();
      });
      const end = () => { drag = null; };
      c.addEventListener('pointerup', end);
      c.addEventListener('pointercancel', end);
      c.addEventListener('wheel', (e) => {
        e.preventDefault();
        this.view.dist = Math.max(70, Math.min(420, this.view.dist * Math.exp(e.deltaY * 0.001)));
        this.render();
      }, { passive: false });
      c.addEventListener('dblclick', () => this.resetView());
    }

    _camera(width, height) {
      const az = this.view.az * DEG;
      const el = this.view.el * DEG;
      const eye = add(TARGET, mul([Math.cos(el) * Math.sin(az), Math.cos(el) * Math.cos(az), Math.sin(el)], this.view.dist));
      const fwd = unit(sub(TARGET, eye));
      const right = unit(cross(fwd, [0, 0, 1]));
      const upv = cross(right, fwd);
      const focal = Math.min(width, height) * 1.55;
      const project = (pt) => {
        const v = sub(pt, eye);
        const z = dot(v, fwd);
        return [width / 2 + (dot(v, right) / z) * focal, height * 0.5 - (dot(v, upv) / z) * focal, z];
      };
      return { eye, project };
    }

    render() {
      const c = this.canvas;
      const ctx = this.ctx;
      const dpr = (typeof window !== 'undefined' && window.devicePixelRatio) || 1;
      const width = c.clientWidth || c.width;
      const height = c.clientHeight || c.height;
      if (c.width !== Math.round(width * dpr) || c.height !== Math.round(height * dpr)) {
        c.width = Math.round(width * dpr);
        c.height = Math.round(height * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);

      const cam = this._camera(width, height);
      this._drawGround(ctx, cam);

      const altaz = this.pose.mode === 'altaz';
      const pose = altaz
        ? (({ alt, az }) => altAzPose(alt, az))(horizontal(this.pose.ha, this.pose.dec, this.pose.lat))
        : mountPose(this.pose.ha, this.pose.dec, this.pose.lat, this.pose.pier);
      const { mesh, pivot, front } = buildMount(pose);
      const lit = new Set();
      if (this.moving.has('e') || this.moving.has('w')) lit.add('ra');
      if (this.moving.has('n') || this.moving.has('s')) lit.add('dec');

      // Painter's algorithm: drop faces turned away, then draw the rest far to near.
      const pts = mesh.verts.map(cam.project);
      const drawn = [];
      for (const f of mesh.faces) {
        const v0 = mesh.verts[f.idx[0]];
        const n = unit(cross(sub(mesh.verts[f.idx[1]], v0), sub(mesh.verts[f.idx[2]], v0)));
        let centre = [0, 0, 0];
        for (const k of f.idx) centre = add(centre, mesh.verts[k]);
        centre = mul(centre, 1 / f.idx.length);
        const toEye = unit(sub(cam.eye, centre));
        if (dot(n, toEye) <= 0) continue;
        if (f.idx.some((k) => pts[k][2] <= 1)) continue;
        const depth = f.idx.reduce((sum, k) => sum + pts[k][2], 0) / f.idx.length;
        const shade = 0.32 + 0.55 * Math.max(0, dot(n, LIGHT)) + 0.18 * Math.max(0, dot(n, toEye));
        let col = f.color.map((x) => Math.min(255, Math.round(x * shade)));
        if (f.part && lit.has(f.part)) col = col.map((x, i) => Math.round(x * 0.45 + this.colors.highlight[i] * 0.55 * shade));
        drawn.push({ idx: f.idx, depth, fill: `rgb(${col[0]},${col[1]},${col[2]})` });
      }
      drawn.sort((a, b) => b.depth - a.depth);
      ctx.lineJoin = 'round';
      ctx.lineWidth = 0.75;
      for (const f of drawn) {
        ctx.beginPath();
        f.idx.forEach((k, i) => (i ? ctx.lineTo(pts[k][0], pts[k][1]) : ctx.moveTo(pts[k][0], pts[k][1])));
        ctx.closePath();
        ctx.fillStyle = f.fill;
        ctx.strokeStyle = f.fill;
        ctx.fill();
        ctx.stroke();
      }

      // Overlays: polar axis and the line of sight, drawn on top so they are always readable.
      // At the pole the tube lies along the polar axis; label only the line of sight then.
      const alongAxis = Math.abs(dot(pose.p, pose.d)) > 0.97;
      this._dashed(ctx, cam, pivot, add(pivot, mul(pose.p, 60)), this.colors.label, alongAxis ? '' : (altaz ? 'Azimuth axis' : 'Polar axis'));
      this._dashed(ctx, cam, front, add(front, mul(pose.d, 90)), this.colors.ink, 'Line of sight');

      if (!this.known) {
        ctx.fillStyle = this.colors.label;
        ctx.font = '13px sans-serif';
        ctx.fillText('Waiting for the mount position', 12, 22);
      }
      return drawn.length;
    }

    _dashed(ctx, cam, a, b, color, label) {
      const pa = cam.project(a);
      const pb = cam.project(b);
      if (pa[2] <= 1 || pb[2] <= 1) return;
      ctx.save();
      ctx.setLineDash([5, 5]);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.25;
      ctx.beginPath();
      ctx.moveTo(pa[0], pa[1]);
      ctx.lineTo(pb[0], pb[1]);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = color;
      ctx.font = '12px sans-serif';
      if (label) {
        // Keep the label inside the canvas: flip it to the left of the line end near the right edge.
        const metrics = ctx.measureText && ctx.measureText(label);
        const w = (metrics && metrics.width) || 60;
        const width = this.canvas.clientWidth || this.canvas.width;
        const height = this.canvas.clientHeight || this.canvas.height;
        let x = pb[0] + 6;
        if (x + w > width - 6) x = pb[0] - 6 - w;
        const y = Math.max(14, Math.min(height - 6, pb[1] + 4));
        ctx.fillText(label, Math.max(6, x), y);
      }
      ctx.restore();
    }

    _drawGround(ctx, cam) {
      // Ground ring and compass points around the tripod.
      ctx.save();
      ctx.strokeStyle = this.colors.hair;
      ctx.lineWidth = 1;
      for (const r of [30, 55]) {
        ctx.beginPath();
        for (let i = 0; i <= 64; i++) {
          const t = (i / 64) * 2 * Math.PI;
          const q = cam.project([Math.sin(t) * r, Math.cos(t) * r, 0]);
          if (i) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]);
        }
        ctx.stroke();
      }
      ctx.fillStyle = this.colors.label;
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      for (const [name, x, y] of [['N', 0, 66], ['E', 66, 0], ['S', 0, -66], ['W', -66, 0]]) {
        const q = cam.project([x, y, 0]);
        if (q[2] > 1) ctx.fillText(name, q[0], q[1] + 4);
      }
      ctx.restore();
    }
  }

  const api = { mountPose, altAzPose, horizontal, altAz, eqFrame, buildMount, MountView };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else Object.assign(root, api);
})(typeof window !== 'undefined' ? window : globalThis);
