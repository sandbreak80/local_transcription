// Local Transcription Tool - Web Interface JavaScript
// Author: Brad Stoner (bmstoner@cisco.com)

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
    
    if (selectedFiles.length > 0) {
        uploadBtn.disabled = false;
        uploadBox.querySelector('h2').textContent = 
            `${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''} selected`;
        
        const fileList = selectedFiles.map(f => `• ${f.name} (${formatFileSize(f.size)})`).join('<br>');
        uploadBox.querySelector('p').innerHTML = fileList;
    } else {
        uploadBtn.disabled = true;
        resetUploadBox();
    }
}

function resetUploadBox() {
    uploadBox.querySelector('h2').textContent = 'Drop files here or click to browse';
    uploadBox.querySelector('p').textContent = 'Supports: MP4, MP3, WAV, AVI, MOV, MKV, and more';
}

// Upload and start transcription
uploadBtn.addEventListener('click', async () => {
    if (selectedFiles.length === 0) return;
    
    const formData = new FormData();
    selectedFiles.forEach(file => formData.append('files', file));
    
    // Add options
    formData.append('model', document.getElementById('modelSelect').value);
    formData.append('language', document.getElementById('languageSelect').value);
    formData.append('animated_quotes', document.getElementById('animatedQuotes').checked);
    formData.append('two_list_quotes', document.getElementById('twoListQuotes').checked);
    
    // Disable upload button
    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Uploading...';
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Show jobs section
            jobsSection.style.display = 'block';
            
            // Add jobs to tracking
            result.jobs.forEach(job => {
                activeJobs.add(job.job_id);
                createJobCard(job.job_id, job.filename);
            });
            
            // Start polling for updates
            startPolling();
            
            // Reset upload section
            selectedFiles = [];
            fileInput.value = '';
            uploadBtn.textContent = 'Upload & Start Transcription';
            resetUploadBox();
            
            // Scroll to jobs section
            jobsSection.scrollIntoView({ behavior: 'smooth' });
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('Upload failed. Please try again.');
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload & Start Transcription';
    }
});

// Create job card in UI
function createJobCard(jobId, filename) {
    const card = document.createElement('div');
    card.className = 'job-card';
    card.id = `job-${jobId}`;
    card.innerHTML = `
        <div class="job-header">
            <div class="job-filename">${filename}</div>
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
            <h4>📥 Download Results:</h4>
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
    document.getElementById(`model-${job.id}`).textContent = job.model;
    document.getElementById(`lang-${job.id}`).textContent = job.language === 'auto' ? 'Auto-detect' : job.language;
    document.getElementById(`size-${job.id}`).textContent = `${job.file_size_mb} MB`;
    
    // Update message
    document.getElementById(`message-${job.id}`).textContent = job.message;
    
    // Update progress bar
    const progressFill = document.getElementById(`progress-${job.id}`);
    progressFill.style.width = `${job.progress}%`;
    progressFill.textContent = `${job.progress}%`;
    
    // Add processing animation
    if (job.status === 'processing') {
        card.classList.add('processing-animation');
    } else {
        card.classList.remove('processing-animation');
    }
    
    // Show downloads if completed
    if (job.status === 'completed' && job.output_files && job.output_files.length > 0) {
        const downloadsSection = document.getElementById(`downloads-${job.id}`);
        downloadsSection.style.display = 'block';
        
        const linksContainer = document.getElementById(`download-links-${job.id}`);
        linksContainer.innerHTML = job.output_files.map(file => 
            `<a href="/download/${job.id}/${file.name}" class="download-link" download>
                📄 ${file.name} (${formatFileSize(file.size)})
            </a>`
        ).join('');
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
    }, 2000); // Poll every 2 seconds
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Local Transcription Tool - Web Interface Ready');
    console.log('Author: Brad Stoner (bmstoner@cisco.com)');
});

