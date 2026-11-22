/* BioNuclei homepage interactions. Lightweight: no libraries, no animation loops
 * except short, user-visible transitions. Respects prefers-reduced-motion. */
(() => {
  'use strict';
  const qs = (s, r = document) => r.querySelector(s);
  const qsa = (s, r = document) => Array.from(r.querySelectorAll(s));
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.documentElement.classList.remove('no-js');
  qsa('[data-year]').forEach(n => { n.textContent = new Date().getFullYear(); });

  /* ---------- Glass navigation ---------- */
  const nav = qs('[data-nav]');
  const hero = qs('[data-hero]');
  const darkZones = qsa('[data-dark]');
  const onScroll = () => {
    if (!nav) return;
    const y = nav.getBoundingClientRect().bottom - 8;
    const overDark = darkZones.some(z => { const r = z.getBoundingClientRect(); return r.top <= y && r.bottom >= y; });
    nav.classList.toggle('is-solid', !overDark);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
  const menu = qs('[data-menu]'), links = qs('[data-nav-links]');
  menu?.addEventListener('click', () => {
    const open = links.classList.toggle('is-open');
    menu.setAttribute('aria-expanded', String(open));
    menu.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
  });
  links?.addEventListener('click', e => { if (e.target.closest('a')) { links.classList.remove('is-open'); menu?.setAttribute('aria-expanded', 'false'); } });

  /* ---------- Scroll reveal ---------- */
  const reveals = qsa('[data-reveal]');
  if ('IntersectionObserver' in window && !reduced) {
    const io = new IntersectionObserver(entries => entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); } }), { threshold: 0.12 });
    reveals.forEach(el => io.observe(el));
  } else reveals.forEach(el => el.classList.add('is-in'));

  /* ---------- Gentle pointer parallax on the hero (fine pointers only) ---------- */
  if (hero && !reduced && window.matchMedia('(pointer: fine)').matches) {
    let raf = 0, px = 0, py = 0;
    hero.addEventListener('pointermove', e => {
      const r = hero.getBoundingClientRect();
      px = (e.clientX - r.left) / r.width - 0.5; py = (e.clientY - r.top) / r.height - 0.5;
      if (!raf) raf = requestAnimationFrame(() => { hero.style.setProperty('--px', px.toFixed(3)); hero.style.setProperty('--py', py.toFixed(3)); raf = 0; });
    });
    hero.addEventListener('pointerleave', () => { hero.style.setProperty('--px', 0); hero.style.setProperty('--py', 0); });
  }

  /* ---------- Procedural fluorescence field with instance outlines ---------- */
  const view = qs('[data-reveal-view]');
  const raw = qs('canvas[data-field="raw"]'), seg = qs('canvas[data-field="seg"]');
  function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function makeNuclei(w, h) {
    const rand = rng(20261122), out = [];
    const target = Math.round((w * h) / 3600);
    const unit = Math.min(w, h) / 360;
    let guard = 0;
    while (out.length < target && guard++ < target * 40) {
      const r = unit * (9 + rand() * 8);
      const n = { x: r + rand() * (w - 2 * r), y: r + rand() * (h - 2 * r), rx: r * (0.85 + rand() * 0.4), ry: r * (0.7 + rand() * 0.35), a: rand() * Math.PI, b: 0.55 + rand() * 0.45, hue: rand() };
      if (out.every(o => Math.hypot(o.x - n.x, o.y - n.y) > (o.rx + n.rx) * 1.02)) out.push(n);
    }
    return out;
  }
  let living = false;
  function drawField() {
    if (!view || !raw || !seg) return;
    if (window.BioNucleiField && !living) {
      // Same seed for both layers: nuclei move identically, the right side adds outlines.
      living = true;
      const a = window.BioNucleiField.create(raw, { outline: false, seed: 20261122 });
      window.BioNucleiField.create(seg, { outline: true, sweep: false, fill: true, dim: 0.6, seed: 20261122 });
      view.classList.add('is-live');
      const count = qs('[data-count]'); if (count) count.textContent = String(a.count());
      return;
    }
    if (living) return;
    const rect = view.getBoundingClientRect();
    if (!rect.width) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = Math.round(rect.width * dpr), h = Math.round(rect.height * dpr);
    [raw, seg].forEach(c => { c.width = w; c.height = h; });
    const nuclei = makeNuclei(w, h);
    const paint = (ctx, dim) => {
      ctx.fillStyle = '#05070a'; ctx.fillRect(0, 0, w, h);
      const bg = ctx.createRadialGradient(w * 0.6, h * 0.4, 0, w * 0.6, h * 0.4, w * 0.8);
      bg.addColorStop(0, 'rgba(40,60,90,.35)'); bg.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
      ctx.globalCompositeOperation = 'lighter';
      nuclei.forEach(n => {
        ctx.save(); ctx.translate(n.x, n.y); ctx.rotate(n.a); ctx.scale(1, n.ry / n.rx);
        const g = ctx.createRadialGradient(0, 0, 0, 0, 0, n.rx * 1.25);
        const blue = `rgba(${90 + n.hue * 40},${150 + n.hue * 50},255,`;
        g.addColorStop(0, blue + (1 * n.b * dim) + ')'); g.addColorStop(0.6, blue + (0.6 * n.b * dim) + ')'); g.addColorStop(1, 'rgba(20,40,90,0)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, n.rx * 1.25, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      });
      ctx.globalCompositeOperation = 'source-over';
    };
    paint(raw.getContext('2d'), 1);
    const s = seg.getContext('2d');
    paint(s, 0.55);
    nuclei.forEach((n, i) => {
      s.save(); s.translate(n.x, n.y); s.rotate(n.a);
      s.beginPath(); s.ellipse(0, 0, n.rx, n.ry, 0, 0, Math.PI * 2);
      const hue = 320 + (i * 37) % 60;
      s.fillStyle = `hsla(${hue},70%,55%,.22)`; s.fill();
      s.lineWidth = 2 * dpr; s.strokeStyle = `hsla(${hue},85%,72%,.95)`; s.stroke();
      s.restore();
      s.fillStyle = 'rgba(255,255,255,.9)'; s.beginPath(); s.arc(n.x, n.y, 1.8 * dpr, 0, Math.PI * 2); s.fill();
    });
    view.classList.add('is-live');
    const count = qs('[data-count]'); if (count) count.textContent = String(nuclei.length);
  }
  let resizeTimer = 0;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(drawField, 150); });
  drawField();

  /* Slider */
  const handle = qs('[data-handle]');
  function setSplit(pct) {
    const v = Math.max(0, Math.min(100, pct));
    view?.style.setProperty('--split', v + '%');
    handle?.setAttribute('aria-valuenow', String(Math.round(v)));
  }
  if (view && handle) {
    let dragging = false;
    const fromEvent = e => { const r = view.getBoundingClientRect(); setSplit(((e.clientX - r.left) / r.width) * 100); };
    view.addEventListener('pointerdown', e => { dragging = true; view.setPointerCapture(e.pointerId); fromEvent(e); intro = false; });
    view.addEventListener('pointermove', e => { if (dragging) fromEvent(e); });
    ['pointerup', 'pointercancel'].forEach(t => view.addEventListener(t, () => { dragging = false; }));
    handle.addEventListener('keydown', e => {
      const now = Number(handle.getAttribute('aria-valuenow')) || 50;
      if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') { setSplit(now - 5); e.preventDefault(); }
      if (e.key === 'ArrowRight' || e.key === 'ArrowUp') { setSplit(now + 5); e.preventDefault(); }
      if (e.key === 'Home') { setSplit(0); e.preventDefault(); }
      if (e.key === 'End') { setSplit(100); e.preventDefault(); }
    });
    // One short introductory sweep so visitors see what the slider does.
    let intro = !reduced;
    if (intro) {
      const start = performance.now();
      const step = t => {
        if (!intro) return;
        const k = Math.min(1, (t - start) / 1800);
        const ease = 1 - Math.pow(1 - k, 3);
        setSplit(92 - 42 * ease);
        if (k < 1) requestAnimationFrame(step);
      };
      setTimeout(() => requestAnimationFrame(step), 500);
    } else setSplit(50);
  }

  /* ---------- Pipeline explorer (stages mirror the repository code) ---------- */
  const STAGES = [
    { t: 'Recognise input', what: 'Reads the file\'s own axes, bit depth and channel metadata. Picks one 2-D plane from stacks, uses the signal channel of RGB exports and identifies dyes such as DAPI or Hoechst.', why: 'Analysing the wrong channel or a brightfield image produces numbers that look real but are not.', out: 'A recognised plane, or a rejection with a reason you can act on.', code: 'input_recognition.py' },
    { t: 'Quality gate', what: 'Checks intensity range, saturation and blank areas, then runs the released network on a small preview to confirm coherent nuclear structure.', why: 'Stops low-quality inputs before they reach measurement.', out: 'READY, CAUTION or BLOCKED, with every warning recorded.', code: 'adaptive_agent.py' },
    { t: 'Boundary U-Net', what: 'The released checkpoint predicts background, nuclear interior and nuclear boundary for every pixel, tile by tile, in evaluation mode.', why: 'Boundary prediction is what lets touching nuclei be separated.', out: 'A per-pixel class map at the original resolution.', code: 'inference.py' },
    { t: 'Instance separation', what: 'Deterministic code turns the class map into explicitly labelled nuclei, each with its own ID.', why: 'Counting and measuring need individual objects, not a blob of foreground.', out: 'A label image with one integer per nucleus.', code: 'inference.py' },
    { t: 'Measurements', what: 'Area, perimeter, circularity, eccentricity, solidity, intensity statistics and nearest-neighbour distances for every nucleus.', why: 'These are the quantities your experiment compares.', out: 'A per-nucleus table in pixels, plus summary reports.', code: 'community.py' },
    { t: 'Specialist review', what: 'Eight deterministic reviewers check the measurements and report, each bound to evidence with a SHA-256 digest.', why: 'Every statement in the report is traceable to measured evidence.', out: 'Verified findings and stated limitations.', code: 'expert_agents.py' },
    { t: 'Report', what: 'Builds HTML, PDF and JSON reports with input recognition, quality, measurements and provenance, and packages them with the mask and overlay.', why: 'Results you can share, audit and reproduce.', out: 'A download bundle. Your original image is not included.', code: 'report.py' }
  ];
  const rail = qs('[data-rail]'), detail = qs('[data-detail]');
  let active = 0, autoplay = !reduced, timer = 0;
  if (rail && detail) {
    STAGES.forEach((s, i) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'lp-step'; b.setAttribute('role', 'tab'); b.dataset.i = i;
      b.innerHTML = `<span>${i + 1}</span><b>${s.t}</b>`;
      b.addEventListener('click', () => { autoplay = false; clearTimeout(timer); select(i); });
      b.addEventListener('keydown', e => {
        if (e.key === 'ArrowRight') { e.preventDefault(); autoplay = false; select((active + 1) % STAGES.length, true); }
        if (e.key === 'ArrowLeft') { e.preventDefault(); autoplay = false; select((active - 1 + STAGES.length) % STAGES.length, true); }
      });
      rail.appendChild(b);
    });
    function select(i, focus) {
      active = i;
      qsa('.lp-step', rail).forEach((b, k) => {
        b.classList.toggle('is-active', k === i); b.classList.toggle('is-done', k < i);
        b.setAttribute('aria-selected', String(k === i)); b.tabIndex = k === i ? 0 : -1;
        if (k === i && focus) b.focus();
      });
      rail.style.setProperty('--fill', `${(i / (STAGES.length - 1)) * 100}%`);
      const line = qs('.lp-rail-line', rail); line?.style.setProperty('--fill', `${(i / (STAGES.length - 1)) * 100}%`);
      const s = STAGES[i];
      detail.innerHTML = `<div class="lp-detail-in"><p class="lp-kicker">Step ${i + 1} of ${STAGES.length}</p><h3>${s.t}</h3><p>${s.what}</p></div><div class="lp-detail-in"><h4>Why it matters</h4><p>${s.why}</p></div><div class="lp-detail-in"><h4>What you get</h4><p>${s.out}</p><p style="margin-top:12px"><code>${s.code}</code></p></div>`;
    }
    select(0);
    const run = () => { if (!autoplay) return; timer = setTimeout(() => { if (!autoplay) return; if (active < STAGES.length - 1) { select(active + 1); run(); } else autoplay = false; }, 2600); };
    if ('IntersectionObserver' in window && autoplay) {
      const io = new IntersectionObserver(es => { if (es[0].isIntersecting) { run(); io.disconnect(); } }, { threshold: 0.5 });
      io.observe(rail);
    }
  }

  /* ---------- Ecosystem map ---------- */
  const ECO = [
    { id: 'lab', name: 'Lab', sub: 'workspace', status: ['operational', 'Operational'], href: 'bionuclei-lab.html', text: 'Where researchers upload images, run analyses, review nuclei and download reports. Includes the experiment tray for multi-image studies.' },
    { id: 'mcp', name: 'BioMCP', sub: 'agents', status: ['experimental', 'Experimental'], href: 'biomcp.html', text: 'A Model Context Protocol server so AI agents can call validated BioNuclei operations with typed inputs and get structured results back.' },
    { id: 'robust', name: 'DomainRobust', sub: 'research', status: ['progress', 'Research in progress'], href: 'research.html', text: 'Experiments on how segmentation holds up across laboratories, microscopes and staining. Results are published only with their evidence.' },
    { id: 'data', name: 'Datasets', sub: 'benchmarks', status: ['operational', 'Documented'], href: 'datasets.html', text: 'BBBC038, BBBC039, S-BIAD634 and S-BSST265 with provenance, licences and the role each plays in evaluation.' },
    { id: 'wf', name: 'BioWF', sub: 'workflows', status: ['planned', 'Planned'], href: 'biowf.html', text: 'Reusable, versioned analysis workflows that chain inspection, segmentation, QC and reporting.' },
    { id: 'skills', name: 'BioSkills', sub: 'tasks', status: ['planned', 'Planned'], href: 'bioskills.html', text: 'Reusable scientific task definitions that connect agents to verified tools rather than free-form prompting.' },
    { id: 'fm', name: 'BioFM', sub: 'models', status: ['direction', 'Research direction'], href: 'biofm.html', text: 'Research into domain-aware foundation models for microscopy, with robustness treated as a first-class requirement.' }
  ];
  const CORE = { id: 'core', name: 'BioNuclei', sub: 'engine', status: ['operational', 'Operational'], href: 'bionuclei.html', text: 'The scientific core: input recognition, quality gate, Boundary U-Net inference, instance separation, measurements, specialist review and reports. Every other part builds on it.' };
  const svg = qs('[data-eco-map]'), panel = qs('[data-eco-panel]');
  if (svg && panel) {
    const NS = 'http://www.w3.org/2000/svg', cx = 260, cy = 260, R = 190;
    const el = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v)); parent.appendChild(n); return n; };
    const ring = el('circle', { cx, cy, r: R, fill: 'none', stroke: 'rgba(255,255,255,.07)', 'stroke-width': 1 }, svg);
    ring.setAttribute('aria-hidden', 'true');
    const nodes = {};
    const linkLayer = el('g', { 'aria-hidden': 'true' }, svg);
    ECO.forEach((d, i) => {
      const ang = -Math.PI / 2 + (i / ECO.length) * Math.PI * 2;
      d.x = cx + R * Math.cos(ang); d.y = cy + R * Math.sin(ang);
      const path = el('path', { d: `M${cx},${cy} L${d.x.toFixed(1)},${d.y.toFixed(1)}`, class: 'link', id: `eco-l-${d.id}` }, linkLayer);
      const dot = el('circle', { r: 3, class: 'flow' }, linkLayer);
      if (!reduced) { const m = el('animateMotion', { dur: '1.8s', repeatCount: 'indefinite' }, dot); el('mpath', { href: `#eco-l-${d.id}` }, m); }
      d.link = path;
    });
    const drawNode = (d, r, core) => {
      const g = el('g', { class: `node${core ? ' core' : ''}`, tabindex: 0, role: 'button', 'aria-label': `${d.name}: ${d.status[1]}` }, svg);
      el('circle', { cx: d.x, cy: d.y, r }, g);
      const t = el('text', { x: d.x, y: d.y - 1 }, g); t.textContent = d.name;
      const s = el('text', { x: d.x, y: d.y + 13, class: 'sub' }, g); s.textContent = d.sub;
      g.addEventListener('click', () => show(d));
      g.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); show(d); } });
      nodes[d.id] = g;
    };
    CORE.x = cx; CORE.y = cy;
    drawNode(CORE, 62, true);
    ECO.forEach(d => drawNode(d, 46, false));
    function show(d) {
      Object.values(nodes).forEach(n => n.classList.remove('is-active'));
      nodes[d.id].classList.add('is-active');
      ECO.forEach(e => e.link.classList.toggle('is-on', e.id === d.id));
      panel.innerHTML = `<div class="lp-detail-in"><span class="lp-status ${d.status[0]}">${d.status[1]}</span><h3>${d.name}</h3><p>${d.text}</p><a href="${d.href}">Learn more →</a></div>`;
    }
    show(CORE);
  }
})();
