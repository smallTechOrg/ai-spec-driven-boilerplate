# Capability: Site Rendering

> **Status: FUTURE PHASE** — Not in the initial build.
>
> Posts are stored in the content library (SQLite DB) and viewed via the dashboard. HTML static site export is deferred to a future phase once the content library is working and validated.

---

## What It Will Do (When Implemented)

Write all posts from the content library as plain HTML + CSS files, producing a browsable static site with an index page and individual post pages.

## Deferred Until

After the content library (DB + dashboard) is stable and the operator wants to export posts to a static host (Netlify, GitHub Pages, etc.).

## Notes for Future Implementation

- Output to configurable `output_dir` (default `./output`)
- Individual post pages at `posts/{slug}.html`
- Index at `index.html` listing all posts newest-first
- `style.css` written once, not overwritten on re-runs
- All paths relative (no absolute URLs)
- Cover image paths use relative paths stored by image generation (see `spec/product/capabilities/03-image-generation.md`)
