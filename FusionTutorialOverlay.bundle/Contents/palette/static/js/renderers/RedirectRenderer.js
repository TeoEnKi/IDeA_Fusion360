/**
 * RedirectRenderer - Renders redirect guidance steps.
 * Shows context indicators, reference images, and navigation instructions.
 */

class RedirectRenderer extends BaseRenderer {
    constructor(container) {
        super(container);
        this.redirectCard = null;
        this.animationRunner = null;
        this.onSkip = null;
        this.isResolved = false;
    }

    /**
     * Render a redirect step
     * @param {Object} step - The redirect step data
     */
    render(step) {
        this.currentStep = step;
        this.isResolved = false;

        // Hide normal tutorial content
        this._hideNormalContent();

        // Show and populate redirect card
        this._showRedirectCard(step);

        // Start animations if available
        if (step.uiAnimations && step.uiAnimations.length > 0) {
            this._runAnimations(step.uiAnimations);
        }
    }

    /**
     * Hide normal tutorial content sections
     */
    _hideNormalContent() {
        const tutorialContent = document.getElementById('tutorialContent');
        if (tutorialContent) {
            tutorialContent.classList.add('hidden');
        }
    }

    /**
     * Show normal tutorial content
     */
    _showNormalContent() {
        const tutorialContent = document.getElementById('tutorialContent');
        if (tutorialContent) {
            tutorialContent.classList.remove('hidden');
        }
    }

    /**
     * Show and populate the redirect card
     * @param {Object} step - The redirect step data
     */
    _showRedirectCard(step) {
        this.redirectCard = document.getElementById('redirectCard');
        if (!this.redirectCard) {
            console.error('Redirect card element not found');
            return;
        }

        // Remove resolved state if present
        this.redirectCard.classList.remove('resolved');

        // Update title
        const titleEl = this.redirectCard.querySelector('.redirect-title');
        if (titleEl) {
            titleEl.textContent = step.title || 'Navigate to Correct Location';
        }

        // Update context indicators
        this._updateContextIndicators(step);

        // Update reference image
        this._updateReferenceImage(step);

        // Update instruction
        const instructionEl = this.redirectCard.querySelector('.redirect-instruction');
        if (instructionEl) {
            instructionEl.textContent = step.instruction || 'Please navigate to the required location.';
        }

        // Setup skip button
        this._setupSkipButton();

        // Show the card
        this.redirectCard.classList.remove('hidden');
    }

    /**
     * Update context indicators (current vs required)
     * @param {Object} step - The redirect step data
     */
    _updateContextIndicators(step) {
        const currentContext = step.currentContext || {};
        const requiredContext = step.requiredContext || {};

        // Update current context display
        const currentValueEl = document.getElementById('currentContext');
        if (currentValueEl) {
            currentValueEl.textContent = currentContext.value || 'Unknown';
        }

        // Update required context display
        const requiredValueEl = document.getElementById('requiredContext');
        if (requiredValueEl) {
            requiredValueEl.textContent = requiredContext.value || 'Unknown';
        }
    }

    /**
     * Update reference image
     * @param {Object} step - The redirect step data
     */
    _updateReferenceImage(step) {
        const imageArea = document.getElementById('referenceImageArea');
        const imageEl = document.getElementById('redirectImage');

        if (!imageArea || !imageEl) return;

        if (step.referenceImage) {
            // Check if we have this image as a data URL in assets
            const imageName = step.referenceImage.replace('.png', '').replace('.jpg', '');
            const assetKey = 'redirect_' + imageName;

            if (window.loadedAssets && window.loadedAssets[assetKey]) {
                imageEl.src = window.loadedAssets[assetKey];
                imageEl.style.display = 'block';
            } else {
                // Try to load from relative path (fallback)
                imageEl.src = '../assets/redirect/' + step.referenceImage;
                imageEl.style.display = 'block';

                // Handle load error
                imageEl.onerror = () => {
                    imageEl.style.display = 'none';
                };
            }
        } else {
            imageEl.style.display = 'none';
        }
    }

    /**
     * Setup skip button event handler
     */
    _setupSkipButton() {
        const skipBtn = document.getElementById('skipRedirectBtn');
        if (skipBtn) {
            skipBtn.onclick = () => {
                if (this.onSkip) {
                    this.onSkip();
                } else {
                    // Default behavior: hide redirect and show warning
                    this.hide();
                }
            };
        }
    }

    /**
     * Run UI animations
     * @param {Array} animations - Array of animation objects
     */
    _runAnimations(animations) {
        // Get animation area within redirect card or create one
        let animArea = this.redirectCard.querySelector('.redirect-animation-area');

        if (!animArea) {
            // Use the reference image area for animations
            animArea = document.getElementById('referenceImageArea');
        }

        if (!animArea) return;

        // Use AnimatedRenderer's animation logic if available
        if (window.AnimatedRenderer && this.animationRunner) {
            this.animationRunner.runAnimationSequence(animations, animArea);
        } else {
            // Simple fallback - just log
            console.log('Would run animations:', animations);
        }
    }

    /**
     * Show context resolved state with success animation
     * @param {Object} resolvedContext - The new context after resolution
     */
    showContextResolved(resolvedContext) {
        this.isResolved = true;

        if (!this.redirectCard) return;

        // Add resolved class for animation
        this.redirectCard.classList.add('resolved');

        // Update current context to show it now matches
        const currentValueEl = document.getElementById('currentContext');
        if (currentValueEl && resolvedContext) {
            currentValueEl.textContent = resolvedContext.environment || resolvedContext.workspace || 'Resolved';
        }

        // Update instruction to show success
        const instructionEl = this.redirectCard.querySelector('.redirect-instruction');
        if (instructionEl) {
            instructionEl.innerHTML = '<span class="context-resolved-message">Context matched! Continuing to tutorial step...</span>';
        }

        // Hide skip button
        const skipBtn = document.getElementById('skipRedirectBtn');
        if (skipBtn) {
            skipBtn.style.display = 'none';
        }
    }

    /**
     * Hide the redirect card and restore normal content
     */
    hide() {
        if (this.redirectCard) {
            this.redirectCard.classList.add('hidden');
        }
        this._showNormalContent();
    }

    /**
     * Replay animations
     */
    replay() {
        if (this.currentStep && this.currentStep.uiAnimations) {
            this._runAnimations(this.currentStep.uiAnimations);
        }
    }

    /**
     * Set callback for skip button
     * @param {Function} callback - Function to call when skip is clicked
     */
    setOnSkip(callback) {
        this.onSkip = callback;
    }

    /**
     * Check if currently showing a redirect
     * @returns {boolean}
     */
    isShowingRedirect() {
        return this.redirectCard && !this.redirectCard.classList.contains('hidden');
    }

    /**
     * Clean up renderer resources
     */
    cleanup() {
        super.cleanup();
        this.hide();
        this.isResolved = false;
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.RedirectRenderer = RedirectRenderer;
}
