"""
test_audio.py — Verify your Piper installation and voice model are working.

Run this before using audio_feed.py to confirm everything is set up correctly.

Usage:
    python test_audio.py
"""

import subprocess
import sys
from pathlib import Path

VOICE_MODEL = Path("~/preprint-fetcher-pod/voices/en_US-libritts-high.onnx").expanduser()
OUTPUT      = Path("/tmp/biorxiv_test.wav")

TEST_SCRIPT = (
    "Testing your bioRxiv audio feed setup. "
    "Piper is installed and your voice model is working correctly. "
    "You are ready to run the audio feed."
)

def test_piper():
    print("Checking Piper installation...")
    result = subprocess.run(
        [sys.executable, "-m", "piper", "--help"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("✗ Piper not found.")
        print("  Install with: pip install piper-tts")
        return False
    print("✓ Piper found")
    return True


def test_voice_model():
    print("Checking voice model...")
    if not VOICE_MODEL.exists():
        print(f"✗ Voice model not found at {VOICE_MODEL}")
        print("  Download with:")
        print("    mkdir -p ~/preprint-fetcher-pod/voices && cd ~/preprint-fetcher-pod/voices")
        print("    curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-libritts-high.onnx")
        print("    curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-libritts-high.onnx.json")
        return False
    print(f"✓ Voice model found at {VOICE_MODEL}")
    return True


def test_synthesis():
    print("Synthesizing test audio...")
    process = subprocess.run(
        [sys.executable, "-m", "piper", "--model", str(VOICE_MODEL), "--output_file", str(OUTPUT)],
        input=TEST_SCRIPT,
        text=True,
        capture_output=True
    )
    if process.returncode != 0:
        print(f"✗ Synthesis failed: {process.stderr}")
        return False
    print(f"✓ Audio generated → {OUTPUT}")
    return True


def test_playback():
    print("Playing test audio...")
    subprocess.run(["afplay", str(OUTPUT)])
    print("✓ Playback complete")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("bioRxiv Audio Feed — Piper Setup Test")
    print("=" * 50)
    print()

    steps = [test_piper, test_voice_model, test_synthesis, test_playback]
    for step in steps:
        if not step():
            print("\n✗ Setup incomplete — fix the issue above and rerun.")
            break
        print()
    else:
        print("=" * 50)
        print("✓ All checks passed. Run: python audio_feed.py")
        print("=" * 50)
