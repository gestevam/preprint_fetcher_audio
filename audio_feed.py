"""
audio_feed.py — Generates and plays a daily bioRxiv audio feed using Piper TTS.

Fully local — no data leaves your machine. No API key, no account, no cost.
Uses piper-tts installed via pip with a local neural voice model.

Usage:
    python audio_feed.py              # generate and play
    python audio_feed.py --list       # print script without speaking
    python audio_feed.py --no-play    # generate WAV only, don't play
"""

from __future__ import annotations

import json
import re
import subprocess
import argparse
import sys
from pathlib import Path

FEED_PATH   = Path("./feed_output/feed.json")
AUDIO_PATH  = Path("./feed_output/feed.wav")
VOICE_MODEL = Path("~/preprint-fetcher-pod/voices/en_US-libritts-high.onnx").expanduser()

FINDING_PHRASES = [
    "we show", "we found", "we demonstrate", "we report", "we reveal",
    "we identify", "we describe", "we present", "we develop", "we establish",
    "our results", "our findings", "our data", "our analysis",
    "this study", "these results", "these findings",
    "we observed", "we detected", "we confirmed", "we validated",
    "importantly", "strikingly", "notably", "surprisingly",
    "together,", "together these", "in summary", "in conclusion",
    "we propose", "we suggest",
]

def extract_findings(abstract: str, max_sentences: int = 3) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', abstract.strip())
    if not sentences:
        return abstract[:300]
    scored = []
    for i, sent in enumerate(sentences):
        sent_lower = sent.lower()
        score = sum(1 for phrase in FINDING_PHRASES if phrase in sent_lower)
        position_bonus = i / len(sentences) * 0.5
        scored.append((score + position_bonus, i, sent))
    scored.sort(reverse=True)
    top = sorted(scored[:max_sentences], key=lambda x: x[1])
    result = " ".join(s for _, _, s in top if s.strip())
    if not result.strip() or all(s == 0 for s, _, _ in scored[:max_sentences]):
        result = " ".join(sentences[-2:])
    return result


def build_script(data) -> str:
    preprints = data.get("preprints", [])
    total     = len(preprints)

    if total == 0:
        return "Here is your preprint feed. No papers matched your filters today. Check back tomorrow."

    lines = []
    lines.append("Here is your preprint feed.")
    lines.append(f"{total} paper{'s' if total != 1 else ''} matched today.")

    for i, p in enumerate(preprints, 1):
        title    = p.get("title", "Untitled")
        authors  = p.get("authors", [])
        abstract = p.get("abstract", "")

        if len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]} and {authors[1]}"
        else:
            last_name = authors[-1].split()[0]
            author_str = f"{authors[0]} from the {last_name} group, and colleagues"

        finding = extract_findings(abstract)

        lines.append(f"Paper {i} of {total}.")
        lines.append(title + ".")
        lines.append(f"By {author_str}.")
        lines.append("Key findings.")
        lines.append(finding)

    lines.append("That is your preprint feed for today.")
    return " ".join(lines)


def check_piper() -> bool:
    if not VOICE_MODEL.exists():
        print(f"Voice model not found at {VOICE_MODEL}")
        print("Download with:")
        print("  mkdir -p ~/preprint-fetcher-pod/voices && cd ~/preprint-fetcher-pod/voices")
        print("  curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-libritts-high.onnx")
        print("  curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-libritts-high.onnx.json")
        return False
    return True


def generate_wav(script: str, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.run(
        [sys.executable, "-m", "piper", "--model", str(VOICE_MODEL), "--output_file", str(output_path)],
        input=script,
        text=True,
        capture_output=True
    )
    if process.returncode != 0:
        raise RuntimeError(f"Piper error: {process.stderr}")
    print(f"✓ Audio saved → {output_path}")


def play_wav(path: Path):
    subprocess.run(["afplay", str(path)])


def convert_to_mp3(wav_path: Path) -> Path:
    mp3_path = wav_path.with_suffix(".mp3")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-qscale:a", "2", str(mp3_path)],
        capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr.decode()}")
    print(f"✓ MP3 saved → {mp3_path}")
    return mp3_path


def run(list_only: bool = False, no_play: bool = False):
    if not FEED_PATH.exists():
        print("No feed found. Run biorxiv_fetcher.py first.")
        return

    data   = json.loads(FEED_PATH.read_text())
    script = build_script(data)
    total  = len(data.get("preprints", []))

    if list_only:
        print(script)
        return

    if total == 0:
        print("No papers today.")
        return

    if not check_piper():
        return

    print(f"Generating audio for {total} paper{'s' if total != 1 else ''}...")
    try:
        generate_wav(script, AUDIO_PATH)
    except Exception as e:
        print(f"Could not generate audio: {e}")
        return

    # Convert WAV to MP3
    try:
        convert_to_mp3(AUDIO_PATH)
    except Exception as e:
        print(f"Could not convert to MP3: {e}")

    # Generate RSS feed
    try:
        from generate_rss import run as generate_rss
        generate_rss()
    except Exception as e:
        print(f"Could not generate RSS: {e}")

    if not no_play:
        print("Playing feed... Press Ctrl+C to stop.")
        try:
            play_wav(AUDIO_PATH)
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="bioRxiv Audio Feed")
    parser.add_argument("--list",    action="store_true", help="Print script without speaking")
    parser.add_argument("--no-play", action="store_true", help="Generate WAV only, don't play")
    args = parser.parse_args()
    run(list_only=args.list, no_play=args.no_play)
