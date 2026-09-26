# ai-loop v4.3 Policy Increment Result

Status: `BLOCKED_EXTERNAL`

## Implemented

- Added isolated `chat-policy-v4.3.cjs` with a versioned strict Chat policy, exact model/reasoning resolution, typed policy failures, policy hashing, and fail-closed proof validation.
- Added an offline regression for exact selection, `MODEL_SOL_OPTION_NOT_FOUND`, ambiguous matches, wrong surface, missing High reasoning, and proof binding.
- Added `bin/verify-v4.3-local` and documented that it is offline-only.
- Preserved the v4.2 controller, broker entrypoints, and `4.2.0` selftest contract.

## Verified locally

- `./bin/verify-v4.3-local` — PASS
- `./bin/verify-v4.2-local` — PASS
- `git diff --check` for the changed v4.3 files — PASS
- Branch: `main`
- HEAD: `6e6d377dae2a9400357d0cd03c6836a17f05c41b`

## External blockers

The full v4.3 acceptance contract was not claimable in this environment. The following remain unverified or unavailable: live `/opt/ai-loop` runtime and `/var/lib/ai-loop` evidence, authenticated Chrome/ChatGPT session, original incident DOM artifacts, GitHub write access, Semaphore, VPS/deployment, and live canaries. Therefore live gates T38–T42, installation validation, and `FULL_LOOP_ACCEPTED` are `BLOCKED_EXTERNAL`.

Unrelated existing worktree modifications and untracked archives/artifacts were preserved.
