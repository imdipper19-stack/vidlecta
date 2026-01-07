/**
 * VidLecta - Internationalization (i18n) System
 * Supports English and Russian languages
 */

class I18n {
    constructor() {
        this.translations = {};
        this.currentLang = 'en';
        this.supportedLangs = ['en', 'ru'];
        this.loaded = false;
    }

    /**
     * Initialize i18n system
     */
    async init() {
        // Get saved language or detect from browser
        this.currentLang = this.getSavedLanguage() || this.detectLanguage();

        // Load translations
        await this.loadTranslations(this.currentLang);

        // Apply translations to page
        this.translatePage();

        // Setup language switcher
        this.setupLanguageSwitcher();

        this.loaded = true;

        // Dispatch event when ready
        window.dispatchEvent(new CustomEvent('i18n:ready', { detail: { lang: this.currentLang } }));
    }

    /**
     * Detect browser language
     */
    detectLanguage() {
        const browserLang = navigator.language || navigator.userLanguage;
        const lang = browserLang.split('-')[0];
        return this.supportedLangs.includes(lang) ? lang : 'en';
    }

    /**
     * Get saved language preference
     */
    getSavedLanguage() {
        return localStorage.getItem('vidlecta_lang');
    }

    /**
     * Save language preference
     */
    saveLanguage(lang) {
        localStorage.setItem('vidlecta_lang', lang);
    }

    /**
     * Load translation file
     */
    async loadTranslations(lang) {
        try {
            const response = await fetch(`/i18n/${lang}.json`);
            if (!response.ok) throw new Error(`Failed to load ${lang} translations`);
            this.translations = await response.json();
        } catch (error) {
            console.error('Error loading translations:', error);
            // Fallback to English
            if (lang !== 'en') {
                await this.loadTranslations('en');
            }
        }
    }

    /**
     * Get translation by key path (e.g., "nav.login")
     */
    t(keyPath, replacements = {}) {
        const keys = keyPath.split('.');
        let value = this.translations;

        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                console.warn(`Translation missing: ${keyPath}`);
                return keyPath;
            }
        }

        if (typeof value !== 'string') {
            return keyPath;
        }

        // Replace placeholders {{key}}
        return value.replace(/\{\{(\w+)\}\}/g, (match, key) => {
            return replacements[key] !== undefined ? replacements[key] : match;
        });
    }

    /**
     * Translate all elements with data-i18n attribute
     */
    translatePage() {
        // Translate text content
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translation = this.t(key);

            // Check if contains HTML (like <span>)
            if (translation.includes('<')) {
                el.innerHTML = translation;
            } else {
                el.textContent = translation;
            }
        });

        // Translate placeholders
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = this.t(key);
        });

        // Translate titles/aria-labels
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            el.title = this.t(key);
            el.setAttribute('aria-label', this.t(key));
        });

        // Update HTML lang attribute
        document.documentElement.lang = this.currentLang;

        // Update meta tags
        this.updateMetaTags();
    }

    /**
     * Update page meta tags for current language
     */
    updateMetaTags() {
        const meta = this.translations.meta;
        if (!meta) return;

        // Title
        if (meta.title) {
            document.title = meta.title;
        }

        // Description
        const descMeta = document.querySelector('meta[name="description"]');
        if (descMeta && meta.description) {
            descMeta.content = meta.description;
        }

        // Keywords
        const keywordsMeta = document.querySelector('meta[name="keywords"]');
        if (keywordsMeta && meta.keywords) {
            keywordsMeta.content = meta.keywords;
        }

        // OG tags
        const ogTitle = document.querySelector('meta[property="og:title"]');
        if (ogTitle && meta.title) {
            ogTitle.content = meta.title.split(' — ')[0];
        }

        const ogDesc = document.querySelector('meta[property="og:description"]');
        if (ogDesc && meta.description) {
            ogDesc.content = meta.description;
        }
    }

    /**
     * Switch language
     */
    async switchLanguage(lang) {
        if (!this.supportedLangs.includes(lang)) {
            console.error(`Unsupported language: ${lang}`);
            return;
        }

        this.currentLang = lang;
        this.saveLanguage(lang);
        await this.loadTranslations(lang);
        this.translatePage();

        // Dispatch language change event
        window.dispatchEvent(new CustomEvent('i18n:changed', { detail: { lang } }));
    }

    /**
     * Setup language switcher elements
     */
    setupLanguageSwitcher() {
        // Handle language toggle buttons
        document.querySelectorAll('[data-lang-switch]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const lang = btn.getAttribute('data-lang-switch');
                this.switchLanguage(lang);
                this.updateActiveLangButton();
            });
        });

        // Handle select dropdowns
        document.querySelectorAll('[data-lang-select]').forEach(select => {
            select.value = this.currentLang;
            select.addEventListener('change', (e) => {
                this.switchLanguage(e.target.value);
            });
        });

        // Update active state
        this.updateActiveLangButton();
    }

    /**
     * Update active language button state
     */
    updateActiveLangButton() {
        document.querySelectorAll('[data-lang-switch]').forEach(btn => {
            const lang = btn.getAttribute('data-lang-switch');
            btn.classList.toggle('active', lang === this.currentLang);
        });
    }

    /**
     * Get current language
     */
    getCurrentLang() {
        return this.currentLang;
    }

    /**
     * Check if RTL language (for future support)
     */
    isRTL() {
        return false; // Russian and English are LTR
    }
}

// Create global instance
const i18n = new I18n();

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    i18n.init();
});

// Export for use in other scripts
window.i18n = i18n;
