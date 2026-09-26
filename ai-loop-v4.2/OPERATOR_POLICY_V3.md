# ai-loop v3 operator policy — v3.35

OpenCode is transport/operator only. It must not implement fixes, diagnose failures, create remediation plans, commit, push, declare GO, or modify CI/repository state.

## Semantic vs effect authority

AI may interpret unstructured information and propose canonical events. It never proves that a file exists, selects artifact bytes, or causes a lifecycle transition by assertion alone. The deterministic controller validates every effect and transition.

## Browser transport

- Semantic/UI interpretation uses serialized local `opencode run` with Playwright MCP.
- Physical remediation-plan acquisition does **not** use Luna/OpenCode. It uses the controller-owned deterministic Node Playwright worker.
- Only one process may own the dedicated browser profile at a time; both paths share the same controller lock.
- Cookies and authenticated sessions are preserved.


## ChatGPT product/model policy

Every authoritative ChatGPT Web delivery uses **normal Chat only**. Work and Codex are forbidden surfaces for the ai-loop implementation channel.

Before every message that can mutate or advance the implementation workflow, the browser transport must prove from the live UI:

- surface: `Chat`;
- model: `GPT-5.6 Sol`;
- reasoning: `High`.

`GPT-5.6 Sol Light`, Instant, Medium, Work, Codex, Astra-through-Work, or any unknown/unreadable selector state are fail-closed conditions. The transport may switch the UI back to Chat and select Sol High without sending a message, but it may not destroy or replace the registered conversation to do so. A message sent without a verified policy PASS is a protocol violation.

## Downloadable plan artifact invariant

A remediation plan is authoritative only when GPT-5.6 Sol provides a real downloadable `.md` artifact and the deterministic controller physically acquires and verifies its bytes.

Internal ChatGPT `msg:<uuid>` values and any single DOM attribute are advisory only. v3.35 discovers physical turns from multiple independent container, role, metadata, and artifact signals. A real `.md`/Download/file-card signal may be used as a deterministic fallback only inside an already controller-approved `PLAN_READY` recovery lane. Physical acquisition is zero-click first: inspect element attributes/URLs, already-open raw preview resources, performance resources, and http/https/blob/data/sandbox schemes before any visible interaction. Network/DOM bodies are candidates only: metadata/JSON/short bodies must never be promoted as the plan. At most one visible artifact interaction is allowed per worker run. Ambiguity or absence of a controller-valid plan body blocks execution.

Inline text, snapshots, code blocks, Base64, chunks, or model-transcribed content are forbidden substitutes. The controller independently verifies size, UTF-8, plan structure, SHA-256, and lifecycle guards before transitioning to `IMPLEMENTING`.

## DOM diagnostics invariant

If physical-turn discovery fails, the worker must return structural diagnostics (turn/article/role/artifact counts and page identity) rather than silently retrying or asking the model to guess selectors.

## State authority

Model statements such as `PLAN_READY`, `CI_SUCCESS`, or `GO` are proposal-only. Deterministic invariants remain mandatory.


## v3 adaptive browser policy
- Browser navigation may be model-guided from live DOM/ARIA/HTML, but the model's prose or JSON is never authoritative proof.
- Only nonce-bound `playwright_browser_run_code` verifier output may authorize bootstrap/policy transitions.
- A plan send requires deterministic fresh-empty-project preflight, browser-local idempotency ledger, deterministic composer+attachment pre-send gate, then one Send click.
- Work and Codex remain forbidden; required normal Chat model is GPT-5.6 Sol with High reasoning.
- Any unresolved UI state must fail closed and persist controller-owned diagnostics under the run browser/adaptive directory.
