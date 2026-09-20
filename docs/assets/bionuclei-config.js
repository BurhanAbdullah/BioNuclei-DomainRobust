/* Public browser configuration for the BioNuclei Community Analyzer.
 * The publishable Supabase key is safe to expose in browser code; never put a
 * service-role/secret key here.
 */
window.BIONUCLEI_CONFIG = {
  apiBase: "https://bionuclei-community-analyzer.onrender.com",
  supabaseUrl: "https://neokbveqyydrfxgebvcf.supabase.co",
  supabasePublishableKey: "sb_publishable_lqjnxrtMfZqZJLNFzgyErw_8uadb6fp"
};

/* Fail-visible bootstrap: the analyzer must never leave a user wondering
 * whether the Guest action registered. The actual session is still created
 * by bionuclei-analyzer.js. */
(function () {
  function boot() {
    var button = document.getElementById('guestButton');
    var target = document.getElementById('guestMsg');
    if (!button || !target) return;
    button.addEventListener('click', function () {
      target.innerHTML = '<div class="note">Starting secure guest session… Please wait.</div>';
      button.disabled = true;
      window.setTimeout(function () { button.disabled = false; }, 15000);
    }, { capture: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
}());

/* The progress and UI-guard layers are loaded after the DOM is available so
 * their event handlers cannot race analyzer page initialization. */
(function () {
  function load() {
    if (window.__BIONUCLEI_PROGRESS_BOOTED) return;
    var script = document.createElement('script');
    script.src = 'assets/bionuclei-progress.js?v=20260920-3';
    script.async = false;
    document.body.appendChild(script);
    var guard = document.createElement('script');
    guard.src = 'assets/bionuclei-ui-guard.js?v=20260920-1';
    guard.async = false;
    document.body.appendChild(guard);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load, { once: true });
  else load();
}());
