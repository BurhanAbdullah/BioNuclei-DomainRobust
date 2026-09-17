/* Public browser configuration for the BioNuclei Community Analyzer.
 * The publishable Supabase key is safe to expose in browser code; never put a
 * service-role or secret key here.
 */
window.BIONUCLEI_CONFIG = {
  apiBase: "https://bionuclei-community-analyzer.onrender.com",
  supabaseUrl: "https://neokbveqyydrfxgebvcf.supabase.co",
  supabasePublishableKey: "sb_publishable_lqjnxrtMfZqZJLNFzgyErw_8uadb6fp"
};

(function () {
  "use strict";

  const DB_NAME = "bionuclei_lab";
  const STORE = "pending_files";

  function openDB() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, 1);
      request.onupgradeneeded = () => {
        if (!request.result.objectStoreNames.contains(STORE)) {
          request.result.createObjectStore(STORE);
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async function saveSelectedFile(file) {
    if (!file) return;
    try {
      const db = await openDB();
      await new Promise((resolve, reject) => {
        const tx = db.transaction(STORE, "readwrite");
        tx.objectStore(STORE).put({
          blob: file,
          name: file.name,
          type: file.type || "application/octet-stream",
          size: file.size,
          saved_at: new Date().toISOString()
        }, "selected");
        tx.oncomplete = resolve;
        tx.onerror = () => reject(tx.error);
      });
      db.close();
      showLocalSave(file);
    } catch (error) {
      console.warn("BioNuclei local file storage unavailable", error);
    }
  }

  function showLocalSave(file) {
    const box = document.getElementById("fileInfo");
    if (!box) return;
    box.dataset.localSaved = "true";
    const existing = box.querySelector(".bionuclei-local-save");
    if (existing) existing.remove();
    const note = document.createElement("div");
    note.className = "bionuclei-local-save local-save-status";
    note.textContent = "Image saved locally in this browser. CNN analysisability check will run before scientific analysis.";
    box.appendChild(note);
  }

  function installBrowserWorkflow() {
    const input = document.getElementById("image");
    if (!input || input.dataset.bionucleiPersistence === "installed") return;
    input.dataset.bionucleiPersistence = "installed";
    input.addEventListener("change", () => saveSelectedFile(input.files && input.files[0]));

    const analyze = document.querySelector('button[onclick="runAnalysis()"]');
    if (analyze) {
      analyze.addEventListener("click", () => {
        analyze.dataset.running = "true";
        analyze.disabled = true;
        analyze.textContent = "Running CNN gate and analysis";
        window.setTimeout(() => {
          if (document.getElementById("runMsg")?.textContent.includes("Complete") ||
              document.getElementById("runMsg")?.textContent.includes("failed")) {
            analyze.disabled = false;
            analyze.textContent = "Analyze image";
            delete analyze.dataset.running;
          }
        }, 1500);
      }, true);
    }

    installContrastGuard();
  }

  function installContrastGuard() {
    const style = document.createElement("style");
    style.id = "bionuclei-contrast-guard";
    style.textContent = `
      :root { color-scheme: light; }
      body, body * { text-shadow: none; }
      .hero, .hero * { color: #ffffff; }
      .hero p, .hero span, .hero small { color: #ffffff !important; }
      .hero .pill { color: #ffffff !important; background: #192c39; }
      .panel, .panel * { color: #12202b; }
      .panel .muted, .panel small, .panel p { color: #657482; }
      .panel .success, .panel .success * { color: #155c3d; }
      .panel .error, .panel .error * { color: #7f1d2d; }
      .panel .note, .panel .note * { color: #263640; }
      .upload, .upload * { color: #12202b; }
      .upload span { color: #657482 !important; }
      .preview, .preview * { color: #ffffff; }
      .preview figcaption { color: #ffffff !important; background: #0b1218; }
      .jobrow, .jobrow * { color: #12202b; }
      .jobrow .muted { color: #657482; }
      .local-save-status { color: #155c3d !important; font-size: 12px; margin-top: 6px; flex-basis: 100%; }
      input, textarea, select { color: #12202b; background: #ffffff; }
      button, .btn { color: #ffffff; }
      .btn:not(.primary) { color: #12202b; background: #ffffff; }
      @media (prefers-color-scheme: dark) {
        body { background: #0b1218; color: #ffffff; }
        .panel { background: #111d26; border-color: #324552; }
        .panel, .panel * { color: #ffffff; }
        .panel .muted, .panel small, .panel p { color: #cfdae1; }
        .auth-card, .stat, .fileinfo, .check, .analysis-card, .jobrow { background: #162630; border-color: #324552; }
        input, textarea, select { color: #ffffff; background: #162630; border-color: #526a79; }
        .upload { background: #162630; border-color: #526a79; }
        .upload span { color: #cfdae1 !important; }
        .btn:not(.primary) { color: #ffffff; background: #162630; border-color: #526a79; }
        .note { background: #1b2c36; }
        .success { background: #153a2a; }
        .error { background: #3a1b24; }
      }
    `;
    document.head.appendChild(style);
  }

  function boot() {
    installBrowserWorkflow();
    const observer = new MutationObserver(installBrowserWorkflow);
    observer.observe(document.body, { childList: true, subtree: true });
    window.setTimeout(() => observer.disconnect(), 10000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
