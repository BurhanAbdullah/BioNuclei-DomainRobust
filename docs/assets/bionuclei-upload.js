/* BioNuclei product upload UX: visible file state + upload/analyze progress. */
document.addEventListener('DOMContentLoaded', function () {
  if (!location.pathname.endsWith('/bionuclei.html') && location.pathname !== 'bionuclei.html') return;
  var file = document.getElementById('file');
  var preview = document.getElementById('preview');
  var api = document.getElementById('api');
  if (!file || !preview) return;

  file.accept = '.nd2,.tif,.tiff';
  var drop = file.closest('.drop');
  if (drop) {
    var span = drop.querySelector('span');
    if (span) span.textContent = 'ND2 or TIFF • choose a file to begin';
  }

  var existing = document.getElementById('uploadStatus');
  var status = existing || document.createElement('div');
  status.id = 'uploadStatus';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  status.style.cssText = 'margin-top:12px;padding:12px 14px;border:1px solid var(--line);border-radius:12px;background:#fff;color:var(--muted);font-size:13px;line-height:1.45;';
  if (!existing) preview.parentNode.insertBefore(status, preview);

  var progressWrap = document.createElement('div');
  progressWrap.style.cssText = 'display:none;margin-top:10px;height:8px;border-radius:999px;background:#e8edf0;overflow:hidden;';
  var progressBar = document.createElement('div');
  progressBar.style.cssText = 'height:100%;width:0;background:var(--accent);transition:width .2s ease;';
  progressWrap.appendChild(progressBar);
  status.after(progressWrap);

  function setStatus(text, kind, progress) {
    status.textContent = text;
    if (kind === 'good') {
      status.style.background = '#eef8f2';
      status.style.borderColor = '#b9dec9';
      status.style.color = '#1f6a4a';
    } else if (kind === 'warn') {
      status.style.background = '#fff7e5';
      status.style.borderColor = '#eed3a0';
      status.style.color = '#7b5b16';
    } else {
      status.style.background = '#fff';
      status.style.borderColor = 'var(--line)';
      status.style.color = 'var(--muted)';
    }
    if (typeof progress === 'number') {
      progressWrap.style.display = 'block';
      progressBar.style.width = Math.max(0, Math.min(100, progress)) + '%';
    } else {
      progressWrap.style.display = 'none';
    }
  }

  function showFileState(f) {
    if (!f) {
      setStatus('No image selected yet. Choose an ND2 or TIFF file to begin.', '');
      return;
    }
    var lower = f.name.toLowerCase();
    var isND2 = lower.endsWith('.nd2');
    var mb = (f.size / (1024 * 1024)).toFixed(1);
    setStatus('Selected: ' + f.name + ' • ' + mb + ' MB • ' + (isND2 ? 'Nikon ND2 — server-side plane selection required' : 'TIFF ready for analysis'), 'good');
  }

  file.addEventListener('change', function () {
    var f = file.files && file.files[0];
    showFileState(f);
    if (!f) return;
    var isND2 = f.name.toLowerCase().endsWith('.nd2');
    if (isND2) {
      setStatus('Selected: ' + f.name + ' • ND2 detected. The browser cannot preview ND2 directly; upload is ready and the server will read its microscopy metadata/planes.', 'good');
      return;
    }
    try {
      var url = URL.createObjectURL(f);
      var img = new Image();
      img.onload = function () {
        setStatus('Image ready: ' + f.name + ' • ' + img.naturalWidth + ' × ' + img.naturalHeight + ' px • ready for analysis.', 'good');
        URL.revokeObjectURL(url);
      };
      img.onerror = function () {
        setStatus('File selected: ' + f.name + ' • browser preview is unavailable, but the file can still be uploaded to a live compatible backend.', 'warn');
        URL.revokeObjectURL(url);
      };
      img.src = url;
    } catch (e) {
      setStatus('File selected and ready to upload: ' + f.name, 'good');
    }
  });

  window.predictImage = function () {
    var f = file.files && file.files[0];
    if (!f) {
      setStatus('Choose an ND2 or TIFF image first.', 'warn');
      return;
    }
    var base = (api && api.value ? api.value : '').replace(/\/$/, '');
    if (!base) {
      setStatus('Image selected and ready, but no live BioNuclei API is configured. Enter a trusted HTTPS API URL above before Analyze.', 'warn');
      var apiInput = document.getElementById('api');
      if (apiInput) { apiInput.focus(); apiInput.scrollIntoView({behavior:'smooth', block:'center'}); }
      return;
    }
    var xhr = new XMLHttpRequest();
    xhr.open('POST', base + '/predict', true);
    var form = new FormData();
    form.append('image', f);
    form.append('device', 'cpu');
    var started = Date.now();
    setStatus('Uploading ' + f.name + '…', '', 0);
    xhr.upload.onprogress = function (e) {
      if (e.lengthComputable) setStatus('Uploading ' + f.name + '… ' + Math.round(e.loaded / e.total * 100) + '%', '', e.loaded / e.total * 70);
    };
    xhr.onload = function () {
      var payload;
      try { payload = JSON.parse(xhr.responseText || '{}'); } catch (_) { payload = {raw:xhr.responseText}; }
      if (xhr.status < 200 || xhr.status >= 300) {
        setStatus('Analysis failed: ' + (payload.detail || payload.error || 'backend returned HTTP ' + xhr.status), 'warn');
        progressWrap.style.display = 'none';
        var out = document.getElementById('output'); if (out) out.textContent = 'ERROR\n\n' + JSON.stringify(payload, null, 2);
        return;
      }
      setStatus('Analysis complete in ' + ((Date.now() - started) / 1000).toFixed(1) + ' s.', 'good', 100);
      var instances = document.getElementById('instances'); if (instances && payload.n_instances != null) instances.textContent = payload.n_instances;
      var shape = document.getElementById('shape'); if (shape && payload.image_shape) shape.textContent = payload.image_shape.join('×');
      var prov = document.getElementById('provState'); if (prov) prov.textContent = 'Returned';
      var state = document.getElementById('status'); if (state) { state.textContent = 'Analysis complete'; state.className = 'status good'; }
      var compare = document.getElementById('imageCompare'); var downloads = document.getElementById('downloads');
      function bind(id, key, downloadId, filename) {
        if (!payload.artifacts || !payload.artifacts[key]) return;
        var img = document.getElementById(id); if (img) img.src = payload.artifacts[key];
        var a = document.getElementById(downloadId); if (a) { a.href = payload.artifacts[key]; a.download = filename; a.style.display = 'inline-block'; }
      }
      bind('maskImage','segmentation_mask.tif','downloadMask','bionuclei-mask.png');
      bind('overlayImage','overlay.tif','downloadOverlay','bionuclei-overlay.png');
      if (compare && payload.artifacts) compare.style.display = 'grid';
      if (downloads && payload.artifacts) downloads.style.display = 'block';
      var out = document.getElementById('output'); if (out) out.textContent = 'LIVE · predict_image\n\n' + JSON.stringify(payload, null, 2);
    };
    xhr.onerror = function () {
      setStatus('Upload failed: the BioNuclei API could not be reached. Check the HTTPS URL and server health.', 'warn');
      progressWrap.style.display = 'none';
    };
    xhr.send(form);
  };

  setStatus('No image selected yet. Choose an ND2 or TIFF file to begin.', '');
});
