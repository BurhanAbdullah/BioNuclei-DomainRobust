(() => {
  'use strict';

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
  }

  function boot() {
    const workspace = document.getElementById('workspace');
    const runMsg = document.getElementById('runMsg');
    const analyzeButton = document.getElementById('analyzeButton');
    if (!workspace || !runMsg || !analyzeButton) return;

    let panel = document.getElementById('analysisProgress');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'analysisProgress';
      panel.className = 'card';
      panel.hidden = true;
      panel.style.marginTop = '16px';
      panel.innerHTML = `
        <div class="eyebrow">Live analysis</div>
        <h3 id="progressTitle">Preparing analysis</h3>
        <p id="progressDetail" class="muted">Your image is processed on the analyzer service and the job status is updated here.</p>
        <div style="height:8px;border-radius:999px;background:var(--border-subtle);overflow:hidden;margin:14px 0">
          <div id="progressBar" style="height:100%;width:8%;border-radius:999px;transition:width .35s ease"></div>
        </div>
        <div id="progressSteps" class="meta"></div>`;
      analyzeButton.closest('.card')?.appendChild(panel);
    }

    const title = document.getElementById('progressTitle');
    const detail = document.getElementById('progressDetail');
    const bar = document.getElementById('progressBar');
    const steps = document.getElementById('progressSteps');
    const stages = [
      ['queued', '1 · Queued', 12],
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

    analyzeButton.addEventListener('click', () => {
      panel.hidden = false;
      render('queued', 'Upload accepted. Creating a disposable analysis job…');
    }, { capture: true });

    const observer = new MutationObserver(() => {
      const text = runMsg.textContent || '';
      const match = text.match(/Analysis status:\s*([a-z_]+)/i);
      if (match) render(match[1], text.replace(/\s+/g, ' ').trim());
      else if (/Uploading|queued|polling/i.test(text)) render('queued', text.replace(/\s+/g, ' ').trim());
      else if (/failed|error|could not/i.test(text)) {
        panel.hidden = false;
        title.textContent = 'Analysis stopped';
        detail.textContent = text.replace(/\s+/g, ' ').trim();
        bar.style.width = '100%';
      }
    });
    observer.observe(runMsg, { childList: true, subtree: true, characterData: true });

    const resultPanel = document.getElementById('resultPanel');
    const resultObserver = new MutationObserver(() => {
      if (!resultPanel.hidden) render('completed', 'Segmentation, measurements and specialist evidence review are complete. Your report is ready to download.');
    });
    resultObserver.observe(resultPanel, { attributes: true, attributeFilter: ['hidden'] });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
