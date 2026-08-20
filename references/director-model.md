# Director Decision Model

Use this reference when a project needs more than prompt writing: story diagnosis, field locking, spatial continuity, action design, cut logic, generation budgeting or failure diagnosis. It is an incremental layer over the existing workflow, not a replacement architecture.

## Decision order

Resolve decisions in this order:

1. story state and required delta;
2. approved identity and appearance state;
3. world-space truth and screen-space projection;
4. motion phases and continuity anchors;
5. camera and cut motivation;
6. generation route, complexity and budget;
7. prompt compilation.

Do not solve a downstream prompt problem while an upstream asset or spatial decision is still ambiguous.

## Story delta

Every production shot should justify itself through one or more observable changes:

- `new_information`;
- `conflict_delta`;
- `emotion_delta`;
- `relationship_delta`;
- `visual_delta`;
- `outcome_delta`;
- `next_hook`.

Reaction, insert and spatial re-establishing shots may have small deltas, but their function must be explicit. Do not impose a universal shot duration or shot count.

## Emotion and sound curve

For multi-beat narrative work, map each beat on a relative 0–10 intensity curve and annotate setup, escalation, peak and release. Add intended silence, room tone, SFX emphasis, BGM entry/exit and transition points. Use the curve to diagnose a flat script and to guide edit density and sound design; do not let it override explicit client timing, dialogue or story facts. The scale is comparative within the current piece and should not be treated as scientific measurement.

## Field policy and asset gate

Classify production fields as:

- locked: requires approval to change;
- state-driven: changes only when the story state authorizes it;
- shot-dynamic: may change per shot.

Separate identity, appearance and performance. A recurring character receives one base identity plus separately approved appearance-stage assets. Emotion, gaze, energy and pose belong to the shot. References are evidence; generated clean turnarounds and stage assets become production anchors only after approval.

## Scene Spatial Bible

Store one scene-level source of truth:

- top-down layout and scale;
- north/reference direction;
- entrances, thresholds, hinges and swing arcs;
- persistent landmarks and practical lights;
- character and effect zones;
- axis IDs;
- safe, risky and forbidden camera zones;
- direct reverse and adjacent views.

For each shot, record `axis_id`, `camera_side`, `world_space` and `screen_space`. World space states physical location and orientation. Screen space states frame position, on-screen facing and movement direction. Crossing an axis is allowed only with an explicit neutral, on-axis, motivated moving, spatial re-establishing or clearly signaled transition shot.

Camera difference is a comprehension test, not a fixed 45-degree law. Adjacent coverage should change at least one meaningful dimension: shot size, camera side, height, subject emphasis, information or emotional function.

Exterior movement across multiple locations uses the same principle at route scale: store ordered nodes, reference direction, approach/departure vectors, relative distance or time when justified, terrain/elevation and allowed view directions before generating plates.

## Motion and transitions

Describe controllable motion with:

`start → preparation → path → impact → reaction → end`

Also record dominant vector and continuity anchors such as framing, camera height, position, facing, gaze, pose, prop state, landmarks and lighting. Transition types are:

- exact;
- action;
- temporal;
- reaction;
- insert;
- time-jump;
- spatial-reestablish.

The incoming shot inherits all fields except its declared `allowed_delta`.

## Generation feasibility

Score 1–10 using character count, contact, prop interaction, motion, camera motion, transformation and continuity dependency:

- 1–4: one keyframe may be sufficient;
- 5–7: prefer start/end frames or a simplified chain;
- 8–10: split coverage, reduce simultaneous changes or use Pose A/B/C.

Priorities: `A` core hook/payoff, `B` main narrative, `C` bridge. Before regeneration, set `failure_source` to prompt, asset, spatial, motion, camera or model and change the responsible layer.

## Director map

For a complete production, compile the approved decisions into one operational map. Each generation or post unit should link:

- story beat and observable delta;
- emotion/sound target;
- approved character state, prop and environment IDs;
- scene node, axis or camera zone;
- generation and edit duration;
- generation route, model/profile and expected handoff state;
- priority, complexity/risk, review focus and gate status.

This is a task map for production, not a fixed-format storyboard and not a prescribed number of units. Derive the units from the current edit and include post-only units for exact text, UI, BGM, grade or effects when generation should not own them.

## QA order

Check story function, asset identity, world space, screen space, axis, action continuity, contact/props, cut motivation, performance, feasibility, style/lighting and finally beauty. A beautiful frame that contradicts topology or state is a failed frame.

## Prompt compiler

Compile self-contained model prompts from approved data in this order: story/conflict state, subject, appearance state, performance, spatial relationship, action, camera, environment, lighting, style, temporal beats, physical feedback, end state and negative constraints. Internal asset IDs may organize project data but must be expanded into observable descriptions in prompts delivered to generation models.

## Scope guardrails

Do not create multiple autonomous agents, a heavy model platform or a large generic phrase library. Add a reusable template only after the same production pattern recurs and the template still expands from current scene, axis, state and shot function.
