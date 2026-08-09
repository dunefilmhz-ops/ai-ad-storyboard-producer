# Local Production Manager

Use these scripts when the user wants a reusable project structure, status tracking, action-budget checks, contact sheets or data for a review board. They do not call GPT, Seedance or Jimeng APIs.

## Initialize

```bash
python scripts/project_manager.py init \
  --output /path/to/project \
  --title "Project title" \
  --aspect-ratio 16:9 \
  --resolution 720x1280 \
  --fps 30 \
  --video-model seedance-2.0-mini
```

This creates the production folders, `project-config.json`, continuity state and dashboard data placeholders.

## Add a shot

```bash
python scripts/project_manager.py add-shot \
  --project /path/to/project \
  --shot-id G01 \
  --client-shot-id C01 \
  --summary "The required story result" \
  --generation-seconds 6 \
  --edit-seconds 2.5
```

Edit the resulting `shot.json` to fill action units, risks, continuity checkpoints, assets and review focus. Keep exact prompt versions in that shot's `prompts/` folder and list them under `assets.prompt_versions`.

Also fill `creative_rationale`: explain the shot's story function and why its framing, motion, light and edit treatment serve that function. This preserves department intent during later revisions instead of storing only a long prompt.

## Register assets

```bash
python scripts/project_manager.py add-asset \
  --project /path/to/project \
  --asset-id face-hero-v1 \
  --type character \
  --version v1 \
  --status approved \
  --path 01_assets/characters/hero-v1.png
```

Reference registered IDs from each `shot.json` under `assets.asset_refs`. Use versioned IDs for faces, costume stages, environments, props, effects, UI and gameplay plates. Do not silently replace an approved asset under the same ID.

## Review and validate

```bash
python scripts/project_manager.py set-review --project /path/to/project --shot-id G01 --status revision --issue "hand contact is broken"
python scripts/project_manager.py validate --project /path/to/project
python scripts/project_manager.py export-dashboard --project /path/to/project
```

Mark project handoffs explicitly instead of inferring them from filenames:

```bash
python scripts/project_manager.py set-workflow --project /path/to/project --scope gate --name storyboard --status approved --note "client approved"
python scripts/project_manager.py set-workflow --project /path/to/project --scope department --name art --status approved
```

Record creative choices that materially affect scope or visual direction:

```bash
python scripts/project_manager.py add-decision \
  --project /path/to/project \
  --decision-id D001 \
  --question "Which opening hook should be used?" \
  --option "conflict first" \
  --option "result first" \
  --selected "conflict first" \
  --rationale "The causal conflict reads faster" \
  --status locked
```

Validation checks model duration, action budget, high-risk review coverage, exact-text routing, gate states and required story fields. Dashboard export writes both `dashboard/review-state.json` and an Excel-friendly `dashboard/review-board.csv`.

## Contact sheet

Set each approved clip's project-relative path in `shot.json` under `assets.video`, then run:

```bash
python scripts/build_contact_sheet.py --project /path/to/project
```

The sheet shows start, middle and end frames for every available shot. Review subject scale, identity, costume, prop, direction, end-state continuity and repeated compositions. Missing clips are reported rather than silently skipped.

## Environment check

```bash
python scripts/project_manager.py doctor --project /path/to/project
```

This checks only local project-management and media-QA capabilities. API credentials remain explicitly out of scope until automation is authorized.

## Dashboard compatibility

Treat `dashboard/review-state.json` as the future board's read model. A board may edit review status, issues and notes, but must write changes back through the same shot records and preserve `history` rather than replacing source files silently.

The board should expose three connected views:

1. Project: specs, gates, department readiness, workflow history and unresolved decisions.
2. Assets: versioned identity/environment/prop records, approval state and shot usage.
3. Shots: keyframe/video preview, story purpose, prompt version, asset tags, duration, risk, review dimensions, issue list and revision history.

Department stages are responsibility lanes, not autonomous agents. Brief, art, storyboard, cinematography, lighting, motion, edit, sound and delivery may be reviewed independently while sharing the same project and shot records.
