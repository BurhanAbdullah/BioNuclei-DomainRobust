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
