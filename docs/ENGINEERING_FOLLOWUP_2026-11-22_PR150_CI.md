

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
- #178 current head `582175007aefdf24c5460770f650858d3aecef40`: two exact-head test checks 44968273192 and 44968267964 passed; Supabase preview skipped. Documentation CI is green for this head.

The PR stack is not integrated or proven together. #150's manual-only pause and #92's identity gate conflict in workflow behavior and need an additive, reviewed reconciliation; do not merge the identity-gated watchdog alone while main still dispatches against a stale runtime.

### Gate/risk

M0 remains partial: complete accessible Actions pagination and PR metadata are refreshed, but full diffs/checks/logs/artifacts for all 99 PRs are not audited. M1 remains unaccepted: main's watchdog still dispatches without verified runtime/checkpoint and deployed parity is false. M2–M7 remain unaccepted. Deadline risk for 2027-01-01 remains high.

Next: continue the M0 source/diff audit, prioritize a single additive M1 integration branch after exact source rereads, and keep public E2E dispatch paused only after authorization to merge the safety change. No Render inspection, deploy, upload, or inference was performed.
