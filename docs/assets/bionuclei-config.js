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
 * whether the Guest action registered. This is deliberately UI-only; the
 * actual session is still created by bionuclei-analyzer.js. */
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

/* Load the visible progress layer before the main analyzer. Cache-busting keeps
 * GitHub Pages from serving a stale progress script after a deployment. */
(function () {
  var script = document.createElement('script');
  script.src = 'assets/bionuclei-progress.js?v=20260920';
  script.async = false;
  document.head.appendChild(script);
}());
