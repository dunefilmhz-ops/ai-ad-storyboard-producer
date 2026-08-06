# Asset Foundation and Spatial Plates

Use this reference when a project needs repeatable character, wardrobe, prop or environment assets. These are optional production aids, not mandatory deliverables for every project.

## Character identity record

Describe observable, stable traits rather than subjective attractiveness:

- approximate adult age band, build and body proportion;
- face shape, jaw, cheekbone and facial fullness;
- hair color, length, parting, texture and silhouette;
- eye shape and color, brow shape, nose structure and lip shape;
- skin tone, texture and distinctive marks;
- costume, accessories and condition stage.

Keep identity traits separate from temporary emotion, pose, lighting and camera effects.

## Asset-board selection

Choose the lightest board that resolves the current risk:

- portrait anchor: face and hair identity;
- three-view body/costume board: front, profile and back;
- four-view character board: front, profile, back and face close view;
- extended detail board: only when face, costume or accessories repeatedly drift;
- prop board: clean, centered, complete object with stable material and proportions.

Do not request arbitrary multi-view sheets when a single approved image is sufficient. Every view in a board must describe the same person, scale, costume construction, accessory count and material.

## Costume and condition stages

Record costume as named stages such as `look-A-clean`, `look-B-damaged` or `look-C-upgraded`. For each stage, state which garments and accessories persist, which are removed, and which condition changes are authorized. Never let a later prompt infer wardrobe from story mood alone.

## Environment master

For recurring locations, establish an empty environment plate before character staging when practical. Record:

- camera position, height, view direction and lens feel;
- persistent landmarks and entrances;
- usable floor area and character blocking zones;
- dominant light source, direction, color and intensity relationship;
- materials, wear and atmosphere;
- clean areas reserved for characters, effects or UI.

Prefer an eye-level frontal master when no other angle is required; it is usually easier to reverse-engineer and stage consistently. This is a default, not a universal aesthetic rule.

## Reverse and side views

Generate alternate views from a spatial contract, not from “same room” alone.

For a reverse view, specify the original camera position, a 180-degree rotation, the new direction of view, and where every persistent landmark should appear. For a side view, specify the source wall, a 90-degree turn, frame-left/frame-right landmarks and the relationship to both master and reverse plates.

Preserve scene style, material, time of day, light direction and object scale. Accept minor decorative variation when it does not affect staging; reject moved doors, reversed windows, changing furniture scale or contradictory light sources.

## Iteration discipline

When an image drifts, first revise the prompt or regenerate from the approved master. Avoid repeatedly editing the same raster when edits visibly degrade sharpness or identity. Record each approved asset with its prompt, intended role, version and continuity stage.
