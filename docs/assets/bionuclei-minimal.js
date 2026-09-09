/* BioNuclei end-user image workflow.
 * Stage 1: read/select locally and show preview.
 * Stage 2: on Analyze, perform the real HTTP upload and show 0-100% transfer.
 */
(function () {
  'use strict';

  function init() {
    var path = window.location.pathname.split('/').pop() || 'index.html';
    if (path !== 'bionuclei.html') return;
    var target = document.getElementById('analyze');
    if (!target) return;
    if (document.getElementById('bnFile')) return;

    var style = document.createElement('style');
    style.id = 'bionuclei-runtime-style';
    style.textContent = [
      '.bn-upload-preview{margin-top:18px;border:1px solid #dbe4e9;border-radius:18px;background:#fff;overflow:hidden}',
      '.bn-preview-head{display:flex;justify-content:space-between;gap:15px;align-items:center;padding:13px 15px;border-bottom:1px solid #e5ecef}',
      '.bn-preview-head b{display:block;font-size:14px}.bn-preview-head small{display:block;color:#667580;font-size:11px;margin-top:3px}',
      '.bn-preview-badge{padding:6px 9px;border-radius:999px;background:#eef7f2;color:#1f7a55;font-size:9px;font-weight:900;letter-spacing:.08em}',
      '.bn-preview-badge.nd2{background:#f3eef8;color:#65458b}',
      '.bn-preview-stage{background:#0b151d;min-height:280px;max-height:560px;display:flex;align-items:center;justify-content:center;overflow:auto;padding:12px}',
      '.bn-preview-stage img{display:block;max-width:100%;max-height:520px;width:auto;height:auto;object-fit:contain}',
      '.bn-progress-wrap{position:relative;margin-top:14px;height:8px;border-radius:999px;background:#e9eef1;overflow:hidden}',
      '.bn-progress{height:100%;width:0;background:#8b173d;transition:width .12s ease}',
      '.bn-progress-label{display:flex;justify-content:space-between;gap:12px;margin-top:7px;color:#667580;font-size:11px}',
      '.bn-result{margin-top:24px}.bn-viewer{margin-top:15px;background:#0b151d;border-radius:18px;overflow:hidden}',
      '.bn-viewer-toolbar{display:flex;gap:7px;align-items:center;flex-wrap:wrap;padding:10px;border-bottom:1px solid #263640}',
      '.bn-viewer-toolbar button{border:1px solid #455660;background:#13212a;color:#eef4f7;border-radius:8px;padding:7px 10px;font:inherit;font-size:11px;font-weight:800;cursor:pointer}',
      '.bn-viewer-toolbar button.active{background:#fff;color:#17222b}.bn-spacer{flex:1}',
      '.bn-canvas-wrap{min-height:340px;max-height:640px;overflow:auto;display:flex;align-items:center;justify-content:center;padding:12px;background:#070e13}',
      '.bn-canvas-wrap img{display:block;max-width:none;transform-origin:center center}.bn-viewer-caption{padding:10px 12px;color:#b9c7cf;font-size:11px}',
      '.bn-result-top{display:flex;justify-content:space-between;align-items:end;gap:15px;flex-wrap:wrap}',
      '.bn-result-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:15px}',
      '.bn-result-grid>div{padding:13px;border:1px solid #dbe4e9;border-radius:12px;background:#fff}',
      '.bn-result-grid span{display:block;color:#667580;font-size:10px;text-transform:uppercase;letter-spacing:.06em}',
      '.bn-result-grid b{display:block;margin-top:4px;font-size:19px}',
      '.bn-table-wrap{margin-top:16px;border:1px solid #dbe4e9;border-radius:14px;background:#fff;overflow:hidden}',
      '.bn-table-head{display:flex;justify-content:space-between;gap:10px;padding:13px 15px;border-bottom:1px solid #e5ecef}',
      '.bn-table-head h4{margin:0;font-size:15px}.bn-table-head span{color:#667580;font-size:11px}',
      '.bn-scroll{overflow:auto}.bn-scroll table{width:100%;border-collapse:collapse;font-size:11px}',
      '.bn-scroll th,.bn-scroll td{text-align:left;padding:8px 9px;border-bottom:1px solid #edf1f3;white-space:nowrap}',
      '.bn-scroll th{background:#f5f8fa;color:#536570;font-weight:800}',
      '.bn-details{margin-top:12px;border:1px solid #dbe4e9;border-radius:12px;background:#fff;padding:10px 13px}',
      '.bn-details summary{cursor:pointer;font-weight:800;font-size:12px}.bn-details pre{max-height:280px;overflow:auto;font-size:11px}',
      '.bn-empty{padding:16px;color:#667580;font-size:12px}',
      '@media(max-width:760px){.bn-result-grid{grid-template-columns:1fr 1fr}}@media(max-width:520px){.bn-result-grid{grid-template-columns:1fr}.bn-preview-stage{min-height:220px}.bn-canvas-wrap{min-height:250px}}'
    ].join('');
    document.head.appendChild(style);

    target.innerHTML = [
      '<div class="wrap">',
      '<div class="section-head"><div class="kicker">Use BioNuclei</div><h2>Upload. Analyze. See the result.</h2><p class="intro">Choose an ND2 or TIFF image. We show the image first. When you click Analyze, the real upload is shown from 0–100% and then the analysis runs.</p></div>',
      '<div class="bn-simple-card">',
      '<label class="bn-drop" for="bnFile"><input id="bnFile" type="file" accept=".nd2,.tif,.tiff"><span class="bn-drop-icon">＋</span><strong id="bnFileTitle">Choose an ND2 or TIFF image</strong><small id="bnFileMeta">Nothing selected yet</small></label>',
      '<div id="bnPreviewWrap" class="bn-upload-preview" hidden><div class="bn-preview-head"><div><b id="bnPreviewTitle">Selected image</b><small id="bnPreviewInfo">Preview</small></div><span id="bnPreviewState" class="bn-preview-badge">READY</span></div><div class="bn-preview-stage"><img id="bnPreview" alt="Selected microscopy image preview"></div></div>',
      '<div class="bn-options"><div><label for="bnAnalysis">Analysis</label><select id="bnAnalysis"><option value="nuclei">Find & count nuclei</option><option value="morphology">Nuclei + morphology</option><option value="intensity">Nuclei + fluorescence</option><option value="all">Nuclei + morphology + fluorescence</option></select></div><button id="bnAnalyze" class="btn primary" type="button" disabled>Analyze image →</button></div>',
      '<div id="bnStatus" class="bn-status" role="status" aria-live="polite">Choose an image to begin.</div>',
      '<div id="bnProgressWrap" hidden><div class="bn-progress-label"><span id="bnProgressStage">Upload</span><span id="bnProgressText">0%</span></div><div class="bn-progress-wrap"><div id="bnProgress" class="bn-progress"></div></div></div>',
      '</div>',
      '<section id="bnResult" class="bn-result" hidden><div class="bn-result-top"><div><div class="kicker">Analysis result</div><h3 id="bnResultTitle">Your image</h3><p id="bnResultMeta" class="small"></p></div><a id="bnDownload" class="btn" download>Download result bundle</a></div>',
      '<div class="bn-viewer"><div class="bn-viewer-toolbar"><button type="button" class="bn-tab active" data-view="input_preview.png">Original</button><button type="button" class="bn-tab" data-view="overlay.tif">Overlay</button><button type="button" class="bn-tab" data-view="segmentation_mask.tif">Segmentation</button><span class="bn-spacer"></span><button type="button" id="bnZoomOut">−</button><button type="button" id="bnZoomReset">100%</button><button type="button" id="bnZoomIn">＋</button></div><div id="bnCanvasWrap" class="bn-canvas-wrap"><img id="bnViewer" alt="BioNuclei image viewer"></div><div class="bn-viewer-caption" id="bnViewerCaption">Original image</div></div>',
      '<div class="bn-result-grid"><div><span>Detected nuclei</span><b id="bnCount">—</b></div><div><span>Image</span><b id="bnShape">—</b></div><div><span>Analysis</span><b id="bnModules">—</b></div><div><span>Provenance</span><b>Included</b></div></div>',
      '<div class="bn-table-wrap"><div class="bn-table-head"><h4>Per-nucleus measurements</h4><span>First 10 rows</span></div><div id="bnTable"></div></div><details class="bn-details"><summary>Machine-readable result</summary><pre id="bnJson"></pre></details></section></div>'
    ].join('');

    var file = document.getElementById('bnFile');
    var title = document.getElementById('bnFileTitle');
    var meta = document.getElementById('bnFileMeta');
    var select = document.getElementById('bnAnalysis');
    var button = document.getElementById('bnAnalyze');
    var status = document.getElementById('bnStatus');
    var progressWrap = document.getElementById('bnProgressWrap');
    var progress = document.getElementById('bnProgress');
    var progressText = document.getElementById('bnProgressText');
    var progressStage = document.getElementById('bnProgressStage');
    var result = document.getElementById('bnResult');
    var viewer = document.getElementById('bnViewer');
    var viewerCaption = document.getElementById('bnViewerCaption');
    var previewWrap = document.getElementById('bnPreviewWrap');
    var preview = document.getElementById('bnPreview');
    var previewInfo = document.getElementById('bnPreviewInfo');
    var previewState = document.getElementById('bnPreviewState');
    var previewObjectUrl = null;
    var zoom = 1;
    var artifacts = {};

    function statusText(text, kind) { status.textContent = text; status.dataset.kind = kind || ''; }
    function setProgress(value, text, stage) { progressWrap.hidden = false; progress.style.width = Math.max(0, Math.min(100, value)) + '%'; progressText.textContent = text || Math.round(value) + '%'; progressStage.textContent = stage || 'Upload'; }
    function apiBase() { return (window.BIONUCLEI_API_URL || window.BIONUCLEI_API || '').replace(/\/$/, ''); }
    function applyZoom() { viewer.style.transform = 'scale(' + zoom + ')'; document.getElementById('bnZoomReset').textContent = Math.round(zoom * 100) + '%'; }
    function escapeHtml(value) { return String(value).replace(/[&<>\"']/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]; }); }

    function loadTiffDecoder() {
      if (window.UTIF) return Promise.resolve(window.UTIF);
      return new Promise(function (resolve, reject) {
        var script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/utif@3.1.0/UTIF.min.js';
        script.onload = function () { window.UTIF ? resolve(window.UTIF) : reject(new Error('TIFF decoder unavailable')); };
        script.onerror = function () { reject(new Error('TIFF decoder could not be loaded')); };
        document.head.appendChild(script);
      });
    }

    async function showLocalPreview(f) {
      if (previewObjectUrl) { URL.revokeObjectURL(previewObjectUrl); previewObjectUrl = null; }
      preview.removeAttribute('src');
      previewWrap.hidden = false;
      var isNd2 = f.name.toLowerCase().endsWith('.nd2');
      if (isNd2) {
        previewState.textContent = 'ND2 FILE';
        previewState.className = 'bn-preview-badge nd2';
        previewInfo.textContent = 'Nikon ND2 selected · the selected acquisition plane is rendered by BioNuclei during analysis';
        statusText('ND2 selected. Ready to analyze.', 'good');
        return;
      }
      previewState.textContent = 'PREVIEW';
      previewState.className = 'bn-preview-badge';
      previewInfo.textContent = 'Reading TIFF locally…';
      progressWrap.hidden = false;
      setProgress(5, '5%', 'Preparing preview');
      try {
        var UTIF = await loadTiffDecoder();
        var buffer = await f.arrayBuffer();
        setProgress(45, '45%', 'Preparing preview');
        var ifds = UTIF.decode(buffer);
        if (!ifds.length) throw new Error('No TIFF image directory found');
        UTIF.decodeImage(buffer, ifds[0]);
        var rgba = UTIF.toRGBA8(ifds[0]);
        var canvas = document.createElement('canvas');
        canvas.width = ifds[0].width;
        canvas.height = ifds[0].height;
        canvas.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(rgba), canvas.width, canvas.height), 0, 0);
        var blob = await new Promise(function(resolve) { canvas.toBlob(resolve, 'image/png'); });
        if (!blob) throw new Error('Could not create preview');
        previewObjectUrl = URL.createObjectURL(blob);
        preview.src = previewObjectUrl;
        previewInfo.textContent = ifds[0].width + ' × ' + ifds[0].height + ' px · shown locally · not uploaded';
        previewState.textContent = 'READY';
        setProgress(100, '100% ready', 'Preview');
        statusText('Image visible. Choose an analysis, then click Analyze.', 'good');
      } catch (err) {
        previewInfo.textContent = 'Preview unavailable in this browser';
        setProgress(100, '100% ready', 'File');
        statusText('File selected. The browser could not render a TIFF preview, but the file is ready for analysis.', 'warn');
      }
    }

    file.addEventListener('change', function () {
      var f = file.files && file.files[0];
      result.hidden = true;
      if (!f) { button.disabled = true; progressWrap.hidden = true; previewWrap.hidden = true; statusText('Choose an image to begin.'); title.textContent = 'Choose an ND2 or TIFF image'; meta.textContent = 'Nothing selected yet'; return; }
      title.textContent = f.name;
      meta.textContent = (f.name.toLowerCase().endsWith('.nd2') ? 'Nikon ND2' : 'TIFF') + ' · ' + (f.size / 1048576).toFixed(1) + ' MB';
      button.disabled = false;
      showLocalPreview(f);
    });

    document.getElementById('bnZoomOut').addEventListener('click', function () { zoom = Math.max(.25, zoom - .25); applyZoom(); });
    document.getElementById('bnZoomIn').addEventListener('click', function () { zoom = Math.min(4, zoom + .25); applyZoom(); });
    document.getElementById('bnZoomReset').addEventListener('click', function () { zoom = 1; applyZoom(); });

    function setViewer(key, caption) { if (!artifacts[key]) { viewer.removeAttribute('src'); viewerCaption.textContent = 'Preview unavailable.'; return; } viewer.src = artifacts[key]; viewerCaption.textContent = caption; zoom = 1; applyZoom(); document.querySelectorAll('.bn-tab').forEach(function (tab) { tab.classList.toggle('active', tab.dataset.view === key); }); }
    document.querySelectorAll('.bn-tab').forEach(function (tab) { tab.addEventListener('click', function () { setViewer(tab.dataset.view, tab.textContent); }); });
    function renderTable(csv) { var lines = csv.trim().split(/\r?\n/).filter(Boolean); var holder = document.getElementById('bnTable'); if (lines.length < 2) { holder.innerHTML = '<div class="bn-empty">No per-nucleus rows were returned.</div>'; return; } var headers = lines[0].split(','); var body = lines.slice(1, 11).map(function(line){return line.split(',');}); holder.innerHTML = '<div class="bn-scroll"><table><thead><tr>' + headers.map(function(h){return '<th>'+escapeHtml(h)+'</th>';}).join('') + '</tr></thead><tbody>' + body.map(function(row){return '<tr>' + headers.map(function(_,i){return '<td>'+escapeHtml(row[i] || '')+'</td>';}).join('') + '</tr>';}).join('') + '</tbody></table></div>'; }

    button.addEventListener('click', function () {
      var f = file.files && file.files[0];
      var base = apiBase();
      if (!f) return;
      if (!base) { statusText('The analysis service is not connected yet. The image has not been uploaded.', 'warn'); return; }
      var form = new FormData();
      form.append('image', f);
      form.append('device', 'cpu');
      form.append('analysis_profile', select.value);
      var xhr = new XMLHttpRequest();
      xhr.open('POST', base + '/predict', true);
      button.disabled = true;
      setProgress(0, '0%', 'Upload');
      statusText('Uploading ' + f.name + '…');
      xhr.upload.onprogress = function (event) { if (!event.lengthComputable) return; var pct = event.loaded / event.total * 100; setProgress(pct, Math.round(pct) + '% uploaded', 'Upload'); };
      xhr.upload.onload = function () { setProgress(100, '100% uploaded', 'Upload complete'); statusText('Upload complete. BioNuclei is analyzing the image…'); };
      xhr.onerror = function () { statusText('Could not reach the BioNuclei analysis service.', 'warn'); button.disabled = false; };
      xhr.onload = function () {
        var payload = {};
        try { payload = JSON.parse(xhr.responseText || '{}'); } catch (e) { payload = {}; }
        if (xhr.status < 200 || xhr.status >= 300) { statusText('Analysis failed: ' + (payload.detail || payload.error || ('HTTP ' + xhr.status)), 'warn'); button.disabled = false; return; }
        setProgress(100, 'Complete', 'Analysis');
        statusText('Analysis complete. Opening your result…', 'good');
        result.hidden = false;
        artifacts = payload.artifacts || {};
        document.getElementById('bnResultTitle').textContent = payload.filename || f.name;
        document.getElementById('bnResultMeta').textContent = 'Original image, segmentation overlay and measurements are available below.';
        document.getElementById('bnCount').textContent = payload.n_instances != null ? payload.n_instances : '—';
        document.getElementById('bnShape').textContent = Array.isArray(payload.image_shape) ? payload.image_shape.join(' × ') : '—';
        document.getElementById('bnModules').textContent = select.value;
        document.getElementById('bnJson').textContent = JSON.stringify(payload, null, 2);
        renderTable(artifacts['measurements.csv'] || '');
        setViewer('input_preview.png', 'Original image');
        result.scrollIntoView({ behavior: 'smooth', block: 'start' });
        button.disabled = false;
      };
      xhr.send(form);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
