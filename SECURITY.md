# Security policy

Codex Island is an early Linux desktop project. Fixes target the current `main`
branch and the latest published release; older releases do not have a separate
maintenance commitment.

## Reporting vulnerabilities

Use **Security → Advisories → Report a vulnerability** on the GitHub repository
when private vulnerability reporting is enabled. If that option is unavailable,
open a minimal issue requesting a private reporting channel without exploitation
details. Never post credentials, terminal transcripts, tokens or private paths.

Maintainers should enable GitHub private vulnerability reporting before public
launch. No response-time guarantee is currently offered.

## Boundaries

- Codex CLI owns sign-in, history, permissions and its own execution sandbox.
- The app does not save terminal transcripts or authentication data.
- Completion notifications discard prompts and assistant responses.
- Docker controls use a local Unix socket and the current user's daemon access.
- Port stops require same-user ownership and fresh process/listener identity
  checks. The app and its terminal process tree are protected.
- A GUI confirmation is required before stopping a selected service.
- There is no remote control server, sudo button, or terminal force-stop control.

Avoid importing untrusted patches or copying secrets into public bug reports.
