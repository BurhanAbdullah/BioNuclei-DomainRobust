# Engineering audit — 2026-11-23 07:08 IST

This audit refreshes repository evidence for PR #178. Browser control was checked: the available browser integration is read-only, and the browser-originating context is unavailable. No manual upload was attempted. No Render workspace, service, deployment, or logs were inspected. No deployment, merge, or public E2E dispatch was performed.

## Identity and CI

- Main SHA: `b8d4a3b015cfcff56201b889702dc0ce7ee83e4f`.
- GitHub commit API: `verified=false`, reason `unsigned`.
- Branch API metadata: `protected=false`; required status-check enforcement was not reported.
- Exact-main CI [45051076563](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45051076563), job `137296096482`: success, **158 passed, 1 skipped**. The complete job log was retrieved and reviewed.
- PR #178 latest head `b408c750d16699b5aec8f43e9cfee707033c51fa`, base `d4a653e94501e8b9f1ec9de09ff71720f90ab340`; exact-head CI [45090528401](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45090528401): success, **145 passed, 1 skipped**. PR remains open/draft and behind current main.
- The new audit document is additive; no application source changed.

## Actions/PR inventory coverage

- `branch=main`: pages 1–10 returned 100 each; pages 11–25 returned 0. API total says 2,500, but only 1,000 records were exposed. The remaining 1,500 are not audited through this listing.
- `event=schedule`: pages 1–6 returned 100; page 7 returned 11. **611 scheduled runs enumerated**.
- `head_sha=current main`: page 1 returned **15/15** runs.
- Open PRs: page 1 returned 100, page 2 returned 4. **104 PRs**. Metadata was refreshed; complete manual diff/check/log/artifact review across all 104 is still not done.

## Latest exact-main public E2E failure — run 45078374593

[Run 45078374593](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45078374593), job `137380627039`, failed at the real public-upload/inference step. Browser dependency setup and syntax validation completed. The full job log was fetched.

The failure is the runtime parity assertion: Render branch reported `main`, deployed SHA `bb6a9d27537e12b85768c7fead1467253b2423ba`, comparison status `ahead`, and parity `false`. Current main is `b8d4a3b015cfcff56201b889702dc0ce7ee83e4f`. The failure lists 11 runtime-diff paths: nine `scripts/` paths and `webapp/community.py`, `webapp/community_app.py`. The complete main-comparison list contains 34 paths.

The health probe had ReadTimeout on attempts 1–4 and HTTP 200 on attempt 5. `checkpoint_available=true` is not immutable digest verification. `guest_token_seen=false`, `job_id_seen=false`, `cleanup_attempted=false`, and `cleanup_verified=false`; upload, inference and cleanup were not reached.

Artifact ID `14776236426`, `live-public-agent-e2e-failure-45078374593`:
- ZIP SHA-256: `5c90001825841558a98eccc29307e902c0e88179f094c58e770c1f3c20f19cd6`
- Extracted JSON SHA-256: `fa958651e4ac6d2fac5f6b7d14e09b887ce20e36cc973d8abf66d63ac6a461e2`

Archive was downloaded, `unzip -l` verified, extracted JSON parsed and hashes recomputed. Tier C public E2E preflight failure; no inference proof.

## Watchdog

[Run 45080030259](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45080030259), current-main SHA, succeeded. Job `137385862721` fetched with steps and complete log. It suppressed dispatch because the current-main E2E was recent (1,092 seconds). Watchdog success proves only its recovery decision executed; no runtime/checkpoint validation.

## Release monitor artifact

[Release status watch 45074918226](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45074918226) completed successfully but reported `status=BLOCKED`, `release_ready=false`.

Artifact `14774119812`, `release-status-watch-45074918226`:
- ZIP SHA-256: `ec2d8b7fdccbb2d934eb0543d8f41198307d24ca0aaa0904c83caea6113c5427`
- Extracted `release_status.json` SHA-256: `89a1721dfb2dc57796a714624246463a4645bbd0c661537b6aa8d39971db2936`
- E4 checkpoint artifact `12183110279`: lookup HTTP 404.
- E7 BBBC038 evidence artifact `12525356981`: lookup HTTP 404.

ZIP integrity/listing and JSON parsing succeeded. A green monitor is not a release-ready result.

## Runtime parity and upload-gate PRs

### PR #82 — parity classifier
Head `5f30a00e5e3910d87ee19420c0293af668d2c531`, base `d4a653e94501e8b9f1ec9de09ff71720f90ab340`, open, non-draft, stale base. Exact-head checks include successful tests and offline `validate-harness`; public-upload job was skipped.

The exact-head classifier excludes `scripts/`, workflow/test paths and most docs; unknown paths remain runtime-affecting. This is consistent with the current Render Dockerfiles, which copy `webapp/`, `src/`, `configs/`, `pyproject.toml`, README, and only `docs/RESEARCH_PROTOCOL.md` and `docs/DATASETS.md`; they do not copy `scripts/`. The two `webapp/community*.py` files from the E2E failure remain runtime paths and must stay parity-gated.

A review comment was added (review ID `6015688479`) with an integration blocker: PR #82's public-upload condition only checks `github.ref == refs/heads/main`, which is not an upstream-repository guard for a fork's main push. It conflicts with PR #187's stricter event/repository/ref condition and the tests assert different expressions. Rebase/integrate the stronger guard and update tests before merging. No merge was performed.

### PR #187 — upstream-main public upload restriction
Head `47d4bdf0b1fb111ac865d6cb360dcdc95cc929a2`, base current main `b8d4a3b015cfcff56201b889702dc0ce7ee83e4f`. Exact-head CI [45045185704](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45045185704) succeeded; **159 passed, 1 skipped**. PR E2E [45045185706](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45045185706) skipped public upload and is harness-only evidence. PR is open/draft.

### PR #188 — deployed-SHA/checkpoint dispatch gate
Head `f2a095f33bdcfd2c521abd1b7b42ded537fe5247`, base current main. Exact-head CI [45068485205](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45068485205) succeeded, **190 passed, 1 skipped**. Its check list includes a "Live Render endpoint" check; that check's logs were not opened because Render inspection is unauthorized, so it is not treated as live deployment evidence. PR is open/draft. M1 is not complete until the gates are integrated on current main, exact-main CI passes, and stale runtime/pin dispatch tests are proven.

## Dataset downloader PR stack

The exact-head checks are green but the PRs remain open and have stale/stacked bases. No live dataset download was performed.

- [PR #136](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/136), head `a85ea1801a58f4146b9540e9e075e0c1f00fd228`, base `d4a653e94501e8b9f1ec9de09ff71720f90ab340`: exact CI run [43723583459](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43723583459) succeeded; retries transient errors, uses temporary downloads and atomic replacement.
- [PR #140](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/140), head `dc42500e447c297682a4f7296833af952b40ee56`, stacked base `1fd0de5f7660148ba1341c6087c1fdcc7c3143d`: exact CI [43727201964](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/43727201964) succeeded; validates compressed-size, ZIP entry/path and expansion limits before CRC scan/extraction.
- [PR #158](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/158), head `b00a0558a51bc3daa5ddd42808268d5038c26d7a`, stacked base `dc42500e447c297682a4f7296833af952b40ee56`: exact CI [44051271731](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/44051271731) succeeded; bounds total download time using a monotonic deadline, socket timeouts and 64 KiB `read1` chunks.

These are runner tests, not BioStudies availability/real dataset evidence. Consolidate the stack before merging; do not merge individually out of order.

## Milestones and next action

- **M0: incomplete.** Current inventory is reproducible for the exposed 1,000 main-run records, 611 schedules, 15 exact-main runs and 104 PRs. Full PR checks/logs/artifacts/manual review remains outstanding, and Actions pagination has an exposure gap.
- **M1: incomplete.** Runtime parity is false; #187/#188 are unmerged; #82 needs integration with #187's upstream/event guard. No Render SHA/checkpoint was verified.
- **M2: incomplete.** Dataset download failure prevented evaluation/metrics; no fresh exact-main baseline/manifest verification.
- **M3: incomplete.** Public E2E stopped at parity, before upload/job/inference/eight outputs/report/ZIP.
- **M4: incomplete.** Privacy/owner-isolation/retention/deletion live checks remain unverified.
- **M5: blocked.** Release monitor missing E4/E7 artifacts; fresh exact-main reproduction not ready.
- **M6: unverified.** Real external BioMCP execution not demonstrated.
- **M7: not ready.** Acceptance evidence incomplete.

Schedule risk remains **HIGH** (about 39 days to 2027-01-01). Prioritize: reconcile #82/#187/#188 runtime guards; verify deployment only after explicit authorization; integrate #136/#140/#158 downloader stack; then rerun fresh exact-main scientific evaluation and release monitor. No source-code edit, local test, inference, public upload, deployment or merge was performed in this audit run.


## Follow-up: S-BIAD634 failure root cause confirmed from complete job log

Run [45077440306](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45077440306), job `137377712207`, is current-main SHA and failed at `Download and inventory S-BIAD634`. I retrieved the complete log and isolated the failure line: `Corrupt ZIP member: rawimages/Neuroblastoma_4.tif`. This is **confirmed archive corruption/CRC failure**, not a demonstrated transient network exception. Baseline artifact `14775742324` was downloaded successfully and its expected digest `09a46f635762b27a9179836e4ede92fe4d58d04fbe5872eb6a8b67a725e07788` is printed in the log; evaluation and metrics were skipped.

Failure artifact `14775299939`:
- ZIP SHA-256: `0dc2c8298f2d490bade6d5a53c81c185ab350d12e80f1000edfc3e1a26e5a213`.
- Extracted `outputs/s_biad634_zero_shot/provenance.json` SHA-256: `1d8bd92691d05a33d19f8ca62ed8a2fc2997978dff029ce692b1a7aee3f6576c`.
- Parsed JSON records only repository, current-main commit, workflow run ID and baseline run ID; it contains no dataset inventory or metrics.

Current main `scripts/download_s_biad634.py` blob `d6e5a27f55cc6c4bd77ef8700aecb891e93a3e3f` downloads once directly to the destination with a 120-second socket timeout, then runs `ZipFile.testzip()`. It detects the corrupt member but has no retry/atomic temporary publication, so the transfer can leave a corrupt destination. PR #136's retry/atomic download alone does not validate CRC before publishing. PR #140 adds resource-bounded ZIP validation and retries corrupt archives; PR #158 is stacked on #140 and adds a total monotonic deadline/socket timeout control. Exact-head CI on these PRs is runner evidence only. A review comment was added to #158 (review ID `6015698282`) to prioritize the #140/#158 stack, rebase and avoid merging #136 separately without reconciliation.

This follow-up strengthens the root-cause evidence but does not complete M2: a real external dataset download, verified manifest, evaluation and metrics remain absent.
