#!/usr/bin/env python3
"""
Local Transcription Tool — Web Interface & REST API
Local Transcription Tool

API Endpoints (all under /api/v1):
  POST   /api/v1/jobs                Upload file(s) and start transcription (< 50MB)
  GET    /api/v1/jobs                List all jobs (?status=queued|processing|completed|failed)
  GET    /api/v1/jobs/<id>           Get job status and details
  DELETE /api/v1/jobs/<id>           Cancel queued/processing job, or delete completed/failed job
  GET    /api/v1/jobs/<id>/files/<name>  Download an output file
  GET    /api/v1/health              Health check with queue and GPU info

Chunked Upload (for files > 50MB, required behind Cloudflare Tunnels):
  POST   /api/v1/uploads             Initiate chunked upload (returns upload_id)
  POST   /api/v1/uploads/<id>/chunks Upload a chunk (50MB max per chunk)
  POST   /api/v1/uploads/<id>/complete  Finalize upload and start transcription

Legacy routes (/upload, /status, etc.) are preserved for the web frontend.
"""

import os
import json
import uuid
import sqlite3
import threading
import signal
import time
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
import subprocess
import shutil
import queue

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 55 * 1024 * 1024  # 55MB per request (chunk size + overhead)

# Rate limiting: 5 requests/second per IP, 300/minute burst
# (relaxed for multi-user; Cloudflare provides additional DDoS protection)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5 per second", "300 per minute"],
    storage_uri="memory://",
)
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp/transcription_uploads')
app.config['CHUNKS_FOLDER'] = os.environ.get('CHUNKS_FOLDER', '/tmp/transcription_chunks')
app.config['OUTPUT_FOLDER'] = os.environ.get('OUTPUT_FOLDER', '/tmp/transcription_outputs')
app.config['DB_PATH'] = os.environ.get('DB_PATH', '/tmp/transcription_jobs.db')
app.config['MAX_CONCURRENT_JOBS'] = int(os.environ.get('MAX_CONCURRENT_JOBS', '2'))
app.config['CHUNK_SIZE_MB'] = int(os.environ.get('CHUNK_SIZE_MB', '50'))

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CHUNKS_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# ---------------------------------------------------------------------------
# Allowed inputs
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {
    'mp4', 'mp3', 'wav', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm',
    'm4v', 'm4a', 'aac', 'flac', 'ogg', 'wma', 'mpeg', 'mpg'
}
VALID_MODELS = {'tiny', 'base', 'small', 'medium', 'large'}
VALID_LANGUAGES = {
    'auto', 'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'zh', 'ko',
    'ar', 'hi', 'nl', 'pl', 'sv', 'da', 'fi', 'no', 'tr', 'uk', 'cs',
    'el', 'he', 'hu', 'id', 'ms', 'ro', 'th', 'vi', 'ca', 'cy', 'tl',
}

# ---------------------------------------------------------------------------
# SQLite job persistence
# ---------------------------------------------------------------------------
def get_db():
    """Get thread-local database connection."""
    if 'db' not in g:
        g.db = _db_connect()
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def _db_connect():
    """Create a properly configured SQLite connection."""
    conn = sqlite3.connect(app.config['DB_PATH'], timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=10000')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create jobs table if it doesn't exist."""
    conn = _db_connect()
    conn.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        input_file TEXT,
        model TEXT NOT NULL DEFAULT 'base',
        language TEXT NOT NULL DEFAULT 'auto',
        animated_quotes INTEGER NOT NULL DEFAULT 0,
        two_list_quotes INTEGER NOT NULL DEFAULT 0,
        speaker_diarization INTEGER NOT NULL DEFAULT 0,
        num_speakers TEXT DEFAULT '',
        speaker_names TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'queued',
        progress INTEGER NOT NULL DEFAULT 0,
        message TEXT NOT NULL DEFAULT 'Waiting in queue...',
        file_size_mb REAL NOT NULL DEFAULT 0,
        output_files TEXT DEFAULT '[]',
        created_at TEXT NOT NULL,
        completed_at TEXT,
        error_detail TEXT
    )''')
    conn.commit()
    conn.close()


def db_save_job(job_dict):
    """Insert or update a job in the database."""
    conn = _db_connect()
    conn.execute('''INSERT OR REPLACE INTO jobs
        (id, filename, input_file, model, language, animated_quotes, two_list_quotes,
         speaker_diarization, num_speakers, speaker_names, status, progress, message,
         file_size_mb, output_files, created_at, completed_at, error_detail)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        job_dict['id'], job_dict['filename'], job_dict.get('input_file', ''),
        job_dict['model'], job_dict['language'],
        int(job_dict.get('animated_quotes', False)),
        int(job_dict.get('two_list_quotes', False)),
        int(job_dict.get('speaker_diarization', False)),
        job_dict.get('num_speakers', ''), job_dict.get('speaker_names', ''),
        job_dict['status'], job_dict['progress'], job_dict['message'],
        job_dict.get('file_size_mb', 0),
        json.dumps(job_dict.get('output_files', [])),
        job_dict['created_at'], job_dict.get('completed_at'),
        job_dict.get('error_detail')
    ))
    conn.commit()
    conn.close()


def db_get_job(job_id):
    """Get a job from the database."""
    conn = _db_connect()
    row = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_dict(row)


def db_list_jobs(status_filter=None):
    """List all jobs, optionally filtered by status."""
    conn = _db_connect()
    if status_filter:
        rows = conn.execute(
            'SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC',
            (status_filter,)).fetchall()
    else:
        rows = conn.execute(
            'SELECT * FROM jobs ORDER BY created_at DESC').fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def db_update_job(job_id, **fields):
    """Update specific fields of a job."""
    conn = _db_connect()
    sets = []
    vals = []
    for k, v in fields.items():
        sets.append(f'{k} = ?')
        vals.append(v)
    vals.append(job_id)
    conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def db_delete_job(job_id):
    """Delete a job from the database."""
    conn = _db_connect()
    conn.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
    conn.commit()
    conn.close()


def _row_to_dict(row):
    d = dict(row)
    d['animated_quotes'] = bool(d['animated_quotes'])
    d['two_list_quotes'] = bool(d['two_list_quotes'])
    d['speaker_diarization'] = bool(d['speaker_diarization'])
    try:
        d['output_files'] = json.loads(d.get('output_files', '[]'))
    except (json.JSONDecodeError, TypeError):
        d['output_files'] = []
    return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_size_mb(filepath):
    return os.path.getsize(filepath) / (1024 * 1024)


def _api_error(message, status_code):
    return jsonify({'error': message}), status_code


def _job_response(job):
    """Standard job response (excludes internal fields like input_file)."""
    return {
        'id': job['id'],
        'filename': job['filename'],
        'status': job['status'],
        'progress': job['progress'],
        'message': job['message'],
        'model': job['model'],
        'language': job['language'],
        'animated_quotes': job.get('animated_quotes', False),
        'two_list_quotes': job.get('two_list_quotes', False),
        'speaker_diarization': job.get('speaker_diarization', False),
        'file_size_mb': job.get('file_size_mb', 0),
        'created_at': job['created_at'],
        'completed_at': job.get('completed_at'),
        'output_files': [
            {'name': f['name'], 'size': f.get('size', 0)}
            for f in job.get('output_files', [])
        ],
    }


def _validate_upload_params(form):
    """Validate and extract upload parameters. Returns (params, error_msg)."""
    model = form.get('model', 'base')
    if model not in VALID_MODELS:
        return None, f"Invalid model '{model}'. Must be one of: {', '.join(sorted(VALID_MODELS))}"

    language = form.get('language', 'auto')
    if language not in VALID_LANGUAGES:
        return None, f"Invalid language '{language}'. Must be one of: {', '.join(sorted(VALID_LANGUAGES))}"

    num_speakers = form.get('num_speakers', '')
    if num_speakers:
        try:
            ns = int(num_speakers)
            if ns < 1 or ns > 20:
                return None, 'num_speakers must be between 1 and 20'
        except ValueError:
            return None, 'num_speakers must be an integer'

    speaker_names = form.get('speaker_names', '')
    if speaker_names and not all(n.strip() for n in speaker_names.split(',')):
        return None, 'speaker_names must be a comma-separated list of non-empty names'

    return {
        'model': model,
        'language': language,
        'animated_quotes': form.get('animated_quotes') == 'true',
        'two_list_quotes': form.get('two_list_quotes') == 'true',
        'speaker_diarization': form.get('speaker_diarization') == 'true',
        'num_speakers': num_speakers,
        'speaker_names': speaker_names,
    }, None


# ---------------------------------------------------------------------------
# Job processing
# ---------------------------------------------------------------------------
job_queue = queue.Queue()
active_processes = {}  # job_id -> subprocess.Popen (for cancellation)
active_processes_lock = threading.Lock()


def _cleanup_input(input_file):
    """Remove input file if it exists."""
    try:
        if input_file and os.path.exists(input_file):
            os.remove(input_file)
    except OSError:
        pass


def process_job(job_id):
    """Process a transcription job."""
    job = db_get_job(job_id)
    if job is None or job['status'] == 'cancelled':
        return

    try:
        db_update_job(job_id, status='processing', progress=10,
                      message='Starting transcription...')

        input_file = job['input_file']
        # Per-job output directory prevents file collisions between users
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], job_id)
        os.makedirs(output_dir, exist_ok=True)

        cmd = ['python3', '/app/transcribe.py', input_file,
               '--output-dir', output_dir]

        if job['model']:
            cmd.extend(['--model', job['model']])
        if job['language'] and job['language'] != 'auto':
            cmd.extend(['--language', job['language']])
        if job.get('animated_quotes'):
            cmd.append('--animated-quotes')
        if job.get('two_list_quotes'):
            cmd.append('--two-lists')
        if job.get('speaker_diarization'):
            cmd.append('--speaker-diarization')
            if job.get('num_speakers'):
                cmd.extend(['--num-speakers', str(job['num_speakers'])])
            if job.get('speaker_names'):
                cmd.extend(['--speaker-names', job['speaker_names']])

        db_update_job(job_id, progress=20, message='Transcribing audio...')

        log_file = os.path.join(output_dir, f"{job_id}_transcribe.log")
        with open(log_file, 'w') as log:
            log.write(f"Command: {' '.join(cmd)}\n")
            log.write(f"Input: {input_file} (exists: {os.path.exists(input_file)})\n")
            log.flush()

            proc = subprocess.Popen(
                cmd, cwd=output_dir,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            with active_processes_lock:
                active_processes[job_id] = proc

            try:
                stdout, stderr = proc.communicate(timeout=3600)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                db_update_job(job_id, status='failed', progress=0,
                              message='Transcription timed out (max 1 hour)')
                return
            finally:
                with active_processes_lock:
                    active_processes.pop(job_id, None)

            log.write(f"\nExit code: {proc.returncode}\n")
            if stdout:
                log.write(f"STDOUT:\n{stdout.decode('utf-8', errors='replace')}\n")
            if stderr:
                log.write(f"STDERR:\n{stderr.decode('utf-8', errors='replace')}\n")

        # Check if cancelled while processing
        job = db_get_job(job_id)
        if job is None or job['status'] == 'cancelled':
            return

        if proc.returncode == 0:
            base_name = Path(job['filename']).stem
            uuid_base_name = Path(input_file).stem
            original_filename = job['filename']
            uuid_filename = Path(input_file).name
            output_files = []

            for ext in ['.vtt', '.json',
                        '_animated_quotes.txt', '_animated_quotes.json',
                        '_two_list_quotes.txt', '_two_list_quotes.json']:
                actual_file = os.path.join(output_dir, uuid_base_name + ext)
                clean_filename = base_name + ext
                clean_path = os.path.join(output_dir, clean_filename)

                if os.path.exists(actual_file):
                    with open(actual_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    content = content.replace(uuid_filename, original_filename)
                    content = content.replace(uuid_base_name, base_name)
                    with open(clean_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    os.remove(actual_file)
                    output_files.append({
                        'name': clean_filename,
                        'path': clean_path,
                        'size': os.path.getsize(clean_path)
                    })
                elif os.path.exists(clean_path):
                    output_files.append({
                        'name': clean_filename,
                        'path': clean_path,
                        'size': os.path.getsize(clean_path)
                    })

            db_update_job(job_id, status='completed', progress=100,
                          message='Transcription completed!',
                          output_files=json.dumps(output_files),
                          completed_at=datetime.now().isoformat())

            # Clean up input file on success
            _cleanup_input(input_file)
        else:
            stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ''
            stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ''
            error_detail = (stderr_text or stdout_text or 'Unknown error').strip()
            db_update_job(job_id, status='failed', progress=0,
                          message=f'Error: {error_detail[:500]}',
                          error_detail=error_detail[:2000])
            _cleanup_input(input_file)

    except Exception as e:
        db_update_job(job_id, status='failed', progress=0,
                      message=f'Error: {str(e)}',
                      error_detail=str(e))
        _cleanup_input(input_file)


def worker_thread(worker_id):
    """Background worker to process jobs from queue."""
    while True:
        try:
            job_id = job_queue.get(timeout=1)
        except queue.Empty:
            continue

        try:
            if job_id:
                print(f"[Worker {worker_id}] Processing job {job_id}")
                process_job(job_id)
        except Exception as e:
            print(f"[Worker {worker_id}] Error processing {job_id}: {e}")
            try:
                db_update_job(job_id, status='failed', progress=0,
                              message=f'Worker error: {str(e)[:200]}')
            except Exception:
                pass
        finally:
            job_queue.task_done()


def restore_queued_jobs():
    """On startup, re-queue any jobs that were queued or processing (interrupted)."""
    for job in db_list_jobs():
        if job['status'] in ('queued', 'processing'):
            db_update_job(job['id'], status='queued', progress=0,
                          message='Re-queued after restart')
            job_queue.put(job['id'])


# Start worker pool
_num_workers = int(os.environ.get('MAX_CONCURRENT_JOBS', '2'))
for _i in range(_num_workers):
    _w = threading.Thread(target=worker_thread, args=(_i,), daemon=True)
    _w.start()

# ---------------------------------------------------------------------------
# Upload helper (shared between legacy and API routes)
# ---------------------------------------------------------------------------
def _handle_upload(request):
    """Shared upload logic. Returns (response_dict, status_code)."""
    if 'files' not in request.files:
        return {'error': 'No files provided. Send multipart form with "files" field.'}, 400

    params, err = _validate_upload_params(request.form)
    if err:
        return {'error': err}, 400

    files = request.files.getlist('files')
    uploaded_jobs = []
    rejected_files = []

    for file in files:
        if not file or not file.filename:
            continue
        if not allowed_file(file.filename):
            rejected_files.append(file.filename)
            continue

        job_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        if not filename:
            rejected_files.append(file.filename)
            continue

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
        file.save(filepath)

        job_dict = {
            'id': job_id,
            'filename': filename,
            'input_file': filepath,
            'status': 'queued',
            'progress': 0,
            'message': 'Waiting in queue...',
            'created_at': datetime.now().isoformat(),
            'file_size_mb': round(get_file_size_mb(filepath), 2),
            'output_files': [],
            **params,
        }
        db_save_job(job_dict)
        job_queue.put(job_id)

        uploaded_jobs.append({'job_id': job_id, 'filename': filename})

    if not uploaded_jobs:
        msg = 'No supported files provided.'
        if rejected_files:
            msg += f' Rejected: {", ".join(rejected_files)}.'
        msg += f' Supported formats: {", ".join(sorted(ALLOWED_EXTENSIONS))}'
        return {'error': msg}, 400

    resp = {'success': True, 'jobs': uploaded_jobs}
    if rejected_files:
        resp['rejected_files'] = rejected_files
    return resp, 200


# ===========================================================================
# REST API v1
# ===========================================================================

@app.route('/api/v1/jobs', methods=['POST'])
@limiter.limit("30 per minute")
def api_create_job():
    """Upload file(s) and create transcription job(s).

    Multipart form fields:
      files (required)       One or more audio/video files
      model                  tiny|base|small|medium|large (default: base)
      language               Language code or "auto" (default: auto)
      animated_quotes        "true" to enable (default: false)
      two_list_quotes        "true" to enable (default: false)
      speaker_diarization    "true" to enable (default: false)
      num_speakers           Integer 1-20 (optional, auto-detect if omitted)
      speaker_names          Comma-separated names (optional)
    """
    resp, code = _handle_upload(request)
    return jsonify(resp), code


@app.route('/api/v1/jobs', methods=['GET'])
def api_list_jobs():
    """List all jobs. Optional query param: ?status=queued|processing|completed|failed"""
    status_filter = request.args.get('status')
    if status_filter and status_filter not in ('queued', 'processing', 'completed', 'failed', 'cancelled'):
        return _api_error('Invalid status filter', 400)
    jobs_list = db_list_jobs(status_filter)
    return jsonify({'jobs': [_job_response(j) for j in jobs_list]})


@app.route('/api/v1/jobs/<job_id>', methods=['GET'])
def api_get_job(job_id):
    """Get details for a specific job."""
    job = db_get_job(job_id)
    if job is None:
        return _api_error('Job not found', 404)
    return jsonify(_job_response(job))


@app.route('/api/v1/jobs/<job_id>', methods=['DELETE'])
def api_delete_job(job_id):
    """Cancel a queued/processing job, or delete a completed/failed job.

    Cancels in-flight subprocess if processing. Cleans up input/output files.
    """
    job = db_get_job(job_id)
    if job is None:
        return _api_error('Job not found', 404)

    if job['status'] == 'processing':
        # Kill the subprocess
        with active_processes_lock:
            proc = active_processes.pop(job_id, None)
        if proc:
            try:
                proc.kill()
            except OSError:
                pass
        db_update_job(job_id, status='cancelled', progress=0,
                      message='Cancelled by user')

    elif job['status'] == 'queued':
        db_update_job(job_id, status='cancelled', progress=0,
                      message='Cancelled by user')

    # Clean up files
    _cleanup_input(job.get('input_file'))
    # Remove per-job output directory
    job_output_dir = os.path.join(app.config['OUTPUT_FOLDER'], job_id)
    if os.path.isdir(job_output_dir):
        shutil.rmtree(job_output_dir, ignore_errors=True)

    db_delete_job(job_id)
    return jsonify({'success': True, 'message': f'Job {job_id} deleted'})


@app.route('/api/v1/jobs/<job_id>/files/<filename>', methods=['GET'])
def api_download_file(job_id, filename):
    """Download an output file from a completed job."""
    job = db_get_job(job_id)
    if job is None:
        return _api_error('Job not found', 404)
    if job['status'] != 'completed':
        return _api_error('Job not completed', 400)

    for output_file in job.get('output_files', []):
        if output_file['name'] == filename:
            if os.path.exists(output_file['path']):
                return send_file(output_file['path'],
                                 as_attachment=True,
                                 download_name=filename)
            return _api_error('File no longer exists on disk', 410)
    return _api_error('File not found', 404)


# ===========================================================================
# Chunked Upload API
# ===========================================================================

# In-memory tracking for active chunked uploads
_chunked_uploads = {}  # upload_id -> {filename, total_chunks, received, params, created_at}
_chunked_uploads_lock = threading.Lock()


@app.route('/api/v1/uploads', methods=['POST'])
@limiter.limit("30 per minute")
def api_init_chunked_upload():
    """Initiate a chunked upload session.

    JSON body:
      filename (required)      Original filename (e.g., "meeting.mp4")
      total_chunks (required)   Total number of chunks to expect
      total_size_mb (optional)  Total file size in MB (informational)
      model, language, animated_quotes, two_list_quotes,
      speaker_diarization, num_speakers, speaker_names — same as /api/v1/jobs
    """
    data = request.get_json(silent=True) or {}

    filename = data.get('filename', '').strip()
    if not filename:
        return _api_error('filename is required', 400)
    if not allowed_file(filename):
        return _api_error(
            f'Unsupported file type. Supported: {", ".join(sorted(ALLOWED_EXTENSIONS))}', 400)

    total_chunks = data.get('total_chunks')
    if total_chunks is None:
        return _api_error('total_chunks is required', 400)
    try:
        total_chunks = int(total_chunks)
        if total_chunks < 1 or total_chunks > 200:
            return _api_error('total_chunks must be between 1 and 200', 400)
    except (ValueError, TypeError):
        return _api_error('total_chunks must be an integer', 400)

    # Validate transcription params
    params, err = _validate_upload_params(data)
    if err:
        return _api_error(err, 400)

    upload_id = str(uuid.uuid4())
    safe_filename = secure_filename(filename)
    if not safe_filename:
        safe_filename = f'upload_{upload_id}.bin'

    # Create chunk directory
    chunk_dir = os.path.join(app.config['CHUNKS_FOLDER'], upload_id)
    os.makedirs(chunk_dir, exist_ok=True)

    with _chunked_uploads_lock:
        _chunked_uploads[upload_id] = {
            'filename': safe_filename,
            'total_chunks': total_chunks,
            'received': set(),
            'params': params,
            'chunk_dir': chunk_dir,
            'created_at': time.time(),
            'total_size_mb': data.get('total_size_mb', 0),
        }

    return jsonify({
        'upload_id': upload_id,
        'filename': safe_filename,
        'total_chunks': total_chunks,
        'chunk_size_mb': app.config['CHUNK_SIZE_MB'],
    }), 201


@app.route('/api/v1/uploads/<upload_id>/chunks', methods=['POST'])
@limiter.exempt
def api_upload_chunk(upload_id):
    """Upload a single chunk.

    Multipart form:
      chunk (required)       The file chunk data
      chunk_index (required) 0-based chunk index
    """
    with _chunked_uploads_lock:
        upload = _chunked_uploads.get(upload_id)
    if upload is None:
        return _api_error('Upload session not found or expired', 404)

    chunk_index = request.form.get('chunk_index')
    if chunk_index is None:
        return _api_error('chunk_index is required', 400)
    try:
        chunk_index = int(chunk_index)
    except (ValueError, TypeError):
        return _api_error('chunk_index must be an integer', 400)

    if chunk_index < 0 or chunk_index >= upload['total_chunks']:
        return _api_error(
            f'chunk_index must be between 0 and {upload["total_chunks"] - 1}', 400)

    if 'chunk' not in request.files:
        return _api_error('No chunk data provided. Send as multipart "chunk" field.', 400)

    chunk_file = request.files['chunk']
    chunk_path = os.path.join(upload['chunk_dir'], f'chunk_{chunk_index:04d}')
    chunk_file.save(chunk_path)

    with _chunked_uploads_lock:
        upload['received'].add(chunk_index)
        received = len(upload['received'])
        total = upload['total_chunks']

    return jsonify({
        'upload_id': upload_id,
        'chunk_index': chunk_index,
        'received': received,
        'total_chunks': total,
        'complete': received == total,
    })


@app.route('/api/v1/uploads/<upload_id>/complete', methods=['POST'])
def api_complete_chunked_upload(upload_id):
    """Finalize a chunked upload: reassemble chunks and start transcription.

    Call this after all chunks have been uploaded.
    """
    with _chunked_uploads_lock:
        upload = _chunked_uploads.get(upload_id)
    if upload is None:
        return _api_error('Upload session not found or expired', 404)

    received = len(upload['received'])
    total = upload['total_chunks']
    if received < total:
        missing = sorted(set(range(total)) - upload['received'])
        return _api_error(
            f'Missing {total - received} chunk(s): {missing[:20]}', 400)

    # Reassemble chunks into final file
    job_id = str(uuid.uuid4())
    filename = upload['filename']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'{job_id}_{filename}')

    try:
        with open(filepath, 'wb') as outf:
            for i in range(total):
                chunk_path = os.path.join(upload['chunk_dir'], f'chunk_{i:04d}')
                with open(chunk_path, 'rb') as cf:
                    while True:
                        block = cf.read(8 * 1024 * 1024)  # 8MB at a time
                        if not block:
                            break
                        outf.write(block)
    except Exception as e:
        return _api_error(f'Failed to reassemble file: {e}', 500)

    # Clean up chunk directory
    shutil.rmtree(upload['chunk_dir'], ignore_errors=True)
    with _chunked_uploads_lock:
        _chunked_uploads.pop(upload_id, None)

    # Create job
    params = upload['params']
    job_dict = {
        'id': job_id,
        'filename': filename,
        'input_file': filepath,
        'status': 'queued',
        'progress': 0,
        'message': 'Waiting in queue...',
        'created_at': datetime.now().isoformat(),
        'file_size_mb': round(os.path.getsize(filepath) / (1024 * 1024), 2),
        'output_files': [],
        **params,
    }
    db_save_job(job_dict)
    job_queue.put(job_id)

    return jsonify({
        'success': True,
        'job_id': job_id,
        'filename': filename,
        'file_size_mb': job_dict['file_size_mb'],
    })


_gpu_cache = {'info': None, 'checked_at': 0}


@app.route('/api/v1/health', methods=['GET'])
@limiter.exempt
def api_health():
    """Health check with queue stats and GPU info."""
    # GPU check — cached for 60 seconds (subprocess is slow)
    now = time.time()
    if _gpu_cache['info'] is None or now - _gpu_cache['checked_at'] > 60:
        try:
            result = subprocess.run(
                ['python3', '-c',
                 'import torch; print(torch.cuda.is_available()); '
                 'print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")'],
                capture_output=True, text=True, timeout=10)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 1:
                gpu_available = lines[0].strip() == 'True'
                gpu_name = lines[1].strip() if len(lines) > 1 else ''
                _gpu_cache['info'] = {'available': gpu_available, 'device': gpu_name}
            else:
                _gpu_cache['info'] = {'available': False, 'device': ''}
        except Exception:
            _gpu_cache['info'] = {'available': False, 'device': ''}
        _gpu_cache['checked_at'] = now
    gpu_info = _gpu_cache['info']

    all_jobs = db_list_jobs()
    return jsonify({
        'status': 'healthy',
        'queue_size': job_queue.qsize(),
        'total_jobs': len(all_jobs),
        'processing': sum(1 for j in all_jobs if j['status'] == 'processing'),
        'queued': sum(1 for j in all_jobs if j['status'] == 'queued'),
        'completed': sum(1 for j in all_jobs if j['status'] == 'completed'),
        'failed': sum(1 for j in all_jobs if j['status'] == 'failed'),
        'gpu': gpu_info,
        'supported_formats': sorted(ALLOWED_EXTENSIONS),
        'supported_models': sorted(VALID_MODELS),
        'chunk_size_mb': app.config['CHUNK_SIZE_MB'],
        'max_request_mb': 55,
    })


# ===========================================================================
# Legacy routes (frontend compatibility)
# ===========================================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/docs')
def docs():
    return render_template('docs.html')


@app.route('/openapi.json')
@limiter.exempt
def openapi_spec():
    """Serve the OpenAPI 3.0 specification."""
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "Local Transcription Tool API",
            "description": "AI-powered audio & video transcription with GPU acceleration, speaker detection, and animated quote extraction. All processing runs locally.",
            "version": "2.0.0",
            "contact": {"url": "https://github.com/sandbreak80/local_transcription"},
            "license": {"name": "MIT"},
        },
        "servers": [
            {"url": "https://transcript.fluximetry.com", "description": "Production"},
            {"url": "http://localhost:5731", "description": "Local development"},
        ],
        "tags": [
            {"name": "Jobs", "description": "Upload files and manage transcription jobs"},
            {"name": "Chunked Upload", "description": "Upload large files in 50MB chunks (required behind Cloudflare Tunnels)"},
            {"name": "Health", "description": "Server health and capabilities"},
        ],
        "paths": {
            "/api/v1/jobs": {
                "post": {
                    "tags": ["Jobs"],
                    "summary": "Upload file(s) and start transcription",
                    "description": "Upload one or more audio/video files (max 50MB per request). For larger files, use the chunked upload endpoints.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "required": ["files"],
                                    "properties": {
                                        "files": {"type": "string", "format": "binary", "description": "Audio/video file(s)"},
                                        "model": {"type": "string", "enum": ["tiny", "base", "small", "medium", "large"], "default": "base", "description": "Whisper model size"},
                                        "language": {"type": "string", "default": "auto", "description": "Language code (e.g., en, es, fr) or 'auto' for detection"},
                                        "animated_quotes": {"type": "string", "enum": ["true", "false"], "default": "false", "description": "Enable voice inflection analysis"},
                                        "two_list_quotes": {"type": "string", "enum": ["true", "false"], "default": "false", "description": "Enable two-list quote detection"},
                                        "speaker_diarization": {"type": "string", "enum": ["true", "false"], "default": "false", "description": "Enable AI speaker detection"},
                                        "num_speakers": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Expected number of speakers (auto-detect if omitted)"},
                                        "speaker_names": {"type": "string", "description": "Comma-separated speaker names (e.g., 'Alice,Bob')"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Jobs created", "content": {"application/json": {"schema": {"type": "object", "properties": {"success": {"type": "boolean"}, "jobs": {"type": "array", "items": {"type": "object", "properties": {"job_id": {"type": "string"}, "filename": {"type": "string"}}}}}}}}},
                        "400": {"description": "Validation error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "429": {"description": "Rate limit exceeded"},
                    },
                },
                "get": {
                    "tags": ["Jobs"],
                    "summary": "List all jobs",
                    "parameters": [
                        {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["queued", "processing", "completed", "failed"]}, "description": "Filter by status"},
                    ],
                    "responses": {
                        "200": {"description": "Job list", "content": {"application/json": {"schema": {"type": "object", "properties": {"jobs": {"type": "array", "items": {"$ref": "#/components/schemas/Job"}}}}}}},
                    },
                },
            },
            "/api/v1/jobs/{job_id}": {
                "get": {
                    "tags": ["Jobs"],
                    "summary": "Get job details",
                    "parameters": [{"name": "job_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Job details", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Job"}}}},
                        "404": {"description": "Job not found"},
                    },
                },
                "delete": {
                    "tags": ["Jobs"],
                    "summary": "Cancel or delete a job",
                    "description": "Cancels a queued/processing job (kills subprocess if running) or deletes a completed/failed job. Cleans up all associated files.",
                    "parameters": [{"name": "job_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Job deleted"},
                        "404": {"description": "Job not found"},
                    },
                },
            },
            "/api/v1/jobs/{job_id}/files/{filename}": {
                "get": {
                    "tags": ["Jobs"],
                    "summary": "Download an output file",
                    "description": "Download a .vtt (WebVTT) or .json output file from a completed job.",
                    "parameters": [
                        {"name": "job_id", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "filename", "in": "path", "required": True, "schema": {"type": "string"}, "description": "e.g., meeting.vtt or meeting.json"},
                    ],
                    "responses": {
                        "200": {"description": "File content"},
                        "400": {"description": "Job not completed"},
                        "404": {"description": "Job or file not found"},
                    },
                },
            },
            "/api/v1/uploads": {
                "post": {
                    "tags": ["Chunked Upload"],
                    "summary": "Initiate chunked upload",
                    "description": "Start a chunked upload session for files over 50MB. Returns an upload_id to use for subsequent chunk uploads.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["filename", "total_chunks"],
                                    "properties": {
                                        "filename": {"type": "string", "description": "Original filename (e.g., 'meeting.mp4')"},
                                        "total_chunks": {"type": "integer", "minimum": 1, "maximum": 200, "description": "Total number of chunks"},
                                        "total_size_mb": {"type": "number", "description": "Total file size in MB (informational)"},
                                        "model": {"type": "string", "enum": ["tiny", "base", "small", "medium", "large"], "default": "base"},
                                        "language": {"type": "string", "default": "auto"},
                                        "animated_quotes": {"type": "string", "enum": ["true", "false"], "default": "false"},
                                        "two_list_quotes": {"type": "string", "enum": ["true", "false"], "default": "false"},
                                        "speaker_diarization": {"type": "string", "enum": ["true", "false"], "default": "false"},
                                        "num_speakers": {"type": "integer", "minimum": 1, "maximum": 20},
                                        "speaker_names": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Upload session created", "content": {"application/json": {"schema": {"type": "object", "properties": {"upload_id": {"type": "string"}, "filename": {"type": "string"}, "total_chunks": {"type": "integer"}, "chunk_size_mb": {"type": "integer"}}}}}},
                        "400": {"description": "Validation error"},
                    },
                },
            },
            "/api/v1/uploads/{upload_id}/chunks": {
                "post": {
                    "tags": ["Chunked Upload"],
                    "summary": "Upload a chunk",
                    "description": "Upload a single chunk (max 50MB). Rate limit exempt for streaming.",
                    "parameters": [{"name": "upload_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "required": ["chunk", "chunk_index"],
                                    "properties": {
                                        "chunk": {"type": "string", "format": "binary", "description": "Chunk data (max 50MB)"},
                                        "chunk_index": {"type": "integer", "description": "0-based chunk index"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Chunk received", "content": {"application/json": {"schema": {"type": "object", "properties": {"upload_id": {"type": "string"}, "chunk_index": {"type": "integer"}, "received": {"type": "integer"}, "total_chunks": {"type": "integer"}, "complete": {"type": "boolean"}}}}}},
                        "400": {"description": "Invalid chunk"},
                        "404": {"description": "Upload session not found"},
                    },
                },
            },
            "/api/v1/uploads/{upload_id}/complete": {
                "post": {
                    "tags": ["Chunked Upload"],
                    "summary": "Finalize chunked upload",
                    "description": "Reassemble all chunks and start the transcription job. Call after all chunks are uploaded.",
                    "parameters": [{"name": "upload_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Job created", "content": {"application/json": {"schema": {"type": "object", "properties": {"success": {"type": "boolean"}, "job_id": {"type": "string"}, "filename": {"type": "string"}, "file_size_mb": {"type": "number"}}}}}},
                        "400": {"description": "Missing chunks"},
                        "404": {"description": "Upload session not found"},
                    },
                },
            },
            "/api/v1/health": {
                "get": {
                    "tags": ["Health"],
                    "summary": "Health check",
                    "description": "Returns server status, GPU info, queue stats, and supported formats/models. Rate limit exempt.",
                    "responses": {
                        "200": {"description": "Health status", "content": {"application/json": {"schema": {"type": "object", "properties": {"status": {"type": "string"}, "gpu": {"type": "object", "properties": {"available": {"type": "boolean"}, "device": {"type": "string"}}}, "queue_size": {"type": "integer"}, "processing": {"type": "integer"}, "completed": {"type": "integer"}, "failed": {"type": "integer"}, "supported_formats": {"type": "array", "items": {"type": "string"}}, "supported_models": {"type": "array", "items": {"type": "string"}}, "chunk_size_mb": {"type": "integer"}, "max_request_mb": {"type": "integer"}}}}}},
                    },
                },
            },
        },
        "components": {
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                },
                "Job": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Job UUID"},
                        "filename": {"type": "string"},
                        "status": {"type": "string", "enum": ["queued", "processing", "completed", "failed", "cancelled"]},
                        "progress": {"type": "integer", "minimum": 0, "maximum": 100},
                        "message": {"type": "string"},
                        "model": {"type": "string"},
                        "language": {"type": "string"},
                        "animated_quotes": {"type": "boolean"},
                        "two_list_quotes": {"type": "boolean"},
                        "speaker_diarization": {"type": "boolean"},
                        "file_size_mb": {"type": "number"},
                        "created_at": {"type": "string", "format": "date-time"},
                        "completed_at": {"type": "string", "format": "date-time", "nullable": True},
                        "output_files": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "size": {"type": "integer"}}}},
                    },
                },
            },
        },
    }
    return jsonify(spec)


@app.route('/upload', methods=['POST'])
def legacy_upload():
    resp, code = _handle_upload(request)
    return jsonify(resp), code


@app.route('/status/<job_id>')
def legacy_job_status(job_id):
    job = db_get_job(job_id)
    if job is None:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(_job_response(job))


@app.route('/status')
def legacy_all_status():
    jobs_list = db_list_jobs()
    return jsonify({'jobs': [_job_response(j) for j in jobs_list]})


@app.route('/download/<job_id>/<filename>')
def legacy_download(job_id, filename):
    job = db_get_job(job_id)
    if job is None:
        return jsonify({'error': 'Job not found'}), 404
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed'}), 400
    for output_file in job.get('output_files', []):
        if output_file['name'] == filename:
            if os.path.exists(output_file['path']):
                return send_file(output_file['path'],
                                 as_attachment=True,
                                 download_name=filename)
            return jsonify({'error': 'File no longer exists'}), 410
    return jsonify({'error': 'File not found'}), 404


@app.route('/scan-outputs')
def legacy_scan_outputs():
    output_dir = app.config['OUTPUT_FOLDER']
    files_found = []
    for file_path in Path(output_dir).glob('*.vtt'):
        base_name = file_path.stem
        json_file = file_path.with_suffix('.json')
        if not json_file.exists():
            continue
        # Skip if we already have a job for this file
        existing = db_list_jobs()
        if any(j['filename'].startswith(base_name) and j['status'] == 'completed'
               for j in existing):
            continue
        job_id = str(uuid.uuid4())
        output_files = []
        for ext in ['.vtt', '.json']:
            f = file_path.parent / f"{base_name}{ext}"
            if f.exists():
                output_files.append({
                    'name': f.name, 'path': str(f), 'size': f.stat().st_size
                })
        job_dict = {
            'id': job_id, 'filename': base_name + '.mp4',
            'status': 'completed', 'progress': 100,
            'message': 'Transcription completed!',
            'model': 'base', 'language': 'auto',
            'file_size_mb': 0, 'output_files': output_files,
            'created_at': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            'completed_at': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        }
        db_save_job(job_dict)
        files_found.append(base_name)
    return jsonify({'success': True, 'files_found': len(files_found),
                    'jobs_created': len(files_found)})


@app.route('/health')
@limiter.exempt
def legacy_health():
    all_jobs = db_list_jobs()
    return jsonify({
        'status': 'healthy',
        'queue_size': job_queue.qsize(),
        'total_jobs': len(all_jobs),
        'processing': sum(1 for j in all_jobs if j['status'] == 'processing'),
        'queued': sum(1 for j in all_jobs if j['status'] == 'queued'),
        'completed': sum(1 for j in all_jobs if j['status'] == 'completed'),
        'failed': sum(1 for j in all_jobs if j['status'] == 'failed')
    })


# ===========================================================================
# Global error handlers
# ===========================================================================

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 2GB.'}), 413


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(429)
def rate_limited(e):
    return jsonify({'error': 'Rate limit exceeded. Maximum 1 request per second.'}), 429


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


# ===========================================================================
# Main
# ===========================================================================

if __name__ == '__main__':
    init_db()
    restore_queued_jobs()

    port = int(os.environ.get('FLASK_PORT', 5731))
    print("=" * 70)
    print("Local Transcription Tool — Web Interface & API")
    print("=" * 70)
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Output folder: {app.config['OUTPUT_FOLDER']}")
    print(f"Database:      {app.config['DB_PATH']}")
    print(f"Server:        http://0.0.0.0:{port}")
    print(f"API docs:      http://0.0.0.0:{port}/api/v1/health")
    print("=" * 70)

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
