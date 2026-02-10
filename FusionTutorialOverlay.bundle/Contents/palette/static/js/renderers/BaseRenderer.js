/**
 * BaseRenderer - Base class for step renderers
 * Defines the interface for rendering tutorial steps
 */

class BaseRenderer {
    constructor(container) {
        this.container = container;
        this.currentStep = null;
    }

    /**
     * Render a step to the UI
     * @param {Object} step - The step data to render
     */
    render(step) {
        this.currentStep = step;
        this.renderStepInfo(step);
        this.renderVisualStep(step);
        this.renderExpandedContent(step);
        this.renderQCChecks(step);
        this.renderWarnings(step);
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

        if (!visualArea || !visualImage || !visualHighlights) return;

        const visualStep = step.visualStep;
        if (!visualStep || !visualStep.image) {
            visualArea.classList.add('hidden');
            return;
        }

        // Show the visual step area
        visualArea.classList.remove('hidden');

        // Set the image source (adjust path - palette is in Contents/palette/, images are in Contents/)
        let imagePath = visualStep.image;
        if (imagePath && !imagePath.startsWith('http') && !imagePath.startsWith('/') && !imagePath.startsWith('../')) {
            imagePath = '../' + imagePath;
        }
        visualImage.src = imagePath;
        visualImage.alt = visualStep.alt || 'Fusion 360 UI Reference';

        // Clear existing highlights
        visualHighlights.innerHTML = '';

        // Add highlights
        if (visualStep.highlights && visualStep.highlights.length > 0) {
            visualStep.highlights.forEach((highlight, index) => {
                const highlightEl = document.createElement('div');
                highlightEl.className = 'visual-highlight' + (highlight.shape === 'circle' ? ' circle' : '');

                // Position and size (percentage-based)
                highlightEl.style.left = highlight.x + '%';
                highlightEl.style.top = highlight.y + '%';
                highlightEl.style.width = highlight.width + '%';
                highlightEl.style.height = highlight.height + '%';

                // Add number indicator
                if (visualStep.highlights.length > 1) {
                    const numberEl = document.createElement('span');
                    numberEl.className = 'visual-highlight-number';
                    numberEl.textContent = (index + 1).toString();
                    highlightEl.appendChild(numberEl);
                }

                // Add label if provided
                if (highlight.label) {
                    const labelEl = document.createElement('span');
                    labelEl.className = 'visual-highlight-label';
                    labelEl.textContent = highlight.label;
                    highlightEl.appendChild(labelEl);
                }

                visualHighlights.appendChild(highlightEl);
            });
        }

        // Set caption
        if (visualCaption) {
            visualCaption.textContent = visualStep.caption || '';
            visualCaption.style.display = visualStep.caption ? 'block' : 'none';
        }
    }

    /**
     * Render basic step information
     * @param {Object} step - The step data
     */
    renderStepInfo(step) {
        const stepNumber = document.getElementById('stepNumber');
        const stepTitle = document.getElementById('stepTitle');
        const stepInstruction = document.getElementById('stepInstruction');
        const stepDetailedText = document.getElementById('stepDetailedText');

        if (stepNumber) {
            stepNumber.textContent = (step.currentIndex || 0) + 1;
        }
        if (stepTitle) {
            stepTitle.textContent = step.title || 'Step';
        }
        if (stepInstruction) {
            stepInstruction.textContent = step.instruction || '';
        }
        if (stepDetailedText) {
            stepDetailedText.textContent = step.detailedText || step.why || 'This step helps you progress in the tutorial.';
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
        if (!expanded) {
            expandedSection.classList.add('hidden');
            return;
        }

        expandedSection.classList.remove('hidden');
        expandedContent.innerHTML = '';

        // Why this matters
        if (expanded.whyThisMatters) {
            const whyDiv = document.createElement('div');
            whyDiv.className = 'expanded-block';
            whyDiv.innerHTML = `<h4>Why This Matters</h4><p>${expanded.whyThisMatters}</p>`;
            expandedContent.appendChild(whyDiv);
        }

        // Tips list
        if (expanded.tips && expanded.tips.length > 0) {
            const tipsDiv = document.createElement('div');
            tipsDiv.className = 'expanded-block';
            tipsDiv.innerHTML = '<h4>Tips</h4>';
            const tipsList = document.createElement('ul');
            tipsList.className = 'tips-list';
            expanded.tips.forEach(tip => {
                const li = document.createElement('li');
                li.textContent = tip;
                tipsList.appendChild(li);
            });
            tipsDiv.appendChild(tipsList);
            expandedContent.appendChild(tipsDiv);
        }

        // Dimensions/Parameters
        if (expanded.dimensions || expanded.parameters) {
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
        if (expanded.referenceImage) {
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
        if (expanded.nextSteps && expanded.nextSteps.length > 0) {
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
        if (expanded.skillsLearned && expanded.skillsLearned.length > 0) {
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

            const symbol = document.createElement('span');
            symbol.className = 'symbol ' + this.getSymbolClass(check.symbol);
            symbol.textContent = check.symbol || '\u2705'; // Default to checkmark

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
        return 'symbol-success';
    }

    /**
     * Clean up renderer resources
     */
    cleanup() {
        this.currentStep = null;
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.BaseRenderer = BaseRenderer;
}
