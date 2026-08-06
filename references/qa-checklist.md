# QA Checklist

## Keyframe gate

- correct character identity, face, hair and defining marks;
- correct costume state, weapon, prop and accessory count;
- correct left/right placement, gaze, direction and contact point;
- hands, fingers, joints and anatomy plausible;
- environment layout and light source match adjacent shots;
- shot size differs meaningfully from neighbors when intended;
- subject and selling point read at thumbnail size;
- safe areas reserved; no unintended text or watermark.

## Motion gate

- action has anticipation, core action, impact/result and reaction;
- movement direction and exit connect to the next shot;
- character does not freeze during shooting, flying, combat or reaction;
- recoil, weight shift, landing, impact and cloth/hair response are credible;
- camera movement supports the action and does not hide it;
- effect follows the subject, has a lifecycle and lights the environment;
- no face drift, identity swap, position swap or unexplained costume change;
- no frame drop, severe blur, tearing, morphing or watermark.

## Edit gate

- hook arrives early;
- no repeated framing or redundant information;
- impacts, reveals, reactions and music/SFX hits align;
- UI and exact text remain readable long enough;
- generated shots, gameplay and end card have intentional transitions;
- grade, sharpness, fps and perceived motion are consistent.

## Final delivery gate

- ratio, resolution, fps, duration and codec match the brief;
- all exact text, subtitles, gift codes, logos and store badges are correct;
- clean version and source segments are included when required;
- prompts, projects and version notes are included;
- no unlicensed placeholder or unrelated game asset remains;
- final contact sheet shows stable identity, costume stages and color continuity.

## Feedback format

Write every issue as:

`Shot ID | time range | observed problem | required visible change | fields to preserve | acceptance test`

Example:

`C04-B | 00:01.2–00:02.0 | muzzle flash has no recoil and projectile direction conflicts with next shot | add shoulder recoil, short camera shake and a fast thin light trail moving screen-right | preserve face, weapon and background | character moves on fire and trail exits toward next shot`
