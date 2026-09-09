/* BioNuclei Lab UX enhancements: immediate TIFF preview, explicit upload progress, and authenticated result previews. */
(function () {
  'use strict';

  function init() {
    if (!location.pathname.endsWith('/bionuclei-lab.html') && location.pathname !== 'bionuclei-lab.html') return;

    var file = document.getElementById('image');
    var drop = document.getElementById('drop');
    var fileInfo = document.getElementById('fileInfo');
    var runBtn = document.getElementById('runBtn');
    var results = document.getElementById('results');
    var progress = document.getElementById('progress');
    var progressMsg = document.getElementById('progressMsg');
    var progressPct = document.getElementById('progressPct');
    var fill = document.getElementById('fill');
    if (!file || !drop || !runBtn) return;

    var localPreview;
    var previewObjectUrl;

    function ensurePreviewArea() {
      if (localPreview) return localPreview;
      localPreview = document.createElement('div');
      localPreview.id = 'bionuclei-selected-preview';
      localPreview.style.cssText = 'display:none;margin-top:14px;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:#0c171e;';
      localPreview.innerHTML = '<div style="padding:10px 13px;color:#fff;font-size:12px;font-weight:800;background:#12232d;display:flex;justify-content:space-between;gap:10px"><span>Selected image</span><span id="bnLocalPreviewMeta" style="color:#b9c9d1;font-weight:600"></span></div><div style="min-height:220px;max-height:520px;display:flex;align-items:center;justify-content:center;padding:12px;overflow:auto"><img id="bnLocalPreviewImage" alt="Selected microscopy image preview" style="display:block;max-width:100%;max-height:480px;width:auto;height:auto;object-fit:contain"></div>';
      drop.parentNode.insertBefore(localPreview, drop.nextSibling);
      return localPreview;
    }

    function setStep(n) {
      var steps = document.querySelectorAll('.step');
      steps.forEach(function (step, index) {
        step.classList.toggle('active', index < n);
      });
    }

    function showPreview(f) {
      var area = ensurePreviewArea();
      var img = document.getElementById('bnLocalPreviewImage');
      var meta = document.getElementById('bnLocalPreviewMeta');
      area.style.display = 'block';
      if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl);
      previewObjectUrl = null;
      var lower = f.name.toLowerCase();
      if (lower.endsWith('.nd2')) {
        img.removeAttribute('src');
        meta.textContent = 'ND2 · preview generated after analysis';
        return;
      }
      meta.textContent = 'TIFF · reading locally…';
      var script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/utif@3.1.0/UTIF.min.js';
      script.onload = function () {
        try {
          var reader = window.UTIF;
          var readerPromise = f.arrayBuffer().then(function (buffer) {
            var ifds = reader.decode(buffer);
            if (!ifds.length) throw new Error('No TIFF image directory found');
            reader.decodeImage(buffer, ifds[0]);
            var rgba = reader.toRGBA8(ifds[0]);
            var canvas = document.createElement('canvas');
            canvas.width = ifds[0].width;
            canvas.height = ifds[0].height;
            canvas.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(rgba), canvas.width, canvas.height), 0, 0);
            return new Promise(function (resolve) { canvas.toBlob(resolve, 'image/png'); }).then(function (blob) {
              if (!blob) throw new Error('Could not create preview');
              previewObjectUrl = URL.createObjectURL(blob);
              img.src = previewObjectUrl;
              meta.textContent = 'TIFF · ' + ifds[0].width + ' × ' + ifds[0].height + ' px · local only';
            });
          });
          readerPromise.catch(function () { meta.textContent = 'TIFF · preview unavailable in this browser'; });
        } catch (_) { meta.textContent = 'TIFF · preview unavailable in this browser'; }
      };
      script.onerror = function () { meta.textContent = 'TIFF · preview decoder unavailable'; };
      document.head.appendChild(script);
    }

    file.addEventListener('change', function () {
      var f = file.files && file.files[0];
      if (!f) {
        if (localPreview) localPreview.style.display = 'none';
        setStep(1);
        return;
      }
      setStep(2);
      showPreview(f);
    });

    drop.addEventListener('drop', function () {
      setTimeout(function () {
        var f = file.files && file.files[0];
        if (f) { setStep(2); showPreview(f); }
      }, 0);
    });

    runBtn.addEventListener('click', function () {
      var f = file.files && file.files[0];
      if (!f) return;
      setStep(3);
      if (progress) progress.style.display = 'block';
      if (progressMsg) progressMsg.textContent = 'Waiting for the analysis service…';
    }, true);

    function configureResultImages() {
      if (!results) return;
      var resultHead = results.querySelector('.result-head');
      if (!resultHead || resultHead.querySelector('.bn-view-tabs')) return;
      var tabs = document.createElement('div');
      tabs.className = 'bn-view-tabs';
      tabs.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;margin-top:12px;';
      tabs.innerHTML = '<button type="button" data-bn-view="overlay">Overlay</button><button type="button" data-bn-view="mask">Segmentation</button>';
      resultHead.appendChild(tabs);
      tabs.querySelectorAll('button').forEach(function (b) {
        b.style.cssText = 'border:1px solid var(--line);background:#fff;border-radius:9px;padding:8px 11px;font:inherit;font-size:12px;font-weight:800;cursor:pointer;';
      });
      tabs.addEventListener('click', function (event) {
        var button = event.target.closest('button[data-bn-view]');
        if (!button) return;
        var target = button.dataset.bnView === 'overlay' ? document.getElementById('overlay') : document.getElementById('mask');
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    }

    if (results) {
      var observer = new MutationObserver(function () {
        if (getComputedStyle(results).display !== 'none') {
          setStep(4);
          configureResultImages();
        }
      });
      observer.observe(results, { attributes: true, attributeFilter: ['style', 'class'] });
    }

    setStep(file.files && file.files.length ? 2 : 1);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
