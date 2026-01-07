/**
 * VideoNotes - Settings Page JavaScript
 */

const API_URL = '/api';

class SettingsPage {
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
        this.setupTabs();
        this.setupForms();
        this.setupAvatarUpload();
        this.setupPasswordValidation();
        this.setupPreferences();
    }

    async loadUserData() {
        try {
            const response = await this.fetchWithAuth(`${API_URL}/users/me`);
            if (response.ok) {
                this.user = await response.json();
                this.populateForm();
            }
        } catch (error) {
            console.error('Error loading user:', error);
            // Demo data
            this.user = {
                display_name: 'Demo User',
                username: 'demo',
                email: 'demo@example.com',
                bio: '',
                avatar_url: null,
                email_verified: true,
                preferred_language: 'en',
                theme: 'dark',
                email_notifications: true
            };
            this.populateForm();
        }
    }

    populateForm() {
        // Profile
        document.getElementById('display_name').value = this.user.display_name || '';
        document.getElementById('username').value = this.user.username || '';
        document.getElementById('bio').value = this.user.bio || '';

        // Avatar
        const avatar = document.getElementById('settings-avatar');
        if (this.user.avatar_url) {
            avatar.innerHTML = `<img src="${this.user.avatar_url}" alt="Avatar">`;
        } else {
            avatar.textContent = (this.user.display_name || this.user.username || 'U').charAt(0).toUpperCase();
        }

        // Account
        document.getElementById('current_email').value = this.user.email || '';
        const verifiedBadge = document.getElementById('email-verified-badge');
        if (this.user.email_verified) {
            verifiedBadge.textContent = 'Verified';
            verifiedBadge.className = 'badge badge-success';
        } else {
            verifiedBadge.textContent = 'Unverified';
            verifiedBadge.className = 'badge badge-warning';
        }

        // Preferences
        document.getElementById('language-select').value = this.user.preferred_language || 'en';
        document.getElementById('email-notifications').checked = this.user.email_notifications !== false;

        // Theme
        const themeOptions = document.querySelectorAll('.theme-option');
        themeOptions.forEach(option => {
            option.classList.toggle('active', option.dataset.theme === (this.user.theme || 'dark'));
        });
    }

    setupTabs() {
        const tabs = document.querySelectorAll('.tab');
        const contents = document.querySelectorAll('.tab-content');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                // Update tabs
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Update content
                contents.forEach(c => c.classList.remove('active'));
                const targetId = `tab-${tab.dataset.tab}`;
                document.getElementById(targetId)?.classList.add('active');
            });
        });
    }

    setupForms() {
        // Profile form
        document.getElementById('profile-form')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.updateProfile();
        });

        // Email form
        document.getElementById('email-form')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.updateEmail();
        });

        // Password form
        document.getElementById('password-form')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.updatePassword();
        });

        // Logout
        document.getElementById('logout-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.logout();
        });
    }

    setupAvatarUpload() {
        const avatarInput = document.getElementById('avatar-input');
        const removeBtn = document.getElementById('remove-avatar-btn');

        avatarInput?.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (file) {
                await this.uploadAvatar(file);
            }
        });

        removeBtn?.addEventListener('click', async () => {
            await this.removeAvatar();
        });
    }

    setupPasswordValidation() {
        const passwordInput = document.getElementById('new_password');
        if (!passwordInput) return;

        passwordInput.addEventListener('input', (e) => {
            const password = e.target.value;
            const strengthBar = document.getElementById('password-strength-bar');
            const strengthLabel = document.getElementById('password-strength-label');

            if (window.PasswordValidator) {
                const score = PasswordValidator.getStrengthScore(password);
                const label = PasswordValidator.getStrengthLabel(score);

                strengthBar.style.width = `${score}%`;

                const colors = {
                    'weak': 'var(--color-error)',
                    'fair': 'var(--color-warning)',
                    'good': 'var(--color-info)',
                    'strong': 'var(--color-success)',
                    'excellent': 'var(--color-success)'
                };
                strengthBar.style.background = colors[label];

                const labels = {
                    'weak': 'Weak password',
                    'fair': 'Fair password',
                    'good': 'Good password',
                    'strong': 'Strong password',
                    'excellent': 'Excellent password!'
                };
                strengthLabel.textContent = password ? labels[label] : '';
                strengthLabel.className = `password-strength-label ${label}`;
            }
        });
    }

    setupPreferences() {
        // Theme options
        const themeOptions = document.querySelectorAll('.theme-option');
        themeOptions.forEach(option => {
            option.addEventListener('click', () => {
                themeOptions.forEach(o => o.classList.remove('active'));
                option.classList.add('active');
            });
        });

        // Save preferences button
        document.getElementById('save-preferences')?.addEventListener('click', async () => {
            await this.savePreferences();
        });
    }

    async updateProfile() {
        const data = {
            display_name: document.getElementById('display_name').value,
            username: document.getElementById('username').value,
            bio: document.getElementById('bio').value
        };

        try {
            const response = await this.fetchWithAuth(`${API_URL}/users/me`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                this.showSuccess('Profile updated successfully!');
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to update profile');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    async updateEmail() {
        const newEmail = document.getElementById('new_email').value;
        const password = document.getElementById('email_password').value;

        if (!newEmail || !password) {
            this.showError('Please fill in all fields');
            return;
        }

        try {
            const response = await this.fetchWithAuth(`${API_URL}/users/me/email`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_email: newEmail, password: password })
            });

            if (response.ok) {
                this.showSuccess('Email updated! Please verify your new email address.');
                document.getElementById('current_email').value = newEmail;
                document.getElementById('new_email').value = '';
                document.getElementById('email_password').value = '';
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to update email');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    async updatePassword() {
        const currentPassword = document.getElementById('current_password').value;
        const newPassword = document.getElementById('new_password').value;
        const confirmPassword = document.getElementById('confirm_new_password').value;

        if (!currentPassword || !newPassword || !confirmPassword) {
            this.showError('Please fill in all password fields');
            return;
        }

        if (newPassword !== confirmPassword) {
            this.showError('New passwords do not match');
            return;
        }

        // Validate password strength
        if (window.PasswordValidator) {
            const validation = PasswordValidator.validate(newPassword);
            if (!validation.isValid) {
                this.showError(validation.errors[0]);
                return;
            }
        }

        try {
            const response = await this.fetchWithAuth(`${API_URL}/users/me/password`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword,
                    new_password_confirm: confirmPassword
                })
            });

            if (response.ok) {
                this.showSuccess('Password updated successfully!');
                document.getElementById('current_password').value = '';
                document.getElementById('new_password').value = '';
                document.getElementById('confirm_new_password').value = '';
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to update password');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    async uploadAvatar(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await this.fetchWithAuth(`${API_URL}/users/me/avatar`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                // Preview the uploaded image
                const reader = new FileReader();
                reader.onload = (e) => {
                    const avatar = document.getElementById('settings-avatar');
                    avatar.innerHTML = `<img src="${e.target.result}" alt="Avatar">`;
                };
                reader.readAsDataURL(file);
                this.showSuccess('Avatar updated!');
            } else {
                throw new Error('Failed to upload avatar');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    async removeAvatar() {
        try {
            const response = await this.fetchWithAuth(`${API_URL}/users/me/avatar`, {
                method: 'DELETE'
            });

            if (response.ok) {
                const avatar = document.getElementById('settings-avatar');
                avatar.innerHTML = '';
                avatar.textContent = (this.user.display_name || 'U').charAt(0).toUpperCase();
                this.showSuccess('Avatar removed!');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    async savePreferences() {
        const language = document.getElementById('language-select').value;
        const theme = document.querySelector('.theme-option.active')?.dataset.theme || 'dark';
        const emailNotifications = document.getElementById('email-notifications').checked;

        try {
            const response = await this.fetchWithAuth(`${API_URL}/users/me`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    preferred_language: language,
                    theme: theme,
                    email_notifications: emailNotifications
                })
            });

            if (response.ok) {
                this.showSuccess('Preferences saved!');
            } else {
                throw new Error('Failed to save preferences');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    async logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login.html';
    }

    async fetchWithAuth(url, options = {}) {
        const token = localStorage.getItem('access_token');
        const headers = options.headers || {};

        if (!(options.body instanceof FormData)) {
            headers['Content-Type'] = headers['Content-Type'] || 'application/json';
        }

        return fetch(url, {
            ...options,
            headers: {
                ...headers,
                'Authorization': `Bearer ${token}`
            }
        });
    }

    showSuccess(message) {
        const alert = document.getElementById('success-alert');
        const messageEl = document.getElementById('success-message');
        alert.classList.remove('hidden');
        messageEl.textContent = message;

        document.getElementById('error-alert').classList.add('hidden');

        setTimeout(() => alert.classList.add('hidden'), 5000);
    }

    showError(message) {
        const alert = document.getElementById('error-alert');
        const messageEl = document.getElementById('error-message');
        alert.classList.remove('hidden');
        messageEl.textContent = message;

        document.getElementById('success-alert').classList.add('hidden');

        setTimeout(() => alert.classList.add('hidden'), 5000);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    new SettingsPage();
});
