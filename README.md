# preprint-fetcher-audio

A local tool that fetches daily preprints from bioRxiv, filters by keywords and authors, generates a HTML feed, and now optional audio summary.

---

## Requirements

- Python 3.10+
- macOS (for scheduler and audio)

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/your-username/preprint-fetcher-audio.git
cd preprint-fetcher-audio

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install requests

# 4. Create your personal config
cp config.example.json config.json
```

Open `config.json` and fill in your keywords, authors, and categories.

---

## Run

```bash
source .venv/bin/activate
python biorxiv_fetcher.py
```

Opens `feed_output/index.html` in default browser automatically. Bookmark for daily use.

---

## Schedule daily refresh

```bash
# Install — runs every day at 6 AM
python scheduler.py --install-launchd

# Verify
launchctl list | grep biorxiv

# Remove
python scheduler.py --uninstall
```

---

## Audio feed (optional)

Requires Piper TTS (Python 3.11+) and a voice model.

```bash
# Install Piper
pip install piper-tts

# Download voice model
mkdir -p ~/preprint-fetcher-audio/voices && cd ~/preprint-fetcher-audio/voices
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts/high/en_US-libritts-high.onnx
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts/high/en_US-libritts-high.onnx.json

# Test setup
python test_audio.py

# Run audio feed
python audio_feed.py
```

---

## Config reference

| Field | Description |
|-------|-------------|
| `keywords` | Matched against title and abstract, case-insensitive |
| `authors` | Partial match — `"Bhatt"` matches `"Bhatt DL"` etc. Leave as `[]` for keywords only |
| `categories` | bioRxiv subject areas — full list in `config.example.json` |
| `days_back` | Days to search. Use `7` on first run, then set to `1` |
| `max_results` | Results cap per run, maximum 200 |

---

## Privacy

- One HTTPS GET to `api.biorxiv.org` per run
- No accounts, no API keys, no data stored externally
- Keywords and config never leave machine
