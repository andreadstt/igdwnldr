/**
 * Instagram Downloader Web App
 * Main JavaScript file for handling UI interactions and API calls
 */

// Global state
let currentTaskId = null;
let statusCheckInterval = null;
let currentFolderName = null;

// DOM Elements
const urlInput = document.getElementById('ig-url');
const parseBtn = document.getElementById('parse-btn');
const downloadBtn = document.getElementById('download-btn');
const parseResult = document.getElementById('parse-result');
const parseInfo = document.getElementById('parse-info');
const progressSection = document.getElementById('progress-section');
const progressBar = document.getElementById('progress-bar');
const progressPercent = document.getElementById('progress-percent');
const progressMessage = document.getElementById('progress-message');
const resultSection = document.getElementById('result-section');
const successResult = document.getElementById('success-result');
const errorResult = document.getElementById('error-result');
const successMessage = document.getElementById('success-message');
const errorMessage = document.getElementById('error-message');
const openFolderBtn = document.getElementById('open-folder-btn');
const viewListBtn = document.getElementById('view-list-btn');
const folderPath = document.getElementById('folder-path');
const newDownloadBtn = document.getElementById('new-download-btn');

// Event Listeners
parseBtn.addEventListener('click', handleParse);
downloadBtn.addEventListener('click', handleDownload);
newDownloadBtn.addEventListener('click', resetForm);
urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleParse();
    }
});

// Handle URL/username parsing
async function handleParse() {
    const url = urlInput.value.trim();

    if (!url) {
        showToast('Please enter an Instagram URL or username', 'warning');
        return;
    }

    parseBtn.disabled = true;
    parseBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';

    // Hide preview while checking
    const previewSection = document.getElementById('preview-section');
    if (previewSection) {
        previewSection.classList.add('hidden');
    }

    try {
        const response = await fetch('/api/parse', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });

        const data = await response.json();

        if (response.ok) {
            // Show parse result
            parseResult.classList.remove('hidden');
            parseInfo.textContent = data.description;
            downloadBtn.disabled = false;

            // Show preview if available
            if (data.preview && data.preview.success) {
                showPreview(data.preview);
            } else if (data.preview_error) {
                showToast('Preview not available: ' + data.preview_error, 'warning');
            }

            showToast('Valid URL detected!', 'success');
        } else {
            showToast(data.error || 'Invalid URL', 'error');
            parseResult.classList.add('hidden');
            downloadBtn.disabled = true;
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
        parseResult.classList.add('hidden');
        downloadBtn.disabled = true;
    } finally {
        parseBtn.disabled = false;
        parseBtn.innerHTML = '<i class="fas fa-search"></i> Check';
    }
}

// Show preview of post
function showPreview(preview) {
    const previewSection = document.getElementById('preview-section');
    const previewImage = document.getElementById('preview-image');
    const previewOwner = document.getElementById('preview-owner');
    const previewLikes = document.getElementById('preview-likes');
    const previewComments = document.getElementById('preview-comments');
    const previewCaption = document.getElementById('preview-caption');
    const previewVideoBadge = document.getElementById('preview-video-badge');

    // Set image
    if (preview.thumbnail_url) {
        previewImage.src = preview.thumbnail_url;
        previewImage.onerror = () => {
            previewImage.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect fill="%23ddd" width="200" height="200"/><text x="50%" y="50%" fill="%23999" text-anchor="middle" dy=".3em">No Preview</text></svg>';
        };
    }

    // Set metadata
    previewOwner.textContent = `@${preview.owner || 'unknown'}`;
    previewLikes.textContent = formatNumber(preview.likes || 0);
    previewComments.textContent = formatNumber(preview.comments || 0);
    previewCaption.textContent = preview.caption || 'No caption';

    // Show video badge if it's a video
    if (preview.is_video && previewVideoBadge) {
        previewVideoBadge.classList.remove('hidden');
    } else if (previewVideoBadge) {
        previewVideoBadge.classList.add('hidden');
    }

    // Show preview section
    previewSection.classList.remove('hidden');

    // Scroll to preview
    previewSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Format large numbers (e.g., 1500 -> 1.5K)
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Handle download start
async function handleDownload() {
    const url = urlInput.value.trim();

    if (!url) {
        showToast('Please enter an Instagram URL or username', 'warning');
        return;
    }

    downloadBtn.disabled = true;
    downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Starting...';

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });

        const data = await response.json();

        if (response.ok) {
            currentTaskId = data.task_id;
            showProgressSection();
            startStatusCheck();
            showToast('Download started!', 'success');
        } else {
            showToast(data.error || 'Failed to start download', 'error');
            downloadBtn.disabled = false;
            downloadBtn.innerHTML = '<i class="fas fa-download mr-2"></i> Start Download';
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = '<i class="fas fa-download mr-2"></i> Start Download';
    }
}

// Show progress section
function showProgressSection() {
    progressSection.classList.remove('hidden');
    resultSection.classList.add('hidden');
    successResult.classList.add('hidden');
    errorResult.classList.add('hidden');
    newDownloadBtn.classList.add('hidden');

    // Scroll to progress section
    progressSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Start checking download status
function startStatusCheck() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }

    statusCheckInterval = setInterval(checkStatus, 1000);
}

// Check download status
async function checkStatus() {
    if (!currentTaskId) return;

    try {
        const response = await fetch(`/api/status/${currentTaskId}`);
        const data = await response.json();

        if (response.ok) {
            // Update progress bar
            updateProgress(data.progress, data.message);

            // Check if completed
            if (data.status === 'completed') {
                clearInterval(statusCheckInterval);
                handleDownloadComplete(data);
            } else if (data.status === 'failed') {
                clearInterval(statusCheckInterval);
                handleDownloadFailed(data);
            }
        } else {
            clearInterval(statusCheckInterval);
            showToast('Error checking status', 'error');
        }
    } catch (error) {
        console.error('Status check error:', error);
    }
}

// Update progress bar and message
function updateProgress(percent, message) {
    progressBar.style.width = percent + '%';
    progressPercent.textContent = percent;
    progressMessage.textContent = message;
}

// Handle successful download
function handleDownloadComplete(data) {
    resultSection.classList.remove('hidden');
    successResult.classList.remove('hidden');
    errorResult.classList.add('hidden');
    newDownloadBtn.classList.remove('hidden');

    successMessage.textContent = data.result_message || 'Download completed successfully!';
    currentFolderName = data.folder;

    // Show folder path
    if (currentFolderName && folderPath) {
        folderPath.textContent = currentFolderName;
    }

    // Setup open/view buttons
    if (currentFolderName) {
        openFolderBtn.onclick = () => openFolder(currentFolderName);
        viewListBtn.onclick = () => window.location.href = '/downloads';
    }

    showToast('Download completed!', 'success');
}

// Handle failed download
function handleDownloadFailed(data) {
    resultSection.classList.remove('hidden');
    successResult.classList.add('hidden');
    errorResult.classList.remove('hidden');
    newDownloadBtn.classList.remove('hidden');

    errorMessage.textContent = data.message || 'Download failed. Please try again.';

    showToast('Download failed', 'error');
}

// Open folder in file manager
async function openFolder(folderName) {
    try {
        const response = await fetch(`/api/open-folder/${folderName}`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            showToast('Opening folder in file manager...', 'success');
        } else {
            showToast(data.error || 'Failed to open folder', 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

// Reset form for new download
function resetForm() {
    // Reset input
    urlInput.value = '';

    // Hide sections
    parseResult.classList.add('hidden');
    const previewSection = document.getElementById('preview-section');
    if (previewSection) {
        previewSection.classList.add('hidden');
    }
    progressSection.classList.add('hidden');
    resultSection.classList.add('hidden');

    // Reset buttons
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = '<i class="fas fa-download mr-2"></i> Start Download';

    // Clear state
    currentTaskId = null;
    currentFolderName = null;

    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }

    // Reset progress
    updateProgress(0, 'Initializing...');

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('IG Downloader initialized');
});
