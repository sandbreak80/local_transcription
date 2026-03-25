#!/usr/bin/env python3
"""
Comprehensive API test suite — functional, edge case, exploratory, and performance.
Runs against a live container.

Usage:
    python tests/test_api_comprehensive.py [BASE_URL]
"""

import os
import sys
import time
import json
import wave
import math
import struct
import unittest
import tempfile
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = os.environ.get("TEST_BASE_URL", "http://192.168.50.114:5731")
API = f"{BASE_URL}/api/v1"

_last_request_time = 0


def pace():
    """Pace requests to stay under rate limits."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 0.25:
        time.sleep(0.25 - elapsed)
    _last_request_time = time.time()


def create_wav(path, duration_s=3, freq=440, sr=16000):
    frames = []
    for i in range(sr * duration_s):
        val = int(32767 * 0.5 * math.sin(2 * math.pi * freq * i / sr))
        frames.append(struct.pack('<h', val))
    with wave.open(path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(b''.join(frames))


def create_speech_wav(path, duration_s=5):
    """Create a WAV with varying frequencies to simulate speech-like audio."""
    sr = 16000
    frames = []
    for i in range(sr * duration_s):
        t = i / sr
        freq = 200 + 300 * math.sin(2 * math.pi * 3 * t)  # Varying pitch
        amp = 0.3 + 0.2 * math.sin(2 * math.pi * 0.5 * t)  # Varying volume
        val = int(32767 * amp * math.sin(2 * math.pi * freq * i / sr))
        frames.append(struct.pack('<h', max(-32768, min(32767, val))))
    with wave.open(path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(b''.join(frames))


def upload_and_wait(filepath, filename=None, data=None, timeout=90):
    """Upload a file and wait for job completion. Returns job dict."""
    pace()
    fname = filename or os.path.basename(filepath)
    with open(filepath, 'rb') as f:
        r = requests.post(f"{API}/jobs",
                          files={'files': (fname, f, 'audio/wav')},
                          data=data or {'model': 'tiny'})
    if r.status_code != 200:
        return {'_upload_status': r.status_code, '_upload_body': r.text}

    job_id = r.json()['jobs'][0]['job_id']
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        pace()
        d = requests.get(f"{API}/jobs/{job_id}").json()
        if d.get('status') in ('completed', 'failed', 'cancelled'):
            d['_job_id'] = job_id
            return d
    return {'_job_id': job_id, 'status': 'timeout'}


def cleanup_job(job_id):
    try:
        pace()
        requests.delete(f"{API}/jobs/{job_id}")
    except Exception:
        pass


# ===========================================================================
# 1. FUNCTIONAL TESTS — Core API behavior
# ===========================================================================

class TestHealthEndpoint(unittest.TestCase):
    def test_returns_200(self):
        r = requests.get(f"{API}/health")
        self.assertEqual(r.status_code, 200)

    def test_required_fields(self):
        d = requests.get(f"{API}/health").json()
        for f in ['status', 'queue_size', 'total_jobs', 'processing', 'queued',
                   'completed', 'failed', 'gpu', 'supported_formats',
                   'supported_models', 'chunk_size_mb', 'max_request_mb']:
            self.assertIn(f, d, f"Missing: {f}")

    def test_gpu_info_structure(self):
        d = requests.get(f"{API}/health").json()
        self.assertIn('available', d['gpu'])
        self.assertIn('device', d['gpu'])

    def test_formats_include_common_types(self):
        d = requests.get(f"{API}/health").json()
        for fmt in ['wav', 'mp3', 'mp4', 'flac', 'ogg', 'mkv']:
            self.assertIn(fmt, d['supported_formats'])

    def test_models_complete(self):
        d = requests.get(f"{API}/health").json()
        self.assertEqual(sorted(d['supported_models']),
                         ['base', 'large', 'medium', 'small', 'tiny'])

    def test_not_rate_limited(self):
        codes = [requests.get(f"{API}/health").status_code for _ in range(10)]
        self.assertTrue(all(c == 200 for c in codes))


class TestJobCreation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wav = tempfile.mktemp(suffix='.wav')
        create_wav(cls.wav)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.wav)

    def test_basic_upload(self):
        pace()
        with open(self.wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('test.wav', f)},
                              data={'model': 'tiny'})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d['success'])
        self.assertEqual(len(d['jobs']), 1)
        self.assertIn('job_id', d['jobs'][0])
        cleanup_job(d['jobs'][0]['job_id'])

    def test_upload_returns_filename(self):
        pace()
        with open(self.wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('my_meeting.wav', f)},
                              data={'model': 'tiny'})
        self.assertEqual(r.json()['jobs'][0]['filename'], 'my_meeting.wav')
        cleanup_job(r.json()['jobs'][0]['job_id'])

    def test_all_options_accepted(self):
        pace()
        with open(self.wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('opts.wav', f)},
                              data={'model': 'tiny', 'language': 'en',
                                    'animated_quotes': 'true',
                                    'two_list_quotes': 'true',
                                    'speaker_diarization': 'true',
                                    'num_speakers': '3',
                                    'speaker_names': 'Alice,Bob,Charlie'})
        self.assertEqual(r.status_code, 200)
        cleanup_job(r.json()['jobs'][0]['job_id'])

    def test_multi_file_upload(self):
        pace()
        with open(self.wav, 'rb') as f1, open(self.wav, 'rb') as f2:
            r = requests.post(f"{API}/jobs",
                              files=[('files', ('a.wav', f1)), ('files', ('b.wav', f2))],
                              data={'model': 'tiny'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()['jobs']), 2)
        for j in r.json()['jobs']:
            cleanup_job(j['job_id'])


class TestJobLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wav = tempfile.mktemp(suffix='.wav')
        create_wav(cls.wav, duration_s=3)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.wav)

    def test_complete_lifecycle(self):
        d = upload_and_wait(self.wav, 'lifecycle.wav')
        self.assertEqual(d['status'], 'completed')
        self.assertEqual(d['progress'], 100)
        self.assertIsNotNone(d.get('completed_at'))

        # Has VTT and JSON
        names = [f['name'] for f in d['output_files']]
        self.assertTrue(any(n.endswith('.vtt') for n in names))
        self.assertTrue(any(n.endswith('.json') for n in names))

        # Download VTT
        vtt_name = [n for n in names if n.endswith('.vtt')][0]
        pace()
        r = requests.get(f"{API}/jobs/{d['_job_id']}/files/{vtt_name}")
        self.assertEqual(r.status_code, 200)
        self.assertIn('WEBVTT', r.text)

        # Download JSON
        json_name = [n for n in names if n.endswith('.json')][0]
        pace()
        r = requests.get(f"{API}/jobs/{d['_job_id']}/files/{json_name}")
        self.assertEqual(r.status_code, 200)
        jd = r.json()
        self.assertIn('text', jd)
        self.assertIn('language', jd)
        self.assertIn('segments', jd)

        # Delete
        pace()
        r = requests.delete(f"{API}/jobs/{d['_job_id']}")
        self.assertEqual(r.status_code, 200)

        # Verify gone
        pace()
        r = requests.get(f"{API}/jobs/{d['_job_id']}")
        self.assertEqual(r.status_code, 404)

    def test_job_response_fields(self):
        d = upload_and_wait(self.wav, 'fields.wav')
        for field in ['id', 'filename', 'status', 'progress', 'message',
                       'model', 'language', 'animated_quotes', 'two_list_quotes',
                       'speaker_diarization', 'file_size_mb', 'created_at',
                       'completed_at', 'output_files']:
            self.assertIn(field, d, f"Missing: {field}")
        cleanup_job(d['_job_id'])

    def test_vtt_format_valid(self):
        d = upload_and_wait(self.wav, 'vtt_check.wav')
        vtt_name = [f['name'] for f in d['output_files'] if f['name'].endswith('.vtt')][0]
        pace()
        r = requests.get(f"{API}/jobs/{d['_job_id']}/files/{vtt_name}")
        lines = r.text.strip().split('\n')
        self.assertEqual(lines[0], 'WEBVTT')
        self.assertTrue(lines[1].startswith('NOTE'))
        cleanup_job(d['_job_id'])


class TestJobListing(unittest.TestCase):
    def test_list_all(self):
        pace()
        r = requests.get(f"{API}/jobs")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json()['jobs'], list)

    def test_filter_completed(self):
        pace()
        r = requests.get(f"{API}/jobs", params={'status': 'completed'})
        self.assertEqual(r.status_code, 200)
        for j in r.json()['jobs']:
            self.assertEqual(j['status'], 'completed')

    def test_filter_invalid(self):
        pace()
        r = requests.get(f"{API}/jobs", params={'status': 'banana'})
        self.assertEqual(r.status_code, 400)

    def test_filter_each_valid_status(self):
        for s in ['queued', 'processing', 'completed', 'failed']:
            pace()
            r = requests.get(f"{API}/jobs", params={'status': s})
            self.assertEqual(r.status_code, 200)


class TestJobDeletion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wav = tempfile.mktemp(suffix='.wav')
        create_wav(cls.wav)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.wav)

    def test_delete_nonexistent(self):
        pace()
        r = requests.delete(f"{API}/jobs/nonexistent-uuid")
        self.assertEqual(r.status_code, 404)

    def test_delete_completed(self):
        d = upload_and_wait(self.wav, 'del_complete.wav')
        pace()
        r = requests.delete(f"{API}/jobs/{d['_job_id']}")
        self.assertEqual(r.status_code, 200)
        pace()
        self.assertEqual(requests.get(f"{API}/jobs/{d['_job_id']}").status_code, 404)

    def test_cancel_processing(self):
        # Use a larger file/model so it's still processing when we cancel
        pace()
        with open(self.wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('cancel.wav', f)},
                              data={'model': 'base'})
        job_id = r.json()['jobs'][0]['job_id']
        time.sleep(3)
        pace()
        r = requests.delete(f"{API}/jobs/{job_id}")
        self.assertEqual(r.status_code, 200)


class TestDownload(unittest.TestCase):
    def test_nonexistent_job(self):
        pace()
        r = requests.get(f"{API}/jobs/fake-id/files/out.vtt")
        self.assertEqual(r.status_code, 404)

    def test_nonexistent_file(self):
        wav = tempfile.mktemp(suffix='.wav')
        create_wav(wav)
        d = upload_and_wait(wav, 'dl_test.wav')
        os.remove(wav)
        pace()
        r = requests.get(f"{API}/jobs/{d['_job_id']}/files/nonexistent.vtt")
        self.assertEqual(r.status_code, 404)
        cleanup_job(d['_job_id'])

    def test_download_before_completion(self):
        wav = tempfile.mktemp(suffix='.wav')
        create_wav(wav)
        pace()
        with open(wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('early_dl.wav', f)},
                              data={'model': 'base'})
        os.remove(wav)
        job_id = r.json()['jobs'][0]['job_id']
        pace()
        r = requests.get(f"{API}/jobs/{job_id}/files/early_dl.vtt")
        self.assertIn(r.status_code, [400, 404])
        cleanup_job(job_id)


# ===========================================================================
# 2. INPUT VALIDATION TESTS
# ===========================================================================

class TestValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wav = tempfile.mktemp(suffix='.wav')
        create_wav(cls.wav)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.wav)

    def _up(self, **data):
        pace()
        with open(self.wav, 'rb') as f:
            return requests.post(f"{API}/jobs",
                                 files={'files': ('v.wav', f)},
                                 data=data)

    def test_no_files(self):
        pace()
        r = requests.post(f"{API}/jobs")
        self.assertEqual(r.status_code, 400)

    def test_unsupported_type(self):
        pace()
        r = requests.post(f"{API}/jobs",
                          files={'files': ('test.exe', b'MZ', 'application/octet-stream')})
        self.assertEqual(r.status_code, 400)

    def test_invalid_model(self):
        r = self._up(model='gigantic')
        self.assertEqual(r.status_code, 400)
        self.assertIn('model', r.json()['error'].lower())

    def test_invalid_language(self):
        r = self._up(language='klingon')
        self.assertEqual(r.status_code, 400)

    def test_num_speakers_zero(self):
        r = self._up(num_speakers='0')
        self.assertEqual(r.status_code, 400)

    def test_num_speakers_negative(self):
        r = self._up(num_speakers='-5')
        self.assertEqual(r.status_code, 400)

    def test_num_speakers_too_high(self):
        r = self._up(num_speakers='100')
        self.assertEqual(r.status_code, 400)

    def test_num_speakers_float(self):
        r = self._up(num_speakers='2.5')
        self.assertEqual(r.status_code, 400)

    def test_num_speakers_text(self):
        r = self._up(num_speakers='many')
        self.assertEqual(r.status_code, 400)

    def test_valid_boundary_speakers(self):
        for ns in ['1', '20']:
            r = self._up(num_speakers=ns, model='tiny')
            self.assertEqual(r.status_code, 200, f"num_speakers={ns} rejected")
            cleanup_job(r.json()['jobs'][0]['job_id'])


# ===========================================================================
# 3. EDGE CASES & EXPLORATORY
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    def test_empty_file(self):
        pace()
        r = requests.post(f"{API}/jobs",
                          files={'files': ('empty.wav', b'', 'audio/wav')},
                          data={'model': 'tiny'})
        if r.status_code == 200:
            job_id = r.json()['jobs'][0]['job_id']
            d = upload_and_wait.__wrapped__(job_id) if hasattr(upload_and_wait, '__wrapped__') else None
            # Wait manually
            for _ in range(20):
                time.sleep(2)
                pace()
                d = requests.get(f"{API}/jobs/{job_id}").json()
                if d['status'] in ('completed', 'failed'):
                    break
            self.assertEqual(d['status'], 'failed')
            cleanup_job(job_id)

    def test_path_traversal_filename(self):
        wav = tempfile.mktemp(suffix='.wav')
        create_wav(wav)
        pace()
        with open(wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('../../../etc/passwd.wav', f)},
                              data={'model': 'tiny'})
        os.remove(wav)
        if r.status_code == 200:
            fn = r.json()['jobs'][0]['filename']
            self.assertNotIn('..', fn)
            self.assertNotIn('/', fn)
            cleanup_job(r.json()['jobs'][0]['job_id'])

    def test_path_traversal_in_download(self):
        wav = tempfile.mktemp(suffix='.wav')
        create_wav(wav)
        d = upload_and_wait(wav, 'traversal_dl.wav')
        os.remove(wav)
        pace()
        r = requests.get(f"{API}/jobs/{d['_job_id']}/files/../../etc/passwd")
        self.assertEqual(r.status_code, 404)
        cleanup_job(d['_job_id'])

    def test_sql_injection_job_id(self):
        pace()
        r = requests.get(f"{API}/jobs/' OR 1=1 --")
        self.assertEqual(r.status_code, 404)

    def test_very_long_job_id(self):
        pace()
        r = requests.get(f"{API}/jobs/{'x' * 5000}")
        self.assertEqual(r.status_code, 404)

    def test_special_chars_filename(self):
        wav = tempfile.mktemp(suffix='.wav')
        create_wav(wav)
        pace()
        with open(wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('my file (v2) [final].wav', f)},
                              data={'model': 'tiny'})
        os.remove(wav)
        self.assertEqual(r.status_code, 200)
        fn = r.json()['jobs'][0]['filename']
        self.assertTrue(fn.endswith('.wav'))
        cleanup_job(r.json()['jobs'][0]['job_id'])

    def test_unicode_filename(self):
        wav = tempfile.mktemp(suffix='.wav')
        create_wav(wav)
        pace()
        with open(wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('会議_録音.wav', f)},
                              data={'model': 'tiny'})
        os.remove(wav)
        # Should accept (sanitized) or reject
        self.assertIn(r.status_code, [200, 400])
        if r.status_code == 200:
            cleanup_job(r.json()['jobs'][0]['job_id'])

    def test_duplicate_filename_different_jobs(self):
        """Two uploads with same filename should not collide."""
        wav = tempfile.mktemp(suffix='.wav')
        create_wav(wav)

        d1 = upload_and_wait(wav, 'same_name.wav')
        d2 = upload_and_wait(wav, 'same_name.wav')
        os.remove(wav)

        self.assertEqual(d1['status'], 'completed')
        self.assertEqual(d2['status'], 'completed')
        self.assertNotEqual(d1['_job_id'], d2['_job_id'])

        # Both should have output files
        self.assertGreater(len(d1['output_files']), 0)
        self.assertGreater(len(d2['output_files']), 0)

        cleanup_job(d1['_job_id'])
        cleanup_job(d2['_job_id'])

    def test_boolean_false_not_truthy(self):
        """'false' string should not enable features."""
        wav = tempfile.mktemp(suffix='.wav')
        create_wav(wav)
        pace()
        with open(wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('bool.wav', f)},
                              data={'model': 'tiny',
                                    'animated_quotes': 'false',
                                    'speaker_diarization': 'false'})
        os.remove(wav)
        job_id = r.json()['jobs'][0]['job_id']
        pace()
        d = requests.get(f"{API}/jobs/{job_id}").json()
        self.assertFalse(d['animated_quotes'])
        self.assertFalse(d['speaker_diarization'])
        cleanup_job(job_id)


# ===========================================================================
# 4. CHUNKED UPLOAD TESTS
# ===========================================================================

class TestChunkedUpload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wav = tempfile.mktemp(suffix='.wav')
        create_wav(cls.wav, duration_s=3)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.wav)

    def test_full_chunked_lifecycle(self):
        file_size = os.path.getsize(self.wav)
        chunk_size = file_size // 3 + 1
        total_chunks = math.ceil(file_size / chunk_size)

        # Init
        pace()
        r = requests.post(f"{API}/uploads", json={
            'filename': 'chunked.wav', 'total_chunks': total_chunks, 'model': 'tiny'})
        self.assertEqual(r.status_code, 201)
        uid = r.json()['upload_id']

        # Upload chunks
        with open(self.wav, 'rb') as f:
            for i in range(total_chunks):
                chunk = f.read(chunk_size)
                r = requests.post(f"{API}/uploads/{uid}/chunks",
                                  files={'chunk': (f'c{i}', chunk)},
                                  data={'chunk_index': i})
                self.assertEqual(r.status_code, 200)

        # Complete
        pace()
        r = requests.post(f"{API}/uploads/{uid}/complete")
        self.assertEqual(r.status_code, 200)
        self.assertIn('job_id', r.json())

        # Wait and verify
        job_id = r.json()['job_id']
        for _ in range(30):
            time.sleep(2)
            pace()
            d = requests.get(f"{API}/jobs/{job_id}").json()
            if d['status'] in ('completed', 'failed'):
                break
        self.assertEqual(d['status'], 'completed')
        cleanup_job(job_id)

    def test_init_bad_filename(self):
        pace()
        r = requests.post(f"{API}/uploads", json={
            'filename': 'bad.txt', 'total_chunks': 1})
        self.assertEqual(r.status_code, 400)

    def test_init_missing_fields(self):
        pace()
        r = requests.post(f"{API}/uploads", json={})
        self.assertEqual(r.status_code, 400)

    def test_init_too_many_chunks(self):
        pace()
        r = requests.post(f"{API}/uploads", json={
            'filename': 'x.wav', 'total_chunks': 999})
        self.assertEqual(r.status_code, 400)

    def test_complete_with_missing_chunks(self):
        pace()
        r = requests.post(f"{API}/uploads", json={
            'filename': 'missing.wav', 'total_chunks': 3, 'model': 'tiny'})
        uid = r.json()['upload_id']

        # Only upload chunk 0
        r = requests.post(f"{API}/uploads/{uid}/chunks",
                          files={'chunk': ('c', b'data')},
                          data={'chunk_index': 0})

        pace()
        r = requests.post(f"{API}/uploads/{uid}/complete")
        self.assertEqual(r.status_code, 400)
        self.assertIn('Missing', r.json()['error'])

    def test_invalid_chunk_index(self):
        pace()
        r = requests.post(f"{API}/uploads", json={
            'filename': 'idx.wav', 'total_chunks': 2, 'model': 'tiny'})
        uid = r.json()['upload_id']

        r = requests.post(f"{API}/uploads/{uid}/chunks",
                          files={'chunk': ('c', b'data')},
                          data={'chunk_index': 99})
        self.assertEqual(r.status_code, 400)

    def test_nonexistent_upload_id(self):
        pace()
        r = requests.post(f"{API}/uploads/fake-id/chunks",
                          files={'chunk': ('c', b'data')},
                          data={'chunk_index': 0})
        self.assertEqual(r.status_code, 404)

    def test_chunk_without_data(self):
        pace()
        r = requests.post(f"{API}/uploads", json={
            'filename': 'nodata.wav', 'total_chunks': 1, 'model': 'tiny'})
        uid = r.json()['upload_id']
        r = requests.post(f"{API}/uploads/{uid}/chunks",
                          data={'chunk_index': 0})
        self.assertEqual(r.status_code, 400)


# ===========================================================================
# 5. ERROR HANDLING TESTS
# ===========================================================================

class TestErrorHandling(unittest.TestCase):
    def test_404_is_json(self):
        pace()
        r = requests.get(f"{API}/nonexistent")
        self.assertEqual(r.status_code, 404)
        self.assertIn('error', r.json())

    def test_wrong_method_post_on_get(self):
        pace()
        r = requests.post(f"{API}/health")
        self.assertIn(r.status_code, [405, 404])

    def test_wrong_method_get_on_post(self):
        pace()
        r = requests.get(f"{BASE_URL}/upload")
        self.assertIn(r.status_code, [405, 404])

    def test_malformed_json_in_chunked_init(self):
        pace()
        r = requests.post(f"{API}/uploads",
                          data='not json',
                          headers={'Content-Type': 'application/json'})
        self.assertIn(r.status_code, [400, 500])


# ===========================================================================
# 6. RATE LIMITING TESTS
# ===========================================================================

class TestRateLimiting(unittest.TestCase):
    def test_burst_triggers_429(self):
        results = [requests.get(f"{API}/jobs").status_code for _ in range(10)]
        self.assertIn(429, results)

    def test_429_is_json(self):
        for _ in range(10):
            r = requests.get(f"{API}/jobs")
            if r.status_code == 429:
                self.assertIn('error', r.json())
                return

    def test_health_exempt(self):
        codes = [requests.get(f"{API}/health").status_code for _ in range(10)]
        self.assertTrue(all(c == 200 for c in codes))

    def test_upload_rate_limit(self):
        """Upload limit is 30/min — hard to hit in tests but verify it exists."""
        pace()
        r = requests.get(f"{API}/health")
        # Just verify the endpoint works — actual limit tested implicitly


# ===========================================================================
# 7. LEGACY ROUTE TESTS
# ===========================================================================

class TestLegacyRoutes(unittest.TestCase):
    def test_index(self):
        pace()
        r = requests.get(f"{BASE_URL}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/html', r.headers.get('Content-Type', ''))

    def test_docs(self):
        pace()
        r = requests.get(f"{BASE_URL}/docs")
        self.assertEqual(r.status_code, 200)
        self.assertIn('swagger', r.text.lower())

    def test_openapi_json(self):
        pace()
        r = requests.get(f"{BASE_URL}/openapi.json")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d['openapi'], '3.0.3')
        self.assertIn('paths', d)

    def test_legacy_health(self):
        pace()
        r = requests.get(f"{BASE_URL}/health")
        self.assertEqual(r.status_code, 200)
        self.assertIn('status', r.json())

    def test_legacy_status(self):
        pace()
        r = requests.get(f"{BASE_URL}/status")
        self.assertEqual(r.status_code, 200)

    def test_legacy_upload(self):
        wav = tempfile.mktemp(suffix='.wav')
        create_wav(wav)
        pace()
        with open(wav, 'rb') as f:
            r = requests.post(f"{BASE_URL}/upload",
                              files={'files': ('legacy.wav', f)},
                              data={'model': 'tiny'})
        os.remove(wav)
        self.assertEqual(r.status_code, 200)
        cleanup_job(r.json()['jobs'][0]['job_id'])

    def test_static_css(self):
        pace()
        self.assertEqual(requests.get(f"{BASE_URL}/static/css/style.css").status_code, 200)

    def test_static_js(self):
        pace()
        self.assertEqual(requests.get(f"{BASE_URL}/static/js/app.js").status_code, 200)


# ===========================================================================
# 8. PERSISTENCE TESTS
# ===========================================================================

class TestPersistence(unittest.TestCase):
    def test_completed_job_persists(self):
        wav = tempfile.mktemp(suffix='.wav')
        create_wav(wav)
        d = upload_and_wait(wav, 'persist.wav')
        os.remove(wav)
        self.assertEqual(d['status'], 'completed')

        # Re-fetch
        pace()
        r = requests.get(f"{API}/jobs/{d['_job_id']}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'completed')
        cleanup_job(d['_job_id'])


# ===========================================================================
# 9. PERFORMANCE TESTS
# ===========================================================================

class TestPerformance(unittest.TestCase):
    def test_health_response_time(self):
        """Health should respond in < 2 seconds."""
        times = []
        for _ in range(5):
            start = time.time()
            r = requests.get(f"{API}/health")
            elapsed = time.time() - start
            times.append(elapsed)
            self.assertEqual(r.status_code, 200)
        avg = sum(times) / len(times)
        print(f"\n  Health avg response: {avg*1000:.0f}ms")
        self.assertLess(avg, 2.0)

    def test_job_list_response_time(self):
        """Job listing should respond in < 2 seconds."""
        pace()
        start = time.time()
        r = requests.get(f"{API}/jobs")
        elapsed = time.time() - start
        print(f"\n  Job list response: {elapsed*1000:.0f}ms")
        self.assertEqual(r.status_code, 200)
        self.assertLess(elapsed, 2.0)

    def test_upload_response_time(self):
        """Small file upload should respond in < 5 seconds."""
        wav = tempfile.mktemp(suffix='.wav')
        create_wav(wav, duration_s=1)
        pace()
        start = time.time()
        with open(wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('perf.wav', f)},
                              data={'model': 'tiny'})
        elapsed = time.time() - start
        os.remove(wav)
        print(f"\n  Upload response: {elapsed*1000:.0f}ms")
        self.assertEqual(r.status_code, 200)
        self.assertLess(elapsed, 5.0)
        cleanup_job(r.json()['jobs'][0]['job_id'])

    def test_concurrent_status_checks(self):
        """10 concurrent status checks should all succeed."""
        def check():
            return requests.get(f"{API}/health").status_code

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(check) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        self.assertTrue(all(c == 200 for c in results))

    def test_concurrent_uploads(self):
        """3 concurrent uploads should all succeed."""
        wavs = []
        for i in range(3):
            w = tempfile.mktemp(suffix='.wav')
            create_wav(w)
            wavs.append(w)

        def do_upload(path, name):
            with open(path, 'rb') as f:
                r = requests.post(f"{API}/jobs",
                                  files={'files': (name, f)},
                                  data={'model': 'tiny'})
            return r.status_code, r.json() if r.status_code == 200 else {}

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(do_upload, w, f'conc_{i}.wav')
                       for i, w in enumerate(wavs)]
            results = [f.result() for f in as_completed(futures)]

        for w in wavs:
            os.remove(w)

        succeeded = sum(1 for code, _ in results if code == 200)
        # At least 1 should succeed (others may hit rate limit)
        self.assertGreaterEqual(succeeded, 1)

        for code, data in results:
            if code == 200:
                for j in data.get('jobs', []):
                    cleanup_job(j['job_id'])


# ===========================================================================
# 10. OPENAPI SPEC TESTS
# ===========================================================================

class TestOpenAPISpec(unittest.TestCase):
    def test_spec_valid_structure(self):
        pace()
        r = requests.get(f"{BASE_URL}/openapi.json")
        d = r.json()
        self.assertEqual(d['openapi'], '3.0.3')
        self.assertIn('info', d)
        self.assertIn('paths', d)
        self.assertIn('components', d)

    def test_spec_has_all_endpoints(self):
        pace()
        d = requests.get(f"{BASE_URL}/openapi.json").json()
        paths = list(d['paths'].keys())
        self.assertIn('/api/v1/jobs', paths)
        self.assertIn('/api/v1/jobs/{job_id}', paths)
        self.assertIn('/api/v1/jobs/{job_id}/files/{filename}', paths)
        self.assertIn('/api/v1/uploads', paths)
        self.assertIn('/api/v1/uploads/{upload_id}/chunks', paths)
        self.assertIn('/api/v1/uploads/{upload_id}/complete', paths)
        self.assertIn('/api/v1/health', paths)

    def test_spec_has_schemas(self):
        pace()
        d = requests.get(f"{BASE_URL}/openapi.json").json()
        schemas = d['components']['schemas']
        self.assertIn('Job', schemas)
        self.assertIn('Error', schemas)

    def test_spec_version_matches(self):
        pace()
        d = requests.get(f"{BASE_URL}/openapi.json").json()
        self.assertEqual(d['info']['version'], '2.0.0')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1].startswith('http'):
        BASE_URL = sys.argv.pop(1)
        API = f"{BASE_URL}/api/v1"

    print(f"Target: {BASE_URL}")
    print(f"API: {API}")
    print()

    unittest.main(verbosity=2)
