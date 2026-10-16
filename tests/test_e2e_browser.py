#!/usr/bin/env python3
"""
End-to-end browser test for the web UI (Playwright, headless Chromium).

Generates real speech with espeak-ng (two different voices), uploads it through
the page with speaker detection on, waits for the job card to complete and
checks the downloaded transcript.

Usage:
    TEST_BASE_URL=http://localhost:5731 pytest tests/test_e2e_browser.py

Requires: playwright (chromium), espeak-ng and ffmpeg on PATH.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright, expect

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:5731")
JOB_TIMEOUT_MS = 600_000

pytestmark = pytest.mark.skipif(
    not (shutil.which("espeak-ng") and shutil.which("ffmpeg")),
    reason="espeak-ng and ffmpeg are needed to synthesize test speech",
)


def _make_two_speaker_wav(path: Path):
    """Two voices, a pause between them, 16 kHz mono."""
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "a.wav", Path(tmp) / "b.wav"
        subprocess.run(["espeak-ng", "-v", "en-us", "-s", "150", "-w", str(a),
                        "Good morning. The quick brown fox jumps over the lazy dog. "
                        "We are testing the transcription system today."], check=True)
        subprocess.run(["espeak-ng", "-v", "en-gb+f3", "-p", "80", "-s", "140", "-w", str(b),
                        "Thank you. The weather is sunny and the meeting starts at ten o'clock. "
                        "Please send the report before lunch."], check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(a), "-i", str(b),
                        "-filter_complex", "[0]apad=pad_dur=1[a0];[a0][1]concat=n=2:v=0:a=1",
                        "-ar", "16000", "-ac", "1", str(path)], check=True)


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pg = browser.new_page()
        pg.goto(BASE_URL)
        yield pg
        browser.close()


def test_page_loads(page):
    assert page.title() != ""
    expect(page.locator("#uploadBox")).to_be_visible()
    expect(page.locator("#uploadBtn")).to_be_disabled()
    for asset in ("/static/js/app.js", "/static/css/style.css"):
        assert page.request.get(BASE_URL + asset).ok, asset


def test_transcribe_two_speakers_through_ui(page):
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "two_speakers.wav"
        _make_two_speaker_wav(wav)

        page.locator("#modelSelect").select_option("base")
        page.locator("#speakerDiarization").set_checked(True, force=True)
        page.locator("#numSpeakers").fill("2")
        page.locator("#fileInput").set_input_files(str(wav))
        expect(page.locator("#uploadBtn")).to_be_enabled()
        page.locator("#uploadBtn").click()

        card = page.locator(".job-card", has_text="two_speakers.wav")
        expect(card).to_be_visible(timeout=30_000)
        expect(card.locator(".job-status")).to_have_class(
            re.compile(r"status-(completed|failed)"), timeout=JOB_TIMEOUT_MS)
        expect(card.locator(".job-status")).to_have_class(re.compile(r"status-completed"))

        links = card.locator(".download-link")
        expect(links.first).to_be_visible()
        names = [l.get_attribute("href") for l in links.all()]
        assert any(n.endswith(".json") for n in names), names

        text = ""
        for href in names:
            resp = page.request.get(BASE_URL + href)
            assert resp.ok, (href, resp.status)
            text += resp.text().lower()

        # espeak is robotic; check words Whisper reliably gets from it
        assert "lazy dog" in text
        assert "report" in text
        # Both voices must be told apart (needs per-utterance segments, not 30s chunks)
        assert "speaker_00" in text and "speaker_01" in text, "expected two speakers in output"
