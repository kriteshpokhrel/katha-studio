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
Narration uses the online Microsoft Edge voice service through `edge-tts`. Check
its terms, and send it only text you are allowed to share.

## Run

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -m katha reel examples\reel\jensen-huang.json
# After reviewing output\<name>.mp4 and the storyboard:
.\.venv\Scripts\python.exe -m katha reel examples\reel\jensen-huang.json --approval "final export गर"
```

A preview run writes these files beside the project:

| Path | Content |
| --- | --- |
| `output/<name>.mp4` | Mixed preview |
| `output/<name>-storyboard.jpg` | Contact sheet with one frame per beat |
| `output/<name>-storyboard.md` | Timed beat table, sources and credits |
| `output/<name>-qa.json` | Every quality check, plus a project fingerprint |
| `.katha/<name>/` | Narration cache, HyperFrames composition, silent render, music and SFX stems (ignored by Git) |

If any quality check fails, the command exits with an error and lists the failure.
`--approval "final export गर"` renders nothing. It copies the preview to
`Exports/<name>.mp4`, but only if:

- the approval text matches exactly;
- the QA file passed;
- the fingerprint still matches the project, the brand, `reel.py`, `sound.py` and the reel assets.

## Project format

See [`examples/reel/jensen-huang.json`](../examples/reel/jensen-huang.json).

| Field | Meaning |
| --- | --- |
| `title`, `topic` | Storyboard title; topic label in the header |
| `voice` | `provider: edge`, `name` (default `ne-NP-SagarNeural`), `rate` such as `+8%`, `pitch` such as `-2Hz` |
| `music` | `seed`, `bpm` and `volume` (0–1, before ducking) for the generated bed |
| `outro.tail` | Seconds the outro holds after the last word (1–5) |
| `steps.label` | Optional caption for the numbered-steps device |
| `brand` | Optional path to a brand JSON; defaults to `brand/brand.json` |
| `sources` | Research sources and credits copied to the storyboard |
| `beats` | 3–30 beats. The last beat, and only the last, is the `outro` |

Each beat has:

- `say`: one spoken line. Keep it to about 10 words or fewer.
- `keyword`: whole spoken words that get the accent marker in the headline.
- `visual`: the beat's animated component.
- `step` and `step_title` (optional): turn the beat into numbered point 1..N. The header then shows the step and segment progress.

Write numbers as spoken words where possible. Narration timing is matched to
`say`, so unusual punctuation or digits can stop the build with an alignment
error.

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
| `outro` | optional `comment_keyword` |

A `cue` is a spoken word in that beat. The element appears when the cue word is
spoken; without a cue, elements are spread across the line.

## Brand kit

[`brand/brand.json`](../brand/brand.json) holds the configurable identity:

- name, mark, handle and tagline;
- eight colours: `paper`, `dot`, `ink`, `muted`, `line`, `card`, `accent` and `on_accent`;
- the font folder;
- outro wording.

The bundled fonts are OFL-licensed: Mukta (Devanagari), Bricolage Grotesque,
DM Serif Display Italic and JetBrains Mono. Their licences are in `brand/fonts/`.
To use another identity, copy the folder and point a project's `brand` at the
copy. The shipped identity is a **proposal** and has not been approved; see
[brand and production](brand-and-production.md).

## How it works

1. **Narration and alignment.** `edge-tts` returns word boundaries. They are split per beat by matching the normalised `say` text. A mismatch stops the build; it never guesses.
2. **Timing.** Each beat starts 0.12 s before its first word. The outro holds for `outro.tail`.
3. **Composition.** One HyperFrames HTML composition is built with a single paused GSAP timeline, timed clips and inlined CSS and fonts. It contains:
   - a dotted paper canvas;
   - a header with the brand mark, topic or step, and a progress track;
   - a top kinetic headline, with words entering as spoken and an accent marker sweeping the keyword;
   - the beat component, whose cues are tied to spoken words;
   - the branded outro, with a comment box and a Follow button that turns to Following.
4. **Render.** `hyperframes render --strict -q delivery` produces a silent video.
5. **Sound.** `katha/sound.py` makes an original, seeded procedural music bed with numpy: a pad, an arpeggio, bass and soft drums. It also makes SFX:
   - a whoosh on beat changes;
   - pops, ticks and stamps on reveals;
   - a chime on the outro.

   Nothing is downloaded, so there are no music-licence questions.
6. **Mix.** FFmpeg ducks the music under the voice (`sidechaincompress`) and mixes voice, music and SFX. It then normalises loudness (`loudnorm`, about −14 LUFS) and applies a −3.5 dB limiter (`alimiter`).
7. **QA** checks:

   | Check | Limit |
   | --- | --- |
   | Duration | 20–90 s |
   | Speech rate | 1.8–3.4 words/s |
   | Beat length | 1–6 s (outro 2–9 s) |
   | Words per beat | 10 or fewer |
   | Integrated loudness | −15.5 to −12.5 LUFS |
   | True peak | −1 dBTP or lower |
   | Motion share (frames with visible change) | at least 35% |
   | Longest static hold | 1.25 s or less |
   | Ink outside the text safe area (x 65–916, y 270–1250) | 200 px or less |

## Limits

- The Edge Nepali voice is synthetic. Pronunciation and naturalness are not verified automatically. Disclose synthetic speech where platforms require it.
- QA checks measurable properties only. It cannot judge factual accuracy, taste, or whether the motion helps the story. Watch the preview before export.
- The research, the script and the beat plan are written by the production agent. There is no topic-to-project generator yet.
- Photos need a licence that permits reuse, plus a credit.
- Rendering takes a few minutes on a laptop CPU or GPU.

## References

- [HyperFrames HTML schema](https://hyperframes.heygen.com/reference/html-schema.md) and [CLI](https://hyperframes.heygen.com/developers/cli.md)
- [GSAP timeline documentation](https://gsap.com/docs/v3/GSAP/Timeline/)
- [edge-tts](https://github.com/rany2/edge-tts)
- FFmpeg [`loudnorm`](https://ffmpeg.org/ffmpeg-filters.html#loudnorm), [`sidechaincompress`](https://ffmpeg.org/ffmpeg-filters.html#sidechaincompress) and [`alimiter`](https://ffmpeg.org/ffmpeg-filters.html#alimiter). The −14 LUFS target is a common level for streaming and short-form video, not a published platform rule.
