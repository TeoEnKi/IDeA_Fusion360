# IDeA_Fusion360


## Deploying the Fusion Add-In

Use the provided deploy script to avoid stale installed bundles:

`powershell
.\scripts\deploy_addin.ps1
` 

Then restart the add-in in Fusion 360 and verify logs show the current BUILD_STAMP and runtime script path.

## Validate Tutorial UI Component References

To verify tutorial highlight component keys only use components defined in Sketch/Solid UI maps:

```powershell
python .\scripts\validate_tutorial_ui_components.py --repo-root . --tutorial FusionTutorialOverlay.bundle/Contents/test_data/cube_hole_tutorial.json --strict-labels
```

## Step Context Rule

`steps[].requires` is treated as the context required at the **beginning** of each step (entry precondition), not the context after its actions run.

The validator also checks this rule:

```powershell
python .\scripts\validate_tutorial_ui_components.py --repo-root . --tutorial FusionTutorialOverlay.bundle/Contents/test_data/cube_hole_tutorial.json --strict-step-context
```

