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

- For story-state deltas, field locking, scene axes, cut motivation, motion phases, generation complexity or failure diagnosis, read [references/director-model.md](references/director-model.md).
- For character turnarounds, wardrobe/prop sheets, empty environment plates, reverse angles or side views, read [references/asset-foundation.md](references/asset-foundation.md).
- For family resemblance, derived creature forms, recurring-prop triage, exterior route topology, color anchors or nine-grid environment expansion, also read [references/asset-foundation.md](references/asset-foundation.md).
- For dialogue-led live action, vertical drama, emotional reaction coverage, action coverage or sliced generations, read [references/dialogue-and-camera-grammar.md](references/dialogue-and-camera-grammar.md).
- For reusable project folders, shot status/version records, action-budget validation, contact sheets or review-board data, read [references/production-manager.md](references/production-manager.md) and use the bundled scripts.

## Token economy protocol

Use project files and the review board as durable memory. Do not repeatedly paste or reload the full production package.

- On first build, write complete data to the project and return the board link plus a short decision summary. Print all prompts in chat only when the user explicitly asks for a text export.
- On revisions, identify affected shot IDs and fields first. Inspect only those records with `project_manager.py inspect`; do not read the full dashboard or every `shot.json` for a single-shot change.
- Apply delta edits: preserve approved and untouched fields, update only affected prompt versions, and summarize changed fields rather than reproducing unchanged prompts.
- Batch related edits, then run `validate` and `export-dashboard` once after the batch instead of after every field mutation.
- Reuse the current turn's already-read brief, references and prompts while their source revision is unchanged. Re-read only when a file, shot revision, reference revision or user instruction changes.
- Keep Seedance-ready prompts self-contained. Token economy applies to analysis, review and chat output; never replace required generation details with unresolved internal IDs.

## Workflow

Use one lightweight Director Brain to route decisions through five concerns: story, assets, space, motion and production. These are responsibility lenses, not autonomous agents and not five separate passes. Resolve the smallest uncertain layer first, store the decision in project data, then compile prompts from approved state.

### 1. Normalize the brief

Extract or infer:

- objective, platform, audience and CTA;
- target ratio, resolution, fps, duration and language;
- story order, required beats, selling points, dialogue and exact text;
- characters, identity anchors, costume states, props, environments and style;
- provided assets, missing assets, client references and prohibited content;
- generation tools and model limits.

For narrative work with multiple beats, create a compact 0–10 emotion-and-sound curve before shot expansion. Mark setup, escalation, peak, release, silence/room-tone zones, BGM entry or exit, and the intended edit effect. Treat the numbers as relative planning aids, not objective measurements or a fixed dramatic formula.

Default to `16:9` horizontal delivery when the client, platform and supplied assets do not specify an aspect ratio. Treat `16:9` as the preferred working canvas for keyframes, storyboards and video prompts. Override it only when the client delivery specification, publishing platform, existing campaign format or approved reference composition explicitly requires another ratio such as `9:16`, `1:1` or `4:5`. Record every override in the brief assumptions and keep all downstream prompts, safe areas and delivery checks on the selected ratio.

Create a script fact lock before creative expansion: exact dialogue, event order, action results, character ownership and non-negotiable selling points. If the client requires faithful adaptation, preserve these facts exactly. Add only visual coverage, anticipation, reaction, inserts or editorial bridges that do not create a new story fact.

Accept pure text. Do not require a reference image or video. If a missing choice does not materially change the result, use a labeled assumption and continue. Ask only when a missing decision changes scope, brand accuracy, legal safety or delivery format.

### 2. Separate client shots from production shots

Treat a client shot as a narrative unit, not an immutable generation boundary. Preserve its story purpose while splitting, combining or adding production shots when needed.

Read [references/shot-design.md](references/shot-design.md). Always output a mapping:

| Client shot | Story requirement | Production shot | Adjustment | Generate | Edit use |
|---|---|---|---|---:|---:|

Add at most 1–2 short shots at a fast beat when they materially improve emotion, causality, impact, scale or conversion. Do not add unrelated plot.

Before retaining any production shot, state its story delta: what new information, conflict, emotion, relationship, visual state or outcome changes because the shot exists. A shot may be short or long; retention comes from meaningful state change, not a fixed seconds-per-shot rule. Merge or remove shots with no readable delta unless they are essential spatial re-establishing, reaction or transition coverage.

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

When characters are biologically related or one form derives from another, define the parent/base identities first and make the relationship observable through a small set of inherited traits. Generate the dependent identity or creature form only after its source identities are approved. Do not force resemblance when the script does not establish it, and do not treat a generated resemblance as a factual claim about real people.

Classify important fields before batch prompting:

- `locked`: identity, approved silhouette, permanent marks, topology and other facts that cannot change without approval;
- `state-driven`: costume stage, damage, wetness, equipment ownership, time of day and other changes authorized by story state;
- `shot-dynamic`: pose, gaze, expression, framing, focus and temporary effects.

Keep character identity, appearance state and performance state separate. Performance is shot data, not a new asset. Bind every recurring shot to one approved appearance-state asset, except the shot that visibly performs the transition.

For every recurring scene, define a compact Scene Spatial Bible before axis-sensitive coverage: top-down layout, north/reference direction, entrances, persistent landmarks, light sources, character zones, scene axes and allowed/risky/forbidden camera zones. Record both world-space truth and its screen-space projection. A reverse angle may swap screen left/right; it may not mirror the physical room.

For exterior journeys or chases across multiple landmarks, add a route topology before plates: ordered nodes, approximate direction/elevation, travel path, relative distance or travel time when story-relevant, entrances/exits and allowed view directions. Use the topology as the source of truth for later exterior plates; do not invent false precision when the script supplies none.

For every production shot, add a compact `blocking_diagram` that can be reviewed independently from prose. It must name the camera, screen or space orientation, each important character's position and facing, and any meaningful movement arrow. Multi-character contact, entrances, exits, fights, crossings and axis-sensitive shots must use an explicit diagram before keyframe approval. For an empty environment or single-subject shot, show the camera, subject zone and motion direction instead of leaving the field blank.

Only story-authorized fields may change. Never write “keep consistent” without naming the fields that must remain stable.

For multi-part generations, append a physical handoff checkpoint to every segment: final framing, camera height, character position, facing, gaze, pose, motion vector, held props, environment landmarks and lighting state. The next segment must begin from this checkpoint.

Describe complex motion as `start → preparation → path → impact → reaction → end`, plus its dominant vector and continuity anchors. Keep preparation and execution in one shot when separation weakens causality; split when contact, transformation, crowd interaction or camera movement makes the generation uncontrollable. Every cut must have a motivation such as new information, action, reaction, emphasis, spatial re-establishing or time compression.

### 5. Produce keyframes before video

Return image-storyboard/keyframe prompts first unless the user explicitly asks only for text. Approve style, identity, layout, action readability and continuity before video generation.

Treat uploaded references as evidence, never as automatically approved production assets. Before recurring characters or locations enter batch keyframe generation: extract authoritative traits; generate a clean identity turnaround for each recurring character; split each costume, damage state, upgrade or creature transformation into a separately named stage asset; generate empty environment masters from one spatial contract; place those derived assets in the board asset library as `draft` or `review` and wait for approval.

Create reusable prop assets only when a prop recurs, changes state, drives action/continuity, carries a selling point or would be costly to regenerate inconsistently. A one-off background object normally stays shot-dynamic; a one-off hero prop may still require an asset.

For every recurring connected interior, build a complete spatial coverage pack rather than a single attractive plate. At minimum include: approach-space master, approach-space reverse, destination-room master and destination-room reverse. Add side views when staging needs them. Every plate must state camera zone and view direction, shared threshold or doorway, hinge side and swing direction, persistent landmarks, light sources and which landmarks appear frame-left/frame-right after reversal. Approve the pack as one linked asset set; reject any plate that invents a second door, mirrors an asymmetric landmark, changes room scale or contradicts the master floor plan.

When a location needs broad angle coverage, approve one spatially correct master first, then expand a contact sheet or nine-grid of purposeful camera zones, shot sizes and lighting states. A grid is a review aid, not nine automatically usable assets: validate each cell against the same topology and register approved cells separately. Lock compact interior/exterior color-and-light anchors before batch generation when palette drift is a material risk; describe dominant colors, practical sources, contrast and prohibited drift rather than relying on a decorative swatch alone.

Do not combine multiple states of one character into one ambiguous anchor. Bind every shot to the exact stage asset it uses. If provisional keyframes already exist, keep them visibly provisional and re-check or regenerate them after the asset gate is approved.

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

For complete productions, also provide a director-map view: one row per generation or post-production unit, linked to story beat, emotion/sound curve, approved input assets, location node or scene axis, duration, generation route, priority, complexity/risk, expected handoff state and review gate. Derive its row count from the actual edit; never copy a case-study count such as 24 video units plus one post unit.

Assign each shot a generation priority and complexity score. Use `A` for critical hooks, payoffs and identity close-ups, `B` for main narrative coverage and `C` for replaceable bridges. Score complexity from 1–10 using character count, contact, props, motion, camera motion, transformation and continuity dependency. Scores 8–10 should normally use split coverage, reduced motion or Pose A/B/C. Before regenerating a failed shot, classify the source as prompt, asset, spatial, motion, camera or model; do not spend another iteration without changing the responsible layer.

When the user wants persistent production management, initialize a project with `scripts/project_manager.py`. Keep one `shot.json` per production shot; record action units, risk tags, continuity start/end states, prompt versions, asset paths, review status, issues and history. Run `validate` before batching and `export-dashboard` after review changes. Use [references/model-profiles.json](references/model-profiles.json) as an editable capability registry rather than hard-coding model limits into prompts.

Register approved character, costume, environment, prop, effect, UI and gameplay assets with versioned IDs and reference those IDs from shots. Record the creative rationale separately from the generation prompt: story purpose, framing, camera movement, lighting and edit intent. Preserve project gates and department readiness so art, storyboard, cinematography, lighting, motion, edit and sound decisions can be reviewed independently without losing the common story goal.

Treat client-supplied visual references as project-level evidence, not disposable chat context. Keep this raw reference library separate from the confirmable production-asset library. Import each usable image into the review board's reference library, classify it at minimum as `style` or `character`, give it a human-readable label and note what is authoritative about it. A style reference may lock palette, rendering, atmosphere, material or camera energy without importing its story facts. A character reference may lock identity, silhouette, costume construction or transformation state without copying visible logos or unrelated text. Record provisional interpretation explicitly when one image contains multiple subjects or its intended role is uncertain.

### 7.1 Create the editable review board

When the user supplies a script or brief and wants a complete storyboard rather than a single isolated prompt, make the editable storyboard board the primary review deliverable. Do not return only a long Markdown document.

Initialize or update the production project, fill each `shot.json` with:

- client script and optimized production-shot script;
- character blocking diagram with camera, orientation, positions, facing and motion arrows;
- dialogue, voiceover and exact on-screen text;
- client, generation and edit-use timing;
- GPT keyframe prompt, Seedance prompt, negative constraints and post-production notes;
- review status, field-level annotations, risks, assets and continuity data.

For every complete script or complete production-package request, run `export-dashboard` and provide at least one actually accessible editable surface without waiting for the user to request a board again. Prefer an in-conversation interactive board when available; its submit action must send selected-shot edits and annotations back into the conversation. Otherwise start `serve-dashboard` and return its local URL. Skip the board only when the user explicitly requests text-only output or a single isolated shot. Give the board as the main approval surface and a concise text summary as support. The board must allow direct field edits, shot-level status changes, field-targeted comments, prompt copying, filtering and save history. It must expose both raw style/character references and a separate asset library for generated turnarounds, stage-specific forms and spatially consistent scene plates with preview, shot linkage, version and approval status. Treat board edits as authoritative user feedback: preserve untouched approved fields and revise only requested variables.

After a reference is uploaded or revised, update the relevant asset/continuity records and affected prompt versions before asking for keyframe approval. Reference images guide generation through their approved visual properties and asset IDs; never put local filesystem paths into a Seedance-ready prompt.

Use these gates:

1. `storyboard`: user checks shot split, script, dialogue and timing.
2. `keyframe`: user checks identity, composition, style and prompt.
3. `motion`: user checks Seedance prompt, action schedule and end frame.
4. `delivery`: user checks edit, audio, text, CTA and technical specs.

Do not advance to generation merely because the board exists; advance when the relevant gate is approved or explicitly waived.

### 8. Review and revise

Translate feedback into observable changes: subject, location, action, timing, camera, effect and continuity. Never use vague instructions such as “optimize more.” Preserve approved fields and change only the requested variable.

For a scoped revision, report `changed shots`, `changed fields`, `validation result` and the board link. Do not resend the complete output contract unless the user requests a full re-export or the change invalidates the overall structure.

Use [references/qa-checklist.md](references/qa-checklist.md) at keyframe approval, first video, revision and final delivery.

When clips exist, run `scripts/build_contact_sheet.py` and inspect the start, middle and end frames before final motion approval. Do not treat a generated contact sheet as approval by itself; record the human review result in each shot.

For dialogue or action scenes, verify that camera grammar serves comprehension: preserve screen direction, change angle or shot size enough to avoid a near-duplicate cut, carry outgoing motion into the incoming shot, and use reaction or detail coverage instead of holding a long speech on one face.

## Output contract

For normal managed-project work, return the board link, current project state, changed shots/fields, assumptions, main risks and required confirmations. Do not dump unchanged prompts or JSON into chat. When the user explicitly asks for a full text package, return sections in this order:

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

For a complete script-to-storyboard request, also create an editable review board and place its access link before the supporting text summary. For text-only or single-shot requests, do not force a board.

When the user asks for only one stage, return that stage without forcing the full package.

## Non-negotiables

- Do not reuse prior-case story content.
- Do not submit one-click assembled output as final.
- Do not enter video generation before keyframe approval unless explicitly waived.
- Do not sacrifice causality or action completion merely to match client seconds.
- Do not hide assumptions, uncertain claims or missing brand assets.
- Do not mark delivery complete when ratio, resolution, fps, duration, text, watermark or AI-deformation checks fail.
