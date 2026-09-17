/* Public browser configuration for the BioNuclei Community Analyzer.
 * The publishable Supabase key is safe to expose in browser code; never put a
 * service-role/secret key here. Populate the Supabase values only when the
 * project is available and the production auth URLs are configured.
 */
window.BIONUCLEI_CONFIG = {
  apiBase: "https://bionuclei-community-analyzer.onrender.com",
  supabaseUrl: "",
  supabasePublishableKey: ""
};
