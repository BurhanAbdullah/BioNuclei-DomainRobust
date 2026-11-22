/* BioNuclei Lab workstation behaviour.
 * Layout and state presentation only. Authentication, upload, job polling,
 * results and deletion stay in bionuclei-analyzer.js and bionuclei-progress.js.
 * Nothing here stores image data: files move only from a drop event into the
 * page's own file input. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const fmtBytes = n => n >= 1048576 ? `${(n / 1048576).toFixed(n % 1048576 ? 1 : 0)} MiB` : `${Math.round(n / 1024)} KiB`;

  /* ---------- Step rail mirrors the real page state ---------- */
  function currentStep() {
    if ($('resultPanel') && !$('resultPanel').hidden) return 'results';
    if ($('workspace') && !$('workspace').hidden) {
      // Only a real server-side job (set by bionuclei-progress.js) or a reported failure counts as the analyze step.
      const progress = $('analysisProgress');
      if (window.__BIONUCLEI_ANALYSIS_ACTIVE) return 'analyze';
      if (progress && !progress.hidden && /analysis failed/i.test(progress.textContent)) return 'analyze';
      return 'image';
    }
    return 'access';
  }
  const order = ['access', 'image', 'analyze', 'results'];
  function syncSteps() {
    const step = currentStep();
    const index = order.indexOf(step);
    qsa('.ws-steps li').forEach(li => {
      const i = order.indexOf(li.dataset.step);
      li.classList.toggle('is-current', i === index);
      li.classList.toggle('is-done', i < index);
      if (i === index) li.setAttribute('aria-current', 'step'); else li.removeAttribute('aria-current');
    });
    const input = $('image');
    const drop = qs('[data-dropzone]');
    if (drop && input) {
      const file = input.files && input.files[0];
      drop.classList.toggle('has-file', Boolean(file));
      const title = qs('b', drop);
      if (title) title.textContent = file ? `${file.name} · ${fmtBytes(file.size)}` : 'Drop a microscopy image here';
    }
  }
  const observer = new MutationObserver(syncSteps);
  ['access', 'workspace', 'resultPanel', 'analysisProgress'].forEach(id => {
    const node = $(id);
    if (node) observer.observe(node, { attributes: true, attributeFilter: ['hidden'], childList: id === 'analysisProgress', subtree: id === 'analysisProgress' });
  });

  /* ---------- Drag and drop into the existing file input ---------- */
  const drop = qs('[data-dropzone]');
  const input = $('image');
  if (drop && input) {
    ['dragenter', 'dragover'].forEach(type => drop.addEventListener(type, event => { event.preventDefault(); drop.classList.add('is-over'); }));
    ['dragleave', 'dragend'].forEach(type => drop.addEventListener(type, () => drop.classList.remove('is-over')));
    drop.addEventListener('drop', event => {
      event.preventDefault();
      drop.classList.remove('is-over');
      const files = event.dataTransfer && event.dataTransfer.files;
      if (files && files.length > 1 && window.BioNucleiExperiment) {
        window.BioNucleiExperiment.add(files);
        qs('#experiment')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
      }
      const file = files && files[0];
      if (!file) return;
      if (!/\.(tif|tiff|nd2)$/i.test(file.name)) {
        const info = $('fileInfo');
        if (info) { info.hidden = false; info.textContent = `${file.name} is not a supported format. Use TIFF/TIF or Nikon ND2.`; }
        return;
      }
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    input.addEventListener('change', syncSteps);
  }
  $('clearButton')?.addEventListener('click', () => setTimeout(syncSteps, 0));

  /* ---------- Result layers and full screen ---------- */
  qsa('[data-layer]').forEach(tab => tab.addEventListener('click', () => {
    qsa('[data-layer]').forEach(t => t.setAttribute('aria-selected', String(t === tab)));
    qsa('[data-layer-panel]').forEach(panel => { panel.hidden = panel.dataset.layerPanel !== tab.dataset.layer; });
  }));
  const fullscreen = qs('[data-fullscreen]');
  const viewerCard = qs('.ws-viewer-card');
  if (fullscreen && viewerCard) {
    if (!viewerCard.requestFullscreen) fullscreen.hidden = true;
    fullscreen.addEventListener('click', () => {
      if (document.fullscreenElement) document.exitFullscreen(); else viewerCard.requestFullscreen().catch(() => {});
    });
  }

  /* ---------- Compact specialist cards (content untouched, only clamped) ---------- */
  function enhanceAgents() {
    qsa('#agentDetails .agent-finding:not([data-ws])').forEach(card => {
      card.dataset.ws = '1';
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'ws-agent-toggle';
      button.setAttribute('aria-expanded', 'false');
      button.textContent = 'Show evidence';
      button.addEventListener('click', () => {
        const open = card.classList.toggle('is-open');
        button.setAttribute('aria-expanded', String(open));
        button.textContent = open ? 'Hide evidence' : 'Show evidence';
      });
      card.appendChild(button);
    });
  }
  const agents = $('agentDetails');
  if (agents) new MutationObserver(enhanceAgents).observe(agents, { childList: true });

  /* ---------- Live server status from GET /health ---------- */
  const api = String((window.BIONUCLEI_CONFIG || {}).apiBase || '').replace(/\/$/, '');
  const pill = qs('[data-server-pill]');
  const setText = (sel, text) => { const n = qs(sel); if (n) n.textContent = text; };
  function setServer(state, label, note) {
    if (pill) { pill.dataset.state = state; const span = qs('span', pill); if (span) span.textContent = label; }
    setText('[data-server-status]', label);
    if (note) setText('[data-server-note]', note);
    const retry = qs('[data-server-retry]');
    if (retry) retry.hidden = state !== 'offline';
  }
  async function probe(timeoutMs) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(`${api}/health`, { cache: 'no-store', signal: controller.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } finally { clearTimeout(timer); }
  }
  let checking = false;
  async function checkServer() {
    if (!api || checking) return;
    checking = true;
    setServer('checking', 'Checking server');
    const started = Date.now();
    const deadline = started + 150000;
    let attempt = 0;
    while (Date.now() < deadline) {
      attempt += 1;
      try {
        const health = await probe(20000);
        const ok = health.status === 'ok' && health.checkpoint_available;
        const waited = Math.round((Date.now() - started) / 1000);
        setServer(ok ? 'ready' : 'degraded', ok ? 'Server ready' : 'Server degraded',
          ok ? (waited > 5 ? `Server woke up after ${waited} s. Analysis is available.` : 'Analysis is available.')
             : 'The server is running but the model checkpoint is not loaded. Analysis will fail until it is restored.');
        setText('[data-server-checkpoint]', health.checkpoint_available ? 'Loaded' : 'Missing');
        const commit = String(health.render_git_commit || 'unknown');
        const dd = qs('[data-server-commit]');
        if (dd) { dd.innerHTML = ''; const code = document.createElement('code'); code.textContent = commit === 'unknown' ? 'unknown' : commit.slice(0, 7); dd.appendChild(code); }
        if (Number(health.max_upload_bytes) > 0) {
          const limit = fmtBytes(Number(health.max_upload_bytes));
          setText('[data-server-limit]', limit);
          qsa('[data-max-upload]').forEach(n => { n.textContent = `up to ${limit}`; });
          window.__BIONUCLEI_MAX_UPLOAD = Number(health.max_upload_bytes);
        }
        checking = false;
        return;
      } catch (_) {
        if (attempt === 1 || Date.now() - started > 6000) setServer('waking', 'Waking server', 'The server was asleep. Waking it now; this usually takes under a minute. You can sign in meanwhile.');
        await new Promise(r => setTimeout(r, Math.min(2000 * attempt, 8000)));
      }
    }
    setServer('offline', 'Server unreachable', 'The analysis server did not respond. Check again in a minute.');
    checking = false;
  }
  qs('[data-server-retry]')?.addEventListener('click', checkServer);

  function boot() { syncSteps(); checkServer(); setInterval(syncSteps, 700); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true }); else boot();
})();
