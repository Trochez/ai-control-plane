# Diagnosis — R20260922T040029 / ai-loop v4.2

## Evidence inspected

production diagnostics archive contained JSON/HTML/screenshot emitted by:

- `ENSURE_FRESH_PROJECT_DRAFT`
- `ENSURE_CHAT_POLICY`

No user message had been sent before failure.

## Finding 1 — project-name parsing was still wrong

target URL is:

`https://chatgpt.com/g/g-p-68782097d6388191b7538c01b189cce8-bot-trading`

but v4. 2 diagnostic recorded:

`projectName = trading`

old parser used greedy opaque-id expression and consumed `-bot`, leaving only `trading`.

At same time, real UI exposed both:

- composer `aria-label="New chat in Bot_trading"`
- project selector `aria-label="Change project: Bot_trading"`

Therefore first v4. 2 fresh-draft attempt incorrectly classified valid project draft as `UNKNOWN` even though UI positively identified target project.

## Finding 2 — the current Chat UI no longer exposes a literal Sol option in the standard Chat composer

real DOM showed:

- selected surface: `Chat`
- model/reasoning trigger: `aria-label="Select ChatGPT model"`
- `data-composer-navigation-target="reasoning"`
- `data-selected-reasoning-effort="high"`
- visible trigger text: `High`

v4. 2 broker instead required selected control matching literal text `GPT-5.6 Sol`. It clicked reasoning trigger and then searched for that literal option. menu did not contain such item, so it raised:

`MODEL_SOL_OPTION_NOT_FOUND`

This was controller/UI-contract mismatch, not evidence that Sol was unavailable.

## Product contract used by v4.3

current standard Chat product exposes reasoning slider rather than separate Sol/Luna/Terra selector. On eligible paid Chat plans, `Medium` and `High` are powered by GPT-5. 6 Sol; `High` is mandatory ai-loop policy.

Therefore v4. 3 proves required model policy as:

`normal Chat selected + reasoning control selected at High => GPT-5.6 Sol / High`

controller still fails closed if Chat is not selected or High cannot be positively proven.

## v4.3 remediation

1. Parse project slug after full opaque project id, producing `bot_trading` instead of `trading`.
2. Add `Change project: Bot_trading` as strong active-project signal.
3. Persist `data-composer-navigation-target`, `data-selected-reasoning-effort`, and related control metadata in browser observations.
4. Replace mandatory literal `GPT-5.6 Sol` menu search in current standard Chat with reasoning-slider policy verifier.
5. Keep explicit-model fallback for legacy UI variants.
6. Preserve fail-closed behavior: selected Chat + selected High + Sol policy proof are all required before attachment or Send.
7. Add exact regression tests derived from R20260922T040029.
