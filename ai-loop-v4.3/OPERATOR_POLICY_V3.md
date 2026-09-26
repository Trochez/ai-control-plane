# ai-loop v3 operator policy — v3.35

OpenCode is a controller-authorized operational operator. It may enter the target repository for status, synchronization, tests, builds, diagnostics, isolated exact-SHA reproduction, and other explicitly authorized work GPT Web cannot physically perform. It must not independently choose fixes, implement application changes, commit, push, declare GO, or modify production.

The controller must provide an explicit target, branch, operation, and side-effect authorization for mutations. Destructive reset/clean, arbitrary branch changes, force push, and browser navigation owned by Browser Broker are forbidden. Browser Broker remains the exclusive ChatGPT browser owner.

## Semantic vs effect authority

AI may interpret unstructured information and propose canonical events. It never proves that file exists, selects artifact bytes, or causes lifecycle transition by assertion alone. deterministic controller validates every effect and transition.

## Browser transport

- Semantic/UI interpretation uses serialized local `opencode run` with Playwright MCP.
- Physical remediation-plan acquisition does **not** use Luna/OpenCode. It uses controller-owned deterministic Node Playwright worker.
- Only one process may own dedicated browser profile at time; both paths share same controller lock.
- Cookies and authenticated sessions are preserved.


## ChatGPT product/model policy

Every authoritative ChatGPT Web delivery uses **normal Chat only**. Work and Codex are forbidden surfaces for ai-loop implementation channel.

Before every message that can mutate or advance implementation workflow, browser transport must prove from live UI:

- surface: `Chat`;
- model: `GPT-5.6 Sol`;
- reasoning: `High`.

`GPT-5.6 Sol Light`, Instant, Medium, Work, Codex, Astra-through-Work, or any unknown/unreadable selector state are fail-closed conditions. transport may switch UI back to Chat and select Sol High without sending message, but it may not destroy or replace registered conversation to do so. message sent without verified policy PASS is protocol violation.

## Downloadable plan artifact invariant

remediation plan is authoritative only when GPT-5. 6 Sol provides real downloadable `.md` artifact and deterministic controller physically acquires and verifies its bytes.

Internal ChatGPT `msg:<uuid>` values and any single DOM attribute are advisory only. v3. 35 discovers physical turns from multiple independent container, role, metadata, and artifact signals. real `.md`/Download/file-card signal may be used as deterministic fallback only inside already controller-approved `PLAN_READY` recovery lane. Physical acquisition is zero-click first: inspect element attributes/URLs, already-open raw preview resources, performance resources, and http/https/blob/data/sandbox schemes before any visible interaction. Network/DOM bodies are candidates only: metadata/JSON/short bodies must never be promoted as plan. At most one visible artifact interaction is allowed per worker run. Ambiguity or absence of controller-valid plan body blocks execution.

Inline text, snapshots, code blocks, Base64, chunks, or model-transcribed content are forbidden substitutes. controller independently verifies size, UTF-8, plan structure, SHA-256, and lifecycle guards before transitioning to `IMPLEMENTING`.

## DOM diagnostics invariant

If physical-turn discovery fails, worker must return structural diagnostics (turn/article/role/artifact counts and page identity) rather than silently retrying or asking model to guess selectors.

## State authority

Model statements such as `PLAN_READY`, `CI_SUCCESS`, or `GO` are proposal-only. Deterministic invariants remain mandatory.


## v3 adaptive browser policy
- Browser navigation may be model-guided from live DOM/ARIA/HTML, but model's prose or JSON is never authoritative proof.
- Only nonce-bound `playwright_browser_run_code` verifier output may authorize bootstrap/policy transitions.
- plan send requires deterministic fresh-empty-project preflight, browser-local idempotency ledger, deterministic composer+attachment pre-send gate, then one Send click.
- Work and Codex remain forbidden; required normal Chat model is GPT-5. 6 Sol with High reasoning.
- Any unresolved UI state must fail closed and persist controller-owned diagnostics under run browser/adaptive directory.
