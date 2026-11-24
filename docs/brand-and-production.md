# छेउबाट: proposed brand and production standard

**Status: proposal, not a finalized brand.** Check the name, handle, domain, and trademarks before adopting or publishing under it. This document proposes a consistent creative direction; it does not claim that the current software can automatically produce the finished style.

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

- **Look:** a quiet editorial notebook, not a neon explainer template. Real footage fills the frame; a brief note or annotation enters from the margin when it adds context. Keep deliberate space and let the subject carry the color.
- **Distinctive device:** one thin, short vertical *margin mark* in muted terracotta beside an occasional annotation. It connects to the name without illustrating an eye, lightbulb, speech bubble, or play button. It is not a permanent border, progress bar, or watermark.
- **Palette:** charcoal `#262824`, paper `#EEEAE0`, muted terracotta `#A45D46`. Use these sparingly for the wordmark, cover, and margin note; footage need not be recolored. Yellow remains reserved for the spoken-word caption highlight requested for the videos—it is not the whole brand.
- **Typography:** try [Mukta](https://fonts.google.com/specimen/Mukta) for legible Devanagari and Latin; it is available under the [SIL Open Font License](https://github.com/google/fonts/blob/main/ofl/mukta/OFL.txt). Use a medium weight for notes, bold only for captions, and a black outline or shadow over footage. The current CLI examples use Nirmala UI; Mukta is a proposed choice, not a bundled or installed font.
- **Wordmark direction:** set `छेउबाट` plainly in a carefully spaced Devanagari wordmark, with the margin mark separated from—not embedded in—the letters. Use `CHHEUBATA` only when Latin is needed. A designer should refine the lettering, spacing, avatar, and one-color versions; no finalized logo or trademark clearance exists yet.
- **Motion language:** show the story moving: relevant footage, motivated cuts, and restrained annotations tracking the subject. A margin mark may draw on briefly for an observation, then leave. No animated logo intro, floating particles, repetitive zooms, or decorative graphs.
- **Visual assets:** use relevant licensed footage, original animation, or AI-generated video when a configured provider actually produces it. Prioritize believable scenes, varied shot sizes, and meaningful visual change. Do not use a low-detail icon or AI image with a slow zoom as a stand-in for a moving shot. Check hands, faces, spelling, and physical continuity in generated footage.
- **On-screen hierarchy:** footage and subject first; short captions second; optional annotation or channel signature last. Avoid permanent thick cards that hide the action. The signature can appear briefly at the end; it need not occupy every frame.

### One episode, three applications

For a book-inspired lesson about money, use an original opening such as **“घरको मूल्य छ। तर हरेक महिना पैसा कता जान्छ?”** Show a real household or relevant licensed footage, not a house icon on a static slide. A small margin note can distinguish *value* from *monthly cash flow*. The narrator explains both the opportunity and the ongoing costs; white/yellow captions follow the actual speech.

- **Cover:** one relevant frame, dark enough for contrast; a short Nepali question in paper-white; a small terracotta margin mark. No portrait cutout, arrows, emoji, or generic “secret” claim.
- **In-video:** real moving images and restrained annotations; the wordmark is absent while the explanation is playing.
- **End:** a short `छेउबाट` wordmark on the final footage or a quiet plain background. No mandatory logo sting or call to follow.

This is a concept, not a claim that the current renderer automatically creates the cover, wordmark, annotation motion, or finished edit.

## Caption and voice standard

- Nepali is the default, with other languages configurable. Narration is optional when a story works without it, but a voice-led episode should use natural, well-paced speech and reviewed pronunciation. Disclose synthetic speech as required by the platform; do not imitate a real person's voice without permission.
- Show short, timed word groups in **white**, highlighting the currently spoken word in **yellow**, with a dark outline. Use actual word timestamps where available. Do not place an entire paragraph on screen.
- Starting point for a 1080 × 1920 master: 60–80 px caption font, centered in a lower-middle safe area; adjust for glyphs, screen size, backgrounds, and platform overlays. Avoid covering faces. These are starting points, not guaranteed platform-safe measurements: check each platform's current interface and preview on a phone.
- Keep captions accurate to the spoken words, legible at normal viewing size, and synchronized through pauses and edits. Ensure the yellow remains distinguishable from the background; use the outline or adjust the shot, not tiny type.
- Use only licensed or original background music. Keep it below speech, avoid abrupt audio cuts, and listen on phone speakers and headphones. Review pronunciation and facts manually; a synthetic voice is not an authoritative source.

## Repeatable production workflow

The production agent carries out research, scripting, sourcing, editing and quality checks. Do not assign routine manual production or transcript correction to the user. If tools or evidence are insufficient to establish quality, report the limitation rather than presenting an unchecked result as correct. The user's previously requested final-export approval remains separate from production work.

1. **Idea and brief.** Choose the audience, one takeaway, series label if appropriate, format, intended duration, and spending cap. Separate a book's ideas from its copyrighted wording and audiovisual adaptations.
2. **Research.** Cross-check claims with primary or reputable sources. Keep URLs, access dates, assumptions, and limitations. Financial, health, legal, and other consequential topics need extra care and must not present generic educational content as personalized advice.
3. **Script.** Write an original hook, context, explanation or example, and a clear takeaway. Plan for roughly two minutes when the story supports it; do not pad. Make each line easy to say naturally in Nepali.
4. **Storyboard review.** Before any final render, show a shot plan mapping time, spoken words, actual moving visual, motion or transition, caption/highlight, optional sound, and source/license to each beat. Mix shot types and visual pacing. Avoid unrelated stock, excessive text, and a slideshow masquerading as animation. Mark assets as licensed stock, original, or generated and identify missing items. Revise with the user before continuing.
5. **Acquire and review assets.** Fetch stock video or run a configured generation provider. Review every shot, people and brands, music, licenses, and creator credits. Record provider/model, prompt where relevant, costs, and provenance. Do not ingest a source reel as reusable content without rights.
6. **Narrate and caption.** Generate or record speech, review pronunciation, and create word-timed white/yellow captions. Use the same reviewed script and confirm that edits do not desynchronize audio and text.
7. **Edit and finish.** Assemble footage, animation, transitions, voice, captions, and permitted music in an editor or HyperFrames. The starter is only a layout/animation test; the current CLI supports basic assembly, not automatic cinematic editing, music mixing, visual generation, or transitions. Aim for 1080 × 1920 at 30 fps. Keep text within x 65–916 and y 270–1250, then check platform overlays and real text bounds; font metrics, outlines and long words can exceed those limits. White/yellow generated-narration captions use a starting position in this area, but their bounds are not automatically guaranteed.
8. **Quality gate.** The production agent checks the complete video with automated technical checks and available visual/audio AI. Check opening and ending, visual relevance and motion, facts, voice, caption size/contrast/sync/safe areas, licensing and attribution, output dimensions, duration, and the intended platform's current rules. Do not delegate routine review or correction to the user. If available tools cannot verify a material claim or speech transcription, report that limitation rather than presenting it as correct.
9. **Final export and publish.** Do not render a final or write to `Exports` until the user explicitly says **final export गर**. Export a clean vertical master and adapt captions, cover, title, description, disclosures, and credits per platform. Publish manually after approval. Review retention, completion, and meaningful comments per platform; compare changes to the hook and pacing without assuming metrics are identical across platforms.

Optional raw-footage work starts with local Whisper transcription, but current Nepali accuracy has failed a real sample; the transcript is not reliable for final captions. Do not ask the user to correct it. Cuts, 110–120% punch-ins every 2–4 seconds where appropriate, numbered badges, short motion graphics, licensed music, and SFX are not automated features. For a before/after comparison, require actual source and edited footage, show the narration script first, then show a storyboard with matching moments before the final-export gate. Voice providers, including ElevenLabs, are not integrated.

## Operating rhythm and costs

Target **three videos per week**. Batch idea research and scripts, acquire visuals and voices, then edit and review each episode individually. Vary series and standalone topics without filling a slot with low-quality material. Track a simple production record per video: script and sources, shot list, asset licenses and credits, provider/model, narration voice, duration, review status, platform links, and actual spend.

The target is **under NPR 5,000 per month**, not a guarantee. Check current local prices, exchange rates, API quotas, and terms before using any provider. Track actual usage; leave room for compute, data, and editing. The repository does not enforce a budget or include a free unlimited AI-video model.

## Current implementation versus the target

| Capability | Current state |
|---|---|
| Original scripts, research, brand design, editing judgment | Human/agent workflow; not automatic |
| Stock photos and moving Pexels footage | API key required; provider limits and rights apply |
| AI-generated images or video | External command adapter only; no model, provider, or credentials included |
| Nepali neural narration | Optional online provider; word timestamps and pronunciation require review |
| White/yellow word captions | Burned in for generated narration; provider word boundaries are checked against the script and audio, but pronunciation and legibility are not automatically guaranteed |
| Preparation | `prepare` prints a scene plan, acquires configured video assets, validates streams and generates configured narration; it cannot judge quality or create a complete storyboard |
| Cinematic editing, transitions, music mix and brand graphics | Manual external editing; not yet implemented |
| Platform adaptation and publishing | Manual; no automatic upload or scheduling |

Start with this proposal and review it against a real moving-footage pilot before treating its name, logo, or styling as final.
