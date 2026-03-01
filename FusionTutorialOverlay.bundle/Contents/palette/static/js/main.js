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
        retryBtn: null,
        warningFooter: null,
        warningFooterMessage: null,
        warningFooterDismiss: null,
        warningFooterAction: null,
        warningFooterBtn: null,
        workspaceMismatchModal: null,
        workspaceMismatchClose: null,
        workspaceMismatchDismissBtn: null,
        workspaceMismatchTitle: null,
        workspaceMismatchMessage: null,
        workspaceMismatchCurrent: null,
        workspaceMismatchRequired: null,
        workspaceMismatchImage: null,
        workspaceMismatchAnnotation: null,
        workspaceMismatchAnnotationLabel: null
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
        elements.retryBtn = document.getElementById('retryBtn');
        // Warning footer elements
        elements.warningFooter = document.getElementById('warningFooter');
        elements.warningFooterMessage = document.getElementById('warningFooterMessage');
        elements.warningFooterDismiss = document.getElementById('warningFooterDismiss');
        elements.warningFooterAction = document.getElementById('warningFooterAction');
        elements.warningFooterBtn = document.getElementById('warningFooterBtn');
        elements.workspaceMismatchModal = document.getElementById('workspaceMismatchModal');
        elements.workspaceMismatchClose = document.getElementById('workspaceMismatchClose');
        elements.workspaceMismatchDismissBtn = document.getElementById('workspaceMismatchDismissBtn');
        elements.workspaceMismatchTitle = document.getElementById('workspaceMismatchTitle');
        elements.workspaceMismatchMessage = document.getElementById('workspaceMismatchMessage');
        elements.workspaceMismatchCurrent = document.getElementById('workspaceMismatchCurrent');
        elements.workspaceMismatchRequired = document.getElementById('workspaceMismatchRequired');
        elements.workspaceMismatchImage = document.getElementById('workspaceMismatchImage');
        elements.workspaceMismatchAnnotation = document.getElementById('workspaceMismatchAnnotation');
        elements.workspaceMismatchAnnotationLabel = document.getElementById('workspaceMismatchAnnotationLabel');
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
        if (elements.retryBtn) {
            elements.retryBtn.addEventListener('click', retryLoad);
        }

        // Warning footer dismiss button
        if (elements.warningFooterDismiss) {
            elements.warningFooterDismiss.addEventListener('click', hideWarningFooter);
        }

        if (elements.workspaceMismatchClose) {
            elements.workspaceMismatchClose.addEventListener('click', hideWorkspaceMismatchModal);
        }
        if (elements.workspaceMismatchDismissBtn) {
            elements.workspaceMismatchDismissBtn.addEventListener('click', hideWorkspaceMismatchModal);
        }
        if (elements.workspaceMismatchModal) {
            elements.workspaceMismatchModal.addEventListener('click', (e) => {
                if (e.target === elements.workspaceMismatchModal) {
                    hideWorkspaceMismatchModal();
                }
            });
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
        }
    }

    /**
     * Wait for Fusion bridge to be available
     */
    function waitForBridge() {
        const maxAttempts = 20;
        let attempts = 0;

        function check() {
            attempts++;

            if (window.adsk && typeof window.adsk.fusionSendData === 'function') {
                bridgeReady = true;
                onBridgeReady();
            } else if (attempts < maxAttempts) {
                setTimeout(check, 100);
            } else {
                console.warn('Fusion bridge not available');
                showError('Fusion bridge unavailable. Open this palette from the Fusion 360 add-in and click Retry.');
            }
        }

        check();
    }

    // Track whether ready has received a response.
    let receivedResponse = false;

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

        // Send initial ready once; manual retries happen via Retry button.
        sendReadyWithRetry();
    }

    /**
     * Send ready message with retry logic
     */
    function sendReadyWithRetry() {
        console.log('TutorialOverlay: Sending ready message to Python');
        sendToBridge({ action: 'ready' });
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
                    if (payload.workspaceMismatchFeedback) {
                        showWorkspaceMismatchModal(payload.workspaceMismatchFeedback);
                    } else {
                        hideWorkspaceMismatchModal();
                    }
                    break;

                case 'error':
                    showError(payload.message);
                    break;

                case 'assets':
                    handleAssets(payload.assets);
                    break;

                case 'runtimeInfo':
                    console.log(
                        'TutorialOverlay runtimeInfo:',
                        `build=${payload.buildStamp}`,
                        `path=${payload.scriptPath}`,
                        `coreModulesLoaded=${payload.coreModulesLoaded}`,
                        `pathMatchesExpected=${payload.pathMatchesExpected}`,
                        `headerHash=${payload.headerHash || 'n/a'}`
                    );
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
                    // Show dismissible warning - does not block navigation
                    showWarningFooter(
                        getContextWarningMessage(payload.mismatch),
                        'warning',
                        { autoHide: 5000 }
                    );
                    break;

                case 'contextWarning':
                    // Show dismissible warning - does not block navigation
                    showWarningFooter(payload.message || getContextWarningMessage(payload.mismatch), 'warning', {
                        autoHide: 5000
                    });
                    break;

                case 'contextResolved':
                    // User switched to the correct environment — dismiss warning
                    hideWarningFooter();
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
     * Show a non-blocking modal with workspace mismatch guidance.
     */
    function showWorkspaceMismatchModal(feedback) {
        if (!feedback || !elements.workspaceMismatchModal) return;

        if (elements.workspaceMismatchTitle && feedback.title) {
            elements.workspaceMismatchTitle.textContent = feedback.title;
        }
        if (elements.workspaceMismatchMessage) {
            elements.workspaceMismatchMessage.textContent = feedback.message ||
                'This step requires a different workspace. You can close this and continue.';
        }
        if (elements.workspaceMismatchCurrent) {
            elements.workspaceMismatchCurrent.textContent = feedback.currentWorkspace || 'Unknown';
        }
        if (elements.workspaceMismatchRequired) {
            elements.workspaceMismatchRequired.textContent = feedback.requiredWorkspace || 'Required';
        }

        if (elements.workspaceMismatchImage) {
            const src = feedback.referenceImageSrc || '../assets/UI Images/Solid/Solid_0.png';
            elements.workspaceMismatchImage.src = encodeURI(src);
        }

        applyWorkspaceMismatchAnnotation(feedback.annotation);
        elements.workspaceMismatchModal.classList.remove('hidden');
    }

    function hideWorkspaceMismatchModal() {
        if (elements.workspaceMismatchModal) {
            elements.workspaceMismatchModal.classList.add('hidden');
        }
    }

    function applyWorkspaceMismatchAnnotation(annotation) {
        if (!elements.workspaceMismatchAnnotation) return;

        if (!annotation || !annotation.position) {
            elements.workspaceMismatchAnnotation.classList.add('hidden');
            return;
        }

        const pos = annotation.position;
        elements.workspaceMismatchAnnotation.style.left = `${Number(pos.x || 0)}%`;
        elements.workspaceMismatchAnnotation.style.top = `${Number(pos.y || 0)}%`;
        elements.workspaceMismatchAnnotation.style.width = `${Number(pos.width || 0)}%`;
        elements.workspaceMismatchAnnotation.style.height = `${Number(pos.height || 0)}%`;

        if (elements.workspaceMismatchAnnotationLabel) {
            elements.workspaceMismatchAnnotationLabel.textContent = annotation.label || 'Workspace selector';
        }

        elements.workspaceMismatchAnnotation.classList.remove('hidden');
    }

    /**
     * Handle completion event from Fusion 360
     */
    function handleCompletionEvent(event) {
        console.log('Completion event received:', event);

        if (event.eventType === 'command_started') {
            // User clicked a tool - transition matching items to "checking" (pulsing)
            markQCChecksAsChecking(event);
        } else {
            // Command completed - transition matching items to "completed" (green check)
            updateQCChecksFromEvent(event);
        }

        // Request viewport capture for visual feedback on feature completion
        const captureEvents = [
            'extrude_created', 'fillet_created', 'sketch_finished',
            'chamfer_created', 'revolve_created', 'shell_created', 'sweep_created'
        ];
        if (captureEvents.includes(event.eventType)) {
            requestViewportCapture();
        }
    }

    /**
     * Mark QC check items as "checking" (in-progress) when a command starts.
     * Matches event's commandId to items' data-expected-command attribute.
     */
    function markQCChecksAsChecking(event) {
        const qcList = document.getElementById('qcList');
        if (!qcList) return;

        const commandId = (event.additionalInfo && event.additionalInfo.commandId) || '';
        if (!commandId) return;

        const items = qcList.querySelectorAll('li');
        let matchedExpectedCommand = false;
        const pendingExpectedCommands = [];

        items.forEach(item => {
            // Only transition pending items
            if (!item.classList.contains('pending')) return;

            const expectedCommand = item.dataset.expectedCommand;
            if (expectedCommand) {
                pendingExpectedCommands.push(expectedCommand);
            }
            if (expectedCommand && expectedCommand === commandId) {
                matchedExpectedCommand = true;
                item.classList.remove('pending');
                item.classList.add('checking');

                // Update symbol to filled circle (pulsing)
                const symbol = item.querySelector('.symbol');
                if (symbol) {
                    symbol.textContent = '\u25CF'; // Filled circle
                    symbol.className = 'symbol symbol-checking';
                }
            }
        });

        // Non-blocking feedback when the user starts a command that doesn't match
        // any expected command documented in the current step's qcChecks.
        if (!matchedExpectedCommand && pendingExpectedCommands.length > 0) {
            const ignorePrefix = ['Select', 'Pan', 'Orbit', 'Zoom'];
            const shouldIgnore = ignorePrefix.some(prefix => commandId.startsWith(prefix));
            if (!shouldIgnore) {
                const expectedPreview = pendingExpectedCommands.slice(0, 3).join(', ');
                const more = pendingExpectedCommands.length > 3 ? ` (+${pendingExpectedCommands.length - 3} more)` : '';
                showWarningFooter(
                    `This step expects command: ${expectedPreview}${more}. You started: ${commandId}.`,
                    'warning',
                    { autoHide: 5000 }
                );
            }
        }
    }

    /**
     * Update QC check items based on completion event.
     * Matches by data-expected-command first, then falls back to text-based matching.
     *
     * Handles two kinds of events:
     * - Feature events (extrude_created, fillet_created, etc.) from timeline changes
     * - command_terminated events for tools that don't create timeline items (sketch tools)
     */
    function updateQCChecksFromEvent(event) {
        const qcList = document.getElementById('qcList');
        if (!qcList) return;

        const commandId = (event.additionalInfo && event.additionalInfo.commandId) || '';

        // Map feature event types to the command IDs that produce them
        const eventToCommandMap = {
            'sketch_created': ['SketchCreate', 'SketchActivate'],
            'sketch_finished': ['FinishSketch'],
            'extrude_created': ['Extrude'],
            'fillet_created': ['FilletEdge'],
            'chamfer_created': ['ChamferEdge'],
            'revolve_created': ['Revolve'],
            'sweep_created': ['Sweep'],
            'shell_created': ['Shell']
        };
        const matchingCommands = eventToCommandMap[event.eventType] || [];

        // For command_terminated events (sketch tools that don't add timeline items),
        // complete the first pending/checking item whose expectedCommand matches
        const isCommandTerminated = event.eventType === 'command_terminated';
        let completedOneForTerminated = false;

        const items = qcList.querySelectorAll('li');
        items.forEach(item => {
            // Skip already completed items
            if (item.classList.contains('completed')) return;

            // For command_terminated, only complete one item at a time for progressive feedback
            if (isCommandTerminated && completedOneForTerminated) return;

            let shouldComplete = false;
            const expectedCommand = item.dataset.expectedCommand;

            // Primary: match by data-expected-command attribute
            if (expectedCommand) {
                if (commandId && expectedCommand === commandId) {
                    shouldComplete = true;
                } else if (matchingCommands.includes(expectedCommand)) {
                    shouldComplete = true;
                }
            }

            // Fallback: text-based matching for items without expectedCommand
            if (!shouldComplete && !expectedCommand) {
                const text = item.textContent.toLowerCase();
                if (event.eventType === 'sketch_created' && text.includes('sketch')) {
                    shouldComplete = true;
                } else if (event.eventType === 'sketch_finished' && (text.includes('finish') || text.includes('constrained'))) {
                    shouldComplete = true;
                } else if (event.eventType === 'extrude_created' && text.includes('extru')) {
                    shouldComplete = true;
                } else if (event.eventType === 'fillet_created' && text.includes('fillet')) {
                    shouldComplete = true;
                } else if (event.eventType === 'revolve_created' && text.includes('revolve')) {
                    shouldComplete = true;
                } else if (event.eventType === 'sweep_created' && text.includes('sweep')) {
                    shouldComplete = true;
                } else if (event.eventType === 'body_created' && text.includes('body')) {
                    shouldComplete = true;
                }
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

                if (isCommandTerminated) {
                    completedOneForTerminated = true;
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
        receivedResponse = false;
        sendToBridge({ action: 'ready' });
    }

    /**
     * Run in standalone mode for testing without Fusion
     */
    function runStandaloneMode() {
        console.warn('Standalone mode disabled for cloud-only tutorial loading.');
        showError('Standalone mode is disabled. Open from Fusion 360 add-in to fetch the latest tutorial.');
    }

    /**
     * Load a tutorial in standalone mode (no Fusion bridge)
     */
    function loadStandaloneTutorial() {
        showError('Standalone mode is disabled. Open from Fusion 360 add-in to fetch the latest tutorial.');
    }

    // Expose functions globally for use by renderers
    window.sendToBridge = sendToBridge;
    window.requestViewportCapture = requestViewportCapture;
    window.showWarningFooter = showWarningFooter;
    window.hideWarningFooter = hideWarningFooter;
    window.showWorkspaceMismatchModal = showWorkspaceMismatchModal;
    window.hideWorkspaceMismatchModal = hideWorkspaceMismatchModal;

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
