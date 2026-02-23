# Visual Step Image Carousel with Per-Image Animations

Auto-switching image carousel for visual steps. Images cycle every 5 seconds. Circle indicator buttons allow manual selection; auto-cycling resumes 5 seconds after manual interaction.

## What Changed (Context)

**A) Animations are now under images (paired with screenshots)**

| | Location |
|---|---|
| **Before** | `step.uiAnimations[]` |
| **Now** | `step.visualStep.images[i].uiAnimations[]` |

So the tutorial player (and future AI generator) can attach the exact animation sequence that matches the screenshot being shown.

Reference: [Fusion360_AI_Tutorial_Software_ArchitecturePlan_refined.md](file:///c:/Users/teoen/GitHub/IDeA_Fusion360/Fusion360_AI_Tutorial_Software_ArchitecturePlan_refined.md#L95-L126)

> [!WARNING]
> Step-level `step.uiAnimations[]` is now **deprecated**. The renderer will still fall back to it for legacy manifests, but new/AI-generated tutorials must place animations under `visualStep.images[i].uiAnimations[]`.

**B) `mug_tutorial.json` has already been replaced** with the new data structure. All 10 steps now have `visualStep.images[]` with per-image `uiAnimations[]`, `highlights[]`, and `caption`. No migration needed for test data.

## Proposed Changes

### Frontend Rendering

---

#### [MODIFY] [BaseRenderer.js](file:///c:/Users/teoen/GitHub/IDeA_Fusion360/FusionTutorialOverlay.bundle/Contents/palette/static/js/renderers/BaseRenderer.js)

Add carousel state management and timer logic:

- **New instance properties**: `carouselTimer`, `carouselImages`, `carouselIndex`, `carouselResumeTimer`
- **New method `startCarousel(imagesArray)`**: Accepts the `visualStep.images` array. Stores it, renders indicators, shows image 0, starts a 5-second `setInterval` cycling to the next image.
- **New method `showCarouselImage(index)`**: Swaps `#visualStepImage.src`, clears `#visualStepHighlights`, renders **only** that image's `highlights[]`, updates caption and indicator dot active states.
- **New method `renderCarouselIndicators(count)`**: Creates circle dot buttons in `#carouselIndicators`. Click handler: switches image, pauses auto-timer, resumes after 5 seconds.
- **New method `stopCarousel()`**: Clears timers. Called from `cleanup()` and start of `renderVisualStep()`.
- **Modify `renderVisualStep()`**: When `step.visualStep.images` (array) exists, call `startCarousel()`. Falls back to existing single-image logic for `step.visualStep.image` (string).

---

#### [MODIFY] [AnimatedRenderer.js](file:///c:/Users/teoen/GitHub/IDeA_Fusion360/FusionTutorialOverlay.bundle/Contents/palette/static/js/renderers/AnimatedRenderer.js)

Adapt animation playback to per-image `uiAnimations`:

- **Override `showCarouselImage(index)`**: After calling `super.showCarouselImage(index)`, abort any in-progress animation, then play `carouselImages[index].uiAnimations[]` (cursor moves, highlights, tooltips, arrows) for the newly active image.
- **Modify `render(step)`**: Instead of reading `step.uiAnimations`, delegate animation playback to the carousel. If no carousel is active (single-image or no `visualStep`), fall back to reading `step.uiAnimations` for backwards compatibility.
- **Backwards-compat fallback**: If `step.visualStep.images` does not exist but `step.uiAnimations` does, play animations the legacy way (current behavior).

---

#### [MODIFY] [tutorial_palette.html](file:///c:/Users/teoen/GitHub/IDeA_Fusion360/FusionTutorialOverlay.bundle/Contents/palette/tutorial_palette.html)

Add carousel indicator container inside `#visualStepArea`, after `#visualStepCaption`:

```html
<div id="carouselIndicators" class="carousel-indicators hidden"></div>
```

---

### Styling

---

#### [MODIFY] [main.css](file:///c:/Users/teoen/GitHub/IDeA_Fusion360/FusionTutorialOverlay.bundle/Contents/palette/static/css/main.css)

Add carousel indicator styles:

- `.carousel-indicators` — flexbox row, centered, padding, gap
- `.carousel-dot` — 12px circle, `var(--bg-tertiary)`, pointer cursor, transition
- `.carousel-dot:hover` — lighter background
- `.carousel-dot.active` — `var(--accent-primary)`, slightly larger scale
- Smooth fade on `#visualStepImage` when carousel-enabled (opacity transition)

---

### Test Data

---

#### [ALREADY DONE] [mug_tutorial.json](file:///c:/Users/teoen/GitHub/IDeA_Fusion360/FusionTutorialOverlay.bundle/Contents/test_data/mug_tutorial.json)

> [!NOTE]
> This file has **already been replaced** with the new per-image data structure. No further edits needed. All 10 steps contain `visualStep.images[]` with per-image `uiAnimations[]`, `highlights[]`, and `caption`. Step-level `uiAnimations` has been removed.

---

## Verification Plan

### Manual Verification (Standalone Browser Mode)

1. `cd FusionTutorialOverlay.bundle/Contents && python -m http.server 8000`
2. Open `http://localhost:8000/palette/tutorial_palette.html`
3. **Every step:**
   - Carousel cycles images automatically every 5 seconds
   - Correct dot count per environment (3 for Solid, 4 for Sketch)
   - Clicking a dot switches image + pauses, resumes after 5 seconds
4. **Per-image animations:** each image's cursor animations / highlights / tooltips play only when that image is displayed and stop when carousel switches
5. **Annotation pairing:** highlights appear only with their paired image
6. **No regressions:** navigating between steps clears timers and animations; no leftover state from previous steps
