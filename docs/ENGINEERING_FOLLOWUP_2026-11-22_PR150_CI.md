# Engineering follow-up — CI completed on PR #150 (2026-11-22)

This follow-up supersedes the initial CI-unavailable note in `ENGINEERING_DELTA_2026-11-22_0313IST.md`. The initial PR-head run lookup was empty while CI was starting; after polling, the exact-head checks completed successfully.

## PR #150 exact-head validation

- PR: https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/150
- Head: `2a4f94493a33f47d91315c6646365daf3bc89534`
- Base: `d4a653e94501e8b9f1ec9de09ff71720f90ab340` (main)
- Main CI run: [44953480644](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953480644), job `136996350200`: **153 passed, 1 skipped, 21 subtests passed**.
- Public E2E workflow run: [44953480581](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953480581), job `136996350049`: **validate-harness succeeded**; public-upload job `136996351197` was **skipped**. This is PR-only runner evidence.
- Watchdog workflow run: [44953480651](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953480651), job `136996350389`: **success**; watchdog tests, compile, and YAML syntax validation passed.
- PR validation log: parity/policy tests **8 passed**; watchdog decision tests **7 passed**; both workflow YAML syntax checks passed.
- The connector returned no combined status contexts; workflow run/job metadata and full job logs were inspected for the completed runs.

## Safety result

The updated PR branch now has no automatic E2E schedule or push trigger, no watchdog schedule/dispatch job or Actions write permission, and the public-upload job is manual `workflow_dispatch` only on upstream `main`. The parity guard and offline PR validation remain. **Main is unchanged**, so its scheduled E2E and watchdog are still active until an authorized merge. No E2E was dispatched by this engineering run, and no public upload/inference occurred.

## Evidence tier

- CI: exact-head PR CI and offline harness jobs above.
- Runner: workflow validation and tests only; not public inference.
- Public: no upload, job, inference, report, or deletion proof.

## Gate/risk

M0 remains partial because the full all-open-PR diff/check/log/artifact audit and complete Actions inventory are unfinished. M1 is not accepted because runtime parity/checkpoint identity has not been independently verified on deployed main. M2–M7 remain unaccepted. Deadline risk for 2027-01-01 remains high.

Next: continue the prioritized PR audit and reconcile runtime parity/watchdog/checkpoint integration. Do not merge, deploy, inspect Render, or dispatch public E2E without authorization.

## Fresh audit — 2026-11-22 06:12 IST

This section adds evidence from the current run. Main remains unchanged and none of the live checks below is public-inference proof.

### Main and Actions enumeration

- Main: `d4a653e94501e8b9f1ec9de09ff71720f90ab340`; freshly fetched commit verification is `verified=true, reason=valid`.
- Branch-main Actions query: pages 1–10 returned 100 each; page 11 returned 0. API `total_count=2500`, but the accessible sequence exposes only 1,000 records, so 2,500 is not fully enumerated.
- Scheduled-event query: pages 1–6 returned 100 each (`total_count=600`); all populated pages were fetched in this run.
- Exact-current-main SHA query: pages 1–4 returned 100 each and page 5 returned 95 (`total_count=495`); all populated pages were fetched.
- Open PR metadata: page 1 returned all 99 open PRs. Full diff/check/log/artifact audits for all 99 are still incomplete.

### Latest exact-main E2E #301

Run [44966699214](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44966699214), scheduled, exact main; job `137037234591`, failure. The full 47,161-character log and steps were inspected.

- Published site/API preflight passed (site HTTP 200; latest-main commit API HTTP 200).
- Health probes 1–4 returned `ReadTimeout`; probe 5 returned HTTP 200. The diagnostic still reports `api_health_request_error=ReadTimeout`, confirming the known stale-health-state issue.
- Runtime parity remained false. Five paths were reported: three script paths not shipped by Render plus genuine runtime mismatches `webapp/community.py` and `webapp/community_app.py`.
- Render reported branch `main`, SHA `bb6a9d27537e12b85768c7fead1467253b2423ba`; expected main is `d4a653e94501e8b9f1ec9de09ff71720f90ab340`. `checkpoint_available=true` is not digest verification.
- `guest_token_seen=false`, `job_id_seen=false`, `cleanup_attempted=false`, `cleanup_verified=false`. No upload, inference, specialist outputs, report, or deletion was reached.

Failure artifact #14731389860 was downloaded, ZIP-tested, extracted, and parsed:

- ZIP: 1,052 bytes; SHA-256 `0f41ba3a21b1008d5fd40bc76b654bcda190130768ef3258cc8e465e51f19214`.
- JSON `live-agent-e2e-failure.json`: 2,806 bytes; SHA-256 `7a40410b73868de6466abaddec4ca27d689611ac00fb6e6896f870e0cb050af4`.
- Artifact contains diagnostics only; no image.

### Watchdog and release monitor

- Watchdog run [44950471453](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44950471453), job `136987053452`, success. Fresh full log confirms `age_seconds=6338` and accepted public-E2E dispatch while deployed runtime SHA/checkpoint identity was not checked by the main watchdog. No artifact was published by this run.
- Release monitor run [44948526489](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44948526489), job `136981084908`, monitor job succeeded, but its evidence status remains `BLOCKED`, `release_ready=false`; frozen E4 checkpoint artifact `12183110279` lookup returned HTTP 404.
- Release artifact #14724805477 ZIP SHA-256 `776268415f313fc83821bfca29bc4b58e9c8f26c7404b96ef1b0179d3d0f925a`; extracted `release_status.json` SHA-256 `19f27f189f6c034a3a304fa83b4df72ccd9072b1a175ee153a644c8e6e15c28a`. JSON parsed successfully.

### PR safety/runtime audit

- PR #150 head `2a4f94493a33f47d91315c6646365daf3bc89534`, base main. Its current five-file diff explicitly removes E2E schedule/push triggers, retains manual dispatch, gates public upload to upstream `main`, removes watchdog schedule/dispatch and Actions write permission, and keeps PR validation offline. The title/body primarily describe Docker parity classification; the actual diff includes the safety pause. Exact-head CI [44953480644](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953480644) reports 153 passed, 1 skipped, 21 subtests; E2E validation [44953480581](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953480581) passed with public upload skipped; watchdog validation [44953480651](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953480651) passed. Main is unchanged and these changes are not merged.
- PR #94 head `4c1376105f3c6d25cc9f376a5906cfab960e532d`, base main, four files. It introduces `scripts/e2e_health_state.py` and regression tests that clear stale health-error/body fields after recovery. Exact-head tests [44938285032](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44938285032) report 150 passed, 1 skipped, 1 warning; offline harness validation [44938285077](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44938285077) passed with public upload skipped. This is the existing fix; no duplicate PR was created.
- PR #92 head `838b89d51cae3db2171bc67b0c2389c043b34122`, base main. It adds a deployed-runtime identity/checkpoint gate to the watchdog. Its CI evidence is historical and not refreshed in this audit. Current main's watchdog still dispatches without deployed-SHA/checkpoint verification.
- PR #178 exact prior head `65485a0d3aa1c287f08967e259327488af2110bf` tests [44958606549](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44958606549) reported 145 passed, 1 skipped. This new tracker commit will require its own CI; the previous result is not carried forward as proof.

### Milestones and deadline

M0 remains partial: all accessible Actions page sequences and open-PR metadata are refreshed, but all-99 PR diffs/checks/logs/artifacts have not been audited. M1 remains unaccepted because the fail-closed stack is not integrated and live identity is unverified. M2–M7 remain unaccepted. Deadline risk is high.

Next: verify PR #178's new documentation commit CI; prioritize exact-head #92/#105/#146 integration review, and keep main's automatic public E2E dispatch risk explicitly escalated until PR #150 is authorized for merge. Do not inspect Render, deploy, upload, or infer without authorization and parity/pin verification.


## Fresh audit — 2026-11-22 08:08 IST

Main and Actions were refreshed again. No public upload/inference was performed.

### Main/signature and Actions pagination

- Main: `d4a653e94501e8b9f1ec9de09ff71720f90ab340`; commit verification freshly fetched: `verified=true, reason=valid` (verified timestamp `2026-10-24T07:08:31Z`).
- `branch=main`: page 1 and pages 2–10 each returned 100; page 11 returned 0. API total is 2,500, but the accessible sequence exposes only 1,000 records.
- `event=schedule`: pages 1–6 returned 100 each; page 7 returned 2; all 602 populated records were fetched.
- Exact main SHA: pages 1–4 returned 100 each; page 5 returned 98; all 498 populated records were fetched.
- Open PR listing: 99 open PRs. Metadata refreshed; full diff/check/log/artifact audit for all 99 remains incomplete.

### E2E #302, watchdog #129, release monitor #372

- E2E [44972727518](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44972727518), exact main, event `workflow_dispatch`, job `137055811890`: failure. Full 47,160-character job log and steps inspected.
- Public preflight/site and latest-main API returned HTTP 200. Health attempts 1–4 timed out; attempt 5 returned HTTP 200 but the final diagnostic retained `ReadTimeout`. Runtime parity false. Render SHA `bb6a9d27537e12b85768c7fead1467253b2423ba` differs from main. Checkpoint was available, but digest verification was not demonstrated. Guest token/job ID absent; cleanup not attempted; upload/inference not reached.
- Failure artifact #14734721065 was downloaded through the GitHub artifact connector, materialized, ZIP integrity-tested, extracted, and parsed. Archive SHA-256: `acc4026852be6922aeb5dc93caa00ab0e196a8c6f9004f26c7c9110ceae2e999`; extracted JSON SHA-256: `2303f89a8945d29947e7fba0efd2c22610ac15f7192936e9cd02a9adda896bdb`. 1,051-byte ZIP, 2,806-byte JSON; no image.
- Watchdog [44972719647](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44972719647), job `137055785175`, succeeded. Full 12,691-character log inspected: E2E stale age 4,521 seconds and dispatch accepted. It did not verify deployed SHA/checkpoint identity before dispatch. This is runner dispatch evidence, not public inference.
- Release monitor [44969806811](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44969806811), job `137046876009`, completed successfully as a monitor but returned `status=BLOCKED`, `release_ready=false`; frozen E4 checkpoint artifact `12183110279` lookup returned HTTP 404. Artifact #14732719621 was downloaded, materialized, ZIP-tested and parsed: archive SHA-256 `d24dcdf1d2e6a1ce252d8178f120aa55d58864f892cee4fddf6a851e8427c442`; JSON SHA-256 `bd8774dda8a6139d7ad5dc91fb4f4bb5d2c915a526b152cc1fa80cac4aaeb1d`. ZIP size 1,200 bytes, JSON 2,765 bytes.

### Priority runtime PR checks refreshed

- #150 head `2a4f94493a33f47d91315c6646365daf3bc89534`: CI run 44953480644 passed (153 passed, 1 skipped); offline E2E validation and watchdog validation passed; public-upload job skipped. The safety pause remains PR-only, not active on main.
- #92 head `838b89d51cae3db2171bc67b0c2389c043b34122`: tests/validation passed on run 43437830689 (165 passed, 1 skipped, 7 subtests); dispatch job skipped. Historical runner evidence.
- #94 head `4c1376105f3c6d25cc9f376a5906cfab960e532d`: tests run 44938285032 passed (150 passed, 1 skipped); offline E2E harness validation passed.
- #103 head `5372d812304eb3612dc7890e1f03ee9361e5c423`: CI run 41794611644 passed (148 passed, 1 skipped); public-upload job skipped.
- #105 head `1d4726b430da933180d2c2744ec564a442c09b96`: tests run 44517779139 passed (158 passed, 1 skipped). Checkpoint-worker validation is runner-only.
- #146 head `7c7f348333ba2cc1fe4bc53e53a0f1e62a9ef433`: tests run 44900605180 passed (163 passed, 1 skipped); checkpoint-worker run 44900605055 passed under its memory gate. Runner evidence only.
- #178 prior head `582175007aefdf24c5460770f650858d3aecef40`: two exact-head test checks 44968273192 and 44968267964 passed; Supabase preview skipped. The replacement documentation commit requires fresh CI.

The PR stack is not integrated or proven together. #150's manual-only pause and #92's identity gate conflict in workflow behavior and need an additive, reviewed reconciliation; do not merge the identity-gated watchdog alone while main still dispatches against a stale runtime.

### Gate/risk

M0 remains partial: complete accessible Actions pagination and PR metadata are refreshed, but full diffs/checks/logs/artifacts for all 99 PRs are not audited. M1 remains unaccepted: main's watchdog still dispatches without verified runtime/checkpoint and deployed parity is false. M2–M7 remain unaccepted. Deadline risk for 2027-01-01 remains high.

Next: continue the M0 source/diff audit, prioritize a single additive M1 integration branch after exact source rereads, and keep public E2E dispatch paused only after authorization to merge the safety change. No Render inspection, deploy, upload, or inference was performed.

## Fresh research-provenance PR audit — 2026-11-22 09:09 IST

Main remains `d4a653e94501e8b9f1ec9de09ff71720f90ab340`; signature verification is `verified=true, reason=valid`. The current audit focused on the scientific baseline/transfer provenance stack rather than duplicating runtime-parity PRs.

### PR #169 — exact-main baseline selection and recipe verification
- Head `6183cf907381880204e94640e2fb4db989cf07e7`; base main `d4a653e94501e8b9f1ec9de09ff71720f90ab340`.
- Five files; full patch reviewed. Restricts baseline push workflow to main, defaults the baseline recipe to 100 epochs, verifies checkpoint config/seed/epochs with safe `weights_only=True`, and makes S-BIAD634 transfer select a successful exact-main baseline run/checkpoint.
- Associated CI run [44664121649](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44664121649) completed successfully. No fresh scientific baseline result was generated in this audit.

### PR #173 — source/acquisition-manifest accurate E4/E5 provenance
- Head `5819fe1cda8b63327099b32450502f60cf049678`; base main.
- Seven files; full patch reviewed. Adds source-download manifest to E4; binds source split/acquisition, configuration, checkpoint and method-record hashes. E5 fixes the preregistered 20-epoch recipe and cross-checks source/target acquisition identities and shared seed/epoch identity across variants; completeness checks require all 79 target images and metric fields.
- Associated CI run [44822792979](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44822792979) completed successfully. CI does not establish fresh training/evaluation reproducibility.

### PR #177 — S-BIAD634 target and metric artifact binding
- Head `b7f5c347ca056fdae397e851f2de116de696b520`; base is PR #169 head `6183cf907381880204e94640e2fb4db989cf07e7`.
- Two files; full patch reviewed. Adds target archive and manifest hashes, target manifest inventory count, metrics/evaluator/instance-metrics hashes, baseline config/verifier hashes, explicit no-target-training flag, and 79-image/IoU-threshold completeness checks before artifact upload.
- Associated CI run [44832437317](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44832437317) completed successfully. This is stacked PR CI evidence, not a fresh exact-main transfer result.

### Baseline audit conclusion
The provenance fixes are technically complementary and the #169 → #177 dependency is explicit. They remain PR-branch evidence: no current-main baseline checkpoint, exact recipe, target manifest, or fresh transfer artifact was independently reproduced here. Prioritize this stack after the M0 audit, with #169 as the baseline foundation, then #173 source-training provenance and #177 target-evaluation provenance. Next science-stack audit: #175/#174 safe checkpoint loading and #168 baseline workflow/config alignment. Do not mark M2 complete from these CI runs.


## Fresh science/security stack audit — 2026-11-22 09:10 IST

The next prioritized research/runtime PRs were inspected at their exact current heads and full patches. These are source/CI findings; none proves live inference or a fresh scientific result.

### PR #175 — weights-only research evaluators
- Head `2b3afbe9ebeaa312734f6e78098934480589360d`, base main; eight files.
- Reviewed changes: `weights_only=True` added to five research/evaluation checkpoint loaders and two E6 workflow loaders; AST/YAML regression tests enforce restricted loading.
- Exact-head CI runs [44814708387](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44814708387) (PR) and [44814703342](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44814703342) (push) both succeeded.

### PR #174 — safe initial checkpoint loading
- Head `cd3a14a7c7d994a6d41004cf78c3f63f2af003f4`, base main; two files.
- Adds a weights-only loader requiring a dictionary model state and tests safe tensor loading, malformed checkpoint rejection, and unsafe pickle rejection.
- Exact-head CI [44747521522](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44747521522) and [44747512105](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44747512105) both succeeded.

### PR #168 — baseline epoch default
- Head `1ce0b31d0b227169abab6851bf4aa53a32529495`, base main; two files.
- Aligns the baseline workflow's default/manual training epochs with the committed 100-epoch config and adds a workflow/config consistency regression test.
- Exact-head CI [44264892049](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44264892049) and [44264881470](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44264881470) both succeeded.
- #169 includes the same 100-epoch alignment plus exact-main baseline/checkpoint verification; #168 may be redundant. Review dependency and test coverage before merging either, avoiding duplicate commits.

### PR #172 — production-image memory and live-check opt-in
- Head `982a04d44c9d23775cc1588e5be8d52814d2d9b5`, base main; ten files.
- Reviewed diff: live Render validation requires a manual main dispatch and explicit `allow_live_render=true` input (default false); constrained-memory validation builds the actual production community Docker image; thread-pool defaults are checked; uint16 raw min/max/dynamic range is preserved in measurements and evidence-bound specialist claims; tiled inference uses `torch.inference_mode()`.
- All five exact-head workflow runs succeeded: community validation [44649655426](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44649655426), BioMCP/web validation [44649655561](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44649655561), CI [44649655608](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44649655608), tiled checkpoint validation [44649655475](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44649655475), and push CI [44649649079](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44649649079).
- These are PR/runner checks. The opt-in live Render job was not run and no production image was inspected or deployed.

### Audit priority
The research/security changes are largely complementary, but #168 is likely a partial duplicate of #169's baseline default alignment. M0 remains open pending the complete 99-PR audit and Actions history limits. M1 is still blocked by main's unsafe automatic dispatch. Next review the research/evaluation stack for exact dependency conflicts, then source-level privacy/deletion paths; do not infer from green CI.
