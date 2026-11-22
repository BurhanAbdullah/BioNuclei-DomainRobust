# Engineering audit — 2026-11-22 12:10 IST

This is an additive baseline refresh for PR #178. It records repository/CI evidence only; it does not establish deployment, public inference, or release readiness.

## Current-main identity

- Main: `97e35c1cc73f39fb2855268e441231975ba4bd0b`.
- GitHub commit API verification: `verified=true`, `reason=valid`; verified timestamp `2026-11-22T04:07:50Z`.
- Current-main CI push run `44992588956`: success; job `137116678746`, all steps including test run succeeded.
- Exact-main Actions query: 40 records on page 1; page 2 empty.
- Branch-main Actions query: 1,000 records (pages 1–10, 100 each); page 11 empty despite API `total_count=2500`. The API/connector exposed only the first 1,000 records, so the other 1,500 cannot be audited here.
- Scheduled-event query: 602 records; pages 1–6 contain 100 each, page 7 contains 2. Pagination is complete.
- Open PRs: 100 on page 1; page 2 is empty. Metadata was enumerated, but full diff/check/log/artifact review for all 100 PRs is not complete.

## Fresh exact-main research run

[E7 BBBC038 external validation run 44994082617](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44994082617) checked out exact main SHA above and failed in job `137121239581` at **Verify retained E4 artifact identity**. The complete job log was fetched and parsed (34,198 characters, 380 lines). The command queried retained artifact ID `12183110279` and GitHub returned HTTP 404; download, dataset acquisition, evaluation, cross-check, and evidence upload were all skipped. No E7 scientific metrics were produced.

The current E7 workflow at this main SHA uses a hard-coded default artifact ID and digest when manual inputs are absent, including for its `workflow_run` event. This is a reproducible source-level failure mechanism: the successful E4 run's artifact is not resolved dynamically from the triggering run. It should be addressed in the scientific-provenance milestone after the baseline gate, with a regression test for event-triggered exact-run artifact resolution.

Other exact-main research status observed:
- E6 external few-shot run `44994082640`: queued.
- E7 run `44994082617`: failed as described.
- S-BIAD634 zero-shot run `44990767024`: in progress.
- E6/E7 uncertainty, aggregate/finalizer and clean-environment workflows have skipped runs on the current SHA; they do not constitute fresh reproducibility evidence.

## Public E2E and runtime proof

No public E2E run was found in the exact-main SHA query. The latest inspected E2E [run 44972727518](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44972727518) is on older main `d4a653e94501e8b9f1ec9de09ff71720f90ab340`; job `137055811890` failed before public job creation. The complete 47,160-character job log confirms Render runtime parity was false, with mismatches in `scripts/aggregate_e6_fraction_evidence.py`, `scripts/download_aitslab_bioimaging1.py`, `scripts/public_e2e_schedule_watchdog.py`, `webapp/community.py`, and `webapp/community_app.py`. The diagnostic showed repeated health ReadTimeout, `checkpoint_available=true`, but no guest token. No public upload/inference was reached. Failure artifact `14734721065` was reported with ZIP SHA-256 `acc4026852be6922aeb5dc93caa00ab0e196a8c6f9004f26c7c9110ceae2e999`; artifact extraction/hash was not repeated in this refresh.

The latest inspected watchdog [run 44972719647](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44972719647), job `137055785175`, on that same stale SHA, accepted dispatch: log states `age_seconds=4521`, stale E2E SHA, then dispatch request accepted. It did not verify deployed SHA/checkpoint pin. This is runner/log evidence for a safety gap on the old SHA; it is not a public inference result.

The latest Pages deployment run `44983675451` had upload succeed and deploy step fail; its full log/artifact was not refreshed here. Do not infer a successful deployment.

Browser tools are read-only; this session has no originating browser context. Render was not selected, inspected, or deployed. No public upload or inference was attempted.

## Milestone ordering

- **M0 baseline:** prioritized engineering inventory exists in the existing PR documentation. This refresh records the current SHA, accessible run/PR pagination, and fresh E7 failure. Full review of all 100 PR diffs/checks/logs/artifacts and the 1,500 inaccessible branch-main runs remains a limitation; M0 is not yet declared complete.
- **M1 runtime integrity:** not accepted. Runtime parity and deployed SHA/checkpoint identity are not live-verified; fail-closed watchdog integration remains outstanding.
- **M2 scientific correctness:** not accepted. The fresh E7 run failed before data acquisition/evaluation; current-main provenance and E6/E7/uncertainty/clean-environment reproduction are incomplete.
- **M3–M7:** not accepted; public workflow, privacy/operations live verification, fresh research reproduction, real external BioMCP, and final acceptance are not proven.

## Evidence tiers

- **Repository/API:** main identity, commit signature, workflow source, PR metadata, and exact-SHA run metadata.
- **CI/runner:** current-main CI and E7 job outcome only. E7 did not reach dataset/evaluation steps.
- **Local parsing:** log extraction/inspection only; no scientific inference.
- **Public inference/deployment:** none.

## Risk and next action

The 2027-01-01 target is high risk with roughly six weeks remaining. Next safe task is to finish the M0 PR/check inventory within connector limits, then reconcile runtime parity, watchdog gating, and checkpoint-pin integrity as a single M1 integration. Do not merge, deploy, select Render, or dispatch public E2E without the required authorization and verified runtime/checkpoint identity.


## Fresh verification update — 2026-11-22 13:07 IST

### Main SHA and accessible Actions inventory

- Main is still `97e35c1cc73f39fb2855268e441231975ba4bd0b`; commit verification is `verified=true`, `reason=valid` (verification time `2026-11-22T04:07:50Z`).
- Branch-main runs: pages 1–10 each returned 100, page 11 empty, API total 2,500; only 1,000 are exposed through this connector listing. Schedule-event runs: pages 1–6 each returned 100, page 7 returned 2; all 602 are enumerated.
- Open PR metadata: 100 returned on page 1, page 2 empty. All PR head/base metadata is visible in the returned listing; the all-PR full diff/check/log/artifact audit is still incomplete. PR #178 is based on stale main `d4a653e94501e8b9f1ec9de09ff71720f90ab340` and its draft branch has not been rebased.
- A `head_sha` workflow-run listing query returned 0, so it was not treated as proof of no runs. The commit check-runs endpoint returned 47 checks, including current-main E7 failure, E6 25% in progress, and successful tests. The latest current-main public E2E/public watchdog runs are not present in the accessible page-1 listing; the newest inspected public E2E/watchdog runs below use stale SHA `d4a653e9...`.

### Current-main CI and science

- Main CI push run [44992588956](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44992588956) succeeded; job `137116678746` completed all steps including tests.
- E7 [44994082617](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44994082617), job `137121239581`, failed at retained-E4 artifact verification. The complete 34,198-character log was refreshed. Artifact ID `12183110279` returns 404; dataset/evaluation/evidence steps were skipped; no E7 metrics exist and the run has no artifacts.
- Source at exact main: `.github/workflows/e7_bbbc038_external.yml` (blob `f5a9c97e3956749d567c4b5f5ae989d32622ec48`) still falls back to hard-coded artifact ID/digest `12183110279` / `sha256:89e66617e272d30ec46471c8403950c404c772780ad778dd6f0e992fc795df0d` for `workflow_run`, rather than resolving the triggering successful E4 artifact. This is a confirmed M2 defect; it is queued behind the incomplete M0 gate.
- E6 [44994082640](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44994082640) is current-main and still in progress. Three fractions (1%, 5%, 10%) have successful runner jobs/artifacts; 25% has resolved the exact E4 checkpoint and verified the dataset split/leakage guard, but training is still running. The 25% job-log fetch was unavailable (connector BlobNotFound); no final metrics are asserted here. Current-main E6 workflow source `.github/workflows/e6_external_few_shot.yml` (blob `eadc9d8a1a8d2e3da887641b72a688b31a528846`) verifies source run branch, SHA, workflow identity, and exactly one unexpired E4 artifact before download.
- Zero-shot [44990767024](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44990767024) completed successfully. Runner success is not a public inference claim.

### E2E/watchdog refresh and failure-artifact hashes

The latest inspected public E2E [44972727518](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44972727518) and scheduled E2E [44966699214](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44966699214) both use stale SHA `d4a653e94501e8b9f1ec9de09ff71720f90ab340`. Both complete job logs/steps and failure-artifact metadata were refreshed. Each failure artifact was downloaded, ZIP-tested, extracted and JSON-parsed; the archives contain only the failure JSON, no source images:

- E2E #302 artifact `14734721065`: archive 1,051 bytes, SHA-256 `acc4026852be6922aeb5dc93caa00ab0e196a8c6f9004f26c7c9110ceae2e999`; extracted JSON 2,806 bytes, SHA-256 `2303f89a8945d29947e7fba0efd2c22610ac15f7192936e9cd02a9adda896bdb`.
- Scheduled #301 artifact `14731389860`: archive 1,052 bytes, SHA-256 `0f41ba3a21b1008d5fd40bc76b654bcda190130768ef3258cc8e465e51f19214`; extracted JSON 2,806 bytes, SHA-256 `7a40410b73868de6466abaddec4ca27d689611ac00fb6e6896f870e0cb050af4`.

Both artifacts report runtime-tree parity false; Render runtime commit `bb6a9d27537e12b85768c7fead1467253b2423ba` is ahead of expected SHA. Health attempts 1–4 timed out; attempt 5 returned HTTP 200 but retained `ReadTimeout`. `checkpoint_available=true` does not verify the digest. No guest token/job ID was observed; upload/inference and cleanup were not reached.

Watchdog [44972719647](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44972719647) is stale-main schedule run; steps refreshed and dispatch was accepted. The available log-fetch response was incomplete in this connector refresh, so the prior detailed log finding is retained only as historical evidence. There is no current-main public E2E/watchdog dispatch to inspect.

### PR #181 stale-retry guard

- PR #181 exact head `823f1f3922980cd91cea11c175d460a492cc88ff`, base current main `97e35c1cc73f39fb2855268e441231975ba4bd0b`. Full 2-file diff reviewed: retry is gated on failure, attempt limit, `head_branch == main`, and `head_sha == github.sha`; static tests cover the guard.
- Exact-head checks: 2 test checks succeeded; Supabase Preview skipped. This is PR/runner evidence only. PR remains open and unmerged; main's E6 retry watchdog does not yet include the SHA/branch guard.

### Evidence tier and gate status

Repository/API and exact source evidence are separate from CI/runner checks and local artifact parsing. No public upload/inference or live deployment is verified. Browser tools available here are read-only; no originating browser context is available. Render was not selected/inspected/deployed. M0 remains partial due all-PR diff/check/log/artifact gaps and inaccessible main-run history; M1–M7 remain unaccepted. Deadline risk is high (about 40 days to 2027-01-01).

Next: finish M0 inventory, then review the fail-closed runtime stack without merging overlapping PRs independently. M2 E7 exact-run artifact resolution must remain queued until M0 is accepted. No public E2E dispatch or merge was performed.
