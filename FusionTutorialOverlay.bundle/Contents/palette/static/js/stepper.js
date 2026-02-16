/**
 * Stepper - Manages step navigation and state
 */

class Stepper {
    constructor(options = {}) {
        this.currentIndex = 0;
        this.totalSteps = 0;
        this.tutorialTitle = '';
        this.onStepChange = options.onStepChange || null;
        this.renderer = null;
        this.redirectRenderer = null;
        this.isRedirecting = false;
        this.pendingStepIndex = null;
    }

    /**
     * Set the renderer to use
     * @param {BaseRenderer} renderer - The renderer instance
     */
    setRenderer(renderer) {
        this.renderer = renderer;
    }

    /**
     * Set the redirect renderer
     * @param {RedirectRenderer} renderer - The redirect renderer instance
     */
    setRedirectRenderer(renderer) {
        this.redirectRenderer = renderer;

        // Set up skip callback
        if (renderer) {
            renderer.setOnSkip(() => {
                this.exitRedirectMode();
                // Notify bridge that redirect was skipped
                if (this.onStepChange) {
                    this.onStepChange('skipRedirect');
                }
            });
        }
    }

    /**
     * Enter redirect mode
     * @param {Object} redirectStep - The redirect step data
     * @param {number} pendingIndex - The step index that will be loaded after redirect completes
     */
    enterRedirectMode(redirectStep, pendingIndex) {
        this.isRedirecting = true;
        this.pendingStepIndex = pendingIndex;

        // Add redirect mode class to navigation
        const nav = document.getElementById('navigation');
        if (nav) {
            nav.classList.add('redirect-mode');
        }

        // Render redirect step
        if (this.redirectRenderer) {
            this.redirectRenderer.render(redirectStep);
        }

        // Update navigation buttons
        this.updateNavigation();
    }

    /**
     * Exit redirect mode
     * @param {boolean} resolved - Whether the context was resolved
     */
    exitRedirectMode(resolved = false) {
        this.isRedirecting = false;

        // Remove redirect mode class
        const nav = document.getElementById('navigation');
        if (nav) {
            nav.classList.remove('redirect-mode');
        }

        // Hide redirect card
        if (this.redirectRenderer) {
            this.redirectRenderer.hide();
        }

        // Update navigation buttons
        this.updateNavigation();

        return this.pendingStepIndex;
    }

    /**
     * Called when context is resolved during redirect
     * @param {Object} resolvedContext - The new context
     */
    onContextResolved(resolvedContext) {
        if (!this.isRedirecting) return;

        // Show resolved animation
        if (this.redirectRenderer) {
            this.redirectRenderer.showContextResolved(resolvedContext);
        }
    }

    /**
     * Load a step from data
     * @param {Object} stepData - The step data from the bridge
     */
    loadStep(stepData) {
        this.currentIndex = stepData.currentIndex || 0;
        this.totalSteps = stepData.totalSteps || 1;
        this.tutorialTitle = stepData.tutorialTitle || 'Tutorial';

        // Update progress UI
        this.updateProgress();

        // Render the step
        if (this.renderer) {
            this.renderer.render(stepData);
        }

        // Update navigation buttons
        this.updateNavigation();
    }

    /**
     * Update progress bar and counter
     */
    updateProgress() {
        const tutorialTitle = document.getElementById('tutorialTitle');
        const progressFill = document.getElementById('progressFill');
        const stepCounter = document.getElementById('stepCounter');

        if (tutorialTitle) {
            tutorialTitle.textContent = this.tutorialTitle;
        }

        if (progressFill) {
            const progress = this.totalSteps > 0
                ? ((this.currentIndex + 1) / this.totalSteps) * 100
                : 0;
            progressFill.style.width = `${progress}%`;
        }

        if (stepCounter) {
            stepCounter.textContent = `Step ${this.currentIndex + 1} of ${this.totalSteps}`;
        }

        // Update step dots if visible
        this.updateStepDots();
    }

    /**
     * Update step dots navigation
     */
    updateStepDots() {
        const stepDots = document.getElementById('stepDots');
        if (!stepDots) return;

        // Create dots if needed
        if (stepDots.children.length !== this.totalSteps) {
            stepDots.innerHTML = '';
            for (let i = 0; i < this.totalSteps; i++) {
                const dot = document.createElement('div');
                dot.className = 'step-dot';
                dot.dataset.index = i;
                dot.addEventListener('click', () => this.goToStep(i));
                stepDots.appendChild(dot);
            }
        }

        // Update active state
        Array.from(stepDots.children).forEach((dot, i) => {
            dot.classList.remove('active', 'completed');
            if (i === this.currentIndex) {
                dot.classList.add('active');
            } else if (i < this.currentIndex) {
                dot.classList.add('completed');
            }
        });
    }

    /**
     * Update navigation button states
     */
    updateNavigation() {
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');

        if (prevBtn) {
            // Disable prev during redirect mode
            prevBtn.disabled = this.currentIndex <= 0 || this.isRedirecting;
        }

        if (nextBtn) {
            const isLast = this.currentIndex >= this.totalSteps - 1;
            // Disable next during redirect mode
            nextBtn.disabled = isLast || this.isRedirecting;

            // Update button text for last step
            const textSpan = nextBtn.querySelector('span:not(.btn-icon)');
            if (textSpan) {
                textSpan.textContent = isLast ? 'Done' : 'Next';
            }
        }

    }

    /**
     * Go to next step
     */
    next() {
        // Block navigation during redirect
        if (this.isRedirecting) {
            console.log('Navigation blocked during redirect');
            return;
        }

        if (this.currentIndex < this.totalSteps - 1) {
            if (this.onStepChange) {
                this.onStepChange('next');
            }
        }
    }

    /**
     * Go to previous step
     */
    prev() {
        // Block navigation during redirect
        if (this.isRedirecting) {
            console.log('Navigation blocked during redirect');
            return;
        }

        if (this.currentIndex > 0) {
            if (this.onStepChange) {
                this.onStepChange('prev');
            }
        }
    }

    /**
     * Go to a specific step
     * @param {number} index - The step index
     */
    goToStep(index) {
        // Block navigation during redirect
        if (this.isRedirecting) {
            console.log('Navigation blocked during redirect');
            return;
        }

        if (index >= 0 && index < this.totalSteps && index !== this.currentIndex) {
            if (this.onStepChange) {
                this.onStepChange('goToStep', index);
            }
        }
    }

    /**
     * Replay current step animations
     */
    replay() {
        // If in redirect mode, replay redirect animations
        if (this.isRedirecting && this.redirectRenderer) {
            this.redirectRenderer.replay();
            return;
        }

        // Otherwise replay normal step animations
        if (this.renderer && typeof this.renderer.replay === 'function') {
            this.renderer.replay();
        }
    }

    /**
     * Check if currently in redirect mode
     * @returns {boolean}
     */
    isInRedirectMode() {
        return this.isRedirecting;
    }

    /**
     * Get the pending step index (to be loaded after redirect)
     * @returns {number|null}
     */
    getPendingStepIndex() {
        return this.pendingStepIndex;
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.Stepper = Stepper;
}
