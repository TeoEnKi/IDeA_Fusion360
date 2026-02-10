/**
 * StaticRenderer - Renders static step content without animations
 * Extends BaseRenderer
 */

class StaticRenderer extends BaseRenderer {
    constructor(container) {
        super(container);
    }

    /**
     * Render a step statically (no animations)
     * @param {Object} step - The step data to render
     */
    render(step) {
        super.render(step);

        // Hide animation area for static rendering
        const animationArea = document.getElementById('animationArea');
        if (animationArea) {
            animationArea.classList.add('hidden');
        }
    }

    /**
     * Replay is a no-op for static renderer
     */
    replay() {
        // Static renderer doesn't have animations to replay
        console.log('StaticRenderer: replay called (no-op)');
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.StaticRenderer = StaticRenderer;
}
