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


## Fresh source/runtime audit — 2026-11-21 19:14 IST

This update records evidence retrieved through the GitHub connector. Actions inventory and commit-signature metadata are not fully exposed by the current connector/browser path, so those fields are not re-certified here.

- Current main still resolves to `d4a653e94501e8b9f1ec9de09ff71720f90ab340` in repository-scoped commit search. Commit-fetch normalized output omits signature verification; prior verification remains historical, not fresh.
- Fresh open-PR inventory returned **99** PRs. This is a count snapshot; a complete per-PR patch/check/log/artifact audit remains outstanding.
- The current-main E2E workflow source blob is `c903cc0ab7b7695ba5a7d402b7a4f82496d38732`. It triggers a `pull_request` event for changes to `scripts/live_public_agent_e2e.py`, while its `public-upload-to-agent` job has no main-only job condition. This is a source-level risk: a qualifying PR can invoke the public upload job. PR #103 adds a PR-only offline harness job and conditions the public-upload job on `github.ref == 'refs/heads/main'`; the exact PR head workflow fetched in this audit contains that guard. PR #103 remains unmerged and therefore does not fix main.
- Current-main watchdog workflow blob `20aef7459b86b464007d19a1025a4492ec34b0fe` and script blob `6800946aeb84a1243219e2f85fd67ea0fee6a67b` confirm the main watchdog uses freshness/SHA of E2E runs to decide dispatch and does not query Render health or require deployed SHA/checkpoint pin. PR #92 proposes the fail-closed health/pin gate; it remains unmerged.
- PR #146 exact head `7c7f348333ba2cc1fe4bc53e53a0f1e62a9ef433`, stacked on PR #105 head `1d4726b430da933180d2c2744ec564a442c09b96`, has CI run **44900605180** with **163 passed, 1 skipped**. Worker run **44900605055**, job **136836858514**, succeeded: 480 MiB cgroup hard limit 503,316,480 bytes, peak 442,347,520 bytes (50,483,200 bytes below the 470 MiB safety ceiling); eight specialist statuses completed and the source-free result manifest lists 16 files. No artifact was attached. This is runner-only validation, not public inference.
- PR #146's worker log confirms real checkpoint download/digest verification, community startup verification, specialist execution, production community image build, and constrained-memory worker validation all completed successfully. The result is still not deployed/public proof.

### Milestone interpretation

- M0 has a prioritized baseline, but its strict exit criterion is **not fully satisfied**: complete Actions run pagination and all-PR patch/check/artifact auditing are unavailable through this connector/browser session.
- M1 remains blocked. The current-main public E2E PR-trigger risk, stale Render runtime, missing main health checkpoint identity, and unmerged watchdog/parity/pin stack are unresolved. PR #103 is the concrete safe fix for the PR-trigger risk; PR #92 is the proposed dispatch gate.
- No public E2E was dispatched, no Render workspace/service was inspected, no deployment or merge was performed, and no public inference is claimed.
- Deadline risk remains **high**: roughly 40 calendar days to 2027-01-01, with M0/M1 incomplete and M2–M7 unaccepted.

**Next safe task:** verify PR #103 and #92 exact-head jobs and reconcile the fail-closed stack without merging or dispatching public E2E. Keep the current main PR-trigger risk documented until a safe fix reaches main.


## Fresh Actions pagination and artifact audit — 2026-11-21 20:11 IST

This run refreshed the GitHub REST run inventory and downloaded/parsed the latest E2E and release-monitor failure artifacts. Browser control still requires the originating browser context and is unavailable here.

- Main SHA: `d4a653e94501e8b9f1ec9de09ff71720f90ab340`; commit API returned `verification.verified=true`, reason `valid`, verified at `2026-10-24T07:08:31Z`. The signed commit is still the current main; this is a fresh API verification of that unchanged SHA.
- Branch=main Actions runs: total_count 2,500; pages 1–10 each populated with 100 records; page 11 returned 0 (total 1,000 accessible records). This is an access/pagination ceiling, not a complete inventory.
- Schedule event: total 594; pages 1–5 populated with 100 each and page 6 with 94. Exact current-main SHA: total 487; pages 1–4 populated with 100 each and page 5 with 87; page 6 returned 0. Inventories include full page boundaries and counts, not only filtered workflow names.
- Latest exact-main public E2E #293, run `44898963983`, job `136830566742`, failed at the current-main GitHub commit lookup (HTTP 403). Health returned HTTP 200 on attempt 5 after four ReadTimeouts; the JSON still carries stale `api_health_request_error=ReadTimeout`. Render reports branch main but SHA `bb6a9d27537e12b85768c7fead1467253b2423ba`, behind current main. `guest_token_seen=false`, `job_id_seen=false`, `cleanup_attempted=false`; no upload or inference.
  - Failure artifact #14705266539 downloaded and parsed. ZIP SHA-256 `318c672b6c5a8288dc7f7c7969654c456751b33b6aabc323dfef301b80df9ca0`; extracted JSON (1,536 bytes) SHA-256 `844375cb30afcf7cbbb55d588d2954f36d25142bdec05bfb001f37481b8c82d2`.
- Watchdog #125 run `44881810319`, job `136778517497`, succeeded and dispatched E2E #292 when current-main E2E age was 18,987 seconds. The full 157-line log confirms dispatch acceptance; watchdog artifact list was empty. The #292 E2E failed. PR #92's health/pin pre-dispatch gate remains unmerged; current main does not gate on deployed SHA/checkpoint verification.
- Release monitor #369 run `44876700996`, job `136762863374`, completed as a monitor but reports `BLOCKED`, `release_ready=false`; frozen E4 checkpoint artifact #12183110279 returned HTTP 404. Artifact #14695923885 was downloaded and parsed. ZIP SHA-256 `2f801d40a66fff17b6807854d2828e5dffd8f1d7762c56b1be5503264ff7ea71`; extracted release_status.json (2,765 bytes) SHA-256 `f8f1bc66d809685f28fceedad2d6ccedeccab9cf8cc9b44558bfeb425259b1ec`. The release monitor is not a scientific reproduction run.
- Exact-main CI run #2670 (`44786861263`) job `136463892312`: successful, 145 passed, 1 skipped. This is GitHub-runner test evidence.
- PR #103 head `5372d812304eb3612dc7890e1f03ee9361e5c423`, base main, is still open. Historical exact-head CI #41231538021 was green (148 passed, 1 skipped); E2E PR harness #41231537964 passed while public upload skipped. Its main-only guard is present in the PR branch, absent on main.
- PR #92 head `838b89d51cae3db2171bc67b0c2389c043b34122`, base main, remains open. Historical CI #43437830508 and watchdog-validation run #43437830689 passed; the PR recovery-dispatch job was skipped. Tests are not live Render evidence.
- PR #146 exact head `7c7f348333ba2cc1fe4bc53e53a0f1e62a9ef433` remains stacked on #105 head `1d4726b430da933180d2c2744ec564a442c09b96`; CI #44900605180 passed (163 passed, 1 skipped), worker #44900605055/job #136836858514 passed with 442,347,520-byte peak under 480 MiB. Runner-only.
- PR #178's tracker CI run #44910585294 passed (both tests jobs); it is documentation-only and remains draft/unmerged.

### M0 disposition

Actions pagination has now been reproduced to the accessible boundary for branch=main, schedule, and exact current-main SHA. The baseline is better evidenced, but M0 remains **not accepted** because complete patch/check/log/artifact auditing of all 99 open PRs is still unfinished. Do not move to M1 until that baseline audit and prioritization are complete.

### Next safe task

Continue the M0 open-PR audit in prioritized batches, beginning with PRs that can unblock M1 (#103, #92, #105, #146, parity stack #82/#102 and health contract #144). Keep public E2E blocked; do not inspect/deploy Render without authorization.


## M0 prioritized PR audit batch — 2026-11-21 20:11 IST

Four additional high-priority PRs were reviewed by fetching their full patches, exact head/base metadata, check-runs, and test job logs. Patch excerpts and targeted implementation/tests were inspected; a complete line-by-line review of every patch in the 99-PR inventory is not yet complete.

- **#82** head `5f30a00e5e3910d87ee19420c0293af668d2c531`, base current main. Runtime parity classifier excludes only paths not copied to Render images; unknown paths fail closed. Historical CI #40859980050 green; PR E2E #40659838318 harness passed, public-upload skipped. Test log #123400457669: 149 passed, 1 skipped, 20 subtests.
- **#102** head `d75c94ef1cf88eea2b6149cdb849f7407eecb90`, base #82 head `5f30a00e5e3910d87ee19420c0293af668d2c531`. Adds Docker COPY/ADD source allowlist protection to parity exclusions. Historical CI #41207553946 green; PR E2E #41207553941 harness passed, upload skipped. Test log #124555631353: 150 passed, 1 skipped, 20 subtests.
- **#144** head `b17312ea25c1d8d6219393a78f3cd5b3bdb19f66`, base main. Adds checkpoint-health contract and explicit opt-in for live Render checks. Historical CI #43691513066 green; live Render job skipped. Test log #132742965543: 154 passed, 1 skipped.
- **#105** head `1d4726b430da933180d2c2744ec564a442c09b96`, base main. Immutable checkpoint pin and health verification, main-only E2E guard, health identity tests; historical CI #44517779139 green. Test log #135538172496: 158 passed, 1 skipped. Checkpoint worker #43421687940 succeeded, but is runner evidence only; public E2E and live Render checks were skipped.
- PR #146 remains stacked on #105 and must be integrated in dependency order. #92/#103 have green historical checks but remain unmerged. These are source/test results only; no deployed-runtime verification.
- After the tracker commit `b16f0a5a8eeec164a76ea6dbac401c6462ff7655`, PR #178 CI runs #44915702198 and #44915698560 were observed **in progress**. Earlier run #44910585294 passed on the prior tracker commit; it is not evidence for this new commit.

### M0 remaining

The current evidence prioritizes the runtime safety PR stack, but complete full-patch review and linked-run/artifact review for all 99 open PRs is not finished. M0 exit is still withheld. The next batch should complete full diffs and dependencies for #82/#102/#144/#105, then audit the remaining PR inventory in bounded batches; do not claim the whole baseline is complete.


## M0 configuration-contract audit — 2026-11-21 20:11 IST

A fresh source read of main confirms a configuration/reporting mismatch that must be resolved in the runtime-health integration:
- Main `render.yaml` blob `7386c0f7ef5d562e83583071a89f47b8f7d2b7c7` configures `BIONUCLEI_RESULT_RETENTION_HOURS=24` for the community service.
- Main `webapp/community_app.py` blob `900bc126a139b7bcb2d2b8204d90ff9482ab061f` still says results expire after one hour in `/` and hardcodes `result_retention_hours: 1` in `/health`. Actual Render service settings were not inspected.
- PR #105's checkpoint health contract also hardcodes one hour. PR #141 (head `00318ed4da86e4eaa4d5e4d3262436d83a93053`, base #105) reads `community_service.DEFAULT_RESULT_RETENTION_HOURS` for both root and health, with tests. Its check-runs are green, but live Render is skipped. PR #101 (main-based) independently implements the same configured-retention reporting fix; avoid merging both copies without reconciliation.
- PR #144 is another main-based draft health-contract/live-check opt-in branch; compare it against #105 before integration rather than merging overlapping stacks.
- PR #105 already has a comment documenting the retention mismatch and #146 sealed-checkpoint dependency. The current #146 head is `7c7f348333ba2cc1fe4bc53e53a0f1e62a9ef433`, stacked on #105; its runner validation is green, but neither branch is deployed.

### M0 disposition

The configuration mismatch and the overlapping #101/#141/#144/#105/#146 branches are now prioritized in the baseline. M0 remains incomplete because the 99-PR inventory has not received exhaustive full-patch, exact-head-check, linked-run/log/artifact review. No milestone advancement is authorized by these partial audits.

## M0 prioritized PR audit batch — 2026-11-21 20:39 IST

This batch reviewed the exact PR-head workflow/source/test files for #150, #128, and #98, plus their historical workflow jobs and logs. This is a prioritized audit, not completion of all 99 PRs.

- **PR #150 — Docker-aware runtime parity:** head `ed314fca17ba7a5dd7848c39e8410b27dea46185`, base main. Reviewed all four changed files: the workflow, parity classifier, E2E helper, and regression tests. The classifier excludes `.github/workflows/`, `tests/`, `scripts/`, and docs other than `docs/RESEARCH_PROTOCOL.md`/`docs/DATASETS.md`; unknown root paths fail closed. Tests also check the Docker COPY/ADD allowlist, parity-trigger paths, and main-only public-upload job. Historical CI run [44210719937](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44210719937) passed **152 tests, 1 skipped, 29 subtests**. E2E validation [44210719925](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44210719925) passed the offline harness and skipped public upload. This does not validate the live runtime.
- **PR #128 — live Render opt-in:** head `7a2104df4112015b235df6ed5f178b39e093aec7`, base main. Reviewed workflow and test. Live Render requires manual dispatch on upstream main with `allow_live_render=true`; default is false. CI [43691622736](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43691622736) passed **146 tests, 1 skipped**. Static validation [43691622730](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43691622730) passed the specialist contract (4 tests) and frontend/authentication/analysis/cleanup checks. Live Render job was skipped. No service was queried.
- **PR #98 — authenticated GitHub REST calls:** head `c3a57ef533834ed29197f5839c6a1023f020e7a0`, stacked on #96, not main. Reviewed workflow, helper, preflight, and tests. The helper requires a token and adds Bearer auth only for GitHub REST; Render requests do not receive it. CI [40462787901](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/40462787901) passed **164 tests, 1 skipped**. Harness [E2E harness run 40462787864](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/40462787864) passed YAML/syntax checks; public-upload was skipped. This is historical PR validation. PR #103 is the newer main-based authentication branch; avoid merging duplicate #98/#103 without reconciling the stack.
- **Integration gap:** #150 has the main-only PR safety guard and Docker-aware parity classifier but does not include #103's authenticated GitHub API helper/preflight. #103 has the authentication fix and main-only public-upload guard but does not carry #150's parity classifier. These are competing main-based changes and need one reviewed integration rather than merging both independently. The current main E2E workflow still has an unconditional public-upload job (no event/ref condition) while its PR trigger includes `scripts/live_public_agent_e2e.py`; a qualifying PR can therefore reach the public job on main's workflow definition. This risk is evidenced by the exact main workflow source, not by public execution.
- **PR #178 tracker validation:** current tracker head `874a25e37d0a384a74b13eb581d1643a9afe9a97`; CI [44915954649](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44915954649) succeeded, **145 passed, 1 skipped**. Documentation-only, draft, unmerged.
- **Fresh-access limitations:** repository metadata and commit search returned the unchanged main SHA `d4a653e94501e8b9f1ec9de09ff71720f90ab340`. The normalized commit fetch does not expose signature-verification metadata; prior verification is not re-certified. Browser list-tabs failed because the originating context is missing. This connector exposes no Actions run-list pagination API, so branch/schedule/exact-main run inventories could not be refreshed. The #293 E2E, #125 watchdog, and #369 release monitor job logs and artifact metadata were fetched again; failure/release artifact ZIPs were not downloaded and re-extracted in this batch, so their earlier hashes remain historical.
- No source changes, merge, deployment, Render inspection, public E2E dispatch, or upload were performed.

### M0 disposition after this batch

The audit advances prioritized PR review, but **M0 remains incomplete**. The full 99-PR patch/check/log/artifact audit, complete Actions pagination, and fresh signature verification are not available. Continue with the next high-priority batch; do not advance to M1.

### Next safe task

Reconcile #150/#103 as a single main-based runtime-parity + authenticated-preflight change, review #92/#105 gating dependencies, and continue PR audit batches. Keep public E2E blocked while deployed SHA/checkpoint identity is unverified.

## M0 prioritized runtime gate and checkpoint audit — 2026-11-21 20:39 IST

This batch inspected exact source and tests for PRs #92 and #105, retrieved their historical CI/workflow jobs and logs, and checked artifact listings. No artifacts were attached to the reviewed runs.

- **PR #92 watchdog fail-closed gate:** head `838b89d51cae3db2171bc67b0c2389c043b34122`, base main. Reviewed the watchdog script, tests, and workflow. It requires upstream repository identity, GitHub server time, Render health status `ok`, main branch, a verified checkpoint, and the expected checkpoint digest before dispatch. The main SHA is compared against the health-reported deployed SHA; unverified or stale runtime suppresses dispatch. Health retries are bounded. Historical CI [43437830508](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43437830508) passed **165 tests, 1 skipped, 7 subtests**. Watchdog validation [43437830689](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43437830689) passed the decision tests/compile/YAML steps; the recovery-dispatch job was skipped. Runner tests only.
- **PR #105 immutable checkpoint pin:** head `1d4726b430da933180d2c2744ec564a442c09b96`, base main. Reviewed `webapp/app.py`, `webapp/community_app.py`, and checkpoint integrity tests. Both health endpoints expose availability, observed SHA-256, and verification; inference rejects mismatches. Cache identity includes device/inode/size/mtime/ctime and verifies descriptor/path metadata before accepting the cached digest. Exact-head CI [43421687985](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43421687985) passed **158 tests, 1 skipped**. Checkpoint worker [43421687940](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43421687940) completed all stages twice under a 480 MiB hard limit; observed peaks were **463,335,424** and **455,524,352 bytes**. It verified the pinned checkpoint before/after, uint16 range and eight evidence-bound specialist statuses. This is GitHub-runner validation only. No worker artifact was attached.
- PR #105's separate MCP/web validation [43421688067](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43421688067) passed the MCP server construction and web adapter/route checks. This is internal CI, not external BioMCP interoperability.
- **Integration limitations:** #92 gates scheduled watchdog dispatch only; it does not protect direct manual dispatch of the public E2E workflow. #105 adds checkpoint health/pin and E2E runtime guard, but its mutable-path verification alone does not close a write-after-check race during model loading. PR #146's sealed snapshot is the follow-up; it is stacked on #105. Integrate #92/#105/#146 only with a reviewed dependency sequence, and include #150's main-only public-upload gate and #103's authenticated API helper. Do not run public E2E until deployed SHA/pin are proven.
- **Artifact audit:** the PR #92 CI/watchdog runs and PR #105 CI/worker runs returned empty artifact lists. No artifact download or extraction was necessary for these runs.

### M0 disposition

This batch adds concrete dependency/security review to the prioritized baseline, but M0 is **still incomplete**: the full patch/check/log/artifact audit for all 99 open PRs, complete Actions pagination, and fresh commit signature verification remain unavailable through this tool set. No milestone advancement.

### Next safe task

Continue M0 in the next batch with the parity/checkpoint branch dependencies and research provenance PRs (#149/#169/#173/#177), focusing on stale stacked bases and exact baseline/checkpoint identity. Avoid merging duplicates or advancing M1 before the baseline exit criteria are met.

## M0 research-provenance PR audit — 2026-11-21 20:39 IST

This batch reviewed exact-head workflow/script/test changes and historical CI logs for PRs #149, #169, #173, #177, and #176. The scientific runs/artifacts are not fresh current-main reproduction evidence.

- **#149 baseline provenance validator** — head `2757687746e96ddb283c062379399edbcbe1a203`, base main. Reviewed `scripts/validate_bbbc039_baseline.py`, `scripts/evaluate_s_biad634.py`, workflow, and tests. The validator checks repository/workflow/run identity, main branch, success/event, baseline SHA, GitHub compare ancestry/merge-base/head, non-truncated commit/file lists, changed training-input paths (unknown paths fail closed), and exact non-expired baseline artifact identity/digest. Historical CI [43743535495](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43743535495) passed **160 tests, 1 skipped**.
- **#169 exact-main baseline/checkpoint recipe** — head `6183cf907381880204e94640e2fb4db989cf07e7`, base main. Reviewed baseline and zero-shot workflow, checkpoint verifier, and training-recipe tests. The baseline workflow is main-triggered and uses 100 epochs by default; checkpoint metadata must match committed config/seed/epoch recipe. Zero-shot selection requires the exact current-main run and checkout and verifies the recipe with weights-only checkpoint loading. Historical CI [44664121649](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44664121649) passed **152 tests, 1 skipped**.
- **#173 E5 training provenance** — head `5819fe1cda8b63327099b32450502f60cf049678`, base main. Reviewed `e5_run_ablation.py`, `train_domain_robust.py`, E5 workflow, preregistration and tests. Each variant hashes source split/acquisition, target manifest, config, checkpoint, method record and metrics; checks target data is not used for training, 79 target metrics, fixed seed/epochs, and cross-variant source/target/training identity. Source/target acquisition canonicalization removes download timestamps only. Historical CI [44822792979](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44822792979) passed **155 tests, 1 skipped**.
- **#177 S-BIAD634 target provenance** — head `b7f5c347ca056fdae397e851f2de116de696b520`, stacked on #169 head `6183cf907381880204e94640e2fb4db989cf07e7`. Reviewed workflow and test. It binds target dataset identity, download manifest/archive digest, file inventory, 79-image metrics, evaluator/instance-metrics scripts, baseline config/verifier, and asserts the provenance binding happens after evaluation and before artifact upload. Historical CI [44832437317](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44832437317) passed **153 tests, 1 skipped**.
- **#176 E5 test-helper follow-up** — head `989dba4488f58debc5d9f6c8844769387e475680`, based on `b7cd8867a42479d6617bd0b5358c831345dd2aaf`, not the current #173 head `5819fe1cda8b63327099b32450502f60cf049678`. Historical CI [44795654485](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44795654485) passed **155 tests, 1 skipped**; however, the stale stacked base must be reconciled before relying on it as the final integrated revision.
- **Dependency/duplication finding:** #149 and #169 both modify the zero-shot workflow but provide different complementary baseline-integrity mechanisms; #177 is stacked on #169. #173 is a main-based training-provenance branch; #176 is stale relative to its parent. Reconcile these in one clean integration and rerun CI instead of merging overlapping PRs independently. No scientific result was re-created here.

### M0 disposition

This source/CI batch improves the prioritized baseline, but M0 is **not accepted**. All 99 PRs have not been fully audited; complete Actions pagination and fresh signature verification are unavailable. Exact-main research artifacts have not been freshly generated.

### Tracker-head verification

The tracker branch now points to commit `7f51531486696d76219b49e1a58d73085eb394e6`. The connector returned no PR-associated workflow run for this new commit and no legacy commit status. The earlier green tracker CI [44915954649](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44915954649) was on prior head `874a25e37d0a384a74b13eb581d1643a9afe9a97`, not this updated head. The new tracker commit therefore has **no verified exact-head CI result**.

### Next safe action

Continue M0 by auditing the remaining open-PR inventory and reconciling the overlapping research-provenance stacks. Keep M1 changes and public E2E blocked until M0 is complete and runtime SHA/checkpoint pin are independently verified.

## M0 checkpoint-worker and failure-artifact audit — 2026-11-21 20:39 IST

This batch reviewed exact-head PR files and CI logs for #171, #170, #168, #167, and #165, then downloaded, unpacked, parsed, and hashed the latest E2E failure and release-status artifacts.

- **PR #171 full uint16 worker guard:** head `63e697137a0e61d1427cfe52f61433a41f664f6e`, base main. The validator checks uint16 dtype, 512×512 fixture, raw min 512, max 65535, dynamic range 65023, saturated nuclear intensity, all eight completed specialists, job/input identity and evidence digests, plus quantitative claims from the intensity specialist. CI [44627587406](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44627587406) passed **146 tests, 1 skipped**; specialist-contract validation [44627587583](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44627587583) passed 4 tests; live Render was skipped. Checkpoint-worker run [44627587381](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44627587381) failed the constrained-memory gate: limit **503,316,480 bytes (480 MiB)**, peak **503,316,480 bytes**, above the **492,830,720-byte (470 MiB)** safety ceiling. The real checkpoint and eight-specialist stages passed before the memory gate. No artifact was attached. PR #172 and #146 have subsequent runner-only memory-gate fixes; this failure must remain recorded, not overwritten.
- **PR #170 retention reporting:** head `7a7e0e58ae88c690971b429ad0323871af925f71`, stacked on #105 head `1d4726b430da933180d2c2744ec564a442c09b96`. Root/health report configured retention hours. CI [44517890895](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44517890895) passed **160 tests, 1 skipped**; community/MCP/web contract checks [44517890858](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44517890858) and [44517890932](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44517890932) succeeded, live Render skipped. Worker [44517890949](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44517890949) succeeded twice; peaks **453,238,784** and **442,748,928 bytes** under the 480 MiB cap. Runner-only; no artifact.
- **PR #168 baseline epochs:** head `1ce0b31d0b227169abab6851bf4aa53a32529495`, base main. Workflow default changed to 100 epochs to match config; CI [44264892049](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44264892049) passed **146 tests, 1 skipped**. This overlaps #169; do not merge both independently.
- **PR #167 checkpoint recipe verifier:** head `430fb3fa8d8dc48fec4f78f6923238e5831103fd`, stacked on #162. Reviewed weights-only checkpoint metadata verification and the E2E baseline check. CI [44226925512](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44226925512) passed **182 tests, 1 skipped**. It overlaps #169's verifier and #149's baseline provenance validator; reconcile rather than merge duplicates.
- **PR #165 E5 release safe loading:** head `2cd2c19878cdec12aac96d75fbac18800f440857`, base main. E5 release asset loader uses `weights_only=True` instead of unsafe unrestricted pickle. CI [44068204912](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44068204912) passed **146 tests, 1 skipped**. This is CI evidence, not a scientific E5 run.

#### Fresh artifact verification

**E2E #293 — run 44898963983, main SHA d4a653e94501e8b9f1ec9de09ff71720f90ab340.** Artifact 14705266539 (700 bytes) was downloaded and ZIP contents inspected. ZIP SHA-256 **318c672b6c5a8288dc7f7c7969654c456751b33b6aabc323dfef301b80df9ca0** matches the GitHub artifact metadata. Extracted `live-agent-e2e-failure.json` (1,536 bytes) SHA-256 **844375cb30afcf7cbbb55d588d2954f36d25142bdec05bfb001f37481b8c82d2**. Parsed fields: site HTTP 200; health attempts 1–4 timed out at ~10s, attempt 5 returned HTTP 200; stale `api_health_request_error=ReadTimeout` remained; current-main GitHub API check returned 403; Render SHA was `bb6a9d27537e12b85768c7fead1467253b2423ba`, behind current main. `guest_token_seen=false`, `job_id_seen=false`, cleanup was not attempted/verified. Therefore no public upload, job, inference, specialist outputs, or cleanup.
  
**Release monitor #369 — run 44876700996.** Artifact 14695923885 (1,199 bytes) ZIP SHA-256 **2f801d40a66fff17b6807854d2828e5dffd8f1d7762c56b1be5503264ff7ea71** matches metadata. Extracted `release_status.json` (2,765 bytes) SHA-256 **f8f1bc66d809685f28fceedad2d6ccedeccab9cf8cc9b44558bfeb425259b1ec**. Parsed status `BLOCKED`, `release_ready=false`, monitor `healthy`; blocker: frozen E4 checkpoint artifact **12183110279** lookup returned HTTP 404. E6/E7/uncertainty artifacts are still referenced by the monitor, but their provenance is on old run SHAs; this is not fresh exact-main reproduction.

The artifacts were extracted and parsed in the working container; no image or secret data was present.

### M0 status

This is an additional evidence batch, not M0 completion. Fresh main SHA from repository metadata/commit search remains `d4a653e94501e8b9f1ec9de09ff71720f90ab340`. Commit verification metadata and complete Actions run-list pagination are unavailable; `fetch_commit_workflow_runs` returns no runs for main in this connector. The tracker head at the start of this batch was `3fefe674a724bae775712e9655e56d5624b30579`; no exact-head workflow run or legacy status was returned for that commit. The new documentation commit is also unvalidated by CI unless a run is later found.

### Next safe action

Continue M0 PR inventory review and stack reconciliation. Keep public E2E disabled until deployed main SHA and checkpoint pin are verified; do not inspect Render or deploy without authorization. The deadline remains high risk.

## M0 memory gate and artifact identity follow-up — 2026-11-21 20:39 IST

- **#171 uint16 validator failure confirmed:** the exact workflow step ran the pinned checkpoint and all eight specialist checks successfully, then failed the 470 MiB safety ceiling. CI and the specialist contract remained green; the failed memory-gate run had no artifact.
- **#172/#146 memory remediation evidence:** historical #172 worker run `44649655475` and #146 worker `44900605055` are green under runner constraints. #172 is main-based; #146 is stacked on #105 and includes the sealed checkpoint snapshot. #146's peak was **442,347,520 bytes**; #172's successful peak was **436,334,592 bytes** (runner-only). #146 CI [44900605180](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44900605180) passed 163 tests, 1 skipped. These are not deployed-runtime results.
- #170, #168, #167, and #165 CI logs were re-read; counts remain **160+1 skipped**, **146+1 skipped**, **182+1 skipped**, and **146+1 skipped**, respectively. No artifacts were attached to the #171/#170 workers.
- **Artifact integrity rechecked locally:** failure ZIP 14705266539 SHA-256 `318c672b6c5a8288dc7f7c7969654c456751b33b6aabc323dfef301b80df9ca0`; extracted JSON SHA-256 `844375cb30afcf7cbbb55d588d2954f36d25142bdec05bfb001f37481b8c82d2`. Release-status ZIP 14695923885 SHA-256 `2f801d40a66fff17b6807854d2828e5dffd8f1d7762c56b1be5503264ff7ea71`; extracted status SHA-256 `f8f1bc66d809685f28fceedad2d6ccedeccab9cf8cc9b44558bfeb425259b1ec`. Both ZIP hashes match GitHub artifact metadata; JSON parses. E2E #293 still has no guest token/job ID, and release status remains blocked by the missing E4 artifact.

The earlier “Tracker-head verification” section records the 7f515 commit at the time it was written; the subsequent provenance audit pushed 3fefe and this current batch started at 268cf. Neither 3fefe nor 268cf had a verified PR run/legacy status when checked. This historical note is not a claim that the tracker is currently CI-green.

### M0 status / next action

M0 remains incomplete. The next batch should reconcile the runtime/parity/checkpoint branches (#103/#105/#146/#150/#172) without merging, and continue the remaining open-PR audit. Exact-main Actions pagination and signature verification remain blocked by connector capability. Public E2E stays blocked pending independent Render authorization and runtime/checkpoint verification.

