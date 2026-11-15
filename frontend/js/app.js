/**
 * MonsoonDelta — app.js
 *
 * 1. Three.js animated particle/globe background
 * 2. API data fetching
 * 3. Chart.js latest forecast bar chart
 * 4. Chart.js revision line chart
 * 5. Leaflet disagreement map
 * 6. Plain-language explanation rendering
 * 7. Stale banner logic
 *
 * No free-form AI text. Explanation strings come from /api/disagreement.
 */

'use strict';

/* ═══════════════════════════════════════════════════════════════════════════
   1. THREE.JS ANIMATED BACKGROUND
   ═══════════════════════════════════════════════════════════════════════════ */
(function initThreeBackground() {
  const canvas = document.getElementById('bg-canvas');
  if (!canvas || typeof THREE === 'undefined') return;

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.z = 5;

  /* ── Particle field (rain drops feel) ── */
  const particleCount = 1800;
  const positions = new Float32Array(particleCount * 3);
  const colors    = new Float32Array(particleCount * 3);
  const palette = [
    new THREE.Color('#38bdf8'),
    new THREE.Color('#a78bfa'),
    new THREE.Color('#2dd4bf'),
    new THREE.Color('#f472b6'),
  ];

  for (let i = 0; i < particleCount; i++) {
    positions[i * 3]     = (Math.random() - 0.5) * 20;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 10;
    const c = palette[Math.floor(Math.random() * palette.length)];
    colors[i * 3]     = c.r;
    colors[i * 3 + 1] = c.g;
    colors[i * 3 + 2] = c.b;
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geo.setAttribute('color',    new THREE.BufferAttribute(colors,    3));

  const mat = new THREE.PointsMaterial({
    size: 0.045,
    vertexColors: true,
    transparent: true,
    opacity: 0.75,
    sizeAttenuation: true,
  });

  const particles = new THREE.Points(geo, mat);
  scene.add(particles);

  /* ── Wireframe globe (Bay of Bengal feel) ── */
  const globeGeo = new THREE.SphereGeometry(2.2, 32, 32);
  const globeMat = new THREE.MeshBasicMaterial({
    color: 0x38bdf8,
    wireframe: true,
    transparent: true,
    opacity: 0.06,
  });
  const globe = new THREE.Mesh(globeGeo, globeMat);
  globe.position.set(3.5, -0.5, -3);
  scene.add(globe);

  /* ── Second torus for extra depth ── */
  const torusGeo = new THREE.TorusGeometry(1.8, 0.015, 8, 80);
  const torusMat = new THREE.MeshBasicMaterial({
    color: 0xa78bfa,
    transparent: true,
    opacity: 0.12,
  });
  const torus = new THREE.Mesh(torusGeo, torusMat);
  torus.position.set(-4, 1, -4);
  scene.add(torus);

  /* ── Animation loop ── */
  let frameId;
  function animate() {
    frameId = requestAnimationFrame(animate);
    particles.rotation.y += 0.00018;
    particles.rotation.x += 0.00008;
    globe.rotation.y     += 0.0012;
    torus.rotation.x     += 0.0008;
    torus.rotation.z     += 0.0005;
    renderer.render(scene, camera);
  }
  animate();

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
})();

/* ═══════════════════════════════════════════════════════════════════════════
   2. MINI GLOBE in hero (Three.js)
   ═══════════════════════════════════════════════════════════════════════════ */
(function initHeroGlobe() {
  const container = document.getElementById('globe-container');
  if (!container || typeof THREE === 'undefined') return;

  const W = 260, H = 260;
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(W, H);
  container.appendChild(renderer.domElement);

  const scene  = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 100);
  camera.position.z = 3.2;

  /* Outer glow sphere */
  const glowGeo = new THREE.SphereGeometry(1.18, 32, 32);
  const glowMat = new THREE.MeshBasicMaterial({
    color: 0x38bdf8, transparent: true, opacity: 0.06, side: THREE.FrontSide,
  });
  scene.add(new THREE.Mesh(glowGeo, glowMat));

  /* Main wireframe globe */
  const mainGeo = new THREE.SphereGeometry(1.0, 36, 36);
  const mainMat = new THREE.MeshBasicMaterial({
    color: 0x38bdf8, wireframe: true, transparent: true, opacity: 0.22,
  });
  const mainGlobe = new THREE.Mesh(mainGeo, mainMat);
  scene.add(mainGlobe);

  /* Latitude rings */
  const ringColors = [0x38bdf8, 0xa78bfa, 0x2dd4bf];
  [-0.4, 0, 0.4].forEach((y, i) => {
    const r = Math.sqrt(1 - y * y) * 1.001;
    const rg = new THREE.TorusGeometry(r, 0.008, 6, 80);
    const rm = new THREE.MeshBasicMaterial({
      color: ringColors[i], transparent: true, opacity: 0.5,
    });
    const ring = new THREE.Mesh(rg, rm);
    ring.position.y = y;
    scene.add(ring);
  });

  /* Bay of Bengal marker dot */
  const markerGeo = new THREE.SphereGeometry(0.055, 12, 12);
  const markerMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24 });
  const marker    = new THREE.Mesh(markerGeo, markerMat);
  // Approx 17.7°N, 83.2°E on a unit sphere
  const lat = 17.7 * Math.PI / 180;
  const lon = 83.2 * Math.PI / 180;
  marker.position.set(
    Math.cos(lat) * Math.sin(lon),
    Math.sin(lat),
    Math.cos(lat) * Math.cos(lon),
  );
  scene.add(marker);

  /* Ambient light ring */
  const pointLight = new THREE.PointLight(0x38bdf8, 1.5, 6);
  pointLight.position.set(2, 1, 2);
  scene.add(pointLight);

  let angle = 0;
  function animate() {
    requestAnimationFrame(animate);
    angle += 0.008;
    mainGlobe.rotation.y = angle;
    marker.position.set(
      Math.cos(lat) * Math.sin(lon + angle),
      Math.sin(lat),
      Math.cos(lat) * Math.cos(lon + angle),
    );
    renderer.render(scene, camera);
  }
  animate();
})();

/* ═══════════════════════════════════════════════════════════════════════════
   3. API + DATA LAYER
   ═══════════════════════════════════════════════════════════════════════════ */
const API_BASE = '';  // same origin; change to full URL if deployed separately

let selectedLat = 17.7;
let selectedLon = 83.2;
let selectedStep = 24;  // current window step_end

let latestChart   = null;
let revisionChart = null;
let disagreeMap   = null;
let disagreeLayer = null;

async function fetchJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status} from ${url}`);
  return resp.json();
}

function showLoading(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('hidden');
}
function hideLoading(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('hidden');
}

/* ── Format UTC time nicely ── */
function fmtRun(utc) {
  if (!utc) return '—';
  try {
    const d = new Date(utc);
    return d.toUTCString().replace(/:\d\d GMT/, ' UTC').replace(/^.*, /, '');
  } catch { return utc; }
}

function fmtMm(v) {
  if (v === null || v === undefined) return '—';
  return v.toFixed(1) + '\u202fmm';
}

/* ── Stale banner ── */
function checkStale(data) {
  const staleBanner = document.getElementById('stale-banner');
  const staleTime   = document.getElementById('stale-time');
  if (data.stale) {
    const wins = data.windows;
    const rt = (wins.ifs && wins.ifs.run_time_utc) || (wins.aifs && wins.aifs.run_time_utc) || '';
    staleTime.textContent = fmtRun(rt) || 'unknown';
    staleBanner.removeAttribute('hidden');
  } else {
    staleBanner.setAttribute('hidden', '');
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   4. LATEST FORECAST CHART
   ═══════════════════════════════════════════════════════════════════════════ */
async function loadLatest() {
  showLoading('latest-loading');
  try {
    const data = await fetchJSON(
      `${API_BASE}/api/latest?lat=${selectedLat}&lon=${selectedLon}`
    );
    checkStale(data);

    const ifsData  = data.windows.ifs  ? data.windows.ifs.data  : [];
    const aifsData = data.windows.aifs ? data.windows.aifs.data : [];

    // Update run-info bar
    document.getElementById('ifs-run-time').textContent  = fmtRun(data.windows.ifs?.run_time_utc);
    document.getElementById('aifs-run-time').textContent = fmtRun(data.windows.aifs?.run_time_utc);
    document.getElementById('updated-time').textContent  = fmtRun(new Date().toISOString());

    if (data.demo_mode) {
      document.getElementById('ifs-run-time').textContent  += ' ★ demo';
      document.getElementById('aifs-run-time').textContent += ' ★ demo';
    }

    // Build labels from IFS steps (or AIFS)
    const ref = ifsData.length ? ifsData : aifsData;
    const labels = ref.map(w => {
      if (w.valid_time_utc) {
        const d = new Date(w.valid_time_utc);
        return d.toUTCString().slice(0, 11) + '\n' + d.toUTCString().slice(17, 22) + 'Z';
      }
      return `+${w.step_end}h`;
    });

    const ifsVals  = ref.map(w => {
      const match = ifsData.find(x => x.step_end === w.step_end);
      return match ? match.total_mm : 0;
    });
    const aifsVals = ref.map(w => {
      const match = aifsData.find(x => x.step_end === w.step_end);
      return match ? match.total_mm : 0;
    });

    const steps = ref.map(w => w.step_end);

    if (latestChart) latestChart.destroy();

    const ctx = document.getElementById('latest-chart');
    latestChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'IFS (mm)',
            data: ifsVals,
            backgroundColor: 'rgba(56, 189, 248, 0.7)',
            borderColor: '#38bdf8',
            borderWidth: 1,
            borderRadius: 4,
            borderSkipped: false,
          },
          {
            label: 'AIFS (mm)',
            data: aifsVals,
            backgroundColor: 'rgba(167, 139, 250, 0.7)',
            borderColor: '#a78bfa',
            borderWidth: 1,
            borderRadius: 4,
            borderSkipped: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        onClick(event, elements) {
          if (!elements.length) return;
          const idx = elements[0].index;
          selectedStep = steps[idx];
          loadRevision();
          loadDisagreement();
          document.getElementById('revision-window-label').textContent =
            `Window: +${selectedStep - 6}h → +${selectedStep}h`;
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            backgroundColor: 'rgba(10,20,45,0.95)',
            borderColor: 'rgba(56,189,248,0.3)',
            borderWidth: 1,
            titleColor: '#e2eaf7',
            bodyColor: '#8ba4c8',
            callbacks: {
              label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)} mm`,
            },
          },
        },
        scales: {
          x: {
            ticks: {
              color: '#546a8b',
              font: { size: 10 },
              maxRotation: 45,
            },
            grid: { color: 'rgba(99,155,230,0.08)' },
          },
          y: {
            ticks: {
              color: '#546a8b',
              callback: v => v + ' mm',
            },
            grid: { color: 'rgba(99,155,230,0.08)' },
            title: {
              display: true,
              text: 'Precipitation (mm)',
              color: '#546a8b',
              font: { size: 11 },
            },
          },
        },
        animation: {
          duration: 800,
          easing: 'easeInOutQuart',
        },
      },
    });

    hideLoading('latest-loading');
  } catch (err) {
    console.error('Latest forecast error:', err);
    hideLoading('latest-loading');
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   5. REVISION CHART
   ═══════════════════════════════════════════════════════════════════════════ */
async function loadRevision() {
  showLoading('revision-loading');
  try {
    const data = await fetchJSON(
      `${API_BASE}/api/revision?model=ifs&lat=${selectedLat}&lon=${selectedLon}&step_end=${selectedStep}`
    );
    const rev = data.revision;

    // Stats
    const changeEl = document.getElementById('stat-change');
    const rangeEl  = document.getElementById('stat-range');
    const dirEl    = document.getElementById('stat-direction');

    changeEl.textContent = rev.latest_change !== null ? fmtMm(rev.latest_change) : '—';
    rangeEl.textContent  = rev.range_mm      !== null ? fmtMm(rev.range_mm)      : '—';

    dirEl.textContent = rev.direction === 'insufficient_data' ? 'N/A' : rev.direction.toUpperCase();
    dirEl.className   = `stat-value direction-badge ${
      rev.direction === 'up' ? 'up' :
      rev.direction === 'down' ? 'down' :
      rev.direction === 'steady' ? 'steady' : 'na'
    }`;

    // Chart
    const labels = data.run_times.map(t => {
      if (!t || t === 'demo') return 'demo';
      const d = new Date(t);
      return d.toUTCString().slice(5, 11) + '\n' + d.toUTCString().slice(17, 22) + 'Z';
    });
    const values = rev.valid_values;

    if (revisionChart) revisionChart.destroy();
    const ctx = document.getElementById('revision-chart');

    if (values.length < 1) {
      hideLoading('revision-loading');
      return;
    }

    revisionChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'IFS forecast (mm)',
          data: values,
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56,189,248,0.1)',
          borderWidth: 2.5,
          pointBackgroundColor: '#38bdf8',
          pointRadius: 5,
          pointHoverRadius: 7,
          tension: 0.4,
          fill: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(10,20,45,0.95)',
            borderColor: 'rgba(56,189,248,0.3)',
            borderWidth: 1,
            callbacks: {
              label: c => `${c.parsed.y.toFixed(1)} mm`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: '#546a8b', font: { size: 10 } },
            grid:  { color: 'rgba(99,155,230,0.08)' },
          },
          y: {
            ticks: {
              color: '#546a8b',
              callback: v => v + ' mm',
            },
            grid: { color: 'rgba(99,155,230,0.08)' },
          },
        },
        animation: { duration: 600, easing: 'easeInOutCubic' },
      },
    });

    hideLoading('revision-loading');
  } catch (err) {
    console.error('Revision error:', err);
    hideLoading('revision-loading');
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   6. DISAGREEMENT MAP + EXPLANATION
   ═══════════════════════════════════════════════════════════════════════════ */
async function loadDisagreement() {
  showLoading('disagree-loading');
  try {
    const data = await fetchJSON(
      `${API_BASE}/api/disagreement?lat=${selectedLat}&lon=${selectedLon}&step_end=${selectedStep}`
    );
    const d = data.disagreement;

    document.getElementById('stat-ifs-mm').textContent   = fmtMm(d.ifs_mm);
    document.getElementById('stat-aifs-mm').textContent  = fmtMm(d.aifs_mm);
    document.getElementById('stat-diff-mm').textContent  = fmtMm(d.diff_mm);
    const wetterEl = document.getElementById('stat-wetter');
    wetterEl.textContent = d.wetter_model;
    wetterEl.className   = 'stat-value wetter-badge';

    // Map
    if (!disagreeMap) {
      disagreeMap = L.map('disagree-map', {
        center: [selectedLat, selectedLon],
        zoom: 5,
        zoomControl: true,
        attributionControl: true,
      });
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 10,
      }).addTo(disagreeMap);
    } else {
      disagreeMap.setView([selectedLat, selectedLon], 5);
    }

    if (disagreeLayer) disagreeLayer.remove();

    // Show a coloured circle indicating disagreement magnitude at the point
    const absD = Math.abs(d.diff_mm);
    const colour = absD < 2  ? '#2dd4bf' :   // close → teal
                   absD < 5  ? '#fbbf24' :   // moderate → amber
                               '#f472b6';    // large → pink
    const opacity = Math.min(0.8, 0.2 + absD / 15);

    disagreeLayer = L.circleMarker([selectedLat, selectedLon], {
      radius: 18,
      fillColor: colour,
      color: colour,
      weight: 2,
      opacity: 1,
      fillOpacity: opacity,
    }).addTo(disagreeMap);

    disagreeLayer.bindPopup(
      `<strong>IFS</strong>: ${fmtMm(d.ifs_mm)}<br>` +
      `<strong>AIFS</strong>: ${fmtMm(d.aifs_mm)}<br>` +
      `<strong>Diff</strong>: ${fmtMm(d.diff_mm)}<br>` +
      `<strong>Wetter</strong>: ${d.wetter_model}`
    ).openPopup();

    // Explanation
    if (data.explanation) {
      renderExplanation(data.explanation);
    }

    hideLoading('disagree-loading');
  } catch (err) {
    console.error('Disagreement error:', err);
    hideLoading('disagree-loading');
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   7. PLAIN-LANGUAGE EXPLANATION
   ═══════════════════════════════════════════════════════════════════════════ */
function renderExplanation(expl) {
  const container = document.getElementById('plain-words-body');
  if (!container) return;

  const sentences = [
    { icon: '🌧️', text: expl.forecast    || '' },
    { icon: '📊', text: expl.revision    || '' },
    { icon: '🔀', text: expl.disagreement|| '' },
  ];

  container.innerHTML = sentences.map((s, i) =>
    s.text ? `
    <div class="words-sentence" style="animation-delay:${i * 0.12}s">
      <span class="words-icon">${s.icon}</span>
      <p class="words-text">${s.text}</p>
    </div>` : ''
  ).join('') + `
  <div class="words-sentence" style="animation-delay:0.4s">
    <span class="words-icon">⚠️</span>
    <p class="words-text" style="font-size:0.82rem; color:#8ba4c8">${expl.disclaimer || ''}</p>
  </div>`;
}

/* ═══════════════════════════════════════════════════════════════════════════
   8. LOCATION SELECTOR
   ═══════════════════════════════════════════════════════════════════════════ */
document.getElementById('location-select').addEventListener('change', function () {
  const [lat, lon] = this.value.split(',').map(Number);
  selectedLat = lat;
  selectedLon = lon;
  if (disagreeMap) disagreeMap.setView([lat, lon], 5);
  loadAll();
});

/* ═══════════════════════════════════════════════════════════════════════════
   9. BOOTSTRAP
   ═══════════════════════════════════════════════════════════════════════════ */
async function loadAll() {
  await loadLatest();
  await loadRevision();
  await loadDisagreement();
}

// Initial load
loadAll();

// Auto-refresh every 5 minutes
setInterval(loadAll, 5 * 60 * 1000);
