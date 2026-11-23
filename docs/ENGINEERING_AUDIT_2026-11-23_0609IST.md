# Engineering audit — 2026-11-23 06:09 IST

This is an additive refresh for PR #178. Repository/CI evidence is separated from runner and public-runtime evidence. No Render workspace/service was inspected; no deployment, merge, manual upload, or new public E2E dispatch was performed.

## Identity and integrity

- Current main SHA: `b8d4a3b015cfcff56201b889702dc0ce7ee83e4f`.
- GitHub commit API verification: `verified=false`, `reason=unsigned`.
- Repository API reports `main` unprotected (`protected=false`); required status-check enforcement is not enabled in the returned branch metadata.
- Exact-main CI [45051076563](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45051076563), job `137296096482`: success, **158 passed, 1 skipped**. The complete job log was fetched.
- Current-main SHA query: 15 records on page 1, total 15 (complete for this SHA).

## Actions pagination and PR inventory

| Query | Fresh page counts | API total | Coverage |
|---|---|---:|---|
| `branch=main` | pages 1–10: 100 each; pages 11–25: 0 each | 2,500 | 1,000 records exposed; 1,500 not accessible through this endpoint |
| `event=schedule` | pages 1–6: 100 each; page 7: 11 | 611 | complete |
| `head_sha=<current main>` | page 1: 15 | 15 | complete |
| open PRs | page 1: 100; page 2: 4; page 3: 0 | 104 | metadata refreshed |

All 104 open-PR metadata records were refreshed. The full-diff/check/log/artifact audit is not complete for all PRs. The current PR #178 head and base were rechecked; its base is still older than main. The M0 gate remains incomplete.

## Current-main runtime source and E2E evidence

Current main has no public-upload job event guard in `.github/workflows/live-public-agent-e2e.yml`. The workflow triggers on schedule, main push, manual dispatch, and a PR path filter; the `public-upload-to-agent` job has no event/ref/repository `if` restriction. PR #187 adds an offline-only PR validation job and restricts public upload to upstream `main`, but it remains unmerged.

The current-main watchdog workflow schedules `recover-missed-e2e` with `actions: write`. Source blob for `scripts/public_e2e_schedule_watchdog.py`: `6800946aeb84a1243219e2f85fd67ea0fee6a67b`. The `should_dispatch` decision suppresses only a recent exact-main run or an active exact-main run; when the latest run is stale/old/missing it dispatches without checking Render's deployed SHA or checkpoint identity. This is a source-level M1 blocker.

### Latest scheduled E2E — run 45078374593

- [Run](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45078374593), job [137380627039](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45078374593/job/137380627039): failed in the public upload/inference step. Syntax and browser dependency setup succeeded.
- Site and UI/API preflight were HTTP 200. Runtime parity failed: Render branch `main`, reported commit `bb6a9d27537e12b85768c7fead1467253b2423ba`, main comparison `ahead`, parity `false`. Current expected main is `b8d4a3b015cfcff56201b889702dc0ce7ee83e4f`.
- Reported 34 main-comparison paths and 11 runtime-diff paths. Health attempts 1–4 were `ReadTimeout`; attempt 5 returned HTTP 200, but the recorded request error remains `ReadTimeout`. `checkpoint_available=true` is not checkpoint digest verification.
- `guest_token_seen=false`, `job_id_seen=false`, `cleanup_attempted=false`, `cleanup_verified=false`. The run did not create a guest session/job, upload, infer, or clean up.
- Failure artifact [14776236426](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45078374593/artifacts/14776236426) was downloaded, ZIP integrity-tested, unpacked and JSON-parsed. ZIP SHA-256: `5c90001825841558a98eccc29307e902c0e88179f094c58e770c1f3c20f19cd6`; extracted JSON SHA-256: `fa958651e4ac6d2fac5f6b7d14e09b887ce20e36cc973d8abf66d63ac6a461e2`.

This is Tier C public E2E **preflight failure evidence only**, not public inference proof.

### Watchdog — run 45080030259

- [Run](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45080030259): workflow succeeded; scheduled recovery job succeeded; PR validation job skipped.
- The complete recovery-job log indicates an exact-main E2E was recent (1,092 seconds) and suppressed a duplicate. The watchdog success does not prove deployed runtime or checkpoint identity.

## Scientific target acquisition failure

Current-main S-BIAD634 zero-shot run [45077440306](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45077440306), job `137377712207`, failed at **Download and inventory S-BIAD634**. It had selected baseline run `45063913011`, downloaded the baseline checkpoint artifact `14775742324` (downloaded SHA-256 `09a46f635762b27a9179836e4ede92fe4d58d04fbe5872eb6a8b67a725e07788`), and recorded provenance. Target evaluation and metrics were skipped.

Failure artifact [14775299939](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45077440306/artifacts/14775299939) was downloaded, ZIP integrity-tested, unpacked and parsed. Archive SHA-256: `0dc2c8298f2d490bade6d5a53c81c185ab350d12e80f1000edfc3e1a26e5a213`; extracted provenance SHA-256: `1d8bd92691d05a33d19f8ca62ed8a2fc2997978dff029ce692b1a7aee3f6576c`. JSON binds repository, current-main SHA, workflow run `45077440306`, and baseline run `45063913011`; it contains no dataset manifest or metrics.

Downloader source at current main, blob `d6e5a27f55cc6c4bd77ef8700aecb891e93a3e3f`, uses direct ZIP URL `https://www.ebi.ac.uk/biostudies/files/S-BSST265/dataset.zip`, a single `urlopen(timeout=120)`, no retry, unbounded `extractall`, and writes the manifest only after extraction. The workflow log/artifact does not expose the download exception. Network failure is possible but unconfirmed; do not patch retry behavior as though the cause were proven. The missing archive size/member limits are a separate robustness/security review item.

## Release monitor

[Release status watch 45074918226](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45074918226), job `137369912756`, succeeded as a monitor. Its downloaded artifact [14774119812](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45074918226/artifacts/14774119812) parsed to `status=BLOCKED`, `release_ready=false`. The E4 checkpoint artifact `12183110279` and E7 evidence artifact `12525356981` each returned HTTP 404.

- Archive SHA-256: `ec2d8b7fdccbb2d934eb0543d8f41198307d24ca0aaa0904c83caea6113c5427`.
- Extracted `release_status.json` SHA-256: `89a1721dfb2dc57796a714624246463a4645bbd0c661537b6aa8d39971db2936`.

Monitor execution success is not evidence-chain success.

## Prioritized open-PR stack

### PR #188 — runtime SHA/checkpoint gate
- Head `f2a095f33bdcfd2c521abd1b7b42ded537fe5247`, base main `b8d4a3b015cfcff56201b889702dc0ce7ee83e4f`.
- Exact-head workflow runs refreshed: five returned runs, all succeeded (CI, community analyzer, BioMCP/web validation, tiled inference checkpoint validation, watchdog validation).
- CI [45068485205](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45068485205): **190 passed, 1 skipped, 7 subtests passed**.
- Adds upstream-only watchdog, bounded health retries and main SHA plus immutable checkpoint verification before dispatch. Live Render health contract is not verified. PR remains draft/unmerged.

### PR #187 — PR-upload guard
- Head `47d4bdf0b1fb111ac865d6cb360dcdc95cc929a2`, base main `b8d4a3b015cfcff56201b889702dc0ce7ee83e4f`.
- Exact-head runs refreshed: CI [45045185704](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45045185704) succeeded (**159 passed, 1 skipped**); PR E2E [45045185706](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45045185706) succeeded with public upload skipped. These are PR/runner checks, not public inference.
- Restricts upload to upstream main/non-PR events and adds offline harness validation. PR remains draft/unmerged. Main currently lacks this guard.

### PR #178 — baseline tracker
- Head `1b33a2935b256f6ce29809a4d449be7d72372043`, base `d4a653e94501e8b9f1ec9de09ff71720f90ab340` (stale).
- Exact-head CI [45085683492](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45085683492), job `137403635015`: success, **158 passed, 1 skipped**. Full log fetched.
- This file is additive. PR remains draft/unmerged.

## Evidence tiers

- **Tier A — repository/API/source:** current-main SHA/signature, workflow source, PR metadata/diffs, GitHub API evidence.
- **Tier B — CI/runner:** exact-main CI, PR CI and offline harness, workflow logs and artifact processing. Does not prove public production behavior.
- **Tier C — public E2E:** the scheduled workflow reached public preflight but failed parity before guest/job/upload/inference. No successful public inference.
- **Local artifact parsing:** ZIP integrity and JSON/hash validation only; not scientific inference.

## Milestones and schedule risk

- M0: **incomplete**. Baseline prioritized and refreshed; manual full diff/check/log/artifact audit for all 104 open PRs remains outstanding. Branch-main listing exposes 1,000 of 2,500 API-total records; remaining 1,500 unavailable through this listing.
- M1: **incomplete**. Main public upload job lacks PR/ref guard; watchdog dispatch lacks deployed-SHA/checkpoint gate; runtime parity false. #187/#188 checks are green but unmerged.
- M2: **incomplete**. Target dataset download failed before evaluation; current-main baseline provenance/evaluation not verified.
- M3: **incomplete**. No public upload-to-inference result; latest E2E stopped at preflight.
- M4: **incomplete**. Lifecycle/privacy stack integration and live verification are outstanding.
- M5: **incomplete**. Current-main scientific artifact chain is not ready; monitor blocked by missing E4/E7 artifacts.
- M6: **unverified**. Real external BioMCP interoperability has not been demonstrated.
- M7: **not ready**. All acceptance gates remain open.

Deadline risk: **high** (39 days to 2027-01-01). Runtime parity/security gates, fresh research provenance, public workflow, privacy integration, current-main reproducibility and external interoperability are critical-path blockers.

## Next action

Continue M0 source/PR audit, then integrate M1 guard changes deliberately as one coherent stack after source/check/log/artifact review. Do not merge, deploy, inspect Render, dispatch public E2E, or perform manual public upload without the required authorization. No source-code change or scientific evaluation was made in this run.


## Dataset downloader PR-stack review — 2026-11-23

The exact-main downloader audit found an unbounded ZIP extraction path. Three open PRs provide related, but stacked/separate, fixes. Their exact-head CI jobs and full logs were refreshed; all are runner-only evidence.


### PR #136 — transient download retry

- Head `a85ea1801a58f4146b9540e9e075e0c1f00fd228`, base current main `d4a653e94501e8b9f1ec9de09ff71720f90ab340` (now stale).
- Exact-head CI [43723583459](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43723583459), job `132840586924`: **151 passed, 1 skipped**.
- Retries only transient transport and retryable HTTP failures, writes to temporary files, atomically replaces the prior archive only after successful transfer/CRC validation, and preserves previous destination on failure.

### PR #140 — bounded archive and expansion

- Head `dc42500e447c297682a4f7296833af952b40ee56`, base PR #139 head `1fd0de5f7660148ba1341c6087c1fdcc7c3143d5`.
- Exact-head CI [43727201964](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43727201964), job `132851635754`: **172 passed, 1 skipped**.
- Limits compressed size to 600 MiB, 512 ZIP entries, 64 MiB per member and 768 MiB total expansion; validates canonical paths, duplicates and special member types before CRC scanning/extraction. These are explicit ceilings, not measured archive sizes.

### PR #158 — total download deadline (stacked on #140)

- Head `b00a0558a51bc3daa5ddd42808268d5038c26d7a`, base PR #140 head `dc42500e447c297682a4f7296833af952b40ee56`.
- Exact-head CI [44051271731](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44051271731), job `133929411739`: **176 passed, 1 skipped**.
- Adds a 10-minute monotonic total deadline, 10-second inactivity timeout, bounded `read1(64 KiB)` streaming and a slow-trickle regression test. It inherits #140's archive/expansion checks.


The current-main downloader has none of these changes. #136 is a separate retry-only stack; #140/#158 depend on #139/#140 and overlap the same downloader. Do not merge the stacks independently. Compare and integrate a single coherent version retaining retry/atomic replacement, archive/member limits, path validation, CRC validation and total-time bounds. Exact-head CI success is not a live BioStudies download or evaluation. The current failure's exception is not visible in its artifact/log; the historical #136 evidence identifies a prior `RemoteDisconnected`, but that does not prove the cause of run 45077440306.
