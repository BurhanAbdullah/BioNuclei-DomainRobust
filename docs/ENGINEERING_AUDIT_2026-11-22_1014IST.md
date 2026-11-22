# Engineering audit — 2026-11-22 10:14 IST

This audit refreshes GitHub API evidence for the unchanged current-main commit and selected E2E/watchdog/release-monitor runs. It does not claim deployed-runtime or public-inference proof.

## Main identity and signature

- Main SHA: `d4a653e94501e8b9f1ec9de09ff71720f90ab340`.
- GitHub commit API freshly returned `verification.verified=true`, `reason=valid`; verification timestamp in the commit object is `2026-10-24T07:08:31Z`. The SHA remains unchanged.
- Browser control is unavailable because this session has no originating browser context. No manual upload was attempted. Render was not inspected or deployed.

## Actions pagination refreshed

REST `actions/runs` queries were refreshed with `per_page=100`:

| Query | Populated pages | Returned records | API total |
|---|---:|---:|---:|
| `branch=main` | 1–10: 100 each; page 11 empty | 1,000 | 2,500 |
| `event=schedule` | 1–6: 100 each; page 7: 2 | 602 | 602 |
| `head_sha=<current main>` | 1–4: 100 each; page 5: 98 | 498 | 498 |

The branch-main listing exposes only the first 1,000 records despite the API total of 2,500; the inaccessible 1,500 were not audited. The workflow-specific `/actions/workflows/{filename}/runs` endpoints were rejected by the GitHub connector; run selection used branch/event/SHA queries instead.

The open PR listing returned 98 records. Head/base metadata was refreshed for the selected runtime PRs and #178; full diffs/checks/logs/artifacts for all 98 remain incomplete.

## Exact-current-main E2E and watchdog

Current main SHA is `d4a653e94501e8b9f1ec9de09ff71720f90ab340`.

- **E2E #302**, [run 44972727518](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44972727518), `workflow_dispatch`, exact main; job `137055811890`: failed at preflight. The full 47,160-character log, job steps, and failure artifact were re-fetched.
- **Scheduled E2E #301**, [run 44966699214](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44966699214), exact main; job `137037234591`: failed at the same preflight.
- Both diagnostics: health attempts 1–4 timed out; attempt 5 returned HTTP 200, while the recorded `api_health_request_error` remains `ReadTimeout`. Runtime parity is false. Reported runtime SHA `bb6a9d27537e12b85768c7fead1467253b2423ba` differs from main. Five runtime-diff paths were reported: three script paths plus the genuine shipped mismatches `webapp/community.py` and `webapp/community_app.py`. `checkpoint_available=true` is not digest verification. No guest token, job ID, upload, inference, or cleanup was reached.
- E2E #302 failure artifact ID `14734721065`: ZIP SHA-256 `acc4026852be6922aeb5dc93caa00ab0e196a8c6f9004f26c7c9110ceae2e999`; extracted JSON SHA-256 `2303f89a8945d29947e7fba0efd2c22610ac15f7192936e9cd02a9adda896bdb`.
- E2E #301 failure artifact ID `14731389860`: ZIP SHA-256 `0f41ba3a21b1008d5fd40bc76b654bcda190130768ef3258cc8e465e51f19214`; extracted JSON SHA-256 `7a40410b73868de6466abaddec4ca27d689611ac00fb6e6896f870e0cb050af4`.
- **Watchdog #129**, [run 44972719647](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44972719647), job `137055785175`: success; full 12,691-character log confirms `age_seconds=4521` and dispatch accepted without deployed SHA/checkpoint verification. The watchdog is still automatically dispatching on main.

Both E2E archives were downloaded, ZIP integrity-tested, extracted, and JSON-parsed. Hashes above are freshly calculated in the audit container. No source image was in either artifact.

## Research release monitor

[Release monitor #372](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44969806811), run `44969806811`, job `137046876009`: monitor job succeeded, but the parsed status artifact says `BLOCKED`, `release_ready=false`. Frozen E4 checkpoint artifact `12183110279` lookup returned HTTP 404.

- Artifact #14732719621 ZIP SHA-256: `d24dcdf1d2e6a1ce252d8178f120aa55d58864f892cee4fddf6a851e8427c442`.
- Extracted `release_status.json` SHA-256: `bd8774dda8a6139d7ad5dc91fb4f4bb5d2c915a526b152cc1fa80cac4aaeb1d6`.
- Archive was integrity-tested; JSON parsed successfully.

A successful monitor execution is not a successful evidence-chain verification or release readiness.

## PR refresh and selected runtime integration

### PR #150 — safety pause plus Docker-aware parity classifier

- Exact head: `2a4f94493a33f47d91315c6646365daf3bc89534`; base main: `d4a653e94501e8b9f1ec9de09ff71720f90ab340`.
- Full 5-file patch refreshed. It removes automatic schedule/push E2E triggers; the public-upload job is manual dispatch, upstream-repository and main-ref only. The watchdog loses schedule and dispatch job/Actions-write permission. PR validation remains offline and covers the parity classifier/watchdog.
- CI [44953480644](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953480644), job `136996350200`: 153 passed, 1 skipped, 21 subtests passed.
- E2E PR validation [44953480581](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953480581): harness validation succeeded; public-upload job skipped.
- Watchdog validation [44953480651](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44953480651): succeeded.
- These are PR/runner checks only. Main still has automatic schedule/push/watchdog behavior because #150 is not merged.

### PR #92 — runtime/checkpoint watchdog gate

Exact head `838b89d51cae3db2171bc67b0c2389c043b34122`, base main. Prior exact-head runner checks succeeded (run 43437830689; 165 passed, 1 skipped, 7 subtests passed). This stack preserves automatic dispatch when the deployed SHA/checkpoint are verified, unlike #150's manual pause. Integrate these differences deliberately; do not merge overlapping workflow branches independently.

### PR #103 — authenticated GitHub API checks

Exact head `5372d812304eb3612dc7890e1f03ee9361e5c423`, base main. Prior exact-head CI/offline harness runs succeeded (41231538021 and 41231537964), but evidence is historical and no public upload was run.

### PR #178 — readiness tracker

Exact head before this audit: `d9fa45eedf5fb993eb395552ecfe430331d91bad`, base main. Existing docs were fetched at this head; this audit is additive. Exact-head CI [44982185237](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44982185237), job `137084880562`, succeeded (test job). It validates the previous tracker head, not this new file.

## Evidence tiers and milestone gates

- **Repository/API:** main identity/signature, Actions metadata, PR metadata and exact source/diff reads.
- **CI/runner:** E2E #301/#302 preflight failures, watchdog dispatch, release monitor, PR #150/#92/#103/#178 checks. None is public inference.
- **Local artifact parsing:** ZIP integrity and JSON parsing/hashes only. This is not inference.
- **Public upload/inference:** none. Deployment: not inspected.

M0 remains **partial/not accepted** because full per-PR diff/check/log/artifact review and the 1,500 inaccessible branch-main run records are outstanding. M1 is **not accepted**: main automatically dispatches, runtime parity is false, deployed SHA/checkpoint pin is unverified. M2–M7 are unaccepted.

## Next safe actions and deadline risk

The 2027-01-01 target is **high risk**. The critical path is fail-closed runtime integration, a verified deployment/checkpoint, fresh baseline provenance and current-main scientific reproduction, controlled public upload-to-inference, lifecycle/privacy integration and authorized verification, and external BioMCP execution.

Keep public E2E paused by a reviewed safety integration until exact runtime/checkpoint identity is verified. Do not inspect Render, deploy, manually upload, dispatch public E2E, or merge without the required authorization.


## Fresh checkpoint-integrity PR audit — 2026-11-22

### PR #105 — immutable release digest on health and inference

- Exact head `1d4726b430da933180d2c2744ec564a442c09b96`, base main. Full 11-file patch was refreshed and reviewed, including `webapp/app.py`, both health endpoints, E2E checkpoint gate, and checkpoint tests.
- The release digest is fixed at `7209a6990514380804210292ac208b0f3b0b0a054338a145e1916044762d7c92`; a configured environment digest cannot redefine the source-controlled pin. Inference returns 503 on missing/unverified/mismatched checkpoint, and health reports the observed SHA plus availability/verification state.
- Exact-head workflow runs [43421688067](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43421688067), [43421687985](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43421687985), [43421688000](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43421688000), [43421687953](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43421687953), and [43421687940](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43421687940) all succeeded. The public E2E job was skipped; these are CI/runner validations only.

### PR #146 — sealed checkpoint snapshot (stacked on #105)

- Exact head `7c7f348333ba2cc1fe4bc53e53a0f1e62a9ef433`, base PR #105 head. Full 10-file patch refreshed; the checkpoint context, sealed memfd snapshot, community inference call, tests, and constrained-memory workflow were reviewed.
- Inference copies the opened, verified checkpoint into a memfd snapshot, hashes the snapshot again, applies and checks write/grow/shrink/seal protections, and fails closed if a stable descriptor path cannot be provided. Model loading consumes the snapshot rather than the mutable deployment path.
- Regression tests exercise pathname replacement and same-inode mutation after snapshot creation and assert sealing. The validation workflow builds the production community image, uses a 480 MiB container memory limit, and checks thread-pool defaults.
- Exact-head runs [44900605117](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44900605117), [44900605141](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44900605141), [44900605180](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44900605180), [44900605104](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44900605104), and [44900605055](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44900605055) all succeeded. This is runner evidence; no deployment, Render inspection, or public upload/inference was performed.

### Integration gate

#105 and #146 are a coherent candidate checkpoint-integrity stack, with exact-head checks green. They remain unmerged and unverified on the deployed runtime. M1 still fails its exit criteria until this stack is integrated with the watchdog/runtime-parity changes, exact-main CI is green, automated stale-SHA/unverified-pin dispatch suppression is proven, and live runtime identity is authorized and verified. Do not merge overlapping PRs independently.


## Tracker CI completion — 2026-11-22

- This audit file was re-fetched at exact PR #178 head `d5020341e87bf6e28afd1f13b74fe9ee4158e2fd` before the update.
- New audit commit `d5020341e87bf6e28afd1f13b74fe9ee4158e2fd` was validated by exact-head run [44986731889](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44986731889), job `137098825555`: **145 passed, 1 skipped**. The full 49,805-character job log was fetched. This is documentation-PR CI evidence, not public inference.
- #178 now has four changed documentation files and remains a draft; no merge was performed.


## Fresh main, Actions, and E6 retry audit — 2026-11-22 11:14 IST

### Current main

- SHA: `97e35c1cc73f39fb2855268e441231975ba4bd0b`; GitHub commit verification: `verified=true`, `reason=valid`, verified at `2026-11-22T04:07:50Z`.
- Actions branch-main query: pages 1–10 populated (100 each); page 11 empty and pages 12–25 empty. API reports 2,500 total, but only 1,000 records are accessible through this listing. Scheduled-event query: pages 1–6 populated (100 each), page 7 has 2; total 602. Exact-main SHA query: 35 records on page 1; page 2 empty. Open PR listing: 99 records on page 1; page 2 empty. Full diffs/checks/logs/artifacts for all 99 PRs remain incomplete.
- Current-main CI run `44983675441` succeeded. Zero-shot run `44990767024` remains in progress. Pages deploy run `44983675451` failed after upload; artifact `github-pages` (`14739385465`, 140,058 bytes, digest `sha256:a956ac81ae265b0d4b03977b268ece0d30521d75b478a236830aea317fb7e723`) is present in the run, while deploy-pages reported 0 artifacts. This is consistent with a transient artifact-metadata/API failure; no source/config fix is justified from this log alone, and deployment was not rerun.
- The Pages ZIP was downloaded and integrity-tested: ZIP SHA-256 matches the API digest above; its `artifact.tar` SHA-256 is `ec974edef858e02312fe3543604e634e90ab1e5aa50a13d120121d63958d45da`. Tar parsing found 113 entries. Selected extracted-file SHA-256: `./index.html` `7d7a1b3a38b885ed5dee29f066819a69cf3d19fe8c741ad08b3474604d6b21b8`; `./bionuclei-app.html` `361063dc12628905ef3d2a19a1e77362b4fcc1df0ea8ecbbb5f603c73f8d2523`; `./assets/site.css` `13e273b69f5f6ba539219cc9f301b1831d8dfc9f4e56929cddbe6817f42ec60`. Artifact integrity/build content is verified; deployment is not.

### E6 provenance and stale retry

- PR #179 is merged at main `97e35c1cc73f39fb2855268e441231975ba4bd0b`. Its E6 workflow now resolves and verifies the E4 artifact from the exact source run. No E4 run exists on this SHA; E6 aggregate/finalize/E7/clean-environment runs on this SHA are skipped.
- Artifact SHA-256 pairs (ID; archive; extracted memory-log):
  - `14739111352`: `a787a9d173ae40533cfdfcd5c81e9231c33ec24f210be53788428caf8262b486`; `adf2bf77dca23c842acae4a6dbe24c32b27c2281472dafde6446e58984ba519c`.
  - `14738926166`: `c0f4e2068de4beb1d9a9686b138c6f2f52a260c783b76caaba8a4089e5e88879`; `5844cf530269515a147d121da4136c688c45ad157b4ebf0823487768703b6d86`.
  - `14738632198`: `e22f4b61c2931489b4996643bf26cfa73886feff2e1326978d17f0cd8a874181`; `327a214a870338348fa19e782775390cb8a3bcaecbcea8949f00f83eccf42d63`.
  - `14738343055`: `9ebf93b4afb185e532f4b865d41c1fb43b8d2485ffa305b6192fd2f160a749a0`; `1c7f5fb683a4d3dae2f8ddafce896a0751d3fb5d56977f16a18aec56041790e`.
  - `14738273307`: `d5621dc08f2734de1019ba3df0195c1d44e7cddaa1f53a2edb1e737dc3b348f5`; `e30d31e1045a0a449d1ed8dde9d1bb70320170b74192464278b99c9a465499f9`.
  All five ZIPs passed integrity testing; each contains only `e6_25pct_memory_watch.log` (20 lines, no JSON scientific metrics).
- New PR #181 adds a current-main SHA gate to the retry watchdog and static regression tests. Exact head `823f1f3922980cd91cea11c175d460a492cc88ff`; both exact-head CI runs `44991042845` and `44991006792` succeeded: **156 passed, 1 skipped** each. Supabase Preview skipped. No artifacts. PR is ready for review, not merged.

### Public E2E and safety

- E2E #301/#302 are preflight failures on then-current main `d4a653e94501e8b9f1ec9de09ff71720f90ab340`. Both archives were refreshed, ZIP integrity-tested and JSON-parsed. #301 ZIP/JSON SHA-256: `0f41ba3a21b1008d5fd40bc76b654bcda190130768ef3258cc8e465e51f19214` / `7a40410b73868de6466abaddec4ca27d689611ac00fb6e6896f870e0cb050af4`; #302: `acc4026852be6922aeb5dc93caa00ab0e196a8c6f9004f26c7c9110ceae2e999` / `2303f89a8945d29947e7fba0efd2c22610ac15f7192936e9cd02a9adda896bdb`. Runtime parity false, runtime SHA stale; neither reached guest session/upload/inference.
- Public E2E watchdog #129 on that old SHA accepted dispatch without deployed-SHA/checkpoint verification. PR #150 remains open; its runner checks pass, but public-upload validation is skipped. Main is still not fail-closed.

### Evidence and milestone status

Repository/API, CI/runner, and local artifact parsing are separate evidence tiers; no public inference or deployed-runtime evidence. M0 remains partial (full PR audit incomplete). M1 remains blocked (automatic dispatch, runtime parity false, deployed identity/checkpoint unverified). M2–M7 unaccepted. Render was not inspected, no deploy/public upload/E2E dispatch was initiated, and browser control is unavailable without an originating context. Deadline risk remains high.
