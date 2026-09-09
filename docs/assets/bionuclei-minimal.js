/* BioNuclei: minimal end-user analysis surface. Replaces the developer console in #analyze. */
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
      '    <div class="kicker">Analyze</div>',
      '    <h2>Upload once. BioNuclei does the rest.</h2>',
      '    <p class="intro">Choose an ND2 or TIFF image and tell BioNuclei what you want to measure. The analysis service runs the validated workflow and returns the image result plus a detailed report.</p>',
      '  </div>',
      '  <div class="bn-simple-card">',
      '    <div class="bn-step active"><span>1</span><div><b>Choose your image</b><small>ND2 or TIFF. For ND2, the analysis service reads the microscopy acquisition and selects the requested plane.</small></div></div>',
      '    <label class="bn-drop" for="bnFile"><input id="bnFile" type="file" accept=".nd2,.tif,.tiff"><span class="bn-drop-icon">＋</span><strong id="bnFileTitle">Choose an ND2 or TIFF image</strong><small id="bnFileMeta">Nothing uploaded yet</small></label>',
      '    <div class="bn-options">',
      '      <div><label for="bnAnalysis">What would you like to analyze?</label><select id="bnAnalysis"><option value="nuclei">Nuclei</option><option value="morphology">Nuclei + morphology</option><option value="intensity">Nuclei + fluorescence intensity</option><option value="all">Nuclei + morphology + intensity</option></select></div>',
      '      <button id="bnAnalyze" class="btn primary" type="button" disabled>Analyze image →</button>',
      '    </div>',
      '    <div id="bnStatus" class="bn-status" role="status" aria-live="polite">Select a file to begin.</div>',
      '    <div id="bnProgressWrap" class="bn-progress-wrap" hidden><div id="bnProgress" class="bn-progress"></div><span id="bnProgressText">0%</span></div>',
      '  </div>',
      '  <div id="bnResult" class="bn-result" hidden></div>',
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

    var apiBase = (window.BIONUCLEI_API || '').replace(/\/$/, '');

    function statusText(text, kind) {
      status.textContent = text;
      status.dataset.kind = kind || '';
    }

    function setProgress(value, text) {
      wrap.hidden = false;
      progress.style.width = Math.max(0, Math.min(100, value)) + '%';
      progressText.textContent = text || Math.round(value) + '%';
    }

    file.addEventListener('change', function () {
      var f = file.files && file.files[0];
      result.hidden = true;
      if (!f) {
        title.textContent = 'Choose an ND2 or TIFF image';
        meta.textContent = 'Nothing uploaded yet';
        button.disabled = true;
        statusText('Select a file to begin.');
        wrap.hidden = true;
        return;
      }
      var mb = (f.size / (1024 * 1024)).toFixed(1);
      var ext = f.name.toLowerCase().endsWith('.nd2') ? 'Nikon ND2' : 'TIFF';
      title.textContent = f.name;
      meta.textContent = ext + ' • ' + mb + ' MB • ready';
      button.disabled = false;
      statusText('File selected. Ready to analyze.', 'good');
    });

    button.addEventListener('click', function () {
      var f = file.files && file.files[0];
      if (!f) return;
      if (!apiBase) {
        statusText('The analysis service is not connected yet. Your file is selected but has not been uploaded.', 'warn');
        return;
      }

      var form = new FormData();
      form.append('image', f);
      form.append('device', 'cpu');
      form.append('analysis_profile', select.value);

      var xhr = new XMLHttpRequest();
      xhr.open('POST', apiBase + '/predict', true);
      button.disabled = true;
      wrap.hidden = false;
      setProgress(0, '0%');
      statusText('Uploading ' + f.name + '…');

      xhr.upload.onprogress = function (event) {
        if (!event.lengthComputable) return;
        var pct = (event.loaded / event.total) * 100;
        setProgress(pct, Math.round(pct) + '% uploaded');
        if (pct >= 100) statusText('Upload complete. Analyzing image…');
      };

      xhr.onerror = function () {
        statusText('Could not reach the BioNuclei analysis service. Please check the service connection.', 'warn');
        button.disabled = false;
      };

      xhr.onload = function () {
        var payload;
        try { payload = JSON.parse(xhr.responseText || '{}'); } catch (e) { payload = { raw: xhr.responseText }; }
        if (xhr.status < 200 || xhr.status >= 300) {
          statusText('Analysis failed: ' + (payload.detail || payload.error || ('HTTP ' + xhr.status)), 'warn');
          button.disabled = false;
          return;
        }
        setProgress(100, '100%');
        statusText('Analysis complete. Your result is ready.', 'good');
        result.hidden = false;
        result.innerHTML = '<div><b>Analysis complete</b><p>Your BioNuclei result is ready for review. The returned package may include the analyzed overlay, segmentation mask, measurements and provenance.</p><pre></pre></div>';
        result.querySelector('pre').textContent = JSON.stringify(payload, null, 2);
        button.disabled = false;
      };

      xhr.send(form);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
