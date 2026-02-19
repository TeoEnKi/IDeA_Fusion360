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
            // Show default Fusion UI image when no step image is set
            const visualImage = document.getElementById('visualStepImage');
            if (visualImage && (!visualImage.src || visualImage.src === window.location.href || visualImage.src.endsWith('/'))) {
                visualImage.src = '../assets/UI Images/fusion_ui.png';
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
            case 'focusCamera':
                await this.animateFocusCamera(anim);
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
     * Resolve an animation target path to a percentage position on fusion_ui.png
     * Uses a hardcoded position map calibrated for the full UI screenshot.
     * @param {string} target - Dot-separated path (e.g. "toolbar.create.revolve")
     * @returns {Object|null} Position {x, y, width, height} in percentages, or null
     */
    resolveAnimationTarget(target) {
        if (!target) return null;

        // Positions calibrated for fusion_ui.png (full Fusion 360 UI screenshot)
        const FULL_UI_POSITIONS = {
            // Browser panel items
            'browser':      { x: 0,    y: 8,    width: 14,  height: 35 },
            'origin':       { x: 2,    y: 16,   width: 8,   height: 2.5 },
            'bodies':       { x: 2,    y: 13,   width: 8,   height: 2.5 },
            'sketches':     { x: 2,    y: 14.5, width: 8,   height: 2.5 },

            // Toolbar groups
            'create':       { x: 8,    y: 5,    width: 8,   height: 4 },
            'modify':       { x: 18,   y: 5,    width: 12,  height: 4 },
            'construct':    { x: 36,   y: 5,    width: 5,   height: 4 },
            'inspect':      { x: 42,   y: 5,    width: 5,   height: 4 },
            'insert':       { x: 48,   y: 5,    width: 7,   height: 4 },
            'assemble':     { x: 56,   y: 5,    width: 6,   height: 4 },
            'select':       { x: 63,   y: 5,    width: 4,   height: 4 },

            // Specific tools in CREATE
            'extrude':      { x: 12,   y: 5,    width: 3,   height: 4 },
            'revolve':      { x: 14.5, y: 5,    width: 3,   height: 4 },
            'sweep':        { x: 8,    y: 5,    width: 8,   height: 4 },
            'loft':         { x: 8,    y: 5,    width: 8,   height: 4 },

            // Specific tools in MODIFY
            'fillet':       { x: 20,   y: 5,    width: 3,   height: 4 },
            'chamfer':      { x: 23,   y: 5,    width: 3,   height: 4 },
            'shell':        { x: 26,   y: 5,    width: 3,   height: 4 },
            'press-pull':   { x: 18,   y: 5,    width: 3,   height: 4 },
            'move-copy':    { x: 29,   y: 5,    width: 3,   height: 4 },

            // Sketch tools (point to Create Sketch icon area)
            'line':         { x: 10,   y: 5,    width: 3,   height: 4 },
            'arc':          { x: 10,   y: 5,    width: 3,   height: 4 },
            'rectangle':    { x: 10,   y: 5,    width: 3,   height: 4 },
            'circle':       { x: 10,   y: 5,    width: 3,   height: 4 },

            // Common actions
            'finishsketch': { x: 85,   y: 5,    width: 5,   height: 4 },

            // ViewCube
            'viewcube':     { x: 88,   y: 8,    width: 8,   height: 8 }
        };

        const parts = target.toLowerCase().split('.');

        // Canvas targets are not resolvable to fixed UI positions
        if (parts[0] === 'canvas') {
            return null;
        }

        // Skip prefix tokens that are just category labels
        const skipTokens = ['toolbar', 'browser', 'canvas'];

        // Walk segments from last to first, return the first match
        for (let i = parts.length - 1; i >= 0; i--) {
            if (skipTokens.includes(parts[i])) continue;
            const pos = FULL_UI_POSITIONS[parts[i]];
            if (pos) return { ...pos };
        }

        return null;
    }

    /**
     * Convert a dot-path animation target to a human-readable label.
     * Strips category prefixes and splits camelCase.
     * @param {string} target - Dot-separated path (e.g. "browser.rootComponent.origin.XZPlane")
     * @returns {string} Readable label (e.g. "Origin > XZ Plane")
     */
    formatTargetLabel(target) {
        if (!target) return '';

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
        const position = this.resolveAnimationTarget(anim.target);
        if (position) {
            const label = this.formatTargetLabel(anim.target);
            this.createImageHighlight(position, anim.style, label);
            if (this.cursorElement) {
                this.cursorElement.classList.remove('hidden');
                this.cursorElement.style.left = `${position.x}%`;
                this.cursorElement.style.top = `${position.y}%`;
            }
        }
        await this.delay(anim.duration || 1500);
    }

    /**
     * Animate a tooltip indicator
     * @param {Object} anim - Tooltip animation config
     */
    async animateTooltip(anim) {
        const position = this.resolveAnimationTarget(anim.target);
        if (position) {
            const label = this.formatTargetLabel(anim.target);
            this.createImageHighlight(position, anim.style, label);
            if (this.cursorElement) {
                this.cursorElement.classList.remove('hidden');
                this.cursorElement.style.left = `${position.x}%`;
                this.cursorElement.style.top = `${position.y}%`;
            }
        }
        await this.delay(anim.duration || 2000);
    }

    /**
     * Animate an arrow indicator
     * @param {Object} anim - Arrow animation config
     */
    async animateArrow(anim) {
        const position = this.resolveAnimationTarget(anim.target);
        if (position) {
            const label = this.formatTargetLabel(anim.target);
            this.createImageHighlight(position, anim.style, label);
            if (this.cursorElement) {
                this.cursorElement.classList.remove('hidden');
                this.cursorElement.style.left = `${position.x}%`;
                this.cursorElement.style.top = `${position.y}%`;
            }
        }
        await this.delay(anim.duration || 1500);
    }

    /**
     * Animate a camera focus indicator
     * @param {Object} anim - Focus camera animation config
     */
    async animateFocusCamera(anim) {
        await this.delay(anim.duration || 1000);
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
