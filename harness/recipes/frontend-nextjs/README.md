# Recipe: frontend-nextjs

A generic, domain-neutral **agent chat UI** — plain **JavaScript** Next.js (App Router),
no TypeScript toolchain so a non-coder can read and edit it without a TS build to learn.
Message in → response out: type a message, the backend runs its agent, the answer renders
as markdown. It is **streaming-ready** (the `send()` flow is a single localized swap away
from an SSE/streaming reader) and ships a visible **stub banner** so a placeholder backend
never reads as "broken".

Runs **green out of the box**: `npm install && npm run build` passes with no backend, no
keys, no business domain. The shipped agent is the generic **echo** example — replace it
(and the example tool on the backend) with your real capability.

**Stamped 2026-06-22.**
Stack: `next` 15.5.19 · `react` 19.1.0 · `react-dom` 19.1.0 · `react-markdown` 10.1.0 ·
`remark-gfm` 4.0.1 · `tailwindcss` 3.4.17 (+ `postcss` 8.5.15, `autoprefixer` 10.4.21).
(`next` is pinned to 15.5.19 — the patched line that clears CVE-2025-66478 and the
Image/middleware advisory chain; re-prove green before re-stamping when these move — see
`../README.md` § re-sync.)

---

## What's here

```
package.json         deps + dev/build/start/lint scripts
package-lock.json    committed lockfile — npm install reproduces what was proven green
next.config.js       rewrites /api/* → ${NEXT_PUBLIC_API_URL}/* (same-origin proxy, no CORS)
tailwind.config.js   content globs for app/
postcss.config.js    Tailwind 3 PostCSS pipeline (tailwindcss + autoprefixer)
jsconfig.json        baseUrl + @/* import alias
.gitignore           node_modules/, .next/, out/, *.log, .env*.local
.env.local.example   NEXT_PUBLIC_API_URL=http://localhost:8000

app/
  layout.js          root layout — metadata.title 'appname', Tailwind body shell
  globals.css        the three @tailwind directives
  page.js            'use client' + dynamic(import("./ChatApp"), { ssr:false })
  ChatApp.js         the chat client — Message + MessageList + InputBar + Page
```
`node_modules/` and `.next/` are gitignored — they regenerate from `npm install` /
`npm run build`.

## Quickstart

```bash
npm install
npm run build        # smoke gate — passes offline, no backend needed
npm run dev          # Next dev server (default :3000). Backend should be up on :8000.
```
`npm run build` is the smoke gate: it compiles the whole app with no backend. For a live
UI the backend agent must be running on **:8000** (both python recipes serve there) — the
UI proxies `/api/*` to it via `next.config.js` rewrites, so a UI with a dead backend is the
#1 false "it's broken" report. `npm run start` runs the production build.

## The four UI states

`ChatApp.js` renders exactly four states; keep them all when you adapt it:

| State | Trigger | What renders |
|---|---|---|
| **1 — empty** | no messages, not sending | "Send a message to the agent. This is a stub — replace the example tool and wire a real LLM." |
| **2 — sending / loading** | request in flight | animated `···` bubble; input + Send disabled |
| **3 — response** | `{ ok:true }` returned | assistant message rendered via react-markdown |
| **4 — error** | request failed / `ok:false` | red card with the message and a **Retry** button |

A **Stub mode** banner sits above all four when the backend's `/health` reports
`stub_mode: true` (fetched once on mount).

## The contract (served by BOTH python recipes)

The UI is decoupled from the backend by a stable two-endpoint contract. Both python
recipes serve it; do not drift either side.

```
POST /api/run      body { "input": <text> }
                   → { "ok": true, "data": { "result": <string>, "run_id": <id> } }
                   → { "ok": false, "error": <string> }            (UI shows state 4)

GET  /api/health   → { "stub_mode": <bool>, ... }                  (drives the banner)
```

No `goal` / `dataset_id` / `chart_spec` / `cost` / `thread` fields — those were
data-analysis-specific and are gone. The browser hits the relative `/api/*` path; the
rewrite in `next.config.js` forwards it to the backend.

## `NEXT_PUBLIC_API_URL`

The backend base is read from **`NEXT_PUBLIC_API_URL`** (default **`http://localhost:8000`**)
and is **actually read by the code** — `next.config.js` builds the rewrite destination from
it:
```js
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
// rewrite: /api/:path*  ->  ${API_URL}/:path*
```
Copy `.env.local.example` to `.env.local` to override it (e.g. a different port or host).
Any browser-read var MUST be `NEXT_PUBLIC_`-prefixed or it is `undefined` client-side. The
client code itself only ever calls the relative `/api` path, so it stays CORS-free; the env
var lives at the proxy layer.

## Rename the project

One placeholder token renames the whole UI:

- **`appname`** (lowercase) — the project/package name. Appears in `package.json` `name`
  (`appname-ui`) and `app/layout.js` `metadata.title`/`description`.
- **`APPNAME`** (uppercase) — env-var prefix, used by the python recipes only. The UI reads
  `NEXT_PUBLIC_API_URL` (not `APPNAME`-prefixed, since it is client-side).

From the project root, after copying the recipe in:
```bash
# macOS:
grep -rl 'appname\|APPNAME' . | xargs sed -i '' 's/APPNAME/MYAPP/g; s/appname/myapp/g'
# linux:
grep -rl 'appname\|APPNAME' . | xargs sed -i 's/APPNAME/MYAPP/g; s/appname/myapp/g'
```
Then delete this recipe directory.

## Guards baked in (keep these)

- **SSR-safe** — `page.js` loads `ChatApp` with `dynamic(…, { ssr:false })`, and every
  `localStorage` call is wrapped in the `ls` helper (`try { window.localStorage… } catch {}`),
  so browser-only APIs never run or throw during SSR.
- **XSS-safe markdown** — assistant text renders through
  `<ReactMarkdown remarkPlugins={[remarkGfm]}>`. react-markdown 10.x does not render raw
  HTML and `rehype-raw` is intentionally absent, so `<script>`/`<img onerror=…>` in LLM
  output is escaped, not executed. **Do not add `rehype-raw`** — it re-opens the hole.
- **Collision-free ids** — `genId()` uses `crypto.randomUUID()` with a `Math.random`
  fallback for non-secure/old contexts.

## Going streaming

`send()` calls a single `runRequest(text)` that POSTs and awaits one JSON body. To stream,
swap the body of `runRequest` for a `fetch` + `ReadableStream`/SSE reader that appends
tokens to the in-progress assistant message — the four UI states, components, and the
`{ input }` request shape are unchanged.
