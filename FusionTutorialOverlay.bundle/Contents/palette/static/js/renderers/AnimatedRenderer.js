/**
 * AnimatedRenderer - Renders steps with cursor animations
 * Supports move, click, drag, and pause directives
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
        super.render(step);
        this.initElements();

        // Show animation area
        if (this.animationArea) {
            this.animationArea.classList.remove('hidden');
        }

        // Queue animations if present
        const animations = step.uiAnimations || [];
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

        // Show and position cursor at start
        if (this.cursorElement) {
            this.cursorElement.classList.remove('hidden');
            this.cursorElement.style.left = '50%';
            this.cursorElement.style.top = '50%';
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

        // Convert percentage to pixels
        const areaRect = this.animationArea.getBoundingClientRect();

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
        super.cleanup();
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.AnimatedRenderer = AnimatedRenderer;
}
