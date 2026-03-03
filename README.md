# IDeA_Fusion360


## Deploying the Fusion Add-In

Use the provided deploy script to avoid stale installed bundles:

`powershell
.\scripts\deploy_addin.ps1
` 

Then restart the add-in in Fusion 360 and verify logs show the current BUILD_STAMP and runtime script path.

## Webhook-First Bootstrap

Tutorials are no longer auto-loaded from local `test_data` fixtures on palette open.

Current runtime bootstrap flow:
1. Open palette (bridge sends `ready`).
2. Palette shows the beginning screen.
3. Click **Get Tutorial**.
4. Plugin calls:
   - `POST https://narwhjorl.app.n8n.cloud/webhook/start-scan`
   - Body: `{ "username": "ProtoGo" }`
5. While waiting, plugin/UI may poll:
   - `GET https://narwhjorl.app.n8n.cloud/webhook/scan-status`
   - Response field `statusCode`: `-1` (idle), `0` (processing), `1` (finished)

`scan-status` is for progress/debug visibility. Tutorial payload is sourced from `start-scan` response.

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

