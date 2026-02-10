/**
 * Consent Dialog - Handles first-run consent and guidance mode settings.
 */

(function() {
    'use strict';

    /**
     * ConsentDialog class for managing consent UI
     */
    class ConsentDialog {
        constructor() {
            this.overlay = null;
            this.onConsentGiven = null;
            this.isVisible = false;
        }

        /**
         * Show the consent dialog
         * @param {Object} options - Dialog options
         * @param {boolean} options.firstRun - Whether this is the first run
         * @param {Function} options.onConsent - Callback when user makes a choice
         */
        show(options = {}) {
            const { firstRun = true, onConsent } = options;
            this.onConsentGiven = onConsent;

            // Get or create overlay
            this.overlay = document.getElementById('consentOverlay');
            if (!this.overlay) {
                this._createOverlay();
            }

            // Update content based on first run status
            this._updateContent(firstRun);

            // Show overlay
            this.overlay.classList.remove('hidden');
            this.isVisible = true;

            // Set up event listeners
            this._setupListeners();
        }

        /**
         * Hide the consent dialog
         */
        hide() {
            if (this.overlay) {
                this.overlay.classList.add('hidden');
            }
            this.isVisible = false;
        }

        /**
         * Create the consent overlay element
         */
        _createOverlay() {
            this.overlay = document.createElement('div');
            this.overlay.id = 'consentOverlay';
            this.overlay.className = 'consent-overlay hidden';

            this.overlay.innerHTML = `
                <div class="consent-card">
                    <div class="consent-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="16" x2="12" y2="12"></line>
                            <line x1="12" y1="8" x2="12.01" y2="8"></line>
                        </svg>
                    </div>
                    <h3 class="consent-title">AI Guidance</h3>
                    <p class="consent-description">
                        Want guided help when you're in the wrong workspace or environment?
                    </p>
                    <p class="consent-subdescription">
                        The tutorial will show you how to navigate to the right place in Fusion 360.
                    </p>
                    <div class="consent-buttons">
                        <button id="consentYes" class="btn btn-primary consent-btn">
                            Yes, help me navigate
                        </button>
                        <button id="consentNo" class="btn btn-secondary consent-btn">
                            No thanks
                        </button>
                    </div>
                    <div class="consent-modes hidden">
                        <p class="consent-modes-label">Choose guidance level:</p>
                        <div class="consent-mode-options">
                            <label class="consent-mode-option">
                                <input type="radio" name="guidanceMode" value="ON">
                                <span class="mode-label">Automatic</span>
                                <span class="mode-description">Guide me without asking</span>
                            </label>
                            <label class="consent-mode-option">
                                <input type="radio" name="guidanceMode" value="ASK" checked>
                                <span class="mode-label">Ask first</span>
                                <span class="mode-description">Ask before showing guidance</span>
                            </label>
                            <label class="consent-mode-option">
                                <input type="radio" name="guidanceMode" value="OFF">
                                <span class="mode-label">Warnings only</span>
                                <span class="mode-description">Just show a warning message</span>
                            </label>
                        </div>
                        <button id="consentSave" class="btn btn-primary consent-btn">
                            Save preferences
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(this.overlay);
        }

        /**
         * Update content based on first run status
         */
        _updateContent(firstRun) {
            const title = this.overlay.querySelector('.consent-title');
            const description = this.overlay.querySelector('.consent-description');
            const buttonsSection = this.overlay.querySelector('.consent-buttons');
            const modesSection = this.overlay.querySelector('.consent-modes');

            if (firstRun) {
                title.textContent = 'AI Guidance';
                description.textContent = 'Want guided help when you\'re in the wrong workspace or environment?';
                buttonsSection.classList.remove('hidden');
                modesSection.classList.add('hidden');
            } else {
                title.textContent = 'Guidance Settings';
                description.textContent = 'How would you like to receive navigation guidance?';
                buttonsSection.classList.add('hidden');
                modesSection.classList.remove('hidden');
            }
        }

        /**
         * Set up event listeners
         */
        _setupListeners() {
            const yesBtn = this.overlay.querySelector('#consentYes');
            const noBtn = this.overlay.querySelector('#consentNo');
            const saveBtn = this.overlay.querySelector('#consentSave');

            if (yesBtn) {
                yesBtn.onclick = () => this._handleConsent('ASK');
            }

            if (noBtn) {
                noBtn.onclick = () => this._handleConsent('OFF');
            }

            if (saveBtn) {
                saveBtn.onclick = () => {
                    const selected = this.overlay.querySelector('input[name="guidanceMode"]:checked');
                    const mode = selected ? selected.value : 'ASK';
                    this._handleConsent(mode);
                };
            }

            // Close on overlay click (outside card)
            this.overlay.onclick = (e) => {
                if (e.target === this.overlay) {
                    // Don't close on first run - force a choice
                    const buttonsSection = this.overlay.querySelector('.consent-buttons');
                    if (buttonsSection.classList.contains('hidden')) {
                        this.hide();
                    }
                }
            };
        }

        /**
         * Handle consent choice
         */
        _handleConsent(mode) {
            this.hide();
            if (this.onConsentGiven) {
                this.onConsentGiven(mode);
            }
        }
    }

    // Create singleton instance
    const consentDialog = new ConsentDialog();

    // Export to window
    window.ConsentDialog = ConsentDialog;
    window.consentDialog = consentDialog;

    /**
     * Show consent dialog - convenience function
     */
    window.showConsentDialog = function(options) {
        consentDialog.show(options);
    };

    /**
     * Hide consent dialog - convenience function
     */
    window.hideConsentDialog = function() {
        consentDialog.hide();
    };

})();
