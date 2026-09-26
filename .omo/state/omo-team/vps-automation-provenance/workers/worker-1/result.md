# Worker: worker-1
## Task
Read-only VPS inspection of cron/systemd automation for `/opt/bot_trad/bot_trading_gru`, `feature/GRU`, git/deploy/sync/restart references, and exact SHAs.

## Findings

- **VPS/evidence:** All remote commands used `/opt/ai-loop/bin/vps-ssh '<remote command>'`; host `Auto-Install-Ubuntu-Server-22`, executed as root. No mutations or external-system queries.
- **Repository:** `/opt/bot_trad/bot_trading_gru` is on branch `feature/GRU`; `HEAD=d4960be98cee3edef96413ee77f200ce744d3461`. `refs/remotes/origin/feature/GRU=2d429e66d185241e0efda9f3385f5aea55b65f5d`; status says local branch is behind 5 commits and has untracked files.
- **Active cron:** `githubactions` runs every minute: `/home/githubactions/.local/state/bot-trading-gru-full-corpus/worktrees/full-corpus-v2-2d429e66d185-2d429e66d185241e0efda9f3385f5aea55b65f5d/ops/ci/supervise_gru_full_corpus.sh`. The worktree path embeds SHA `2d429e66d185241e0efda9f3385f5aea55b65f5d`.
- **Root cron:** GRU simulation/trade entries are commented out (`run_simulation_cycle.sh` and `trade_v5.sh` with `BOT_TRAD_MODEL_MODE=gru`); no active root GRU trade/simulation cron was found. Other active root cron jobs are unrelated maintenance/trading jobs.
- **Recurring systemd:** `gru-monitor-reconciler.timer` is enabled and runs every minute. Its service works in `/opt/bot_trad/bot_trading_gru`, runs orphan-remediation and monitor-coverage scripts, and is runtime reconciliation (not git deployment). `bot-ci-breaker.timer` is enabled and runs every five minutes; service invokes CI circuit-breaker reconciliation, with no SHA/path in unit metadata.
- **Enabled runtime service:** `bot-trading-gru-simulator-frontend.service` uses `/opt/bot_trad/bot_trading_gru/apy/simulation`, `Restart=always`; no git/deploy/branch/SHA reference.
- **On-demand acceptance:** `gru-p2-acceptance.service` is disabled (historical transient instances exist), runs as `githubactions` in `/opt/bot_trad/bot_trading_gru` through `run_gru_p2_worker_wrapper.sh`, and has checkout write access; classify as acceptance/deployment support, not recurring automation.
- **Repository CI automation:** `.github/workflows/sync-feature-gru-server.yml` states Semaphore is the only automatic production deploy owner for `feature/GRU`; it invokes `ops/ci/deploy_feature_gru_remote.sh`. That script performs fetch, exact-SHA checks, branch checkout, monitor/breaker service starts, and final SHA verification. These are CI-triggered workflow actions, not local cron/systemd scheduling. `.github/workflows/autoupdate_server.yaml` contains fetch/clone and systemd restart paths, likewise workflow definitions rather than local scheduler evidence.

## Commands / evidence

1. `/opt/ai-loop/bin/vps-ssh 'crontab -u root -l; crontab -u githubactions -l; grep -RInE "bot_trad|feature/GRU|git|deploy|sync|restart|[0-9a-f]{7,40}" /etc/cron* /var/spool/cron'`
2. `/opt/ai-loop/bin/vps-ssh 'systemctl list-unit-files --type=service --type=timer; systemctl list-timers --all; systemctl cat bot-ci-breaker.service bot-ci-breaker.timer gru-monitor-reconciler.service gru-monitor-reconciler.timer gru-p2-acceptance.service'`
3. `/opt/ai-loop/bin/vps-ssh 'git -C /opt/bot_trad/bot_trading_gru branch --show-current; git -C /opt/bot_trad/bot_trading_gru rev-parse HEAD refs/remotes/origin/feature/GRU; git -C /opt/bot_trad/bot_trading_gru status --short --branch'`
4. `/opt/ai-loop/bin/vps-ssh 'grep -RInE "feature/GRU|git (checkout|pull|fetch|rev-parse)|systemctl (restart|start|stop)|deploy|rsync|/opt/bot_trad/bot_trading_gru" /opt/bot_trad/bot_trading_gru/ops /opt/bot_trad/bot_trading_gru/.github'`

## Classification

| Surface | Classification | SHA |
|---|---|---|
| `githubactions` per-minute full-corpus cron | Recurring supervisor/dispatch | `2d429e66d185241e0efda9f3385f5aea55b65f5d` |
| Root GRU cron lines | Disabled/commented | None |
| `gru-monitor-reconciler.timer` | Recurring monitor reconciliation | None observed |
| `bot-ci-breaker.timer` | Recurring CI circuit-breaker/deployment control | None observed |
| `gru-p2-acceptance.service` | Disabled/on-demand acceptance support | None in unit metadata |
| Production checkout | Current deployed repository state | `d4960be98cee3edef96413ee77f200ce744d3461` |

## Recommendations

- Treat the `githubactions` minute cron and the two enabled timers as the local automation surfaces.
- Investigate the five-commit divergence separately; current checkout does not match its remote-tracking `feature/GRU` SHA.
