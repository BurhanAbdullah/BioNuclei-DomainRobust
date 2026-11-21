# Engineering delta — 2026-11-22 03:13 IST

This additive audit records newly inspected exact-main Actions logs/artifacts and a safety update to the existing runtime-parity PR. It does not declare release readiness.

## Main identity

- Main SHA used for the exact-main run: `d4a653e94501e8b9f1ec9de09ff71720f90ab340`.
- Fresh commit fetch resolved this SHA and its message, but the normalized GitHub connector did not expose signature-verification fields. The historical verification record is not re-certified in this update.
- Browser control is unavailable because this session lacks the originating browser context. GitHub's Actions run-list/pagination endpoints are not exposed through the available connector; selected known runs were refreshed instead.
- Render workspace/services were not inspected.

## Exact-main public E2E failure

Run [44941126536 (#298)](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44941126536), scheduled, exact current main. Job [136958351446](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44941126536).

The full 47,162-character job log and failure artifact were inspected. The workflow failed at runtime-parity before guest session/job creation or upload:

- Render branch: `main`.
- Render commit: `bb6a9d27537e12b85768c7fead1467253b2423ba`, not current main.
- Runtime parity: false.
- Five mismatches reported: three script paths not copied into Render images, plus genuine shipped runtime mismatches `webapp/community.py` and `webapp/community_app.py`.
- Health attempts 1–4 timed out; attempt 5 returned HTTP 200. The diagnostic still retains `api_health_request_error=ReadTimeout`, so the recovered health record is internally inconsistent.
- `checkpoint_available=true` is not digest verification.
- `guest_token_seen=false`, `job_id_seen=false`, `cleanup_attempted=false`. No upload/inference was reached.

Failure artifact #14722175126 was downloaded, integrity-checked, extracted and parsed:

- ZIP: 1,053 bytes; SHA-256 `1d06c127d9b4dd853b996ba05652873bda4a38d0c52c2b323f013551843c7ece`.
- JSON: 2,807 bytes; SHA-256 `e16cbb7d97a7ef6692c602e8064d191ee19f5a17c9270c5929b4260cec7d3299`.
- JSON keys and parity/health fields were parsed. The artifact contained only the diagnostic JSON; no image.

## Watchdog dispatch evidence

Run [44920438929](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44920438929), job `136895080077`, succeeded. The full job log confirms the watchdog considered the last E2E stale (`age_seconds=15372`) and accepted dispatch of the public E2E workflow. The watchdog does not check deployed Render SHA or checkpoint identity before dispatch. This dispatch led to the above parity failure; it did not produce public inference.

## Research release monitor

Run [44916557550](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44916557550), job `136883314106`, completed successfully as a monitor, but its parsed artifact reports:

- `monitor=healthy`
- `status=BLOCKED`
- `release_ready=false`
- blocker: frozen E4 checkpoint artifact `12183110279` returned HTTP 404.

Artifact #14711388375:

- ZIP: 1,199 bytes; SHA-256 `42552f5bbdbf2e7101e52dd4566085869a64ae396ddbe179952ddd658e61b5d0`.
- Extracted `release_status.json`: 2,765 bytes; SHA-256 `42a4e6fe1a7733b622bfb27b65e9587887650795da14e1e7f234a1fa7450de2`.
- Parsed identities: E6 run 40047981532, E6 finalize 40054174193, E7 run 40008115593, uncertainty 40060954277, clean reproduction 40060994966. These are monitored artifact references, not newly reproduced research results.

## Safety change on existing PR #150

PR [#150](https://github.com/BurhanAbdullah/BioNuclei-DomainRobustness/pull/150) was reread at exact prior head `ed314fca17ba7a5dd7848c39e8410b27dea46185` and base main `d4a653e94501e8b9f1ec9de09ff71720f90ab340`. The workflow, parity test, and watchdog workflow were fetched before editing.

Added commits on the existing PR branch (no duplicate PR):

- `658e3f2ca551de71e84187e3aa5afd366559c1f0`: remove automatic E2E schedule and push triggers; retain `workflow_dispatch` and offline PR validation; require manual dispatch, upstream repository, and main ref for the public upload job; expand PR validation paths and offline test steps.
- `bf42a0e5826780a6e40e0ca8be629467e4f2efc`: remove watchdog schedule and dispatch job, including Actions write permission; retain PR-only validation.
- `2a4f94493a33f47d91315c6646365daf3bc89534`: tests enforce manual-only E2E, disabled watchdog dispatch, and PR-path coverage.

Updated PR head: `2a4f94493a33f47d91315c6646365daf3bc89534`; base remains main at `d4a653e94501e8b9f1ec9de09ff71720f90ab340`. Full PR diff was refreshed and the three new commit diffs inspected.

Local validation was run in an isolated directory populated from the fetched source (not a repository checkout):

- parity/policy tests: **8 passed**;
- watchdog decision tests: **7 passed**;
- Python compile checks: passed;
- Ruby YAML syntax checks for both workflow files: passed.

Exact-head CI could not be retrieved: the PR-head workflow-run lookup returned an empty list and combined status returned no statuses. These are unavailable/empty connector results, not proof that GitHub CI is green or absent. No PR merge, deployment, upload, or E2E dispatch occurred. The public E2E is paused in the PR branch only; main is unchanged until a merge is authorized.

## Evidence tier

- **Repository/API:** exact main/PR metadata and fetched source.
- **CI/runner:** E2E #298 parity preflight and watchdog/release-monitor runner logs/artifacts. No inference evidence.
- **Local:** copied-source tests and syntax checks only.
- **Public upload/inference:** none.
- **Deployment:** not inspected.

## Milestone disposition

- **M0:** partial/not accepted. Prior baseline and prioritized audits exist, but complete all-open-PR diff/check/log/artifact audit and complete Actions enumeration remain outstanding.
- **M1:** not accepted. Runtime parity, watchdog/deployment/checkpoint identity, authenticated API and health contract are not integrated and verified on deployed main.
- **M2–M7:** not accepted. Fresh scientific provenance/reproduction, public upload-to-inference, authorized privacy/deletion verification, and real external BioMCP remain outstanding.

## Deadline risk and next action

The 2027-01-01 target remains **high risk**. Prioritize verifying CI for updated PR #150, then review the existing fail-closed watchdog/checkpoint stack (#92/#105/#146) against the exact current sources. Keep automated public E2E dispatch paused in the PR branch. Do not inspect Render or merge/deploy without authorization.

## Fresh audit — 2026-11-22 04:14 IST

This follow-up supersedes the latest-run/Actions-page snapshot above only where new evidence is listed. The full PR audit remains incomplete.

### Main identity

- Main remains `d4a653e94501e8b9f1ec9de09ff71720f90ab340`.
- Fresh commit API verification: `verified=true`, `reason=valid`; `verified_at=2026-10-24T07:08:31Z`. This is the current unchanged commit, freshly re-fetched and verified.

### Actions pagination refreshed

- Branch `main`: pages 1–10 returned 100 records each; page 11 returned 0. API `total_count=2500`, but only 1,000 records were returned by the accessible page sequence; do not treat this as a complete 2,500-run inventory.
- Event `schedule`: pages 1–5 returned 100 records each, page 6 returned 99; `total_count=599`. All populated pages were refreshed.
- Exact current-main SHA: pages 1–4 returned 100 each, page 5 returned 94; `total_count=494`. All populated pages were refreshed.
- Open PR listing: 99 PRs returned on the first page. Exact head/base metadata was refreshed; complete diff/check/log/artifact review of all 99 is not complete.

### Latest exact-main E2E and watchdog

- E2E #299, run [44950482311](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44950482311), event `workflow_dispatch`, exact main, failed in job `136987088691`. The full 47,163-character job log and artifact were inspected.
- Render reports branch `main`, SHA `bb6a9d27537e12b85768c7fead1467253b2423ba`, while current main is `d4a653e94501e8b9f1ec9de09ff71720f90ab340`. Runtime parity is false; the diagnostic lists five paths: three scripts not copied to the image and the genuine shipped mismatches `webapp/community.py` and `webapp/community_app.py`.
- Health attempts 1–4 timed out; attempt 5 returned HTTP 200. Diagnostic still has `api_health_request_error=ReadTimeout`. `checkpoint_available=true` is not checkpoint digest verification. `guest_token_seen=false`, `job_id_seen=false`, `cleanup_attempted=false`; upload/inference was not reached.
- Failure artifact #14724819791 was downloaded, ZIP integrity checked, extracted and JSON parsed. ZIP SHA-256: `332a292c6ed8036a8d7ef0351594cf5362b2c09aa0e69de151c978e559f7f677`. Extracted JSON SHA-256: `dc4274f9c1e4be1bacea2a8380e8442d7c5dde44f0436f1c267c7ca854789559`. JSON size 2,807 bytes; no image was present.
- Watchdog #127, run [44950471453](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44950471453), job `136987053452`, succeeded. Full log records E2E age `6338` seconds and an accepted dispatch. Main still has the scheduled watchdog and E2E triggers; PR #150's pause is unmerged. This is a concrete safety blocker requiring merge authorization, not a reason to dispatch manually.

### PR #150 exact-head CI

- Head `2a4f94493a33f47d91315c6646365daf3bc89534`, base current main.
- CI run [44953480644](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953480644), job `136996350200`: **153 passed, 1 skipped, 21 subtests passed**.
- Offline E2E validation run [44953480581](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953480581), job `136996350049`: passed; public upload job `136996351197` skipped.
- Watchdog validation run [44953480651](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953480651), job `136996350389`: passed.
- These are PR CI/offline-harness results, not public upload/inference evidence.

### PR #178 baseline tracker validation

- PR #178 exact head `90bbf8af0374ad5f5c1830e3abd0643f5174512f`, base current main. Existing baseline docs were reread at this head before this update.
- CI run [44953702964](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953702964), job `136997036694`: **145 passed, 1 skipped**. A second test run [44953697267](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953697267), job `136997019393`, also reported **145 passed, 1 skipped**. These checks validate the current pre-update PR head only; new-head CI is pending after this documentation update.

### Evidence tier and gate

- **Repository/API:** exact main and signature verification, Actions page metadata, PR metadata and patches.
- **CI/runner:** E2E #299 preflight failure, watchdog dispatch, PR #150 CI, and PR #178 CI. No public inference.
- **Public upload/inference:** none. **Deployment:** not inspected.
- **M0:** still partial; Actions populated pages refreshed, but full per-PR diff/check/log/artifact audit is unfinished.
- **M1:** not accepted; stale runtime, parity, watchdog dispatch and checkpoint pin are unresolved on deployed main.
- **M2–M7:** not accepted.
- **Deadline:** high risk for 2027-01-01; integration and authorized deployment/public validation remain critical-path blockers.

Next safe work: audit the existing #103 authenticated API and #92 fail-closed gate at exact heads, and reconcile the #105/#146 checkpoint stack without merging or touching Render. Do not manually dispatch public E2E while runtime identity is stale/unverified.
