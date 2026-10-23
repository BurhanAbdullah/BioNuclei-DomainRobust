(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(root);
  else root.BIONUCLEI_SPECIALIST_VERIFICATION = factory(root);
})(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
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
    if (value === null || typeof value === "string" || typeof value === "boolean") return JSON.stringify(value);
    if (typeof value === "number") {
      if (!Number.isFinite(value)) throw new TypeError("Non-finite number in specialist payload");
      return JSON.stringify(value);
    }
    if (Array.isArray(value)) return "[" + value.map(stableJson).join(",") + "]";
    if (value && typeof value === "object") {
      return "{" + Object.keys(value).sort().map(key => JSON.stringify(key) + ":" + stableJson(value[key])).join(",") + "}";
    }
    throw new TypeError("Unsupported value in specialist payload");
  }

  async function sha256Hex(text, cryptoApi) {
    if (!cryptoApi || !cryptoApi.subtle) throw new Error("Web Crypto SHA-256 is unavailable");
    const digest = await cryptoApi.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
  }

  function resolveReference(root, reference) {
    let value = root;
    for (const key of String(reference).split(".")) {
      if (!value || typeof value !== "object" || !Object.prototype.hasOwnProperty.call(value, key)) return { found: false };
      value = value[key];
    }
    return { found: true, value };
  }

  function fail(reason) {
    return { ok: false, reason: reason, artifact: null };
  }

  async function verifySpecialistArtifact(options) {
    try {
      const job = options && options.job;
      const result = options && options.result;
      const embedded = options && options.embedded;
      const fetchJson = options && options.fetchJson;
      const cryptoApi = (options && options.cryptoApi) || root.crypto;

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
      if (artifact.agent_version !== "1.2") return fail("unsupported specialist artifact version");
      if (!embedded || stableJson(artifact) !== stableJson(embedded)) return fail("downloaded artifact differs from the embedded job result");

      const execution = artifact.execution;
      if (!execution || execution.status !== "completed") return fail("server marked specialist execution incomplete");
      if (execution.job_id !== jobId || execution.job_id_valid !== true) return fail("specialist execution is bound to a different or invalid job");
      if (execution.input_sha256 !== inputHash || execution.input_hash_valid !== true) return fail("specialist execution is bound to a different or invalid input");
      if (typeof execution.execution_payload_json !== "string" || !execution.execution_payload_json) return fail("canonical execution payload is missing");
      if (!SHA256.test(String(execution.execution_sha256 || ""))) return fail("execution digest is missing or malformed");

      const computedExecutionDigest = await sha256Hex(execution.execution_payload_json, cryptoApi);
      if (computedExecutionDigest !== execution.execution_sha256) return fail("execution digest does not match the exact canonical payload bytes");
      let canonicalPayload;
      try {
        canonicalPayload = JSON.parse(execution.execution_payload_json);
      } catch (_) {
        return fail("canonical execution payload is not valid JSON");
      }

      const agents = artifact.agents;
      if (!Array.isArray(agents) || agents.length !== EXPECTED_AGENTS.size) return fail("expected eight specialist reviewers");
      const seen = new Set();
      for (const agent of agents) {
        if (!agent || !EXPECTED_AGENTS.has(agent.agent) || seen.has(agent.agent)) return fail("specialist reviewer set is invalid");
        seen.add(agent.agent);
        if (!Array.isArray(agent.observations) || !Array.isArray(agent.limitations)) return fail("reviewer observations or limitations are malformed");
        const modules = result.analysis_modules;
        if (!Array.isArray(modules) || stableJson(modules) !== stableJson(Array.from(new Set(modules)).sort())) return fail("result analysis_modules is not canonical");
        const requirements = { morphology_agent: ["morphology"], intensity_agent: ["intensity"], biological_interpretation_agent: ["morphology", "intensity"] };
        const unselected = (requirements[agent.agent] || []).filter(module => !modules.includes(module)).sort();
        if (unselected.length) {
          const emptyDigest = "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a";
          const expectedObservation = "Not applicable: required analysis module(s) not selected: " + unselected.join(", ") + ".";
          const expectedLimitation = "This reviewer did not execute because its required modules were not selected; no findings or quantitative claims are asserted.";
          if (agent.status !== "not_applicable") return fail("reviewer should be not_applicable: " + agent.agent);
          if (stableJson(agent.observations) !== stableJson([expectedObservation]) || stableJson(agent.limitations) !== stableJson([expectedLimitation])) return fail("not-applicable reviewer reason is invalid: " + agent.agent);
          if (stableJson(agent.evidence_references) !== "[]" || stableJson(agent.missing_evidence_references) !== "[]" || stableJson(agent.quantitative_claims) !== "[]") return fail("not-applicable reviewer cannot assert evidence or measurements: " + agent.agent);
          if (agent.evidence_payload !== "{}" || agent.evidence_sha256 !== emptyDigest) return fail("not-applicable reviewer empty-evidence digest is invalid: " + agent.agent);
          continue;
        }
        if (agent.status !== "completed") return fail("reviewer " + agent.agent + " is incomplete");
        if (!Array.isArray(agent.evidence_references) || agent.evidence_references.length === 0) return fail("reviewer has no evidence references");
        if (!Array.isArray(agent.missing_evidence_references) || agent.missing_evidence_references.length !== 0) return fail("reviewer declares missing evidence");
        if (typeof agent.evidence_payload !== "string" || !agent.evidence_payload) return fail("reviewer canonical evidence bytes are missing");
        if (!SHA256.test(String(agent.evidence_sha256 || ""))) return fail("reviewer evidence digest is missing or malformed");
        const computedEvidenceDigest = await sha256Hex(agent.evidence_payload, cryptoApi);
        if (computedEvidenceDigest !== agent.evidence_sha256) return fail("reviewer evidence digest does not match exact evidence bytes: " + agent.agent);

        let evidencePayload;
        try {
          evidencePayload = JSON.parse(agent.evidence_payload);
        } catch (_) {
          return fail("reviewer evidence payload is not valid JSON: " + agent.agent);
        }
        const evidenceKeys = Object.keys(evidencePayload).sort();
        const references = agent.evidence_references.slice().sort();
        if (stableJson(evidenceKeys) !== stableJson(references)) return fail("reviewer evidence keys do not match declared references: " + agent.agent);
        for (const reference of agent.evidence_references) {
          const resolved = resolveReference(result, reference);
          if (!resolved.found) return fail("unresolved computed-evidence reference: " + reference);
          if (stableJson(evidencePayload[reference]) !== stableJson(resolved.value)) return fail("evidence payload differs from computed result: " + reference);
        }

        if (!Array.isArray(agent.quantitative_claims)) return fail("structured quantitative claims are missing: " + agent.agent);
        for (const claim of agent.quantitative_claims) {
          if (!claim || typeof claim.reference !== "string" || typeof claim.unit !== "string") return fail("malformed quantitative claim: " + agent.agent);
          const resolved = resolveReference(result, claim.reference);
          if (!resolved.found || typeof resolved.value !== "number" || !Number.isFinite(resolved.value)) {
            return fail("quantitative claim does not resolve to a finite computed number: " + claim.reference);
          }
          if (stableJson(claim.value) !== stableJson(resolved.value)) return fail("quantitative claim value differs from computed result: " + claim.reference);
          if (!agent.evidence_references.some(reference => claim.reference === reference || claim.reference.indexOf(reference + ".") === 0)) {
            return fail("quantitative claim is not covered by declared evidence: " + claim.reference);
          }
        }
      }
      if (seen.size !== EXPECTED_AGENTS.size) return fail("one or more expected reviewers are absent");
      const completedCount = agents.filter(agent => agent.status === "completed").length;
      const notApplicableCount = agents.filter(agent => agent.status === "not_applicable").length;
      const resolvedCount = completedCount + notApplicableCount;
      const incompleteAgents = agents.filter(agent => !["completed", "not_applicable"].includes(agent.status)).map(agent => agent.agent);
      if (execution.agent_count !== agents.length || execution.completed_agent_count !== completedCount || execution.not_applicable_agent_count !== notApplicableCount || execution.resolved_agent_count !== resolvedCount) return fail("execution reviewer counts do not match the artifact");
      if (execution.status !== "completed" || !Array.isArray(execution.incomplete_reasons) || execution.incomplete_reasons.length !== 0) return fail("execution manifest is incomplete");
      if (!Array.isArray(execution.incomplete_agents) || stableJson(execution.incomplete_agents) !== stableJson(incompleteAgents)) return fail("execution manifest incomplete reviewer list does not match");
      if (!artifact.training_status || typeof artifact.training_status !== "object") return fail("training provenance status is absent");
      if (artifact.training_status.verified !== true && artifact.training_status.claim_allowed !== false) return fail("unverified training provenance is not explicitly disallowed");

      const expectedPayload = {
        agent_version: "1.2",
        analysis_modules: execution.analysis_modules,
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
          evidence_payload: agent.evidence_payload,
          quantitative_claims: agent.quantitative_claims,
          missing_evidence_references: agent.missing_evidence_references
        })),
        training_status: artifact.training_status
      };
      if (stableJson(canonicalPayload) !== stableJson(expectedPayload)) return fail("canonical execution payload differs from the artifact contents");
      return { ok: true, reason: "Job/input binding, exact execution bytes, per-reviewer evidence bytes, and quantitative claims verified", artifact: artifact };
    } catch (error) {
      return fail(error && error.message ? error.message : "specialist artifact verification failed");
    }
  }

  return { verifySpecialistArtifact: verifySpecialistArtifact, stableJson: stableJson };
});
