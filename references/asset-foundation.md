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

Separate identity from form. Keep one base identity record, then create one asset per visible stage or transformation. A sheet containing a human form, upgraded armor and creature form is source evidence only; reinterpret it into distinct confirmation assets before downstream use. Every shot must bind to exactly one active stage unless the shot itself depicts the transition.

## Related and derived identities

When the script establishes family relationships, create and approve the parent or source identities before dependent identities. Choose a few observable inherited anchors such as face shape, brow/eye structure, hair texture, skin tone or a distinctive mark, while preserving age, sex, styling and individual variation. Do not clone one face or require every relative to share every trait.

For a creature, mutation, older/younger form or other derived identity, preserve only the anchors needed for recognition and explicitly list what may transform. Store the result as its own versioned stage asset. Generate the dependent asset from approved sources when the image tool supports references; otherwise carry the inherited anchors into the prompt and flag the resemblance as provisional for review.

## Prop triage

Register a prop as a reusable asset when at least one condition applies:

- it recurs across shots or changes owner/state;
- an action depends on its exact count, geometry or orientation;
- it is a product, reward, weapon, UI-linked object or other selling-point carrier;
- inconsistency would break causality or make a cut fail.

Leave incidental one-off set dressing in shot data. A one-off hero prop can still deserve an asset; recurrence is a filter, not an absolute exclusion rule.

## Environment master

For recurring locations, establish an empty environment plate before character staging when practical. Record:

- camera position, height, view direction and lens feel;
- persistent landmarks and entrances;
- usable floor area and character blocking zones;
- dominant light source, direction, color and intensity relationship;
- materials, wear and atmosphere;
- clean areas reserved for characters, effects or UI.

Prefer an eye-level frontal master when no other angle is required; it is usually easier to reverse-engineer and stage consistently. This is a default, not a universal aesthetic rule.

## Exterior route topology

Before generating plates for a journey, pursuit, battlefield or multi-node exterior, record a simple top-down route contract:

- ordered landmark nodes and their visual identifiers;
- north/reference direction, slope/elevation and approach direction;
- character route, entrances, exits and major occluders;
- relative spacing or travel time when the story makes it relevant;
- safe, risky and impossible camera directions;
- which adjacent nodes can plausibly appear together in one view.

Use qualitative spacing when exact measurements are unknown. The topology exists to prevent contradictory travel direction, landmark placement and reverse coverage, not to fabricate survey data.

## Coverage expansion and color anchors

Expand a recurring location only after one topology-correct master or connected-space pack is approved. A contact sheet or nine-grid may explore purposeful combinations of camera zone, shot size, height and authorized lighting state. Reject cells that mirror landmarks, invent openings, alter scale or violate the floor plan; register approved cells as individual assets rather than treating the whole grid as approved.

When palette or lighting continuity is fragile, create compact color-and-light anchors for each materially different condition, such as exterior night and interior practical light. Record dominant and secondary hues, black/white point behavior, contrast, saturation, practical source direction, skin-light relationship and prohibited color drift. Swatches support these written constraints but do not replace them.

For a doorway connecting two recurring spaces, store one spatial contract before generating any plate: room names, north arrow, camera zones, threshold geometry, hinge side, swing direction, floor and wall materials, persistent landmarks, light sources and blocking zones. Mood references may control style but never determine topology.

## Complete connected-space pack

For two connected recurring spaces A and B, generate and approve at least four empty plates as one linked set:

1. `A-master`: camera in A looking toward the shared threshold and B;
2. `A-reverse`: camera near the threshold or B looking back into A;
3. `B-master`: camera in B looking toward the threshold and A;
4. `B-reverse`: camera near the threshold or A looking back into B.

For a corridor and room, this means corridor forward, corridor reverse, room forward and room reverse. Add left/right side plates only when action blocking, entrances, furniture or effects need them.

Record for every plate:

- camera zone, height, heading and lens family;
- threshold position and which space lies beyond it;
- physical hinge side and swing arc, described in world coordinates before screen coordinates;
- frame-left/frame-right position of asymmetric landmarks;
- shared floor seams, wall ribs, windows, furniture and practical lights;
- allowed character and effect zones;
- the plate IDs that are its direct reverse and adjacent views.

Validate the set with a top-down floor plan. A reverse view may swap screen-left and screen-right, but it must not mirror written symbols, move physical hinges, change the door's swing, invent openings, alter room scale or relocate light sources. Never generate a reverse plate independently from a mood image or from the phrase “same room.”

## Reference-to-asset gate

Use this order: raw references; extracted authoritative traits and exclusions; clean turnaround or complete connected-space pack; board review of the linked set; approved versioned asset IDs; shot binding and keyframe generation. Raw references may be branded, cropped, mixed or multi-subject. Confirmation assets must be clean, single-purpose, stage-specific and free of unrelated text or logos.

## Reverse and side views

Generate alternate views from a spatial contract, not from “same room” alone.

For a reverse view, specify the original camera position, a 180-degree rotation, the new direction of view, and where every persistent landmark should appear. For a side view, specify the source wall, a 90-degree turn, frame-left/frame-right landmarks and the relationship to both master and reverse plates.

Preserve scene style, material, time of day, light direction and object scale. Accept minor decorative variation when it does not affect staging; reject moved doors, reversed windows, changing furniture scale or contradictory light sources.

## Iteration discipline

When an image drifts, first revise the prompt or regenerate from the approved master. Avoid repeatedly editing the same raster when edits visibly degrade sharpness or identity. Record each approved asset with its prompt, intended role, version and continuity stage.
