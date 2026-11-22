/* BioNuclei experiment tray.
 * Recognises several microscopy files in the browser, numbers them, lets the
 * user choose which to analyse, runs the chosen ones one after another on the
 * BioNuclei server and builds an experiment summary from the returned results.
 *
 * Nothing is uploaded until "Analyze selected". Files are held in page memory
 * only (no IndexedDB/localStorage). The server repeats every check and is the
 * final authority on suitability.
 */
(() => {
  'use strict';
  const qs = (s, r = document) => r.querySelector(s);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const MAX_ITEMS = 20;
  const MIN_SIDE = 32;
  const items = [];
  let fluor = [];
  let running = false;
  let stopRequested = false;

  fetch('assets/fluorophores.json').then(r => r.ok ? r.json() : []).then(t => { fluor = Array.isArray(t) ? t : []; items.forEach(i => { annotateChannels(i); render(); }); }).catch(() => {});

  /* ---------- Fluorophore lookup (table shared with the server) ---------- */
  const norm = t => String(t || '').toLowerCase().replace(/[\s_\-]+/g, ' ').trim();
  function identify(name) {
    const n = ` ${norm(name)} `, compact = n.replace(/ /g, '');
    const pairs = fluor.flatMap(e => e.aliases.map(a => [norm(a), e])).sort((a, b) => b[0].length - a[0].length);
    for (const [a, e] of pairs) {
      if (a.replace(/ /g, '').length <= 3) { if (new RegExp(`(^|[^a-z0-9])${a.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}([^a-z0-9]|$)`).test(n)) return e; }
      else if (n.includes(` ${a} `) || compact.includes(a.replace(/ /g, ''))) return e;
    }
    return null;
  }
  function identifyByEmission(em) {
    if (!em) return [];
    return fluor.filter(e => Math.abs(e.em - em) <= 12);
  }

  /* ---------- File-name labels: condition and replicate ---------- */
  function parseName(name) {
    const stem = name.replace(/\.(ome\.)?(tiff?|nd2)$/i, '');
    const tokens = stem.split(/[_\-\s.]+/).filter(Boolean);
    let replicate = '';
    const keep = [];
    tokens.forEach(t => {
      const lower = t.toLowerCase();
      const rep = lower.match(/^(rep|replicate|r|n|well|pos|position|field|f|s|img|image)?0*(\d{1,3})$/);
      if (rep) { replicate = rep[2]; return; }
      if (/^(c|ch|w)\d+$/.test(lower) || lower === 'ome' || lower === 'max' || lower === 'mip') return;
      if (identify(t)) return;
      keep.push(t);
    });
    return { condition: keep.join('_') || 'unlabelled', replicate };
  }

  /* ---------- Minimal TIFF header reader ---------- */
  function readTiffHeader(buf) {
    const dv = new DataView(buf);
    if (buf.byteLength < 8) throw new Error('File is too short to be a TIFF.');
    const order = dv.getUint16(0);
    const le = order === 0x4949;
    if (!le && order !== 0x4d4d) throw new Error('Not a TIFF file (bad byte-order mark).');
    const magic = dv.getUint16(2, le);
    if (magic === 43) return { bigtiff: true };
    if (magic !== 42) throw new Error('Not a TIFF file.');
    const u16 = o => dv.getUint16(o, le), u32 = o => dv.getUint32(o, le);
    const typeSize = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 11: 4, 12: 8, 16: 8 };
    let offset = u32(4), pages = 0, first = null;
    const seen = new Set();
    while (offset && offset + 2 <= buf.byteLength && pages < 5000 && !seen.has(offset)) {
      seen.add(offset);
      const count = u16(offset);
      if (!first) {
        first = {};
        for (let i = 0; i < count; i++) {
          const e = offset + 2 + i * 12;
          if (e + 12 > buf.byteLength) break;
          const tag = u16(e), type = u16(e + 2), n = u32(e + 4);
          const size = (typeSize[type] || 1) * n;
          const at = size > 4 ? u32(e + 8) : e + 8;
          const read = k => type === 3 ? u16(at + k * 2) : type === 4 ? u32(at + k * 4) : dv.getUint8(at + k);
          if (tag === 270 && type === 2) first.description = new TextDecoder().decode(new Uint8Array(buf, at, Math.min(n, buf.byteLength - at))).replace(/\0+$/, '');
          else if ([256, 257, 258, 259, 262, 277, 339].includes(tag) && at + size <= buf.byteLength) first[tag] = read(0);
        }
      }
      pages += 1;
      const next = offset + 2 + count * 12;
      offset = next + 4 <= buf.byteLength ? u32(next) : 0;
    }
    if (!first) throw new Error('TIFF has no image directory.');
    return { width: first[256], height: first[257], bits: first[258] || 1, compression: first[259], photometric: first[262], spp: first[277] || 1, sampleFormat: first[339] || 1, description: first.description || '', pages };
  }

  function describeAxes(h) {
    const d = h.description;
    const axes = { C: 1, Z: 1, T: 1 };
    const channels = [];
    let flavour = 'TIFF';
    if (/<OME[\s>]/.test(d)) {
      flavour = 'OME-TIFF';
      const px = d.match(/<Pixels\b[^>]*>/);
      if (px) ['C', 'Z', 'T'].forEach(a => { const m = px[0].match(new RegExp(`Size${a}="(\\d+)"`)); if (m) axes[a] = +m[1]; });
      (d.match(/<Channel\b[^>]*>/g) || []).forEach((tag, i) => {
        const get = k => (tag.match(new RegExp(`${k}="([^"]*)"`)) || [])[1];
        channels.push({ index: i, name: get('Fluor') || get('Name') || '', emission: get('EmissionWavelength') ? +get('EmissionWavelength') : null, source: 'OME-XML' });
      });
    } else if (/^ImageJ=/m.test(d)) {
      flavour = 'ImageJ TIFF';
      const num = k => { const m = d.match(new RegExp(`^${k}=(\\d+)`, 'm')); return m ? +m[1] : 1; };
      axes.C = num('channels'); axes.Z = num('slices'); axes.T = num('frames');
      if (axes.C === 1 && axes.Z === 1 && axes.T === 1 && h.pages > 1) axes.Z = h.pages;
    } else if (h.pages > 1) {
      axes.Z = h.pages;
    }
    return { flavour, axes, channels };
  }

  /* ---------- Contrast check on a decoded preview ---------- */
  let utifLoading = null;
  function loadUtif() {
    if (window.UTIF) return Promise.resolve();
    if (!utifLoading) utifLoading = new Promise((res, rej) => { const s = document.createElement('script'); s.src = 'https://cdn.jsdelivr.net/npm/utif@3.1.0/UTIF.min.js'; s.onload = res; s.onerror = () => { utifLoading = null; rej(new Error('Preview decoder unavailable')); }; document.head.appendChild(s); });
    return utifLoading;
  }
  function contrast(values) {
    const step = Math.max(1, Math.floor(values.length / 60000));
    const s = [];
    for (let i = 0; i < values.length; i += step) s.push(values[i]);
    s.sort((a, b) => a - b);
    const q = p => s[Math.min(s.length - 1, Math.floor(s.length * p))];
    const p01 = q(0.01), med = q(0.5), p995 = q(0.995);
    const mean = s.reduce((a, b) => a + b, 0) / s.length;
    const sd = Math.sqrt(s.reduce((a, b) => a + (b - mean) ** 2, 0) / s.length) || 0;
    const skew = sd ? s.reduce((a, b) => a + ((b - mean) / sd) ** 3, 0) / s.length : 0;
    return { p01, p995, relMedian: p995 > p01 ? (med - p01) / (p995 - p01) : 0, skew, sd };
  }
  async function decodePreview(item, buf, h) {
    await loadUtif();
    const ifds = UTIF.decode(buf);
    const ifd = ifds[0];
    UTIF.decodeImage(buf, ifd);
    const w = ifd.width, hgt = ifd.height, n = w * hgt;
    let grey;
    if (h.bits === 16 && h.spp === 1 && ifd.data) {
      const dv = new DataView(ifd.data.buffer, ifd.data.byteOffset, ifd.data.byteLength);
      grey = new Float32Array(n);
      for (let i = 0; i < n; i++) grey[i] = dv.getUint16(i * 2, true);
    } else {
      const rgba = UTIF.toRGBA8(ifd);
      grey = new Float32Array(n);
      for (let i = 0; i < n; i++) grey[i] = (rgba[i * 4] + rgba[i * 4 + 1] + rgba[i * 4 + 2]) / 3;
    }
    const c = contrast(grey);
    const scale = Math.min(1, 96 / Math.max(w, hgt));
    const tw = Math.max(1, Math.round(w * scale)), th = Math.max(1, Math.round(hgt * scale));
    const canvas = document.createElement('canvas');
    canvas.width = tw; canvas.height = th;
    const ctx = canvas.getContext('2d');
    const out = ctx.createImageData(tw, th);
    const span = Math.max(1e-9, c.p995 - c.p01);
    for (let y = 0; y < th; y++) for (let x = 0; x < tw; x++) {
      const v = grey[Math.min(hgt - 1, Math.floor(y / scale)) * w + Math.min(w - 1, Math.floor(x / scale))];
      const g = Math.max(0, Math.min(255, Math.round((v - c.p01) * 255 / span)));
      const o = (y * tw + x) * 4;
      out.data[o] = out.data[o + 1] = out.data[o + 2] = g; out.data[o + 3] = 255;
    }
    ctx.putImageData(out, 0, 0);
    item.thumb = canvas.toDataURL('image/png');
    item.contrast = c;
  }

  /* ---------- Recognition ---------- */
  function annotateChannels(item) {
    const chans = (item.channels || []).map(ch => {
      const byName = identify(ch.name);
      const byEm = byName ? [] : identifyByEmission(ch.emission);
      return { ...ch, dye: byName ? byName.name : byEm.length === 1 ? byEm[0].name : byEm.length ? byEm.map(e => e.name).join(' / ') : '', nuclear: byName ? byName.nuclear : byEm.length && byEm.every(e => e.nuclear) ? true : byEm.length && byEm.every(e => !e.nuclear) ? false : null };
    });
    item.channelInfo = chans;
    const nuclear = chans.filter(c => c.nuclear === true);
    if (nuclear.length === 1) { item.nuclearChannel = nuclear[0].index; if (!item.channelTouched) item.plane.channel = nuclear[0].index; }
    const fileDye = identify(item.file.name);
    item.fileDye = fileDye ? fileDye.name : '';
    if (fileDye && !fileDye.nuclear && item.verdict === 'ready') item.warnings.push(`File name suggests ${fileDye.name}, which is not a nuclear stain.`);
  }

  async function recognise(item) {
    const f = item.file;
    const lower = f.name.toLowerCase();
    item.warnings = [];
    if (!/\.(tiff?|nd2)$/.test(lower)) { item.verdict = 'rejected'; item.reason = 'Unsupported format. Use TIFF/TIF or Nikon ND2.'; return; }
    const limit = window.__BIONUCLEI_MAX_UPLOAD || 64 * 1048576;
    if (f.size > limit) { item.verdict = 'rejected'; item.reason = `Larger than the ${Math.round(limit / 1048576)} MiB upload limit.`; return; }
    const buf = await f.arrayBuffer();
    const digest = await crypto.subtle.digest('SHA-256', buf);
    item.sha256 = Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, '0')).join('');
    const dupe = items.find(o => o !== item && o.sha256 === item.sha256);
    if (dupe) { item.verdict = 'duplicate'; item.reason = `Identical content to #${dupe.n}.`; return; }
    if (lower.endsWith('.nd2')) {
      item.kind = 'Nikon ND2'; item.verdict = 'plane';
      item.reason = 'ND2 axes and channel names are read on the server. Set the plane if you know it.';
      annotateChannels(item);
      return;
    }
    let h;
    try { h = readTiffHeader(buf); } catch (e) { item.verdict = 'rejected'; item.reason = e.message; return; }
    if (h.bigtiff) { item.kind = 'BigTIFF'; item.verdict = 'plane'; item.reason = 'BigTIFF details are checked on the server.'; return; }
    const { flavour, axes, channels } = describeAxes(h);
    item.kind = flavour; item.axes = axes; item.channels = channels; item.header = h;
    const rgb = h.spp >= 3 && h.photometric === 2;
    const dims = [`${h.width}×${h.height}`, `${h.bits}-bit`];
    if (rgb) dims.push('RGB');
    if (axes.C > 1) dims.push(`${axes.C} ch`);
    if (axes.Z > 1) dims.push(`${axes.Z} z`);
    if (axes.T > 1) dims.push(`${axes.T} t`);
    item.dims = dims.join(' · ');
    if (Math.min(h.width, h.height) < MIN_SIDE) { item.verdict = 'rejected'; item.reason = `Only ${h.width}×${h.height} px; needs ${MIN_SIDE} px per side.`; return; }
    if (h.sampleFormat === 3 && h.bits === 64) item.warnings.push('64-bit float data.');
    try { await decodePreview(item, buf, h); } catch (_) { item.warnings.push('Preview unavailable; the server will check contrast.'); }
    if (item.contrast) {
      if (item.contrast.sd === 0 || item.contrast.p995 === item.contrast.p01) { item.verdict = 'rejected'; item.reason = 'The first plane is blank (no intensity variation).'; return; }
      if (item.contrast.relMedian > 0.55 && item.contrast.skew < -0.5) { item.verdict = 'rejected'; item.reason = rgb ? 'Looks like a colour brightfield or stained-histology image (bright background, darker objects).' : 'Looks like brightfield or phase contrast (bright background, darker objects).'; return; }
    }
    item.verdict = (axes.C > 1 || axes.Z > 1 || axes.T > 1) ? 'plane' : 'ready';
    item.reason = item.verdict === 'plane' ? 'Multi-dimensional: one 2-D plane will be analysed.' : rgb ? 'RGB export: the server analyses the colour channel with the strongest signal.' : '2-D fluorescence plane.';
    annotateChannels(item);
    if (item.verdict === 'plane' && item.nuclearChannel != null) {
      const dye = (item.channelInfo.find(c => c.index === item.nuclearChannel) || {}).dye;
      item.verdict = 'ready';
      item.reason = `Nuclear stain found in channel ${item.nuclearChannel}${dye ? ` (${dye})` : ''}; that channel will be analysed. Change C, Z or T if needed.`;
    }
  }

  /* ---------- Rendering ---------- */
  const VERDICT = { pending: ['Checking…', 'is-pending'], ready: ['Ready', 'is-ready'], plane: ['Choose plane', 'is-plane'], rejected: ['Not suitable', 'is-rejected'], duplicate: ['Duplicate', 'is-rejected'] };
  const runnable = i => i.verdict === 'ready' || i.verdict === 'plane';
  function fmtNum(v, d = 1) { return v == null || !Number.isFinite(+v) ? '—' : (+v).toLocaleString(undefined, { maximumFractionDigits: d }); }

  function render() {
    const body = qs('[data-exp-body]');
    if (!body) return;
    qs('[data-exp-empty]').hidden = items.length > 0;
    qs('[data-exp-table]').hidden = items.length === 0;
    qs('[data-exp-actions]').hidden = items.length === 0;
    body.innerHTML = items.map(i => {
      const [label, cls] = VERDICT[i.verdict] || VERDICT.pending;
      const chans = (i.channelInfo || []).filter(c => c.dye).map(c => `<span class="ws-tag${c.nuclear ? ' is-nuclear' : ''}" title="Channel ${c.index}${c.emission ? `, emission ${c.emission} nm` : ''} (${esc(c.source)})">C${c.index} ${esc(c.dye)}</span>`).join('');
      const fileDye = i.fileDye ? `<span class="ws-tag" title="From the file name">${esc(i.fileDye)}</span>` : '';
      const multi = i.verdict === 'plane' || (i.axes && (i.axes.C > 1 || i.axes.Z > 1 || i.axes.T > 1));
      const plane = multi ? `<div class="ws-plane"><label>C<input type="number" min="0" value="${i.plane.channel}" data-plane="channel" data-n="${i.n}" aria-label="Channel for image ${i.n}"></label><label>Z<input type="number" min="0" value="${i.plane.z}" data-plane="z" data-n="${i.n}" aria-label="Z slice for image ${i.n}"></label><label>T<input type="number" min="0" value="${i.plane.time}" data-plane="time" data-n="${i.n}" aria-label="Time point for image ${i.n}"></label></div>` : '<span class="ws-muted-s">2-D</span>';
      let result = '<span class="ws-muted-s">Not run</span>';
      if (i.job.status === 'queued' || i.job.status === 'uploading') result = `<span class="ws-run">${esc(i.job.label || 'Queued')}</span>`;
      else if (i.job.status === 'completed') result = `<b>${fmtNum(i.job.nuclei, 0)}</b> nuclei<br><button type="button" class="ws-linkbtn" data-open="${i.n}">Open result</button>`;
      else if (i.job.status === 'failed') result = `<span class="ws-err" title="${esc(i.job.error)}">Failed</span><br><small>${esc(i.job.error).slice(0, 110)}</small>`;
      else if (i.job.status === 'deleted') result = '<span class="ws-muted-s">Deleted from server</span>';
      return `<tr class="${cls}">
        <td><input type="checkbox" data-pick="${i.n}" ${i.selected ? 'checked' : ''} ${runnable(i) && !running ? '' : 'disabled'} aria-label="Analyse image ${i.n}"></td>
        <td class="ws-num">${i.n}</td>
        <td><div class="ws-file">${i.thumb ? `<img src="${i.thumb}" alt="" width="40" height="40">` : '<span class="ws-thumb"></span>'}<div><b title="${esc(i.file.name)}">${esc(i.file.name)}</b><small>${(i.file.size / 1048576).toFixed(2)} MiB</small></div></div></td>
        <td><input class="ws-cell" value="${esc(i.condition)}" data-edit="condition" data-n="${i.n}" aria-label="Condition for image ${i.n}"></td>
        <td><input class="ws-cell short" value="${esc(i.replicate)}" data-edit="replicate" data-n="${i.n}" aria-label="Replicate for image ${i.n}"></td>
        <td><span class="ws-badge ${cls}">${label}</span><small class="ws-why">${esc(i.kind || '')}${i.dims ? ' · ' + esc(i.dims) : ''}</small><small class="ws-why">${esc(i.reason || '')}</small>${chans || fileDye ? `<div class="ws-tags">${chans}${fileDye}</div>` : ''}${(i.warnings || []).map(w => `<small class="ws-warn">${esc(w)}</small>`).join('')}</td>
        <td>${plane}</td>
        <td>${result}</td></tr>`;
    }).join('');
    const ready = items.filter(runnable);
    const picked = items.filter(i => i.selected && runnable(i));
    const done = items.filter(i => i.job.status === 'completed');
    const conditions = new Set(items.map(i => i.condition));
    qs('[data-exp-summary]').textContent = `${items.length} image${items.length === 1 ? '' : 's'} · ${conditions.size} condition${conditions.size === 1 ? '' : 's'} · ${ready.length} suitable · ${picked.length} selected${done.length ? ` · ${done.length} analysed` : ''}`;
    const all = qs('[data-exp-all]');
    if (all) { all.checked = ready.length > 0 && picked.length === ready.length; all.indeterminate = picked.length > 0 && picked.length < ready.length; all.disabled = running; }
    const run = qs('[data-exp-run]');
    run.disabled = running || picked.length === 0;
    run.textContent = running ? 'Analysing…' : `Analyze selected (${picked.length})`;
    qs('[data-exp-stop]').hidden = !running;
    qs('[data-exp-csv]').disabled = !items.some(i => i.job.status === 'completed' || i.job.status === 'failed');
    qs('[data-exp-delete]').disabled = running || !items.some(i => i.job.id && i.job.status !== 'deleted');
    qs('[data-exp-clear]').disabled = running;
  }

  async function add(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    const room = MAX_ITEMS - items.length;
    if (room <= 0) { status(`The tray holds up to ${MAX_ITEMS} images.`); return; }
    if (files.length > room) status(`Only the first ${room} files were added; the tray holds ${MAX_ITEMS}.`);
    const added = files.slice(0, room).map((file, k) => {
      const item = { n: items.length + k + 1, file, verdict: 'pending', reason: '', warnings: [], plane: { channel: 0, z: 0, time: 0 }, job: {}, selected: false, ...parseName(file.name) };
      return item;
    });
    items.push(...added);
    render();
    for (const item of added) {
      try { await recognise(item); } catch (e) { item.verdict = 'rejected'; item.reason = `Could not read the file (${e.message}).`; }
      item.selected = runnable(item);
      render();
    }
  }

  /* ---------- Running ---------- */
  function status(text) { const n = qs('[data-exp-status]'); if (n) n.textContent = text; }
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const STAGE = { queued: 'Queued on server', planning: 'Checking input', running: 'Running model', measuring: 'Measuring nuclei', expert_review: 'Specialist review', packaging: 'Building report' };

  async function runOne(bridge, item) {
    const fd = new FormData();
    fd.append('image', item.file);
    fd.append('research_consent', 'false');
    fd.append('algorithm_profile', 'auto');
    fd.append('analysis_modules', 'nuclei,morphology,intensity');
    fd.append('nd2_channel', String(item.plane.channel));
    fd.append('nd2_time', String(item.plane.time));
    fd.append('nd2_z', String(item.plane.z));
    fd.append('nd2_field', '0');
    item.job = { status: 'uploading', label: 'Uploading' }; render();
    const started = Date.now();
    try {
      const body = await bridge.request('/analyze', { method: 'POST', body: fd, headers: { 'X-BioNuclei-Batch': '1' } });
      item.job = { status: 'queued', id: body.job_id, label: 'Queued on server' }; render();
      for (;;) {
        if (Date.now() - started > 15 * 60 * 1000) throw new Error('Timed out after 15 minutes.');
        await sleep(2000);
        const j = await bridge.request(`/jobs/${encodeURIComponent(item.job.id)}`);
        const s = String(j?.status || '').toLowerCase();
        if (s === 'completed') {
          const r = j.result || {}, rep = r.reports || {};
          Object.assign(item.job, {
            status: 'completed', seconds: Math.round((Date.now() - started) / 1000),
            nuclei: rep.nuclei_count ?? r.n_instances ?? null,
            meanArea: rep.morphology?.mean_area ?? null, medianArea: rep.morphology?.median_area ?? null,
            meanCircularity: rep.morphology?.mean_circularity ?? null, meanIntensity: rep.intensity?.mean_nuclear_intensity ?? null,
            gate: r.adaptive_plan?.status || '', recognised: r.input_metadata?.recognized_as || r.input_metadata?.input_format || '',
            notes: (r.input_metadata?.notes || []).join(' ')
          });
          return;
        }
        if (s === 'failed') { Object.assign(item.job, { status: 'failed', error: j.error || 'Analysis failed.' }); return; }
        item.job.label = STAGE[s] || s; render();
      }
    } catch (e) {
      Object.assign(item.job, { status: 'failed', error: e.message || String(e) });
    } finally { render(); }
  }

  async function runSelected() {
    const bridge = window.BioNucleiAnalyzer;
    if (!bridge || !bridge.authenticated()) { status('Start a session first: sign in or continue as guest.'); return; }
    const queue = items.filter(i => i.selected && runnable(i));
    if (!queue.length) return;
    running = true; stopRequested = false; window.__BIONUCLEI_ANALYSIS_ACTIVE = true; render();
    let k = 0;
    for (const item of queue) {
      if (stopRequested) break;
      k += 1;
      status(`Analysing ${k} of ${queue.length}: #${item.n} ${item.file.name}. Images run one at a time on the server.`);
      await runOne(bridge, item);
    }
    running = false; window.__BIONUCLEI_ANALYSIS_ACTIVE = false;
    const ok = queue.filter(i => i.job.status === 'completed').length, failed = queue.filter(i => i.job.status === 'failed').length;
    status(`${stopRequested ? 'Stopped. ' : ''}${ok} analysed, ${failed} failed. Server results expire after the retention window; download the summary and any reports you need.`);
    render();
  }

  /* ---------- Summary export ---------- */
  function csvCell(v) { const s = String(v ?? ''); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; }
  function downloadCsv() {
    const head = ['image_number', 'file_name', 'condition', 'replicate', 'sha256', 'recognised_in_browser', 'server_recognised_as', 'channel', 'z', 'time', 'status', 'nuclei_count', 'mean_area_px', 'median_area_px', 'mean_circularity', 'mean_nuclear_intensity', 'quality_gate', 'job_id', 'error', 'server_notes'];
    const rows = items.map(i => [i.n, i.file.name, i.condition, i.replicate, i.sha256 || '', [i.kind, i.dims].filter(Boolean).join(' '), i.job.recognised || '', i.plane.channel, i.plane.z, i.plane.time, i.job.status || i.verdict, i.job.nuclei ?? '', i.job.meanArea ?? '', i.job.medianArea ?? '', i.job.meanCircularity ?? '', i.job.meanIntensity ?? '', i.job.gate || '', i.job.id || '', i.job.error || (runnable(i) ? '' : i.reason), i.job.notes || '']);
    const csv = [head, ...rows].map(r => r.map(csvCell).join(',')).join('\n') + '\n';
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const a = document.createElement('a');
    a.href = url; a.download = `bionuclei-experiment-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    status('Experiment summary downloaded. Values come from the server results for each image.');
  }

  async function deleteAll() {
    const bridge = window.BioNucleiAnalyzer;
    const jobs = items.filter(i => i.job.id && i.job.status !== 'deleted');
    let ok = 0;
    for (const i of jobs) {
      try { await bridge.request(`/jobs/${encodeURIComponent(i.job.id)}`, { method: 'DELETE' }); i.job.status = 'deleted'; ok += 1; }
      catch (e) { i.job.error = `Delete failed: ${e.message}`; }
    }
    status(`${ok} of ${jobs.length} server results deleted.`);
    render();
  }

  /* ---------- Events ---------- */
  document.addEventListener('DOMContentLoaded', render);
  qs('#batchInput')?.addEventListener('change', e => { add(e.target.files); e.target.value = ''; });
  document.addEventListener('change', e => {
    const t = e.target;
    if (t.matches('[data-pick]')) { const i = items.find(x => x.n === +t.dataset.pick); if (i) i.selected = t.checked; render(); }
    else if (t.matches('[data-exp-all]')) { items.forEach(i => { if (runnable(i)) i.selected = t.checked; }); render(); }
    else if (t.matches('[data-plane]')) { const i = items.find(x => x.n === +t.dataset.n); const v = Math.max(0, parseInt(t.value, 10) || 0); if (i) { i.plane[t.dataset.plane] = v; if (t.dataset.plane === 'channel') i.channelTouched = true; } t.value = v; }
    else if (t.matches('[data-edit]')) { const i = items.find(x => x.n === +t.dataset.n); if (i) i[t.dataset.edit] = t.value.trim() || (t.dataset.edit === 'condition' ? 'unlabelled' : ''); render(); }
  });
  document.addEventListener('click', async e => {
    const t = e.target.closest('button');
    if (!t) return;
    if (t.matches('[data-exp-run]')) runSelected();
    else if (t.matches('[data-exp-stop]')) { stopRequested = true; status('Stopping after the current image…'); }
    else if (t.matches('[data-exp-csv]')) downloadCsv();
    else if (t.matches('[data-exp-delete]')) deleteAll();
    else if (t.matches('[data-exp-clear]')) { items.length = 0; status(''); render(); }
    else if (t.matches('[data-open]')) {
      const i = items.find(x => x.n === +t.dataset.open);
      try { status(`Opening #${i.n} ${i.file.name}…`); await window.BioNucleiAnalyzer.openJob(i.job.id); status(`Showing #${i.n} ${i.file.name} (${i.condition}${i.replicate ? ', rep ' + i.replicate : ''}).`); }
      catch (err) { status(`Could not open #${i.n}: ${err.message}`); }
    }
  });

  window.BioNucleiExperiment = Object.freeze({ add, count: () => items.length });
})();
