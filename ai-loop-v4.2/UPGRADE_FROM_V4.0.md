# Upgrade ai-loop v4.0 -> v4.1

v4.1 replaces one-shot/split browser ownership with a persistent deterministic browser broker and fixes the v4.0 false `FRESH_PROJECT_WRONG_PROJECT` failure when ChatGPT shows `New chat in Bot_trading` at a generic `chatgpt.com` URL.

## Major changes

- `browser-broker-v1.cjs` owns the ChatGPT browser profile for the run.
- project identity is multi-signal (`TARGET|OTHER|UNKNOWN`) rather than URL-only.
- a generic ChatGPT URL is neutral; `New chat in Bot_trading` + target project link evidence can prove the project.
- OpenCode becomes text-only for semantic classification/action selection.
- exact code blocks are materialized by the broker and SHA/length checked before execution.
- plan artifact downloads and Semaphore read-only evidence use the same broker.
- Chat/Sol/High must be positively re-read after selection.
- attachment proof is bound to the active composer/file input.
- normal browser waits are condition-driven.
- startup send interval defaults are reduced to remove the previous multi-minute idle latency while preserving rate-limit backoff.

## Important acceptance status

The package includes deterministic/local tests and a 100-cycle synthetic control-plane soak. The live G10/G11 gates from the implementation plan require the target WSL/browser/GitHub/VPS/Semaphore environment and must be run there before declaring the remediation operationally complete.

## Upgrade

1. Stop all existing loop/controller/browser processes.
2. Extract the bundle.
3. Run `./bin/verify-v4.1-local`.
4. Run `./install.sh`.
5. Run `/opt/ai-loop/bin/preflight-v4.1 <PLAN>`.
6. Run the safe live canary first (`AI_LOOP_FULL_ACCEPTANCE_20260922T0155-0500.md`).
7. Only after the safe canary reaches FINAL_GO, run the real remediation plan.

See `README.md` for exact commands.
