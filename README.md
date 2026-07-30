# AI Study Buddy — Curriculum Repo (Sessions 1–7)

This repo is the **instructor's master copy** of the Study Buddy project across the first seven sessions of the AI Intensives course.

Each folder is a **complete, runnable Streamlit app** that represents what a student's project should look like at the end of that session.

## How to use this repo

Every folder is self-contained:

```
session-0X-.../
├── README.md           ← what's new, how to run, what to try
├── app.py              ← the Streamlit app (and sometimes rag.py too)
├── requirements.txt    ← exact deps for this session
├── .env.example        ← shows students what key they need
├── .gitignore          ← so .env and chroma_db/ don't get committed
└── samples/            ← (S4+) example notes / images / PDFs
```

### Running any session

```bash
cd session-02-v0-qa      # or whichever session
python -m venv .venv
source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env
# paste your Gemini API key into .env
streamlit run app.py
```

A browser tab opens at `http://localhost:8501`. That's your Study Buddy.

## Getting a free Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in with any Google account.
3. Click **Get API key** → **Create API key**.
4. Copy the key into the `.env` file for any session folder you run:

```
GOOGLE_API_KEY=paste_your_key_here
```

**Cost:** $0. The free tier (`gemini-2.0-flash`) gives 15 requests/minute and 1,500/day, which is plenty for a full classroom.

## How class distribution works

- Before each session, zip the **previous** session's folder and share it with students who fell behind — it's their clean starting point.
- After each session, zip the **current** session's folder and share it as the reference solution so students can diff their work against the canonical answer.

## Tech stack at a glance

| Layer | Tool |
|---|---|
| Language | Python 3.10+ |
| UI / frontend | Streamlit (Python becomes a web app — no HTML/CSS/JS) |
| AI backend | Google Gemini (`gemini-2.0-flash`) — free tier |
| Embeddings (S6) | Google `text-embedding-004` — same API key, free |
| Vector store (S6) | ChromaDB (local, persistent) |
| Doc parsing (S6) | `pypdf` |
| External API (S7) | Wikipedia REST — no key needed |
| Editor | VS Code |
| Version control | Git + GitHub |
| AI coding assistant | Claude Code (or Copilot / Cursor — pick one as class standard) |

One API key, one SDK, free all the way through.

## What each session teaches

| Session | Feature added | Concept taught |
|---|---|---|
| S1 | Scaffolding + first Streamlit page | Setup, tooling, project framing |
| S2 | One-box Q&A app | input → model → output, first AI call |
| S3 | Subject + level + tutor persona | System prompts, prompt engineering |
| S4 | "Summarize my notes" tab | Text summarization workflow |
| S5 | "Study from a photo" tab | Vision / multimodal input |
| S6 | "My reviewers" tab with citations | RAG pipeline (chunk→embed→store→retrieve) |
| S7 | "Look it up" Wikipedia toggle | External APIs, safe key storage |

See each session folder's `README.md` for details on what was added that week.
