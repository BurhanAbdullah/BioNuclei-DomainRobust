/* Browser-side verification of the server-produced specialist artifact.
 * This checks job/input binding and internal evidence-manifest consistency.
 * It is not a substitute for scientific validation of the underlying model.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.BIONUCLEI_SPECIALIST_VERIFICATION = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const EXPECTED_AGENTS = new Set([
    "image_quality_agent",
    "segmentation_quality_agent",
    "morphology_agent",
    "intensity_agent",
    "population_agent",
    "biological_interpretation_agent",
    "scientific_review_agent",
    "report_agent"
  ]);
  const SHA256 = /^[a-f0-9]{64}$/i;

  function stableJson(value) {
    if (value === null || typeof value === "string" || typeof value === "boolean") {
      return JSON.stringify(value);
    }
    if (typeof value === "number") {
      if (!Number.isFinite(value)) throw new TypeError("Non-finite number in execution manifest");
      return JSON.stringify(value);
    }
    if (Array.isArray(value)) return "[" + value.map(stableJson).join(",") + "]";
    if (value && typeof value === "object") {
      return "{" + Object.keys(value).sort().map(key =>
        JSON.stringify(key) + ":" + stableJson(value[key])
      ).join(",") + "}";
    }
    throw new TypeError("Unsupported value in execution manifest");
  }

  async function sha256Hex(text, cryptoApi) {
    if (!cryptoApi || !cryptoApi.subtle) throw new Error("Web Crypto SHA-256 is unavailable");
    const digest = await cryptoApi.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
  }

  function resolveReference(root, reference) {
    let value = root;
    for (const key of String(reference).split(".")) {
      if (!value || typeof value !== "object" || !Object.prototype.hasOwnProperty.call(value, key)) {
        return { found: false };
      }
      value = value[key];
    }
    return { found: true, value };
  }

  function fail(reason) {
    return { ok: false, reason, artifact: null };
  }

  async function verifySpecialistArtifact({ job, result, embedded, fetchJson, cryptoApi }) {
    try {
      if (!job || typeof job.job_id !== "string" || !job.job_id.trim()) return fail("missing job identifier");
      if (!result || typeof result !== "object") return fail("completed job has no structured result");
      if (typeof fetchJson !== "function") return fail("artifact fetch is unavailable");
      const jobId = job.job_id;
      const inputHash = result.input_sha256;
      if (typeof inputHash !== "string" || !SHA256.test(inputHash)) return fail("result input SHA-256 is missing or malformed");
      if (job.input_sha256 != null && job.input_sha256 !== inputHash) return fail("job and result input SHA-256 do not match");
      if (result.job_id !== jobId) return fail("result is not bound to the selected job");

      const artifact = await fetchJson("/jobs/" + encodeURIComponent(jobId) + "/files/expert_agents.json");
      if (!artifact || typeof artifact !== "object" || Array.isArray(artifact)) return fail("specialist artifact is not a JSON object");
      if (artifact.agent_version !== "1.1") return fail("unsupported specialist artifact version");
      if (!embedded || stableJson(artifact) !== stableJson(embedded)) return fail("downloaded artifact differs from the embedded job result");

      const execution = artifact.execution;
      if (!execution || execution.status !== "completed") return fail("server marked specialist execution incomplete");
      if (execution.job_id !== jobId || execution.job_id_valid !== true) return fail("specialist execution is bound to a different or invalid job");
      if (execution.input_sha256 !== inputHash || execution.input_hash_valid !== true) return fail("specialist execution is bound to a different or invalid input");
      if (!SHA256.test(String(execution.execution_sha256 || ""))) return fail("execution digest is missing or malformed");

      const agents = artifact.agents;
      if (!Array.isArray(agents) || agents.length !== EXPECTED_AGENTS.size) return fail("expected eight specialist reviewers");
      const seen = new Set();
      for (const agent of agents) {
        if (!agent || !EXPECTED_AGENTS.has(agent.agent) || seen.has(agent.agent)) return fail("specialist reviewer set is invalid");
        seen.add(agent.agent);
        if (agent.status !== "completed") return fail("reviewer " + agent.agent + " is incomplete");
        if (!Array.isArray(agent.observations) || !Array.isArray(agent.limitations)) return fail("reviewer observations or limitations are malformed");
        if (!Array.isArray(agent.evidence_references) || agent.evidence_references.length === 0) return fail("reviewer has no evidence references");
        if (!Array.isArray(agent.missing_evidence_references) || agent.missing_evidence_references.length !== 0) return fail("reviewer declares missing evidence");
        if (!SHA256.test(String(agent.evidence_sha256 || ""))) return fail("reviewer evidence digest is missing or malformed");
        for (const reference of agent.evidence_references) {
          if (typeof reference !== "string" || !resolveReference(result, reference).found) {
            return fail("unresolved computed-evidence reference: " + String(reference));
          }
        }
      }
      if (seen.size !== EXPECTED_AGENTS.size) return fail("one or more expected reviewers are absent");
      if (execution.agent_count !== agents.length || execution.completed_agent_count !== agents.length) {
        return fail("execution reviewer counts do not match the artifact");
      }
      if (!Array.isArray(execution.incomplete_agents) || execution.incomplete_agents.length !== 0) {
        return fail("execution manifest lists incomplete reviewers");
      }
      if (!artifact.training_status || typeof artifact.training_status !== "object") {
        return fail("training provenance status is absent");
      }
      if (artifact.training_status.verified !== true && artifact.training_status.claim_allowed !== false) {
        return fail("unverified training provenance is not explicitly disallowed");
      }

      // Match src/bionuclei/expert_agents.py's execution-payload contract.
      const payload = {
        agent_version: "1.1",
        job_id: execution.job_id,
        job_id_valid: execution.job_id_valid,
        input_sha256: execution.input_sha256,
        input_hash_valid: execution.input_hash_valid,
        agents: agents.map(agent => ({
          agent: agent.agent,
          status: agent.status,
          observations: agent.observations,
          limitations: agent.limitations,
          evidence_references: agent.evidence_references,
          evidence_sha256: agent.evidence_sha256,
          missing_evidence_references: agent.missing_evidence_references
        })),
        training_status: artifact.training_status
      };
      const computed = await sha256Hex(stableJson(payload), cryptoApi || root.crypto);
      if (computed !== execution.execution_sha256) return fail("execution digest does not match the artifact contents");
      return { ok: true, reason: "Job, input, reviewers, evidence references, and execution digest verified", artifact };
    } catch (error) {
      return fail(error && error.message ? error.message : "specialist artifact verification failed");
    }
  }

  return { verifySpecialistArtifact, stableJson };
});
