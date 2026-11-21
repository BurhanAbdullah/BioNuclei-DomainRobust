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