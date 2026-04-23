# Data Model

## Storage Technology

**SQLite** via SQLAlchemy 2.0 ORM. Single file at `./data/blogforge.db` (configurable via env var). Chosen for simplicity — no separate database process required.

Generated HTML files are stored on disk at `./output/` (not in the database). The database stores metadata and content source; the filesystem holds the rendered artifacts.

---

## Entities

### Blog (singleton — one row)

The blog's identity. Only one blog per deployment.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | INTEGER | yes | Always 1 (singleton) |
| name | TEXT | yes | Blog display name (e.g. "The Curious Mind") |
| tagline | TEXT | no | Short description shown in header |
| niche | TEXT | yes | Topic focus (e.g. "AI tools for solopreneurs") |
| themes | TEXT | yes | JSON array of sub-themes (e.g. ["productivity", "automation"]) |
| posts_per_run | INTEGER | yes | How many posts to generate per run (default: 3) |
| schedule_cron | TEXT | no | Cron expression for scheduled runs (null = no schedule) |
| output_dir | TEXT | yes | Filesystem path for generated HTML (default: "./output") |
| created_at | DATETIME | yes | |
| updated_at | DATETIME | yes | |

### Writer

A persona that writes posts. Multiple writers per blog.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | INTEGER | yes | Primary key |
| name | TEXT | yes | Writer's display name (e.g. "Alex Chen") |
| persona_prompt | TEXT | yes | System prompt injected into LLM when this writer drafts a post |
| bio | TEXT | yes | Short bio shown on posts (2–3 sentences) |
| avatar_url | TEXT | no | URL or path to writer avatar image |
| is_active | BOOLEAN | yes | Inactive writers are excluded from assignment (default: true) |
| created_at | DATETIME | yes | |
| updated_at | DATETIME | yes | |

### Post

A generated blog post. One post per topic per run.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | INTEGER | yes | Primary key |
| run_id | INTEGER | yes | FK → Run |
| writer_id | INTEGER | yes | FK → Writer |
| topic | TEXT | yes | The topic that was generated for this post |
| title | TEXT | yes | Generated post title |
| content_markdown | TEXT | yes | Full post body in Markdown |
| content_html | TEXT | yes | Rendered HTML of the post body |
| cover_image_path | TEXT | no | Relative path within output_dir (e.g. "images/post-42-cover.png") |
| cover_image_prompt | TEXT | no | The prompt used to generate the cover image |
| slug | TEXT | yes | URL-safe identifier (e.g. "why-ai-tools-matter-2026-04") |
| published_at | DATETIME | no | When the HTML was written to disk (null if not yet rendered) |
| created_at | DATETIME | yes | |

### Run

A single generation run (one invocation of the agent pipeline).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | INTEGER | yes | Primary key |
| trigger | TEXT | yes | "manual" or "scheduled" |
| status | TEXT | yes | "running" / "completed" / "failed" |
| posts_requested | INTEGER | yes | How many posts were requested |
| posts_completed | INTEGER | yes | How many posts were successfully generated |
| error_message | TEXT | no | Error details if status = "failed" |
| started_at | DATETIME | yes | |
| completed_at | DATETIME | no | |

### UsedTopic

Topics that have already been used — prevents repetition across runs.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | INTEGER | yes | Primary key |
| topic | TEXT | yes | The topic string (normalised to lowercase) |
| post_id | INTEGER | yes | FK → Post |
| used_at | DATETIME | yes | |

---

## Relationships

- `Run` → has many `Post`
- `Writer` → has many `Post`
- `Post` → has one `UsedTopic` entry

## Data Lifecycle

- Blog config: created once at setup; updated via dashboard
- Writers: created/updated/deactivated via dashboard; never hard-deleted (soft deactivation only)
- Posts: created per run; never deleted (serve as history)
- Runs: created when triggered; updated as the run progresses
- UsedTopics: append-only; never deleted (ensures no repetition over the lifetime of the blog)

## Sensitive Data

No PII or payment data. The Gemini API key is stored in environment variables only — never in the database.
