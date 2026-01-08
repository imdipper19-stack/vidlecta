/**
 * VidLecta - Dashboard JavaScript
 */

const API_URL = '/api';

/**
 * Dashboard Manager
 */
class Dashboard {
    constructor() {
        this.user = null;
        this.init();
    }

    async init() {
        // Check authentication
        const token = localStorage.getItem('access_token');
        if (!token) {
            window.location.href = '/login.html';
            return;
        }

        // Load user data
        await this.loadUserData();

        // Setup event listeners
        this.setupEventListeners();

        // Load recent transcriptions
        await this.loadRecentTranscriptions();

        // Load stats
        await this.loadStats();
    }

    async loadUserData() {
        try {
            const response = await this.fetchWithAuth(`${API_URL}/auth/me`);
            if (response.ok) {
                this.user = await response.json();
                this.updateUserUI();
            } else {
                throw new Error('Failed to load user');
            }
        } catch (error) {
            console.error('Error loading user:', error);
            // Use placeholder data for demo
            this.user = {
                display_name: 'Demo User',
                username: 'demo',
                avatar_url: null
            };
            this.updateUserUI();
        }
    }

    updateUserUI() {
        const name = this.user.display_name || this.user.username;

        // Update welcome message
        const welcomeName = document.getElementById('welcome-name');
        if (welcomeName) {
            welcomeName.textContent = name.split(' ')[0];
        }

        // Update header
        const userName = document.getElementById('user-name');
        if (userName) {
            userName.textContent = name;
        }

        // Update avatar
        const userAvatar = document.getElementById('user-avatar');
        if (userAvatar) {
            if (this.user.avatar_url) {
                userAvatar.innerHTML = `<img src="${this.user.avatar_url}" alt="${name}">`;
            } else {
                userAvatar.textContent = name.charAt(0).toUpperCase();
            }
        }
    }

    async loadRecentTranscriptions() {
        try {
            const response = await this.fetchWithAuth(`${API_URL}/transcriptions?limit=5`);
            if (response.ok) {
                const data = await response.json();
                this.renderTranscriptions(data.transcriptions);
            }
        } catch (error) {
            console.error('Error loading transcriptions:', error);
        }
    }

    renderTranscriptions(transcriptions) {
        const container = document.getElementById('transcription-list');
        if (!container) return;

        if (transcriptions.length === 0) {
            const emptyTitle = i18n.t('dashboard.empty.title');
            const emptyDesc = i18n.t('dashboard.empty.desc');

            container.innerHTML = `
                <div class="empty-state">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                    </svg>
                    <h3>${emptyTitle}</h3>
                    <p>${emptyDesc}</p>
                </div>
            `;
            return;
        }

        container.innerHTML = transcriptions.map(t => {
            // Transcriptions don't have status field - they're always completed when listed
            const status = t.status || 'completed';
            const statusLabel = i18n.t(`common.status.${status}`) || status;

            return `
            <div class="transcription-item" data-id="${t.id}">
                <div class="transcription-thumb">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    </svg>
                </div>
                <div class="transcription-info">
                    <div class="transcription-title">${this.escapeHtml(t.video_title || 'Untitled')}</div>
                    <div class="transcription-meta">
                        ${t.language.toUpperCase()} • ${this.formatDate(t.created_at)}
                    </div>
                </div>
                <span class="badge badge-${status === 'completed' ? 'success' : 'warning'}">
                    ${statusLabel}
                </span>
            </div>
        `}).join('');
    }

    async loadStats() {
        try {
            const response = await this.fetchWithAuth(`${API_URL}/users/me/stats`);
            if (response.ok) {
                const stats = await response.json();
                this.updateStats(stats);
            }
        } catch (error) {
            console.error('Error loading stats:', error);
            // Use demo stats
            this.updateStats({
                total_videos: 0,
                total_minutes: 0,
                storage_used_mb: 0
            });
        }
    }

    updateStats(stats) {
        const videosStat = document.getElementById('stat-videos');
        const minutesStat = document.getElementById('stat-minutes');
        const remainingStat = document.getElementById('stat-remaining');
        const limitStat = document.getElementById('stat-limit');
        const progressFill = document.getElementById('minutes-progress-fill');

        if (videosStat) videosStat.textContent = stats.total_videos || 0;
        if (minutesStat) minutesStat.textContent = Math.round(stats.total_minutes_processed || 0);

        // Calculate remaining minutes
        const used = stats.monthly_minutes_used || 0;
        const limit = stats.monthly_minutes_limit || 60;
        const remaining = Math.max(0, limit - used);

        if (remainingStat) remainingStat.textContent = remaining;
        if (limitStat) limitStat.textContent = limit;

        // Update progress bar (remaining percentage)
        if (progressFill) {
            const percentage = limit > 0 ? (remaining / limit) * 100 : 0;
            progressFill.style.width = `${percentage}%`;

            // Change color based on remaining
            if (percentage < 20) {
                progressFill.style.background = 'var(--color-error)';
            } else if (percentage < 50) {
                progressFill.style.background = 'var(--color-warning)';
            }
        }
    }

    setupEventListeners() {
        // File upload
        const uploadZone = document.getElementById('upload-zone');
        const fileInput = document.getElementById('file-input');

        if (uploadZone && fileInput) {
            // Click to upload
            uploadZone.addEventListener('click', () => fileInput.click());

            // Drag and drop
            uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadZone.classList.add('dragover');
            });

            uploadZone.addEventListener('dragleave', () => {
                uploadZone.classList.remove('dragover');
            });

            uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadZone.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length) {
                    this.handleFileUpload(files[0]);
                }
            });

            // File input change
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) {
                    this.handleFileUpload(e.target.files[0]);
                }
            });
        }

        // Language selection
        const languageOptions = document.querySelectorAll('.language-option');
        languageOptions.forEach(option => {
            option.addEventListener('click', () => {
                languageOptions.forEach(o => o.classList.remove('active'));
                option.classList.add('active');
                // Ensure the radio input is checked
                const radio = option.querySelector('input[type="radio"]');
                if (radio) radio.checked = true;
            });
        });

        // Logout
        const logoutBtn = document.getElementById('logout-btn');
        const logoutDropdown = document.getElementById('logout-dropdown');

        [logoutBtn, logoutDropdown].forEach(btn => {
            if (btn) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.logout();
                });
            }
        });

        // Upload tabs switching
        const uploadTabs = document.querySelectorAll('.upload-tab');
        const uploadFileContent = document.getElementById('upload-file-content');
        const uploadUrlContent = document.getElementById('upload-url-content');

        uploadTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                uploadTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                if (tab.dataset.uploadTab === 'file') {
                    uploadFileContent?.classList.add('active');
                    uploadUrlContent?.classList.remove('active');
                } else {
                    uploadFileContent?.classList.remove('active');
                    uploadUrlContent?.classList.add('active');
                }
            });
        });

        // URL upload submission
        const submitUrlBtn = document.getElementById('submit-url-btn');
        const urlInput = document.getElementById('video-url-input');

        if (submitUrlBtn && urlInput) {
            submitUrlBtn.addEventListener('click', () => this.handleUrlUpload());
            urlInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.handleUrlUpload();
            });
        }
    }

    async handleUrlUpload() {
        const urlInput = document.getElementById('video-url-input');
        const submitBtn = document.getElementById('submit-url-btn');
        const url = urlInput?.value.trim();

        if (!url) {
            alert(i18n.t('dashboard.upload.url_empty') || 'Please enter a video URL');
            return;
        }

        // Simple URL validation
        if (!url.match(/^https?:\/\/.+/i)) {
            alert(i18n.t('dashboard.upload.url_invalid') || 'Invalid URL format');
            return;
        }

        // Get selected language
        const selectedLang = document.querySelector('input[name="language"]:checked');
        const language = selectedLang ? selectedLang.value : 'en';

        // Show loading state
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = i18n.t('common.loading') || 'Processing...';

        try {
            const response = await this.fetchWithAuth(`${API_URL}/videos/from-url`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, language })
            });

            if (response.ok) {
                const data = await response.json();
                alert(i18n.t('dashboard.upload.url_success') || `Video queued for download! ID: ${data.id}`);
                urlInput.value = '';
                // Refresh transcriptions list
                await this.loadRecentTranscriptions();
            } else {
                const error = await response.json();
                alert(error.detail || i18n.t('common.error') || 'Upload failed');
            }
        } catch (error) {
            console.error('URL upload error:', error);
            alert(i18n.t('common.error') || 'An error occurred');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    }

    async handleFileUpload(file) {
        const validTypes = [
            'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska',
            'video/webm', 'audio/mpeg', 'audio/wav', 'audio/x-m4a'
        ];

        if (!validTypes.includes(file.type) && !file.name.match(/\.(mp4|mov|avi|mkv|webm|mp3|wav|m4a)$/i)) {
            alert(i18n.t('js.alerts.invalid_type'));
            return;
        }

        if (file.size > 1024 * 1024 * 1024) {
            alert(i18n.t('js.alerts.file_too_large'));
            return;
        }

        // Show progress
        const uploadZone = document.getElementById('upload-zone');
        const progressContainer = document.getElementById('upload-progress');
        const filenameEl = document.getElementById('upload-filename');
        const percentEl = document.getElementById('upload-percent');
        const progressFill = document.getElementById('progress-fill');

        uploadZone.classList.add('hidden');
        progressContainer.classList.remove('hidden');
        filenameEl.textContent = file.name;

        // Get selected language
        const selectedLang = document.querySelector('.language-option.active input')?.value || 'en';

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('language', selectedLang);

            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    percentEl.textContent = `${percent}%`;
                    progressFill.style.width = `${percent}%`;
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status === 200 || xhr.status === 201) {
                    alert(i18n.t('js.alerts.upload_success'));
                    this.loadRecentTranscriptions();
                } else {
                    alert(i18n.t('js.alerts.upload_error'));
                }
                this.resetUploadUI();
            });

            xhr.addEventListener('error', () => {
                alert(i18n.t('js.alerts.upload_error'));
                this.resetUploadUI();
            });

            const token = localStorage.getItem('access_token');
            xhr.open('POST', `${API_URL}/videos/upload`);
            xhr.setRequestHeader('Authorization', `Bearer ${token}`);
            xhr.send(formData);

        } catch (error) {
            console.error('Upload error:', error);
            alert(i18n.t('js.alerts.upload_error'));
            this.resetUploadUI();
        }
    }

    resetUploadUI() {
        const uploadZone = document.getElementById('upload-zone');
        const progressContainer = document.getElementById('upload-progress');
        const progressFill = document.getElementById('progress-fill');
        const fileInput = document.getElementById('file-input');

        uploadZone.classList.remove('hidden');
        progressContainer.classList.add('hidden');
        progressFill.style.width = '0%';
        fileInput.value = '';
    }

    async logout() {
        const refreshToken = localStorage.getItem('refresh_token');

        try {
            await this.fetchWithAuth(`${API_URL}/auth/logout`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ refresh_token: refreshToken })
            });
        } catch (error) {
            console.error('Logout error:', error);
        }

        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login.html';
    }

    async fetchWithAuth(url, options = {}) {
        const token = localStorage.getItem('access_token');
        return fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Bearer ${token}`
            }
        });
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return i18n.t('js.time.just_now');
        if (diff < 3600000) return `${Math.floor(diff / 60000)}${i18n.t('js.time.ago_m')}`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}${i18n.t('js.time.ago_h')}`;

        return date.toLocaleDateString();
    }

    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

// Dropdown toggle
function toggleDropdown() {
    const dropdown = document.getElementById('user-dropdown');
    dropdown.classList.toggle('open');
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown && !dropdown.contains(e.target)) {
        dropdown.classList.remove('open');
    }
});

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});
