# Capability: Browse Articles

**What it does:** Lists saved articles newest-first and shows a single article's full markdown.

**Inputs:** (list) none; (detail) `article_id`.

**Outputs:** HTML list page; HTML detail page rendering the markdown body.

**External calls:** Postgres only.

**Error cases:** unknown `article_id` → 404.

**Success criteria:** Manual browser check in Phase 2.
