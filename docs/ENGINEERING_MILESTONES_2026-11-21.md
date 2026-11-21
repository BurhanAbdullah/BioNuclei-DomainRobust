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

## M0 upload, postprocessing, and readiness-deadline audit — 2026-11-21 20:39 IST

- **#160 upload/memory optimization:** head `a99fa75820e854363fe42eb7bad439dc4599e1a1`, base main (27 commits ahead). Reviewed adaptive image profiling, inference normalization, thread/lock memory controls, and tests. CI [43944175091](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43944175091) passed **154 tests, 1 skipped**; analyzer/MCP/web/cleanup validations passed. Real checkpoint worker [43944175257](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43944175257) passed under 480 MiB; peak **281,657,344 bytes**, with eight specialists. No artifact attached.
- **#161 bounded streaming upload:** head `0cbf1d115131c92919f6677f474e89a789b3ce47`, stacked on #160. Reviewed upload route/service: passes the spooled file handle, copies in 1 MiB chunks, enforces upload-size limits during copy, hashes without whole-file `read_bytes()`, rejects oversized streams, and removes partial job state. CI [43991350039](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43991350039) passed **159 tests, 1 skipped**; validation [43991350142](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43991350142) passed. No worker artifact. The PR is draft and must be integrated with #160 rather than independently.
- **#162 shared postprocessing:** head `9a43ef504135b81da7526350769266a5428827d7`, base `ea904133e7fbe8923bbedb3ec64987202655a2f` (19 commits ahead of main). Reviewed the boundary-aware semantic-to-instance splitter and evaluator/inference alignment. Four-connectivity is used for foreground components and interior markers; watershed allocates boundary pixels, with a fallback for boundary-only components. CI [44153721127](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44153721127) passed **180 tests, 1 skipped**. Real checkpoint validation [44153721154](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44153721154) passed; peak **280,424,448 bytes** under the 480 MiB cap, with eight specialist evidence stages. No artifact. The branch is stacked on an older baseline and needs reconciliation.
- **#163 total health-probe deadline:** head `423a29c42dbd0d2a6bd285c7cb203a495644b0f5`, base `9f30e9cdd267fa567a51356e2a2327d2d90bd622` (16 commits ahead of main). Reviewed health-probe code and tests. It uses a monotonic overall budget, bounded streamed reads, a 64 KiB response limit, and fails closed if socket timeout control is absent/rejected. CI [44097200020](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44097200020) passed **160 tests, 1 skipped**; PR E2E [44097202532](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44097202532) passed the harness (**15 tests**) and skipped public upload. No artifact. PR is draft; harness is not public proof.
- **Stack reconciliation:** #161 depends on #160; #162 is based on a 19-commit stack; #163 is based on a 16-commit stack. These branches overlap the current runtime/parity/postprocessing work. Keep the stacks intact until a fresh integration branch can be tested end-to-end; do not merge them piecemeal.
- The PR #178 CI run **44918465097** subsequently completed successfully on prior tracker head `af4dab4cc7337bbb59163f54dc6db1f4ca233c8a`: **145 passed, 1 skipped**. It did not validate later tracker head `0665f9234967205254ebe948318c073029aeb505`; no current-head CI result is claimed for the next documentation commit.

### M0 disposition

M0 remains incomplete. This batch added prioritized source and runner evidence but did not audit all 99 open PRs, enumerate all Actions pages, or freshly verify the main commit signature. Public runtime is still stale/unverified; E2E must remain blocked.

## M0 tracker CI completion note — 2026-11-21

The completion note above was added after run 44918465097 finished. Its successful test result applies to commit `af4dab4cc7337bbb59163f54dc6db1f4ca233c8a`, not the current tracker commit created by this note. The connector still does not expose Actions check-run listing for this current head.

## Fresh Actions pagination and exact-main runtime audit — 2026-11-21 22:16 IST

This update refreshes the accessible GitHub Actions pagination and latest exact-main runtime evidence. No Render workspace/service was inspected and no public E2E was manually dispatched.

### Main identity and signature

- Main SHA: `d4a653e94501e8b9f1ec9de09ff71720f90ab340`.
- GitHub REST commit object was freshly fetched. Signature verification: `verified=true`, `reason=valid`, verified at `2026-10-24T07:08:31Z`. This signed commit is unchanged.
- Open PR inventory: **99**, refreshed from `GET /pulls?state=open&per_page=100&page=1`; exact head/base metadata returned for all 99. Full patch/check/log/artifact review of every PR remains incomplete.

### Actions pagination

- Branch=main: total_count **2,500**; pages 1–10 returned 100 each; page 11 returned 0. **1,000 records accessible** in this query; total_count exceeds accessible results. Page 1 contains newest main runs, including E2E #294 and watchdog below.
- Event=schedule: total_count **596**; pages 1–5 returned 100 each, page 6 returned 96, page 7 returned 0. **596 records enumerated**.
- Exact current-main SHA: total_count **490**; pages 1–4 returned 100 each, page 5 returned 90, page 6 returned 0. **490 records enumerated**.

These are fresh REST inventories with page counts and boundaries; the branch=main query is truncated by the accessible-page boundary and is not a complete 2,500-run audit.

### Latest exact-main E2E #294 — failed safely before upload

- Run **44920455705**, job **136895133329**, main SHA above; workflow_dispatch, completed failure.
- Site preflight HTTP 200. Health attempts 1–4 timed out; attempt 5 returned HTTP 200. The final state still retained `api_health_request_error=ReadTimeout`.
- Current-main GitHub commit API returned HTTP 200 in this run; the earlier 403 was not reproduced.
- Render branch main, deployed SHA `bb6a9d27537e12b85768c7fead1467253b2423ba`; comparison HTTP 200, status `ahead`, parity false. Runtime-diff list includes three non-shipped script paths plus genuine shipped mismatches `webapp/community.py` and `webapp/community_app.py`.
- `guest_token_seen=false`, `job_id_seen=false`, `cleanup_attempted=false`; no upload, inference, specialists, report or deletion verification occurred.

Failure artifact **14713328852**:
- ZIP size 1,052 bytes, SHA-256 `7668c9bce879827cfb2d876acc3f64025adec4f44516c82b773c4cf04d244c37` (matches the upload log digest).
- Extracted `live-agent-e2e-failure.json`, 2,807 bytes, SHA-256 `6fabd1636c3263c86c1c78b433829cea1cffc33c6f669f85ffa55ac5b7b4bbe3`; ZIP unpack and JSON parsing succeeded.

### Watchdog #? — dispatch accepted

- Run **44920438929**, job **136895080077**, scheduled watchdog succeeded.
- Complete job log: latest E2E age **15,372 seconds**; it accepted a dispatch of the existing E2E workflow for current main.
- The current-main watchdog uses freshness/SHA logic only; it does not preflight deployed Render SHA or checkpoint verification. This is a concrete M1 safety gap. The dispatched E2E #294 failed the unchanged parity guard before upload.
- No watchdog artifact was attached.

### Release monitor #370 — monitor healthy, release blocked

- Run **44916557550**, job **136883314106**, completed successfully as a monitor.
- Artifact **14711388375**, ZIP 1,199 bytes, SHA-256 `42552f5bbdbf2e7101e52dd4566085869a64ae396ddbe179952ddd658e61b5d0` (matches the upload log).
- Extracted `release_status.json`, 2,765 bytes, SHA-256 `42a4e6fe1a7733b622bfb27b65e9587887650795da14e1e7f234a1fa7450de2`; parsed successfully.
- Status `BLOCKED`, `release_ready=false`. Frozen E4 checkpoint artifact **12183110279** lookup returned HTTP 404. E6/E7/uncertainty artifacts remain linked to old source run IDs; clean reproduction is also old, not exact-main freshness evidence.

### PR #178 tracker validation

- PR head remains `3d4a8e3c0c28b1d315b06319c44fd6329ea543a4`, base exact main.
- CI run **44918701139**, job **136889777268**, exact-head successful; `145 passed, 1 skipped`.
- This validates the tracker head as documentation/test CI only, not application runtime or scientific reproduction.

### M0 and M1 disposition

M0 remains **not accepted**: Actions pagination is now reproducible within the accessible boundary, and 99 open PR head/base SHAs were refreshed, but complete PR patches/checks/logs/artifacts and the truncated branch=main run history are not audited.

M1 remains **not accepted**: main still has the PR-trigger public upload-job risk (PR #103's main-only guard is verified on its branch, not main); the watchdog lacks a deployed-runtime/checkpoint pre-dispatch gate; Render runtime is stale; the exact main health contract does not prove immutable checkpoint verification. The two shipped webapp mismatches remain behind the strict parity guard.

### Evidence tiers and next action

- **Repository/API evidence:** main SHA/signature, Actions page counts, PR metadata, workflow source.
- **CI evidence:** #178 tests passed on its exact PR head.
- **Runner artifact evidence:** E2E failure/release-monitor artifacts were downloaded, unpacked, hashed and parsed; neither proves inference.
- **Public inference:** **not demonstrated**.

Next safe task: finish the prioritized PR audit (#103/#92/#105/#146/#150 and provenance stacks), then reconcile a clean additive runtime branch. Keep public upload blocked by stale runtime/checkpoint and parity. No merge/deploy authorization is assumed. Deadline risk remains **high**.

## Prioritized runtime-stack exact-head review — 2026-11-21 22:16 IST

Full patches were fetched for #92, #103, #105, #146, and #150; their relevant source/workflow/test changes were reviewed. Exact head/base metadata, associated workflow runs, job steps, logs, and artifact lists were refreshed for this selected stack. This is not a full 99-PR audit.

### #92 — watchdog pre-dispatch health/SHA/checkpoint gate

- Head 838b89d51cae3db2171bc67b0c2389c043b34122, base main d4a653e94501e8b9f1ec9de09ff71720f90ab340.
- CI run 43437830508, job 131927398126: 165 passed, 1 skipped, 7 subtests passed.
- Watchdog validation run 43437830689, job 131927398351, succeeded. Tests exercise current/stale/unverified runtime, checkpoint pin, API server time, bounded health retry, and dispatch decisions. Recovery-dispatch job 131927400708 was skipped on PR validation.
- Source review confirms pre-dispatch health requires main branch, healthy status, available and verified checkpoint, expected immutable digest, and valid 40-character Render SHA. Dispatch decisions compare deployed SHA to current main. Missing health/server time fails closed.
- Artifact lists for both runs: empty. Runner/PR validation only.

### #103 — public-upload main-only guard and authenticated GitHub REST checks

- Head 5372d812304eb3612dc7890e1f03ee9361e5c423, base main.
- CI 41231538021, job 124626597239: 148 passed, 1 skipped.
- E2E validation 41231537964: offline harness compile succeeded; public-upload job 124626868453 skipped. Artifacts: none.
- Full patch confirms PRs compile offline; public upload is restricted to upstream main; GitHub REST commit/compare requests use a read-only Bearer token, which is not sent to Render.
- Guard/auth fix remains unmerged; current main workflow still has the PR-trigger public-upload risk.

### #105 — immutable checkpoint health pin

- Head 1d4726b430da933180d2c2744ec564a442c09b96, base main.
- CI 43421687985, job 131872961675: 158 passed, 1 skipped.
- Tiled checkpoint validation 43421687940, job 131876422471: succeeded. Download/digest check, community startup health pin, real checkpoint worker, and constrained-memory validation steps passed. Worker log shows two 480 MiB-capped attempts with peaks 463,335,424 and 455,524,352 bytes, under the 470 MiB safety ceiling. It built an isolated validation image, not the production community image.
- Community/API validation run 43421687953 and BioMCP/web validation 43421688067 also succeeded; public E2E run 43421688000 was skipped.
- Patch review confirms health reports actual checkpoint digest and verification status; inference fails closed on mismatch. Environment digest override must still match the source-controlled release pin. All PR artifacts: none.

### #146 — sealed verified checkpoint snapshot

- Head 7c7f348333ba2cc1fe4bc53e53a0f1e62a9ef433, base PR #105 head 1d4726b430da933180d2c2744ec564a442c09b96.
- CI 44900605180, job 136835494093: 163 passed, 1 skipped.
- Checkpoint worker 44900605055, job 136836858514, succeeded. It builds the production community image; two 480 MiB-capped attempts peaked at 450,338,816 and 442,347,520 bytes, below the 470 MiB ceiling. Checkpoint SHA remained unchanged and all eight specialists completed.
- Patch review confirms inference consumes a second SHA-256-verified anonymous memfd snapshot with write/grow/shrink/seal protections, rather than the mutable pathname. Artifacts: none. Runner evidence only.

### #150 — Docker-input-aware runtime parity

- Head ed314fca17ba7a5dd7848c39e8410b27dea46185, base main.
- CI 44210719937, job 134488047196: 152 passed, 1 skipped, 29 subtests passed.
- Offline harness run 44210719925, job 134488047613, succeeded with seven classifier/workflow tests; public upload job 134488049712 skipped. Artifacts: none.
- Full patch review confirms only paths proven not copied into the Render images are excluded, unknown paths fail closed, Docker COPY/ADD inputs are allowlisted, and runtime build inputs trigger the parity workflow. Real webapp/community.py and webapp/community_app.py mismatches remain gated.

### Integration finding

These PRs are complementary, not individually mergeable as one tested stack. #103 and #150 overlap the E2E workflow/script; #105 introduces the health checkpoint contract; #146 is stacked on #105; #92 requires that health contract and suppresses dispatch when Render is stale/unverified. The safe sequence is a fresh additive integration branch with all required tests, not piecemeal merges or force-pushes. No merge was performed.

M0 remains **not accepted**: this is a prioritized stack audit, not complete full-patch/check/log/artifact review for all 99 open PRs. M1 is not accepted; selected PR green CI/runner evidence does not prove the live Render revision or public inference.


## Focused CI and PR audit — 2026-11-21 23:09 IST

Fresh repository metadata/search still resolves main to `d4a653e94501e8b9f1ec9de09ff71720f90ab340`. The commit fetch returned no signature-verification object in this connector payload; signature status is **not freshly verifiable here**. The main CI workflow at that SHA (blob `7a1d470d6ef7b0aef68673ff6ceb1539cc3d161e`) installs `.[test,web]` only, so the optional MCP SDK is not guaranteed to be present in the main CI environment. The Actions run-list endpoint and originating browser are unavailable through this session; no new main/schedule/exact-SHA inventory or public upload was performed.

### PR #80 — MCP SDK CI coverage

- Exact head `abf750e2bbea8cc5a449305790ead63ebf0979ba`, base main `d4a653e94501e8b9f1ec9de09ff71720f90ab340`.
- CI run **40079114233**, job **120828754444**: **147 passed**. The exact log confirms `mcp` is installed in the environment, but this run still uses the CI job's normal pytest collection.
- BioMCP/web validation run **40079114201**: MCP server smoke job **120828754710** succeeded; installed the MCP extra, built the server, and ran MCP-focused tests: **3 passed**. Web adapter smoke and public console integrity also succeeded.
- Patch is narrowly scoped: `.github/workflows/ci.yml` changes `.[test,web]` to `.[test,web,mcp]`; `tests/test_mcp_server.py` adds a real stdio MCP client protocol test using a synthetic uint16 TIFF (max 65535) and asserts tool discovery plus image inspection.
- This is **CI/runner evidence**, not external BioMCP interoperability or public user inference. PR #80 remains open; no merge.

### PR #174 — safe initial checkpoint loader

- Head `cd3a14a7c7d994a6d41004cf78c3f63f2af003f4`, base main.
- CI run **44747521522**, job **136326561315**: **148 passed, 1 skipped**.
- Patch uses `torch.load(..., weights_only=True)` and requires dictionary/model-state shape. Tests verify normal tensor-state loading, missing model state, and rejection of an unsupported pickle object. Source/tests reviewed; no weights or scientific result changed. Runner evidence only.

### PR #175 — restricted research checkpoint deserialization

- Head `2b3afbe9ebeaa312734f6e78098934480589360d`, base main.
- CI run **44814708387**, job **136559915307**: **147 passed, 1 skipped**.
- Patch restricts checkpoint deserialization in five standalone evaluators and two E6 workflows to `weights_only=True`, with AST/YAML regression checks. Full selected patch reviewed; no model/metrics changed. Runner evidence only.

### PR #178 — tracker exact-head CI

- Head `99dc8e9c78c830f2f22ae26a7da9b31578be0798`, base main.
- CI run **44926908678**, job **136914885944**: **145 passed, 1 skipped**; full job log confirms dependency install and pytest success.
- This validates the tracker documentation commit's CI, not application runtime, deployment parity, public inference, or research reproduction.

### M0 disposition

This audit adds verified exact-head CI and patch evidence for three selected PRs. M0 remains incomplete: the 99-PR inventory is not fully reviewed patch/check/log/artifact-by-artifact, main Actions pagination is inaccessible, and signature verification is unavailable in the current connector. Prioritize closing these inventory gaps and avoiding duplicate PRs. M1 remains blocked on runtime integration and authorized live SHA/checkpoint verification; M2–M7 are not accepted.


## Tracker follow-up — current PR head and validation visibility — 2026-11-21

The tracker branch now points to commit `69369978ce7f8d4b33ee28dc886947712f9e5479` (blob `5bc7a4753568a23a87ee3a3362fdd2b56b019f8b`). The push succeeded and the PR head/base metadata refreshed. The commit-scoped workflow-run lookup and combined-status endpoint returned empty for this new head; therefore its CI is **not yet verified**, not assumed green. The prior `99dc8e...` tracker commit's CI (run **44926908678**, job **136914885944**, 145 passed/1 skipped) remains valid only for that earlier commit.

### CI dependency finding

Main CI installs `.[test,web]` at the current main SHA; it does not install the `mcp` extra. PR #80 changes the install to `.[test,web,mcp]`. PR #80's exact-head run **40079114233**, job **120828754444**, succeeded (**147 passed, 1 skipped**). Its separate validation run **40079114201** succeeded: MCP smoke job **120828754710** installed the MCP extra, constructed the server, and ran the focused protocol tests (**3 passed**). This is a useful CI coverage fix, but still runner evidence; it does not establish interoperability with a real external BioMCP client/service.

### Safe checkpoint-loading PRs

- PR #174 exact head `cd3a14a7c7d994a6d41004cf78c3f63f2af003f4`, main-based. CI run **44747521522**, job **136326561315**, **148 passed, 1 skipped**. Reviewed patch: restricted `weights_only=True` loading for initial checkpoints, shape checks, and rejection tests.
- PR #175 exact head `2b3afbe9ebeaa312734f6f78098934480589360d`, main-based. CI run **44814708387**, job **136559915307**, **147 passed, 1 skipped**. Reviewed patch: restricted deserialization in five evaluators and two E6 workflow checkpoint reads; AST/YAML regression checks.
- Both are CI evidence and have not been merged; no model or scientific artifact was modified.

### Current baseline priority

1. Preserve and review existing PRs; do not duplicate #80, #174, or #175.
2. Complete remaining PR patch/check/log/artifact audit and refresh accessible Actions evidence.
3. M1 runtime stack integration still requires exact-main CI plus the authorized deployed SHA/checkpoint identity gate. Render and public E2E remain uninspected/unperformed in this run.
4. M0 remains partial. M2–M7 remain unaccepted.


## Fresh audit and diagnostic fix — 2026-11-22 00:16 IST

### Repository identity and evidence access

- Repository-scoped commit search still resolves main to `d4a653e94501e8b9f1ec9de09ff71720f90ab340`. The normalized commit fetch does not expose signature verification; signature is **not freshly verified** in this run.
- Browser tools are read-only tab/context APIs, and the originating browser context is unavailable. GitHub Actions run-list pagination and commit-verification details are not exposed by the current connector; public GitHub API URLs could not be opened through the web fallback. No fresh branch/schedule/exact-main Actions inventory, latest E2E/watchdog identification, or main-run artifact download was possible. The last-known E2E/watchdog records remain historical and are not relabeled fresh.

### Current-main source audit

- E2E workflow blob `c903cc0ab7b7695ba5a7d402b7a4f82496d38732` includes a `pull_request` trigger for `scripts/live_public_agent_e2e.py`; its public-upload job has no main-only job condition. This is a source-level PR upload risk on main. PR #103 contains the `refs/heads/main` restriction and PR-only offline harness, but is still unmerged; the risk remains on main.
- Watchdog workflow blob `20aef7459b86b464007d19a1025a4492ec34b0fe` and script blob `6800946aeb84a1243219e2f85fd67ea0fee6a67b` still dispatch based on E2E freshness/current SHA and do not preflight deployed-runtime SHA/checkpoint identity. PR #92 remains the proposed gate and is unmerged.
- These source findings were read at the exact main SHA above; no deployment or Render service was inspected.

### PR #94 — health diagnostics follow the latest attempt

PR #94 head was refreshed from `10e4867bfb52b05d525848032a04957317e5a206` and advanced with three non-force commits:

- `6e68e89084c29cc64cf4dc2335fcc5ec2b16829f`: helper functions record latest HTTP response or transport error and remove contradictory stale fields.
- `f54d2336c4cfed479b833655533ae9d43a5648c5`: E2E uses the helpers for response, timeout, and readiness-budget diagnostics.
- `4c1376105f3c6d25cc9f376a5906cfab960e532d`: tests cover recovered HTTP 200, non-200 response after a prior timeout, and request error after a previous body.

The branch update was verified through commit/file retrieval. Exact-head CI run `44938285032`, job `136949662592`, completed successfully: **150 passed, 1 skipped, 1 warning**. The full log is 51,086 bytes; the warning is an `invalid escape sequence '\\/'` deprecation in the source-inspection test. Run `44938285077`, job `136949662996`, passed the offline compile-only harness; its public-upload job `136949664003` was skipped. Both runs had no artifacts. This is PR CI/harness evidence only. PR-harness run `44938285077`, job `136949662996`, succeeded: Python compilation passed and the public-upload job `136949664003` was skipped. Run `44938285077` had no artifacts. The local isolated helper-transition check passed 3 cases; this is **local logic evidence only**, not the full repository suite or public inference.

### PR #178 tracker validation

- Current tracker head `43b54e4c30dac230f5b3e0a0dc4cebb16878f153`, base main. CI run `44931462717`, job `136928795152`, passed `145 passed, 1 skipped`. No artifacts were attached. This result validates that earlier tracker commit only; a new tracker commit will need its own checks.

### Milestone gate and risk

M0 remains **not accepted**: the selected PR audit is not a complete review of every open PR's full patch/check/log/artifact set, and the Actions inventory/signature refresh is blocked by tool access. M1 remains blocked by the main-only public-upload guard not being merged, the watchdog lacking runtime/checkpoint pre-dispatch gating, and stale/unverified deployment identity. M2–M7 are not accepted. Public upload/inference was not performed.

Deadline risk remains **high** for 2027-01-01. Next safe task is refresh #94 CI after it completes and prioritize existing #103/#92/#105/#146/#150 integration without duplicate PRs. Merge, Render inspection/deployment, and public E2E require authorization and verified runtime/checkpoint identity.


## PR safety and watchdog review — 2026-11-22 00:16 IST

### PR #94 exact-head validation refresh

- PR #94 head `4c1376105f3c6d25cc9f376a5906cfab960e532d`, base exact main.
- CI run `44938285032`, job `136949662592`: **150 passed, 1 skipped, 1 warning**. Full job log retrieved (51,086 bytes). The warning is a deprecation warning from source inspection: `invalid escape sequence '\\/'`.
- E2E harness run `44938285077`, job `136949662996`, passed the compile-only harness. Public-upload job `136949664003` was skipped. Both runs had no artifacts.
- The new diagnostic helpers/tests were verified at the exact PR head. Three isolated local transition checks passed, but local logic checks are not repository CI or public inference.

### PR #92 watchdog gate review

- Head `838b89d51cae3db2171bc67b0c2389c043b34122`, base exact main.
- CI run `43437830508`, job `131927398126`: **165 passed, 1 skipped, 7 subtests passed**.
- Watchdog validation run `43437830689`, job `131927398351`, succeeded. Full log (24,269 bytes) shows mocked health-preflight timeout/rejection paths fail closed; recovery dispatch job `131927400708` was skipped on PR. Both runs had no artifacts. This is PR/runner validation, not live Render proof.
- Patch review confirms dispatch requires a verified current-main Render SHA and the immutable checkpoint digest; it preserves the existing E2E parity gate. The gate is still unmerged and the live health contract has not been independently verified.

### PR #103 main-only upload guard

- Head `5372d812304eb3612dc7890e1f03ee9361e5c423`, base exact main. Patch reviewed: PR events compile the harness; public upload is conditioned on `refs/heads/main`; GitHub REST calls use a read-only token that is not sent to Render.
- Associated CI run `41231538021`, job `124626597239`: **148 passed, 1 skipped**. E2E harness run `41231537964`, job `124626867341`, passed compilation; upload job `124626868453` was skipped. No artifacts. These checks are historical (31 October/1 November), not a fresh rerun.
- Main source remains unsafe for PR-triggered public upload until this guard reaches main; no merge was performed.

### Tracker validation status

Tracker head `d8984dda6f1cdc8085eb291c5efb32b40fe33aa7`; its CI run `44938634115`, job `136950720578`, was still in dependency installation with pytest pending at the last refresh. No artifact was attached. Earlier tracker CI does not validate this commit.



## Checkpoint stack and last-known public E2E artifact re-verification — 2026-11-22

### PR #105 / #146 evidence refresh

- PR #105 head `1d4726b430da933180d2c2744ec564a442c09b96` (base main). Associated CI run `43421687985`, job `131872961675`: 158 passed, 1 skipped. Community validation `43421687953`, job `131872961979`: 4 passed; live Render job `131872964071` skipped. Tiled worker `43421687940`, job `131876422471`, succeeded with two attempts; checkpoint SHA remained the pin. Peaks were 463,335,424 and 455,524,352 bytes against 503,316,480-byte limit and 492,830,720-byte safety ceiling. These runs predate PR #105's 19-Nov update and their run metadata does not expose tested head SHA; do not treat them as proof of latest-head validation.
- PR #146 head `7c7f348333ba2cc1fe4bc53e53a0f1e62a9ef433` is stacked on #105. Associated CI `44900605180`, job `136835494093`: 163 passed, 1 skipped. Worker `44900605055`, job `136836858514`, succeeded twice; pinned checkpoint SHA before/after matched; peaks 450,338,816 and 442,347,520 bytes, below the 470-MiB ceiling and 480-MiB hard limit. Community contract `44900605117` job `136835493892`: 4 passed; failure cleanup `44900605141` job `136835494233`: 18 passed; web adapter `44900605104` job `136835494045`: 163 passed, 1 skipped; MCP smoke `44900605104` job `136835494146`: 2 passed. Live Render validation was skipped. No artifacts were attached. All of these are runner/CI evidence, not public inference; run-to-head SHA correlation is not visible in the returned metadata.
- **Stack dependency to verify before merge:** PR #105's patch imports/uses `_checkpoint_for_inference` in `webapp/community.py`, but its `webapp/app.py` patch does not introduce that helper. PR #146's `webapp/app.py` patch does introduce `_checkpoint_for_inference`. Treat #105 as dependent on #146; do not merge #105 alone. The file-fetch API also returned the main blob SHA for `webapp/community.py` at #105's commit despite the PR patch showing changes, so exact-file retrieval is inconsistent and the integration review remains incomplete.

### E2E #294 artifact re-download

The last-known exact-main E2E #294 run `44920455705`, job `136895133329`, was retrieved again. Artifact `14713328852` was downloaded, unpacked, and parsed successfully; archive SHA-256 `7668c9bce879827cfb2d876acc3f64025adec4f44516c82b773c4cf04d244c37` matched the workflow log. Extracted JSON SHA-256: `6fabd1636c3263c86c1c78b433829cea1cffc33c6f669f85ffa55ac5b7b4bbe3`. It confirms health HTTP 200 after four ReadTimeout attempts but stale `api_health_request_error=ReadTimeout`, Render SHA `bb6a9d27537e12b85768c7fead1467253b2423ba`, parity false, and five runtime/config mismatches. `guest_token_seen=false`, `job_id_seen=false`, `cleanup_attempted=false`; upload/inference never started. This is the last-known run, not a freshly enumerated latest-main run.
- Last-known watchdog #124 run `44843387759`, job `136657079593`, accepted a dispatch because exact-main E2E age was 11,111 seconds; it did not check deployed SHA/checkpoint identity. No artifacts. Main watchdog safety gap remains until #92 is merged and runtime is independently verified.

### Tracker CI

Commit `3cfd0742385ae8ac8987140546cb38089c11257a` was verified as the tracker file's latest previous revision. Its CI run `44938877172` was in progress at last refresh; a subsequent tracker update will require another exact-head check.
