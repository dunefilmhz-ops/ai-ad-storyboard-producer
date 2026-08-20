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

This creates the production folders, `project-config.json`, continuity state and dashboard data placeholders. It also creates `00_brief/story-state.json`, `02_storyboard/field-policy.json` and `02_storyboard/scenes/scene-bibles.json` so story, field authority and scene topology are stored once instead of reconstructed for every shot.

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

The incremental director fields are optional while drafting and become required only when their risk applies:

- `story`: shot function and observable information/conflict/emotion/relationship/visual/outcome delta;
- `characters`: exact appearance-state asset plus shot-specific performance state;
- `blocking`: axis, camera side, world-space truth and screen-space projection;
- `motion`: start, preparation, path, impact, reaction, end, dominant vector and continuity anchors;
- `camera`: framing and explicit cut motivation;
- `transition`: inherited shot, transition type and allowed delta;
- `production`: A/B/C priority, complexity score, budget and diagnosed failure source.

Do not duplicate scene topology in every shot. Store the master layout, axes, camera zones, thresholds and linked reverse plates once in `scene-bibles.json`; shots reference the applicable scene and axis.

Fill the root-level `blocking_diagram` with a compact, editable spatial plan. Use plain text so it remains readable in JSON, CSV and the review board. At minimum include:

- `摄影机` and its view direction;
- screen or world orientation such as `画左 / 画右 / 前景 / 后景` or `北 / 南 / 东 / 西`;
- each important character's fixed position and facing;
- movement arrows for entries, exits, crossings, attacks, falls or camera-relative travel.

Example:

```text
北：宝库门（半开）
画左：翀 → 门内      画中：佛朗哥 ↑ 踹门      画右：周 ← 门内
南：摄影机，正面看向宝库门
```

Multi-character contact, doorways, fights, crossing paths and axis-sensitive coverage require a diagram before keyframe approval. For an empty environment or a single subject, record the camera, subject zone and motion direction rather than omitting the field.

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

## Import visual references

Import client style and character images into the project-level reference library so they are visible and editable in the review board:

```bash
python scripts/project_manager.py add-reference \
  --project /path/to/project \
  --category style \
  --file /path/to/style-reference.png \
  --label "Night-sea ghost-ship mood" \
  --note "Use palette, spectral light and atmosphere; do not copy composition or logos"
```

Use `--category character` for identity, costume, transformation or silhouette references. The importer validates image type and size, copies the file into `01_assets/references/`, creates a stable reference ID, and records revision history. The dashboard supports adding more images, editing labels and notes, conflict-safe saves, uncropped previews and recoverable removal. Keep a reference's intended authority in its note, and bind the corresponding versioned asset IDs to affected shots after approval.

## Review and validate

Inspect the smallest useful slice before editing:

```bash
# compact project and shot overview
python scripts/project_manager.py inspect --project /path/to/project

# only the fields needed for one or more shots
python scripts/project_manager.py inspect \
  --project /path/to/project \
  --shot-id G04 --shot-id G05 \
  --field editorial.keyframe_prompt \
  --field assets.asset_refs \
  --field blocking_diagram
```

Use this instead of loading `dashboard/review-state.json` or every shot record for a scoped revision. Omit `--field` to receive a compact review-oriented shot summary; use `--full` only when the complete source record is genuinely required.

```bash
python scripts/project_manager.py set-review --project /path/to/project --shot-id G01 --status revision --issue "hand contact is broken"
python scripts/project_manager.py validate --project /path/to/project
python scripts/project_manager.py export-dashboard --project /path/to/project
```

Open the editable local review board:

```bash
python scripts/project_manager.py serve-dashboard \
  --project /path/to/project \
  --host 127.0.0.1 \
  --port 8765
```

The command prints a loopback-only local URL. Keep the process running while the user reviews. The board writes edits directly to the matching `shot.json`, increments its revision and appends a `board_update` history entry with changed fields plus before/after values. If another tab saved the same shot first, the stale tab receives a conflict instead of overwriting newer work.

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

Validation checks model duration, action budget, high-risk review coverage, exact-text routing, gate states, required story fields, production priority, generation-complexity range, failure-source vocabulary, transition type and structured world/screen blocking when used. Dashboard export writes `dashboard/review-state.json`, an Excel-friendly `dashboard/review-board.csv`, and the editable `dashboard/index.html` review surface.

## Contact sheet

Attach generated media without manually rewriting `shot.json`:

```bash
python scripts/project_manager.py set-shot-media \
  --project /path/to/project \
  --shot-id G01 \
  --kind keyframe \
  --file /path/to/project/03_keyframes/G01/G01-keyframe-v1.png \
  --status keyframe-review
```

The command requires the media file to live inside the project, increments the shot revision, records changed fields in history and refreshes dashboard data. Use `--kind video` for generated clips.

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

Treat `dashboard/review-state.json` as the board's read model. The board may edit script, blocking diagram, dialogue, prompts, timing, review status, issues, notes and field-level annotations, but must write changes back through the same shot records and preserve `history` rather than replacing source files silently.

The board should expose three connected views:

1. Project: specs, gates, department readiness, workflow history and unresolved decisions.
2. Assets: versioned identity/environment/prop records, approval state and shot usage.
3. Shots: keyframe/video preview, story purpose, prompt version, asset tags, duration, risk, review dimensions, issue list and revision history.

Department stages are responsibility lanes, not autonomous agents. Brief, art, storyboard, cinematography, lighting, motion, edit, sound and delivery may be reviewed independently while sharing the same project and shot records.
