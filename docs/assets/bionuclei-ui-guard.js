/* BioNuclei analyzer UX guard.
 * Keeps the browser file state and visible run state synchronized.
 * It never persists image bytes and never replaces the scientific API call.
 */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const note = (id, text) => {
    const el = $(id);
    if (el) el.innerHTML = `<div class="note">${String(text).replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}</div>`;
  };
  const setFileReady = (file) => {
    const button = $('analyzeButton');
    if (button) button.disabled = !file;
    if (file) note('runMsg', `${file.name} is ready. Press Analyze image to start the disposable analysis job.`);
  };
  function boot() {
    if (window.__BIONUCLEI_UI_GUARD_BOOTED) return;
    window.__BIONUCLEI_UI_GUARD_BOOTED = true;
    const input = $('image');
    const analyze = $('analyzeButton');
    const clear = $('clearButton');
    if (!input || !analyze) return;
    analyze.disabled = true;
    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      if (!file) {
        analyze.disabled = true;
        return;
      }
      setFileReady(file);
    }, { capture: true });
    analyze.addEventListener('click', () => {
      const file = input.files && input.files[0];
      if (!file) {
        analyze.disabled = true;
        note('runMsg', 'No file is attached to the browser upload control. Choose the TIFF/ND2 again, then press Analyze image once.');
        return;
      }
      analyze.disabled = true;
      note('runMsg', 'Analysis started. Uploading the image to the disposable analysis job…');
    }, { capture: true });
    clear?.addEventListener('click', () => {
      analyze.disabled = true;
      note('runMsg', 'Selected file removed. Choose a TIFF/ND2 image to begin.');
    }, { capture: true });
    window.setInterval(() => {
      if (!input.files?.length && $('fileInfo')?.hidden === false && !window.__BIONUCLEI_ANALYSIS_ACTIVE) {
        analyze.disabled = true;
      }
    }, 1000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
