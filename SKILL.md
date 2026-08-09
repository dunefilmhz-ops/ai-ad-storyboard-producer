---
name: ai-ad-storyboard-producer
description: Convert client AI advertising requirements into production-ready storyboards, keyframe prompts, Seedance video prompts, timing plans, revision notes, and delivery QA. Use for mobile-game acquisition ads, AI video briefs, scripts, shot lists, PDFs, spreadsheets, character sheets, reference images or videos, including pure-text scripts with no visual references; use when client shots need to be split, expanded, re-timed, generalized across genres, or translated into GPT image generation and Seedance image-to-video workflows.
---

# AI Ad Storyboard Producer

Produce a subject-agnostic AI acquisition-video plan. Treat every project as new; never carry characters, settings, costumes, brands, codes, or story facts from an earlier case.

## Source authority

Apply sources in this order:

1. Current client production standard and explicit user corrections.
2. Current project script, character sheets, game assets and delivery specs.
3. Current project reference images/videos.
4. Reusable heuristics and prior case lessons.

When sources conflict, preserve the higher-authority source and flag the conflict. Use [references/production-standard.md](references/production-standard.md) for mandatory workflow and delivery rules. Use [references/case-lessons.md](references/case-lessons.md) only as pattern recognition, never as project content.

Load specialized references only when relevant:

- For character turnarounds, wardrobe/prop sheets, empty environment plates, reverse angles or side views, read [references/asset-foundation.md](references/asset-foundation.md).
- For dialogue-led live action, vertical drama, emotional reaction coverage, action coverage or sliced generations, read [references/dialogue-and-camera-grammar.md](references/dialogue-and-camera-grammar.md).
- For reusable project folders, shot status/version records, action-budget validation, contact sheets or review-board data, read [references/production-manager.md](references/production-manager.md) and use the bundled scripts.

## Workflow

### 1. Normalize the brief

Extract or infer:

- objective, platform, audience and CTA;
- target ratio, resolution, fps, duration and language;
- story order, required beats, selling points, dialogue and exact text;
- characters, identity anchors, costume states, props, environments and style;
- provided assets, missing assets, client references and prohibited content;
- generation tools and model limits.

Default to `16:9` horizontal delivery when the client, platform and supplied assets do not specify an aspect ratio. Treat `16:9` as the preferred working canvas for keyframes, storyboards and video prompts. Override it only when the client delivery specification, publishing platform, existing campaign format or approved reference composition explicitly requires another ratio such as `9:16`, `1:1` or `4:5`. Record every override in the brief assumptions and keep all downstream prompts, safe areas and delivery checks on the selected ratio.

Create a script fact lock before creative expansion: exact dialogue, event order, action results, character ownership and non-negotiable selling points. If the client requires faithful adaptation, preserve these facts exactly. Add only visual coverage, anticipation, reaction, inserts or editorial bridges that do not create a new story fact.

Accept pure text. Do not require a reference image or video. If a missing choice does not materially change the result, use a labeled assumption and continue. Ask only when a missing decision changes scope, brand accuracy, legal safety or delivery format.

### 2. Separate client shots from production shots

Treat a client shot as a narrative unit, not an immutable generation boundary. Preserve its story purpose while splitting, combining or adding production shots when needed.

Read [references/shot-design.md](references/shot-design.md). Always output a mapping:

| Client shot | Story requirement | Production shot | Adjustment | Generate | Edit use |
|---|---|---|---|---:|---:|

Add at most 1–2 short shots at a fast beat when they materially improve emotion, causality, impact, scale or conversion. Do not add unrelated plot.

### 3. Design timing from performance

Ignore mechanically inaccurate client seconds. Estimate the minimum time needed for anticipation, action, result and reaction, then provide:

- client reference duration;
- recommended generation duration;
- recommended edit duration;
- compressed alternative when required;
- per-second action schedule for complex shots.

Keep each generation inside the selected model limit. Prefer one continuous setting and one achievable action chain per generation. Split scene changes, identity transformations, complex UI and multi-stage combat.

### 4. Build continuity states

Create explicit state tables before prompts:

- character identity invariants;
- costume/condition stages;
- prop count and ownership;
- environment layout and light source;
- screen direction, position, gaze and action continuity;
- effect color, source, path and interaction with the scene.

Only story-authorized fields may change. Never write “keep consistent” without naming the fields that must remain stable.

For multi-part generations, append a physical handoff checkpoint to every segment: final framing, camera height, character position, facing, gaze, pose, motion vector, held props, environment landmarks and lighting state. The next segment must begin from this checkpoint.

### 5. Produce keyframes before video

Return image-storyboard/keyframe prompts first unless the user explicitly asks only for text. Approve style, identity, layout, action readability and continuity before video generation.

Write prompts with [references/prompt-schema.md](references/prompt-schema.md). A keyframe prompt must specify subject identity, state, action instant, spatial relationship, shot size, camera angle, lens feel, environment, light source, style, safe area and negative constraints.

### 6. Produce directly usable video prompts

For each production shot, return one self-contained prompt that can be pasted into Seedance after uploading the corresponding image. Do not include local paths, internal filenames or production commentary in the prompt.

Specify:

- aspect ratio and continuity locks;
- second-by-second action beats when useful;
- camera movement and ending composition;
- physical weight, secondary motion, reaction and effect lifecycle;
- dynamic negative constraints derived from the shot risk.

Do not ask video models to render exact UI text, codes, logos, subtitles or store marks. Preserve an uploaded UI image when animation is required; otherwise assign exact typography to post-production.

### 7. Package generation batches

Group work by asset readiness and review risk, not by story theme. Prioritize:

1. identity/style anchors;
2. multi-character blocking and hands;
3. complex action and transformations;
4. environment/wide shots;
5. UI, gameplay and end card.

Provide a batch table with input asset, model, duration, prompt, expected end frame and review focus.

When the user wants persistent production management, initialize a project with `scripts/project_manager.py`. Keep one `shot.json` per production shot; record action units, risk tags, continuity start/end states, prompt versions, asset paths, review status, issues and history. Run `validate` before batching and `export-dashboard` after review changes. Use [references/model-profiles.json](references/model-profiles.json) as an editable capability registry rather than hard-coding model limits into prompts.

Register approved character, costume, environment, prop, effect, UI and gameplay assets with versioned IDs and reference those IDs from shots. Record the creative rationale separately from the generation prompt: story purpose, framing, camera movement, lighting and edit intent. Preserve project gates and department readiness so art, storyboard, cinematography, lighting, motion, edit and sound decisions can be reviewed independently without losing the common story goal.

### 8. Review and revise

Translate feedback into observable changes: subject, location, action, timing, camera, effect and continuity. Never use vague instructions such as “optimize more.” Preserve approved fields and change only the requested variable.

Use [references/qa-checklist.md](references/qa-checklist.md) at keyframe approval, first video, revision and final delivery.

When clips exist, run `scripts/build_contact_sheet.py` and inspect the start, middle and end frames before final motion approval. Do not treat a generated contact sheet as approval by itself; record the human review result in each shot.

For dialogue or action scenes, verify that camera grammar serves comprehension: preserve screen direction, change angle or shot size enough to avoid a near-duplicate cut, carry outgoing motion into the incoming shot, and use reaction or detail coverage instead of holding a long speech on one face.

## Output contract

Return sections in this order:

1. brief normalization and assumptions;
2. client-shot to production-shot map;
3. optimized timeline;
4. continuity state tables;
5. keyframe prompts;
6. directly usable video prompts;
7. post-production instructions;
8. batch plan;
9. shot-level QA checklist;
10. delivery checklist.

When the user asks for only one stage, return that stage without forcing the full package.

## Non-negotiables

- Do not reuse prior-case story content.
- Do not submit one-click assembled output as final.
- Do not enter video generation before keyframe approval unless explicitly waived.
- Do not sacrifice causality or action completion merely to match client seconds.
- Do not hide assumptions, uncertain claims or missing brand assets.
- Do not mark delivery complete when ratio, resolution, fps, duration, text, watermark or AI-deformation checks fail.
