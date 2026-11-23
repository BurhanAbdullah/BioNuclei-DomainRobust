# Engineering audit — 2026-11-22 23:08 IST

This is an additive refresh of the baseline PR. It records current-main repository and Actions evidence; it does not establish deployment or public inference.

## Main identity and integrity

- Main SHA: `b8d4a3b015cfcff56201b889702dc0ce7ee83e4f`.
- Commit verification: `verified=false`, reason `unsigned`; signature object is present and explicitly reports no signature.
- Exact-main CI run [45033447021](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45033447021), job [137241865015](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45033447021/job/137241865015): successful. Test log: **158 passed, 1 skipped**.
- Exact-main Pages run [45033447025](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45033447025): successful. This is workflow evidence, not browser-level verification.
- Rulesets endpoint returned an empty array. Branch-protection endpoint returned 403 `Resource not accessible by integration`; therefore branch protection is **not verified** in this audit.
- Actions API reports 2,500 runs for `branch=main` and 608 scheduled runs. Page 1 was refreshed for each query (100 records); full pagination was not completed. Exact current-main SHA query returned 10 records.

## Exact-main workflow snapshot

| Run | Workflow | Event | Result |
|---|---|---|---|
| [45049473842](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45049473842) | Public E2E schedule watchdog #131 | schedule | success |
| [45048552764](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45048552764) | S-BIAD634 zero-shot transfer | workflow_run | in progress at query |
| [45046003953](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45046003953) | S-BIAD634 zero-shot transfer | workflow_run | success |
| [45045139175](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45045139175) | CI | push to feature branch | success |
| [45043763018](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45043763018) | Live public agent E2E #303 | schedule | failure |
| [45043089844](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45043089844) | Release status watch | schedule | success (monitor job only) |
| [45041443776](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45041443776) | S-BIAD634 zero-shot transfer | workflow_run | success |
| [45039935869](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45039935869) | S-BIAD634 zero-shot transfer | workflow_run | success |
| [45033447021](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45033447021) | CI | push | success |
| [45033447025](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45033447025) | Pages deployment | push | success |

## Public E2E #303 — current-main SHA, blocked before upload

Run [45043763018](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45043763018), job [137273705796](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45043763018/job/137273705796), is a failure on exact main.

- Published UI preflight: HTTP 200.
- Render health: 4 ReadTimeout attempts, then HTTP 200 on attempt 5 (7.862 seconds).
- Diagnostic retained `api_health_request_error=ReadTimeout` despite recovery; this is a stale error-state bug in the E2E diagnostic.
- `checkpoint_available=true` is not digest verification.
- Render branch: main; Render commit: `bb6a9d27537e12b85768c7fead1467253b2423ba`.
- Render comparison: `ahead`; parity false. The diff includes research scripts and actual webapp mismatches; no public job was created.
- No guest token, job ID, upload, inference, specialist output, report/export, or cleanup.

Failure artifact [14762747641](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45043763018/artifacts/14762747641) was downloaded, ZIP-tested and JSON-parsed; it contains JSON only, no source image.

- ZIP SHA-256: `09d587885b12e5e48b915e74a5c2e702502edd8f9577915a9857b51885409714`.
- Extracted `live-agent-e2e-failure.json` SHA-256: `6bbc87faa1e4f3bd6e0c420932c93a5e8da7408e1f9d724ed035dc34c8a11d28`.
- Extracted JSON size: 3,651 bytes.

## Watchdog #131

Run [45049473842](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45049473842), job [137291187131](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45049473842/job/137291187131), completed successfully. Its log says: `current-main E2E is recent (3677 seconds old)`. Dispatch was suppressed. The watchdog source on current main still lacks the pre-dispatch Render SHA and checkpoint digest gate. A successful watchdog conclusion is not an inference result.

## PR #187 — public E2E trigger guard

[PR #187](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/pull/187), head `47d4bdf0b1fb111ac865d6cb360dcdc95cc929a2`, base current main `b8d4a3b015cfcff56201b889702dc0ce7ee83e4f`, remains draft.

- CI [45045185704](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45045185704): tests job succeeded.
- E2E validation [45045185706](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/45045185706): PR harness syntax and workflow YAML validation succeeded; public-upload job was skipped.
- Changed files: `.github/workflows/live-public-agent-e2e.yml`, `tests/test_live_public_agent_e2e_workflow.py`.
- Full two-file patch reviewed. Guard restricts public job to upstream repo, non-PR event and `refs/heads/main`; PR validation compiles the harness and parses YAML offline.
- Fresh E2E failure evidence was added to the PR conversation. No merge.

## M1 follow-up

PR #92 remains stale-base (base `d4a653e...`, head `838b89d51cae3db2171bc67b0c2389c043b34122`). Its full patch was reviewed against current-main watchdog source. It adds a bounded health retry, GitHub server-time freshness, upstream-only scheduled job, exact Render main SHA and immutable checkpoint digest preflight, and tests for stale/unverified runtime. Current health data does not yet prove the pinned digest; this guard should suppress dispatch until the contract is available. No code was cherry-picked or merged.

PR #95 is stale and overlaps the new #187 guard. #103/#104/#105/#92 remain an unintegrated runtime/auth/parity/checkpoint stack. Do not merge stale stacked branches as a bundle without rebasing and reviewing each diff.

## Evidence tiers and milestone decision

- Repository/API/workflow/job logs and parsed artifact: repository/CI evidence.
- Runner checkpoint workers and research metrics: runner-only; not public inference.
- Public upload-to-inference: **not demonstrated**.
- M0 remains partial: recent baseline evidence is reproducible, but Actions page 1 only, incomplete open-PR diff audit, and inaccessible branch-protection endpoint prevent complete baseline acceptance.
- M1 remains blocked: PR #187 is CI-green but draft/unmerged; watchdog runtime/checkpoint gate is not on main.
- M2 remains blocked: current-main fresh provenance and final E6/E7 evidence chain are not accepted.
- M3–M7 remain unaccepted.

## Deadline risk and next safe action

Deadline 2027-01-01 remains high risk. Next: reconcile #187 and #92/#104/#105 on current main, validate exact-head CI, and verify checkpoint/runtime contract before any authorized public E2E. No Render workspace, deployment, public upload, or merge was performed.
