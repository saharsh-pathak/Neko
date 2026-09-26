<div align="center">

# Neko 🐾
### Your Personal, Private Knowledge Vault

**Tag anything you read online. Ask it questions later. Never forget it again — and never send it to the cloud.**

[![Built for OSDHack 2026](https://img.shields.io/badge/Built%20for-OSDHack%202026-blueviolet?style=for-the-badge)](https://github.com)
[![Track: On-Device AI](https://img.shields.io/badge/Track-On--Device%20AI%20%2F%20TinyML%20%2F%20Embedded-success?style=for-the-badge)](https://github.com)
[![Privacy: 100% Local](https://img.shields.io/badge/Privacy-100%25%20Local-orange?style=for-the-badge)](https://github.com)

</div>

---

## 🛑 The Problem

We collect knowledge constantly — bookmarks, highlights, half-read articles, saved tweets — and almost never revisit any of it. Existing "save for later" tools (read-it-later apps, bookmark managers, cloud note-takers) either:

1. **Send your reading history** to a third-party server, or
2. **Just store text** with no way to actually retrieve or use it later.

We wanted a tool that captures what you read, understands it, and actively helps you remember it — **entirely on your own machine**.

---

## 💡 The Solution

Neko is a two-part system designed for absolute privacy and maximum retention:

* **Browser Extension** — Highlight text or tag a full page on any website, by typing or by voice. Ask questions about the page you're on right now.
* **Local Knowledge Agent (`localhost`)** — A private AI that indexes everything you've tagged, answers questions grounded only in your material, and actively quizzes you on it using spaced repetition — so you actually retain what you save.

🔒 **No account. No cloud database. No API keys required for core functionality. Everything runs on your machine.**

---

## 📐 Architecture

```text
┌─────────────────────────────┐
│      BROWSER EXTENSION      │
│                             │
│  • Highlight → tag + context│
│  • Full page → Readability  │
│    extraction               │
│  • Voice input (popup mic)  │
│  • Offline queue (syncs when│
│    local server is back)    │
│  • Revisit badge on tagged  │
│    pages                    │
└──────────────┬──────────────┘
               │ localhost API (fetch)
               ▼
┌─────────────────────────────┐
│   LOCAL SERVER (the brain)  │
│                             │
│  Whisper (tiny/base)        │
│  → voice transcription      │
│    (Transformers.js, WebGPU)│
│                             │
│  LFM2.5-Embedding-350M      │
│  → fast dense retrieval     │
│                             │
│  LFM2.5-ColBERT-350M        │
│  → rerank top candidates    │
│                             │
│  Qwen3 4B (via Ollama)      │
│  → RAG answers +            │
│    conversational quizzes   │
│                             │
│  SQLite → notes, tags,      │
│           review history    │
│  Chroma → vector index      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│    CUSTOM LOCAL WEB UI      │
│                             │
│  • Chat / ask-your-vault    │
│  • Vault browser (tags,     │
│    sources, timestamps)     │
│  • Active Recall mode       │
│    (SM-2 spaced repetition +│
│     adaptive LLM quizzing)  │
└─────────────────────────────┘
