/**
 * Main - Entry point for the tutorial palette UI
 * Handles Fusion bridge communication and initialization
 */

(function() {
    'use strict';

    // State
    let stepper = null;
    let renderer = null;
    let redirectRenderer = null;
    let bridgeReady = false;
    let pendingMessages = [];
    let loadedAssets = {};  // Store preloaded assets

    // DOM Elements
    const elements = {
        loadingState: null,
        errorState: null,
        tutorialContent: null,
        navigation: null,
        stepNavigator: null,
        errorMessage: null,
        prevBtn: null,
        nextBtn: null,
        replayBtn: null,
        retryBtn: null,
        warningFooter: null,
        warningFooterMessage: null,
        warningFooterDismiss: null,
        warningFooterAction: null,
        warningFooterBtn: null
    };

    /**
     * Initialize the application
     */
    function init() {
        console.log('TutorialOverlay: init() called');

        // Cache DOM elements
        cacheElements();
        console.log('TutorialOverlay: DOM elements cached');

        // Initialize stepper and renderer
        initStepper();
        console.log('TutorialOverlay: Stepper initialized');

        // Set up event listeners
        setupEventListeners();
        console.log('TutorialOverlay: Event listeners set up');

        // Wait for Fusion bridge
        waitForBridge();
        console.log('TutorialOverlay: Waiting for bridge...');
    }

    /**
     * Cache DOM elements
     */
    function cacheElements() {
        elements.loadingState = document.getElementById('loadingState');
        elements.errorState = document.getElementById('errorState');
        elements.tutorialContent = document.getElementById('tutorialContent');
        elements.navigation = document.getElementById('navigation');
        elements.stepNavigator = document.getElementById('stepNavigator');
        elements.errorMessage = document.getElementById('errorMessage');
        elements.prevBtn = document.getElementById('prevBtn');
        elements.nextBtn = document.getElementById('nextBtn');
        elements.replayBtn = document.getElementById('replayBtn');
        elements.retryBtn = document.getElementById('retryBtn');
        // Warning footer elements
        elements.warningFooter = document.getElementById('warningFooter');
        elements.warningFooterMessage = document.getElementById('warningFooterMessage');
        elements.warningFooterDismiss = document.getElementById('warningFooterDismiss');
        elements.warningFooterAction = document.getElementById('warningFooterAction');
        elements.warningFooterBtn = document.getElementById('warningFooterBtn');
    }

    /**
     * Initialize stepper with animated renderer
     */
    function initStepper() {
        try {
            // Create animated renderer
            renderer = new AnimatedRenderer(document.getElementById('tutorialContent'));
            console.log('TutorialOverlay: AnimatedRenderer created');

            // Create redirect renderer (optional - may not exist)
            if (typeof RedirectRenderer !== 'undefined') {
                redirectRenderer = new RedirectRenderer(document.getElementById('app'));
                console.log('TutorialOverlay: RedirectRenderer created');
            }

            // Create stepper with step change callback
            stepper = new Stepper({
                onStepChange: handleStepChange
            });
            console.log('TutorialOverlay: Stepper created');

            stepper.setRenderer(renderer);
            if (redirectRenderer) {
                stepper.setRedirectRenderer(redirectRenderer);
            }

            // Make assets available globally for renderers
            window.loadedAssets = loadedAssets;
        } catch (e) {
            console.error('TutorialOverlay: Error in initStepper:', e);
        }
    }

    /**
     * Set up event listeners
     */
    function setupEventListeners() {
        // Navigation buttons
        if (elements.prevBtn) {
            elements.prevBtn.addEventListener('click', () => stepper.prev());
        }
        if (elements.nextBtn) {
            elements.nextBtn.addEventListener('click', () => stepper.next());
        }
        if (elements.replayBtn) {
            elements.replayBtn.addEventListener('click', () => stepper.replay());
        }
        if (elements.retryBtn) {
            elements.retryBtn.addEventListener('click', retryLoad);
        }

        // Warning footer dismiss button
        if (elements.warningFooterDismiss) {
            elements.warningFooterDismiss.addEventListener('click', hideWarningFooter);
        }

        // Viewport screenshot refresh button
        const refreshViewportBtn = document.getElementById('refreshViewportBtn');
        if (refreshViewportBtn) {
            refreshViewportBtn.addEventListener('click', requestViewportCapture);
        }

        // Keyboard navigation (when palette has focus)
        document.addEventListener('keydown', handleKeydown);
    }

    /**
     * Handle keyboard navigation
     */
    function handleKeydown(e) {
        switch (e.key) {
            case 'ArrowLeft':
                stepper.prev();
                break;
            case 'ArrowRight':
                stepper.next();
                break;
            case 'r':
            case 'R':
                stepper.replay();
                break;
        }
    }

    /**
     * Wait for Fusion bridge to be available
     */
    function waitForBridge() {
        const maxAttempts = 20;  // Reduced from 50 for faster fallback (2 seconds)
        let attempts = 0;

        function check() {
            attempts++;

            if (window.adsk && typeof window.adsk.fusionSendData === 'function') {
                bridgeReady = true;
                onBridgeReady();
            } else if (attempts < maxAttempts) {
                setTimeout(check, 100);
            } else {
                // Bridge not available - run in standalone mode for testing
                console.warn('Fusion bridge not available, running in standalone test mode');
                runStandaloneMode();
            }
        }

        check();
    }

    // Track if we've received a response from Python
    let receivedResponse = false;
    let readyRetryCount = 0;
    const MAX_READY_RETRIES = 5;
    const READY_RETRY_INTERVAL = 500; // ms

    /**
     * Called when Fusion bridge is ready
     */
    function onBridgeReady() {
        console.log('TutorialOverlay: Bridge is ready!');

        // Set up message handler
        window.fusionJavaScriptHandler = {
            handle: function(action, data) {
                console.log('TutorialOverlay: Received from Python:', action);
                receivedResponse = true;
                return handleBridgeMessage(action, data);
            }
        };

        // Send ready message to Python with retry logic
        sendReadyWithRetry();
    }

    /**
     * Send ready message with retry logic
     */
    function sendReadyWithRetry() {
        console.log('TutorialOverlay: Sending ready message to Python (attempt ' + (readyRetryCount + 1) + ')');
        sendToBridge({ action: 'ready' });

        // Set up retry if no response received
        setTimeout(() => {
            if (!receivedResponse && readyRetryCount < MAX_READY_RETRIES) {
                readyRetryCount++;
                console.log('TutorialOverlay: No response received, retrying...');
                sendReadyWithRetry();
            } else if (!receivedResponse) {
                console.warn('TutorialOverlay: No response after retries, falling back to standalone mode');
                runStandaloneMode();
            }
        }, READY_RETRY_INTERVAL);
    }

    /**
     * Handle messages from Python bridge
     */
    function handleBridgeMessage(action, data) {
        console.log('Bridge message:', action, data);

        try {
            const payload = typeof data === 'string' ? JSON.parse(data) : data;

            switch (payload.action) {
                case 'tutorialLoaded':
                case 'updateStep':
                    // Exit redirect mode if active
                    if (stepper.isInRedirectMode()) {
                        stepper.exitRedirectMode();
                    }
                    // Clear any context warnings from previous navigation attempts
                    clearContextWarnings();
                    // Clear viewport screenshot from previous step
                    clearViewportPreview();
                    showTutorial();
                    stepper.loadStep(payload.step);
                    break;

                case 'replayStep':
                    stepper.replay();
                    break;

                case 'error':
                    showError(payload.message);
                    break;

                case 'assets':
                    handleAssets(payload.assets);
                    break;

                // Consent system
                case 'consentRequired':
                    // Show consent dialog (tutorial already loaded in background)
                    showConsentDialog(payload.firstRun);
                    break;

                // Redirect system
                case 'redirectStep':
                    handleRedirectStep(payload.step);
                    break;

                case 'redirectComplete':
                    handleRedirectComplete(payload.resolvedContext, payload.pendingStepIndex);
                    break;

                case 'askRedirect':
                    showAskRedirectDialog(payload.mismatch, payload.targetIndex);
                    break;

                case 'contextWarning':
                    // Use persistent footer instead of blocking warning
                    showWarningFooter(payload.message || getContextWarningMessage(payload.mismatch), 'warning', {
                        showAction: true,
                        actionLabel: 'Show me how',
                        onAction: () => {
                            sendToBridge({ action: 'showRedirectHelp' });
                        }
                    });
                    break;

                case 'completionEvent':
                    handleCompletionEvent(payload.event);
                    break;

                case 'viewportCaptured':
                    handleViewportCaptured(payload);
                    break;

                case 'qcResults':
                    handleQCResults(payload.results);
                    break;

                case 'designState':
                    handleDesignState(payload.state);
                    break;

                case 'redirectSkipped':
                    // Redirect was skipped, continue with normal flow
                    if (stepper.isInRedirectMode()) {
                        stepper.exitRedirectMode();
                    }
                    break;

                default:
                    console.warn('Unknown action:', payload.action);
            }
        } catch (e) {
            console.error('Error handling bridge message:', e);
        }

        return '{"status": "ok"}';
    }

    /**
     * Send message to Python bridge
     */
    function sendToBridge(data) {
        if (bridgeReady && window.adsk) {
            const jsonStr = JSON.stringify(data);
            console.log('TutorialOverlay: Sending to bridge:', jsonStr);
            // Fusion expects: fusionSendData(action, data) - two params
            window.adsk.fusionSendData('cycleEvent', jsonStr);
        } else {
            pendingMessages.push(data);
        }
    }

    /**
     * Handle step change from stepper
     */
    function handleStepChange(action, index) {
        if (action === 'goToStep') {
            sendToBridge({ action: 'goToStep', index: index });
        } else if (action === 'skipRedirect') {
            // User clicked skip during redirect
            sendToBridge({ action: 'skipRedirect' });
        } else {
            sendToBridge({ action: action });
        }
    }

    /**
     * Handle assets from Python
     */
    function handleAssets(assets) {
        // Store assets globally
        loadedAssets = assets;
        window.loadedAssets = assets;

        // Update cursor image if provided
        if (assets.cursor) {
            const cursorImg = document.querySelector('#cursorElement img');
            if (cursorImg) {
                cursorImg.src = assets.cursor;
            }
        }
    }

    /**
     * Show consent dialog
     */
    function showConsentDialog(firstRun) {
        if (elements.loadingState) {
            elements.loadingState.classList.add('hidden');
        }

        // Use the consentDialog module
        if (window.consentDialog) {
            window.consentDialog.show({
                firstRun: firstRun,
                onConsent: handleConsentChoice
            });
        } else {
            // Fallback - show embedded consent overlay
            const overlay = document.getElementById('consentOverlay');
            if (overlay) {
                overlay.classList.remove('hidden');
                setupConsentListeners();
            }
        }
    }

    /**
     * Setup consent dialog button listeners
     */
    function setupConsentListeners() {
        const yesBtn = document.getElementById('consentYes');
        const noBtn = document.getElementById('consentNo');

        if (yesBtn) {
            yesBtn.onclick = () => handleConsentChoice('ASK');
        }
        if (noBtn) {
            noBtn.onclick = () => handleConsentChoice('OFF');
        }
    }

    /**
     * Handle consent choice
     */
    function handleConsentChoice(mode) {
        // Hide consent overlay
        const overlay = document.getElementById('consentOverlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }

        // Send consent to Python
        sendToBridge({ action: 'setConsent', mode: mode });

        // Show loading while tutorial loads
        if (elements.loadingState) {
            elements.loadingState.classList.remove('hidden');
        }
    }

    /**
     * Handle redirect step
     */
    function handleRedirectStep(step) {
        const pendingIndex = step.originalStepIndex || 0;

        // Enter redirect mode
        stepper.enterRedirectMode(step, pendingIndex);

        // Hide normal content, show redirect card
        if (elements.tutorialContent) {
            elements.tutorialContent.classList.add('hidden');
        }
    }

    /**
     * Handle redirect complete (context resolved)
     */
    function handleRedirectComplete(resolvedContext, pendingStepIndex) {
        // Show resolved animation
        stepper.onContextResolved(resolvedContext);

        // Auto-advance after a brief delay
        setTimeout(() => {
            stepper.exitRedirectMode(true);

            // Request the pending step
            if (pendingStepIndex !== undefined && pendingStepIndex !== null) {
                sendToBridge({ action: 'goToStep', index: pendingStepIndex });
            }
        }, 1000);
    }

    /**
     * Show ask redirect dialog (ASK mode) - now uses persistent footer
     */
    function showAskRedirectDialog(mismatch, targetIndex) {
        let message = 'Wrong environment detected.';
        if (mismatch && mismatch.mismatches && mismatch.mismatches.length > 0) {
            const m = mismatch.mismatches[0];
            message = `You're in ${m.current} mode, but this step requires ${m.required} mode.`;
        }

        // Use persistent warning footer instead of blocking overlay
        showWarningFooter(message, 'warning', {
            showAction: true,
            actionLabel: 'Show me how',
            onAction: () => {
                sendToBridge({ action: 'showRedirectHelp', targetIndex: targetIndex });
            }
        });

        // Also keep the old overlay for backwards compatibility (hidden by default)
        const overlay = document.getElementById('askRedirectOverlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    }

    /**
     * Clear all context warnings
     */
    function clearContextWarnings() {
        const warningsList = document.getElementById('warningsList');
        if (warningsList) {
            const contextWarnings = warningsList.querySelectorAll('.context-warning');
            contextWarnings.forEach(el => el.remove());

            // Hide warnings section if empty
            const warningsSection = document.getElementById('warningsSection');
            if (warningsSection && warningsList.children.length === 0) {
                warningsSection.classList.add('hidden');
            }
        }
    }

    /**
     * Show context warning (OFF mode or after skip) - now uses persistent footer
     */
    function showContextWarning(mismatch, customMessage) {
        const message = customMessage ||
                       (mismatch && mismatch.mismatches && mismatch.mismatches[0]?.message) ||
                       'Context mismatch detected';
        showWarningFooter(message + ' Click Next to retry.', 'warning');
    }

    /**
     * Get context warning message from mismatch data
     */
    function getContextWarningMessage(mismatch) {
        if (mismatch && mismatch.mismatches && mismatch.mismatches.length > 0) {
            const m = mismatch.mismatches[0];
            return `You're in ${m.current} mode, but this step requires ${m.required} mode.`;
        }
        return 'Context mismatch detected. Please switch to the correct environment.';
    }

    /**
     * Show warning footer with message
     * @param {string} message - The warning message to display
     * @param {string} type - 'warning', 'error', or 'info'
     * @param {Object} options - Optional settings
     */
    function showWarningFooter(message, type = 'warning', options = {}) {
        if (!elements.warningFooter) return;

        // Set message
        if (elements.warningFooterMessage) {
            elements.warningFooterMessage.textContent = message;
        }

        // Set type class
        elements.warningFooter.classList.remove('error', 'info');
        if (type === 'error') {
            elements.warningFooter.classList.add('error');
        } else if (type === 'info') {
            elements.warningFooter.classList.add('info');
        }

        // Handle action button
        if (options.showAction && elements.warningFooterAction && elements.warningFooterBtn) {
            elements.warningFooterAction.classList.remove('hidden');
            elements.warningFooterBtn.textContent = options.actionLabel || 'Take action';

            // Remove old listener and add new one
            const newBtn = elements.warningFooterBtn.cloneNode(true);
            elements.warningFooterBtn.parentNode.replaceChild(newBtn, elements.warningFooterBtn);
            elements.warningFooterBtn = newBtn;

            if (options.onAction) {
                elements.warningFooterBtn.addEventListener('click', () => {
                    hideWarningFooter();
                    options.onAction();
                });
            }
        } else if (elements.warningFooterAction) {
            elements.warningFooterAction.classList.add('hidden');
        }

        // Show the footer
        elements.warningFooter.classList.remove('hidden');

        // Auto-hide after delay if specified
        if (options.autoHide) {
            setTimeout(hideWarningFooter, options.autoHide);
        }
    }

    /**
     * Hide warning footer
     */
    function hideWarningFooter() {
        if (elements.warningFooter) {
            elements.warningFooter.classList.add('hidden');
        }
    }

    /**
     * Handle completion event from Fusion 360
     */
    function handleCompletionEvent(event) {
        console.log('Completion event received:', event);

        // Update QC checks based on the event
        updateQCChecksFromEvent(event);

        // Request viewport capture for visual feedback
        if (event.eventType === 'extrude_created' ||
            event.eventType === 'fillet_created' ||
            event.eventType === 'sketch_finished') {
            requestViewportCapture();
        }
    }

    /**
     * Update QC check items based on completion event
     */
    function updateQCChecksFromEvent(event) {
        const qcList = document.getElementById('qcList');
        if (!qcList) return;

        const items = qcList.querySelectorAll('li');
        items.forEach(item => {
            const text = item.textContent.toLowerCase();

            // Match event types to QC check text
            let shouldComplete = false;

            if (event.eventType === 'sketch_created' && text.includes('sketch')) {
                shouldComplete = true;
            } else if (event.eventType === 'sketch_finished' && text.includes('finish')) {
                shouldComplete = true;
            } else if (event.eventType === 'extrude_created' && text.includes('extru')) {
                shouldComplete = true;
            } else if (event.eventType === 'fillet_created' && text.includes('fillet')) {
                shouldComplete = true;
            } else if (event.eventType === 'body_created' && text.includes('body')) {
                shouldComplete = true;
            }

            if (shouldComplete) {
                item.classList.remove('pending', 'checking');
                item.classList.add('completed');

                // Update symbol to checkmark
                const symbol = item.querySelector('.symbol');
                if (symbol) {
                    symbol.textContent = '\u2705';
                    symbol.className = 'symbol symbol-success';
                }
            }
        });
    }

    /**
     * Request viewport screenshot capture
     */
    function requestViewportCapture() {
        const timestamp = Date.now();
        sendToBridge({
            action: 'captureViewport',
            filename: `viewport_${timestamp}.png`
        });
    }

    /**
     * Handle viewport captured response
     */
    function handleViewportCaptured(payload) {
        if (payload.success && payload.imageData) {
            console.log('Viewport captured with base64 data');
            updateViewportPreview(payload.imageData);
        } else if (payload.success && payload.path) {
            // Fallback for file path (may not work in Qt WebEngine sandbox)
            console.log('Viewport captured:', payload.path);
            updateViewportPreview('../' + payload.path + '?' + Date.now());
        }
    }

    /**
     * Update viewport preview in visual step area using base64 data URL
     */
    function updateViewportPreview(imageDataUrl) {
        const container = document.getElementById('viewportScreenshot');
        const img = document.getElementById('viewportScreenshotImg');
        const visualArea = document.getElementById('visualStepArea');

        if (container && img) {
            img.src = imageDataUrl;
            container.classList.remove('hidden');
        }

        if (visualArea) {
            visualArea.classList.remove('hidden');
        }
    }

    /**
     * Clear viewport preview (called on step change)
     */
    function clearViewportPreview() {
        const container = document.getElementById('viewportScreenshot');
        const img = document.getElementById('viewportScreenshotImg');

        if (container) {
            container.classList.add('hidden');
        }
        if (img) {
            img.src = '';
        }
    }

    /**
     * Handle QC results from bridge
     */
    function handleQCResults(results) {
        const qcList = document.getElementById('qcList');
        if (!qcList || !results) return;

        results.forEach((result, index) => {
            const item = qcList.children[index];
            if (item) {
                item.classList.remove('pending', 'checking');
                item.classList.add(result.passed ? 'completed' : 'failed');

                const symbol = item.querySelector('.symbol');
                if (symbol) {
                    symbol.textContent = result.passed ? '\u2705' : '\u274C';
                    symbol.className = 'symbol ' + (result.passed ? 'symbol-success' : 'symbol-error');
                }
            }
        });
    }

    /**
     * Handle design state from bridge
     */
    function handleDesignState(state) {
        console.log('Design state:', state);
        // Could update UI indicators based on state
    }

    /**
     * Show tutorial content
     */
    function showTutorial() {
        if (elements.loadingState) elements.loadingState.classList.add('hidden');
        if (elements.errorState) elements.errorState.classList.add('hidden');
        if (elements.tutorialContent) elements.tutorialContent.classList.remove('hidden');
        if (elements.navigation) elements.navigation.classList.remove('hidden');
        if (elements.stepNavigator) elements.stepNavigator.classList.remove('hidden');
    }

    /**
     * Show error state
     */
    function showError(message) {
        if (elements.loadingState) elements.loadingState.classList.add('hidden');
        if (elements.tutorialContent) elements.tutorialContent.classList.add('hidden');
        if (elements.navigation) elements.navigation.classList.add('hidden');
        if (elements.errorState) elements.errorState.classList.remove('hidden');
        if (elements.errorMessage) elements.errorMessage.textContent = message || 'An error occurred';
    }

    /**
     * Retry loading
     */
    function retryLoad() {
        if (elements.errorState) elements.errorState.classList.add('hidden');
        if (elements.loadingState) elements.loadingState.classList.remove('hidden');
        sendToBridge({ action: 'ready' });
    }

    /**
     * Run in standalone mode for testing without Fusion
     */
    function runStandaloneMode() {
        console.log('Running in standalone test mode');

        // Hide loading immediately
        if (elements.loadingState) {
            elements.loadingState.classList.add('hidden');
        }

        // Load test tutorial directly
        const testTutorial = {
            tutorialId: 'test',
            title: 'Test Tutorial (Standalone Mode)',
            steps: [
                {
                    stepId: 'step1',
                    stepNumber: 1,
                    title: 'Welcome to the Tutorial',
                    instruction: 'This is a test step running in standalone mode (no Fusion 360 connection).',
                    detailedText: 'The palette is running without the Fusion 360 bridge. This allows you to test the UI independently.',
                    qcChecks: [
                        { symbol: '\u2705', text: 'UI loaded successfully' },
                        { symbol: '\u2705', text: 'Animations are working' }
                    ],
                    warnings: [
                        { symbol: '\u26A0\uFE0F', text: 'Running in standalone test mode' }
                    ],
                    uiAnimations: [
                        { type: 'move', from: { x: 20, y: 30 }, to: { x: 80, y: 70 }, duration: 800 },
                        { type: 'click', at: { x: 80, y: 70 } },
                        { type: 'pause', duration: 500 }
                    ],
                    currentIndex: 0,
                    totalSteps: 3,
                    tutorialTitle: 'Test Tutorial'
                },
                {
                    stepId: 'step2',
                    stepNumber: 2,
                    title: 'Cursor Animation Demo',
                    instruction: 'Watch the cursor demonstrate a drag operation.',
                    detailedText: 'This step shows how cursor animations can guide users through drag operations.',
                    qcChecks: [],
                    warnings: [],
                    uiAnimations: [
                        { type: 'drag', from: { x: 25, y: 50 }, to: { x: 75, y: 50 }, duration: 1000 }
                    ],
                    currentIndex: 1,
                    totalSteps: 3,
                    tutorialTitle: 'Test Tutorial'
                },
                {
                    stepId: 'step3',
                    stepNumber: 3,
                    title: 'Complete!',
                    instruction: 'You have completed the standalone test tutorial.',
                    detailedText: 'To test with Fusion 360, install the add-in and run it from within Fusion.',
                    qcChecks: [
                        { symbol: '\u2705', text: 'Tutorial completed successfully' }
                    ],
                    warnings: [],
                    uiAnimations: [
                        { type: 'click', at: { x: 50, y: 50 } }
                    ],
                    currentIndex: 2,
                    totalSteps: 3,
                    tutorialTitle: 'Test Tutorial'
                }
            ]
        };

        // Minimal delay for UI initialization
        setTimeout(() => {
            // Override step change handler for standalone mode
            stepper.onStepChange = (action, index) => {
                let newIndex = stepper.currentIndex;

                if (action === 'next' && newIndex < testTutorial.steps.length - 1) {
                    newIndex++;
                } else if (action === 'prev' && newIndex > 0) {
                    newIndex--;
                } else if (action === 'goToStep') {
                    newIndex = index;
                }

                const step = testTutorial.steps[newIndex];
                step.currentIndex = newIndex;
                step.totalSteps = testTutorial.steps.length;
                step.tutorialTitle = testTutorial.title;
                stepper.loadStep(step);
            };

            // Load first step
            showTutorial();
            const firstStep = testTutorial.steps[0];
            firstStep.currentIndex = 0;
            firstStep.totalSteps = testTutorial.steps.length;
            firstStep.tutorialTitle = testTutorial.title;
            stepper.loadStep(firstStep);

        }, 100);
    }

    // Expose functions globally for use by renderers
    window.sendToBridge = sendToBridge;
    window.requestViewportCapture = requestViewportCapture;
    window.showWarningFooter = showWarningFooter;
    window.hideWarningFooter = hideWarningFooter;

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
