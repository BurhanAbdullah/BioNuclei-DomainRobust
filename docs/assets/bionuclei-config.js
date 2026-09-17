/* Public browser configuration for the BioNuclei Community Analyzer.
 * The publishable Supabase key is safe to expose in browser code; never put a
 * service-role/secret key here.
 */
window.BIONUCLEI_CONFIG = {
  apiBase: "https://bionuclei-community-analyzer.onrender.com",
  supabaseUrl: "https://neokbveqyydrfxgebvcf.supabase.co",
  supabasePublishableKey: "sb_publishable_lqjnxrtMfZqZJLNFzgyErw_8uadb6fp"
};

/* Production readability, workflow and evidence disclosure safeguards. */
(function () {
  var css = document.createElement("style");
  css.textContent = `
    body { color: #12202b !important; background: #f7f9fb !important; }
    .hero { background: #111d26 !important; color: #ffffff !important; }
    .hero h1, .hero h2, .hero h3, .hero p, .hero span, .hero strong { color: #ffffff !important; }
    .hero p { color: #e2eaf0 !important; }
    .pill { background: #192c39 !important; color: #ffffff !important; border-color: #526875 !important; }
    .panel, .auth-card, .analysis-card, .stat, .fileinfo, .upload, .check, .jobrow { color: #12202b !important; background: #ffffff !important; }
    .panel h2, .panel h3, .auth-card h3, .analysis-card { color: #12202b !important; }
    .panel p, .analysis-card p, .muted, .upload span, .check small, .footer-note { color: #50606b !important; }
    .note { background: #26343e !important; color: #ffffff !important; border: 1px solid #526875 !important; }
    .note * { color: #ffffff !important; }
    .error { background: #651f2a !important; color: #ffffff !important; border-left-color: #ff9eaa !important; }
    .error * { color: #ffffff !important; }
    .success { background: #145c3e !important; color: #ffffff !important; border-left-color: #8ee0b7 !important; }
    .success * { color: #ffffff !important; }
    .preview { background: #0b1218 !important; color: #ffffff !important; }
    .preview figcaption { color: #ffffff !important; background: #0b1218 !important; }
    input, select, textarea { color: #12202b !important; background: #ffffff !important; }
    button:disabled { opacity: .55; cursor: not-allowed !important; transform: none !important; }
    .contrast-dark { background: #111d26 !important; color: #ffffff !important; }
    .contrast-dark * { color: #ffffff !important; }
    .contrast-light { background: #ffffff !important; color: #12202b !important; }
    .contrast-light * { color: #12202b !important; }
    .agent-status { margin-top: 12px; padding: 12px 14px; border-radius: 10px; background: #eef4f7; color: #12202b; border: 1px solid #cfd9e0; font-size: 12px; line-height: 1.5; }
    .agent-status b { color: #12202b; }
    @media (max-width: 800px) {
      .hero { padding: 28px !important; }
      .hero h1 { font-size: clamp(34px, 12vw, 54px) !important; }
      .panel { padding: 20px !important; }
    }
  `;
  document.head.appendChild(css);

  function installWorkflowGuards() {
    var file = document.getElementById("image");
    var analyze = document.querySelector("button[onclick=\"runAnalysis()\"]");
    var runMsg = document.getElementById("runMsg");
    if (!file || !analyze) return;

    function saveSelected(f) {
      if (!f || !window.indexedDB) return;
      try {
        var req = indexedDB.open("bionuclei_lab", 1);
        req.onupgradeneeded = function () {
          if (!req.result.objectStoreNames.contains("pending_files")) req.result.createObjectStore("pending_files");
        };
        req.onsuccess = function () {
          var db = req.result;
          var tx = db.transaction("pending_files", "readwrite");
          tx.objectStore("pending_files").put({name:f.name, type:f.type, size:f.size, blob:f}, "selected");
          tx.oncomplete = function () { db.close(); };
        };
      } catch (_) {}
    }

    file.addEventListener("change", function () { saveSelected(file.files && file.files[0]); });

    var original = window.runAnalysis;
    if (typeof original === "function" && !original.__bionucleiGuarded) {
      window.runAnalysis = async function () {
        if (analyze.disabled) return;
        analyze.disabled = true;
        analyze.setAttribute("aria-busy", "true");
        analyze.dataset.originalText = analyze.textContent;
        analyze.textContent = "Analysis running";
        try { return await original.apply(this, arguments); }
        finally {
          analyze.disabled = false;
          analyze.removeAttribute("aria-busy");
          analyze.textContent = analyze.dataset.originalText || "Analyze image";
        }
      };
      window.runAnalysis.__bionucleiGuarded = true;
    }

    if (runMsg && !runMsg.dataset.contrastGuard) {
      runMsg.dataset.contrastGuard = "1";
      new MutationObserver(function () {
        var nodes = runMsg.querySelectorAll(".note,.error,.success");
        nodes.forEach(function (node) {
          var bg = getComputedStyle(node).backgroundColor;
          var m = bg.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
          if (m) {
            var lum = (Number(m[1]) * 299 + Number(m[2]) * 587 + Number(m[3]) * 114) / 1000;
            node.style.color = lum < 145 ? "#ffffff" : "#12202b";
          }
        });
      }).observe(runMsg, {childList:true, subtree:true});
    }

    var analyzer = document.querySelector(".fileinfo .muted");
    if (analyzer) analyzer.textContent = "Boundary U Net, quantitative measurements, and evidence constrained specialist agents";
    var info = document.getElementById("fileInfo");
    if (info && !document.getElementById("agentStatus")) {
      var note = document.createElement("div");
      note.id = "agentStatus";
      note.className = "agent-status";
      note.innerHTML = "<b>Specialist analysis:</b> 8 evidence constrained agents review image quality, segmentation, morphology, intensity, population metrics, interpretation, scientific consistency, and report generation. Training provenance is disclosed only when a verified manifest supports it.";
      info.parentNode.insertBefore(note, info.nextSibling);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", installWorkflowGuards);
  else installWorkflowGuards();
})();
