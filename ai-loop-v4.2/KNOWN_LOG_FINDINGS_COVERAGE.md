# ai-loop v4.0 — observed failure coverage

| Observed failure | v4.0 handling |
|---|---|
| `ADAPTIVE_PLAYWRIGHT_PROOF_MISSING` although browser performed actions | Bootstrap/send no longer parse OpenCode CLI transcript; direct Node worker returns JSON to Python |
| Model selector `menuitemradio[aria-checked=true]` missing | Semantic multi-role selection; exact Sol option click is accepted as deterministic action evidence |
| `playwright_browser_file_upload` requires modal | Retired from sender; direct `setInputFiles()` or Playwright `filechooser` |
| 15–20 minute bootstrap with no verified send | LLM removed from bootstrap; direct local worker; maximum two pre-click attempts |
| Model clicked Send before proof | Retired; only direct worker owns Send |
| Proof missing after possible click caused ambiguous state | No resend; direct read-only observer only |
| Recovery itself failed with `ADAPTIVE_PLAYWRIGHT_PROOF_MISSING` | Recovery observer is direct Node/Playwright and model-free |
| Old ambiguous delivery blocks a new run | Prior-run ambiguity remains quarantined; new loop never adopts old chat |
| Old `/c/` restored on project navigation | Direct worker requires zero conversation turns before attachment/send |
| Wrong Work/Codex surface | Direct policy worker switches/rejects before write |
| Sol model not visible in closed header | Direct worker opens model control and selects exact `GPT-5.6 Sol` semantically |
| High reasoning selection | Direct worker verifies visible/selected High or selects it |
| Base64/UTF-8/SHA action corruption | Existing DOM/file action payload + SHA/length architecture preserved |
| implicit local→VPS route | Existing strict route ownership preserved |
| missing capabilities / transient GitHub | Existing preflight and bounded network retries preserved |
