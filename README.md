# UP Police AI Workshop

AI Learn-to-Learn progress tracker for Uttar Pradesh Police staff.

> **All data stays on the device.** Officer profiles, assessment scores, and plan progress are stored in browser `localStorage` only — nothing is sent to any server.

## How to Run

The app fetches `data/data.json`, so it must be served over HTTP (not opened as `file://`).

**Python (no install needed):**

```bash
python3 -m http.server 8001
```

Then open: http://localhost:8001

Any static file server works — nginx, VS Code Live Server, etc.

## What It Does

1. **Register** — enter name + badge number (no password, no account)
2. **Self-Assessment** — 20 questions across 4 AI skill areas, scored 1–5
3. **30-Day Plan** — auto-generated from your scores (Beginner / Intermediate / Advanced per area)
4. **Progress Tracking** — mark tasks done/in-progress, progress bar shows X/30 complete

## Files

```
index.html          Landing page + registration
assessment.html     20-question self-assessment
plan.html           30-day plan dashboard
css/style.css       Styles
js/app.js           All app logic + localStorage handling
data/data.json      Questions + 60 tasks (edit to customise content)
```

## Customising Content

Edit `data/data.json` to change questions or tasks. Task keys follow the format:
`{area}_{level}_{index}` — e.g. `A_B_0` = AI Tools · Beginner · task 0.

## Skill Areas & Levels

| Code | Area | Beginner | Intermediate | Advanced |
|------|------|----------|-------------|---------|
| A | AI Tools & General Literacy | avg < 2.5 | avg < 3.75 | avg ≥ 3.75 |
| B | Cybersecurity & AI Threats | same | same | same |
| C | Communication & Data Analytics | same | same | same |
| D | CCTV & Surveillance AI | same | same | same |

## Tech Stack

Pure HTML + CSS + JavaScript. No framework, no build step, no server required.
Data persists in browser `localStorage` — secure and fully offline-capable.
