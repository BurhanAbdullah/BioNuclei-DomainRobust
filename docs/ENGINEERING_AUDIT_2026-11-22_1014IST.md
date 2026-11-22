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
