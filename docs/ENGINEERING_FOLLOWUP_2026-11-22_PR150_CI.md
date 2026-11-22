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
