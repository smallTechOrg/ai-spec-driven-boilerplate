# Secret Hygiene

The harness rule is in [harness/rules/secret-hygiene.md](../../harness/rules/secret-hygiene.md).
This file records project-specific conventions.

---

## What counts as a secret in this project

Any field whose name matches `*_token`, `*_secret`, `*_password`, `*_key`, or
`*_credential`. Treat all LLM API keys, DB credentials, and OAuth tokens as secrets.

## Where secrets live

| Location | Allowed? |
|----------|----------|
| `.env` | Yes — primary store |
| OS environment | Yes |
| Source code | Never — including tests |
| Git history | Never |
| Logs, commit messages, PRs | Never |

## Code rules

- Never log a secret value — log `token_present=bool(token)` instead
- Never include secrets in exception messages
- Never `print()` or `repr()` a config object that may contain secrets
- Config models use the framework's secret type (e.g. pydantic `SecretStr`) for raw values;
  call `.get_secret_value()` only at the boundary where the secret is actually used

## On commit

Before every commit, scan the diff for strings that look like tokens (length > 20,
alphanumeric mix, prefixes like `sk-`, `gsk_`, `ghp_`). If anything matches — stop,
do not commit, rotate the secret.

## If a secret leaks

1. Rotate immediately at the provider
2. Purge from git history (`git filter-repo` / `bfg`) — force-push with operator approval
3. Note the incident in the commit message without repeating the value
