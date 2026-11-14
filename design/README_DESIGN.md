# Khet Sathi UI design bundle

Exported on 2026-11-14 (screens updated the same day, version 1794632161-9240: frosted-glass cards, a warmer accent, and the new 6-month screen) from the UI teammate's Claude Design artifact "Khet Sathi: App Screens"
(https://claude.ai/artifact/XrimQmSPQywSytu48uw3pP). These are DESIGN files, not a deployable website:
each `screens/*.dc.html` needs the design tool's own runtime (`support.js`, `<x-dc>` templates) and every
text and number in them is hard-coded sample content. Use them as the visual and wording specification
for the real static site in `site/`.

## Screens

Phone (390 x 844): `Main` (1 Home), `Photo` (2 Photo from above), `Parts` (3 Your farm's parts),
`Robot` (4 Soil test), `Choose` (5 What to see), `Today` (6a Your field today), `Future` (6b Next 3 months), `Future6` (6c Next 6 months),
`P0_Prototype` (the clickable phone flow).

Web (1440 x 900): `W1_Home` ... `W8_Future6` (the same steps), `W0_Prototype` (the clickable web flow).

`canvas.json` lists the boards and their sizes. Each screen holds English and Nepali strings in its
`<script type="text/x-dc">` block.

## Images (`assets/`), referenced in the screens as `/_blob/<id>`

| File | Used by |
| --- | --- |
| `4f0b25b11732b3cab6a3285746008d0b.svg` | background of every phone screen |
| `3aa695d5bdb8271424d72ab091c78b64.svg` | background of the web screens 2 to 7 and the web prototype |
| `e400c3e133fe4d41d2c3e7591df34505.webp` | the farm illustration on both home screens |
| `90f92978700e4db452626990662eb262.svg` | phone home screen |

Fonts: Inter Tight, Inter and Mukta (Google Fonts).
