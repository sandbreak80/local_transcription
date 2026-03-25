// Local Transcription Tool - Web Interface JavaScript
// Local Transcription Tool

const CHUNK_SIZE = 50 * 1024 * 1024; // 50MB chunks (Cloudflare Tunnel safe)

let selectedFiles = [];
let activeJobs = new Set();

// DOM elements
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const jobsSection = document.getElementById('jobsSection');
const jobsList = document.getElementById('jobsList');

// File selection handlers
uploadBox.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});

// Drag and drop handlers
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('dragover');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('dragover');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
});

// Handle selected files
function handleFiles(files) {
    selectedFiles = Array.from(files);

    const uploadTitle = document.getElementById('uploadTitle');
    const uploadDescription = document.getElementById('uploadDescription');
    const fileListDiv = document.getElementById('fileList');

    if (selectedFiles.length > 0) {
        uploadBtn.disabled = false;
        uploadTitle.textContent = `${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''} selected`;
        uploadDescription.style.display = 'none';

        const fileList = selectedFiles.map(f => {
            const escapedName = escapeHtml(f.name);
            const needsChunking = f.size > CHUNK_SIZE;
            const chunkLabel = needsChunking ? ' <span style="color: #ffd700;">[chunked upload]</span>' : '';
            return `<div style="padding: 5px 0; color: #fff;">${escapedName} <span style="color: #aaa;">(${formatFileSize(f.size)})</span>${chunkLabel}</div>`;
        }).join('');
        fileListDiv.innerHTML = fileList;
        fileListDiv.style.display = 'block';
    } else {
        uploadBtn.disabled = true;
        resetUploadBox();
    }
}

function resetUploadBox() {
    document.getElementById('uploadTitle').textContent = 'Drop files here or click to browse';
    document.getElementById('uploadDescription').textContent = 'Supports: MP4, MP3, WAV, AVI, MOV, MKV, and more';
    document.getElementById('uploadDescription').style.display = 'block';
    document.getElementById('fileList').style.display = 'none';
    document.getElementById('fileList').innerHTML = '';
}

// Gather transcription options from the form
function getOptions() {
    const opts = {
        model: document.getElementById('modelSelect').value,
        language: document.getElementById('languageSelect').value,
        animated_quotes: document.getElementById('animatedQuotes').checked ? 'true' : 'false',
        two_list_quotes: document.getElementById('twoListQuotes').checked ? 'true' : 'false',
        speaker_diarization: document.getElementById('speakerDiarization').checked ? 'true' : 'false',
    };
    const numSpeakers = document.getElementById('numSpeakers').value;
    if (numSpeakers) opts.num_speakers = numSpeakers;
    const speakerNames = document.getElementById('speakerNames').value;
    if (speakerNames) opts.speaker_names = speakerNames;
    return opts;
}

// ---------------------------------------------------------------------------
// Small file upload (single request, < 50MB)
// ---------------------------------------------------------------------------
async function uploadSmallFile(file, options) {
    const formData = new FormData();
    formData.append('files', file);
    Object.entries(options).forEach(([k, v]) => formData.append(k, v));

    const response = await fetch('/upload', { method: 'POST', body: formData });
    const result = await response.json();
    if (!response.ok || !result.success) {
        throw new Error(result.error || 'Upload failed');
    }
    return result.jobs[0];
}

// ---------------------------------------------------------------------------
// Chunked upload (multiple requests, for files > 50MB)
// ---------------------------------------------------------------------------
async function uploadChunkedFile(file, options, onProgress) {
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

    // Step 1: Initiate upload session
    const initResp = await fetch('/api/v1/uploads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            filename: file.name,
            total_chunks: totalChunks,
            total_size_mb: Math.round(file.size / (1024 * 1024) * 100) / 100,
            ...options,
        }),
    });
    const initData = await initResp.json();
    if (!initResp.ok) {
        throw new Error(initData.error || 'Failed to initiate upload');
    }
    const uploadId = initData.upload_id;

    // Step 2: Upload each chunk
    for (let i = 0; i < totalChunks; i++) {
        const start = i * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, file.size);
        const chunkBlob = file.slice(start, end);

        const chunkForm = new FormData();
        chunkForm.append('chunk', chunkBlob, `chunk_${i}`);
        chunkForm.append('chunk_index', i);

        const chunkResp = await fetch(`/api/v1/uploads/${uploadId}/chunks`, {
            method: 'POST',
            body: chunkForm,
        });
        if (!chunkResp.ok) {
            const err = await chunkResp.json();
            throw new Error(err.error || `Chunk ${i} upload failed`);
        }
        if (onProgress) {
            onProgress(Math.round(((i + 1) / totalChunks) * 100));
        }
    }

    // Step 3: Finalize
    const completeResp = await fetch(`/api/v1/uploads/${uploadId}/complete`, {
        method: 'POST',
    });
    const completeData = await completeResp.json();
    if (!completeResp.ok) {
        throw new Error(completeData.error || 'Failed to finalize upload');
    }

    return { job_id: completeData.job_id, filename: completeData.filename };
}

// ---------------------------------------------------------------------------
// Upload handler — auto-selects chunked vs single based on file size
// ---------------------------------------------------------------------------
uploadBtn.addEventListener('click', async () => {
    if (selectedFiles.length === 0) return;

    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Uploading...';
    const options = getOptions();

    try {
        for (const file of selectedFiles) {
            let job;

            if (file.size > CHUNK_SIZE) {
                // Chunked upload for large files
                uploadBtn.textContent = `Uploading ${escapeHtml(file.name)} (0%)...`;
                job = await uploadChunkedFile(file, options, (pct) => {
                    uploadBtn.textContent = `Uploading ${escapeHtml(file.name)} (${pct}%)...`;
                });
            } else {
                // Single-request upload for small files
                uploadBtn.textContent = `Uploading ${escapeHtml(file.name)}...`;
                job = await uploadSmallFile(file, options);
            }

            // Track the job
            jobsSection.style.display = 'block';
            activeJobs.add(job.job_id);
            createJobCard(job.job_id, job.filename);
        }

        startPolling();

        // Reset
        selectedFiles = [];
        fileInput.value = '';
        uploadBtn.textContent = 'Upload & Start Transcription';
        resetUploadBox();
        jobsSection.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Upload error:', error);
        alert(`Upload failed: ${error.message}`);
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload & Start Transcription';
    }
});

// Create job card in UI
function createJobCard(jobId, filename) {
    const card = document.createElement('div');
    card.className = 'job-card';
    card.id = `job-${jobId}`;
    const escapedFilename = escapeHtml(filename);
    card.innerHTML = `
        <div class="job-header">
            <div class="job-filename">${escapedFilename}</div>
            <div class="job-status status-queued">Queued</div>
        </div>
        <div class="job-info">
            <span>Model: <strong id="model-${jobId}">-</strong></span>
            <span>Language: <strong id="lang-${jobId}">-</strong></span>
            <span>Size: <strong id="size-${jobId}">-</strong></span>
        </div>
        <div class="job-message" id="message-${jobId}">Waiting in queue...</div>
        <div class="progress-bar">
            <div class="progress-fill" id="progress-${jobId}" style="width: 0%">0%</div>
        </div>
        <div class="download-section" id="downloads-${jobId}" style="display: none;">
            <h4>Download Results:</h4>
            <div id="download-links-${jobId}"></div>
        </div>
    `;

    jobsList.insertBefore(card, jobsList.firstChild);
}

// Update job status
function updateJobCard(job) {
    const card = document.getElementById(`job-${job.id}`);
    if (!card) return;

    // Update status badge
    const statusBadge = card.querySelector('.job-status');
    statusBadge.className = `job-status status-${job.status}`;
    statusBadge.textContent = job.status.charAt(0).toUpperCase() + job.status.slice(1);

    // Update info
    const modelEl = document.getElementById(`model-${job.id}`);
    if (modelEl) modelEl.textContent = job.model || '-';
    const langEl = document.getElementById(`lang-${job.id}`);
    if (langEl) langEl.textContent = job.language === 'auto' ? 'Auto-detect' : (job.language || '-');
    const sizeEl = document.getElementById(`size-${job.id}`);
    if (sizeEl) sizeEl.textContent = `${job.file_size_mb} MB`;

    // Update message
    const msgEl = document.getElementById(`message-${job.id}`);
    if (msgEl) msgEl.textContent = job.message;

    // Update progress bar
    const progressFill = document.getElementById(`progress-${job.id}`);
    if (progressFill) {
        progressFill.style.width = `${job.progress}%`;
        progressFill.textContent = `${job.progress}%`;
    }

    // Add processing animation
    if (job.status === 'processing') {
        card.classList.add('processing-animation');
    } else {
        card.classList.remove('processing-animation');
    }

    // Show downloads if completed
    if (job.status === 'completed' && job.output_files && job.output_files.length > 0) {
        const downloadsSection = document.getElementById(`downloads-${job.id}`);
        if (downloadsSection) {
            downloadsSection.style.display = 'block';
            const linksContainer = document.getElementById(`download-links-${job.id}`);
            if (linksContainer) {
                linksContainer.innerHTML = job.output_files.map(file =>
                    `<a href="/download/${job.id}/${escapeHtml(file.name)}" class="download-link" download>
                        ${escapeHtml(file.name)} (${formatFileSize(file.size)})
                    </a>`
                ).join('');
            }
        }
    }
}

// Poll for job status updates
let pollingInterval = null;

function startPolling() {
    if (pollingInterval) return;

    pollingInterval = setInterval(async () => {
        if (activeJobs.size === 0) {
            stopPolling();
            return;
        }

        for (const jobId of activeJobs) {
            try {
                const response = await fetch(`/status/${jobId}`);
                if (!response.ok) {
                    activeJobs.delete(jobId);
                    continue;
                }
                const job = await response.json();

                updateJobCard(job);

                // Remove from active jobs if completed or failed
                if (job.status === 'completed' || job.status === 'failed') {
                    activeJobs.delete(jobId);
                }
            } catch (error) {
                console.error(`Error fetching status for job ${jobId}:`, error);
            }
        }
    }, 2000);
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Local Transcription Tool - Web Interface Ready');
});
