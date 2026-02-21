/**
 * AnimatedRenderer - Renders steps with cursor animations
 * Supports move, click, drag, and pause directives.
 * Delegates target resolution to BaseRenderer.resolveTarget() and swaps
 * environment-specific screenshots when highlighting dropdown tools.
 */

class AnimatedRenderer extends BaseRenderer {
    constructor(container) {
        super(container);
        this.animationQueue = [];
        this.isAnimating = false;
        this.animationAborted = false;
        this.cursorElement = null;
        this.clickRipple = null;
        this.animationArea = null;
    }

    /**
     * Initialize animation elements
     */
    initElements() {
        this.animationArea = document.getElementById('animationArea');
        this.cursorElement = document.getElementById('cursorElement');
        this.clickRipple = document.getElementById('clickRipple');
    }

    /**
     * Render a step with animations
     * @param {Object} step - The step data to render
     */
    render(step) {
        this.abort();
        this.clearSemanticIndicators();
        super.render(step);
        this.initElements();

        // Show animation area
        if (this.animationArea) {
            this.animationArea.classList.remove('hidden');
        }

        // Ensure parent #visualStepArea is visible when animations exist
        const animations = step.uiAnimations || [];
        if (animations.length > 0) {
            const visualArea = document.getElementById('visualStepArea');
            if (visualArea) {
                visualArea.classList.remove('hidden');
            }
            // Show default environment image when no step image is set
            const visualImage = document.getElementById('visualStepImage');
            if (visualImage && (!visualImage.src || visualImage.src === window.location.href || visualImage.src.endsWith('/'))) {
                visualImage.src = this.getImagePath(this.currentEnvironment, 0);
                visualImage.dataset.env = this.currentEnvironment;
                visualImage.dataset.imageIndex = '0';
            }
            // Give animation area a min-height when no image is present
            if (this.animationArea && (!visualImage || !visualImage.src || visualImage.src.endsWith('/'))) {
                this.animationArea.style.minHeight = '80px';
            }
        }

        // Queue animations if present
        if (animations.length > 0) {
            this.playAnimations(animations);
        } else {
            // No animations, hide cursor
            if (this.cursorElement) {
                this.cursorElement.classList.add('hidden');
            }
        }
    }

    /**
     * Play a sequence of animations
     * @param {Array} animations - Array of animation directives
     */
    async playAnimations(animations) {
        this.animationAborted = false;
        this.animationQueue = [...animations];
        this.isAnimating = true;

        // Check if any animation needs the cursor (move/click/drag types)
        const cursorTypes = ['move', 'click', 'drag', 'highlight', 'tooltip', 'arrow'];
        const needsCursor = animations.some(a => cursorTypes.includes(a.type || a.action));

        // Show and position cursor at start (only for cursor-based animations)
        if (this.cursorElement && needsCursor) {
            this.cursorElement.classList.remove('hidden');
            this.cursorElement.style.left = '50%';
            this.cursorElement.style.top = '50%';
        } else if (this.cursorElement) {
            this.cursorElement.classList.add('hidden');
        }

        for (const anim of this.animationQueue) {
            if (this.animationAborted) break;
            await this.executeAnimation(anim);
        }

        this.isAnimating = false;
    }

    /**
     * Execute a single animation directive
     * @param {Object} anim - The animation directive
     */
    async executeAnimation(anim) {
        const type = anim.type || anim.action;

        switch (type) {
            case 'move':
                await this.animateMove(anim);
                break;
            case 'click':
                await this.animateClick(anim);
                break;
            case 'drag':
                await this.animateDrag(anim);
                break;
            case 'pause':
                await this.animatePause(anim);
                break;
            case 'highlight':
                await this.animateHighlight(anim);
                break;
            case 'tooltip':
                await this.animateTooltip(anim);
                break;
            case 'arrow':
                await this.animateArrow(anim);
                break;
            default:
                console.warn('Unknown animation type:', type);
        }
    }

    /**
     * Animate cursor movement
     * @param {Object} anim - Move animation config
     */
    async animateMove(anim) {
        if (!this.cursorElement || !this.animationArea) return;

        const from = anim.from || { x: 50, y: 50 };
        const to = anim.to || { x: 50, y: 50 };
        const duration = anim.duration || 500;

        // Set starting position
        this.cursorElement.style.left = `${from.x}%`;
        this.cursorElement.style.top = `${from.y}%`;
        this.cursorElement.classList.remove('animating');

        // Force reflow
        this.cursorElement.offsetHeight;

        // Animate to end position
        this.cursorElement.style.transition = `left ${duration}ms ease-out, top ${duration}ms ease-out`;
        this.cursorElement.classList.add('animating');
        this.cursorElement.style.left = `${to.x}%`;
        this.cursorElement.style.top = `${to.y}%`;

        await this.delay(duration);

        this.cursorElement.classList.remove('animating');
        this.cursorElement.style.transition = 'none';
    }

    /**
     * Animate a click
     * @param {Object} anim - Click animation config
     */
    async animateClick(anim) {
        if (!this.cursorElement || !this.clickRipple || !this.animationArea) return;

        const at = anim.at || { x: 50, y: 50 };

        // Position cursor at click location
        this.cursorElement.style.left = `${at.x}%`;
        this.cursorElement.style.top = `${at.y}%`;

        // Position and show ripple
        this.clickRipple.style.left = `${at.x}%`;
        this.clickRipple.style.top = `${at.y}%`;
        this.clickRipple.classList.remove('hidden', 'active');

        // Force reflow
        this.clickRipple.offsetHeight;

        // Trigger ripple animation
        this.clickRipple.classList.add('active');

        await this.delay(600);

        this.clickRipple.classList.remove('active');
        this.clickRipple.classList.add('hidden');
    }

    /**
     * Animate a drag operation
     * @param {Object} anim - Drag animation config
     */
    async animateDrag(anim) {
        if (!this.cursorElement || !this.animationArea) return;

        const from = anim.from || { x: 30, y: 50 };
        const to = anim.to || { x: 70, y: 50 };
        const duration = anim.duration || 800;

        // Position at start
        this.cursorElement.style.left = `${from.x}%`;
        this.cursorElement.style.top = `${from.y}%`;

        // Show click at start
        await this.animateClick({ at: from });

        // Move while "pressed"
        this.cursorElement.style.transform = 'scale(0.9)';
        await this.animateMove({ from, to, duration });

        // Release
        this.cursorElement.style.transform = 'scale(1)';
        await this.animateClick({ at: to });
    }

    /**
     * Pause animation
     * @param {Object} anim - Pause animation config
     */
    async animatePause(anim) {
        const duration = anim.duration || 1000;
        await this.delay(duration);
    }

    /**
     * Resolve an animation target path to a position on the UI screenshot.
     * Delegates to BaseRenderer.resolveTarget() and normalizes the result
     * into {x, y, width, height, label, env, imageIndex}.
     * @param {string} target - Dot-separated path (e.g. "toolbar.create.revolve")
     * @returns {Object|null} Position data or null
     */
    resolveAnimationTarget(target) {
        if (!target) return null;

        const resolved = this.resolveTarget(target);
        if (!resolved) return null;

        const pos = resolved.position;
        return {
            x: pos.x,
            y: pos.y,
            width: pos.width || 3,
            height: pos.height || 5,
            label: resolved.label,
            env: resolved.env,
            imageIndex: resolved.imageIndex
        };
    }

    /**
     * Swap the UI screenshot if the target's environment/imageIndex differs
     * from what is currently displayed.
     * @param {string} env - Target environment ('solid' or 'sketch')
     * @param {number} imageIndex - Target image index
     */
    ensureCorrectImage(env, imageIndex) {
        const visualImage = document.getElementById('visualStepImage');
        if (!visualImage) return;

        const currentEnv = visualImage.dataset.env || '';
        const currentIdx = parseInt(visualImage.dataset.imageIndex || '-1', 10);

        if (currentEnv !== env || currentIdx !== imageIndex) {
            visualImage.src = this.getImagePath(env, imageIndex);
            visualImage.dataset.env = env;
            visualImage.dataset.imageIndex = String(imageIndex);
        }
    }

    /**
     * Convert a dot-path animation target to a human-readable label.
     * Prefers the JSON-sourced label from resolveTarget; falls back to
     * path formatting for unresolvable targets.
     * @param {string} target - Dot-separated path (e.g. "browser.rootComponent.origin.XZPlane")
     * @returns {string} Readable label (e.g. "Origin" or "Origin > XZ Plane")
     */
    formatTargetLabel(target) {
        if (!target) return '';

        // Try JSON label first
        const resolved = this.resolveTarget(target);
        if (resolved && resolved.label) return resolved.label;

        // Fallback: format the path segments
        const skipTokens = ['toolbar', 'browser', 'canvas', 'dialog', 'rootcomponent'];
        const parts = target.split('.')
            .filter(p => !skipTokens.includes(p.toLowerCase()))
            .map(p => p.replace(/([a-z])([A-Z])/g, '$1 $2')   // split camelCase
                       .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2') // split consecutive caps
                       .replace(/^./, s => s.toUpperCase()));      // capitalize first letter

        return parts.join(' > ');
    }

    /**
     * Create a visual highlight overlay on the UI image
     * @param {Object} position - {x, y, width, height} in percentages
     * @param {string} [style] - Optional style variant (e.g. 'pulse')
     * @param {string} [label] - Optional text label to display above the highlight
     */
    createImageHighlight(position, style, label) {
        const highlightsContainer = document.getElementById('visualStepHighlights');
        if (!highlightsContainer || !position) return;

        const highlightEl = document.createElement('div');
        highlightEl.className = 'visual-highlight semantic-overlay' + (style ? ` ${style}` : '');

        highlightEl.style.left = position.x + '%';
        highlightEl.style.top = position.y + '%';
        highlightEl.style.width = (position.width || 5) + '%';
        highlightEl.style.height = (position.height || 8) + '%';

        if (label) {
            const labelEl = document.createElement('span');
            labelEl.className = 'visual-highlight-label';
            labelEl.textContent = label;
            highlightEl.appendChild(labelEl);
        }

        highlightsContainer.appendChild(highlightEl);
    }

    /**
     * Animate a highlight indicator
     * @param {Object} anim - Highlight animation config
     */
    async animateHighlight(anim) {
        const target = this.resolveAnimationTarget(anim.target);
        if (target) {
            this.ensureCorrectImage(target.env, target.imageIndex);
            const label = target.label || this.formatTargetLabel(anim.target);
            this.createImageHighlight(target, anim.style, label);
            if (this.cursorElement) {
                this.cursorElement.classList.remove('hidden');
                this.cursorElement.style.left = `${target.x + target.width / 2}%`;
                this.cursorElement.style.top = `${target.y + target.height / 2}%`;
            }
        }
        await this.delay(anim.duration || 1500);
    }

    /**
     * Animate a tooltip indicator
     * @param {Object} anim - Tooltip animation config
     */
    async animateTooltip(anim) {
        const target = this.resolveAnimationTarget(anim.target);
        if (target) {
            this.ensureCorrectImage(target.env, target.imageIndex);
            const label = target.label || this.formatTargetLabel(anim.target);
            this.createImageHighlight(target, anim.style, label);
            if (this.cursorElement) {
                this.cursorElement.classList.remove('hidden');
                this.cursorElement.style.left = `${target.x + target.width / 2}%`;
                this.cursorElement.style.top = `${target.y + target.height / 2}%`;
            }
        }
        await this.delay(anim.duration || 2000);
    }

    /**
     * Animate an arrow indicator
     * @param {Object} anim - Arrow animation config
     */
    async animateArrow(anim) {
        const target = this.resolveAnimationTarget(anim.target);
        if (target) {
            this.ensureCorrectImage(target.env, target.imageIndex);
            const label = target.label || this.formatTargetLabel(anim.target);
            this.createImageHighlight(target, anim.style, label);
            if (this.cursorElement) {
                this.cursorElement.classList.remove('hidden');
                this.cursorElement.style.left = `${target.x + target.width / 2}%`;
                this.cursorElement.style.top = `${target.y + target.height / 2}%`;
            }
        }
        await this.delay(anim.duration || 1500);
    }

    /**
     * Remove all semantic indicator elements and image overlays
     */
    clearSemanticIndicators() {
        const highlightsContainer = document.getElementById('visualStepHighlights');
        if (highlightsContainer) {
            highlightsContainer.querySelectorAll('.semantic-overlay').forEach(el => el.remove());
        }
    }

    /**
     * Replay the current step's animations
     */
    replay() {
        if (!this.currentStep) return;

        this.abort();

        setTimeout(() => {
            const animations = this.currentStep.uiAnimations || [];
            if (animations.length > 0) {
                this.playAnimations(animations);
            }
        }, 100);
    }

    /**
     * Abort current animation sequence
     */
    abort() {
        this.animationAborted = true;
        this.isAnimating = false;
        this.animationQueue = [];
        this.clearSemanticIndicators();
    }

    /**
     * Delay helper
     * @param {number} ms - Milliseconds to delay
     */
    delay(ms) {
        return new Promise(resolve => {
            setTimeout(resolve, ms);
        });
    }

    /**
     * Clean up renderer
     */
    cleanup() {
        this.abort();
        this.clearSemanticIndicators();
        super.cleanup();
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.AnimatedRenderer = AnimatedRenderer;
}
