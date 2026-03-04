/**
 * BaseRenderer - Base class for step renderers
 * Defines the interface for rendering tutorial steps
 */

class BaseRenderer {
    constructor(container) {
        this.container = container;
        this.currentStep = null;
        this.uiConfigs = null;
        this.lookupMap = null;
        this.currentEnvironment = 'solid';
        this.carouselTimer = null;
        this.carouselResumeTimer = null;
        this.carouselImages = [];
        this.carouselIndex = 0;
        this.carouselAlt = 'Fusion 360 UI Reference';
        this.zoomInitialized = false;
        this.isZoomMode = false;
        this.zoomScale = 1;
        this.zoomPanX = 0;
        this.zoomPanY = 0;
        this.zoomMinScale = 1;
        this.zoomMaxScale = 4;
        this.zoomStep = 0.2;
        this.zoomToggleScale = 2;
        this.isDraggingZoom = false;
        this.zoomDragStartX = 0;
        this.zoomDragStartY = 0;
        this.zoomDragOriginX = 0;
        this.zoomDragOriginY = 0;
        this.lastTouchEndAt = 0;
        this.lastTouchTapX = 0;
        this.lastTouchTapY = 0;
        this.zoomHintTimer = null;
        this.zoomHintHideTimer = null;
        this.boundZoomHandlers = null;
        this.loadUIConfigs();
    }

    /**
     * Load UI component configurations for all environments
     */
    async loadUIConfigs() {
        try {
            const [solidRes, sketchRes] = await Promise.all([
                fetch('../assets/UI Images/Solid/Solid_UIComponents.json'),
                fetch('../assets/UI Images/Sketch/Sketch_UIComponents.json')
            ]);

            this.uiConfigs = {};
            if (solidRes.ok) this.uiConfigs.solid = await solidRes.json();
            if (sketchRes.ok) this.uiConfigs.sketch = await sketchRes.json();

            console.log('UI configs loaded:', Object.keys(this.uiConfigs));
            this.buildLookupMap();
            this.preloadImages();
        } catch (e) {
            console.warn('Could not load UI configs:', e);
        }
    }

    /**
     * Build a flat lookup map from all UI configs for O(1) target resolution.
     * Keys are registered both with and without environment prefix.
     */
    buildLookupMap() {
        this.lookupMap = {};

        for (const [envName, config] of Object.entries(this.uiConfigs)) {
            const components = config.components;
            if (!components) continue;

            // Toolbar groups and their tools
            if (components.toolbarGroups) {
                for (const [groupId, group] of Object.entries(components.toolbarGroups)) {
                    this._registerKey(`toolbar.${groupId}`, {
                        env: envName, imageIndex: group.imageIndex,
                        position: group.position, label: group.label, type: 'group'
                    });

                    if (group.tools) {
                        for (const tool of group.tools) {
                            const toolEntry = {
                                env: envName, imageIndex: group.imageIndex,
                                position: tool.position, label: tool.label, type: 'tool'
                            };
                            this._registerKey(`toolbar.${groupId}.${tool.id}`, toolEntry);
                            this._registerKey(`toolbar.*.${tool.id}`, toolEntry);
                        }
                    }
                }
            }

            // Environment tabs
            if (components.environmentTabs) {
                for (const [tabId, tab] of Object.entries(components.environmentTabs)) {
                    this._registerKey(`environmentTabs.${tabId}`, {
                        env: envName, imageIndex: tab.imageIndex,
                        position: tab.position, label: tab.label, type: 'envTab'
                    });
                }
            }

            // Browser items
            if (components.browser && components.browser.items) {
                for (const [itemId, item] of Object.entries(components.browser.items)) {
                    this._registerKey(`browser.${itemId}`, {
                        env: envName, imageIndex: item.imageIndex,
                        position: item.position, label: item.label, type: 'browser'
                    });
                }
            }

            // Navigation bar
            if (components.navigationBar) {
                for (const [navId, nav] of Object.entries(components.navigationBar)) {
                    this._registerKey(`nav.${navId}`, {
                        env: envName, imageIndex: nav.imageIndex,
                        position: nav.position, label: navId, type: 'nav'
                    });
                }
            }

            // Special: finishSketch
            if (components.finishSketch) {
                const fs = components.finishSketch;
                this._registerKey('toolbar.finishSketch', {
                    env: envName, imageIndex: fs.imageIndex,
                    position: fs.position, label: fs.label, type: 'special'
                });
                this._registerKey('finishSketch', {
                    env: envName, imageIndex: fs.imageIndex,
                    position: fs.position, label: fs.label, type: 'special'
                });
            }

            // Workspace dropdown
            if (components.workspaceDropdown) {
                const wd = components.workspaceDropdown;
                this._registerKey('workspaceDropdown', {
                    env: envName, imageIndex: wd.imageIndex,
                    position: wd.position, label: wd.label, type: 'special'
                });
            }
        }

        console.log('Lookup map built:', Object.keys(this.lookupMap).length, 'keys');
    }

    /**
     * Register a key in the lookup map with env-prefixed and unprefixed variants.
     * Unprefixed key is only stored if not already taken (first-registered wins).
     */
    _registerKey(key, entry) {
        const envKey = `${entry.env}:${key}`;
        this.lookupMap[envKey] = entry;
        if (!this.lookupMap[key]) {
            this.lookupMap[key] = entry;
        }
    }

    /**
     * Look up a key, trying currentEnvironment-prefixed first then unprefixed.
     * Returns a shallow copy so callers can mutate without affecting the map.
     */
    _lookupWithEnv(key) {
        const envKey = `${this.currentEnvironment}:${key}`;
        if (this.lookupMap[envKey]) return { ...this.lookupMap[envKey] };
        if (this.lookupMap[key]) return { ...this.lookupMap[key] };
        return null;
    }

    /**
     * Resolve an animation/highlight target path to component data.
     * Multi-strategy resolution handles various target path patterns from tutorials.
     * @param {string} targetPath - Dot-separated target path (e.g. "toolbar.create.revolve")
     * @returns {Object|null} { env, imageIndex, position, label, type } or null
     */
    resolveTarget(targetPath) {
        if (!targetPath || !this.lookupMap) return null;

        const parts = targetPath.split('.');

        // 1. Skip canvas.* and dialog.* — these are viewport/dialog elements, not UI image targets
        if (parts[0] === 'canvas' || parts[0] === 'dialog') return null;

        // 2. Direct lookup
        let result = this._lookupWithEnv(targetPath);
        if (result) return this._finalizeResult(result);

        // 3. Strip non-structural segments and retry
        const nonStructural = ['rootcomponent', 'sketch', 'solid'];
        const cleaned = parts.filter(p => !nonStructural.includes(p.toLowerCase()));
        const cleanedPath = cleaned.join('.');
        if (cleanedPath !== targetPath) {
            result = this._lookupWithEnv(cleanedPath);
            if (result) return this._finalizeResult(result);
        }

        // 4. Progressive path shortening (for browser-like deep paths)
        if (cleaned.length > 2) {
            for (let len = cleaned.length - 1; len >= 2; len--) {
                const shortened = cleaned.slice(0, len).join('.');
                result = this._lookupWithEnv(shortened);
                if (result) return this._finalizeResult(result);
            }
        }

        // 5. Wildcard: toolbar.*.{lastSegment}
        const lastSegment = cleaned[cleaned.length - 1];
        result = this._lookupWithEnv(`toolbar.*.${lastSegment}`);
        if (result) return this._finalizeResult(result);

        // 6. camelCase to kebab-case and retry wildcard
        const kebab = lastSegment.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
        if (kebab !== lastSegment.toLowerCase()) {
            result = this._lookupWithEnv(`toolbar.*.${kebab}`);
            if (result) return this._finalizeResult(result);
        }

        // 7. Substring match in wildcard keys (e.g. "arc" matches "3-point-arc")
        const lowerLast = lastSegment.toLowerCase();
        for (const key of Object.keys(this.lookupMap)) {
            if (key.includes(':')) continue; // skip env-prefixed keys
            if (key.startsWith('toolbar.*.') && key.toLowerCase().includes(lowerLast)) {
                result = this._lookupWithEnv(key);
                if (result) return this._finalizeResult(result);
            }
        }

        // 8. Browser fallback
        result = this._lookupWithEnv(`browser.${lastSegment}`);
        if (result) return this._finalizeResult(result);

        // 9. Bare segment lookup
        result = this._lookupWithEnv(lastSegment);
        if (result) return this._finalizeResult(result);

        return null;
    }

    /**
     * Finalize a resolved result — override env for environment-agnostic items
     * (browser and nav panels appear the same across environments)
     */
    _finalizeResult(result) {
        if (result.type === 'browser' || result.type === 'nav') {
            result.env = this.currentEnvironment;
        }
        return result;
    }

    /**
     * Get image path for an environment and image index.
     * Convention: ../assets/UI Images/{Env}/{Env}_{index}.png
     * @param {string} env - 'solid' or 'sketch'
     * @param {number} imageIndex - 0 = base UI, 1+ = dropdown states
     * @returns {string} Relative image path
     */
    getImagePath(env, imageIndex) {
        const envCap = env.charAt(0).toUpperCase() + env.slice(1);
        return `../assets/UI Images/${envCap}/${envCap}_${imageIndex}.png`;
    }

    /**
     * Detect which environment a step belongs to from step data.
     * @param {Object} step - Step data
     * @returns {string} 'solid' or 'sketch'
     */
    detectStepEnvironment(step) {
        // 1. Explicit requires
        if (step.requires && step.requires.environment) {
            return step.requires.environment.toLowerCase();
        }

        const actions = step.fusionActions || [];

        // 2. ui.openWorkspace with environment field (highest priority action)
        for (const action of actions) {
            if (action.type === 'ui.openWorkspace' && action.environment) {
                return action.environment.toLowerCase();
            }
        }

        // 3. ui.enterMode or ui.exitMode: Sketch
        for (const action of actions) {
            if ((action.type === 'ui.enterMode' || action.type === 'ui.exitMode') &&
                action.mode === 'Sketch') {
                return 'sketch';
            }
        }

        // 4. Default
        return 'solid';
    }

    /**
     * Preload all environment images to prevent flicker during swaps.
     */
    preloadImages() {
        for (const [envName, config] of Object.entries(this.uiConfigs)) {
            let maxIdx = 0;
            const components = config.components;
            if (components && components.toolbarGroups) {
                for (const group of Object.values(components.toolbarGroups)) {
                    if (group.imageIndex > maxIdx) maxIdx = group.imageIndex;
                }
            }
            for (let i = 0; i <= maxIdx; i++) {
                const img = new Image();
                img.src = this.getImagePath(envName, i);
            }
        }
    }

    /**
     * Render a step to the UI
     * @param {Object} step - The step data to render
     */
    render(step) {
        this.initVisualZoomControls();
        this.resetZoomState(true);
        this.currentStep = step;
        this.currentEnvironment = this.detectStepEnvironment(step);
        this.renderStepInfo(step);
        this.renderVisualStep(step);
        this.renderExpandedContent(step);
        this.renderQCChecks(step);
        this.renderWarnings(step);

        // Reset tracking for new step
        if (window.sendToBridge) {
            window.sendToBridge({ action: 'resetTracking' });
        }
    }

    /**
     * Render visual step with UI image and highlights
     * @param {Object} step - The step data
     */
    renderVisualStep(step) {
        const visualArea = document.getElementById('visualStepArea');
        const visualImage = document.getElementById('visualStepImage');
        const visualHighlights = document.getElementById('visualStepHighlights');
        const visualCaption = document.getElementById('visualStepCaption');
        const carouselIndicators = document.getElementById('carouselIndicators');
        const carouselNav = document.getElementById('carouselNav');

        if (!visualArea || !visualImage || !visualHighlights) return;

        this.stopCarousel();
        const visualStep = step.visualStep;

        if (!visualStep || (!visualStep.image && !Array.isArray(visualStep.images))) {
            if (step.uiTargets && step.uiTargets.length > 0 && this.uiConfigs) {
                this.renderNavbarWithTargets(step.uiTargets, visualArea, visualImage, visualHighlights, visualCaption);
                return;
            }

            visualHighlights.innerHTML = '';
            if (visualCaption) {
                visualCaption.textContent = '';
                visualCaption.style.display = 'none';
            }
            if (carouselIndicators) {
                carouselIndicators.innerHTML = '';
                carouselIndicators.classList.add('hidden');
            }
            if (carouselNav) {
                carouselNav.classList.add('hidden');
            }

            visualArea.classList.add('hidden');
            this.resetZoomState(true);
            return;
        }

        visualArea.classList.remove('hidden');
        this.resetZoomState(true);

        if (Array.isArray(visualStep.images) && visualStep.images.length > 0) {
            visualImage.dataset.env = this.currentEnvironment;
            visualImage.alt = visualStep.alt || 'Fusion 360 UI Reference';
            visualImage.classList.add('carousel-enabled');

            this.startCarousel(visualStep.images, visualImage.alt);
            return;
        }

        const imagePath = this.normalizeVisualImagePath(visualStep.image, visualStep.useNavbar);

        visualImage.src = imagePath;
        visualImage.dataset.env = this.currentEnvironment;
        visualImage.dataset.imageIndex = '0';
        visualImage.alt = visualStep.alt || 'Fusion 360 UI Reference';
        visualImage.classList.remove('carousel-enabled');
        visualImage.style.opacity = '';

        if (carouselIndicators) {
            carouselIndicators.innerHTML = '';
            carouselIndicators.classList.add('hidden');
        }
        if (carouselNav) {
            carouselNav.classList.add('hidden');
        }

        const highlights = this.resolveHighlights(visualStep.highlights);
        this.renderHighlightElements(visualHighlights, highlights);

        if (visualCaption) {
            visualCaption.textContent = visualStep.caption || '';
            visualCaption.style.display = visualStep.caption ? 'block' : 'none';
        }
    }

    /**
     * Render UI image with specific targets highlighted
     */
    renderNavbarWithTargets(targets, visualArea, visualImage, visualHighlights, visualCaption) {
        const carouselIndicators = document.getElementById('carouselIndicators');
        const carouselNav = document.getElementById('carouselNav');
        visualArea.classList.remove('hidden');
        visualImage.src = this.getImagePath(this.currentEnvironment, 0);
        visualImage.dataset.env = this.currentEnvironment;
        visualImage.dataset.imageIndex = '0';
        visualImage.alt = 'Fusion 360 Toolbar';
        visualImage.classList.remove('carousel-enabled');
        visualImage.style.opacity = '';

        visualHighlights.innerHTML = '';
        if (carouselIndicators) {
            carouselIndicators.innerHTML = '';
            carouselIndicators.classList.add('hidden');
        }
        if (carouselNav) {
            carouselNav.classList.add('hidden');
        }
        this.resetZoomState(true);

        targets.forEach((target, index) => {
            const resolved = this.resolveTarget(target.component || target);
            if (resolved) {
                const pos = resolved.position;
                const highlightEl = document.createElement('div');
                highlightEl.className = 'visual-highlight';

                highlightEl.style.left = pos.x + '%';
                highlightEl.style.top = pos.y + '%';
                highlightEl.style.width = (pos.width || 3) + '%';
                highlightEl.style.height = (pos.height || 5) + '%';

                if (targets.length > 1) {
                    const numberEl = document.createElement('span');
                    numberEl.className = 'visual-highlight-number';
                    numberEl.textContent = (index + 1).toString();
                    highlightEl.appendChild(numberEl);
                }

                const labelEl = document.createElement('span');
                labelEl.className = 'visual-highlight-label';
                labelEl.textContent = target.label || resolved.label || target.component;
                highlightEl.appendChild(labelEl);

                visualHighlights.appendChild(highlightEl);
            }
        });

        if (visualCaption) {
            visualCaption.textContent = '';
            visualCaption.style.display = 'none';
        }
    }

    normalizeVisualImagePath(imagePath, useNavbar = false) {
        if (useNavbar || imagePath === 'navbar' || imagePath === 'toolbar') {
            return this.getImagePath(this.currentEnvironment, 0);
        }
        if (imagePath && !imagePath.startsWith('http') && !imagePath.startsWith('/') && !imagePath.startsWith('../')) {
            return '../' + imagePath;
        }
        return imagePath;
    }

    renderHighlightElements(container, highlights) {
        if (!container) return;
        container.innerHTML = '';

        if (!highlights || highlights.length === 0) return;

        highlights.forEach((highlight, index) => {
            const highlightEl = document.createElement('div');
            highlightEl.className = 'visual-highlight' + (highlight.shape === 'circle' ? ' circle' : '');

            highlightEl.style.left = highlight.x + '%';
            highlightEl.style.top = highlight.y + '%';
            highlightEl.style.width = highlight.width + '%';
            highlightEl.style.height = highlight.height + '%';

            if (highlights.length > 1) {
                const numberEl = document.createElement('span');
                numberEl.className = 'visual-highlight-number';
                numberEl.textContent = (index + 1).toString();
                highlightEl.appendChild(numberEl);
            }

            if (highlight.label) {
                const labelEl = document.createElement('span');
                labelEl.className = 'visual-highlight-label';
                labelEl.textContent = highlight.label;
                highlightEl.appendChild(labelEl);
            }

            container.appendChild(highlightEl);
        });
    }

    startCarousel(imagesArray, alt = 'Fusion 360 UI Reference') {
        this.stopCarousel();
        this.carouselAlt = alt;
        this.carouselIndex = 0;

        if (!Array.isArray(imagesArray)) {
            this.carouselImages = [];
        } else if (imagesArray.length > 0 && typeof imagesArray[0] === 'string') {
            // Backward-compatible internal shape if strings are ever passed.
            this.carouselImages = imagesArray.map(image => ({
                image: this.normalizeVisualImagePath(image),
                highlights: [],
                caption: ''
            }));
        } else {
            this.carouselImages = imagesArray.map(entry => ({
                ...entry,
                image: this.normalizeVisualImagePath(entry.image)
            }));
        }

        this.renderCarouselIndicators(this.carouselImages.length);

        if (this.carouselImages.length === 0) {
            this.updateCarouselControls();
            return;
        }

        this.showCarouselImage(0);
    }

    showCarouselImage(index) {
        const visualImage = document.getElementById('visualStepImage');
        const visualHighlights = document.getElementById('visualStepHighlights');
        const visualCaption = document.getElementById('visualStepCaption');

        if (!visualImage || !visualHighlights || !this.carouselImages || this.carouselImages.length === 0) return;

        const imageCount = this.carouselImages.length;
        const safeIndex = ((index % imageCount) + imageCount) % imageCount;
        this.carouselIndex = safeIndex;

        visualImage.classList.add('carousel-enabled');
        visualImage.style.opacity = '0.92';
        const activeImage = this.carouselImages[safeIndex] || {};

        visualImage.src = activeImage.image || '';
        visualImage.alt = this.carouselAlt || 'Fusion 360 UI Reference';
        visualImage.dataset.imageIndex = String(safeIndex);
        requestAnimationFrame(() => {
            visualImage.style.opacity = '1';
        });

        const activeHighlights = this.resolveHighlights(activeImage.highlights || []);
        this.renderHighlightElements(visualHighlights, activeHighlights);

        if (visualCaption) {
            const caption = activeImage.caption || '';
            visualCaption.textContent = caption;
            visualCaption.style.display = caption ? 'block' : 'none';
        }
        this.resetZoomState(false);
        this.updateCarouselControls();
    }

    showPrevCarouselImage() {
        if (!Array.isArray(this.carouselImages) || this.carouselImages.length <= 1) return;
        if (this.carouselIndex <= 0) return;
        this.showCarouselImage(this.carouselIndex - 1);
    }

    showNextCarouselImage() {
        if (!Array.isArray(this.carouselImages) || this.carouselImages.length <= 1) return;
        if (this.carouselIndex >= this.carouselImages.length - 1) return;
        this.showCarouselImage(this.carouselIndex + 1);
    }

    renderCarouselIndicators(count) {
        const carouselIndicators = document.getElementById('carouselIndicators');
        if (!carouselIndicators) return;

        carouselIndicators.innerHTML = '';
        if (!count || count <= 0) {
            carouselIndicators.classList.add('hidden');
            this.updateCarouselControls();
            return;
        }

        for (let i = 0; i < count; i++) {
            const dot = document.createElement('button');
            dot.type = 'button';
            dot.className = 'carousel-dot' + (i === this.carouselIndex ? ' active' : '');
            dot.setAttribute('aria-label', `Show image ${i + 1}`);
            dot.addEventListener('click', () => {
                this.showCarouselImage(i);
            });
            carouselIndicators.appendChild(dot);
        }

        this.updateCarouselControls();
    }

    updateCarouselControls() {
        const count = Array.isArray(this.carouselImages) ? this.carouselImages.length : 0;
        const carouselNav = document.getElementById('carouselNav');
        const carouselIndicators = document.getElementById('carouselIndicators');
        const prevBtn = document.getElementById('carouselPrevImageBtn');
        const nextBtn = document.getElementById('carouselNextImageBtn');

        if (carouselIndicators) {
            carouselIndicators.classList.toggle('hidden', count <= 1);
            carouselIndicators.querySelectorAll('.carousel-dot').forEach((dot, dotIndex) => {
                dot.classList.toggle('active', dotIndex === this.carouselIndex);
            });
        }

        if (carouselNav) {
            carouselNav.classList.toggle('hidden', count <= 1);
        }

        if (prevBtn) {
            prevBtn.disabled = count <= 1 || this.carouselIndex <= 0;
        }
        if (nextBtn) {
            nextBtn.disabled = count <= 1 || this.carouselIndex >= count - 1;
        }
    }

    stopCarousel() {
        if (this.carouselTimer) {
            clearInterval(this.carouselTimer);
            this.carouselTimer = null;
        }
        if (this.carouselResumeTimer) {
            clearTimeout(this.carouselResumeTimer);
            this.carouselResumeTimer = null;
        }
    }

    initVisualZoomControls() {
        if (this.zoomInitialized) return;

        const animationArea = document.getElementById('animationArea');
        const prevBtn = document.getElementById('carouselPrevImageBtn');
        const nextBtn = document.getElementById('carouselNextImageBtn');

        if (!animationArea) return;

        this.boundZoomHandlers = {
            onWheel: (event) => this.handleWheelZoom(event),
            onMouseDown: (event) => this.handleZoomDragStart(event),
            onMouseMove: (event) => this.handleZoomDragMove(event),
            onMouseUp: () => this.handleZoomDragEnd(),
            onMouseLeave: () => this.handleZoomDragEnd(),
            onClick: (event) => this.handleZoomHintCandidateClick(event),
            onDoubleClick: (event) => this.handleZoomToggleGesture(event),
            onTouchEnd: (event) => this.handleTouchZoomToggle(event)
        };

        animationArea.addEventListener('wheel', this.boundZoomHandlers.onWheel, { passive: false });
        animationArea.addEventListener('mousedown', this.boundZoomHandlers.onMouseDown);
        animationArea.addEventListener('click', this.boundZoomHandlers.onClick);
        animationArea.addEventListener('dblclick', this.boundZoomHandlers.onDoubleClick);
        animationArea.addEventListener('touchend', this.boundZoomHandlers.onTouchEnd, { passive: false });
        window.addEventListener('mousemove', this.boundZoomHandlers.onMouseMove);
        window.addEventListener('mouseup', this.boundZoomHandlers.onMouseUp);
        animationArea.addEventListener('mouseleave', this.boundZoomHandlers.onMouseLeave);

        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.showPrevCarouselImage());
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.showNextCarouselImage());
        }

        this.zoomInitialized = true;
        this.applyZoomUiState();
        this.updateCarouselControls();
        this.applyZoomTransform();
    }

    getVisualZoomElements() {
        return {
            animationArea: document.getElementById('animationArea'),
            zoomLayer: document.getElementById('visualStepZoomLayer'),
            zoomHint: document.getElementById('zoomGestureHint')
        };
    }

    toggleZoomMode(forceMode) {
        const nextMode = typeof forceMode === 'boolean' ? forceMode : !this.isZoomMode;
        this.isZoomMode = nextMode;

        if (!this.isZoomMode) {
            this.resetZoomState(false);
            this.applyZoomUiState();
            return;
        }

        this.zoomScale = 1;
        this.zoomPanX = 0;
        this.zoomPanY = 0;
        this.isDraggingZoom = false;
        this.applyZoomUiState();
        this.applyZoomTransform();
    }

    resetZoomState(exitMode = false) {
        this.cancelZoomGestureHint();
        this.hideZoomGestureHint();
        this.zoomScale = 1;
        this.zoomPanX = 0;
        this.zoomPanY = 0;
        this.isDraggingZoom = false;
        if (exitMode) {
            this.isZoomMode = false;
        }
        this.applyZoomUiState();
        this.applyZoomTransform();
    }

    applyZoomUiState() {
        const { animationArea } = this.getVisualZoomElements();
        if (animationArea) {
            animationArea.classList.toggle('zoomed', this.zoomScale > 1);
            animationArea.classList.toggle('dragging', this.isDraggingZoom);
        }
    }

    applyZoomTransform() {
        const { zoomLayer } = this.getVisualZoomElements();
        if (!zoomLayer) return;
        const pan = this.clampZoomPan(this.zoomPanX, this.zoomPanY, this.zoomScale);
        this.zoomPanX = pan.x;
        this.zoomPanY = pan.y;
        zoomLayer.style.transform = `translate3d(${this.zoomPanX}px, ${this.zoomPanY}px, 0) scale(${this.zoomScale})`;
    }

    setZoomScale(nextScale, anchorPoint = null) {
        const { animationArea, zoomLayer } = this.getVisualZoomElements();
        if (!animationArea || !zoomLayer) return;

        const oldScale = this.zoomScale;
        const clampedScale = Math.min(this.zoomMaxScale, Math.max(this.zoomMinScale, nextScale));
        if (clampedScale === oldScale) return;

        if (anchorPoint) {
            const contentX = (anchorPoint.x - this.zoomPanX) / oldScale;
            const contentY = (anchorPoint.y - this.zoomPanY) / oldScale;
            this.zoomPanX = anchorPoint.x - (contentX * clampedScale);
            this.zoomPanY = anchorPoint.y - (contentY * clampedScale);
        }

        this.zoomScale = clampedScale;
        if (this.zoomScale <= 1) {
            this.zoomPanX = 0;
            this.zoomPanY = 0;
        }

        this.applyZoomUiState();
        this.applyZoomTransform();
    }

    clampZoomPan(panX, panY, scale = this.zoomScale) {
        const { animationArea, zoomLayer } = this.getVisualZoomElements();
        if (!animationArea || !zoomLayer || scale <= 1) {
            return { x: 0, y: 0 };
        }

        const viewportW = animationArea.clientWidth;
        const viewportH = animationArea.clientHeight;
        const contentW = zoomLayer.offsetWidth;
        const contentH = zoomLayer.offsetHeight;
        const scaledW = contentW * scale;
        const scaledH = contentH * scale;

        const minX = Math.min(0, viewportW - scaledW);
        const minY = Math.min(0, viewportH - scaledH);
        const x = Math.min(0, Math.max(minX, panX));
        const y = Math.min(0, Math.max(minY, panY));
        return { x, y };
    }

    handleWheelZoom(event) {
        const { animationArea } = this.getVisualZoomElements();
        if (!animationArea) return;

        this.cancelZoomGestureHint();
        this.hideZoomGestureHint();
        event.preventDefault();

        const rect = animationArea.getBoundingClientRect();
        const anchor = {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top
        };
        const delta = event.deltaY < 0 ? this.zoomStep : -this.zoomStep;
        this.setZoomScale(this.zoomScale + delta, anchor);
    }

    handleZoomHintCandidateClick(event) {
        if (!event || event.button !== 0) return;

        // Ignore synthetic click that commonly follows touchend.
        if (Date.now() - this.lastTouchEndAt < 500) return;

        this.scheduleZoomGestureHint(event.clientX, event.clientY);
    }

    handleZoomToggleGesture(event) {
        const { animationArea } = this.getVisualZoomElements();
        if (!animationArea) return;

        this.cancelZoomGestureHint();
        this.hideZoomGestureHint();
        event.preventDefault();
        const rect = animationArea.getBoundingClientRect();
        const anchor = {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top
        };

        if (this.zoomScale > 1) {
            this.setZoomScale(1, anchor);
        } else {
            this.setZoomScale(this.zoomToggleScale, anchor);
        }
    }

    handleTouchZoomToggle(event) {
        const { animationArea } = this.getVisualZoomElements();
        if (!animationArea) return;
        if (!event.changedTouches || event.changedTouches.length === 0) return;

        const touch = event.changedTouches[0];
        const now = Date.now();
        const dt = now - this.lastTouchEndAt;
        const dx = touch.clientX - this.lastTouchTapX;
        const dy = touch.clientY - this.lastTouchTapY;
        const distSq = (dx * dx) + (dy * dy);

        this.lastTouchEndAt = now;
        this.lastTouchTapX = touch.clientX;
        this.lastTouchTapY = touch.clientY;

        // Double-tap within 300ms and ~24px radius toggles zoom.
        if (dt > 0 && dt <= 300 && distSq <= (24 * 24)) {
            this.cancelZoomGestureHint();
            this.hideZoomGestureHint();
            event.preventDefault();
            this.handleZoomToggleGesture({
                preventDefault() {},
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            return;
        }

        this.scheduleZoomGestureHint(touch.clientX, touch.clientY);
    }

    handleZoomDragStart(event) {
        if (this.zoomScale <= 1) return;
        if (event.button !== 0) return;

        this.cancelZoomGestureHint();
        this.hideZoomGestureHint();
        this.isDraggingZoom = true;
        this.zoomDragStartX = event.clientX;
        this.zoomDragStartY = event.clientY;
        this.zoomDragOriginX = this.zoomPanX;
        this.zoomDragOriginY = this.zoomPanY;
        this.applyZoomUiState();
        event.preventDefault();
    }

    handleZoomDragMove(event) {
        if (!this.isDraggingZoom) return;

        const deltaX = event.clientX - this.zoomDragStartX;
        const deltaY = event.clientY - this.zoomDragStartY;
        this.zoomPanX = this.zoomDragOriginX + deltaX;
        this.zoomPanY = this.zoomDragOriginY + deltaY;
        this.applyZoomTransform();
    }

    handleZoomDragEnd() {
        if (!this.isDraggingZoom) return;
        this.isDraggingZoom = false;
        this.applyZoomUiState();
    }

    scheduleZoomGestureHint(clientX, clientY) {
        this.cancelZoomGestureHint();
        this.hideZoomGestureHint();
        this.zoomHintTimer = setTimeout(() => {
            this.zoomHintTimer = null;
            this.showZoomGestureHint(clientX, clientY);
        }, 2000);
    }

    cancelZoomGestureHint() {
        if (this.zoomHintTimer) {
            clearTimeout(this.zoomHintTimer);
            this.zoomHintTimer = null;
        }
    }

    hideZoomGestureHint() {
        if (this.zoomHintHideTimer) {
            clearTimeout(this.zoomHintHideTimer);
            this.zoomHintHideTimer = null;
        }

        const { zoomHint } = this.getVisualZoomElements();
        if (!zoomHint) return;
        zoomHint.classList.remove('play');
        zoomHint.classList.add('hidden');
    }

    showZoomGestureHint(clientX, clientY) {
        const { animationArea, zoomHint } = this.getVisualZoomElements();
        if (!animationArea || !zoomHint) return;

        const rect = animationArea.getBoundingClientRect();
        const localX = clientX - rect.left;
        const localY = clientY - rect.top;

        zoomHint.classList.remove('hidden', 'play');
        // Measure after unhide
        const hintW = zoomHint.offsetWidth || 120;
        const hintH = zoomHint.offsetHeight || 28;
        const offsetX = 14;
        const offsetY = -10;
        const maxX = Math.max(0, animationArea.clientWidth - hintW - 6);
        const maxY = Math.max(0, animationArea.clientHeight - hintH - 6);
        const left = Math.min(maxX, Math.max(6, localX + offsetX));
        const top = Math.min(maxY, Math.max(6, localY + offsetY));
        zoomHint.style.left = `${left}px`;
        zoomHint.style.top = `${top}px`;

        // Restart animation cleanly
        void zoomHint.offsetWidth;
        zoomHint.classList.add('play');

        this.zoomHintHideTimer = setTimeout(() => {
            this.zoomHintHideTimer = null;
            this.hideZoomGestureHint();
        }, 3000);
    }

    /**
     * Resolve highlight definitions — convert component references to positions
     */
    resolveHighlights(highlights) {
        if (!highlights) return [];

        return highlights.map(h => {
            if (h.component) {
                const resolved = this.resolveTarget(h.component);
                if (resolved) {
                    const pos = resolved.position;
                    return {
                        x: pos.x,
                        y: pos.y,
                        width: pos.width || 3,
                        height: pos.height || 5,
                        label: h.label || resolved.label,
                        shape: h.shape || 'rect'
                    };
                }
            }
            return h;
        });
    }

    /**
     * Render basic step information
     * @param {Object} step - The step data
     */
    renderStepInfo(step) {
        const stepNumber = document.getElementById('stepNumber');
        const stepTitle = document.getElementById('stepTitle');
        const stepInstruction = document.getElementById('stepInstruction');
        if (stepNumber) {
            stepNumber.textContent = (step.currentIndex || 0) + 1;
        }
        if (stepTitle) {
            stepTitle.textContent = step.title || 'Step';
        }
        if (stepInstruction) {
            stepInstruction.textContent = step.instruction || '';
        }
    }

    /**
     * Render expanded content (tips, dimensions, reference images)
     * @param {Object} step - The step data
     */
    renderExpandedContent(step) {
        const expandedSection = document.getElementById('expandedSection');
        const expandedContent = document.getElementById('expandedContent');

        if (!expandedSection || !expandedContent) return;

        const expanded = step.expandedContent;
        const topLevelTips = step.tips || [];

        // Hide if no expandedContent AND no top-level tips
        if (!expanded && topLevelTips.length === 0) {
            expandedSection.classList.add('hidden');
            return;
        }

        expandedSection.classList.remove('hidden');
        expandedContent.innerHTML = '';

        // Why this matters
        if (expanded && expanded.whyThisMatters) {
            const whyDiv = document.createElement('div');
            whyDiv.className = 'expanded-block';
            whyDiv.innerHTML = `<h4>Why This Matters</h4><p>${expanded.whyThisMatters}</p>`;
            expandedContent.appendChild(whyDiv);
        }

        // Merge tips: expandedContent.tips (plain strings) + step.tips ({symbol, text} or strings)
        const mergedTips = [];
        if (expanded && expanded.tips && expanded.tips.length > 0) {
            expanded.tips.forEach(tip => {
                mergedTips.push({ symbol: null, text: tip });
            });
        }
        if (topLevelTips.length > 0) {
            topLevelTips.forEach(tip => {
                if (typeof tip === 'string') {
                    mergedTips.push({ symbol: null, text: tip });
                } else {
                    mergedTips.push({ symbol: tip.symbol || null, text: tip.text || '' });
                }
            });
        }

        if (mergedTips.length > 0) {
            const tipsDiv = document.createElement('div');
            tipsDiv.className = 'expanded-block';
            tipsDiv.innerHTML = '<h4>Tips</h4>';
            const tipsList = document.createElement('ul');
            tipsList.className = 'tips-list';
            mergedTips.forEach(tip => {
                const li = document.createElement('li');
                if (tip.symbol) {
                    li.classList.add('has-symbol');
                    li.textContent = tip.symbol + ' ' + tip.text;
                } else {
                    li.textContent = tip.text;
                }
                tipsList.appendChild(li);
            });
            tipsDiv.appendChild(tipsList);
            expandedContent.appendChild(tipsDiv);
        }

        // Dimensions/Parameters
        if (expanded && (expanded.dimensions || expanded.parameters)) {
            const data = expanded.dimensions || expanded.parameters;
            const dataDiv = document.createElement('div');
            dataDiv.className = 'expanded-block dimensions-block';
            dataDiv.innerHTML = `<h4>${expanded.dimensions ? 'Dimensions' : 'Parameters'}</h4>`;
            const dataList = document.createElement('dl');
            dataList.className = 'dimensions-list';
            Object.entries(data).forEach(([key, value]) => {
                const dt = document.createElement('dt');
                dt.textContent = key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase());
                const dd = document.createElement('dd');
                dd.textContent = value;
                dataList.appendChild(dt);
                dataList.appendChild(dd);
            });
            dataDiv.appendChild(dataList);
            expandedContent.appendChild(dataDiv);
        }

        // Reference image
        if (expanded && expanded.referenceImage) {
            let refImagePath = expanded.referenceImage;
            if (refImagePath && !refImagePath.startsWith('http') && !refImagePath.startsWith('/') && !refImagePath.startsWith('../')) {
                refImagePath = '../' + refImagePath;
            }
            const imgDiv = document.createElement('div');
            imgDiv.className = 'expanded-block reference-image-block';
            imgDiv.innerHTML = `<h4>Reference</h4><img src="${refImagePath}" alt="Step reference" class="reference-image" onclick="this.classList.toggle('expanded')">`;
            expandedContent.appendChild(imgDiv);
        }

        // Next steps (for final step)
        if (expanded && expanded.nextSteps && expanded.nextSteps.length > 0) {
            const nextDiv = document.createElement('div');
            nextDiv.className = 'expanded-block';
            nextDiv.innerHTML = '<h4>Next Steps</h4>';
            const nextList = document.createElement('ul');
            nextList.className = 'next-steps-list';
            expanded.nextSteps.forEach(step => {
                const li = document.createElement('li');
                li.textContent = step;
                nextList.appendChild(li);
            });
            nextDiv.appendChild(nextList);
            expandedContent.appendChild(nextDiv);
        }

        // Skills learned (for final step)
        if (expanded && expanded.skillsLearned && expanded.skillsLearned.length > 0) {
            const skillsDiv = document.createElement('div');
            skillsDiv.className = 'expanded-block skills-block';
            skillsDiv.innerHTML = '<h4>Skills Learned</h4>';
            const skillsList = document.createElement('ul');
            skillsList.className = 'skills-list';
            expanded.skillsLearned.forEach(skill => {
                const li = document.createElement('li');
                li.innerHTML = `<span class="skill-check">\u2705</span> ${skill}`;
                skillsList.appendChild(li);
            });
            skillsDiv.appendChild(skillsList);
            expandedContent.appendChild(skillsDiv);
        }
    }

    /**
     * Render QC checks with symbols
     * @param {Object} step - The step data
     */
    renderQCChecks(step) {
        const qcSection = document.getElementById('qcSection');
        const qcList = document.getElementById('qcList');

        if (!qcSection || !qcList) return;

        const checks = step.qcChecks || [];
        if (checks.length === 0) {
            qcSection.classList.add('hidden');
            return;
        }

        qcSection.classList.remove('hidden');
        qcList.innerHTML = '';

        checks.forEach(check => {
            const li = document.createElement('li');
            li.classList.add('pending');

            // Add data attributes for event matching
            if (check.expectedCommand) {
                li.dataset.expectedCommand = check.expectedCommand;
            }
            if (check.condition && check.condition.type) {
                li.dataset.conditionType = check.condition.type;
            }

            const symbol = document.createElement('span');
            symbol.className = 'symbol symbol-pending';
            symbol.textContent = '\u25CB'; // Empty circle for pending state

            const text = document.createElement('span');
            text.textContent = check.text || check.message || '';

            li.appendChild(symbol);
            li.appendChild(text);
            qcList.appendChild(li);
        });
    }

    /**
     * Render warnings with symbols
     * @param {Object} step - The step data
     */
    renderWarnings(step) {
        const warningsSection = document.getElementById('warningsSection');
        const warningsList = document.getElementById('warningsList');

        if (!warningsSection || !warningsList) return;

        // Always clear old warnings (including context warnings)
        warningsList.innerHTML = '';

        const warnings = step.warnings || [];
        if (warnings.length === 0) {
            warningsSection.classList.add('hidden');
            return;
        }

        warningsSection.classList.remove('hidden');

        warnings.forEach(warning => {
            const li = document.createElement('li');

            const symbol = document.createElement('span');
            symbol.className = 'symbol ' + this.getSymbolClass(warning.symbol);
            symbol.textContent = warning.symbol || '\u26A0\uFE0F'; // Default to warning

            const text = document.createElement('span');
            text.textContent = warning.text || warning.message || '';

            li.appendChild(symbol);
            li.appendChild(text);
            warningsList.appendChild(li);
        });
    }

    /**
     * Get CSS class for a symbol
     * @param {string} symbol - The symbol character
     * @returns {string} CSS class name
     */
    getSymbolClass(symbol) {
        if (symbol === '\u2705' || symbol === '\u2714' || symbol === '\u2714\uFE0F') {
            return 'symbol-success';
        }
        if (symbol === '\u26A0\uFE0F' || symbol === '\u26A0') {
            return 'symbol-warning';
        }
        if (symbol === '\u26D4' || symbol === '\u274C' || symbol === '\u2716') {
            return 'symbol-error';
        }
        return 'symbol-pending';
    }

    /**
     * Clean up renderer resources
     */
    cleanup() {
        this.stopCarousel();
        if (this.zoomInitialized && this.boundZoomHandlers) {
            const animationArea = document.getElementById('animationArea');
            if (animationArea) {
                animationArea.removeEventListener('wheel', this.boundZoomHandlers.onWheel);
                animationArea.removeEventListener('mousedown', this.boundZoomHandlers.onMouseDown);
                animationArea.removeEventListener('click', this.boundZoomHandlers.onClick);
                animationArea.removeEventListener('dblclick', this.boundZoomHandlers.onDoubleClick);
                animationArea.removeEventListener('touchend', this.boundZoomHandlers.onTouchEnd);
                animationArea.removeEventListener('mouseleave', this.boundZoomHandlers.onMouseLeave);
            }
            window.removeEventListener('mousemove', this.boundZoomHandlers.onMouseMove);
            window.removeEventListener('mouseup', this.boundZoomHandlers.onMouseUp);
            this.zoomInitialized = false;
        }
        this.cancelZoomGestureHint();
        this.hideZoomGestureHint();
        this.currentStep = null;
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.BaseRenderer = BaseRenderer;
}
