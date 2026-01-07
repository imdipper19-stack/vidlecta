/**
 * VideoNotes - Authentication & Password Validation JavaScript
 */

// API Base URL
const API_URL = '/api';

// Password blacklist
const PASSWORD_BLACKLIST = [
    'password', 'password123', '123456', '12345678', '123456789',
    'qwerty', 'qwerty123', 'abc123', '111111', '123123',
    'admin', 'admin123', 'letmein', 'welcome', 'monkey',
    'dragon', 'master', 'login', 'princess', 'solo',
    'пароль', 'йцукен', 'привет', 'любовь', 'солнце'
];

// Sequential patterns to check
const SEQUENTIAL_PATTERNS = [
    '1234', '2345', '3456', '4567', '5678', '6789', '7890',
    'abcd', 'bcde', 'cdef', 'defg', 'qwer', 'wert', 'asdf', 'zxcv'
];

/**
 * Password Validator Class
 */
class PasswordValidator {
    static MIN_LENGTH = 8;
    static SPECIAL_CHARS = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`';

    /**
     * Validate password and return detailed results
     */
    static validate(password) {
        const results = {
            isValid: true,
            errors: [],
            requirements: {
                length: password.length >= this.MIN_LENGTH,
                uppercase: /[A-Z]/.test(password),
                lowercase: /[a-z]/.test(password),
                number: /\d/.test(password),
                special: new RegExp(`[${this.escapeRegex(this.SPECIAL_CHARS)}]`).test(password)
            }
        };

        // Check each requirement
        if (!results.requirements.length) {
            results.errors.push(`Password must be at least ${this.MIN_LENGTH} characters`);
            results.isValid = false;
        }

        if (!results.requirements.uppercase) {
            results.errors.push('Password must contain at least one uppercase letter');
            results.isValid = false;
        }

        if (!results.requirements.lowercase) {
            results.errors.push('Password must contain at least one lowercase letter');
            results.isValid = false;
        }

        if (!results.requirements.number) {
            results.errors.push('Password must contain at least one number');
            results.isValid = false;
        }

        if (!results.requirements.special) {
            results.errors.push('Password must contain at least one special character');
            results.isValid = false;
        }

        // Check blacklist
        if (PASSWORD_BLACKLIST.includes(password.toLowerCase())) {
            results.errors.push('This password is too common');
            results.isValid = false;
        }

        // Check sequential patterns
        const lowerPassword = password.toLowerCase();
        for (const pattern of SEQUENTIAL_PATTERNS) {
            if (lowerPassword.includes(pattern)) {
                results.errors.push('Password contains sequential patterns');
                results.isValid = false;
                break;
            }
        }

        // Check consecutive characters
        if (/(.)\1{3,}/.test(password)) {
            results.errors.push('Password contains too many consecutive identical characters');
            results.isValid = false;
        }

        return results;
    }

    /**
     * Calculate password strength score (0-100)
     */
    static getStrengthScore(password) {
        if (!password) return 0;

        let score = 0;

        // Length bonus (up to 30 points)
        score += Math.min(password.length * 2, 30);

        // Character variety (up to 40 points)
        if (/[a-z]/.test(password)) score += 10;
        if (/[A-Z]/.test(password)) score += 10;
        if (/\d/.test(password)) score += 10;
        if (new RegExp(`[${this.escapeRegex(this.SPECIAL_CHARS)}]`).test(password)) score += 10;

        // Bonus for multiple uppercase/special (up to 20 points)
        const upperCount = (password.match(/[A-Z]/g) || []).length;
        const specialCount = (password.match(new RegExp(`[${this.escapeRegex(this.SPECIAL_CHARS)}]`, 'g')) || []).length;
        if (upperCount > 1) score += 10;
        if (specialCount >= 2) score += 10;

        // Penalties
        if (PASSWORD_BLACKLIST.includes(password.toLowerCase())) {
            score = Math.max(0, score - 50);
        }
        if (/(.)\1{2,}/.test(password)) {
            score = Math.max(0, score - 20);
        }

        return Math.min(100, score);
    }

    /**
     * Get strength label from score
     */
    static getStrengthLabel(score) {
        if (score < 30) return 'weak';
        if (score < 50) return 'fair';
        if (score < 70) return 'good';
        if (score < 90) return 'strong';
        return 'excellent';
    }

    static escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
}

/**
 * Form Handler Class
 */
class AuthForm {
    constructor(formId) {
        this.form = document.getElementById(formId);
        if (!this.form) return;

        this.setupEventListeners();
        this.setupPasswordValidation();
        this.setupAvatarUpload();
    }

    setupEventListeners() {
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));

        // Real-time validation for inputs
        const inputs = this.form.querySelectorAll('.form-input');
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearFieldError(input));
        });

        // Password toggle visibility
        const passwordToggle = document.getElementById('password-toggle');
        if (passwordToggle) {
            passwordToggle.addEventListener('click', () => this.togglePasswordVisibility());
        }
    }

    setupPasswordValidation() {
        const passwordInput = document.getElementById('password');
        if (!passwordInput) return;

        passwordInput.addEventListener('input', (e) => {
            this.updatePasswordStrength(e.target.value);
            this.updatePasswordRequirements(e.target.value);
        });

        // Initial state
        this.updatePasswordStrength('');
        this.updatePasswordRequirements('');
    }

    updatePasswordStrength(password) {
        const strengthBar = document.getElementById('password-strength-bar');
        const strengthLabel = document.getElementById('password-strength-label');
        if (!strengthBar || !strengthLabel) return;

        const score = PasswordValidator.getStrengthScore(password);
        const label = PasswordValidator.getStrengthLabel(score);

        // Update bar
        strengthBar.style.width = `${score}%`;
        strengthBar.className = 'password-strength-bar';

        // Set color based on strength
        switch (label) {
            case 'weak':
                strengthBar.style.background = 'var(--color-error)';
                break;
            case 'fair':
                strengthBar.style.background = 'var(--color-warning)';
                break;
            case 'good':
                strengthBar.style.background = 'var(--color-info)';
                break;
            case 'strong':
            case 'excellent':
                strengthBar.style.background = 'var(--color-success)';
                break;
        }

        // Update label
        if (password) {
            const labels = {
                'weak': 'Weak password',
                'fair': 'Fair password',
                'good': 'Good password',
                'strong': 'Strong password',
                'excellent': 'Excellent password!'
            };
            strengthLabel.textContent = labels[label];
            strengthLabel.className = `password-strength-label ${label}`;
        } else {
            strengthLabel.textContent = '';
        }
    }

    updatePasswordRequirements(password) {
        const validation = PasswordValidator.validate(password);

        const requirements = [
            { id: 'req-length', valid: validation.requirements.length },
            { id: 'req-uppercase', valid: validation.requirements.uppercase },
            { id: 'req-lowercase', valid: validation.requirements.lowercase },
            { id: 'req-number', valid: validation.requirements.number },
            { id: 'req-special', valid: validation.requirements.special }
        ];

        requirements.forEach(req => {
            const element = document.getElementById(req.id);
            if (element) {
                element.classList.remove('valid', 'invalid');
                if (password) {
                    element.classList.add(req.valid ? 'valid' : 'invalid');
                }
            }
        });
    }

    togglePasswordVisibility() {
        const passwordInput = document.getElementById('password');
        const eyeIcon = document.getElementById('eye-icon');
        const eyeOffIcon = document.getElementById('eye-off-icon');

        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            eyeIcon.classList.add('hidden');
            eyeOffIcon.classList.remove('hidden');
        } else {
            passwordInput.type = 'password';
            eyeIcon.classList.remove('hidden');
            eyeOffIcon.classList.add('hidden');
        }
    }

    setupAvatarUpload() {
        const avatarInput = document.getElementById('avatar-input');
        const avatarPreview = document.getElementById('avatar-preview');
        if (!avatarInput || !avatarPreview) return;

        avatarInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                // Validate file type
                if (!file.type.startsWith('image/')) {
                    this.showError('Please select an image file');
                    return;
                }

                // Validate file size (5MB)
                if (file.size > 5 * 1024 * 1024) {
                    this.showError('Image must be less than 5MB');
                    return;
                }

                // Preview image
                const reader = new FileReader();
                reader.onload = (e) => {
                    avatarPreview.innerHTML = `<img src="${e.target.result}" alt="Avatar preview">`;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    validateField(input) {
        const name = input.name;
        const value = input.value.trim();
        let error = '';

        switch (name) {
            case 'email':
                if (!value) {
                    error = 'Email is required';
                } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
                    error = 'Please enter a valid email address';
                }
                break;

            case 'username':
                if (!value) {
                    error = 'Username is required';
                } else if (!/^[a-zA-Z0-9_]{3,30}$/.test(value)) {
                    error = 'Username must be 3-30 characters, letters, numbers, underscores only';
                } else if (/^\d+$/.test(value)) {
                    error = 'Username cannot be all numbers';
                } else if (value.startsWith('_')) {
                    error = 'Username cannot start with underscore';
                }
                break;

            case 'password':
                const validation = PasswordValidator.validate(value);
                if (!validation.isValid) {
                    error = validation.errors[0];
                }
                break;

            case 'password_confirm':
                const password = document.getElementById('password')?.value;
                if (value !== password) {
                    error = 'Passwords do not match';
                }
                break;
        }

        if (error) {
            this.showFieldError(input, error);
            return false;
        } else {
            this.clearFieldError(input);
            input.classList.add('valid');
            return true;
        }
    }

    showFieldError(input, message) {
        const errorElement = document.getElementById(`${input.name}-error`);
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.classList.remove('hidden');
        }
        input.classList.add('invalid');
        input.classList.remove('valid');
    }

    clearFieldError(input) {
        const errorElement = document.getElementById(`${input.name}-error`);
        if (errorElement) {
            errorElement.classList.add('hidden');
        }
        input.classList.remove('invalid');
    }

    showError(message) {
        const errorAlert = document.getElementById('error-alert');
        const errorMessage = document.getElementById('error-message');
        if (errorAlert && errorMessage) {
            errorMessage.textContent = message;
            errorAlert.classList.remove('hidden');
        }
    }

    hideError() {
        const errorAlert = document.getElementById('error-alert');
        if (errorAlert) {
            errorAlert.classList.add('hidden');
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        this.hideError();

        // Validate all required fields
        const requiredInputs = this.form.querySelectorAll('.form-input[required]');
        let isValid = true;

        requiredInputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });

        // Check terms checkbox
        const termsCheckbox = document.getElementById('terms');
        if (termsCheckbox && !termsCheckbox.checked) {
            this.showFieldError(termsCheckbox, 'You must agree to the Terms of Service');
            isValid = false;
        }

        if (!isValid) return;

        // Show loading state
        const submitBtn = document.getElementById('submit-btn');
        const submitText = document.getElementById('submit-text');
        const submitSpinner = document.getElementById('submit-spinner');

        submitBtn.disabled = true;
        submitText.textContent = 'Creating account...';
        submitSpinner.classList.remove('hidden');

        try {
            // Collect form data
            const formData = {
                email: document.getElementById('email').value.trim(),
                username: document.getElementById('username').value.trim(),
                display_name: document.getElementById('display_name')?.value.trim() || null,
                password: document.getElementById('password').value,
                password_confirm: document.getElementById('password_confirm').value
            };

            // Send registration request
            const response = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail?.message || data.detail || 'Registration failed');
            }

            // Success! Redirect to login or dashboard
            window.location.href = '/login.html?registered=true';

        } catch (error) {
            this.showError(error.message);
        } finally {
            submitBtn.disabled = false;
            submitText.textContent = 'Create Account';
            submitSpinner.classList.add('hidden');
        }
    }
}

/**
 * Login Form Handler
 */
class LoginForm {
    constructor(formId) {
        this.form = document.getElementById(formId);
        if (!this.form) return;

        this.setupEventListeners();
    }

    setupEventListeners() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));

        // Password toggle
        const passwordToggle = document.getElementById('password-toggle');
        if (passwordToggle) {
            passwordToggle.addEventListener('click', () => {
                const passwordInput = document.getElementById('password');
                const eyeIcon = document.getElementById('eye-icon');
                const eyeOffIcon = document.getElementById('eye-off-icon');

                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    eyeIcon?.classList.add('hidden');
                    eyeOffIcon?.classList.remove('hidden');
                } else {
                    passwordInput.type = 'password';
                    eyeIcon?.classList.remove('hidden');
                    eyeOffIcon?.classList.add('hidden');
                }
            });
        }
    }

    showError(message) {
        const errorAlert = document.getElementById('error-alert');
        const errorMessage = document.getElementById('error-message');
        if (errorAlert && errorMessage) {
            errorMessage.textContent = message;
            errorAlert.classList.remove('hidden');
        }
    }

    async handleSubmit(e) {
        e.preventDefault();

        const submitBtn = document.getElementById('submit-btn');
        const submitText = document.getElementById('submit-text');
        const submitSpinner = document.getElementById('submit-spinner');

        submitBtn.disabled = true;
        submitText.textContent = 'Signing in...';
        submitSpinner?.classList.remove('hidden');

        try {
            const formData = {
                email: document.getElementById('email').value.trim(),
                password: document.getElementById('password').value,
                remember_me: document.getElementById('remember_me')?.checked || false
            };

            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Login failed');
            }

            // Store tokens
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);

            // Redirect to dashboard
            window.location.href = '/dashboard.html';

        } catch (error) {
            this.showError(error.message);
        } finally {
            submitBtn.disabled = false;
            submitText.textContent = 'Sign In';
            submitSpinner?.classList.add('hidden');
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Check which form is on the page
    if (document.getElementById('register-form')) {
        new AuthForm('register-form');
    }

    if (document.getElementById('login-form')) {
        new LoginForm('login-form');
    }

    // Show success message if just registered
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('registered') === 'true') {
        const successMessage = document.createElement('div');
        successMessage.className = 'alert alert-success';
        successMessage.innerHTML = 'Account created successfully! Please sign in.';
        const form = document.querySelector('.auth-form');
        if (form) {
            form.parentNode.insertBefore(successMessage, form);
        }
    }
});

// Export for use in other scripts
window.PasswordValidator = PasswordValidator;
