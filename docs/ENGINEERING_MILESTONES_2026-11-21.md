# Engineering Readiness Baseline — 2026-11-21

This is a time-bounded engineering snapshot, not a release declaration. It distinguishes repository/CI evidence from deployed-runtime and public-inference evidence.

## Repository identity

- Repository: [BioNuclei-DomainRobust](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust)
- Main SHA: `d4a653e94501e8b9f1ec9de09ff71720f90ab340`
- Commit signature: GitHub verification `verified=true`, `reason=valid`, verified at `2026-10-24T07:08:31Z`.
- Latest exact-main CI: [run 44786861263 (#2670)](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44786861263), successful; job 136463892312; `145 passed, 1 skipped`.

## Actions inventory (REST snapshots)

- Branch=main: API reports 2,500 total; populated pages 1–10 returned 100 each (1,000 records). Page 11 was empty in the previous pagination check. This is not a complete 2,500-run audit.
- Event=schedule: 594 runs across populated pages 1–6 (100, 100, 100, 100, 100, 94).
- Exact current-main SHA: 486 runs across populated pages 1–5 (100, 100, 100, 100, 86).
- Open PR inventory: 98. Exact PR heads/bases were enumerated, but a complete patch/check/log/artifact audit of all 98 PRs has not been performed.

## Latest public E2E

[Run 293 — 44898963983](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44898963983), exact main SHA, failed in job 136830566742.

- Public website preflight: HTTP 200.
- Health: four ReadTimeout attempts followed by HTTP 200 on attempt 5.
- Current-main commit lookup: HTTP 403. This is the fatal step before public upload/job creation.
- The health failure field retained the earlier `ReadTimeout` after recovery; diagnostic state is stale.
- Render-reported runtime SHA: `bb6a9d27537e12b85768c7fead1467253b2423ba`, not current main.
- No guest token, public job ID, inference, specialist output, cleanup or public report was produced.

Failure artifact #14705266539:
- ZIP SHA-256: `318c672b6c5a8288dc7f7c7969654c456751b33b6aabc323dfef301b80df9ca0`
- Extracted `live-agent-e2e-failure.json` SHA-256: `844375cb30afcf7cbbb55d588d2954f36d25142bdec05bfb001f37481b8c82d2`
- JSON parsed successfully; 1,536 bytes.

## Watchdog

[Run 125 — 44881810319](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44881810319), job 136778517497, succeeded. The complete job log records E2E age 18,987 seconds, then an accepted dispatch of the existing E2E workflow. The current main watchdog source `scripts/public_e2e_schedule_watchdog.py` decides from E2E freshness/SHA and does not verify the deployed Render SHA or checkpoint pin before dispatch. PR #92 proposes the missing fail-closed gate; it is not merged.

## Research release monitor

[Run 369 — 44876700996](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44876700996), job 136762863374, monitor succeeded, but the artifact reports `status=BLOCKED`, `release_ready=false`.

Blocker: frozen E4 checkpoint artifact 12183110279 returned HTTP 404.

- Artifact #14695923885 ZIP SHA-256: `2f801d40a66fff17b6807854d2828e5dffd8f1d7762c56b1be5503264ff7ea71`
- Extracted `release_status.json` SHA-256: `f8f1bc66d809685f28fceedad2d6ccedeccab9cf8cc9b44558bfeb425259b1ec`
- Parsed JSON size: 2,765 bytes.

## Prioritized engineering blockers

### P0 — Runtime/public-E2E safety and progress
1. **GitHub REST 403 in public E2E:** PR #103 adds authenticated read-only GitHub API headers for both main and compare calls, passes `GITHUB_TOKEN` only to GitHub API calls, and keeps public-upload off PRs. Current run 293 reproduces the 403. PR #103 head `5372d812304eb3612dc7890e1f03ee9361e5c423`; historical checks were green (148 passed, 1 skipped) and PR harness passed/public upload skipped. Re-fetch exact checks before relying on them.
2. **Watchdog fail-closed runtime/checkpoint gate:** PR #92. Main watchdog still dispatches based on stale E2E age. Verify and integrate only after exact-head review/checks.
3. **Runtime parity classifier:** PR #150 `ed314fca17ba7a5dd7848c39e8410b27dea46185`. Docker-build-input-aware exclusions must remain strict; real shipped `webapp/community.py` and `webapp/community_app.py` changes remain parity-gated.
4. **Immutable checkpoint health/inference:** PR #105 `1d4726b430da933180d2c2744ec564a442c09b96`. Health and inference must verify the same pinned digest. Do not rely on availability alone.
5. Reconcile sealed-checkpoint validation and memory limits (PR #146/#172) without weakening evidence or the memory gate.

No public E2E should be manually dispatched while the deployed SHA or checkpoint pin is unverified/stale.

### P1 — Scientific provenance/reproducibility

- Reconcile baseline training recipe/epoch/config/checkpoint/dataset manifest and exact-main provenance (PRs #149, #168, #173, and related source-baseline work).
- Reconcile target transfer metrics and unique-label counts with production postprocessing and exact dataset identity (PRs #162, #169, #177).
- Reproduce E6/E7/uncertainty/clean-environment artifacts on current main; old artifacts or missing E4 artifact cannot pass freshness gates.

### P2 — Public workflow, privacy and operations

- Public uint16 upload-to-inference, pinned model, raw-range propagation, eight evidence-bound specialists, browser/report path and source-free ZIP.
- Owner isolation, consent, no-upload-training, retention consistency, truthful errors, expiry-at-access, worker-safe and verified deletion.
- Real external BioMCP execution, not internal mocks.

## Milestone exit criteria

- **M0 baseline:** evidence above is reproducible and prioritized. Exhaustive PR diffs remain a separate audit item.
- **M1 runtime integrity:** not accepted until parity, authenticated API, watchdog SHA/pin gate and immutable checkpoint health are reconciled, exact-head checks are green, and automated tests prove stale/unverified runtime cannot dispatch.
- **M2 scientific correctness:** not accepted until source training provenance, dataset identity, postprocessing/metrics consistency and fresh exact-main evaluation are proven.
- **M3 public workflow:** not accepted; no public upload-to-inference evidence.
- **M4 privacy/operations:** not accepted; full code review plus authorized live verification remains.
- **M5 reproducibility:** not accepted; fresh current-main E6/E7/uncertainty/clean reproduction and release monitor readiness required.
- **M6 BioMCP:** not accepted; real external interoperability unverified.
- **M7 final acceptance:** not ready; all prior gates must pass.

## Evidence tiers

- GitHub source, commit verification, Actions job/logs, parsed workflow artifacts: repository/CI evidence.
- Runner checkpoint-worker artifacts: runner-only; not public inference.
- Public upload-to-inference: **not demonstrated**.

## Deadline risk

The 2027-01-01 target remains high risk. Runtime integrity, scientific provenance, public inference, live privacy/deletion verification, current-main research reproduction, and external BioMCP remain incomplete. No deadline guarantee is made.

## Next safe action

Review PR #103 against the current main and refresh exact-head CI; it directly addresses the newly reproduced HTTP 403. Then reconcile PR #92/#150/#105 as a fail-closed M1 stack. Do not merge without authorization or run public E2E against stale/unverified Render.


## Fresh evidence update — 2026-11-21 18:11 IST

This additive update supersedes only the time-sensitive PR inventory and checkpoint-worker details above; the original dated E2E/release artifact snapshot is retained for traceability.

- Repository commit search still returns main SHA `d4a653e94501e8b9f1ec9de09ff71720f90ab340` as the newest commit. The normalized commit-fetch/search connector does not expose a fresh signature-verification object, so the earlier verified signature result is not re-certified in this update.
- The PR connector returned **99 open PRs** (limit 100); this is a fresh connector inventory, not a complete Actions pagination audit.
- PR #146 head `7c7f348333ba2cc1fe4bc53e53a0f1e62a9ef433`, based on PR #105 head `1d4726b430da933180d2c2744ec564a442c09b96`, now has exact-head CI run [44900605180](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44900605180) successful: **163 passed, 1 skipped**. Tiled checkpoint worker run [44900605055](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44900605055) completed successfully; the log records an enforced 503,316,480-byte cgroup limit and peak 442,347,520 bytes, below the unchanged 492,830,720-byte safety target by 50,483,200 bytes. All eight specialist statuses completed and the result ZIP manifest lists 16 result files. This is GitHub-runner evidence only, not public inference. No artifact was attached to this worker run.
- Main-based PR #172 head `982a04d44c9d23775cc1588e5be8d52814d2d9b5` also has CI run [44649655608](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44649655608) successful (**147 passed, 1 skipped**) and checkpoint worker run [44649655475](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44649655475) successful with peak 436,334,592 bytes under the same 480 MiB limit. Its prior worker run recorded 447,467,520 bytes. These results remain runner-only.
- PR #174 safe initial-checkpoint loading: exact-head CI run [44747521522](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44747521522) successful, **148 passed, 1 skipped**.
- PR #175 weights-only research evaluator loading: exact-head CI run [44814708387](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44814708387) successful, **147 passed, 1 skipped**.
- PR #146's checkpoint-sealing security fix is stacked on #105; #172 is main-based and overlaps the memory-image thread-cap work. These branches need a deliberate additive integration/review sequence; do not merge a dependent branch by itself or force-push.
- Browser control remains unavailable (originating browser context required). The GitHub connector does not expose full Actions run enumeration for branch/schedule/exact-main, and fresh signature verification is unavailable through its normalized commit schema. Therefore those required audits are explicitly outstanding.

**Milestone impact:** checkpoint memory validation on #146 now passes under the strict safety ceiling, but M1 remains incomplete because runtime parity, watchdog dispatch gating, and the #105/#146 integration/deployment identity are not proven. M0 tracker is updated with this evidence; exhaustive PR and Actions inventories remain incomplete.
