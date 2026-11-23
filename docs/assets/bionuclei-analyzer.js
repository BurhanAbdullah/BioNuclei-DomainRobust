(() => {
  'use strict';

  const cfg = window.BIONUCLEI_CONFIG || {};
  const api = String(cfg.apiBase || '').replace(/\/$/, '');
  let supa = null;
  let currentToken = '';
  let guestToken = '';
  let currentJob = '';
  let pollTimer = null;
  let pollBusy = false;
  let previewUrls = [];
  let measurementRows = [];
  let activeMetric = 'area';
  let roi = null;
  let roiStart = null;
  let draggingROI = false;
  let specialistVerified = false;
  let specialistVerificationReason = "Specialist artifact has not been verified for the selected job.";

  const $ = id => document.getElementById(id);
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
  const msg = (id, text) => { const n = $(id); if (n) n.innerHTML = `<div class="note">${escapeHtml(text)}</div>`; };
  const headers = () => currentToken ? { Authorization: `Bearer ${currentToken}` } : (guestToken ? { 'X-BioNuclei-Guest-Token': guestToken } : {});
  const authenticated = () => Boolean(currentToken || guestToken);

  function setAccessMode(mode) {
    document.querySelectorAll('[data-access-tab]').forEach(tab => {
      const selected = tab.dataset.accessTab === mode;
      tab.classList.toggle('is-active', selected);
      tab.setAttribute('aria-selected', String(selected));
      const panel = document.querySelector(`[data-access-panel="${tab.dataset.accessTab}"]`);
      if (panel) panel.hidden = !selected;
    });
  }

  function showWorkspace(account) {
    $('access').hidden = true;
    $('workspace').hidden = false;
    $('signout').hidden = !account;
    $('workspace').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function showAccess() {
    $('access').hidden = false;
    $('workspace').hidden = true;
    $('resultPanel').hidden = true;
    $('signout').hidden = true;
  }

  function clearLocalFile() {
    const input = $('image');
    if (input) input.value = '';
    $('fileInfo').hidden = true;
    $('nd2Controls').hidden = true;
  }

  function clearResult() {
    if (pollTimer) clearTimeout(pollTimer);
    pollTimer = null;
    pollBusy = false;
    previewUrls.forEach(URL.revokeObjectURL);
    previewUrls = [];
    measurementRows = [];
    specialistVerified = false;
    specialistVerificationReason = "Specialist artifact has not been verified for the selected job.";
    const downloadButton = $('downloadButton');
    if (downloadButton) downloadButton.disabled = true;
    roi = null;
    $('resultPanel').hidden = true;
    $('overlayPreview').removeAttribute('src');
    $('maskPreview').removeAttribute('src');
    $('measurementTools').hidden = true;
    $('measurementBody').innerHTML = '';
    $('measurementCount').textContent = 'Waiting for measurement data.';
    $('roiSummary').textContent = 'Draw a rectangle on the viewer to inspect a spatial subset.';
    const canvas = $('analysisCanvas');
    if (canvas) { canvas.width = 0; canvas.height = 0; }
  }

  async function jsonFetch(path, options = {}) {
    const r = await fetch(api + path, { ...options, headers: { ...headers(), ...(options.headers || {}) }, cache: 'no-store' });
    let body = null;
    try { body = await r.json(); } catch (_) {}
    if (!r.ok) throw new Error(body?.detail || body?.error || `Request failed (${r.status})`);
    return body;
  }

  async function ensureGuest() {
    if (guestToken) return true;
    if (!api) { msg('guestMsg', 'The production analyzer endpoint is not configured.'); return false; }
    try {
      const body = await jsonFetch('/guest-session', { method: 'POST' });
      if (!body?.guest_token) throw new Error('Guest session was not created.');
      guestToken = body.guest_token;
      currentToken = '';
      showWorkspace(false);
      msg('guestMsg', 'Guest session ready. Your analysis job is disposable and tied to this session.');
      return true;
    } catch (e) { msg('guestMsg', e.message); return false; }
  }

  const UNREACHABLE = 'Account sign-in is unavailable right now. You can continue as guest and analyze images without an account.';
  const authFailure = (error) => /failed to fetch|networkerror|load failed|fetch failed/i.test(error?.message || '') || error?.name === 'AuthRetryableFetchError' || error?.status === 0;

  async function signUp() {
    if (!supa) { msg('signupMsg', 'Account service is unavailable. Guest analysis remains available.'); return; }
    const email = $('signupEmail').value.trim();
    const password = $('signupPassword').value;
    if (!email || password.length < 8) { msg('signupMsg', 'Enter an email and a password of at least 8 characters.'); return; }
    let data, error;
    try { ({ data, error } = await supa.auth.signUp({ email, password, options: { emailRedirectTo: location.href } })); }
    catch (_) { msg('signupMsg', UNREACHABLE); return; }
    if (error) { msg('signupMsg', authFailure(error) ? UNREACHABLE : error.message); return; }
    if (data.session) {
      currentToken = data.session.access_token;
      guestToken = '';
      showWorkspace(true);
      msg('signupMsg', 'Account created and signed in.');
    } else {
      msg('signupMsg', 'Account created. Confirm your email if required, then use Sign in.');
    }
  }

  async function signIn() {
    if (!supa) { msg('loginMsg', 'Account service is unavailable. Guest analysis remains available.'); return; }
    const email = $('loginEmail').value.trim();
    const password = $('loginPassword').value;
    if (!email || !password) { msg('loginMsg', 'Enter your email and password.'); return; }
    let data, error;
    try { ({ data, error } = await supa.auth.signInWithPassword({ email, password })); }
    catch (_) { msg('loginMsg', UNREACHABLE); return; }
    if (error) { msg('loginMsg', authFailure(error) ? UNREACHABLE : /invalid login credentials/i.test(error.message) ? 'Email or password is incorrect.' : error.message); return; }
    currentToken = data.session?.access_token || '';
    guestToken = '';
    if (currentToken) showWorkspace(true);
  }

  async function resetPassword() {
    if (!supa) { msg('loginMsg', 'Account service is unavailable.'); return; }
    const email = $('loginEmail').value.trim();
    if (!email) { msg('loginMsg', 'Enter your email first.'); return; }
    let error;
    try { ({ error } = await supa.auth.resetPasswordForEmail(email, { redirectTo: location.href })); }
    catch (_) { msg('loginMsg', UNREACHABLE); return; }
    if (error) msg('loginMsg', authFailure(error) ? UNREACHABLE : error.message);
    else msg('loginMsg', 'If an account exists for this email, a password reset link is on its way.');
  }

  async function signOut() {
    if (supa) await supa.auth.signOut();
    currentToken = '';
    guestToken = '';
    currentJob = '';
    clearLocalFile();
    clearResult();
    showAccess();
    setAccessMode('signin');
  }

  function setFile(file) {
    if (!file) { clearLocalFile(); return; }
    const lower = file.name.toLowerCase();
    if (!['.tif','.tiff','.nd2'].some(ext => lower.endsWith(ext))) {
      clearLocalFile();
      msg('runMsg', 'Unsupported file. Choose a TIFF (.tif/.tiff) or Nikon ND2 (.nd2).');
      return;
    }
    $('fileInfo').hidden = false;
    $('fileInfo').textContent = `${file.name} · ${(file.size / 1048576).toFixed(2)} MiB · held in browser memory only`;
    $('nd2Controls').hidden = !lower.endsWith('.nd2');
  }

  function validateNd2Inputs() {
    for (const id of ['nd2Channel','nd2Time','nd2Z','nd2Field']) {
      const value = Number($(id).value);
      if (!Number.isInteger(value) || value < 0) return false;
    }
    return true;
  }

  async function runAnalysis() {
    const file = $('image').files[0];
    if (!file) { msg('runMsg', 'Choose a TIFF or ND2 image first.'); return; }
    if (!api) { msg('runMsg', 'The production analyzer endpoint is not configured.'); return; }
    if (!authenticated()) { msg('runMsg', 'Choose Sign up, Sign in, or Guest first.'); $('access').scrollIntoView({ behavior: 'smooth' }); return; }
    if (!validateNd2Inputs()) { msg('runMsg', 'ND2 channel, time, Z and field must be non-negative integers.'); return; }

    clearResult();
    const fd = new FormData();
    fd.append('image', file);
    fd.append('research_consent', 'false');
    fd.append('algorithm_profile', 'auto');
    fd.append('analysis_modules', 'nuclei,morphology,intensity');
    fd.append('nd2_channel', $('nd2Channel').value);
    fd.append('nd2_time', $('nd2Time').value);
    fd.append('nd2_z', $('nd2Z').value);
    fd.append('nd2_field', $('nd2Field').value);

    $('analyzeButton').disabled = true;
    msg('runMsg', 'Uploading for transient analysis…');
    try {
      const body = await jsonFetch('/analyze', { method: 'POST', body: fd });
      if (!body?.job_id) throw new Error('Analyzer did not return a job identifier.');
      currentJob = body.job_id;
      clearLocalFile();
      msg('runMsg', 'Analysis queued. The browser is polling the owned job for completion.');
      await pollOnce();
    } catch (e) {
      $('analyzeButton').disabled = false;
      msg('runMsg', e.message);
    }
  }

  async function pollOnce() {
    if (!currentJob || pollBusy) return;
    pollBusy = true;
    try {
      const body = await jsonFetch(`/jobs/${encodeURIComponent(currentJob)}`);
      const status = String(body?.status || '').toLowerCase();
      msg('runMsg', `Analysis status: ${status || 'unknown'}`);
      if (status === 'completed') {
        $('analyzeButton').disabled = false;
        await showResult(body);
        return;
      }
      if (status === 'failed') {
        $('analyzeButton').disabled = false;
        msg('runMsg', body.error || 'Analysis failed. No result was loaded.');
        return;
      }
      pollTimer = setTimeout(() => { pollBusy = false; pollOnce(); }, 2000);
    } catch (e) {
      $('analyzeButton').disabled = false;
      msg('runMsg', e.message);
    } finally {
      if (!pollTimer) pollBusy = false;
    }
  }

  async function fetchBlob(path) {
    const r = await fetch(api + path, { headers: headers(), cache: 'no-store' });
    if (!r.ok) throw new Error(`Could not retrieve ${path.split('/').pop()} (${r.status}).`);
    return r.blob();
  }

  async function fetchText(path) {
    const r = await fetch(api + path, { headers: headers(), cache: 'no-store' });
    if (!r.ok) throw new Error(`Could not retrieve ${path.split('/').pop()} (${r.status}).`);
    return r.text();
  }

  function parseCSV(text) {
    const trimmed = String(text || '').trim();
    if (!trimmed) return [];
    const lines = trimmed.split(/\r?\n/);
    const parseLine = line => {
      const out = []; let cur = ''; let quote = false;
      for (let i = 0; i < line.length; i++) {
        const c = line[i];
        if (c === '"' && line[i + 1] === '"') { cur += '"'; i++; continue; }
        if (c === '"') { quote = !quote; continue; }
        if (c === ',' && !quote) { out.push(cur); cur = ''; } else cur += c;
      }
      out.push(cur);
      return out;
    };
    const head = parseLine(lines[0]);
    return lines.slice(1).filter(Boolean).map(line => {
      const values = parseLine(line); const row = {};
      head.forEach((h, i) => { row[h] = values[i] ?? ''; });
      return row;
    });
  }

  const number = (row, key) => { const n = Number(row[key]); return Number.isFinite(n) ? n : null; };
  function normalize(rows) {
    return rows.map((r, i) => ({
      id: number(r, 'label') ?? i + 1,
      x: number(r, 'centroid-1'), y: number(r, 'centroid-0'),
      area: number(r, 'area'), perimeter: number(r, 'perimeter'),
      eccentricity: number(r, 'eccentricity'), solidity: number(r, 'solidity'), circularity: number(r, 'circularity'),
      mean_intensity: number(r, 'mean_intensity'), max_intensity: number(r, 'max_intensity'), min_intensity: number(r, 'min_intensity')
    }));
  }

  function metricValue(row) {
    if (activeMetric === 'intensity') return row.mean_intensity;
    if (activeMetric === 'circularity') return row.circularity;
    if (activeMetric === 'eccentricity') return row.eccentricity;
    return row.area;
  }

  function fmt(value) { return value == null ? '—' : Number(value).toFixed(2); }

  function renderTable() {
    const body = $('measurementBody');
    const rows = measurementRows.slice(0, 500);
    body.innerHTML = rows.map(r => `<tr><td>${escapeHtml(r.id)}</td><td>${fmt(r.area)}</td><td>${fmt(r.circularity)}</td><td>${fmt(r.eccentricity)}</td><td>${fmt(r.mean_intensity)}</td><td>${fmt(r.x)}, ${fmt(r.y)}</td></tr>`).join('');
    $('measurementCount').textContent = `${measurementRows.length.toLocaleString()} nuclei · first ${Math.min(500, measurementRows.length).toLocaleString()} shown`;
  }

  function drawCanvas() {
    const canvas = $('analysisCanvas');
    const img = $('overlayPreview');
    if (!canvas || !img || !img.naturalWidth) return;
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const values = measurementRows.map(metricValue).filter(v => v != null);
    if (values.length) {
      const min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
      measurementRows.forEach(row => {
        if (row.x == null || row.y == null) return;
        const value = metricValue(row);
        if (value == null) return;
        const t = (value - min) / span;
        ctx.beginPath();
        ctx.arc(row.x, row.y, Math.max(2, Math.min(8, 2 + Math.sqrt(Math.max(row.area || 1, 1)) / 12)), 0, Math.PI * 2);
        ctx.fillStyle = `hsl(${220 - 210 * t} 80% 50% / 0.65)`;
        ctx.fill();
      });
    }
    if (roi) {
      ctx.strokeStyle = 'white';
      ctx.lineWidth = Math.max(2, canvas.width / 500);
      ctx.setLineDash([8, 6]);
      ctx.strokeRect(roi.x, roi.y, roi.w, roi.h);
      ctx.setLineDash([]);
    }
  }

  function setupROI() {
    const canvas = $('analysisCanvas');
    canvas.addEventListener('pointerdown', event => {
      const rect = canvas.getBoundingClientRect();
      roiStart = { x: (event.clientX - rect.left) * canvas.width / rect.width, y: (event.clientY - rect.top) * canvas.height / rect.height };
      draggingROI = true;
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', event => {
      if (!draggingROI) return;
      const rect = canvas.getBoundingClientRect();
      const x = (event.clientX - rect.left) * canvas.width / rect.width;
      const y = (event.clientY - rect.top) * canvas.height / rect.height;
      roi = { x: Math.min(roiStart.x, x), y: Math.min(roiStart.y, y), w: Math.abs(x - roiStart.x), h: Math.abs(y - roiStart.y) };
      drawCanvas();
    });
    canvas.addEventListener('pointerup', () => { if (draggingROI) { draggingROI = false; updateROI(); } });
    canvas.addEventListener('pointercancel', () => { draggingROI = false; });
  }

  function updateROI() {
    if (!roi) return;
    const inside = measurementRows.filter(r => r.x != null && r.y != null && r.x >= roi.x && r.x <= roi.x + roi.w && r.y >= roi.y && r.y <= roi.y + roi.h);
    const meanArea = inside.length ? inside.reduce((sum, r) => sum + (r.area || 0), 0) / inside.length : null;
    const meanIntensity = inside.length ? inside.reduce((sum, r) => sum + (r.mean_intensity || 0), 0) / inside.length : null;
    $('roiSummary').textContent = `ROI: ${inside.length.toLocaleString()} nuclei · mean area ${fmt(meanArea)} px² · mean intensity ${fmt(meanIntensity)}`;
  }

  function setMetric(metric) {
    activeMetric = metric;
    document.querySelectorAll('[data-heatmap]').forEach(button => button.classList.toggle('is-active', button.dataset.heatmap === metric));
    drawCanvas();
  }

  async function showResult(job) {
    const result = job.result || {};
    const reports = result.reports || {};
    const verifier = window.BIONUCLEI_SPECIALIST_VERIFICATION;
    let verifiedExpert = null;
    specialistVerified = false;
    specialistVerificationReason = "Specialist verifier is unavailable.";
    if (verifier && typeof verifier.verifySpecialistArtifact === "function") {
      const verification = await verifier.verifySpecialistArtifact({
        job,
        result,
        embedded: result.expert_agents,
        fetchJson: path => jsonFetch(path),
        cryptoApi: window.crypto
      });
      if (verification && verification.ok === true) {
        specialistVerified = true;
        specialistVerificationReason = verification.reason || "Specialist evidence verified.";
        verifiedExpert = verification.artifact;
      } else {
        specialistVerificationReason = verification?.reason || "Specialist evidence verification failed.";
      }
    }
    $('downloadButton').disabled = !specialistVerified;
    $('resultPanel').hidden = false;
    $('nucleusCount').textContent = reports.nuclei_count ?? result.n_instances ?? 'Not available';
    const shape = result.image_shape || result.input_metadata?.selected_plane_shape;
    $('resultShape').textContent = Array.isArray(shape) ? shape.join(' × ') : '2-D plane';
    $('reportCount').textContent = Array.isArray(result.analysis_modules) ? result.analysis_modules.length : 0;
    const agentContainer = $('agentDetails');
    agentContainer.replaceChildren();
    const expertReport = verifiedExpert || {};
    const agents = Array.isArray(expertReport.agents)
      ? expertReport.agents
      : (Array.isArray(expertReport.findings) ? expertReport.findings : []);
    const appendList = (parent, label, values) => {
      if (!values.length) return;
      const heading = document.createElement('h5');
      heading.textContent = label;
      parent.appendChild(heading);
      const list = document.createElement('ul');
      values.forEach(value => {
        const item = document.createElement('li');
        item.textContent = value && typeof value === 'object' ? JSON.stringify(value) : String(value);
        list.appendChild(item);
      });
      parent.appendChild(list);
    };
    if (!specialistVerified) {
      const failed = document.createElement('p');
      failed.setAttribute('role', 'alert');
      failed.textContent = `Specialist evidence was not verified for this job: ${specialistVerificationReason}. Specialist findings and downloads are withheld.`;
      agentContainer.appendChild(failed);
    } else if (agents.length) {
      const ROLES = {
        image_quality_agent: 'Checks bit depth, dynamic range, saturation and whether the image suits analysis.',
        segmentation_quality_agent: 'Checks the instance mask for fragments, merges and edge effects.',
        morphology_agent: 'Summarizes nuclear size and shape.',
        intensity_agent: 'Summarizes nuclear stain intensity.',
        population_agent: 'Describes the population: counts, spread and spatial layout.',
        biological_interpretation_agent: 'States what the measurements can and cannot support biologically.',
        scientific_review_agent: 'Audits every claim against the measured evidence and training provenance.',
        report_agent: 'Assembles the report from verified values only.'
      };
      const prettyName = raw => {
        const words = String(raw || 'specialist').replace(/_agent$/i, '').split(/[_\s]+/).filter(Boolean);
        const text = words.join(' ');
        const name = text.charAt(0).toUpperCase() + text.slice(1);
        return /review$/i.test(name) ? name : name + ' review';
      };
      const tidyNumber = value => {
        const n = Number(value);
        if (!Number.isFinite(n) || String(value).trim() === '') return String(value);
        if (Number.isInteger(n)) return n.toLocaleString();
        const abs = Math.abs(n);
        return n.toLocaleString(undefined, { maximumFractionDigits: abs >= 100 ? 1 : abs >= 1 ? 2 : 4 });
      };
      const tidyText = text => String(text).replace(/-?\d+\.\d{5,}/g, m => tidyNumber(m)).replace(/\s*pixels?\^2/g, ' px²').replace(/\bpx\^2/g, 'px²').replace(/([a-z])_([a-z])/g, '$1 $2');
      const prettyKey = ref => {
        const parts = String(ref).split('.').filter(p => !/^(reports|adaptive_plan|raw_image)$/.test(p));
        return parts.map(p => p.replace(/_/g, ' ')).join(' · ') || String(ref);
      };
      const prettyUnit = unit => {
        const u = String(unit || '').replace(/_/g, ' ').trim();
        if (!u || /^(unitless|fraction|raw intensity units?)$/i.test(u)) return '';
        return ' ' + u.replace(/pixels?\^2|px\^2/g, 'px²');
      };
      agents.slice(0, 8).forEach(agent => {
        const card = document.createElement('section');
        card.className = 'agent-finding';
        const key = String(agent.agent || agent.name || '').toLowerCase();
        const title = document.createElement('h4');
        title.textContent = prettyName(agent.agent || agent.name);
        const status = agent.status ?? agent.execution_status;
        const chip = document.createElement('span');
        const ok = String(status || '').toLowerCase() === 'completed';
        chip.className = 'agent-status' + (ok ? '' : ' is-other');
        chip.textContent = status == null ? 'Status not reported' : (ok ? 'Completed' : String(status));
        title.appendChild(chip);
        card.appendChild(title);
        if (ROLES[key]) {
          const role = document.createElement('p');
          role.className = 'agent-role';
          role.textContent = ROLES[key];
          card.appendChild(role);
        }
        const observations = Array.isArray(agent.observations)
          ? agent.observations
          : [agent.statement ?? agent.finding ?? agent.summary].filter(value => value != null && String(value).trim() !== '');
        appendList(card, 'Findings', observations.map(tidyText));
        appendList(card, 'Limitations', Array.isArray(agent.limitations) ? agent.limitations.map(tidyText) : []);
        const claims = Array.isArray(agent.quantitative_claims) ? agent.quantitative_claims : [];
        const references = Array.isArray(agent.evidence_references)
          ? agent.evidence_references
          : (Array.isArray(agent.evidence_refs) ? agent.evidence_refs : []);
        const digest = agent.evidence_digest || agent.evidence_sha256 || agent.sha256;
        const trail = document.createElement('details');
        const summary = document.createElement('summary');
        summary.textContent = `Evidence trail · ${claims.length} verified value${claims.length === 1 ? '' : 's'}`;
        trail.appendChild(summary);
        if (claims.length) {
          const table = document.createElement('table');
          table.className = 'evidence-table';
          claims.forEach(claim => {
            const row = table.insertRow();
            row.insertCell().textContent = prettyKey(claim.reference);
            row.insertCell().textContent = tidyNumber(claim.value) + prettyUnit(claim.unit);
          });
          trail.appendChild(table);
        }
        if (references.length) appendList(trail, 'Sources', references.map(prettyKey));
        const digestLine = document.createElement('p');
        digestLine.className = 'digest';
        digestLine.textContent = digest ? `Evidence SHA-256: ${String(digest)}` : 'Evidence SHA-256: not included in this result schema.';
        trail.appendChild(digestLine);
        card.appendChild(trail);
        agentContainer.appendChild(card);
      });
    } else {
      const empty = document.createElement('p');
      empty.textContent = 'No specialist findings were returned for this job. Do not treat this result as specialist-reviewed.';
      agentContainer.appendChild(empty);
    }
    if (typeof expertReport.evidence_policy === 'string' && expertReport.evidence_policy.trim()) {
      const policy = document.createElement('p');
      policy.textContent = expertReport.evidence_policy;
      agentContainer.appendChild(policy);
    }
    const profile = result.adaptive_plan?.profile;
    if (profile && typeof profile === 'object') {
      const card = document.createElement('section');
      card.className = 'raw-image-profile';
      const title = document.createElement('h4');
      title.textContent = 'Raw image intensity profile';
      card.appendChild(title);
      const fields = [
        ['Shape', Array.isArray(profile.shape) ? profile.shape.join(' × ') : profile.shape],
        ['Data type', profile.dtype],
        ['Minimum', profile.min],
        ['1st percentile', profile.p01],
        ['Median', profile.median],
        ['99.5th percentile', profile.p995],
        ['Maximum', profile.max],
        ['Mean', profile.mean],
        ['Standard deviation', profile.std],
        ['Saturation fraction', profile.saturation_fraction],
        ['Zero fraction', profile.zero_fraction],
        ['All values finite', profile.finite]
      ];
      const list = document.createElement('dl');
      fields.forEach(([label, value]) => {
        if (value === undefined || value === null) return;
        const term = document.createElement('dt');
        term.textContent = label;
        const detail = document.createElement('dd');
        const n = Number(value);
        detail.textContent = typeof value === 'boolean' ? (value ? 'Yes' : 'No')
          : (typeof value === 'number' && Number.isFinite(n)) ? (Number.isInteger(n) ? n.toLocaleString() : n.toLocaleString(undefined, { maximumFractionDigits: Math.abs(n) >= 100 ? 1 : 4 }))
          : String(value);
        const pair = document.createElement('div');
        pair.append(term, detail);
        list.appendChild(pair);
      });
      card.appendChild(list);
      agentContainer.appendChild(card);
    }

    try {
      previewUrls.forEach(URL.revokeObjectURL);
      previewUrls = [];
      const [overlay, mask, csv] = await Promise.all([
        fetchBlob(`/jobs/${encodeURIComponent(job.job_id)}/preview/overlay.tif`),
        fetchBlob(`/jobs/${encodeURIComponent(job.job_id)}/preview/segmentation_mask.tif`),
        fetchText(`/jobs/${encodeURIComponent(job.job_id)}/files/nuclei_analysis.csv`)
      ]);
      const overlayUrl = URL.createObjectURL(overlay);
      const maskUrl = URL.createObjectURL(mask);
      previewUrls = [overlayUrl, maskUrl];
      $('overlayPreview').src = overlayUrl;
      $('maskPreview').src = maskUrl;
      measurementRows = normalize(parseCSV(csv));
      renderTable();
      $('measurementTools').hidden = false;
      $('overlayPreview').onload = drawCanvas;
      if ($('overlayPreview').complete) drawCanvas();
      msg('resultMsg', 'Analysis complete. The evidence viewer is ready.');
    } catch (e) {
      msg('resultMsg', `Analysis completed, but the interactive evidence layer could not be loaded: ${e.message}. You can still download the complete report.`);
    }
    $('resultPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function downloadReport() {
    if (!currentJob) return msg('resultMsg', 'No analysis result is selected.');
    if (!specialistVerified) return msg('resultMsg', 'Download withheld: specialist evidence for this job has not passed verification.');
    try {
      const blob = await fetchBlob(`/jobs/${encodeURIComponent(currentJob)}/download`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `bionuclei-${currentJob}.zip`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
      msg('resultMsg', 'Report downloaded to your device. The server copy remains available until you delete it or it expires.');
    } catch (e) { msg('resultMsg', e.message); }
  }

  async function deleteJob() {
    if (!currentJob) return;
    try {
      await jsonFetch(`/jobs/${encodeURIComponent(currentJob)}`, { method: 'DELETE' });
      clearResult();
      currentJob = '';
      msg('runMsg', 'Analysis data deleted from the server.');
    } catch (e) { msg('resultMsg', e.message); }
  }

  async function init() {
    if (window.supabase && cfg.supabaseUrl && cfg.supabasePublishableKey) {
      supa = window.supabase.createClient(cfg.supabaseUrl, cfg.supabasePublishableKey, { auth: { persistSession: false, autoRefreshToken: true, detectSessionInUrl: true } });
      const { data } = await supa.auth.getSession();
      if (data.session?.access_token) { currentToken = data.session.access_token; showWorkspace(true); }
      supa.auth.onAuthStateChange((_event, session) => {
        currentToken = session?.access_token || '';
        if (currentToken) { guestToken = ''; showWorkspace(true); }
      });
    }
    if (!api) msg('runMsg', 'The production analyzer endpoint is not configured.');

    document.querySelectorAll('[data-access-tab]').forEach(tab => tab.addEventListener('click', () => setAccessMode(tab.dataset.accessTab)));
    $('signupButton').addEventListener('click', signUp);
    $('signinButton').addEventListener('click', signIn);
    $('resetButton').addEventListener('click', resetPassword);
    const submitOnEnter = (ids, action) => ids.forEach(id => $(id).addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); action(); } }));
    submitOnEnter(['loginEmail', 'loginPassword'], signIn);
    submitOnEnter(['signupEmail', 'signupPassword'], signUp);
    $('guestButton').addEventListener('click', ensureGuest);
    $('signout').addEventListener('click', signOut);
    $('image').addEventListener('change', e => setFile(e.target.files[0]));
    $('analyzeButton').addEventListener('click', runAnalysis);
    $('clearButton').addEventListener('click', clearLocalFile);
    $('downloadButton').addEventListener('click', downloadReport);
    $('deleteButton').addEventListener('click', deleteJob);
    document.querySelectorAll('[data-heatmap]').forEach(button => button.addEventListener('click', () => setMetric(button.dataset.heatmap)));
    $('clearROI').addEventListener('click', () => { roi = null; $('roiSummary').textContent = 'Draw a rectangle on the viewer to inspect a spatial subset.'; drawCanvas(); });
    setupROI();
    setMetric('area');
  }

  // Narrow bridge for the experiment tray (assets/experiment.js). It reuses
  // this session's authorization without exposing the token itself.
  window.BioNucleiAnalyzer = Object.freeze({
    authenticated: () => authenticated(),
    request: (path, options) => jsonFetch(path, options),
    async openJob(jobId) {
      clearResult();
      currentJob = String(jobId);
      const body = await jsonFetch(`/jobs/${encodeURIComponent(currentJob)}`);
      if (String(body?.status || '').toLowerCase() !== 'completed') throw new Error('This analysis is not complete.');
      await showResult(body);
    }
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
