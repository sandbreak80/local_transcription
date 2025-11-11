#!/usr/bin/env python3
"""
Web Interface for Local Transcription Tool
Author: Brad Stoner (bmstoner@cisco.com)
Created for: Splunk and Cisco
"""

import os
import json
import uuid
import threading
import time
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import subprocess
import queue

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/transcription_uploads'
app.config['OUTPUT_FOLDER'] = '/tmp/transcription_outputs'

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Job tracking
jobs = {}
job_queue = queue.Queue()
processing_lock = threading.Lock()

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'mp4', 'mp3', 'wav', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm',
    'm4v', 'm4a', 'aac', 'flac', 'ogg', 'wma', 'mpeg', 'mpg'
}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size_mb(filepath):
    """Get file size in MB"""
    return os.path.getsize(filepath) / (1024 * 1024)

def process_job(job_id):
    """Process a transcription job"""
    job = jobs[job_id]
    
    try:
        job['status'] = 'processing'
        job['progress'] = 10
        job['message'] = 'Starting transcription...'
        
        # Build command
        input_file = job['input_file']
        output_dir = app.config['OUTPUT_FOLDER']
        
        cmd = ['python3', '/app/transcribe.py', input_file]
        
        # Add model parameter
        if job['model']:
            cmd.extend(['--model', job['model']])
        
        # Add language parameter
        if job['language'] and job['language'] != 'auto':
            cmd.extend(['--language', job['language']])
        
        # Add optional features
        if job.get('animated_quotes'):
            cmd.append('--animated-quotes')
        
        if job.get('two_list_quotes'):
            cmd.append('--two-list-quotes')
        
        job['progress'] = 20
        job['message'] = 'Transcribing audio...'
        
        # Run transcription
        result = subprocess.run(
            cmd,
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            # Find output files
            base_name = Path(input_file).stem
            output_files = []
            
            # Look for generated files
            for ext in ['_transcription.txt', '_transcription.json', 
                       '_animated_quotes.txt', '_animated_quotes.json',
                       '_two_list_quotes.txt', '_two_list_quotes.json']:
                output_file = os.path.join(output_dir, base_name + ext)
                if os.path.exists(output_file):
                    output_files.append({
                        'name': os.path.basename(output_file),
                        'path': output_file,
                        'size': os.path.getsize(output_file)
                    })
            
            job['status'] = 'completed'
            job['progress'] = 100
            job['message'] = 'Transcription completed!'
            job['output_files'] = output_files
            job['completed_at'] = datetime.now().isoformat()
        else:
            job['status'] = 'failed'
            job['progress'] = 0
            job['message'] = f'Error: {result.stderr[:200]}'
            
    except subprocess.TimeoutExpired:
        job['status'] = 'failed'
        job['message'] = 'Transcription timed out (max 1 hour)'
    except Exception as e:
        job['status'] = 'failed'
        job['message'] = f'Error: {str(e)}'
    finally:
        # Clean up input file
        try:
            if os.path.exists(job['input_file']):
                os.remove(job['input_file'])
        except:
            pass

def worker_thread():
    """Background worker to process jobs from queue"""
    while True:
        try:
            job_id = job_queue.get(timeout=1)
            if job_id:
                process_job(job_id)
                job_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Worker error: {e}")

# Start worker thread
worker = threading.Thread(target=worker_thread, daemon=True)
worker.start()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    model = request.form.get('model', 'base')
    language = request.form.get('language', 'auto')
    animated_quotes = request.form.get('animated_quotes') == 'true'
    two_list_quotes = request.form.get('two_list_quotes') == 'true'
    
    uploaded_jobs = []
    
    for file in files:
        if file and allowed_file(file.filename):
            # Generate unique job ID
            job_id = str(uuid.uuid4())
            
            # Secure filename
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
            
            # Save file
            file.save(filepath)
            
            # Create job entry
            jobs[job_id] = {
                'id': job_id,
                'filename': filename,
                'input_file': filepath,
                'model': model,
                'language': language,
                'animated_quotes': animated_quotes,
                'two_list_quotes': two_list_quotes,
                'status': 'queued',
                'progress': 0,
                'message': 'Waiting in queue...',
                'created_at': datetime.now().isoformat(),
                'file_size_mb': round(get_file_size_mb(filepath), 2)
            }
            
            # Add to queue
            job_queue.put(job_id)
            
            uploaded_jobs.append({
                'job_id': job_id,
                'filename': filename
            })
    
    return jsonify({
        'success': True,
        'jobs': uploaded_jobs
    })

@app.route('/status/<job_id>')
def job_status(job_id):
    """Get job status"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    return jsonify({
        'id': job['id'],
        'filename': job['filename'],
        'status': job['status'],
        'progress': job['progress'],
        'message': job['message'],
        'model': job['model'],
        'language': job['language'],
        'file_size_mb': job['file_size_mb'],
        'created_at': job['created_at'],
        'completed_at': job.get('completed_at'),
        'output_files': job.get('output_files', [])
    })

@app.route('/status')
def all_status():
    """Get status of all jobs"""
    job_list = []
    for job_id, job in jobs.items():
        job_list.append({
            'id': job['id'],
            'filename': job['filename'],
            'status': job['status'],
            'progress': job['progress'],
            'message': job['message'],
            'created_at': job['created_at']
        })
    
    # Sort by creation time (newest first)
    job_list.sort(key=lambda x: x['created_at'], reverse=True)
    
    return jsonify({'jobs': job_list})

@app.route('/download/<job_id>/<filename>')
def download_file(job_id, filename):
    """Download output file"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed'}), 400
    
    # Find the file
    for output_file in job.get('output_files', []):
        if output_file['name'] == filename:
            return send_file(
                output_file['path'],
                as_attachment=True,
                download_name=filename
            )
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'queue_size': job_queue.qsize(),
        'total_jobs': len(jobs),
        'processing': sum(1 for j in jobs.values() if j['status'] == 'processing'),
        'queued': sum(1 for j in jobs.values() if j['status'] == 'queued'),
        'completed': sum(1 for j in jobs.values() if j['status'] == 'completed'),
        'failed': sum(1 for j in jobs.values() if j['status'] == 'failed')
    })

if __name__ == '__main__':
    print("=" * 70)
    print("🎙️  Local Transcription Tool - Web Interface")
    print("=" * 70)
    print(f"📂 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"📂 Output folder: {app.config['OUTPUT_FOLDER']}")
    print(f"🌐 Server starting on http://0.0.0.0:5000")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

