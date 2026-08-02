# HackerRank Orchestrate — Message Notification Router

> **AI-Powered WhatsApp Multimodal Notification Routing System**  
> *Built for HackerRank Orchestrate Hackathon (August 2026)*

---

## Overview

WhatsApp streams are noisy. Users receive family messages, work deadlines, society notices, business promotions, image posters, audio voice notes, and scam attempts in the same inbox. Treating every message identically causes two failures: critical updates get missed, and low-value or unsafe messages interrupt the user.

This project implements a personalized **Message Notification Router** powered by **Gemini 2.0 Flash**. It processes incoming multimodal messages (Text, Images, Voice Notes) along with rich contextual metadata to decide whether to:

- `notify`: Interrupt the user immediately (time-sensitive, urgent, or high-value personal updates)
- `digest`: Batch for later summary (general discussions, non-urgent news, or social events)
- `mute`: Suppress silently (low-value promotions, spam, scams, or muted group chatter)

---

## Key Technical Features

- **Native Multimodal Processing**: Directly routes `.jpg` images and `.mp3` audio files to Gemini's native API without external Whisper or OCR pre-processing.
- **Rule-Based Fast-Path Scam Detection**: Instant short-circuiting for domain spoofing (`official_domain` != `domain_used_by_sender`), OTP theft, and viral chain scams.
- **Rich Context Aggregation**: Assembles user DND/Quiet Hours, group admin roles, group mute states, and business opt-in preferences.
- **Evidence Retrieval Engine**: Searches historical interaction data (`message_history.csv`, `message_events.csv`) to populate `evidence_message_ids`.
- **Confidence Calibration**: Post-processes prediction confidence based on entity context density.
- **Exponential Backoff & Rate Limit Handling**: Automatic handling of API rate limits (15 RPM / 1,500 RPD).

---

## Repository Layout

```text
.
├── AGENTS.md                   # AI Coding Agent Rules & Audit Logging Specification
├── problem_statement.md        # Full HackerRank challenge specification
├── README.md                   # You are here
├── requirements.txt            # Python dependencies
├── .env.example                # API key template
├── output.csv                  # Main prediction submission file
├── dataset/                    # Official dataset directory (CSVs + Media)
│   ├── messages.csv            # Target incoming messages to route
│   ├── sample_messages.csv     # Solved benchmark ground truth
│   ├── users.csv               # User profiles & do_not_disturb_window
│   ├── groups.csv & members    # Group metadata & membership roles
│   ├── business_accounts.csv   # Business accounts & domain verification
│   ├── message_history.csv     # Historical interaction records
│   └── media/                  # Audio (.mp3) and image (.jpg) files
└── code/                       # Core system implementation
    ├── main.py                 # Terminal execution entry point
    ├── router.py               # Gemini 2.0 Flash SDK integration & LLM client
    ├── context_builder.py      # Personalized multi-entity context assembler
    ├── scam_detector.py        # Phishing and scam fast-path engine
    ├── evidence_retriever.py   # Historical evidence lookup
    ├── media_processor.py      # Path resolution & MIME detector
    ├── prompts.py              # System & user prompt templates
    ├── utils.py                # Quiet hours calculator & sanitizers
    ├── package_submission.py   # Output validator & code.zip builder
    ├── evaluation/
    │   └── main.py             # Accuracy & F1 evaluation benchmark
    └── tests/
        └── test_router.py      # Unit test suite
```

---

## Quick Start

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

> *Note: If `GOOGLE_API_KEY` is omitted, the engine automatically runs in offline rule-based mode.*

---

## Running the Router & Evaluator

### Run Full Message Notification Router Pipeline

Processes all incoming messages in `dataset/messages.csv` and outputs `output.csv`:

```bash
python3 code/main.py
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
```

---

## Output Format Specification

The system generates `output.csv` matching the exact HackerRank contract schema:

```csv
message_id,action,message_type,reason,confidence,evidence_message_ids
msg_023,mute,business_update,Promotional messages from business accounts muted by user preference.,0.82,message_0101
msg_091,notify,personal,Personal direct message routed for immediate user notification.,0.82,message_0381
msg_090,notify,personal,Personal direct message routed for immediate user notification.,0.82,none
```

---

## Packaging for HackerRank Submission

To generate the required `code.zip` submission archive and validate `output.csv`:

```bash
python3 code/package_submission.py
```

This verifies schema compliance and creates a clean `code.zip` bundle excluding temporary files and secrets.

---

## License & Authorship

Built by **Rehaan Ahmad** for the **HackerRank Orchestrate** hackathon challenge.
