/* BioNuclei: simple end-user analysis surface with a real image/result viewer. */
(function () {
  'use strict';

  function init() {
    var path = window.location.pathname.split('/').pop() || 'index.html';
    if (path !== 'bionuclei.html') return;

    var target = document.getElementById('analyze');
    if (!target) return;

    target.innerHTML = [
      '<div class="wrap">',
      '  <div class="section-head">',
      '    <div class="kicker">Use BioNuclei</div>',
      '    <h2>Upload. Analyze. See the result.</h2>',
      '    <p class="intro">Choose an ND2 or TIFF image. BioNuclei analyzes it and opens the result for visual inspection.</p>',
      '  </div>',
      '  <div class="bn-simple-card">',
      '    <label class="bn-drop" for="bnFile"><input id="bnFile" type="file" accept=".nd2,.tif,.tiff"><span class="bn-drop-icon">＋</span><strong id="bnFileTitle">Choose an ND2 or TIFF image</strong><small id="bnFileMeta">Nothing selected yet</small></label>',
      '    <div class="bn-options"><div><label for="bnAnalysis">Analysis</label><select id="bnAnalysis"><option value="nuclei">Find & count nuclei</option><option value="morphology">Nuclei + morphology</option><option value="intensity">Nuclei + fluorescence</option><option value="all">Nuclei + morphology + fluorescence</option></select></div><button id="bnAnalyze" class="btn primary" type="button" disabled>Analyze image →</button></div>',
      '    <div id="bnStatus" class="bn-status" role="status" aria-live="polite">Choose an image to begin.</div>',
      '    <div id="bnProgressWrap" class="bn-progress-wrap" hidden><div id="bnProgress" class="bn-progress"></div><span id="bnProgressText">0%</span></div>',
      '  </div>',
      '  <section id="bnResult" class="bn-result" hidden>',
      '    <div class="bn-result-top"><div><div class="kicker">Analysis result</div><h3 id="bnResultTitle">Your image</h3><p id="bnResultMeta" class="small"></p></div><a id="bnDownload" class="btn" download>Download result bundle</a></div>',
      '    <div class="bn-viewer">',
      '      <div class="bn-viewer-toolbar"><button type="button" class="bn-tab active" data-view="input_preview.png">Original</button><button type="button" class="bn-tab" data-view="overlay.tif">Overlay</button><button type="button" class="bn-tab" data-view="segmentation_mask.tif">Segmentation</button><span class="bn-spacer"></span><button type="button" id="bnZoomOut">−</button><button type="button" id="bnZoomReset">100%</button><button type="button" id="bnZoomIn">＋</button></div>',
      '      <div id="bnCanvasWrap" class="bn-canvas-wrap"><img id="bnViewer" alt="BioNuclei image viewer"></div>',
      '      <div class="bn-viewer-caption" id="bnViewerCaption">Original image</div>',
      '    </div>',
      '    <div class="bn-result-grid"><div><span>Detected nuclei</span><b id="bnCount">—</b></div><div><span>Image</span><b id="bnShape">—</b></div><div><span>Analysis</span><b id="bnModules">—</b></div><div><span>Provenance</span><b>Included</b></div></div>',
      '    <div class="bn-table-wrap"><div class="bn-table-head"><h4>Per-nucleus measurements</h4><span>First 10 rows</span></div><div id="bnTable"></div></div>',
      '    <details class="bn-details"><summary>Machine-readable result</summary><pre id="bnJson"></pre></details>',
      '  </section>',
      '</div>'
    ].join('');

    var file = document.getElementById('bnFile');
    var title = document.getElementById('bnFileTitle');
    var meta = document.getElementById('bnFileMeta');
    var select = document.getElementById('bnAnalysis');
    var button = document.getElementById('bnAnalyze');
    var status = document.getElementById('bnStatus');
    var wrap = document.getElementById('bnProgressWrap');
    var progress = document.getElementById('bnProgress');
    var progressText = document.getElementById('bnProgressText');
    var result = document.getElementById('bnResult');
    var viewer = document.getElementById('bnViewer');
    var viewerCaption = document.getElementById('bnViewerCaption');
    var zoom = 1;
    var artifacts = {};

    function statusText(text, kind) { status.textContent = text; status.dataset.kind = kind || ''; }
    function setProgress(value, text) { wrap.hidden = false; progress.style.width = Math.max(0, Math.min(100, value)) + '%'; progressText.textContent = text || Math.round(value) + '%'; }
    function escapeHtml(value) { return String(value).replace(/[&<>\"']/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]; }); }
    function apiBase() { return (window.BIONUCLEI_API_URL || window.BIONUCLEI_API || '').replace(/\/$/, ''); }
    function applyZoom() { viewer.style.transform = 'scale(' + zoom + ')'; document.getElementById('bnZoomReset').textContent = Math.round(zoom * 100) + '%'; }

    file.addEventListener('change', function () {
      var f = file.files && file.files[0];
      result.hidden = true;
      if (!f) { title.textContent = 'Choose an ND2 or TIFF image'; meta.textContent = 'Nothing selected yet'; button.disabled = true; statusText('Choose an image to begin.'); wrap.hidden = true; return; }
      title.textContent = f.name;
      meta.textContent = (f.name.toLowerCase().endsWith('.nd2') ? 'Nikon ND2' : 'TIFF') + ' · ' + (f.size / 1048576).toFixed(1) + ' MB · ready';
      button.disabled = false;
      statusText('Image selected. Ready to analyze.', 'good');
    });

    document.getElementById('bnZoomOut').addEventListener('click', function () { zoom = Math.max(.25, zoom - .25); applyZoom(); });
    document.getElementById('bnZoomIn').addEventListener('click', function () { zoom = Math.min(4, zoom + .25); applyZoom(); });
    document.getElementById('bnZoomReset').addEventListener('click', function () { zoom = 1; applyZoom(); });

    button.addEventListener('click', function () {
      var f = file.files && file.files[0];
      var base = apiBase();
      if (!f) return;
      if (!base) { statusText('The BioNuclei analysis service is not connected yet. The image has not been uploaded.', 'warn'); return; }

      var form = new FormData();
      form.append('image', f);
      form.append('device', 'cpu');
      form.append('analysis_profile', select.value);
      var xhr = new XMLHttpRequest();
      xhr.open('POST', base + '/predict', true);
      button.disabled = true;
      setProgress(0, '0%');
      statusText('Uploading ' + f.name + '…');
      xhr.upload.onprogress = function (event) { if (!event.lengthComputable) return; var pct = event.loaded / event.total * 70; setProgress(pct, Math.round(event.loaded / event.total * 100) + '% uploaded'); };
      xhr.onerror = function () { statusText('Could not reach the BioNuclei analysis service.', 'warn'); button.disabled = false; };
      xhr.onload = function () {
        var payload = {};
        try { payload = JSON.parse(xhr.responseText || '{}'); } catch (e) { payload = {}; }
        if (xhr.status < 200 || xhr.status >= 300) { statusText('Analysis failed: ' + (payload.detail || payload.error || ('HTTP ' + xhr.status)), 'warn'); button.disabled = false; return; }
        setProgress(100, '100%');
        statusText('Analysis complete. Opening your result…', 'good');
        result.hidden = false;
        artifacts = payload.artifacts || {};
        document.getElementById('bnResultTitle').textContent = payload.filename || f.name;
        document.getElementById('bnResultMeta').textContent = 'Original image, segmentation overlay and machine-readable measurements are available below.';
        document.getElementById('bnCount').textContent = payload.n_instances != null ? payload.n_instances : '—';
        document.getElementById('bnShape').textContent = Array.isArray(payload.image_shape) ? payload.image_shape.join(' × ') : '—';
        document.getElementById('bnModules').textContent = select.value;
        document.getElementById('bnJson').textContent = JSON.stringify(payload, null, 2);
        renderTable(artifacts['measurements.csv'] || '');
        document.getElementById('bnDownload').style.display = artifacts['results.json'] ? 'inline-flex' : 'none';
        setViewer('input_preview.png', 'Original image');
        document.querySelectorAll('.bn-tab').forEach(function (tab) { tab.classList.toggle('active', tab.dataset.view === 'input_preview.png'); });
        result.scrollIntoView({ behavior: 'smooth', block: 'start' });
        button.disabled = false;
      };
      xhr.send(form);
    });

    function setViewer(key, caption) {
      if (!artifacts[key]) { viewer.removeAttribute('src'); viewerCaption.textContent = 'Preview unavailable in this response.'; return; }
      viewer.src = artifacts[key]; viewerCaption.textContent = caption; zoom = 1; applyZoom();
      document.querySelectorAll('.bn-tab').forEach(function (tab) { tab.classList.toggle('active', tab.dataset.view === key); });
    }

    document.querySelectorAll('.bn-tab').forEach(function (tab) { tab.addEventListener('click', function () { setViewer(tab.dataset.view, tab.textContent); }); });

    function renderTable(csv) {
      var lines = csv.trim().split(/\r?\n/).filter(Boolean);
      var holder = document.getElementById('bnTable');
      if (lines.length < 2) { holder.innerHTML = '<div class="bn-empty">No per-nucleus rows were returned.</div>'; return; }
      var headers = lines[0].split(',');
      var body = lines.slice(1, 11).map(function (line) { return line.split(','); });
      holder.innerHTML = '<div class="bn-scroll"><table><thead><tr>' + headers.map(function (h) { return '<th>' + escapeHtml(h) + '</th>'; }).join('') + '</tr></thead><tbody>' + body.map(function (row) { return '<tr>' + headers.map(function (_, i) { return '<td>' + escapeHtml(row[i] || '') + '</td>'; }).join('') + '</tr>'; }).join('') + '</tbody></table></div>';
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
