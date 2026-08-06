# Prompt Schemas

## Keyframe prompt

Write in this order:

1. format: ratio and intended use;
2. identity: exact character invariants;
3. current state: costume, damage, emotion and owned props;
4. action instant: one readable moment;
5. blocking: left/right/front/rear, gaze, contact and scale;
6. camera: shot size, angle, lens feel and composition;
7. environment: layout and persistent landmarks;
8. light: source, direction, color and interaction;
9. style: only the current project's approved style;
10. constraints: likely failure modes for this shot.

Do not include future motion in a still-image prompt except to define the selected action instant.

## Video prompt

Make the prompt directly pasteable. Do not include paths or internal notes.

```text
<ratio and continuity locks>.
0–Xs: <starting action and camera>.
X–Ys: <core action, physical weight and reactions>.
Y–Zs: <result, ending composition and edit handle>.
<environment/effect secondary motion>.
Avoid: <dynamic shot-specific failures>.
```

Name the fields to lock: face, hair, costume stage, prop count, positions, direction, environment structure and light source. Avoid generic “keep consistent” alone.

## Effect lifecycle

Specify source, onset, movement, peak, dissipation and scene interaction. Example pattern:

`The effect originates at the contact point, expands along the surface, peaks after impact, casts matching light on the subject and nearby objects, then dissipates without changing color or source.`

## UI and exact text

- Generate a clean plate or animate an approved UI image.
- Add exact text, gift codes, subtitles, logos and store marks in post.
- If using image-to-video with existing text, explicitly lock spelling, placement, scale and opacity; minimize motion around text.

## Dynamic negative constraints

Derive negatives from the shot:

- multi-character: identity swap, position swap, merged limbs;
- hands/contact: extra fingers, broken grip, changing hand, missing contact;
- movement: teleportation, wrong direction, sliding feet, no weight;
- continuity: changing prop count, light source or costume stage;
- effects: wrong origin, static effect, disappearing effect, no light interaction;
- camera: axis jump, unwanted zoom, excessive wide-angle distortion;
- UI: rewritten text, extra buttons, distorted panels;
- delivery: text, logo or watermark when a clean plate is required.
