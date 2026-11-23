# Engineering audit — 2026-11-22 15:11 IST

This additive audit refreshes current-main identity, accessible Actions pagination, E2E/watchdog logs and failure artifacts, scientific-run evidence, and one additional PR review. It is repository/runner evidence only; no deployment or public inference is established.

## Main identity

- Main: `97e35c1cc73f39fb2855268e441231975ba4bd0b`
- GitHub commit API: `verified=true`, `reason=valid`, verified at `2026-11-22T04:07:50Z`.
- Main CI run [44992588956](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44992588956), job `137116678746`: **154 passed, 1 skipped**. Full job log and steps refreshed.

## Actions/PR pagination

| Query | Accessible populated pages | Count |
|---|---|---:|
| `branch=main` | 1–10: 100 each; page 11 empty | 1,000 (API total 2,500) |
| `event=schedule` | 1–6: 100 each; page 7: 5 | 605, complete |
| `head_sha=<current main>` | page 1: 51; page 2 empty | 51, complete |
| Open PRs | page 1: 100; page 2 empty | 100 |

The GitHub API/connector exposes only the first 1,000 branch-main run records in this query; pages 11–25 returned zero, despite the reported total 2,500. The remaining 1,500 cannot be audited here. PR metadata is enumerated, but full diff/check/log/artifact reviews are incomplete for 89 PRs (85 untouched, 4 partial).

## Current-main E2E and watchdog

- E2E run [45001551896](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45001551896), job `137143982659`: failed at the real-pipeline stage. Full 49,379-character job log and steps refreshed.
- Failure artifact `14745857325` was downloaded, ZIP integrity tested, extracted and JSON parsed. Archive SHA-256: `17c7b55cdafc77e82502e0b59feaa151dba65a53821809648691e5b9384cfadd`. Extracted JSON SHA-256: `06b3326559733bcf8d21ceb88552668526ae3b10244d981c82cb7f13552beecc`. The artifact contained JSON only, no source image.
- Diagnostic: runtime-tree parity false; Render-reported SHA `bb6a9d27537e12b85768c7fead1467253b2423ba`; main comparison `ahead` with 27 diff paths. Health attempts 1–7 timed out; attempt 8 returned HTTP 200 while the report retained `ReadTimeout`. `checkpoint_available=true` is not digest verification. No guest token or job ID was created; upload, inference, specialist/report and cleanup were not reached.
- Watchdog run [45004997402](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45004997402), job `137154482422`: success; full 12,404-character log and steps fetched. It suppressed dispatch because an exact-main E2E was recent (2,663 seconds). No artifact. Current watchdog only uses workflow freshness/SHA and does not probe deployed health/checkpoint identity.
- Exact-main source blobs: E2E workflow `c903cc0ab7b7695ba5a7d402b7a4f82496d38732`, watchdog workflow `20aef7459b86b464007d19a1025a4492ec34b0fe`, watchdog script `6800946aeb84a1243219e2f85fd67ea0fee6a67b`. E2E workflow still has schedule and main-push triggers, so it can run independently of watchdog gating.

## Scientific runs

- E7 run [44994082617](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44994082617), job `137121239581`: complete log/steps refreshed; hard-coded retained E4 artifact `12183110279` returns 404. Dataset/evaluation/cross-check/evidence steps skipped; no E7 metrics/artifacts.
- E6 run [44994082640](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44994082640): all four fraction jobs (1%, 5%, 10%, 25%) and aggregate evidence completed successfully. Its artifacts were inventoried.
- Aggregate recovery [45001779947](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45001779947), job `137144695977`: success. Artifact `14746132185` (`e6-external-few-shot-recovered-44994082640`) was downloaded, ZIP-tested, extracted and parsed. Archive SHA-256 `c919fe55d4c55cb0be40d82050ecd6de9483d4bb82db24fe1e49c9ac2045186d`; extracted `aggregate_results.json` SHA-256 `238734faa8fc4bff0646ff44be756e31b318e01af03f220b9e09b39633c1ce20`. It records all four fractions verified and the target-leakage guard passed. These are runner research metrics only:
  - 1%: Dice 0.747168, IoU 0.601703, AJI 0.554320, boundary F1 0.194617.
  - 5%: Dice 0.743236, IoU 0.593025, AJI 0.545434, boundary F1 0.206690.
  - 10%: Dice 0.655943, IoU 0.491004, AJI 0.460659, boundary F1 0.162966.
  - 25%: Dice 0.674573, IoU 0.511027, AJI 0.481184, boundary F1 0.161399.
- E6 finalizer [45001779876](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45001779876), job `137144695816`: failure. Full 20,331-character log refreshed. It still queries the hard-coded E4 artifact ID/digest and returns 404 before frozen checkpoint download/finalization. No artifact.
- Exact-main source blob IDs: E7 workflow `f5a9c97e3956749d567c4b5f5ae989d32622ec48`; E6 workflow `eadc9d8a1a8d2e3da887641b72a688b31a528846`; E6 finalizer `e254d957e5b657012988d6f47bdf5a3d541b84df`; aggregate recovery `f3b021b495c8acabddf7feb98f95f26bf658836e`. E6 binds its fractions to an exact E4 source run, but E7 and the finalizer retain the stale hard-coded artifact pin.

## PR #180 — local Lab drag/drop usability

PR [#180](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/180), head `f280159aa18e6e23f5107bc6bcf911d787f8d669`, base main `97e35c1cc73f39fb2855268e441231975ba4bd0b`. Full four-file diff reviewed: adds local TIFF/ND2 drag/drop, clear-selection, live status and styling; it retains local-only preview and the existing manual/automated paths. Regression tests check drop handling, invalid-file message, object-URL revocation and local asset links. Both exact-head test checks [44986148062](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44986148062) and [44986143573](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44986143573) succeeded: **156 passed, 1 skipped** each; full job logs fetched, no artifacts. Supabase Preview skipped. No browser interaction was performed; these are static/CI validations.

## Evidence tier and milestone gates

- **Repository/API/source:** current SHA/signature, workflow source, PR metadata/diff.
- **CI/runner:** main CI, E2E preflight, watchdog and E6/E7 jobs. E6 metric artifact is runner research evidence, not public proof.
- **Local artifact parsing:** ZIP integrity, JSON parsing and hashes only.
- **Public inference/deployment:** none verified. Browser tool attempted, but access requires an originating browser context; no manual upload. Render was not selected/inspected/deployed.

M0 remains partial/not accepted: 89 open PRs still need full audit and 1,500 branch-main run records are inaccessible. M1 remains blocked by automatic E2E triggers, parity false and unverified live SHA/checkpoint. M2 remains blocked by E7 and E6 finalizer artifact 404s. M3–M7 are unaccepted.

Deadline risk is **high** for 2027-01-01. Next safe action: continue M0 review of the next unreviewed PRs; then rebase a coherent M1 safety stack onto current main and validate exact-head CI before requesting merge authorization. No Render access, deployment, public E2E dispatch, or public upload was performed.
