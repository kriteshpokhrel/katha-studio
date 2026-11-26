# Branded reel pipeline

`python -m katha reel <project.json>` turns a beat-by-beat script into a branded
1080 × 1920, 30 fps vertical reel without user-supplied footage or voice. It is
the recommended path for faceless explainers; the older `render` command remains
for scene/footage assembly.

The format adapts the *concept* of the analysed reference reel: a static branded
canvas, a kinetic top headline, story-specific animated components, a numbered
"step" device, sound design and a branded outro. It does not copy that reel's
assets, wording, voice, music or exact layout.

## Install

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-reel.txt
npm ci   # installs HyperFrames and GSAP 3.13.0
```

FFmpeg/ffprobe must be on PATH, and HyperFrames needs Node 22+ and Chrome.
The default narration uses the online Microsoft Edge voice service through
`edge-tts`. Check its terms, and send it only text you are allowed to share.
Alternatively, import local narration and its Scribe word timestamps.

## Run

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -m katha reel examples\reel\jensen-huang.json
# Visual-storytelling proof: original diagrams, no downloaded images needed
.\.venv\Scripts\python.exe -m katha reel examples\reel\moon.json
# After reviewing output\<name>.mp4 and the storyboard:
.\.venv\Scripts\python.exe -m katha reel examples\reel\jensen-huang.json --approval "final export गर"
```

A preview run writes these files beside the project:

| Path | Content |
| --- | --- |
| `output/<name>.mp4` | Mixed preview |
| `output/<name>-storyboard.jpg` | Two frames per beat (25% and 75%), chronological left to right |
| `output/<name>-storyboard.md` | Timed beat table, captions, spoken text, scene purposes/actions, explicit sounds, sources, credits and review limitations; written before the preview render |
| `output/<name>-qa.json` | Every quality check, plus a project fingerprint |
| `.katha/<name>/` | Narration cache, HyperFrames composition, silent render, music and SFX stems (ignored by Git) |

If any quality check fails, the command exits with an error and lists the failure.
`--approval "final export गर"` renders nothing. It copies the preview to
`Exports/<name>.mp4`, but only if:

- the approval text matches exactly;
- the QA file passed;
- the fingerprint still matches the project, the brand, `reel.py`, `speech.py`,
  `sound.py`, `scenes.py`, the reel assets, local media/photos and bundled fonts;
- the preview's SHA-256 matches the video that passed QA.

A new preview attempt invalidates the previous QA report before building. A failed
attempt cannot accidentally export the earlier report or a partly replaced video.

## Project format

See [`examples/reel/jensen-huang.json`](../examples/reel/jensen-huang.json).

| Field | Meaning |
| --- | --- |
| `title`, `topic` | Storyboard title; topic label in the header |
| `profile` | Use `visual_storytelling` for new production. Omission retains `legacy` compatibility with older component scripts |
| `story` | Narration-first brief, hook candidates and sections; required by the production workflow for new reels, optional in the loader for existing projects |
| `voice` | `provider: edge`, `name` (default `ne-NP-SagarNeural`), `rate` and `pitch`; or `provider: scribe` with project-relative `audio` and `timestamps` paths |
| `music` | `seed`, `bpm` (60–140), `volume` (0–1, before ducking), `duck_ratio` (1–12, default 3); optional `asset` references local licensed/original audio instead of synthesis |
| `sfx.volume` | Independent effect gain, 0–1 (default 0.18); no automatic effect on every transition |
| `assets`, `scenes` | Local-media manifest and persistent visual scene definitions; see below |
| `outro.tail` | Seconds the outro holds after the last word (1–5) |
| `steps.label` | Optional caption for the numbered-steps device |
| `brand` | Optional path to a brand JSON; defaults to `brand/brand.json` |
| `sources` | Research sources and credits copied to the storyboard |
| `beats` | 3–75 beats. The last beat, and only the last, is the `outro` |

Each beat has:

- `say`: authoritative caption slice, at most 10 words. It need not be a sentence: preserve the continuous narration's punctuation across beats.
- `pronunciations` (optional): map individual caption words to their spoken form.
- `keyword`: whole caption words that get the accent marker in the headline.
- `visual`: the beat's animated component.
- `sound` (optional): `{"kind":"pop","cue":"word"}`. At most one editorial effect per beat; omit for silence. Kinds: `pop`, `tick`, `stamp`, `chime`, `whoosh`. No cue means beat start.
- `step` and `step_title` (optional): turn the beat into numbered point 1..N. The header then shows the step and segment progress.

For existing narration, `voice: {"provider":"scribe","audio":"narration.mp3",
"timestamps":"scribe.json"}` imports the provided audio and Scribe's
`segments[].words[]` (`text`, `start_time`, `end_time`). Whitespace entries
are ignored. Caption words still have to align with the transcript; use
pronunciation overrides for transcript normalization differences, and review
the transcription and synchronization by listening. Both input files are
included in the export fingerprint; mismatches and invalid timings fail.

For example:

```json
{
  "say": "NVIDIA मा CEO फर्किए।",
  "pronunciations": { "NVIDIA": "एनभिडिया", "CEO": "सीईओ" },
  "keyword": "CEO",
  "visual": { "type": "card", "title": "नेतृत्व" }
}
```

The visible caption keeps `NVIDIA` and `CEO`; the voice receives the Nepali
spellings. Keys match individual display words ignoring case and punctuation;
each replacement can contain multiple spoken words. A replacement applies to
each occurrence of that word in the beat. Cues and keywords refer to the
**caption** words, not the replacement. The producer must supply and review
appropriate spellings; the pipeline does not automatically transliterate text
or verify pronunciation. A wrong or unused key is an error.

### Narration first, caption beats second

The renderer already synthesizes the entire script in one request. The earlier
beat-first authoring convention encouraged disconnected headline fragments;
the fix is not adding pauses or just increasing the words allowed on screen.
Write the complete explanation first, using connected clauses and varied
sentence lengths, then segment it for captions and visual cues.

New productions include a `story` object. See
[`gold-reversal.json`](../examples/reel/gold-reversal.json) for the full example:

```json
{
  "audience": "Nepali household gold buyers",
  "takeaway": "Quoted gold rates and jewellery bills are different.",
  "target_seconds": 50,
  "hooks": [
    "सुनको दुई दिनको वृद्धि, एकै दिनमै मेटियो!",
    "सुन घट्यो, तर गहनाको बिल नि?",
    "सुनको भाउ बढ्दैमा जोखिम सकिन्छ?"
  ],
  "selected_hook": 0,
  "sections": [
    {"role": "hook", "text": "सुनको दुई दिनको वृद्धि, एकै दिनमै मेटियो!"},
    {"role": "explanation", "text": "Write the connected explanation here."},
    {"role": "cta", "text": "Write the final question here."}
  ]
}
```

This is the shape of the `story` value, not a standalone render project.
Replace the placeholder narration and supply matching `beats`.

- `audience` and `takeaway` must be non-empty; `target_seconds` is 20-150
  seconds including the outro hold.
- Provide exactly three distinct hook candidates, each at most eight
  whitespace-separated words. `selected_hook` is a zero-based index.
  The opening section must match that candidate exactly.
- Provide 3-12 sections. Supported roles: `hook`, `context`, `problem`,
  `explanation`, `step`, `result`, `impact`, `caveat`, `cta`. Only the first
  section is `hook`; only the last is `cta`. Choose middle sections for the
  subject: news need not pretend to be a three-step tutorial.
- Each section's text must equal consecutive complete `say` slices in order,
  including punctuation (whitespace differences are allowed). A sentence
  may cross caption boundaries; a narrative section must end at one.
  Every beat must be covered, and the CTA maps only to the outro.
  This checked repetition keeps the readable full script and the timed
  captions from drifting. Pronunciation overrides still operate per beat.
- Before rendering, the measured preview duration must be within 15% of
  target, with at least three seconds of tolerance. The same check appears
  in QA and gates export. Revise the script or explicitly reconsider its
  target; do not silently speed up speech or pad the video.

The storyboard shows the audience, takeaway, candidate hooks, continuous
narration and timed narrative sections before its caption/visual table.
These checks cannot establish naturalness, narrative logic, hook quality,
factual accuracy or pronunciation. A producer must review those separately.
Existing projects without `story` still load unchanged; no semantic score or
automatic topic-to-script generator is implied.

Word boundaries are mapped back to the original caption tokens, including
punctuation. If a provider splits one displayed word into several boundaries,
their times are combined; if a boundary crosses two displayed words or the
words cannot be matched, the build fails rather than inventing timing or
substituting provider text. A multiword pronunciation is displayed as one
caption token for the duration of that spoken phrase.

Visual types:

| `visual.type` | Fields |
| --- | --- |
| `photo` | `src` (local file) or `url` + `credit`; optional `stamp`, `stamp_cue` |
| `card` | `title`; optional `eyebrow`, `chip`, `latin`, `lines[{tag, text, cue}]` |
| `swap` | `from` / `to` `{name, initials, role}`, optional `cue` |
| `counter` | integer `to`, optional `label` |
| `stamp` | `text`; optional `eyebrow`, `title`, `cue` |
| `checklist`, `list` | `items[{text, cue}]` (1–5) |
| `timeline` | `items[{when, what, cue, live, chip}]` (1–5) |
| `scene` | `scene` ID, `purpose`, and optional narration-cued `actions`; objects persist across consecutive beats |
| `outro` | optional `comment_keyword` |

A `cue` is a spoken word in that beat. The element appears when the cue word is
spoken; without a cue, elements are spread across the line.

## Visual storytelling, not caption slides

Start with what the viewer needs to **see happen**, then write its short caption.
For software demonstrations, prefer an original screen recording, cropped to the
relevant action. Otherwise use a relevant licensed/generated foreground asset
or an original diagram with moving objects, connections and state changes.
Do not substitute a card repeating the spoken sentence.

[`moon.json`](../examples/reel/moon.json) is a complete example: a large phase
hook, a light/reflection explanation, then a persistent Sun/Earth/Moon model
with a synchronized Earth-view disc. Its labels are supporting annotations, not
the whole story. The top view is schematic: sizes, distances and orbital tilt
are omitted; the approximately 29.5-day phase cycle is not a sidereal orbit
measurement. Its phase display is idealized, not a local sky forecast.

[`gold-reversal.json`](../examples/reel/gold-reversal.json) is a dated Nepal
economy example with a persistent gold ingot, a sourced daily-price chart,
proportional change blocks and an illustrated jewellery bill. Run
`python -m katha reel examples\reel\gold-reversal.json` to recreate its review
preview. Its November 22-25, 2026 quotations are historical inputs, not live
prices; recheck the linked sources before repurposing it as current news.
The chart explicitly labels its truncated axis, and the script distinguishes
quoted gold rates from jewellery bills without predicting future prices.

Minimal scene excerpt (inside a normal reel project):

```json
{
  "profile": "visual_storytelling",
  "scenes": {
    "route": {
      "description": "A package travels to a destination",
      "objects": [
        {"id":"package","type":"rect","x":60,"y":160,
         "attrs":{"width":100,"height":80,"fill":"accent"}}
      ]
    }
  },
  "beats": [{
    "say": "पार्सल गन्तव्यतिर जान्छ।",
    "keyword": "गन्तव्यतिर",
    "visual": {
      "type":"scene","scene":"route","purpose":"Show delivery rather than a text card",
      "actions":[{
        "target":"package","cue":"गन्तव्यतिर","duration":0.5,
        "to":{"x":550},"meaning":"Move the package toward its destination"
      }]
    }
  }]
}
```

The excerpt still needs the remaining beats and final outro. A scene occupies
consecutive beats and is rendered once, not rebuilt at every caption change.
Each action starts at its caption-word cue, or beat start when omitted.
An action extending beyond its beat or overlapping an earlier action on the
same target/property is an error. Adjust the script or duration, not its timestamps
by guesswork. Motion follows a paused, seekable GSAP master timeline.

The stage is 768 × 548 at (120, 670) on the 1080 × 1920 canvas. Object types:
`group` (with `children`), `circle`, `ellipse`, `rect`, `line`, `path`, `text`,
`image`, `video`, `phase`. Give every object a unique lowercase/hyphen ID.
Use `attrs` for SVG geometry, `fill`, `stroke`, `stroke-width`, `font-size`
and `text-anchor`; arbitrary markup, JavaScript and CSS are not accepted.
Colors can be a brand token, `none`, or `#RRGGBB`. Text is escaped.

Animated state fields: `x`, `y`, `rotation`, `scale`, `opacity`, `draw` (stroke
reveal), `angle` (requires `orbit: {cx,cy,rx,ry}`) and `phase` (phase objects only).
`clip: {"r":80}` adds a circular clip. A phase disc has optional `attrs.r`:
0 degrees is new, 90 first quarter, 180 full, 270 last quarter.
Orbit angles translate an object without rotating its Sun-facing hemisphere.
Paths must be original or licensed geometry; this is not a general SVG importer.

### Real images, recordings and generated assets

Acquire assets **before** `reel`: use the existing `fetch` (Pexels key required)
or configurable external `generate` command from [usage](usage.md), record an
original screen capture, or create original artwork. Those commands use their
own acquisition project format, not a reel JSON. Add the resulting local files
to the reel manifest; `reel` does not search, download or generate them for you.

```json
{
  "assets": {
    "demo": {
      "kind":"video","src":"assets/demo.mp4","origin":"original",
      "credit":"Original screen recording","license":"Owned original; reviewed UI rights"
    },
    "bed": {
      "kind":"audio","src":"assets/bed.wav","origin":"licensed",
      "credit":"Creator and required attribution","license":"Exact reuse licence",
      "source":"https://example.com/the-asset-and-licence"
    }
  },
  "music": {"asset":"bed","volume":0.3,"duck_ratio":2}
}
```

Reference `demo` from a scene object:
`{"id":"screen","type":"video","asset":"demo","attrs":{"width":700,"height":400}}`.
Images use the same structure with `type: image`. Files are relative to the
reel project (absolute local paths also work). Supported: PNG/JPEG/WebP,
MP4, WAV/MP3/M4A. Every manifest entry needs `origin`, `credit` and `license`.
`licensed` and `generated` also require `source`; generated assets additionally
require `provider`, `prompt` and `cost` text. These are provenance records, not
proof that a licence or provider's claims are valid.

Media is probed and decoded before rendering. Video must cover its entire
persistent scene span: it starts at source time zero and plays muted.
Short video fails rather than silently freezing or looping; trim/extend it
explicitly. Audio beds loop and receive entry/exit fades. Local video sound,
source offsets and arbitrary multitrack audio editing are not supported.
Provider fees/terms and acquisition remain separate; no model, subscription,
credentials or automatic budget enforcement are included.

## Brand kit

[`brand/brand.json`](../brand/brand.json) holds the configurable identity:

- name, mark, handle and tagline;
- eight colours: `paper`, `dot`, `ink`, `muted`, `line`, `card`, `accent` and `on_accent`;
- the font folder;
- outro wording.

The selected **Saffron Signal** palette is the default: warm paper, dark ink,
and a deeper orange-red accent. The name, mark and handle remain provisional;
selecting the palette did not approve those. The bundled fonts are OFL-licensed:
Mukta (Devanagari), Bricolage Grotesque,
DM Serif Display Italic and JetBrains Mono. Their licences are in `brand/fonts/`.
To use another identity, copy the folder and point a project's `brand` at the
copy. See
[brand and production](brand-and-production.md).

## How it works

1. **Narration and alignment.** Optional pronunciation overrides are applied
   before `edge-tts`, or matched against the supplied Scribe transcript.
   Provider word boundaries are mapped back to the original `say` tokens.
   Ambiguous or mismatched boundaries stop the build.
2. **Timing.** Each beat starts 0.12 s before its first word. The outro holds for `outro.tail`.
3. **Plan and pacing.** The pipeline writes the timed storyboard before the
   preview render. It checks the interval between planned story-content reveals
   (such as a new card row, stamp or timeline item). A gap over three seconds
   fails before rendering; split a beat or add relevant, cued content and retry.
   The closing outro is exempt. Scene action spans on pictorial objects count,
   but text-only actions, captions, progress, decorative float and sound do not.
   In `visual_storytelling`, at least 75% of non-outro duration must use
   pictorial scenes/photos, with no more than one consecutive text-only beat.
4. **Composition.** One HyperFrames HTML composition is built with a single paused GSAP timeline, timed clips and inlined CSS and fonts. It contains:
   - a dotted paper canvas;
   - a header with the brand mark, topic or step, and a progress track;
   - a top kinetic headline, with words entering as spoken and an accent marker sweeping the keyword;
   - the beat component, whose cues are tied to spoken words;
   - a separately laid-out branded outro: identity, comment prompt and follow/handle
     groups with generous separation, no ambient float or looping CTA pulse.
     The Follow cue changes color; it is an animation, not an interactive button.
5. **Render.** `hyperframes render --strict -q delivery` produces a silent video.
6. **Sound.** The fallback is an original seeded warm pad, sparse plucks, bass
   and a soft low pulse, without bright hats/snare. Alternatively, `music.asset`
   selects your reviewed local bed. Effects are lower-pitched and only emitted
   where a beat explicitly requests `sound`; existing component scripts now
   have no automatic whooshes, reveal ticks or outro chimes.
7. **Mix.** Independent music/effect gains, a 3 kHz effect low-pass, and gentler
   configurable music ducking keep foreground speech separate. FFmpeg applies
   `sidechaincompress`, `loudnorm` (about −14 LUFS) and a limiter. Synthetic
   stems contain no downloaded music; a supplied bed needs separate rights.
   The final mix still requires listening: numerical checks cannot establish
   that effects are pleasant or the bed matches a reference.
8. **QA** checks:

   | Check | Limit |
   | --- | --- |
   | Duration | 20–150 s |
   | Speech rate | 1.8–3.4 words/s |
   | Beat length | 1–6 s (outro 2–9 s) |
   | Planned story-content reveal gap | at most 3 s per non-outro beat |
   | Pictorial duration (`visual_storytelling`, non-outro) | at least 75% |
   | Consecutive text-only beats (`visual_storytelling`) | at most 1 |
   | Words per beat | 10 or fewer |
   | Integrated loudness | −15.5 to −12.5 LUFS |
   | True peak | −1 dBTP or lower |
   | Motion share (frames with visible change) | at least 35% |
   | Longest static hold | 1.25 s or less |
   | Ink outside the safe area (x 65–916, y 270–1250; outro extends to y 1520) | 200 px or less |

For `visual_storytelling`, pixel motion is measured in the foreground stage
instead of the whole dotted canvas, excluding the top captions, header and
closing outro. The closing call to action may settle for reading; it does not
need decorative movement to satisfy story-motion checks.
The outro uses the lower safe canvas for separated identity, comment and follow
groups, leaving 400 px clear below its y 1520 boundary. Platform overlays still
need review; this is a repository layout boundary, not a universal platform rule.
Thresholds are unchanged. This measures change, not semantic quality. Structural
picture coverage can include unhelpful or hidden artwork; inspect actual frames.

## Regression checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
node tests\test_reel_scenes.cjs
# Optional real HyperFrames image/video integration render (FFmpeg, Node, Chrome):
$env:KATHA_RENDER_MEDIA_TEST = "1"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_scenes.py -q
Remove-Item Env:\KATHA_RENDER_MEDIA_TEST
```

## Limits

- The Edge Nepali voice is synthetic. Pronunciation and naturalness are not verified automatically. Disclose synthetic speech where platforms require it.
- QA checks measurable properties only. It cannot judge factual accuracy, taste, or whether the motion helps the story. Watch the preview before export.
- Pacing measures the scheduled component reveals, not whether they are
  relevant, legible, correctly rendered or semantically different; production
  review must check those separately. A failed gate does not rewrite a beat.
- The research, the script and the beat plan are written by the production agent. There is no topic-to-project generator yet.
- Two-minute reels fit the configured limits, but long-form quality and pacing
  have not yet been validated end to end.
- Photos need a licence that permits reuse, plus a credit.
- Rendering takes a few minutes on a laptop CPU or GPU.

## References

- [HyperFrames HTML schema](https://hyperframes.heygen.com/reference/html-schema.md) and [CLI](https://hyperframes.heygen.com/developers/cli.md)
- [GSAP timeline documentation](https://gsap.com/docs/v3/GSAP/Timeline/)
- [edge-tts](https://github.com/rany2/edge-tts)
- FFmpeg [`loudnorm`](https://ffmpeg.org/ffmpeg-filters.html#loudnorm), [`sidechaincompress`](https://ffmpeg.org/ffmpeg-filters.html#sidechaincompress) and [`alimiter`](https://ffmpeg.org/ffmpeg-filters.html#alimiter). The −14 LUFS target is a common level for streaming and short-form video, not a published platform rule.
