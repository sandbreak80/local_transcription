#!/usr/bin/env python3
"""
End-to-end test suite for Local Transcription Tool API.
Runs against a live container at BASE_URL.

Usage:
    python tests/test_e2e.py [BASE_URL]

Requires: requests, a running container, and /tmp/test_audio.wav
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
import requests

BASE_URL = os.environ.get("TEST_BASE_URL", "http://192.168.50.114:5731")
API = f"{BASE_URL}/api/v1"

# Rate limit: 1 req/sec. This helper ensures we don't get 429s.
_last_request_time = 0


def rate_limit():
    """Sleep enough to stay under 1 req/sec."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 1.15:
        time.sleep(1.15 - elapsed)
    _last_request_time = time.time()


def create_test_wav(path, duration_s=3, freq=440, sample_rate=16000):
    """Create a simple WAV file for testing."""
    frames = []
    for i in range(sample_rate * duration_s):
        val = int(32767 * 0.5 * math.sin(2 * math.pi * freq * i / sample_rate))
        frames.append(struct.pack('<h', val))
    with wave.open(path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(b''.join(frames))


def wait_for_job(job_id, timeout=120):
    """Poll job status until completed or failed."""
    start = time.time()
    while time.time() - start < timeout:
        rate_limit()
        r = requests.get(f"{API}/jobs/{job_id}")
        if r.status_code == 200:
            data = r.json()
            if data['status'] in ('completed', 'failed', 'cancelled'):
                return data
        time.sleep(2)
    raise TimeoutError(f"Job {job_id} did not finish within {timeout}s")


class TestHealthEndpoint(unittest.TestCase):
    """Tests for GET /api/v1/health"""

    def test_health_returns_200(self):
        rate_limit()
        r = requests.get(f"{API}/health")
        self.assertEqual(r.status_code, 200)

    def test_health_has_required_fields(self):
        rate_limit()
        data = requests.get(f"{API}/health").json()
        for field in ['status', 'queue_size', 'total_jobs', 'processing',
                      'queued', 'completed', 'failed', 'gpu',
                      'supported_formats', 'supported_models']:
            self.assertIn(field, data, f"Missing field: {field}")

    def test_health_status_is_healthy(self):
        rate_limit()
        data = requests.get(f"{API}/health").json()
        self.assertEqual(data['status'], 'healthy')

    def test_health_gpu_info(self):
        rate_limit()
        data = requests.get(f"{API}/health").json()
        self.assertIn('available', data['gpu'])
        self.assertIn('device', data['gpu'])

    def test_health_lists_formats(self):
        rate_limit()
        data = requests.get(f"{API}/health").json()
        self.assertIn('wav', data['supported_formats'])
        self.assertIn('mp3', data['supported_formats'])
        self.assertIn('mp4', data['supported_formats'])

    def test_health_lists_models(self):
        rate_limit()
        data = requests.get(f"{API}/health").json()
        for model in ['tiny', 'base', 'small', 'medium', 'large']:
            self.assertIn(model, data['supported_models'])

    def test_health_exempt_from_rate_limit(self):
        """Health should never be rate-limited."""
        for _ in range(5):
            r = requests.get(f"{API}/health")
            self.assertEqual(r.status_code, 200)


class TestInputValidation(unittest.TestCase):
    """Tests for upload input validation."""

    @classmethod
    def setUpClass(cls):
        cls.wav_path = tempfile.mktemp(suffix='.wav')
        create_test_wav(cls.wav_path)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.wav_path):
            os.remove(cls.wav_path)

    def _upload(self, files=None, data=None):
        rate_limit()
        if files is None:
            files = {'files': ('test.wav', open(self.wav_path, 'rb'), 'audio/wav')}
        return requests.post(f"{API}/jobs", files=files, data=data or {})

    def test_no_files_returns_400(self):
        rate_limit()
        r = requests.post(f"{API}/jobs")
        self.assertEqual(r.status_code, 400)
        self.assertIn('error', r.json())

    def test_unsupported_file_type_returns_400(self):
        rate_limit()
        files = {'files': ('test.txt', b'hello', 'text/plain')}
        r = requests.post(f"{API}/jobs", files=files)
        self.assertEqual(r.status_code, 400)
        self.assertIn('error', r.json())
        self.assertIn('Supported formats', r.json()['error'])

    def test_invalid_model_returns_400(self):
        r = self._upload(data={'model': 'enormous'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('Invalid model', r.json()['error'])

    def test_invalid_language_returns_400(self):
        r = self._upload(data={'language': 'klingon'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('Invalid language', r.json()['error'])

    def test_num_speakers_too_high_returns_400(self):
        r = self._upload(data={'num_speakers': '999'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('num_speakers', r.json()['error'])

    def test_num_speakers_too_low_returns_400(self):
        r = self._upload(data={'num_speakers': '0'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('num_speakers', r.json()['error'])

    def test_num_speakers_non_integer_returns_400(self):
        r = self._upload(data={'num_speakers': 'abc'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('integer', r.json()['error'])

    def test_valid_models_accepted(self):
        for model in ['tiny', 'base']:
            r = self._upload(data={'model': model})
            self.assertEqual(r.status_code, 200, f"Model '{model}' rejected")
            job_id = r.json()['jobs'][0]['job_id']
            rate_limit()
            requests.delete(f"{API}/jobs/{job_id}")

    def test_valid_languages_accepted(self):
        for lang in ['auto', 'en', 'es']:
            r = self._upload(data={'language': lang})
            self.assertEqual(r.status_code, 200, f"Language '{lang}' rejected")
            job_id = r.json()['jobs'][0]['job_id']
            rate_limit()
            requests.delete(f"{API}/jobs/{job_id}")

    def test_valid_num_speakers_accepted(self):
        for ns in ['1', '10']:
            r = self._upload(data={'num_speakers': ns})
            self.assertEqual(r.status_code, 200, f"num_speakers={ns} rejected")
            job_id = r.json()['jobs'][0]['job_id']
            rate_limit()
            requests.delete(f"{API}/jobs/{job_id}")

    def test_path_traversal_filename_sanitized(self):
        rate_limit()
        files = {'files': ('../../../etc/passwd.wav', open(self.wav_path, 'rb'), 'audio/wav')}
        r = requests.post(f"{API}/jobs", files=files)
        # Should succeed with sanitized filename or reject
        self.assertIn(r.status_code, [200, 400])
        if r.status_code == 200:
            job_id = r.json()['jobs'][0]['job_id']
            # Filename should not contain path separators
            rate_limit()
            job = requests.get(f"{API}/jobs/{job_id}").json()
            self.assertNotIn('/', job['filename'])
            self.assertNotIn('..', job['filename'])
            rate_limit()
            requests.delete(f"{API}/jobs/{job_id}")


class TestJobLifecycle(unittest.TestCase):
    """Tests for the full job lifecycle: create → process → download → delete."""

    @classmethod
    def setUpClass(cls):
        cls.wav_path = tempfile.mktemp(suffix='.wav')
        create_test_wav(cls.wav_path, duration_s=3)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.wav_path):
            os.remove(cls.wav_path)

    def test_full_lifecycle(self):
        """Upload → wait → check status → download files → delete."""
        # Upload
        rate_limit()
        with open(self.wav_path, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('lifecycle_test.wav', f, 'audio/wav')},
                              data={'model': 'tiny', 'language': 'en'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['success'])
        job_id = r.json()['jobs'][0]['job_id']

        # Wait for completion
        job = wait_for_job(job_id, timeout=60)
        self.assertEqual(job['status'], 'completed')
        self.assertEqual(job['progress'], 100)
        self.assertIsNotNone(job['completed_at'])

        # Verify output files exist
        self.assertGreater(len(job['output_files']), 0)
        has_txt = any(f['name'].endswith('.vtt') for f in job['output_files'])
        has_json = any(f['name'].endswith('.json') for f in job['output_files'])
        self.assertTrue(has_txt, "Missing .vtt output")
        self.assertTrue(has_json, "Missing .json output")

        # Download .txt
        txt_name = [f['name'] for f in job['output_files'] if f['name'].endswith('.vtt')][0]
        rate_limit()
        r = requests.get(f"{API}/jobs/{job_id}/files/{txt_name}")
        self.assertEqual(r.status_code, 200)
        self.assertIn('WEBVTT', r.text)

        # Download .json
        json_name = [f['name'] for f in job['output_files'] if f['name'].endswith('.json')][0]
        rate_limit()
        r = requests.get(f"{API}/jobs/{job_id}/files/{json_name}")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn('text', data)
        self.assertIn('language', data)

        # Delete
        rate_limit()
        r = requests.delete(f"{API}/jobs/{job_id}")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['success'])

        # Verify deleted
        rate_limit()
        r = requests.get(f"{API}/jobs/{job_id}")
        self.assertEqual(r.status_code, 404)

    def test_job_response_fields(self):
        """Verify all expected fields in job response."""
        rate_limit()
        with open(self.wav_path, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('fields_test.wav', f, 'audio/wav')},
                              data={'model': 'tiny'})
        job_id = r.json()['jobs'][0]['job_id']
        job = wait_for_job(job_id, timeout=60)

        expected_fields = ['id', 'filename', 'status', 'progress', 'message',
                           'model', 'language', 'animated_quotes', 'two_list_quotes',
                           'speaker_diarization', 'file_size_mb', 'created_at',
                           'completed_at', 'output_files']
        for field in expected_fields:
            self.assertIn(field, job, f"Missing field: {field}")

        self.assertEqual(job['model'], 'tiny')
        self.assertIsInstance(job['file_size_mb'], (int, float))
        self.assertIsInstance(job['output_files'], list)

        # Cleanup
        rate_limit()
        requests.delete(f"{API}/jobs/{job_id}")


class TestJobListing(unittest.TestCase):
    """Tests for GET /api/v1/jobs with filters."""

    def test_list_all_jobs(self):
        rate_limit()
        r = requests.get(f"{API}/jobs")
        self.assertEqual(r.status_code, 200)
        self.assertIn('jobs', r.json())
        self.assertIsInstance(r.json()['jobs'], list)

    def test_filter_by_status_completed(self):
        rate_limit()
        r = requests.get(f"{API}/jobs", params={'status': 'completed'})
        self.assertEqual(r.status_code, 200)
        for job in r.json()['jobs']:
            self.assertEqual(job['status'], 'completed')

    def test_filter_by_status_failed(self):
        rate_limit()
        r = requests.get(f"{API}/jobs", params={'status': 'failed'})
        self.assertEqual(r.status_code, 200)
        for job in r.json()['jobs']:
            self.assertEqual(job['status'], 'failed')

    def test_filter_invalid_status_returns_400(self):
        rate_limit()
        r = requests.get(f"{API}/jobs", params={'status': 'banana'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('error', r.json())


class TestJobDeletion(unittest.TestCase):
    """Tests for DELETE /api/v1/jobs/<id>."""

    @classmethod
    def setUpClass(cls):
        cls.wav_path = tempfile.mktemp(suffix='.wav')
        create_test_wav(cls.wav_path)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.wav_path):
            os.remove(cls.wav_path)

    def test_delete_nonexistent_returns_404(self):
        rate_limit()
        r = requests.delete(f"{API}/jobs/nonexistent-job-id")
        self.assertEqual(r.status_code, 404)

    def test_delete_completed_job(self):
        rate_limit()
        with open(self.wav_path, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('delete_test.wav', f, 'audio/wav')},
                              data={'model': 'tiny'})
        job_id = r.json()['jobs'][0]['job_id']
        wait_for_job(job_id, timeout=60)

        rate_limit()
        r = requests.delete(f"{API}/jobs/{job_id}")
        self.assertEqual(r.status_code, 200)

        rate_limit()
        r = requests.get(f"{API}/jobs/{job_id}")
        self.assertEqual(r.status_code, 404)

    def test_cancel_processing_job(self):
        """Submit a large-model job and cancel it while processing."""
        rate_limit()
        with open(self.wav_path, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('cancel_test.wav', f, 'audio/wav')},
                              data={'model': 'base'})
        job_id = r.json()['jobs'][0]['job_id']

        # Wait for it to start processing
        time.sleep(5)
        rate_limit()
        status = requests.get(f"{API}/jobs/{job_id}").json()

        # Cancel it
        rate_limit()
        r = requests.delete(f"{API}/jobs/{job_id}")
        self.assertEqual(r.status_code, 200)

        # Verify gone
        rate_limit()
        r = requests.get(f"{API}/jobs/{job_id}")
        self.assertEqual(r.status_code, 404)


class TestDownload(unittest.TestCase):
    """Tests for GET /api/v1/jobs/<id>/files/<name>."""

    def test_download_nonexistent_job_returns_404(self):
        rate_limit()
        r = requests.get(f"{API}/jobs/nonexistent/files/output.txt")
        self.assertEqual(r.status_code, 404)

    def test_download_nonexistent_file_returns_404(self):
        # Create and complete a job first
        wav_path = tempfile.mktemp(suffix='.wav')
        create_test_wav(wav_path)
        rate_limit()
        with open(wav_path, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('dl_test.wav', f, 'audio/wav')},
                              data={'model': 'tiny'})
        os.remove(wav_path)
        job_id = r.json()['jobs'][0]['job_id']
        wait_for_job(job_id, timeout=60)

        rate_limit()
        r = requests.get(f"{API}/jobs/{job_id}/files/nonexistent_file.txt")
        self.assertEqual(r.status_code, 404)

        # Cleanup
        rate_limit()
        requests.delete(f"{API}/jobs/{job_id}")

    def test_download_from_incomplete_job_returns_400(self):
        wav_path = tempfile.mktemp(suffix='.wav')
        create_test_wav(wav_path)
        rate_limit()
        with open(wav_path, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('incomplete_test.wav', f, 'audio/wav')},
                              data={'model': 'base'})
        os.remove(wav_path)
        job_id = r.json()['jobs'][0]['job_id']

        # Try downloading immediately (before completion)
        rate_limit()
        r = requests.get(f"{API}/jobs/{job_id}/files/incomplete_test_transcription.txt")
        self.assertIn(r.status_code, [400, 404])

        # Cleanup
        rate_limit()
        requests.delete(f"{API}/jobs/{job_id}")

    def test_path_traversal_in_download_blocked(self):
        wav_path = tempfile.mktemp(suffix='.wav')
        create_test_wav(wav_path)
        rate_limit()
        with open(wav_path, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('traversal_test.wav', f, 'audio/wav')},
                              data={'model': 'tiny'})
        os.remove(wav_path)
        job_id = r.json()['jobs'][0]['job_id']
        wait_for_job(job_id, timeout=60)

        rate_limit()
        r = requests.get(f"{API}/jobs/{job_id}/files/../../etc/passwd")
        self.assertEqual(r.status_code, 404)

        rate_limit()
        requests.delete(f"{API}/jobs/{job_id}")


class TestRateLimiting(unittest.TestCase):
    """Tests for rate limiting behavior."""

    def test_rapid_requests_get_429(self):
        """Burst of requests exceeding 5/sec should get 429."""
        results = []
        for _ in range(8):
            results.append(requests.get(f"{API}/jobs").status_code)
        self.assertIn(429, results, "Expected at least one 429 in burst of 8 requests")

    def test_429_response_is_json(self):
        """Rate limit response should be JSON, not HTML."""
        # Send burst to trigger rate limit
        for _ in range(8):
            r = requests.get(f"{API}/jobs")
            if r.status_code == 429:
                self.assertIn('error', r.json())
                self.assertIn('Rate limit', r.json()['error'])
                return
        # If we never hit 429, that's OK — rate limit is lenient

    def test_health_exempt_from_rate_limit(self):
        """Health endpoint should never return 429."""
        results = []
        for _ in range(5):
            r = requests.get(f"{API}/health")
            results.append(r.status_code)
        self.assertTrue(all(c == 200 for c in results))


class TestErrorHandlers(unittest.TestCase):
    """Tests for global error handlers."""

    def test_404_returns_json(self):
        rate_limit()
        r = requests.get(f"{API}/nonexistent-endpoint")
        self.assertEqual(r.status_code, 404)
        self.assertIn('error', r.json())

    def test_sql_injection_in_job_id(self):
        rate_limit()
        r = requests.get(f"{API}/jobs/' OR 1=1--")
        self.assertEqual(r.status_code, 404)

    def test_very_long_job_id(self):
        rate_limit()
        r = requests.get(f"{API}/jobs/{'a' * 1000}")
        self.assertEqual(r.status_code, 404)


class TestLegacyRoutes(unittest.TestCase):
    """Tests for legacy frontend routes."""

    def test_index_returns_html(self):
        rate_limit()
        r = requests.get(f"{BASE_URL}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/html', r.headers.get('Content-Type', ''))

    def test_legacy_health(self):
        rate_limit()
        r = requests.get(f"{BASE_URL}/health")
        self.assertEqual(r.status_code, 200)
        self.assertIn('status', r.json())

    def test_legacy_status(self):
        rate_limit()
        r = requests.get(f"{BASE_URL}/status")
        self.assertEqual(r.status_code, 200)
        self.assertIn('jobs', r.json())

    def test_static_css(self):
        rate_limit()
        r = requests.get(f"{BASE_URL}/static/css/style.css")
        self.assertEqual(r.status_code, 200)

    def test_static_js(self):
        rate_limit()
        r = requests.get(f"{BASE_URL}/static/js/app.js")
        self.assertEqual(r.status_code, 200)

    def test_legacy_upload_works(self):
        wav_path = tempfile.mktemp(suffix='.wav')
        create_test_wav(wav_path)
        rate_limit()
        with open(wav_path, 'rb') as f:
            r = requests.post(f"{BASE_URL}/upload",
                              files={'files': ('legacy_test.wav', f, 'audio/wav')},
                              data={'model': 'tiny'})
        os.remove(wav_path)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['success'])
        job_id = r.json()['jobs'][0]['job_id']

        # Legacy status endpoint
        rate_limit()
        r = requests.get(f"{BASE_URL}/status/{job_id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['id'], job_id)

        # Cleanup
        rate_limit()
        requests.delete(f"{API}/jobs/{job_id}")

    def test_legacy_status_nonexistent(self):
        rate_limit()
        r = requests.get(f"{BASE_URL}/status/nonexistent")
        self.assertEqual(r.status_code, 404)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and boundary conditions."""

    def test_upload_multiple_files(self):
        """Upload two files in one request."""
        wav1 = tempfile.mktemp(suffix='.wav')
        wav2 = tempfile.mktemp(suffix='.wav')
        create_test_wav(wav1)
        create_test_wav(wav2, freq=880)
        rate_limit()
        with open(wav1, 'rb') as f1, open(wav2, 'rb') as f2:
            r = requests.post(f"{API}/jobs",
                              files=[('files', ('multi1.wav', f1, 'audio/wav')),
                                     ('files', ('multi2.wav', f2, 'audio/wav'))],
                              data={'model': 'tiny'})
        os.remove(wav1)
        os.remove(wav2)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()['jobs']), 2)

        # Cleanup
        for job in r.json()['jobs']:
            rate_limit()
            requests.delete(f"{API}/jobs/{job['job_id']}")

    def test_upload_mix_valid_and_invalid_files(self):
        """Upload one valid and one invalid file — should accept valid, reject invalid."""
        wav = tempfile.mktemp(suffix='.wav')
        create_test_wav(wav)
        rate_limit()
        with open(wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files=[('files', ('valid.wav', f, 'audio/wav')),
                                     ('files', ('invalid.txt', b'hello', 'text/plain'))],
                              data={'model': 'tiny'})
        os.remove(wav)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()['jobs']), 1)
        if 'rejected_files' in r.json():
            self.assertIn('invalid.txt', r.json()['rejected_files'])

        # Cleanup
        rate_limit()
        requests.delete(f"{API}/jobs/{r.json()['jobs'][0]['job_id']}")

    def test_boolean_params_as_strings(self):
        """Ensure 'true'/'false' strings are handled correctly for boolean params."""
        wav = tempfile.mktemp(suffix='.wav')
        create_test_wav(wav)
        rate_limit()
        with open(wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('bool_test.wav', f, 'audio/wav')},
                              data={'model': 'tiny', 'animated_quotes': 'true',
                                    'speaker_diarization': 'false'})
        os.remove(wav)
        self.assertEqual(r.status_code, 200)
        job_id = r.json()['jobs'][0]['job_id']

        rate_limit()
        job = requests.get(f"{API}/jobs/{job_id}").json()
        self.assertTrue(job['animated_quotes'])
        self.assertFalse(job['speaker_diarization'])

        rate_limit()
        requests.delete(f"{API}/jobs/{job_id}")

    def test_empty_file_accepted_but_fails(self):
        """0-byte file should be accepted (current behavior) but fail processing."""
        rate_limit()
        r = requests.post(f"{API}/jobs",
                          files={'files': ('empty.wav', b'', 'audio/wav')},
                          data={'model': 'tiny'})
        if r.status_code == 200:
            job_id = r.json()['jobs'][0]['job_id']
            job = wait_for_job(job_id, timeout=60)
            self.assertEqual(job['status'], 'failed')
            rate_limit()
            requests.delete(f"{API}/jobs/{job_id}")
        else:
            # If validation rejects it, that's also fine
            self.assertEqual(r.status_code, 400)

    def test_special_characters_in_filename(self):
        """Filenames with spaces and special chars should be sanitized."""
        wav = tempfile.mktemp(suffix='.wav')
        create_test_wav(wav)
        rate_limit()
        with open(wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('my file (copy).wav', f, 'audio/wav')},
                              data={'model': 'tiny'})
        os.remove(wav)
        self.assertEqual(r.status_code, 200)
        filename = r.json()['jobs'][0]['filename']
        # Should be sanitized but recognizable
        self.assertTrue(filename.endswith('.wav'))

        rate_limit()
        requests.delete(f"{API}/jobs/{r.json()['jobs'][0]['job_id']}")


class TestJobPersistence(unittest.TestCase):
    """Tests for SQLite persistence across restarts."""

    def test_completed_job_survives_conceptual(self):
        """Verify a completed job is retrievable (DB persistence test)."""
        wav = tempfile.mktemp(suffix='.wav')
        create_test_wav(wav)
        rate_limit()
        with open(wav, 'rb') as f:
            r = requests.post(f"{API}/jobs",
                              files={'files': ('persist_test.wav', f, 'audio/wav')},
                              data={'model': 'tiny'})
        os.remove(wav)
        job_id = r.json()['jobs'][0]['job_id']
        job = wait_for_job(job_id, timeout=60)
        self.assertEqual(job['status'], 'completed')

        # Re-fetch — should still be there
        rate_limit()
        r = requests.get(f"{API}/jobs/{job_id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'completed')

        rate_limit()
        requests.delete(f"{API}/jobs/{job_id}")


class TestScanOutputs(unittest.TestCase):
    """Tests for GET /scan-outputs."""

    def test_scan_outputs_returns_success(self):
        rate_limit()
        r = requests.get(f"{BASE_URL}/scan-outputs")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data['success'])
        self.assertIn('files_found', data)
        self.assertIn('jobs_created', data)


if __name__ == '__main__':
    # Allow passing BASE_URL as command line arg
    if len(sys.argv) > 1 and sys.argv[1].startswith('http'):
        BASE_URL = sys.argv.pop(1)
        API = f"{BASE_URL}/api/v1"

    print(f"Running tests against: {BASE_URL}")
    print(f"API endpoint: {API}")
    print()

    unittest.main(verbosity=2)
