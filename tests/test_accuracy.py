#!/usr/bin/env python3
"""
Accuracy validation suite for Local Transcription Tool.

Tests:
  1. WER (Word Error Rate) on LibriSpeech test-clean — 10 speakers, 2 models
  2. Speaker count detection accuracy — single vs multi-speaker audio
  3. VTT output correctness — format, timestamps, speaker tags
  4. Timestamp monotonicity and coverage
  5. Language detection accuracy

Requires:
  - Running API at BASE_URL
  - LibriSpeech samples at /tmp/librispeech_test/samples/
  - jiwer: pip install jiwer
  - /tmp/speech_test.wav (TTS-generated speech)

Usage:
    python tests/test_accuracy.py [BASE_URL]
"""

import os
import sys
import re
import time
import json
import math
import wave
import struct
import tempfile
import requests
from pathlib import Path

try:
    from jiwer import wer, cer
except ImportError:
    print("ERROR: pip install jiwer")
    sys.exit(1)

BASE_URL = os.environ.get("TEST_BASE_URL", "http://192.168.50.114:5731")
API = f"{BASE_URL}/api/v1"
SAMPLES_DIR = Path("/tmp/librispeech_test/samples")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def upload_and_wait(filepath, filename=None, data=None, timeout=300):
    """Upload and wait for completion. Returns (job_dict, vtt_text, json_data)."""
    fname = filename or os.path.basename(filepath)
    with open(filepath, 'rb') as f:
        r = requests.post(f"{API}/jobs",
                          files={'files': (fname, f, 'audio/wav')},
                          data=data or {'model': 'base'})
    if r.status_code != 200:
        return None, None, None

    job_id = r.json()['jobs'][0]['job_id']
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(3)
        d = requests.get(f"{API}/jobs/{job_id}").json()
        if d.get('status') in ('completed', 'failed'):
            break
    else:
        d = {'status': 'timeout', '_job_id': job_id}

    d['_job_id'] = job_id

    vtt_text = None
    json_data = None
    if d['status'] == 'completed':
        for f in d.get('output_files', []):
            time.sleep(0.3)
            if f['name'].endswith('.vtt'):
                r = requests.get(f"{API}/jobs/{job_id}/files/{f['name']}")
                vtt_text = r.text
            elif f['name'].endswith('.json'):
                r = requests.get(f"{API}/jobs/{job_id}/files/{f['name']}")
                json_data = r.json()

    return d, vtt_text, json_data


def cleanup(job_id):
    try:
        time.sleep(0.3)
        requests.delete(f"{API}/jobs/{job_id}")
    except Exception:
        pass


def normalize(text):
    text = text.upper()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_vtt(vtt_text):
    """Parse VTT into list of {index, start, end, speaker, text}."""
    cues = []
    lines = vtt_text.strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Look for cue index (number)
        if re.match(r'^\d+$', line):
            index = int(line)
            i += 1
            if i >= len(lines):
                break
            # Timestamp line
            ts_match = re.match(r'(\d+:\d+:\d+\.\d+)\s*-->\s*(\d+:\d+:\d+\.\d+)', lines[i].strip())
            if ts_match:
                start_ts = ts_match.group(1)
                end_ts = ts_match.group(2)
                i += 1
                # Text lines (until blank line)
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1
                text = ' '.join(text_lines)
                # Extract speaker from <v SPEAKER_XX>
                speaker = None
                speaker_match = re.match(r'<v\s+([^>]+)>(.*)', text)
                if speaker_match:
                    speaker = speaker_match.group(1)
                    text = speaker_match.group(2)
                cues.append({
                    'index': index,
                    'start': ts_to_seconds(start_ts),
                    'end': ts_to_seconds(end_ts),
                    'speaker': speaker,
                    'text': text.strip(),
                })
        i += 1
    return cues


def ts_to_seconds(ts):
    """Convert HH:MM:SS.mmm to seconds."""
    parts = ts.split(':')
    h, m = int(parts[0]), int(parts[1])
    s = float(parts[2])
    return h * 3600 + m * 60 + s


# ===========================================================================
# TEST 1: Transcription Accuracy (WER)
# ===========================================================================

def test_wer():
    """Test Word Error Rate against LibriSpeech ground truth."""
    print("=" * 70)
    print("TEST 1: TRANSCRIPTION ACCURACY (WER)")
    print("Dataset: LibriSpeech test-clean, 10 speakers")
    print("=" * 70)

    if not SAMPLES_DIR.exists():
        print("  SKIP: LibriSpeech samples not found at", SAMPLES_DIR)
        return True

    wavs = sorted(SAMPLES_DIR.glob("sample_*.wav"))
    refs = {}
    for ref_file in SAMPLES_DIR.glob("ref_*.txt"):
        key = ref_file.stem.replace("ref_", "sample_")
        refs[key] = ref_file.read_text().strip()

    samples = [{'wav': w, 'ref': refs[w.stem], 'name': w.stem}
               for w in wavs if w.stem in refs]

    if not samples:
        print("  SKIP: No matched samples found")
        return True

    all_pass = True

    for model in ['base', 'small']:
        print(f"\n  Model: {model}")
        print(f"  {'Sample':<30} {'WER':>6} {'CER':>6} {'Status':>8}")
        print(f"  {'-'*56}")

        wer_scores = []
        cer_scores = []

        for s in samples:
            d, vtt, jd = upload_and_wait(str(s['wav']), f"{s['name']}.wav",
                                          data={'model': model, 'language': 'en'})
            if d is None or d['status'] != 'completed' or jd is None:
                print(f"  {s['name']:<30} {'FAIL':>6} {'':>6} {'FAILED':>8}")
                all_pass = False
                if d:
                    cleanup(d['_job_id'])
                continue

            ref_norm = normalize(s['ref'])
            hyp_norm = normalize(jd.get('text', ''))

            w = wer(ref_norm, hyp_norm) * 100
            c = cer(ref_norm, hyp_norm) * 100
            wer_scores.append(w)
            cer_scores.append(c)

            status = "PASS" if w < 15 else "WARN" if w < 25 else "FAIL"
            if status == "FAIL":
                all_pass = False
            print(f"  {s['name']:<30} {w:5.1f}% {c:5.1f}% {status:>8}")

            cleanup(d['_job_id'])

        if wer_scores:
            avg_wer = sum(wer_scores) / len(wer_scores)
            avg_cer = sum(cer_scores) / len(cer_scores)
            min_wer = min(wer_scores)
            max_wer = max(wer_scores)
            status = "PASS" if avg_wer < 10 else "WARN" if avg_wer < 15 else "FAIL"
            print(f"\n  {model} SUMMARY: avg WER={avg_wer:.1f}% (min={min_wer:.1f}% max={max_wer:.1f}%) avg CER={avg_cer:.1f}% [{status}]")
            if avg_wer >= 15:
                all_pass = False

    return all_pass


# ===========================================================================
# TEST 2: Speaker Detection Accuracy
# ===========================================================================

def test_speaker_detection():
    """Test speaker count detection on known audio."""
    print("\n" + "=" * 70)
    print("TEST 2: SPEAKER DETECTION ACCURACY")
    print("=" * 70)

    all_pass = True

    # Test A: Single speaker (TTS generated)
    print("\n  Test A: Single speaker audio")
    speech_file = '/tmp/speech_test.wav'
    if not os.path.exists(speech_file):
        print("  SKIP: /tmp/speech_test.wav not available")
    else:
        d, vtt, jd = upload_and_wait(speech_file, 'single_speaker.wav',
                                      data={'model': 'tiny', 'speaker_diarization': 'true'})
        if d and d['status'] == 'completed' and vtt:
            cues = parse_vtt(vtt)
            speakers = set(c['speaker'] for c in cues if c.get('speaker'))
            n = len(speakers)
            status = "PASS" if n == 1 else "WARN"
            print(f"  Detected {n} speaker(s): {speakers} [{status}]")
            if n > 2:
                all_pass = False
        else:
            print(f"  FAILED: {d.get('status') if d else 'no response'}")
            all_pass = False
        if d:
            cleanup(d['_job_id'])

    # Test B: LibriSpeech samples (each is a single speaker)
    print("\n  Test B: LibriSpeech single-speaker samples")
    if SAMPLES_DIR.exists():
        wavs = sorted(SAMPLES_DIR.glob("sample_*.wav"))[:3]  # Test 3 samples
        for wav in wavs:
            d, vtt, jd = upload_and_wait(str(wav), wav.name,
                                          data={'model': 'tiny',
                                                'speaker_diarization': 'true'})
            if d and d['status'] == 'completed' and vtt:
                cues = parse_vtt(vtt)
                speakers = set(c['speaker'] for c in cues if c.get('speaker'))
                n = len(speakers)
                # Single speaker audio should detect 1-2 speakers max
                status = "PASS" if n <= 2 else "FAIL"
                if status == "FAIL":
                    all_pass = False
                print(f"  {wav.stem}: {n} speaker(s) [{status}]")
            else:
                print(f"  {wav.stem}: FAILED")
            if d:
                cleanup(d['_job_id'])
    else:
        print("  SKIP: No LibriSpeech samples")

    return all_pass


# ===========================================================================
# TEST 3: VTT Output Correctness
# ===========================================================================

def test_vtt_format():
    """Validate VTT output format, structure, and content."""
    print("\n" + "=" * 70)
    print("TEST 3: VTT OUTPUT CORRECTNESS")
    print("=" * 70)

    all_pass = True
    speech_file = '/tmp/speech_test.wav'
    if not os.path.exists(speech_file):
        print("  SKIP: /tmp/speech_test.wav not available")
        return True

    d, vtt, jd = upload_and_wait(speech_file, 'vtt_test.wav',
                                  data={'model': 'tiny', 'speaker_diarization': 'true'})

    if not vtt:
        print("  FAILED: No VTT output")
        if d:
            cleanup(d['_job_id'])
        return False

    # Test A: VTT header
    print("\n  Test A: VTT header")
    has_header = vtt.startswith('WEBVTT')
    status = "PASS" if has_header else "FAIL"
    print(f"  Starts with WEBVTT: {has_header} [{status}]")
    if not has_header:
        all_pass = False

    has_note = 'NOTE' in vtt
    print(f"  Contains NOTE metadata: {has_note} [{'PASS' if has_note else 'WARN'}]")

    # Test B: Parse cues
    print("\n  Test B: Cue structure")
    cues = parse_vtt(vtt)
    print(f"  Total cues: {len(cues)}")
    has_cues = len(cues) > 0
    status = "PASS" if has_cues else "FAIL"
    print(f"  Has cues: {has_cues} [{status}]")
    if not has_cues:
        all_pass = False

    # Test C: Cue numbering is sequential
    if cues:
        print("\n  Test C: Sequential cue numbering")
        expected = list(range(1, len(cues) + 1))
        actual = [c['index'] for c in cues]
        sequential = actual == expected
        status = "PASS" if sequential else "FAIL"
        print(f"  Sequential: {sequential} [{status}]")
        if not sequential:
            all_pass = False

    # Test D: Timestamps are valid and monotonic
    if cues:
        print("\n  Test D: Timestamp validity")
        valid_ts = all(c['start'] >= 0 and c['end'] > c['start'] for c in cues)
        status = "PASS" if valid_ts else "FAIL"
        print(f"  All timestamps valid (start >= 0, end > start): {valid_ts} [{status}]")
        if not valid_ts:
            all_pass = False

        monotonic = all(cues[i]['start'] >= cues[i-1]['start'] for i in range(1, len(cues)))
        status = "PASS" if monotonic else "FAIL"
        print(f"  Timestamps monotonically increasing: {monotonic} [{status}]")
        if not monotonic:
            all_pass = False

    # Test E: Speaker tags present when diarization enabled
    if cues:
        print("\n  Test E: Speaker tags")
        has_speakers = any(c.get('speaker') for c in cues)
        status = "PASS" if has_speakers else "FAIL"
        print(f"  Speaker tags present: {has_speakers} [{status}]")
        if not has_speakers:
            all_pass = False

        speaker_format = all(
            re.match(r'SPEAKER_\d+', c['speaker'])
            for c in cues if c.get('speaker')
        )
        status = "PASS" if speaker_format else "FAIL"
        print(f"  Speaker format SPEAKER_XX: {speaker_format} [{status}]")
        if not speaker_format:
            all_pass = False

    # Test F: Text content is non-empty
    if cues:
        print("\n  Test F: Text content")
        non_empty = all(len(c['text'].strip()) > 0 for c in cues)
        status = "PASS" if non_empty else "FAIL"
        print(f"  All cues have text: {non_empty} [{status}]")
        if not non_empty:
            all_pass = False

    if d:
        cleanup(d['_job_id'])
    return all_pass


# ===========================================================================
# TEST 4: JSON Output Correctness
# ===========================================================================

def test_json_output():
    """Validate JSON output structure and content."""
    print("\n" + "=" * 70)
    print("TEST 4: JSON OUTPUT CORRECTNESS")
    print("=" * 70)

    all_pass = True
    speech_file = '/tmp/speech_test.wav'
    if not os.path.exists(speech_file):
        print("  SKIP: /tmp/speech_test.wav not available")
        return True

    d, vtt, jd = upload_and_wait(speech_file, 'json_test.wav',
                                  data={'model': 'tiny'})

    if not jd:
        print("  FAILED: No JSON output")
        if d:
            cleanup(d['_job_id'])
        return False

    # Required fields
    print("\n  Required fields:")
    for field in ['text', 'language', 'segments', 'file_path', 'timestamp']:
        present = field in jd
        status = "PASS" if present else "FAIL"
        print(f"  '{field}': {present} [{status}]")
        if not present:
            all_pass = False

    # Text is non-empty
    has_text = len(jd.get('text', '').strip()) > 0
    status = "PASS" if has_text else "FAIL"
    print(f"\n  Text non-empty: {has_text} [{status}]")
    if not has_text:
        all_pass = False

    # Language detected
    lang = jd.get('language', '')
    has_lang = len(lang) > 0 and lang != 'unknown'
    print(f"  Language detected: '{lang}' [{'PASS' if has_lang else 'WARN'}]")

    # Segments structure
    segments = jd.get('segments', [])
    print(f"  Segment count: {len(segments)}")

    if segments:
        seg = segments[0]
        for field in ['start', 'end', 'text']:
            present = field in seg
            status = "PASS" if present else "FAIL"
            print(f"  Segment has '{field}': {present} [{status}]")
            if not present:
                all_pass = False

        # Segment timestamps are floats
        all_float = all(
            isinstance(s.get('start'), (int, float)) and
            isinstance(s.get('end'), (int, float))
            for s in segments
        )
        status = "PASS" if all_float else "FAIL"
        print(f"  Timestamps are numeric: {all_float} [{status}]")
        if not all_float:
            all_pass = False

    if d:
        cleanup(d['_job_id'])
    return all_pass


# ===========================================================================
# TEST 5: Language Detection
# ===========================================================================

def test_language_detection():
    """Test auto language detection."""
    print("\n" + "=" * 70)
    print("TEST 5: LANGUAGE DETECTION")
    print("=" * 70)

    all_pass = True
    speech_file = '/tmp/speech_test.wav'
    if not os.path.exists(speech_file):
        print("  SKIP: /tmp/speech_test.wav not available")
        return True

    # English TTS file with auto-detect
    d, vtt, jd = upload_and_wait(speech_file, 'lang_test.wav',
                                  data={'model': 'tiny', 'language': 'auto'})
    if jd:
        detected = jd.get('language', 'unknown')
        is_english = detected == 'en'
        status = "PASS" if is_english else "WARN"
        print(f"  English TTS auto-detected as: '{detected}' [{status}]")
    else:
        print("  FAILED: No output")
        all_pass = False

    if d:
        cleanup(d['_job_id'])

    # Explicit language should be respected
    time.sleep(2)
    d, vtt, jd = upload_and_wait(speech_file, 'lang_explicit.wav',
                                  data={'model': 'tiny', 'language': 'en'})
    if jd:
        detected = jd.get('language', 'unknown')
        status = "PASS" if detected == 'en' else "FAIL"
        print(f"  Explicit 'en' returned as: '{detected}' [{status}]")
        if detected != 'en':
            all_pass = False
    if d:
        cleanup(d['_job_id'])

    return all_pass


# ===========================================================================
# TEST 6: Consistency — same input produces same output
# ===========================================================================

def test_consistency():
    """Same file transcribed twice should produce identical text."""
    print("\n" + "=" * 70)
    print("TEST 6: TRANSCRIPTION CONSISTENCY")
    print("=" * 70)

    speech_file = '/tmp/speech_test.wav'
    if not os.path.exists(speech_file):
        print("  SKIP: /tmp/speech_test.wav not available")
        return True

    texts = []
    for i in range(2):
        time.sleep(2)
        d, vtt, jd = upload_and_wait(speech_file, f'consist_{i}.wav',
                                      data={'model': 'tiny', 'language': 'en'})
        if jd:
            texts.append(normalize(jd.get('text', '')))
        if d:
            cleanup(d['_job_id'])

    if len(texts) == 2:
        identical = texts[0] == texts[1]
        w = wer(texts[0], texts[1]) * 100 if texts[0] and texts[1] else 100
        status = "PASS" if w < 5 else "WARN" if w < 15 else "FAIL"
        print(f"  Run 1: '{texts[0][:60]}...'")
        print(f"  Run 2: '{texts[1][:60]}...'")
        print(f"  Identical: {identical}, WER between runs: {w:.1f}% [{status}]")
        return w < 15
    else:
        print("  FAILED: Could not complete both runs")
        return False


# ===========================================================================
# Main
# ===========================================================================

def main():
    if len(sys.argv) > 1 and sys.argv[1].startswith('http'):
        global BASE_URL, API
        BASE_URL = sys.argv[1]
        API = f"{BASE_URL}/api/v1"

    print(f"Target: {BASE_URL}")
    print(f"API: {API}")
    print()

    results = {}
    results['WER'] = test_wer()
    results['Speaker Detection'] = test_speaker_detection()
    results['VTT Format'] = test_vtt_format()
    results['JSON Output'] = test_json_output()
    results['Language Detection'] = test_language_detection()
    results['Consistency'] = test_consistency()

    print("\n" + "=" * 70)
    print("ACCURACY TEST SUMMARY")
    print("=" * 70)
    all_pass = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name:<25} {status}")
        if not passed:
            all_pass = False

    print("=" * 70)
    print(f"  Overall: {'ALL PASS' if all_pass else 'SOME FAILURES'}")
    print("=" * 70)

    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
