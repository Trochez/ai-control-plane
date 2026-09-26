# Worker: worker-2
# Task: scripts hooks and checkout artifacts

## Summary
Read-only VPS inspection completed via `/opt/ai-loop/bin/vps-ssh`; no remote or local deployment state was mutated. The VPS contains an SHA-fenced GRU deployment engine, remote inventory/sync tooling, runtime SHA markers, and a recovery backup directory. Current checkout and marker provenance disagree with the configured remote-tracking ref.

## Findings

### Target checkout and exact SHAs
- Primary target: `/opt/bot_trad/bot_trading_gru`.
- Branch: `feature/GRU`; `HEAD=d4960be98cee3edef96413ee77f200ce744d3461`.
- `refs/remotes/origin/feature/GRU=2d429e66d185241e0efda9f3385f5aea55b65f5d`; checkout is behind 5 commits.
- Checkout has untracked deployment/recovery/evidence artifacts, but no tracked-file dirtiness was reported.
- Runtime marker `/tmp/bot_trad_feature_gru_sync_verified.sha` contains `d4960be98cee3edef96413ee77f200ce744d3461`.
- Runtime status says `DEPLOYED_PENDING_LIVE_ACCEPTANCE`, engine `circleci`, timestamp `2026-09-14T17:37:54Z`; deploy-engine marker contains the same SHA.
- Other observed checkouts: `/opt/bot_trad/bot_trading` at `c766a9ae12bf2ea2e90f25f81b524dc5d49376e4`; `/opt/bot_trad/bot_trading_ensemble` at `a9899003c7a7b725994b2b12ea71f2c10518ac32`.

### Deployment/sync capability
- `ops/ci/deploy_feature_gru_remote.sh` requires `EXPECTED_SHA` and `REPOSITORY`, fetches only `feature/GRU`, requires fetched remote SHA to equal `EXPECTED_SHA`, stages via detached worktree, runs compile/shell/unit/release/simulation gates, then promotes with deployment and cycle locks.
- Promotion uses `git checkout -B feature/GRU refs/remotes/origin/feature/GRU` followed by `git reset --hard EXPECTED_SHA`; failure invokes rollback to the prior SHA.
- Post-promotion verification requires branch, `HEAD`, origin ref, and sync marker all equal `EXPECTED_SHA`, with no tracked-file dirtiness.
- It writes the sync, release-status, and deploy-engine markers atomically and starts the breaker reconciliation only after verification.
- `apy/tests/run_simulation_v2_remote_inventory.sh` can inspect a remote checkout's SHA/branch/dirty state/process state against a target manifest.
- `apy/tests/run_simulation_v2_remote_sync.sh` supports no-op when SHAs match; otherwise fetches, checks out detached `FETCH_HEAD`, verifies resulting SHA, and attempts rollback to the saved SHA on mismatch/failure. It explicitly warns that it may proceed with `FETCH_HEAD` if it differs from the target SHA.
- `apy/run_identity.sh` resolves identity from live Git `HEAD` first, then the sync marker; this is capability, not evidence that it was run successfully during this inspection.

### Hooks and recovery artifacts
- No non-sample Git hooks were found under `/opt/bot_trad`; only standard `.sample` hooks exist.
- `/opt/bot_trad/bot_trading_gru/.deploy-backup-recovery-20260824T103038Z` exists, owned by `githubactions`, containing three files: `binanceOp.py`, `monitoring_portfolio_symbol.py`, and `sync_portfolio_monitors.py`.
- Backup SHA-256 values: `binanceOp.py=a9c0e73b8febf498fca7692dfbc44ede3649f35b0dd85db477deb993bc67be83`; `monitoring_portfolio_symbol.py=2e2b14a285ed89ec23987bd05eb3526ff0e21786eab45259696a37d554e6060e`; `sync_portfolio_monitors.py=a97dcfa803a825fd3fa3302a895b1e73c72b7b092483693380f94c1941b2ac90`.
- No backup manifest or embedded source commit SHA was present in that directory.
- `ops/recovery_rebuy/release_manifest.py` is capable of producing/verifying a secret-free manifest binding Git SHA, branch/dirty state, and file SHA-256 values; no generated recovery manifest was found in the inspected backup directory.

## Capability versus execution
- **Capability confirmed:** scripts implement SHA-fenced fetch/staging/promotion, lock-based serialization, rollback, marker writes, remote inventory/sync, and recovery manifest verification.
- **Execution evidence confirmed:** current checkout SHA, remote-tracking SHA, runtime marker contents, release status, deploy engine marker, reflog, service definitions, and backup file hashes were read from the VPS.
- **Not proven by this inspection:** that the deployment script or sync script successfully executed for the current checkout; that the current `HEAD` matches the remote branch; that live acceptance completed; or that backup files were restored/used. The marker explicitly remains `DEPLOYED_PENDING_LIVE_ACCEPTANCE`.

## Files Modified
- `.omo/state/omo-team/vps-automation-provenance/workers/worker-2/result.md` only.

## Recommendations
- Treat `d4960be...` as the last recorded deployed/marker SHA, not as proof of current remote provenance; independently reconcile against expected target SHA before any mutation.
- Preserve and inspect the untracked `.deploy-backup-recovery-20260824T103038Z` artifacts and their hashes as recovery evidence; do not infer their source commit without a manifest.
