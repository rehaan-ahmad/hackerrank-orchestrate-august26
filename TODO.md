# Message Notification Router — Build TODO

---

## PHASE 0 — SETUP

- [ ] Clone HackerRank repo → get `dataset/` folder locally
- [ ] Copy all CSV + `media/` into `code/dataset/`
- [ ] `cp .env.example .env` → paste `GOOGLE_API_KEY` (get from [aistudio.google.com](https://aistudio.google.com) → no card required)
- [ ] **Google Student Ambassador perk**: check ambassador portal for elevated rate limits or credits before using the default free tier
- [ ] Update `requirements.txt`: replace `anthropic>=0.39.0` and `faster-whisper>=1.0.0` with `google-generativeai>=0.8.0`
- [ ] `pip install -r requirements.txt`
- [ ] Verify SDK loads: `python -c "import google.generativeai as genai; print('ok')"`
- [ ] Verify API key works: `python -c "import google.generativeai as genai, os; genai.configure(api_key=os.environ['GOOGLE_API_KEY']); m=genai.GenerativeModel('gemini-2.0-flash'); print(m.generate_content('ping').text)"`

---

## PHASE 1 — DATA EXPLORATION (CRITICAL — do before touching code)

**Goal**: understand actual column names, value distributions, schema gaps. The problem statement schema is aspirational — real CSVs differ.

### 1.1 Inspect every CSV

Run this for each file to check real column names:

```python
import pandas as pd, os
for f in os.listdir("dataset"):
    if f.endswith(".csv"):
        df = pd.read_csv(f"dataset/{f}", nrows=3)
        print(f"\n=== {f} ===")
        print(df.dtypes.to_string())
        print(df.head(2).to_string())
```

- [ ] `messages.csv` — note exact column names (esp. media_type values, conversation_type values)
- [ ] `sample_messages.csv` — study action distribution, message_type distribution, reason style
- [ ] `users.csv` — find quiet_hours column names exactly
- [ ] `groups.csv` — find group_type values (family? work? society?)
- [ ] `group_members.csv` — find mute/role column names
- [ ] `business_accounts.csv` — find verified column name + values (bool? string?)
- [ ] `user_business_history.csv` — find opt-in/opt-out/order column names
- [ ] `message_history.csv` — check if sender_user_id + business_id exist
- [ ] `message_events.csv` — list all unique event_type values
- [ ] `images.csv` — find exact image_id + file_path column names
- [ ] `voice_notes.csv` — find exact voice_note_id + file_path column names
- [ ] `daily_notification_summary.csv` — see what metric columns exist

### 1.2 Check media files

```bash
ls dataset/media/ | head -20
ls dataset/media/ | wc -l
file dataset/media/<first_audio_file>   # check format: ogg? mp3? wav?
```

- [ ] Note image file extensions (jpg/png/webp) — all supported by Gemini inline
- [ ] Note audio file extensions — Gemini natively supports: `audio/ogg`, `audio/mp3`, `audio/wav`, `audio/opus`, `audio/aac`, `audio/flac`
- [ ] No ffmpeg, no whisper, no conversion needed — Gemini handles raw WhatsApp `.ogg` files directly
- [ ] Check total media folder size: `du -sh dataset/media/` — if individual files > 20MB, must use File API upload instead of inline base64

### 1.3 Study sample_messages.csv deeply

```python
df = pd.read_csv("dataset/sample_messages.csv")
print(df["action"].value_counts())
print(df["message_type"].value_counts())
print(df["reason"].head(10).to_string())
print(df["confidence"].describe())
print(df[df["evidence_message_ids"] != "none"]["evidence_message_ids"].head())
```

- [ ] How are reasons phrased? Match that style in the prompt.
- [ ] What confidence range is used? Calibrate accordingly.
- [ ] What does evidence look like when present vs "none"?
- [ ] What's the action split? (notify/digest/mute %) — helps calibrate default outputs

### 1.4 Fix column name mismatches in code

After exploration, update hardcoded column name assumptions in:

- [ ] `context_builder.py` — `_user_ctx`, `_group_ctx`, `_business_ctx`, `_sender_ctx`
- [ ] `context_builder.py` — `_image_ctx`: fix `id_col` and `path_col` detection
- [ ] `context_builder.py` — `_voice_ctx`: fix `id_col` and `path_col` detection
- [ ] `evidence_retriever.py` — fix column name checks in `find_evidence`

---

## PHASE 2 — FIX KNOWN CODE ISSUES

### 2.1 context_builder.py

- [ ] **Column guard**: wrap every `.columns` check with actual column from CSV (found in Phase 1)
- [ ] **`_sender_ctx` filter bug**: `self.message_history.get(...)` is wrong — check if column exists with `"col" in df.columns` instead
- [ ] **`_user_hist_index`**: change groupby key to string: `str(uid)` → also cast `msg["user_id"]` to string when looking up
- [ ] **Media path**: `os.path.join(dataset_dir, info[path_col])` — if `file_path` already contains `media/` prefix, don't double-prepend. Add check:
  ```python
  if str(info[path_col]).startswith("media/") or str(info[path_col]).startswith("dataset/"):
      full_path = os.path.join(self.dataset_dir, str(info[path_col]))
  else:
      full_path = os.path.join(self.dataset_dir, "media", str(info[path_col]))
  ```
- [ ] **NaN group_id**: `msg.get("group_id")` returns `nan` (float) for non-group msgs — add: `gid = msg.get("group_id"); gid = None if pd.isna(gid) else gid`
- [ ] **Same fix for business_id, sender_user_id, media_id** — all can be `nan` float

### 2.2 evidence_retriever.py

- [ ] **`find_evidence` strategies**: guard each with column existence checks before filtering
- [ ] **Text similarity**: `message_text` can be `nan` — add `str(text) != "nan"` guard
- [ ] **Evidence dedup**: ensure same ID from multiple strategies doesn't produce duplicates in output

### 2.3 router.py — rewrite for Gemini SDK

Replace entire Anthropic client with `google-generativeai`:

```python
import google.generativeai as genai

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
self.model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=SYSTEM_PROMPT,
    generation_config=genai.GenerationConfig(
        temperature=0.2,       # low temp = consistent routing
        max_output_tokens=512,
    )
)
```

API call (text only):
```python
response = self.model.generate_content(prompt_text)
result_text = response.text
```

API call (image inline):
```python
import PIL.Image
img = PIL.Image.open(image_path)
response = self.model.generate_content([img, prompt_text])
```

API call (voice inline — ogg/mp3/wav):
```python
audio_part = genai.protos.Part(
    inline_data=genai.protos.Blob(
        mime_type="audio/ogg",
        data=open(audio_path, "rb").read()
    )
)
response = self.model.generate_content([audio_part, prompt_text])
```

- [ ] **Rewrite `router.py`** with Gemini client (see above)
- [ ] **Remove** all `anthropic` imports
- [ ] **Pass image as `PIL.Image`** not base64 string — Gemini SDK accepts PIL directly
- [ ] **Pass audio inline** as `genai.protos.Blob` — no transcription step needed
- [ ] **Response parse**: use `response.text` not `response.content[0].text`
- [ ] **Safety filter handling**: Gemini may block content with `response.prompt_feedback.block_reason` — add check, fall back to rule-based router if blocked
- [ ] **JSON parse fallback**: same regex approach works — verify `re.DOTALL`
- [ ] **Max reason length**: truncate at 300 chars
- [ ] **Image size guard**: Gemini inline limit is 20MB — still add check for very large files, use File API upload path for >10MB

### 2.4 media_processor.py — simplify drastically

Whisper is gone. Gemini handles both images and audio natively in the same API call as the routing decision. `media_processor.py` shrinks to just path resolution + mime type detection:

```python
MIME_MAP = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp",
    ".ogg": "audio/ogg", ".mp3": "audio/mp3", ".wav": "audio/wav",
    ".opus": "audio/opus", ".aac": "audio/aac", ".flac": "audio/flac",
    ".m4a": "audio/mp4",
}

def get_media(path: str) -> dict:
    ext = os.path.splitext(path)[1].lower()
    mime = MIME_MAP.get(ext)
    if not mime or not os.path.exists(path):
        return {}
    return {"path": path, "mime_type": mime}
```

- [ ] **Delete** `_load_whisper`, `transcribe_voice`, `describe_image`, `get_image_base64` methods
- [ ] **Replace** with single `get_media(path) -> dict` returning path + mime_type
- [ ] **Remove** `faster-whisper`, `Pillow` from requirements.txt (Gemini SDK handles internally — keep Pillow only if needed elsewhere)
- [ ] **In `context_builder.py`**: `_image_ctx` and `_voice_ctx` now just resolve paths and return `{"path": ..., "mime_type": ...}`
- [ ] **In `router.py`**: read file bytes + mime_type → pass as `genai.protos.Blob` inline
- [ ] Voice notes and images now route through **same API call** as text — no separate transcription pass, no extra cost

### 2.5 prompts.py

- [ ] **Reason style**: study sample_messages reasons → update the prompt instruction to match length + tone
- [ ] **Message type calibration**: if sample shows `promotion` is rare and `business_update` is common, say so in prompt
- [ ] **Add direct mention detection**: check if `message_text` contains `@` or user's name
- [ ] **Quiet hours logic**: pass current hour extracted from `created_at` + quiet hours range to prompt explicitly as "IS IN QUIET HOURS: yes/no" — don't make Gemini calculate it
- [ ] **Voice prompt addition**: when audio is present, add to prompt: `"A voice note is attached. Transcribe it, then use the content and tone in your routing decision."` — Gemini will do both in one pass
- [ ] **Image prompt addition**: when image is present, add: `"An image is attached. Identify if it is promotional, informational, scam-related, or personal before routing."`

---

## PHASE 3 — IMPROVEMENTS BEYOND BASELINE

### 3.1 Pre-compute quiet hours flag

Before calling LLM, compute whether message arrives in quiet hours.
Pass as explicit boolean in prompt instead of raw times.

```python
# In context_builder.py _user_ctx or build()
from utils import is_in_quiet_hours
in_quiet = is_in_quiet_hours(msg.get("created_at",""), user.get("quiet_hours_start",""), user.get("quiet_hours_end",""))
context["in_quiet_hours"] = in_quiet
```

- [ ] Add `utils.py` with `is_in_quiet_hours(timestamp, start, end) -> bool`
- [ ] Add `is_in_quiet_hours` to prompt as explicit field

### 3.2 Pre-compute scam score

Run keyword scam check before LLM. If high confidence scam → skip LLM, output mute directly. Saves cost + time.

```python
SCAM_PATTERNS = [
    r'\b(won|winner|congratulations).{0,30}(lottery|prize|reward|cash)\b',
    r'\bkbc\b',
    r'\bsend\s+(your\s+)?(otp|pin|password)\b',
    r'\bclaim\s+your\s+(prize|reward|money|cash)\b',
    r'\b(free\s+iphone|free\s+gift|free\s+laptop)\b',
    r'\bverify\s+your\s+(account|whatsapp|number)\b',
    r'\bclick\s+(here|the\s+link).{0,30}(win|claim|verify)\b',
]
```

- [ ] Add `scam_detector.py` with `detect_scam(text) -> (bool, str, float)` (is_scam, reason, confidence)
- [ ] Short-circuit in `main.py`: if `detect_scam` triggers → write mute/scam row directly, skip API call
- [ ] Log how many were short-circuited (saves API cost)

### 3.3 Gemini free tier rate limit management

Free tier limits (Gemini 2.0 Flash): **15 RPM, 1,500 RPD, 1M TPM**.

- [ ] Set `SLEEP_SEC=4.0` in `.env` (= 15 RPM ceiling: 60s ÷ 15 = 4s per call)
- [ ] With scam short-circuit (Phase 3.2), actual API calls drop — real throughput closer to 10–12 RPM
- [ ] Estimate run time: `n_messages × 4s ÷ 60 = minutes`. 300 messages ≈ 20 min. 500 messages ≈ 33 min.
- [ ] Add retry with exponential backoff on `429 ResourceExhausted`:
  ```python
  import time
  for attempt in range(3):
      try:
          response = self.model.generate_content(...)
          break
      except Exception as e:
          if "429" in str(e) or "quota" in str(e).lower():
              time.sleep(30 * (attempt + 1))
          else:
              raise
  ```
- [ ] **Data privacy**: on free tier, Google may use prompts for model training. Dataset contains user messages — acceptable for a hackathon, but add note to README.
- [ ] **Model choice**: use `gemini-2.0-flash` (1,500 RPD free) not `gemini-2.5-pro` (100 RPD free) — flash is faster, cheaper, sufficient for routing

### 3.5 Direct mention detection

WhatsApp direct mentions are `@+phonenumber` or `@username` in text. If user is mentioned → strong notify signal.

```python
import re
def has_direct_mention(text: str, user_phone: str = "") -> bool:
    if "@" in str(text):
        return True
    # Also check name mention if user profile has name
    return False
```

- [ ] Add `has_direct_mention` to `utils.py`
- [ ] Pass as explicit field in prompt: `"Direct mention: yes/no"`

### 3.6 Forwarded count handling

High forwarded_count + scam-adjacent content = strong mute signal. Pre-compute:

```python
fwd = int(msg.get("forwarded_count", 0) or 0)
if fwd > 5:
    # Add to prompt as "HIGH FORWARD COUNT — likely viral misinformation or spam"
```

- [ ] Add explicit `high_forward_risk` bool to prompt context
- [ ] If `fwd > 10` AND scam keywords → short-circuit to mute

### 3.7 Better evidence selection

Current text similarity is keyword overlap. Improve:

- [ ] Check if same image `media_id` appeared before (exact duplicate detection)
- [ ] Check `forwarded_count` on historical messages from same chain
- [ ] Prioritize evidence where user took strong action (reported > dismissed > opened)
- [ ] Add `evidence_count` cap: never return more than 3 IDs, quality over quantity

### 3.8 Confidence calibration

Current confidence from LLM is often over-confident. Add post-processing:

```python
def calibrate_confidence(confidence: float, context: dict) -> float:
    # Reduce confidence if minimal context available
    has_history = bool(context.get("history", {}).get("total_messages"))
    has_user = bool(context.get("user"))
    
    if not has_history and not has_user:
        confidence = min(confidence, 0.65)
    return confidence
```

- [ ] Add calibration step in `router.route()` after parsing

---

## PHASE 4 — TESTING

### 4.1 Unit tests

- [ ] Test `EvidenceRetriever.find_evidence` with mocked DataFrames
- [ ] Test `_parse` in `router.py` with malformed JSON, missing fields, wrong enum values
- [ ] Test `is_in_quiet_hours` edge cases: midnight crossing, exact boundary
- [ ] Test `detect_scam` against known scam phrases

### 4.2 Single message smoke test

```bash
# Create a test script
python -c "
import pandas as pd
from context_builder import ContextBuilder
from router import MessageRouter

ctx = ContextBuilder('dataset')
router = MessageRouter()

# Pick first row from messages.csv
msg = pd.read_csv('dataset/messages.csv').iloc[0].to_dict()
print('Message:', msg)
context = ctx.build(msg)
result = router.route(msg, context)
print('Result:', result)
"
```

- [ ] Run single message test → check all fields present
- [ ] Run on a known scam message (find one in sample_messages with action=mute, type=scam)
- [ ] Run on a known personal notify message
- [ ] Run on an image message → verify image bytes sent inline to Gemini (not a separate description call)
- [ ] Run on a voice note → verify audio bytes sent inline to Gemini (no whisper, no ffmpeg)

### 4.3 Sample evaluation

```bash
python main.py
# Check output.csv
# Check evaluation printout
```

- [ ] Action accuracy > 70% on sample_messages
- [ ] Message type accuracy > 60% on sample_messages
- [ ] Calibration delta > 0 (confident when right, less confident when wrong)
- [ ] No "none" evidence for >50% of messages (if history exists)
- [ ] No empty reason fields

---

## PHASE 5 — PROMPT TUNING

After seeing evaluation results:

### 5.1 Error analysis

```python
import pandas as pd
preds = pd.read_csv("output.csv")
gt = pd.read_csv("dataset/sample_messages.csv")
merged = preds.merge(gt, on="message_id", suffixes=("_pred","_gt"))
wrong = merged[merged["action_pred"] != merged["action_gt"]]
print(wrong[["message_id","action_pred","action_gt","reason_pred","message_type_gt"]].to_string())
```

- [ ] Find top 3 error patterns (e.g., "digest predicted as notify", "promotion predicted as scam")
- [ ] Add explicit rules to system prompt for each error pattern
- [ ] Re-run evaluation after each prompt change

### 5.2 Common fixes to try

- [ ] If over-notifying group messages → add: "Group messages without direct mention default to digest unless emergency keywords present"
- [ ] If under-muting promotions → add: "Any business message where user has no opt-in and no order history → prefer digest or mute over notify"
- [ ] If misclassifying payment messages → add explicit payment handling: "Payment messages from unknown senders → scam. From known contacts with prior messages → notify"
- [ ] If reasons too generic → add to prompt: "Reference specific context: sender name, group type, forwarded count, business name"

---

## PHASE 6 — FULL RUN

- [ ] Run `python main.py` on full `messages.csv`
- [ ] Verify `output.csv` row count == `messages.csv` row count
- [ ] Verify no empty rows, no missing columns
- [ ] Verify `action` only contains: notify/digest/mute
- [ ] Verify `message_type` only contains valid values
- [ ] Verify `confidence` between 0 and 1
- [ ] Verify `evidence_message_ids`: either "none" or semicolon-separated IDs (no spaces around semicolons)
- [ ] Spot-check 10 rows manually

```python
import pandas as pd
df = pd.read_csv("output.csv")
print(df.shape)
print(df.isnull().sum())
print(df["action"].value_counts())
print(df["message_type"].value_counts())
print(df["confidence"].describe())
assert df["action"].isin(["notify","digest","mute"]).all(), "BAD ACTION"
assert (df["confidence"] >= 0).all() and (df["confidence"] <= 1).all(), "BAD CONFIDENCE"
assert df["evidence_message_ids"].notna().all(), "NULL EVIDENCE"
print("VALIDATION PASSED")
```

---

## PHASE 7 — SUBMISSION PREP

### 7.1 output.csv
- [ ] Final `output.csv` verified (Phase 6 validation passed)
- [ ] Column order matches exactly: `message_id, action, message_type, reason, confidence, evidence_message_ids`
- [ ] No BOM, no extra index column (use `to_csv(index=False)`)

### 7.2 code.zip
Items to INCLUDE:
- [ ] `main.py`
- [ ] `context_builder.py`
- [ ] `router.py`
- [ ] `media_processor.py`
- [ ] `evidence_retriever.py`
- [ ] `prompts.py`
- [ ] `evaluator.py`
- [ ] `requirements.txt`
- [ ] `README.md`
- [ ] `.env.example`

Items to EXCLUDE:
- [ ] `.env` (has API key)
- [ ] `dataset/` folder
- [ ] `__pycache__/`
- [ ] `*.pyc`
- [ ] `.venv/` or `venv/`
- [ ] `output.csv` (submitted separately)

```bash
cd /path/to/code
zip -r code.zip . \
  --exclude "*.pyc" \
  --exclude "__pycache__/*" \
  --exclude ".env" \
  --exclude "dataset/*" \
  --exclude "*.csv" \
  --exclude ".venv/*" \
  --exclude "venv/*"
```

### 7.3 Chat transcript
- [ ] HackerRank generates `log.txt` automatically — locate path shown in problem statement
- [ ] Alternatively: export this conversation as transcript

### 7.4 Final checklist before submit

- [ ] `output.csv` rows == `messages.csv` rows
- [ ] `code.zip` unzips and `python main.py` runs without errors (test in clean env)
- [ ] README has clear setup instructions with exact commands
- [ ] API key is NOT in any submitted file

---

## PHASE 8 — AI JUDGE PREP (after submission)

Judge will ask about design decisions. Prepare answers:

- [ ] **Why LLM over rules?** Rules can't handle ambiguous context (same message, different users, different actions). LLM reasons over all signals together.
- [ ] **How personalization works?** User's quiet hours, engagement history (reply/dismiss/report rates), group mute state, business opt-in status — all passed as structured context.
- [ ] **How multimodal handled?** Images and voice notes sent inline to Gemini's native multimodal API — no separate transcription step, no whisper, no ffmpeg. Gemini transcribes voice and reads images in the same call that makes the routing decision. Supports `.ogg` (WhatsApp's native format) directly.
- [ ] **Why Gemini over Anthropic/OpenAI?** Only provider with a permanent free tier covering text + image + audio in one call. 1,500 req/day at zero cost. No credit card. Anthropic has no permanent free tier; OpenAI's free tier excludes audio.
- [ ] **How evidence selected?** Four strategies: same sender, same business, same group + negative events, keyword text similarity. Prioritized by action severity (reported > dismissed > read).
- [ ] **What's the fallback?** If API fails → keyword scam detection + conversation_type rule. Never crashes.
- [ ] **How evaluated?** Automated comparison vs sample_messages.csv on action accuracy, type accuracy, confidence calibration.
- [ ] **What would you improve with more time?** Embedding-based evidence retrieval, fine-tuned scam classifier, async batching for speed, caching seen patterns.

---

## QUICK REFERENCE

```bash
# Verify Gemini API key
python -c "import google.generativeai as genai, os; genai.configure(api_key=os.environ['GOOGLE_API_KEY']); print(genai.GenerativeModel('gemini-2.0-flash').generate_content('ping').text)"

# Full run
python main.py

# Single message test
python -c "
import pandas as pd; from context_builder import ContextBuilder; from router import MessageRouter
ctx = ContextBuilder('dataset'); r = MessageRouter()
msg = pd.read_csv('dataset/messages.csv').iloc[0].to_dict()
print(r.route(msg, ctx.build(msg)))
"

# Validate output
python -c "
import pandas as pd
df = pd.read_csv('output.csv')
assert df['action'].isin(['notify','digest','mute']).all()
assert (df['confidence'].between(0,1)).all()
assert df['evidence_message_ids'].notna().all()
print(f'VALID: {len(df)} rows')
print(df['action'].value_counts())
"

# Package for submission
zip -r code.zip . --exclude "*.pyc" --exclude "__pycache__/*" --exclude ".env" --exclude "dataset/*" --exclude "*.csv" --exclude ".venv/*"
```
