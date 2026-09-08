# Harness Engineering Multi-Agent Demo

A production-style customer support demo that shows **harness engineering**: wrapping specialist LLM agents in a deterministic control flow instead of letting a single model decide everything.

The app runs this pipeline:

**Guardrail → Router → Specialist agent → Reviewer**

Built with FastAPI, LangGraph, LangChain, and Groq.

## Why a harness?

Not every decision should go through an LLM. This demo keeps cheap, testable Python rules at the edges (safety checks and routing) and uses models only for the work they are good at: writing and reviewing answers.

## Features

- FastAPI web UI with example technical, billing, and general questions
- Deterministic guardrail that blocks unsafe password / payment-card requests
- Keyword router that can select one specialist or several for mixed questions
- Specialist agents with scoped prompts and a demo billing policy
- Reviewer agent that checks the draft for clarity, safety, and over-promising
- Execution trace shown in the UI so you can see each harness step

## How it works

```text
question
   │
   ▼
guardrail ──blocked──► refusal (end)
   │
   ▼
router ── one or more matches ──► specialist(s) ──► reviewer ──► final answer
```

| Step | File | What it does |
|---|---|---|
| Guardrail + router + graph | `graph.py` | Safety check, route selection, LangGraph wiring |
| Specialist + reviewer agents | `agents.py` | Groq-backed prompts for each role |
| HTTP API + UI server | `app.py` | FastAPI app on port `8080` |
| Browser UI | `templates/index.html`, `static/` | Chat form, route badge, harness trace |

Routing is keyword-based on purpose, and it collects **every** match. A mixed question such as an API error plus a refund request plus “what can support help with?” runs the technical, billing, and general agents, then the reviewer merges the drafts. That keeps billing policy on the billing agent instead of letting the technical agent invent prices.

## Requirements

- Python 3.11+
- A Groq API key
- `conda` or `venv`

## Setup

```bash
conda create -n demo python=3.11 -y
conda activate demo
pip install -r requirements.txt
```

Or with `venv`:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
```

The agents use `openai/gpt-oss-20b` on Groq (`agents.py`).

## Run

```bash
python app.py
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080).

`POST /api/chat` accepts `{ "message": "..." }` and returns `{ "route", "answer", "trace" }`.

## Example questions

- Technical: `I am getting an API login error. How can I fix it?`
- Billing: `How much is the Pro plan and can I get a refund?`
- General: `What can your support team help me with?`
- Mixed: `I am getting an API login error. How can I fix it? How much is the Pro plan and can I get a refund? What can your support team help me with?`

Demo billing policy used by the billing agent:

- Starter: `$10/month`
- Pro: `$25/month`
- Refunds must be reviewed; the agent must not claim a refund is already approved
