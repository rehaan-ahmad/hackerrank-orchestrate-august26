# 🚀 HackerRank Orchestrate — Message Notification Router

> **AI-Powered WhatsApp Multimodal Notification Routing System**  
> *Built for HackerRank Orchestrate Hackathon (August 2026)*

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![Gemini](https://img.shields.io/badge/Gemini-2.0%20Flash-4285F4?logo=google)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![HackerRank](https://img.shields.io/badge/HackerRank-Orchestrate%202026-orange)](https://hackerrank.com)

---

## 📖 Overview

WhatsApp streams are noisy. Users receive family messages, work deadlines, society notices, business promotions, image posters, audio voice notes, and scam attempts in the same inbox. Treating every message identically causes two failures: **critical updates get missed**, and **low-value or unsafe messages interrupt the user**.

This project implements a personalized **Message Notification Router** powered by **Gemini 2.0 Flash**. It processes incoming multimodal messages (Text, Images, Voice Notes) along with rich contextual metadata to decide whether to:

| Action | Icon | Description |
|--------|------|-------------|
| `notify` | 🔔 | Interrupt the user immediately — time-sensitive, urgent, or high-value personal updates |
| `digest` | 📋 | Batch for later summary — general discussions, non-urgent news, or social events |
| `mute` | 🔇 | Suppress silently — low-value promotions, spam, scams, or muted group chatter |

---

## ✨ Key Technical Features

| Feature | Description |
|---------|-------------|
| 🎯 **Native Multimodal Processing** | Directly routes `.jpg` images and `.mp3` audio files to Gemini's native API — no external Whisper or OCR pre-processing needed |
| 🛡️ **Fast-Path Scam Detection** | Instant short-circuiting for domain spoofing (`official_domain` ≠ `domain_used_by_sender`), OTP theft, and viral chain scams |
| 🧠 **Rich Context Aggregation** | Assembles user DND/Quiet Hours, group admin roles, group mute states, and business opt-in preferences |
| 🔍 **Evidence Retrieval Engine** | Searches historical interaction data (`message_history.csv`, `message_events.csv`) to populate `evidence_message_ids` |
| 📊 **Confidence Calibration** | Post-processes prediction confidence based on entity context density |
| ⚡ **Rate Limit Handling** | Exponential backoff with automatic handling of API rate limits (15 RPM / 1,500 RPD) |
| 🔄 **Offline Fallback** | Deterministic rule-based engine when API key is unavailable — zero external dependencies |

---

## 📁 Repository Layout

```text
.
├── AGENTS.md                   # 🤖 AI Coding Agent Rules & Audit Logging Specification
├── problem_statement.md        # 📋 Full HackerRank challenge specification
├── README.md                   # 📖 You are here
├── requirements.txt            # 📦 Python dependencies
├── .env.example                # 🔐 API key template
├── output.csv                  # 🎯 Main prediction submission file
├── dataset/                    # 📂 Official dataset directory (CSVs + Media)
│   ├── messages.csv            # 📨 Target incoming messages to route
│   ├── sample_messages.csv     # ✅ Solved benchmark ground truth
│   ├── users.csv               # 👤 User profiles & do_not_disturb_window
│   ├── groups.csv & members    # 👥 Group metadata & membership roles
│   ├── business_accounts.csv   # 🏢 Business accounts & domain verification
│   ├── message_history.csv     # 📜 Historical interaction records
│   └── media/                  # 🖼️ Audio (.mp3) and image (.jpg) files
└── code/                       # ⚙️ Core system implementation
    ├── main.py                 # ▶️ Terminal execution entry point
    ├── router.py               # 🤖 Gemini 2.0 Flash SDK integration & LLM client
    ├── context_builder.py      # 🏗️ Personalized multi-entity context assembler
    ├── scam_detector.py        # 🛡️ Phishing and scam fast-path engine
    ├── evidence_retriever.py   # 🔍 Historical evidence lookup
    ├── media_processor.py      # 📎 Path resolution & MIME detector
    ├── prompts.py              # 💬 System & user prompt templates
    ├── utils.py                # 🛠️ Quiet hours calculator & sanitizers
    ├── package_submission.py   # ✅ Output validator & code.zip builder
    ├── evaluation/
    │   └── main.py             # 📈 Accuracy & F1 evaluation benchmark
    └── tests/
        └── test_router.py      # 🧪 Unit test suite
```

---

## 🚀 Quick Start

### 1. Installation

Ensure Python 3.10+ is installed, then install the dependencies:

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the `.env.example` file and configure your Google Gemini API key:

```bash
cp .env.example .env
```

Edit `.env`:
```env
GOOGLE_API_KEY=your_actual_gemini_api_key
SLEEP_SEC=0.2
```

> **Note:** If `GOOGLE_API_KEY` is omitted, the engine automatically runs in **offline rule-based mode** — fully functional without any API calls.

---

## ▶️ Running the Router & Evaluator

### Run Full Message Notification Router Pipeline

Processes all incoming messages in `dataset/messages.csv` and outputs `output.csv`:

```bash
python3 code/main.py
```

**Expected Output:**
```text
[+] Using dataset directory: /path/to/dataset
[+] Loaded 110 messages to route.
[!] GOOGLE_API_KEY not set. Operating in offline rule-based mode.
  Processed 40/110 messages... (Scams: 3, LLM: 0)
  Processed 60/110 messages... (Scams: 8, LLM: 0)
  ...
[+] Successfully wrote 110 predictions to output.csv

=== ROUTING ACTION DISTRIBUTION ===
action
digest    54
mute      40
notify    16
```

### Run Benchmark Evaluator

Evaluates predictions against ground truth in `dataset/sample_messages.csv`:

```bash
python3 code/evaluation/main.py
```

### Run Unit Test Suite

Runs unit tests for quiet hours, scam detection, and utility helpers:

```bash
python3 code/tests/test_router.py
# OR
pytest code/tests/ -v
```

---

## 📄 Output Format Specification

The system generates `output.csv` matching the exact HackerRank contract schema:

```csv
message_id,action,message_type,reason,confidence,evidence_message_ids
msg_023,mute,business_update,Promotional messages from business accounts muted by user preference.,0.82,message_0101
msg_091,notify,personal,Personal direct message routed for immediate user notification.,0.82,message_0381
msg_090,notify,personal,Personal direct message routed for immediate user notification.,0.82,none
```

### Column Reference

| Column | Type | Description |
|--------|------|-------------|
| `message_id` | string | Unique identifier from `messages.csv` |
| `action` | enum | `notify` \| `digest` \| `mute` |
| `message_type` | string | `personal` \| `business_update` \| `event` \| `scam` \| `spam` |
| `reason` | string | Human-readable explanation (≤ 280 chars) |
| `confidence` | float | Calibrated confidence score [0.0, 1.0] |
| `evidence_message_ids` | string | Comma-separated historical message IDs or `none` |

---

## 📦 Packaging for HackerRank Submission

To generate the required `code.zip` submission archive and validate `output.csv`:

```bash
python3 code/package_submission.py
```

**What it does:**
- ✅ Validates `output.csv` schema compliance
- ✅ Creates clean `code.zip` bundle
- ✅ Excludes temporary files, secrets, and dataset

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        MESSAGE ROUTER                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  messages.csv ──► ContextBuilder ──► ScamDetector ──► Router  │
│       │              │                  │                    │   │
│       ▼              ▼                  ▼                    ▼   │
│  ┌────────┐    ┌──────────┐       ┌──────────┐         ┌─────┐ │
│  │ User   │    │ Group    │       │ Business │         │ LLM │ │
│  │ Profile│    │ Membership│      │ Opt-in   │         │ or  │ │
│  │ DND    │    │ Mute     │       │ Domain   │         │Rule │ │
│  └────────┘    └──────────┘       └──────────┘         └─────┘ │
│       │              │                  │                    │   │
│       └──────────────┴──────────────────┴────────────────────┘   │
│                              │                                    │
│                              ▼                                    │
│                    EvidenceRetriever                              │
│                              │                                    │
│                              ▼                                    │
│                      output.csv                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Scam Detection Patterns

The fast-path engine catches these patterns **before** any LLM call:

| Pattern Type | Example | Confidence |
|--------------|---------|------------|
| Domain Spoofing | `talabat-refund.com` vs `talabat.com` | 93% |
| OTP/Credential Theft | "Send your OTP to verify" | 91% |
| Fake Urgency | "Account blocked — act now!" | 91% |
| Lottery/Prize | "Congratulations! You won ₹50L" | 91% |
| KBC Scams | "KBC lottery winner" | 91% |
| High Forward Spam | Viral chain (>8 forwards + keywords) | 88% |

---

## 📊 Performance Benchmarks

| Metric | Value |
|--------|-------|
| **Messages Processed** | 110/110 (100%) |
| **Action Distribution** | notify: 16, digest: 54, mute: 40 |
| **Scam Short-Circuits** | 14 (12.7%) |
| **Confidence Range** | 0.82 – 0.93 |
| **Offline Mode Latency** | < 2 sec total |
| **Unit Tests** | 4/4 passing ✅ |

---

## 🔐 Security & Privacy

- **No secrets in code** — API keys loaded from `.env` only
- **Offline-first design** — Works without any external API calls
- **Data stays local** — Dataset never leaves your machine
- **Free tier safe** — Uses Gemini 2.0 Flash (1,500 req/day free, no credit card)

---

## 📝 License & Authorship

Built by **Rehaan Ahmad** for the **HackerRank Orchestrate** hackathon challenge.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

<div align="center">

**⭐ Star this repo if you found it useful!**

[Report Bug](https://github.com/issues) • [Request Feature](https://github.com/issues) • [HackerRank](https://hackerrank.com)

</div>