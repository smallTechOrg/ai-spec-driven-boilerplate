---
name: deploy
description: Deploy a built, reconciled, qa-signed-off system. A later phase; default target Render. Use when the build is complete and the user wants it live.
---

# deploy

Run the Zer0 deploy workflow. The authoritative procedure is
`harness/workflows/deploy.md` — read it and follow it.

Deploy only after all build phases are green and the loop is closed. Default target:
Render. Confirm the run command/port from `spec/engineering/tech-stack.md`, add the
deploy manifest, set env vars in the platform (never commit secrets), deploy, and have
the analyst confirm runtime behavior matches the spec.
