# Worker 3 findings

- Read-only VPS evidence was collected with `/opt/ai-loop/bin/vps-ssh`; no remote state was changed.
- At `2026-09-13 14:38:22 UTC`, the automation logged `CANDIDATE_SIMULATION_RESULT=FULL_SUCCESS exit=0` and the full workflow completed successfully.
- At `14:38:23 UTC`, staging passed with `simulation_production_authority_mutations=0`; the promotion boundary acquired `/tmp/bot_trad_run_trade_v5_bot_trading_gru.lock` and passed the exact-process gate (`exact_trade_v5_processes=0`).
- The promotion automation reset `feature/GRU` to `origin/feature/GRU`; the resulting checkout reported `HEAD is now at d4960be fix(gru): make raw payload persistence unicode-safe`.
- Exact SHA: `d4960be98cee3edef96413ee77f200ce744d3461`. Independent readable artifacts also record it as `expected_sha` and `remote_feature_gru_sha`.
- Follow-on validation at `14:38:25-26 UTC` passed: 51 GRU tests, 15 CI-breaker tests, and the model quality verdict was `PASS`.

Evidence paths on VPS:

- `journalctl` system journal, queried for `2026-09-13 14:38:20..14:38:30 UTC` (automation process IDs 3638697, 3639302, 3716674, 3716679, 3716688, 3716750, 3716751).
- `/tmp/bot_trad_deploy_logs_1000/runtime_logs/` (runtime logs; includes SHA-named replay/shadow artifacts).
- `/home/githubactions/.local/state/bot-trading-gru-full-corpus/results/semaphore-18-d4960be98cee/candidate_source.json` (`expected_sha`, `remote_feature_gru_sha`, worktree path).
- `/home/githubactions/.local/state/bot-trading-gru-full-corpus/results/semaphore-18-d4960be98cee/worker.status` (`sha=...`).
- `/home/githubactions/.local/state/bot-trading-gru-full-corpus/results/semaphore-18-d4960be98cee/full_corpus_train_acceptance.json` and `runtime_logs/payload_validation.json` (exact expected SHA).

Note: the historical worktree path referenced by the logs was no longer present when inspected; no claim is made from a live checkout, only from journal and retained result artifacts.
