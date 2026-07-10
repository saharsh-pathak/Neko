# Neko — Your Personal, Private Knowledge Vault

*Tag anything you read online. Ask it questions later. Never forget it again — and never send it to the cloud.*

> Built for OSDHack 2026 — On-Device AI / TinyML / Embedded Track

---

## The Problem

We collect knowledge constantly — bookmarks, highlights, half-read articles, saved tweets — and almost never revisit any of it. Existing "save for later" tools (read-it-later apps, bookmark managers, cloud note-takers) either:
- Send your reading history to a third-party server, or
- Just store text with no way to actually *retrieve* or *use* it later.

We wanted a tool that captures what you read, understands it, and actively helps you remember it — entirely on your own machine.

---

## The Solution

**Neko** is a two-part system:

1. **Browser Extension** — highlight text or tag a full page on any website, by typing or by voice. Ask questions about the page you're on right now.
2. **Local Knowledge Agent** (`localhost`) — a private AI that indexes everything you've tagged, answers questions grounded only in *your* material, and actively quizzes you on it using spaced repetition — so you actually retain what you save.

No account. No cloud database. No API keys required for core functionality. Everything runs on your machine.

---

## Architecture

```
┌─────────────────────────────┐
│      BROWSER EXTENSION       │
│                              │
│  • Highlight → tag + context │
│  • Full page → Readability   │
│    extraction                │
│  • Voice input (popup mic)   │
│  • Offline queue (syncs when │
│    local server is back)     │
│  • Revisit badge on tagged   │
│    pages                     │
└──────────────┬───────────────┘
               │ localhost API (fetch)
               ▼
┌─────────────────────────────┐
│   LOCAL SERVER (the brain)   │
│                              │
│  Whisper (tiny/base)         │
│   → voice transcription      │
│   (Transformers.js, WebGPU)  │
│                              │
│  LFM2.5-Embedding-350M       │
│   → fast dense retrieval     │
│                              │
│  LFM2.5-ColBERT-350M         │
│   → rerank top candidates    │
│                              │
│  Qwen3 4B (via Ollama)       │
│   → RAG answers +            │
│     conversational quizzes   │
│                              │
│  SQLite → notes, tags,       │
│           review history     │
│  Chroma → vector index       │
└──────────────┬───────────────┘
               │
               ▼
┌─────────────────────────────┐
│   CUSTOM LOCAL WEB UI        │
│                              │
│  • Chat / ask-your-vault     │
│  • Vault browser (tags,      │
│    sources, timestamps)      │
│  • Active Recall mode        │
│    (SM-2 spaced repetition + │
│    adaptive LLM quizzing)    │
└──────────────────────────────┘
```

The entire core AI pipeline runs locally. The only optional cloud touchpoints (e.g. exporting a weekly digest via email) are secondary — never the core intelligence.

---

## Killer Feature: Active Recall

Most "save for later" tools are where knowledge goes to die. Neko doesn't just store what you tag — it makes sure you actually remember it.

- **Spaced repetition (SM-2)** — the system tracks how well you answer each item and schedules the next review at the optimal interval, just like Anki, but generated automatically from whatever you've tagged.
- **On-demand review** — trigger a session anytime you want a quick refresher.
- **Conversational, not flashcards** — the LLM asks a question grounded in your own saved material, and *adapts its follow-ups based on your actual answer* rather than a binary right/wrong flashcard flip.

This turns passive bookmarking into active learning, entirely offline, entirely private.

---

## Model Footprint

| Component | Model | Size (approx.) |
|---|---|---|
| Voice transcription | Whisper-tiny/base | ~75–140 MB |
| Fast retrieval | LFM2.5-Embedding-350M | ~350M params |
| Reranking | LFM2.5-ColBERT-350M | ~350M params |
| RAG + quiz generation | Qwen3 4B (Q4 via Ollama) | ~2.5–3 GB |

*Total local footprint: under ~4 GB, runs on consumer hardware with no cloud dependency for core features.*

---

## Engineering Highlights

- Two-stage retrieval pipeline (dense bi-encoder → late-interaction reranker) instead of a single embedding pass, for meaningfully better search accuracy at a small latency cost
- Offline-first extension design — local queueing when the backend server isn't running, syncing automatically once it's back
- SM-2 spaced repetition implemented from scratch, driving an LLM-adaptive (not static flashcard) quiz experience
- Context-aware capture — highlights save surrounding paragraph context, not just the raw selection, improving downstream RAG quality

---

## Roadmap / Stretch Goals

- Voice replies (local TTS, e.g. Piper)
- Auto-tagging via LLM
- Multi-language support
- Weekly digest email (optional cloud hook)
