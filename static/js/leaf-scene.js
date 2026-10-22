/**
 * AgroDoktor landing hero: 3D leaf being scanned by the AI.
 * A procedurally textured, curved leaf is swept by a scanner bar; surface sample
 * points light up under the beam, disease spots get marked and the readout
 * panel fills in with the diagnosis. Respects prefers-reduced-motion.
 */

(function () {
  'use strict';

  const root = document.querySelector('[data-leaf-scene]');
  if (!root || !window.THREE) return;

  const THREE = window.THREE;
  const canvasHost = root.querySelector('[data-leaf-canvas]');
  const labelLayer = root.querySelector('[data-leaf-labels]');
  const readout = document.querySelector('[data-leaf-readout]');
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Leaf lives in local coordinates x in [-1.1, 1.1], y in [-2, 2] (tip at +2).
  const W = 2.2;
  const H = 4;
  const TEX_W = 512;
  const TEX_H = 1024;

  // Disease spots in leaf coordinates, with the label shown once detected.
  const SPOTS = [
    { x: 0.42, y: 0.75, r: 0.2, label: "Qo'ng'ir dog'" },
    { x: -0.38, y: -0.15, r: 0.26, label: "Nekroz o'chog'i" },
    { x: 0.3, y: -0.95, r: 0.15, label: "Sarg'ayish" },
  ];

  function surfaceZ(x, y, t) {
    const fold = 0.32 * x * x;
    const arch = -0.24 * (y / 2) * (y / 2);
    const ripple = 0.035 * Math.sin(x * 5 + y * 2.2 + t * 0.9);
    return fold + arch + ripple;
  }

  function toCanvas(x, y) {
    return [((x + W / 2) / W) * TEX_W, (1 - (y + H / 2) / H) * TEX_H];
  }

  function traceLeaf(ctx) {
    const p = (x, y) => toCanvas(x, y);
    ctx.beginPath();
    ctx.moveTo(...p(0, -1.85));
    ctx.bezierCurveTo(...p(0.95, -1.55), ...p(1.1, 0.4), ...p(0, 1.98));
    ctx.bezierCurveTo(...p(-1.1, 0.4), ...p(-0.95, -1.55), ...p(0, -1.85));
    ctx.closePath();
  }

  function buildLeafTexture() {
    const c = document.createElement('canvas');
    c.width = TEX_W;
    c.height = TEX_H;
    const ctx = c.getContext('2d');

    traceLeaf(ctx);
    ctx.save();
    ctx.clip();

    const g = ctx.createLinearGradient(0, 0, TEX_W, TEX_H);
    g.addColorStop(0, '#5f9a3e');
    g.addColorStop(0.55, '#457f33');
    g.addColorStop(1, '#2c5f2a');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, TEX_W, TEX_H);

    // Subtle cell texture
    for (let i = 0; i < 2600; i++) {
      ctx.fillStyle = `rgba(${Math.random() < 0.5 ? '20,60,20' : '200,235,150'},0.05)`;
      ctx.beginPath();
      ctx.arc(Math.random() * TEX_W, Math.random() * TEX_H, 2 + Math.random() * 5, 0, Math.PI * 2);
      ctx.fill();
    }

    // Side veins
    ctx.strokeStyle = 'rgba(220,245,190,0.55)';
    ctx.lineCap = 'round';
    for (let i = 0; i < 9; i++) {
      const y = -1.5 + i * 0.38;
      [-1, 1].forEach((side) => {
        const [x0, y0] = toCanvas(0, y);
        const [x1, y1] = toCanvas(side * 0.45, y + 0.42);
        const [x2, y2] = toCanvas(side * 0.95, y + 0.7);
        ctx.lineWidth = 3.2 - i * 0.18;
        ctx.beginPath();
        ctx.moveTo(x0, y0);
        ctx.quadraticCurveTo(x1, y1, x2, y2);
        ctx.stroke();
      });
    }

    // Midrib
    const [mx0, my0] = toCanvas(0, -1.85);
    const [mx1, my1] = toCanvas(0, 1.9);
    ctx.strokeStyle = 'rgba(232,250,205,0.85)';
    ctx.lineWidth = 7;
    ctx.beginPath();
    ctx.moveTo(mx0, my0);
    ctx.lineTo(mx1, my1);
    ctx.stroke();

    // Disease spots: yellow halo, brown necrotic centre, concentric ring
    SPOTS.forEach((s) => {
      const [cx, cy] = toCanvas(s.x, s.y);
      const rad = (s.r / W) * TEX_W;
      const halo = ctx.createRadialGradient(cx, cy, rad * 0.3, cx, cy, rad * 1.9);
      halo.addColorStop(0, 'rgba(214,170,48,0.9)');
      halo.addColorStop(1, 'rgba(214,170,48,0)');
      ctx.fillStyle = halo;
      ctx.beginPath();
      ctx.arc(cx, cy, rad * 1.9, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#6b3a1e';
      ctx.beginPath();
      ctx.ellipse(cx, cy, rad, rad * 0.85, 0.4, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = 'rgba(40,20,10,0.6)';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.ellipse(cx, cy, rad * 0.55, rad * 0.45, 0.4, 0, Math.PI * 2);
      ctx.stroke();
    });

    // Darker rim
    ctx.restore();
    traceLeaf(ctx);
    ctx.strokeStyle = '#2a5f28';
    ctx.lineWidth = 6;
    ctx.stroke();

    return c;
  }

  const leafCanvas = buildLeafTexture();
  const maskData = leafCanvas.getContext('2d').getImageData(0, 0, TEX_W, TEX_H).data;

  function insideLeaf(x, y) {
    const [cx, cy] = toCanvas(x, y);
    const ix = Math.floor(cx);
    const iy = Math.floor(cy);
    if (ix < 0 || iy < 0 || ix >= TEX_W || iy >= TEX_H) return false;
    return maskData[(iy * TEX_W + ix) * 4 + 3] > 200;
  }

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch (e) {
    root.classList.add('is-static');
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  canvasHost.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 50);
  camera.position.set(0, 0, 9.2);

  scene.add(new THREE.HemisphereLight(0xf4ffe8, 0x3a4a30, 0.7));
  const sun = new THREE.DirectionalLight(0xfff6e6, 0.6);
  sun.position.set(2.5, 4, 5);
  scene.add(sun);

  const group = new THREE.Group();
  scene.add(group);

  // Leaf surface
  const leafGeo = new THREE.PlaneGeometry(W, H, 44, 88);
  const basePositions = leafGeo.attributes.position.array.slice();
  const leafTex = new THREE.CanvasTexture(leafCanvas);
  leafTex.anisotropy = 4;
  const leafMat = new THREE.MeshStandardMaterial({
    map: leafTex,
    alphaTest: 0.5,
    side: THREE.DoubleSide,
    roughness: 0.62,
    metalness: 0.0,
  });
  const leaf = new THREE.Mesh(leafGeo, leafMat);
  group.add(leaf);

  function deformLeaf(t) {
    const pos = leafGeo.attributes.position.array;
    for (let i = 0; i < pos.length; i += 3) {
      pos[i + 2] = surfaceZ(basePositions[i], basePositions[i + 1], t);
    }
    leafGeo.attributes.position.needsUpdate = true;
    leafGeo.computeVertexNormals();
  }

  // Petiole
  const stem = new THREE.Mesh(
    new THREE.CylinderGeometry(0.035, 0.05, 0.9, 10),
    new THREE.MeshStandardMaterial({ color: 0x3d7a2f, roughness: 0.7 })
  );
  stem.position.set(0, -2.25, surfaceZ(0, -1.85, 0) - 0.08);
  stem.rotation.x = -0.25;
  group.add(stem);

  // Sample points across the surface, flagged when they sit on a disease spot
  const POINTS = 1500;
  const ptPos = new Float32Array(POINTS * 3);
  const ptSpot = new Float32Array(POINTS);
  const ptSeed = new Float32Array(POINTS);
  for (let n = 0; n < POINTS; ) {
    const x = (Math.random() - 0.5) * W;
    const y = (Math.random() - 0.5) * H;
    if (!insideLeaf(x, y)) continue;
    ptPos[n * 3] = x;
    ptPos[n * 3 + 1] = y;
    ptPos[n * 3 + 2] = surfaceZ(x, y, 0) + 0.02;
    ptSpot[n] = SPOTS.some((s) => Math.hypot(x - s.x, y - s.y) < s.r * 1.5) ? 1 : 0;
    ptSeed[n] = Math.random();
    n++;
  }
  const ptGeo = new THREE.BufferGeometry();
  ptGeo.setAttribute('position', new THREE.BufferAttribute(ptPos, 3));
  ptGeo.setAttribute('aSpot', new THREE.BufferAttribute(ptSpot, 1));
  ptGeo.setAttribute('aSeed', new THREE.BufferAttribute(ptSeed, 1));
  const ptMat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    depthTest: false,
    uniforms: {
      uScanY: { value: 3 },
      uTime: { value: 0 },
      uPixel: { value: renderer.getPixelRatio() },
    },
    vertexShader: `
      attribute float aSpot;
      attribute float aSeed;
      uniform float uScanY;
      uniform float uTime;
      uniform float uPixel;
      varying float vBeam;
      varying float vSpot;
      varying float vPassed;
      varying float vSeed;
      void main() {
        vSeed = aSeed;
        float d = position.y - uScanY;
        vBeam = exp(-d * d * 30.0);
        vPassed = step(uScanY, position.y);
        vSpot = aSpot;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        float pulse = 0.85 + 0.15 * sin(uTime * 3.0 + aSeed * 6.28);
        float size = mix(2.0, 5.5, vBeam) + aSpot * vPassed * 1.2 * pulse;
        gl_PointSize = size * uPixel * (9.0 / -mv.z);
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: `
      varying float vBeam;
      varying float vSpot;
      varying float vPassed;
      varying float vSeed;
      void main() {
        vec2 c = gl_PointCoord - 0.5;
        if (dot(c, c) > 0.25) discard;
        vec3 beamCol = vec3(0.93, 1.0, 0.86);
        vec3 spotCol = vec3(0.78, 0.25, 0.12);
        float spotOn = vSpot * vPassed;
        vec3 col = mix(beamCol, spotCol, spotOn * (1.0 - vBeam * 0.6));
        float a = max(vBeam * 0.95, spotOn * step(0.55, vSeed) * 0.85);
        gl_FragColor = vec4(col, a);
      }
    `,
  });
  group.add(new THREE.Points(ptGeo, ptMat));

  // Scanner bar: a bright line with a soft trailing sheet
  const scanner = new THREE.Group();
  const bar = new THREE.Mesh(
    new THREE.BoxGeometry(2.9, 0.022, 0.022),
    new THREE.MeshBasicMaterial({ color: 0x163a2b })
  );
  scanner.add(bar);
  const sheetCanvas = document.createElement('canvas');
  sheetCanvas.width = 4;
  sheetCanvas.height = 128;
  const sctx = sheetCanvas.getContext('2d');
  const sg = sctx.createLinearGradient(0, 0, 0, 128);
  sg.addColorStop(0, 'rgba(120,190,90,0.0)');
  sg.addColorStop(1, 'rgba(120,190,90,0.22)');
  sctx.fillStyle = sg;
  sctx.fillRect(0, 0, 4, 128);
  const sheet = new THREE.Mesh(
    new THREE.PlaneGeometry(2.9, 0.7),
    new THREE.MeshBasicMaterial({
      map: new THREE.CanvasTexture(sheetCanvas),
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    })
  );
  sheet.position.y = 0.35;
  scanner.add(sheet);
  scanner.position.z = 0.55;
  group.add(scanner);

  // Detection rings + HTML labels
  const rings = SPOTS.map((s) => {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(s.r * 1.55, s.r * 1.55 + 0.03, 48),
      new THREE.MeshBasicMaterial({ color: 0xb4472a, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false })
    );
    ring.position.set(s.x, s.y, surfaceZ(s.x, s.y, 0) + 0.06);
    group.add(ring);

    const el = document.createElement('div');
    el.className = 'leaf-tag';
    el.textContent = s.label;
    labelLayer.appendChild(el);
    return { spot: s, ring, el, shown: false };
  });

  // Base orientation: tilted back and turned diagonally like a specimen on a plate
  group.rotation.set(-0.55, 0, 0.42);
  group.position.y = 0.3;

  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  root.addEventListener('pointermove', (e) => {
    const r = root.getBoundingClientRect();
    pointer.tx = ((e.clientX - r.left) / r.width - 0.5) * 2;
    pointer.ty = ((e.clientY - r.top) / r.height - 0.5) * 2;
  });
  root.addEventListener('pointerleave', () => {
    pointer.tx = 0;
    pointer.ty = 0;
  });

  function resize() {
    const w = canvasHost.clientWidth;
    const h = canvasHost.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.position.z = w / h < 0.9 ? 9.4 : 8.2;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();

  // Scan cycle: sweep tip -> base, hold the result, reset
  const SWEEP = 4.2;
  const HOLD = 3.6;
  const CYCLE = SWEEP + HOLD;
  const SCAN_TOP = 2.2;
  const SCAN_BOTTOM = -2.2;
  const tmp = new THREE.Vector3();

  function setReadout(progress) {
    if (!readout) return;
    const done = progress >= 1;
    readout.dataset.state = done ? 'done' : 'scanning';
    const pct = readout.querySelector('[data-readout-progress]');
    if (pct) pct.textContent = `${Math.round(progress * 100)}%`;
    const found = rings.filter((r) => r.shown).length;
    const count = readout.querySelector('[data-readout-found]');
    if (count) count.textContent = String(found);
    const bar = readout.querySelector('[data-readout-bar]');
    if (bar) bar.style.transform = `scaleX(${progress})`;
  }

  function placeLabels() {
    const w = canvasHost.clientWidth;
    const h = canvasHost.clientHeight;
    rings.forEach((r) => {
      tmp.set(r.spot.x + r.spot.r * 1.6, r.spot.y + r.spot.r * 0.4, surfaceZ(r.spot.x, r.spot.y, 0));
      group.localToWorld(tmp);
      tmp.project(camera);
      r.el.style.transform = `translate(${((tmp.x + 1) / 2) * w}px, ${((1 - tmp.y) / 2) * h}px)`;
    });
  }

  function frame(t) {
    const local = t % CYCLE;
    const progress = Math.min(local / SWEEP, 1);
    const eased = progress < 1 ? 1 - Math.pow(1 - progress, 1.6) : 1;
    const scanY = progress < 1 ? SCAN_TOP + (SCAN_BOTTOM - SCAN_TOP) * eased : -10;

    scanner.position.y = progress < 1 ? scanY : SCAN_BOTTOM;
    scanner.visible = progress < 1;
    ptMat.uniforms.uScanY.value = scanY;
    ptMat.uniforms.uTime.value = t;

    rings.forEach((r) => {
      const passed = progress >= 1 || scanY < r.spot.y - r.spot.r;
      if (passed !== r.shown) {
        r.shown = passed;
        r.el.classList.toggle('is-on', passed);
      }
      const target = passed ? 0.95 : 0;
      r.ring.material.opacity += (target - r.ring.material.opacity) * 0.15;
      const s = 1 + 0.06 * Math.sin(t * 3 + r.spot.x * 4);
      r.ring.scale.set(s, s, 1);
    });

    // Fade out the result just before the next sweep
    root.classList.toggle('is-resetting', local > CYCLE - 0.5);
    setReadout(progress);
  }

  function updatePose(t) {
    pointer.x += (pointer.tx - pointer.x) * 0.05;
    pointer.y += (pointer.ty - pointer.y) * 0.05;
    group.rotation.y = Math.sin(t * 0.35) * 0.32 + pointer.x * 0.35;
    group.rotation.x = -0.55 + pointer.y * 0.2;
    group.position.y = 0.3 + Math.sin(t * 0.8) * 0.06;
  }

  function render() {
    renderer.render(scene, camera);
    placeLabels();
  }

  if (prefersReduced) {
    deformLeaf(0);
    frame(SWEEP + 0.1);
    rings.forEach((r) => (r.ring.material.opacity = 0.95));
    render();
    window.addEventListener('resize', render);
    return;
  }

  let visible = false;
  let looping = false;
  let last = 0;
  let clock = 0;
  new IntersectionObserver((entries) => {
    visible = entries[0].isIntersecting;
    if (visible && !looping) {
      looping = true;
      last = performance.now();
      requestAnimationFrame(loop);
    }
  }).observe(root);

  function loop(now) {
    if (!visible) {
      looping = false;
      return;
    }
    clock += Math.min((now - last) / 1000, 0.05);
    last = now;
    deformLeaf(clock);
    updatePose(clock);
    frame(clock);
    render();
    requestAnimationFrame(loop);
  }
})();
