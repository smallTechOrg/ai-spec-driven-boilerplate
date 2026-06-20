# Test me — Customer-Support Triage Agent

This is a friendly, non-technical guide to trying the agent on your own machine. No coding required —
just copy-paste the commands below in order.

## What this agent does

You paste in an incoming **customer-support ticket** and the agent gives you back, in one step:

- an **urgency** label — `low`, `normal`, `high`, or `urgent`
- a **category** label — `billing`, `technical`, `account`, `shipping`, or `general`
- a **drafted suggested reply** to the customer that acknowledges the problem and states the next step

It is grounded in your support policy (it looks the policy up before quoting a timeframe — it does **not**
invent numbers), and it will **refuse** to perform irreversible actions: it drafts the reply, but a real
refund or account deletion is left for an authorized human to do.

Two more abilities — **escalate a ticket** and **summarize a long thread** — are wired in and reachable but
ship as honest placeholders for now (they return a fixed result until promoted in a later build).

---

## Step 1 — the ONE thing to do first: add your key

The agent needs a **funded LLM API key** to think. This is the only setup that requires you.

1. Make your own copy of the example settings file:

   ```bash
   cp .env.example .env
   ```

2. Open `.env` in any text editor and paste your funded key after `APP_LLM_API_KEY=` so the line reads:

   ```
   APP_LLM_API_KEY=sk-ant-...your-real-key...
   ```

   - The default model is `claude-haiku-4-5` (the cheap tier). To use a different model, change the
     `APP_LLM_MODEL=` line — no code edit needed.
   - `.env` is private and is never committed to git. Keep your key in here only.

> Without a real key the server will still **start**, but the moment you ask it to triage a ticket it will
> return a clean error instead of an answer. The key is what makes it actually work.

---

## Step 2 — install and run it

You need: Python 3.12, [`uv`](https://docs.astral.sh/uv/), Node 20+, and `jq`. Then:

```bash
uv sync          # installs the Python dependencies
make setup       # installs the UI and a browser for the automated check (one-time)
make dev         # starts BOTH the agent and the web UI together (press Ctrl-C to stop)
```

That opens three things:

- The web UI: <http://localhost:3001>
- The agent's API: <http://localhost:8001>
- The runs dashboard: <http://localhost:8001/traces>

---

## Step 3 — what SUCCESS looks like

You'll know it's working when **all** of these happen:

1. **The server boots.** `make dev` prints startup lines and does not crash. Visiting
   <http://localhost:8001/health> shows `{"ok": true, ...}`.

2. **The UI loads.** Open <http://localhost:3001> — you see a "Support Triage Agent" page with a text box.

3. **You get a triaged reply.** Paste a ticket, e.g.
   *"I was charged twice for my subscription this month and I'm really frustrated. When will I get my money
   back?"*, click **Run**, and within a few seconds you get back an **Urgency**, a **Category** (`billing`),
   and a drafted **Reply** that quotes the real policy timeframe (it should say refunds take **5 business
   days**, taken from the policy — not invented). Ask it to *"just issue the refund now"* and it should
   politely **decline** and say an authorized human must handle it.

4. **The two-turn follow-up works.** After it answers, send a follow-up like *"Can you make the reply a bit
   more apologetic?"* — it remembers the previous ticket and revises the same draft (it doesn't start over).
   (The UI sends one ticket per Run; the multi-turn memory is exercised end-to-end by the gate in Step 4.)

5. **The dashboard shows the run.** Open <http://localhost:8001/traces>. You see your run listed with, in
   plain English, what the agent did step by step, whether it succeeded, how many **tokens** it used, and
   what it **cost** in dollars.

---

## Step 4 — run the full automated check (the "gate")

The gate is the mechanical definition of "done." It boots the real agent, has a two-turn conversation,
has an AI judge grade the answer, drives the UI in a real browser, and confirms the run shows up on the
dashboard — all automatically.

```bash
make gate        # runs the whole suite; needs your funded APP_LLM_API_KEY
echo $?          # 0 means DONE. Anything else means it is not done.
```

**If `echo $?` prints `0`, everything passed — the agent is verified end to end.** If it prints anything
else, the output above it names exactly which check failed.

---

## Already verified for you (no key needed)

Before handing this over, the keyless parts were checked and pass: the repo structure, the acceptance-criteria
binding lint, all the offline unit tests, and a boot smoke test (the server starts and `/health` responds).
The only things waiting on **your** key are the live triage answers and the full `make gate`. See the PR
description for the exact green/needs-key checklist.
