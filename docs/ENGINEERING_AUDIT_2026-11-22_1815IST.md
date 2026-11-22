# Engineering audit — 2026-11-22 18:15 IST

This refresh records repository, CI, runner-artifact, and public E2E evidence. It does not establish a deployed release or public inference.

## Main identity and CI

- Main: `97e35c1cc73f39fb2855268e441231975ba4bd0b`.
- GitHub commit verification: `verified=true`, `reason=valid`, timestamp `2026-11-22T04:07:50Z`.
- Exact-main CI run [44983675441 (#2841)](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44983675441), job [137089463110](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44983675441/job/137089463110): success, **154 passed, 1 skipped**.
- `main` is currently unprotected (`protected=false`; required checks not enforced). This is a repository-governance risk; branch-protection changes were not made.
- Open PR inventory: 100 returned on page 1, page 2 empty. Head/base metadata refreshed. Full diff/check/log/artifact review of every PR is not complete.

## Actions pagination

| Query | Fresh results |
|---|---|
| `branch=main` | API total 2,500; pages 1–10 returned 100 each. Pages 11, 12 and 25 returned empty. The connector exposes only the first 1,000 records; the remaining 1,500 cannot be audited through this path. |
| `event=schedule` | 605 total: pages 1–6 returned 100 each, page 7 returned 5; complete. |
| Current main SHA filtered from accessible `branch=main` pages | 48 runs found on the current SHA; the head-SHA query endpoint did not return usable records. |

## Public E2E run 303 — blocked before upload

[Run 45001551896](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45001551896), job [137143982659](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45001551896/job/137143982659), exact main SHA: **failure**.

- Published site preflight returned HTTP 200 and the UI pointed to the expected API.
- Render-reported commit: `bb6a9d27537e12b85768c7fead1467253b2423ba`; current main is `97e35c1cc73f39fb2855268e441231975ba4bd0b`.
- Main-to-Render comparison returned 28 changed files. Current-main parity classifier incorrectly treated 9 `scripts/` files as runtime, but the two actual shipped mismatches remain `webapp/community.py` and `webapp/community_app.py`. The exact Dockerfiles copy `src/`, `webapp/`, `configs/`, and the two research docs, not `scripts/`.
- Health retries 1–7 timed out; attempt 8 returned HTTP 200. The JSON retained the earlier `ReadTimeout` field despite recovery. `checkpoint_available=true` is not digest verification.
- No guest token or job ID was created; public upload, inference, specialists, report/export and cleanup were not reached.
- Artifact #14745857325 was downloaded, ZIP-tested and parsed. It contains JSON only (no source image). ZIP SHA-256: `17c7b55cdafc77e82502e0b59feaa151dba65a53821809648691e5b9384cfadd`. Extracted `live-agent-e2e-failure.json` SHA-256: `06b3326559733bcf8d21ceb88552668526ae3b10244d981c82cb7f13552beecc`.

## Watchdog and release monitor

- [Watchdog run 45004997402 (#130)](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45004997402), job 137154482422: success. It suppressed dispatch because current-main E2E was recent (2,663 seconds). No artifact. Main watchdog still checks run freshness/SHA only; it does not gate on live runtime SHA or verified checkpoint.
- [Release monitor run 45000867363 (#373)](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45000867363), job 137141871612: monitor job succeeded, but `release_status.json` reports `status=BLOCKED`, `release_ready=false`; the frozen E4 artifact 12183110279 returned HTTP 404.
- Release artifact #14744889814 was downloaded, ZIP-tested and parsed. ZIP SHA-256: `fc353110ebf5fd3064dc7efb73d93ce87d7ffc9edb8275369b1b7889866616b6`. Extracted `release_status.json` SHA-256: `54d34ae84465a3ed4e34ff840d8865287f91690b9c3249182310f207c0985d3e`.

## Research runs (runner-only evidence)

- E6 source run [44994082640 (#64)](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44994082640) succeeded; aggregate recovery [45001779947 (#155)](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45001779947) succeeded. Artifact #14746132185 was downloaded and parsed: all four fractions verified and target-leakage guard passed. ZIP SHA-256: `c919fe55d4c55cb0be40d82050ecd6de9483d4bb82db24fe1e49c9ac2045186d`; extracted JSON SHA-256: `238734faa8fc4bff0646ff44be756e31b318e01af03f220b9e09b39633c1ce20`.
- Runner aggregate means (not public inference): 1% Dice/IoU/AJI/boundary-F1 = 0.7472/0.6017/0.5543/0.1946; 5% = 0.7432/0.5930/0.5454/0.2067; 10% = 0.6559/0.4910/0.4607/0.1630; 25% = 0.6746/0.5110/0.4812/0.1614.
- E6 finalizer [45001779876 (#21)](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45001779876) failed at frozen E4 identity (artifact 12183110279 404); download/finalization steps were skipped and no artifact was produced.
- E7 [44994082617 (#331)](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44994082617) failed at the same retained E4 artifact identity; dataset/evaluator/evidence steps were skipped and no artifact was produced.
- These are GitHub-runner research results only; no external/public inference is claimed.

## Focused M1 PR review (metadata, full patch payloads and CI refreshed)

| PR | Head SHA | Base SHA | CI / validation | Review outcome |
|---|---|---|---|
| [#103](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/103) | `5372d812304eb3612dc7890e1f03ee9361e5c423` | `d4a653e94501e8b9f1ec9de09ff71720f90ab340` | 148 passed, 1 skipped; offline E2E harness passed; public upload skipped | Adds authenticated GitHub API requests and PR-only harness, but is not current-main and its main-ref condition alone is not a fork guard. |
| [#104](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/104) | `0b1e474db9b5175cfb4fbd2e01863f1c3e14ee5c` | PR #103 head `5372d812304eb3612dc7890e1f03ee9361e5c423` | 185 passed, 1 skipped, 20 subtests passed; offline E2E validation passed; public upload skipped | Adds early exact-SHA/runtime/checkpoint preflight, retries, and Docker-aware parity classifier; upstream-repository/main guard present. Stacked and stale from current main. |
| [#105](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/105) | `1d4726b430da933180d2c2744ec564a442c09b96` | `d4a653e94501e8b9f1ec9de09ff71720f90ab340` | 158 passed, 1 skipped; Community contract 4 passed; tiled real-checkpoint worker succeeded; live Render/E2E skipped | Adds immutable checkpoint verification in health/inference. Runner worker twice passed 480 MiB cap (peaks 463,335,424 and 455,524,352 bytes); runner-only. Stale main base. |
| [#82](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/82) | `5f30a00e5e3910d87ee19420c0293af668d2c531` | `d4a653e94501e8b9f1ec9de09ff71720f90ab340` | 149 passed, 1 skipped, 20 subtests passed; offline harness passed | Older parity-classifier work; mergeable=false and stale. #104 overlaps/supersedes its classifier. |
| [#92](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/92) | `838b89d51cae3db2171bc67b0c2389c043b34122` | `d4a653e94501e8b9f1ec9de09ff71720f90ab340` | 165 passed, 1 skipped, 7 subtests passed; watchdog tests passed; dispatch job skipped on PR | Adds upstream guard, server-time freshness, bounded health retry, exact Render SHA and checkpoint-pin gating. Stale base; not on main. |
| [#181](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/181) | `823f1f3922980cd91cea11c175d460a492cc88ff` | Current main `97e35c1cc73f39fb2855268e441231975ba4bd0b` | 156 passed, 1 skipped (push and PR checks green) | Correctly limits E6 25% retry to failed, bounded-attempt, main-branch, exact-current-main runs. Small and current-base; not merged. |
| [#178](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/178) | `0953c5ecc41f3684e330ede22cc0005eecfd4e4f` | `d4a653e94501e8b9f1ec9de09ff71720f90ab340` | 145 passed, 1 skipped | Baseline documentation PR; draft and stale base. This audit is added to its branch. |

No artifacts were returned for the listed PR CI/harness checks. Full line-by-line review of every open PR remains incomplete.

## Pages deployment

[Pages run 44983675451 (#701)](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44983675451) on exact main: file validation, setup and artifact upload succeeded; deployment failed in `actions/deploy-pages@v4` with artifact-metadata lookup error (`error_count=10`, "No artifacts named github-pages were found"). The published page still returned HTTP 200 in E2E preflight. No deployment retry was attempted.

## Evidence tiers, milestones and deadline

- Source/commit/API, workflow logs and parsed artifacts: repository/CI evidence.
- Checkpoint worker and E6 metrics: runner-only evidence; never public inference.
- Public upload-to-inference: **not demonstrated**.
- M0 baseline is reproducible for accessible evidence, but still partial because the full 2,500-run and all-PR diff audits are inaccessible/incomplete.
- M1 remains **blocked**: runtime is stale; main E2E still lacks an upstream-only public-upload guard and checkpoint-digest gate; watchdog dispatch gate and runtime classifier/pin changes are not merged. Exact-current-main CI is green but does not prove deployment parity.
- M2 remains blocked by the missing frozen E4 artifact, so E6 finalization and E7 evidence are not fresh/complete. M3–M7 remain unaccepted.
- Deadline risk for 2027-01-01: **high** (about 40 days remain). No guarantee is made.

## Next safe action

Reconcile #103/#104/#105/#92 into one reviewed, current-main-based M1 integration sequence, run the exact-head tests, and verify the deployment/checkpoint gate before any authorized public E2E. Do not create a duplicate PR or merge without authorization. Render workspace access, deployment retry, and interactive public upload remain outside this run.
