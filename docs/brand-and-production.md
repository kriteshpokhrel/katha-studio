# छेउबाट: proposed brand and production standard

**Status:** Saffron Signal was selected as the default palette. The channel name,
mark and handle remain proposals, not a finalized brand. Check the name, handle,
domain and trademarks before adopting or publishing under it.

## Brand recommendation

**Channel:** छेउबाट | Chheubata

**Production identity:** Katha Studio

**Pronunciation:** छे-उ-बा-ट

**Idea:** Look at a subject from alongside it: notice the detail, trade-off, or question people tend to miss.

**Why this name:** It has a conversational Nepali rhythm and leaves room for money, books, technology, culture, or an unexpected standalone subject. The promise is a thoughtful perspective, not expertise in every subject or a forced contrarian take. `Katha Studio` remains the production/repository name, not the channel name. The Roman spelling is a practical proposal, not a confirmed handle.

The subject can change; the recurring editorial move is to begin with something familiar and make one overlooked part understandable. No slogan is required in every video.

**Voice:** observant, calm, specific. Use natural Nepali; use an English term when it is clearer, and explain jargon. Sound like someone sharing an interesting observation, not a motivational speaker or a presenter claiming certainty. Avoid exaggerated wealth promises, fearbait, copied scripts, and sensational medical claims.

**Editorial test:** What is the particular detail the viewer might not have noticed? Is it true and appropriately sourced? Does the viewer understand why it matters? Do not invent a surprising twist when a straightforward explanation is better.

## Series architecture

Series are editorial formats, not separate sub-brands. Use a small, plain-text label only when it helps the viewer understand the episode:

| Format | Use | Example episode framing |
|---|---|---|
| **पैसा** | Money, work, decisions | A house can have value and still cost you money each month |
| **पुस्तकबाट** | Ideas inspired by books | Examine one idea in original words, with its limitations |
| **यस्तो किन?** | Everyday questions | Why a familiar thing works the way it does |
| **प्रविधि** | Technology and its consequences | A new tool, what it actually changes, and what it does not |
| **बिना शृङ्खला** | Standalone experiments | No label is needed; the subject is the headline |

These are working labels, not fixed categories. A standalone video should still feel related through its editorial perspective, voice, and restrained treatment—not a repeated intro animation.

## Visual identity

- **Look:** a quiet editorial notebook, not a neon explainer template. Use a consistent, static branded background as the canvas; story-specific foreground elements carry the explanation. Keep deliberate space and restrained color. The chosen palette does not finalize the channel identity.
- **Distinctive device:** one thin, short vertical *margin mark* in muted terracotta beside an occasional annotation. It connects to the name without illustrating an eye, lightbulb, speech bubble, or play button. It is not a permanent border, progress bar, or watermark.
- **Palette (selected Saffron Signal, implemented in `brand/brand.json`):** warm paper `#F2EEE6` with a subtle dot grid `#D6D0C3`, ink `#151413`, muted `#706B62`, card `#FFFCF6`, and orange-red accent `#D83C10`, used for keyword markers, the brand mark, step numbers and the Follow button. Colors remain configurable for other users.
- **Typography (bundled, OFL):** [Mukta](https://fonts.google.com/specimen/Mukta) for Devanagari headlines and labels, Bricolage Grotesque for Latin names, DM Serif Display Italic for step numerals, JetBrains Mono for small tags. Licences are in `brand/fonts/`.
- **Wordmark direction:** set `छेउबाट` plainly in a carefully spaced Devanagari wordmark, with the margin mark separated from—not embedded in—the letters. Use `CHHEUBATA` only when Latin is needed. A designer should refine the lettering, spacing, avatar, and one-color versions; no finalized logo or trademark clearance exists yet.
- **Motion language:** animate the foreground in service of the script: reveal, connect, replace or move relevant photographs, dates, diagrams and brief annotations. A margin mark may draw on briefly for an observation, then leave. No animated logo intro, floating particles, repetitive zooms, or decorative graphs. Meaningful motion and editorial pacing matter; a succession of static text slides is not enough.
- **Visual assets:** use story-specific original or licensed photographs, documents, motion graphics or footage as foreground elements when they add context. Do not use unrelated stock clips as a moving background or imply illustrative material depicts the actual event. Check rights, attribution, likeness, legibility and generated-asset errors.
- **On-screen hierarchy:** story-specific foreground first; short captions second; optional annotation or channel signature last. Keep the signature restrained and the background consistent without treating the proposed name or logo as approved.
- **Layout quality:** align elements to a deliberate grid, use consistent margins and spacing, and give each beat a clear visual focal point. Check text size, contrast, line breaks and actual bounds at phone size; do not crowd the canvas with unrelated labels or competing cards. The rejected pilot did not meet this standard.
- **Outro spacing:** keep identity, comment and follow/handle in separate groups, with 96 px between them and no perpetual pulse/float. The outro can extend to y 1520, leaving the bottom 400 px clear; other beats retain y 1250. Check the target platform's actual overlays.

### One episode, three applications

For a book-inspired lesson about money, use an original opening such as **“घरको मूल्य छ। तर हरेक महिना पैसा कता जान्छ?”** On the consistent background, animate a clear cash-flow comparison with relevant, properly licensed imagery when it adds context. A small margin note can distinguish *value* from *monthly cash flow*. The narrator explains both the opportunity and the ongoing costs; white/yellow captions follow the actual speech.

- **Cover:** the consistent background, a short readable Nepali question and, when useful, a relevant licensed visual. No generic “secret” claim.
- **In-video:** animated story-specific elements and restrained annotations; the proposed wordmark need not appear.
- **End:** a quiet branded background or closing note. Do not use the proposed wordmark as a finalized identity.

This is a concept, not a claim that the current renderer automatically creates the cover, wordmark, annotation motion, or finished edit.

## Caption and voice standard

- Nepali is the initial audience, with other languages configurable. For this channel, prefer a natural-sounding male narrator. The reel default is `ne-NP-SagarNeural` at `+8%` rate, but a male or synthetic voice is not automatically natural. The older `render` workflow can omit narration; `reel` currently requires it. Review pronunciation and pacing. Disclose synthetic speech as the platform requires, and do not imitate a real person's voice without permission.
- **Reel captions (the `reel` command):** one short script line per beat (10 words or fewer), shown as a kinetic headline at the top of the safe area. Caption text comes from the script; optional word-level pronunciations can differ. The provider's word boundaries time the reveal, and an accent marker sweeps the keyword. Unmatched or ambiguous alignment fails rather than substituting provider text. The headline is 56–78 px, depending on line length.
- **Footage captions (the older `render` command):** white timed word groups, with the spoken word in yellow and a dark outline, in a lower-middle safe area.
- Keep captions accurate to the spoken words, legible at phone size, and synchronized through edits.
- Sound: a warm original procedural bed or reviewed local licensed music under the narration. Use sparse, explicitly cued SFX, not an effect on every transition/reveal. `music.volume`, `music.duck_ratio` and `sfx.volume` control balance independently; effects receive a 3 kHz low-pass. Loudness is normalised to about −14 LUFS with a peak limiter. These measurable controls cannot replace listening on phone speakers.

### Approved audio baseline

On 2026-11-25, the user approved the Moon **audio-only** revision after its music
gain was halved from 0.4 to 0.2 (approximately -6 dB). Use this balance as the
starting point for new reels, rather than reverting to the louder preview:

```json
{
  "music": {"seed": 12, "bpm": 78, "volume": 0.2, "duck_ratio": 2},
  "sfx": {"volume": 0.15}
}
```

These settings are saved in `examples/reel/moon.json`. They are an explicit
production baseline, not a change to every omitted-field CLI default. Keep
narration in front, with continuous quiet music and sparse, cued effects; the
Moon proof uses only a pop and a chime. Seed/BPM describe that original bed,
not a requirement to use identical music for every topic. Different voices,
recordings and licensed beds still need balance review; gain 0.2 does not
guarantee the same perceived loudness across source material.

The approved reference was `output/moon-quieter-music.mp3` (generated, not
tracked). The previous video preview still contains the louder mix: regenerate
it from the saved project before any final export. This audio approval does
not approve the full video, channel identity, pronunciation independently,
or final export; the exact **final export गर** gate remains required.

## Repeatable production workflow

The production agent carries out research, scripting, sourcing, editing and quality checks. Do not assign routine manual production or transcript correction to the user. If tools or evidence are insufficient to establish quality, report the limitation rather than presenting an unchecked result as correct. The user's previously requested final-export approval remains separate from production work.

1. **Idea and brief.** Choose the audience, one takeaway, series label if appropriate, format, intended duration, and spending cap. Separate a book's ideas from its copyrighted wording and audiovisual adaptations.
2. **Research.** Cross-check claims with primary or reputable sources. Keep URLs, access dates, assumptions, and limitations. Financial, health, legal, and other consequential topics need extra care and must not present generic educational content as personalized advice.
3. **Script.** Write an original hook, context, explanation or example, and a clear takeaway. Plan for roughly two minutes when the story supports it; do not pad. Make each line easy to say naturally in Nepali.
4. **Storyboard review.** Use `profile: visual_storytelling` for new episodes. Choose the visible action for each line before its caption: original screen recording when demonstrating software, otherwise relevant imagery or a persistent object scene. The pipeline writes purposes, cued actions, sounds and source/license details before rendering; it rejects gaps over three seconds and requires at least 75% pictorial content duration with no consecutive text-only sequence. These structural gates cannot establish relevance. The contact sheet contains two frames per beat to expose changes rather than just slide layouts.
5. **Acquire and review assets.** Source or create the foreground elements and sound appropriate to the story. Review people and brands, audio, licenses, and creator credits. Record provider/model, prompt where relevant, costs, and provenance. Do not ingest a source reel as reusable content without rights.
6. **Narrate and caption.** Generate or record speech, review pronunciation, and align captions to the reviewed script. `reel` uses an accent-highlighted headline; the older `render` command uses white/yellow captions. Confirm that edits do not desynchronize audio and text.
7. **Edit and finish.** The `reel` command assembles branded components, transitions, narration, a procedural music bed and effects. The older `render` workflow supports basic scene assembly, not automatic cinematic editing or music mixing. Aim for 1080 × 1920 at 30 fps. Keep text within x 65–916 and y 270–1250, then check platform overlays and real text bounds; sampled pixel checks cannot guarantee glyph bounds or readability.
8. **Quality gate.** The production agent checks the complete video with automated technical checks and available visual/audio AI. Check opening and ending, visual relevance and motion, facts, voice, caption size/contrast/sync/safe areas, licensing and attribution, output dimensions, duration, and the intended platform's current rules. Do not delegate routine review or correction to the user. If available tools cannot verify a material claim or speech transcription, report that limitation rather than presenting it as correct.
9. **Final export and publish.** Do not render a final or write to `Exports` until the user explicitly says **final export गर**. Export a clean vertical master and adapt captions, cover, title, description, disclosures, and credits per platform. Publish manually after approval. Review retention, completion, and meaningful comments per platform; compare changes to the hook and pacing without assuming metrics are identical across platforms.

Optional raw-footage work starts with local Whisper transcription, but current Nepali accuracy has failed a real sample; the transcript is not reliable for final captions. Do not ask the user to correct it. Cuts, 110–120% punch-ins every 2–4 seconds where appropriate, numbered badges, short motion graphics, licensed music, and SFX are not automated features. For a before/after comparison, require actual source and edited footage, show the narration script first, then show a storyboard with matching moments before the final-export gate. Voice providers, including ElevenLabs, are not integrated.

## Operating rhythm and costs

Target **three videos per week**. Batch idea research and scripts, acquire visuals and voices, then edit and review each episode individually. Vary series and standalone topics without filling a slot with low-quality material. Track a simple production record per video: script and sources, shot list, asset licenses and credits, provider/model, narration voice, duration, review status, platform links, and actual spend.

The target is **under NPR 5,000 per month**, not a guarantee. Check current local prices, exchange rates, API quotas, and terms before using any provider. Track actual usage; leave room for compute, data, and editing. The repository does not enforce a budget or include a free unlimited AI-video model.

## Current implementation versus the target

| Capability | Current state |
|---|---|
| Branded explainer reel (canvas, kinetic headline, animated components, steps, outro, music, SFX, mix, QA) | Implemented by `python -m katha reel`; see [reel pipeline](reel-pipeline.md) |
| Original scripts, research, brand design, editing judgment | Production agent writes the beat script; no topic-to-project generator yet |
| Stock photos and moving Pexels footage | API key required; provider limits and rights apply; background footage is not the preferred default |
| AI-generated images or video | External command adapter only; no model, provider, or credentials included |
| Nepali neural narration | Online Edge provider; optional per-word spoken forms; timestamps and pronunciation require review |
| White/yellow word captions | Burned in for generated narration; provider word boundaries are checked against the script and audio, but pronunciation and legibility are not automatically guaranteed |
| Preparation | `prepare` currently requires video assets, so it cannot produce the preferred static-background storyboard; it validates streams and generates configured narration but cannot judge quality |
| Foreground screen recordings and media | Local images and muted MP4s are supported inside persistent scenes, with rights metadata and stream/length checks; no automatic recording, source offsets or cinematic cut editor |
| Platform adaptation and publishing | Manual; no automatic upload or scheduling |

Use [the provided reference](https://www.tiktok.com/@aitips.nepali/video/7708399596870831367) as inspiration for a stable canvas and animated editorial information, not as permission to reuse its assets, narration or exact design. Review the proposed identity before treating its name, logo, or styling as final.
