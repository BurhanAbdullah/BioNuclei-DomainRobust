# Engineering audit — 2026-11-23 05:17 IST

This additive audit refreshes current-main identity, Actions pagination, open-PR metadata, exact-main CI/E2E/watchdog/release runs, and failure artifacts. Runner and public E2E evidence are distinguished from live deployment/inference proof. No Render workspace/service was inspected and no deployment or merge was performed.

## Evidence tiers

- **Tier A — repository/API/source:** GitHub API metadata and source files read at the exact SHA below.
- **Tier B — runner/CI:** GitHub Actions tests, workflow logs, and artifacts. These do not prove public production behavior.
- **Tier C — public scheduled E2E runner:** the workflow reached public URLs, but its failure artifact shows it stopped at runtime-parity preflight. It did not create a guest session or analysis job and therefore does not prove inference.

## Main identity and integrity

- Current `main`: `b8d4a3b015cfcff56201b889702dc0ce7ee83e4f`.
- Commit verification: `verified=false`, reason `unsigned`. This SHA is not signature-verified.
- `main` branch API reports `protected=false`; required status-check enforcement is not enabled in the returned branch metadata.
- Exact-main CI run [45033447021](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45033447021), job [137241865015](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45033447021/job/137241865015): success, **158 passed, 1 skipped**.
- Exact current-main SHA query returned 15 records on page 1 (complete, total 15).

## Actions pagination

| Query | Fresh pages/records | API total | Coverage |
|---|---|---:|---|
| `branch=main` | pages 1–10: 100 each; pages 11, 12, 25: 0 | 2,500 on page 1 | only 1,000 records exposed; remaining 1,500 unavailable through this listing |
| `event=schedule` | pages 1–6: 100 each; page 7: 11 | 611 | complete |
| `head_sha=<current main>` | page 1: 15 | 15 | complete |
| open PRs | page 1: 100; page 2: 4; page 3: 0 | — | 104 metadata records |

The branch-main Actions listing is capped/truncated by the connector/API path; it is not treated as a complete history. Full diff content for all 104 open PRs was retrieved in a diff-enabled listing and path/keyword triage was performed; complete manual review plus check/log/artifact review for all 104 remains outstanding.

## Exact-current-main workflow snapshot

| Run | Workflow | Event | Result |
|---|---|---|---|
| [45080030259](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45080030259) | Public E2E schedule watchdog | schedule | success |
| [45078374593](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45078374593) | Live public agent E2E | schedule | failure |
| [45077440306](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45077440306) | S-BIAD634 zero-shot transfer | workflow_run | failure |
| [45074918226](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45074918226) | Release status watch | schedule | success, but status artifact says blocked |
| [45051076563](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45051076563) | CI | push | success |
| [45049473842](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45049473842) | Public E2E schedule watchdog | schedule | success |
| [45048552764](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45048552764) | S-BIAD634 zero-shot transfer | workflow_run | success |
| [45046003953](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45046003953) | S-BIAD634 zero-shot transfer | workflow_run | success |
| [45045139175](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45045139175) | CI | push | success |
| [45043763018](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45043763018) | Live public agent E2E | schedule | failure |
| [45043089844](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45043089844) | Release status watch | schedule | success |
| [45041443776](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45041443776) | S-BIAD634 zero-shot transfer | workflow_run | success |
| [45039935869](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45039935869) | S-BIAD634 zero-shot transfer | workflow_run | success |
| [45033447021](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45033447021) | CI | push | success, 158 passed/1 skipped |
| [45033447025](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45033447025) | Pages deploy workflow | push | success |

### Public E2E failure — run 45078374593

Job [137380627039](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45078374593/job/137380627039) and artifact [14776236426](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45078374593/artifacts/14776236426) were refreshed, downloaded, unpacked, and parsed.

- Site/API preflight HTTP 200 was observed, but the runtime-parity check failed: Render branch `main`, deployed commit `bb6a9d27537e12b85768c7fead1467253b2423ba`, current main comparison `ahead`, runtime tree parity `false`.
- Artifact listed 34 differences against main and 11 runtime-tree differences. The runtime SHA is not the current-main SHA.
- API health attempts 1–4 returned `ReadTimeout`; attempt 5 returned HTTP 200.
- `guest_token_seen=false`, `job_id_seen=false`, `cleanup_attempted=false`, `cleanup_verified=false`. The job did not reach upload/inference or cleanup.
- ZIP integrity test passed. Archive SHA-256: `5c90001825841558a98eccc29307e902c0e88179f094c58e770c1f3c20f19cd6`. Extracted JSON SHA-256: `fa958651e4ac6d2fac5f6b7d14e09b887ce20e36cc973d8abf66d63ac6a461e2`.

This is Tier C preflight failure evidence only; it is not public inference proof.

### Watchdog — run 45080030259

Job [137385862721](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45080030259/job/137385862721) succeeded. Its log says the current-main E2E was recent (1,092 seconds old), so the watchdog suppressed a duplicate. This does not verify deployed runtime or checkpoint identity.

### Zero-shot S-BIAD634 — run 45077440306

Job [137377712207](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45077440306/job/137377712207) failed at **Download and inventory S-BIAD634** after selecting baseline run `45063913011`, downloading its checkpoint artifact, and recording provenance. Evaluation and metrics steps were skipped. The log does not expose the download exception, so a timeout/network failure is plausible but not confirmed; the downloader currently performs one `urlopen(..., timeout=120)` with no retry.

Failure artifact [14775299939](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45077440306/artifacts/14775299939) contains provenance only (no dataset manifest). ZIP integrity and JSON parsing passed. Archive SHA-256: `0dc2c8298f2d490bade6d5a53c81c185ab350d12e80f1000edfc3e1a26e5a213`; extracted provenance JSON SHA-256: `1d8bd92691d05a33d19f8ca62ed8a2fc2997978dff029ce692b1a7aee3f6576c`.

The current-main downloader source blob is `d6e5a27f55cc6c4bd77ef8700aecb891e93a3e3f`. It uses a direct BioStudies ZIP URL, a single 120-second download attempt, and writes the manifest only after extraction. No source change was made because the run log did not establish the failure cause. Official BioStudies/BioImage Archive guidance describes FTP/Aspera downloads and obtaining accession-specific paths via the `/info` API; verify the current S-BSST265 path before changing the downloader:
- https://www.ebi.ac.uk/bioimage-archive/help-download/
- https://www.ebi.ac.uk/biostudies/RH3R/help

### Release status watch — run 45074918226

Job [137369912756](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45074918226/job/137369912756) succeeded as a monitor, but artifact [14774119812](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45074918226/artifacts/14774119812) says `status=BLOCKED`, `release_ready=false`.

- Blocker: frozen E4 checkpoint artifact `12183110279` returned HTTP 404.
- Blocker: E7 BBBC038 evidence artifact `12525356981` returned HTTP 404.
- Six checked E6/uncertainty artifacts remain available and identity-matched at that monitor's recorded source run IDs; those IDs are not current-main provenance.

The monitor's success means it ran successfully, not that the release is ready. Archive SHA-256: `ec2d8b7fdccbb2d934eb0543d8f41198307d24ca0aaa0904c83caea6113c5427`; extracted JSON SHA-256: `89a1721dfb2dc57796a714624246463a4645bbd0c661537b6aa8d39971db2936`.

## Selected open-PR audit

All 104 open PRs' head/base metadata and full diff content were refreshed. Broad path/keyword triage flagged 98 PRs (mostly workflow/runtime/security/data/privacy paths); a limited hard-coded credential-pattern scan found 0 hits. This is not a comprehensive secret scanner or manual code review. Checks/logs/artifacts for all 104 are **not** audited. These prioritized PRs were inspected at exact heads:

### PR #188 — runtime SHA/checkpoint gate

- Head `f2a095f33bdcfd2c521abd1b7b42ded537fe5247`, base main `b8d4a3b015cfcff56201b889702dc0ce7ee83e4f`; 7 files, 1,077 additions/35 deletions, 15 commits.
- Six exact-head workflow runs succeeded. CI [45068485205](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45068485205), job [137349893189](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45068485205/job/137349893189): **190 passed, 1 skipped, 7 subtests passed**.
- Adds upstream watchdog guard, bounded health retries, required current-main SHA, actual immutable checkpoint digest/verification, and tests for stale/unverified runtime/pin. Render was not inspected, so live contract is unverified.
- Exact-head runner checks are green, but no live deploy, public E2E, or merge is authorized/performed.

### PR #187 — prevent PR-triggered public uploads

- Head `47d4bdf0b1fb111ac865d6cb360dcdc95cc929a2`, base main `b8d4a3b015cfcff56201b889702dc0ce7ee83e4f`; 2 files, 40 additions/0 deletions.
- Three exact-head workflow runs succeeded. CI [45045185704](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45045185704), job [137278137052](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45045185704/job/137278137052): **159 passed, 1 skipped**. The PR-triggered E2E run [45045185706](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45045185706) passed offline validation and skipped public upload.
- Main workflow at the current SHA still lacks a public-upload job guard on PR events. This is a security priority; PR #187 adds a guard for upstream main/non-PR events and an offline-only PR validation job.

### PR #178 — baseline audit bundle

- Head `e636dd844bd1b57be3f9b29f111c4dfc12a60f2d`, base `d4a653e94501e8b9f1ec9de09ff71720f90ab340` (behind current main); 8 documentation files, 1,910 additions, 64 commits.
- Exact-head PR CI [45051014735](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45051014735), job [137295906480](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45051014735/job/137295906480): **190 passed, 1 skipped, 7 subtests passed**; push CI [45051009962](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45051009962) succeeded (**158 passed, 1 skipped**).
- The PR remains draft and its base is stale. Do not merge until its documentation is reconciled with current main and full audit coverage is reviewed.

## Prioritized engineering work

1. **M1/security (highest):** PR #187 guard PR-triggered public upload; PR #188 fail-closed deployed SHA/checkpoint gate. Review integration order and live contract before merging; both remain open/draft.
2. **M1/runtime parity:** current E2E runtime differs from main. Do not dispatch public E2E or attempt upload while runtime SHA/checkpoint cannot be independently verified.
3. **M2/science:** zero-shot dataset acquisition failed before evaluation; investigate BioStudies URL/path, retries, and bounded download integrity without assuming cause. E4 checkpoint and E7 evidence artifacts are missing (404); recreate provenance on exact main.
4. **M4/privacy:** reconcile lifecycle stacks (#85–#87 vs #129) for worker-safe deletion, expiry-at-access, lock order, and verified cleanup before live acceptance.
5. **M5/reproducibility:** current-main E6/E7/uncertainty/clean-environment runs and fresh, identity-bound artifacts remain unverified.
6. **M6/BioMCP:** runner validation exists; real external integration remains unverified.
7. **Governance:** main is unsigned and unprotected per API metadata; address commit signing and required CI protections with owner authorization.

## Milestone gate

- M0: baseline inventory and priority list are refreshed, but complete PR diff/check/log/artifact audit is outstanding; **not complete**.
- M1: **not complete** (main workflow public-upload guard missing; watchdog lacks deployed-SHA/checkpoint gate; exact-head PR checks are runner evidence only).
- M2: **not complete** (fresh current-main baseline/evaluation provenance and successful target evaluation not proven).
- M3: **not complete** (no successful public upload-to-inference run; latest run stopped before guest/job creation).
- M4: **not complete** (source/CI review only; no authorized live deletion/privacy verification).
- M5: **not complete** (release status blocked; current-main research artifacts unavailable).
- M6: **not complete** (external BioMCP execution not demonstrated).
- M7: **not complete**.

Deadline risk: **high** — 39 days remain until 2027-01-01. Runtime parity, unmerged safety PRs, scientific artifact loss, and incomplete audit coverage are on the critical path. Deadline is not guaranteed.

## Next action

Continue the M0 audit and exact-head validation of the high-priority runtime/security and research PR stacks. Keep public E2E dispatch, Render inspection/deploy, and merge blocked pending explicit authorization. No source-code change or research evaluation was performed in this audit run.
