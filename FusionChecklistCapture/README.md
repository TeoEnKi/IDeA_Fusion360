# Fusion Checklist Capture Add-in

Standalone Fusion add-in to run the UI click checklist and capture real command events.

## Deploy

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_checklist_addin.ps1
```

## Use in Fusion

1. Tools > Add-Ins > Scripts and Add-Ins > Add-Ins tab.
2. Run `FusionChecklistCapture`.
3. Click `Checklist Capture` in Tools > Utilities.
4. In palette:
   - `Start Session`
   - `Arm Next Click`
   - click the prompted target button/tab in Fusion
   - when a method is captured, choose `Save`, `Discard`, or `Retry Capture`
   - use `Next`/`Prev` to move between rows and update saved values anytime
   - `Export Report`

## Output

Files are written to:

`FusionChecklistCapture/capture_output/`

- `live_capture_events_<session>.jsonl`
- `ui_capture_source_<session>.json` (source of truth with saved `eventCalled`)
- `ui_capture_mapping_<session>.csv`
- `ui_capture_report_<session>.md`
