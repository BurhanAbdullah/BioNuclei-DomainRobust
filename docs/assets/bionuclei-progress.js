(() => {
  'use strict';
  if (window.__BIONUCLEI_PROGRESS_BOOTED) return;
  window.__BIONUCLEI_PROGRESS_BOOTED = true;

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
  }

  function boot() {
    const workspace = document.getElementById('workspace');
    const runMsg = document.getElementById('runMsg');
    const analyzeButton = document.getElementById('analyzeButton');
    const guestButton = document.getElementById('guestButton');
    if (!workspace || !runMsg || !analyzeButton) return;

    let panel = document.getElementById('analysisProgress');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'analysisProgress';
      panel.className = 'card';
      panel.hidden = true;
      panel.style.marginTop = '16px';
      panel.innerHTML = `<div class="eyebrow">Live analysis</div><h3 id="progressTitle">Preparing analysis</h3><p id="progressDetail" class="muted">Your image is processed on the analyzer service and the job status is updated here.</p><div style="height:8px;border-radius:999px;background:var(--border-subtle);overflow:hidden;margin:14px 0"><div id="progressBar" style="height:100%;width:5%;border-radius:999px;transition:width .35s ease"></div></div><div id="progressSteps" class="meta"></div>`;
      analyzeButton.closest('.card')?.appendChild(panel);
    }

    const title = document.getElementById('progressTitle');
    const detail = document.getElementById('progressDetail');
    const bar = document.getElementById('progressBar');
    const steps = document.getElementById('progressSteps');
    const stages = [
      ['guest_ready', 'Ready for image upload', 5],
      ['queued', '1 · Analysis started / queued', 12],
      ['planning', '2 · Quality & planning', 24],
      ['running', '3 · Boundary U-Net inference', 52],
      ['measuring', '4 · Instance measurements', 68],
      ['expert_review', '5 · Expert evidence review', 84],
      ['packaging', '6 · Report packaging', 94],
      ['completed', '7 · Complete', 100]
    ];

    function render(status, detailText) {
      const normalized = String(status || '').toLowerCase();
      const idx = Math.max(0, stages.findIndex(([key]) => key === normalized));
      const current = stages[idx] || stages[0];
      panel.hidden = false;
      title.textContent = current[1];
      detail.textContent = detailText || 'Analysis is running. Keep this tab open until the report is ready.';
      bar.style.width = `${current[2]}%`;
      steps.innerHTML = stages.map(([key, label], i) => `<div style="margin:4px 0;opacity:${i <= idx ? 1 : .42}">${i <= idx ? '✓' : '○'} ${escapeHtml(label)}</div>`).join('');
    }

    function renderReady(detailText) {
      render('guest_ready', detailText || 'Select a TIFF or Nikon ND2 file, then press Analyze image.');
    }

    function renderFailure(text) {
      panel.hidden = false;
      title.textContent = 'Analysis needs attention';
      detail.textContent = text || 'The analyzer stopped before the report was ready. Review the message and retry.';
      bar.style.width = '100%';
      steps.innerHTML = stages.map(([key, label], i) => `<div style="margin:4px 0;opacity:${i < 3 ? 1 : .42}">${i < 3 ? '✓' : '○'} ${escapeHtml(label)}</div>`).join('');
    }

    if (guestButton) {
      guestButton.addEventListener('click', () => {
        render('queued', 'Starting the disposable guest session…');
        const started = Date.now();
        const check = () => {
          if (!workspace.hidden) {
            renderReady('Guest session ready. Select a TIFF or Nikon ND2 file, then press Analyze image.');
            return;
          }
          if (Date.now() - started < 15000) window.setTimeout(check, 250);
          else renderFailure('Guest session did not become ready within 15 seconds. Check the analyzer connection and retry.');
        };
        window.setTimeout(check, 250);
      }, { capture: true });
    }

    analyzeButton.addEventListener('click', () => {
      const input = document.getElementById('image');
      if (!input?.files?.length) {
        renderReady('No file is attached to the browser upload control. Please choose the TIFF/ND2 again, then press Analyze image once.');
        return;
      }
      render('queued', 'Analysis started. Upload accepted; creating a disposable analysis job…');
    }, { capture: true });

    const observer = new MutationObserver(() => {
      const text = runMsg.textContent || '';
      const compact = text.replace(/\s+/g, ' ').trim();
      const match = compact.match(/Analysis status:\s*([a-z_]+)/i);
      if (match) render(match[1], compact);
      else if (/Choose a TIFF|Choose a TIFF or ND2|choose.*image first/i.test(compact)) renderReady('Please choose the TIFF or Nikon ND2 file again. The previous request did not start.');
      else if (/Uploading|queued|polling/i.test(compact)) render('queued', compact);
      else if (/Failed to fetch|NetworkError|Load failed/i.test(compact)) renderFailure('The browser could not reach the analyzer service. Retry when the service is responding.');
      else if (/failed|error|could not/i.test(compact)) renderFailure(compact);
    });
    observer.observe(runMsg, { childList: true, subtree: true, characterData: true });

    const resultPanel = document.getElementById('resultPanel');
    if (resultPanel) {
      const resultObserver = new MutationObserver(() => {
        if (!resultPanel.hidden) render('completed', 'Segmentation, measurements and specialist evidence review are complete. Your report is ready to download.');
      });
      resultObserver.observe(resultPanel, { attributes: true, attributeFilter: ['hidden'] });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
