/* BioNuclei live analysis progress.
 * Observes the real /analyze response and polls the server's artifact-derived
 * /jobs/{id}/progress endpoint. No synthetic stage timing is used.
 */
(() => {
  'use strict';
  if (window.__BIONUCLEI_PROGRESS_BOOTED) return;
  window.__BIONUCLEI_PROGRESS_BOOTED = true;

  const $ = id => document.getElementById(id);
  const stages = [
    ['queued', '1 · Analysis started', 12],
    ['planning', '2 · Quality & planning', 24],
    ['running', '3 · Boundary U-Net inference', 52],
    ['measuring', '4 · Instance measurements', 68],
    ['expert_review', '5 · Expert evidence review', 84],
    ['packaging', '6 · Report packaging', 94],
    ['completed', '7 · Complete', 100]
  ];

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function card() {
    return $('analysisProgress') || $('liveAnalysis') || document.querySelector('[data-analysis-progress]');
  }
  function render(phase, message, percent) {
    const host = card();
    if (!host) return;
    const index = Math.max(0, stages.findIndex(s => s[0] === phase));
    host.hidden = false;
    host.innerHTML = `<div class="section-head"><div class="eyebrow">Live analysis</div><h3>${escapeHtml(message || 'Analysis in progress')}</h3><p class="muted">${escapeHtml(phase === 'completed' ? 'The scientific pipeline and specialist evidence review are complete.' : 'This status is read from the active server-side analysis job.')}</p></div><div role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}" style="height:8px;border-radius:999px;background:var(--border-subtle);overflow:hidden"><div style="height:100%;width:${percent}%;background:var(--accent);transition:width .25s ease"></div></div><ol style="margin:16px 0 0;padding-left:24px">${stages.map((s, i) => `<li style="margin:7px 0;opacity:${i <= index ? 1 : .45};font-weight:${i === index ? 700 : 400}">${i < index ? '✓ ' : i === index ? '● ' : '○ '}${escapeHtml(s[1])}</li>`).join('')}</ol>`;
  }
  function ensureCard() {
    if (card()) return;
    const workspace = $('workspace');
    if (!workspace) return;
    const wrap = workspace.querySelector('.wrap');
    if (!wrap) return;
    const host = document.createElement('div');
    host.id = 'analysisProgress';
    host.className = 'card';
    host.hidden = true;
    wrap.appendChild(host);
  }
  async function poll(api, jobId) {
    ensureCard();
    let failures = 0;
    for (;;) {
      try {
        const response = await originalFetch(`${api}/jobs/${encodeURIComponent(jobId)}/progress`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`Progress request failed (${response.status})`);
        const data = await response.json();
        failures = 0;
        render(data.phase, data.message || data.label, Number(data.progress || 0));
        window.__BIONUCLEI_ANALYSIS_ACTIVE = data.phase !== 'completed';
        if (data.phase === 'completed') return;
        await new Promise(resolve => setTimeout(resolve, 1500));
      } catch (error) {
        failures += 1;
        if (failures >= 5) {
          render('queued', 'Analysis connection interrupted', 12);
          const runMsg = $('runMsg');
          if (runMsg) runMsg.innerHTML = `<div class="note">${escapeHtml(error.message)}. The job may still be running; keep this page open and retry the status check.</div>`;
          return;
        }
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
  }

  const originalFetch = window.fetch.bind(window);
  window.fetch = async function (...args) {
    const response = await originalFetch(...args);
    try {
      const request = args[0];
      const url = typeof request === 'string' ? request : request?.url || '';
      const method = (args[1]?.method || request?.method || 'GET').toUpperCase();
      if (method === 'POST' && /\/analyze(?:\?|$)/.test(url) && response.ok) {
        const copy = response.clone();
        copy.json().then(data => {
          if (data?.job_id) {
            window.__BIONUCLEI_CURRENT_JOB = data.job_id;
            window.__BIONUCLEI_ANALYSIS_ACTIVE = true;
            const api = String((window.BIONUCLEI_CONFIG || {}).apiBase || '').replace(/\/$/, '');
            render('queued', '1 · Analysis started', 12);
            if (api) poll(api, data.job_id);
          }
        }).catch(() => {});
      }
    } catch (_) {}
    return response;
  };

  function boot() {
    ensureCard();
    const input = $('image');
    const analyze = $('analyzeButton');
    if (input && analyze) {
      analyze.disabled = !input.files?.length;
      input.addEventListener('change', () => {
        if (input.files?.length) render('queued', `${input.files[0].name} ready for analysis`, 5);
      }, { capture: true });
    }
    const guest = $('guestButton');
    guest?.addEventListener('click', () => {
      ensureCard();
      render('queued', 'Preparing disposable guest session…', 5);
    }, { capture: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
