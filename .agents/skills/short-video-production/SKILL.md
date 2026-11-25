---
name: short-video-production
description: Produce and review original faceless vertical videos with a consistent visual identity, animated storyboards, narration, sound, and timed captions.
---

# Short video production

Use this workflow for original, agent-reviewed short videos. Ask for the intended audience only when it is genuinely unclear; never imply an example reel grants rights to reuse its footage, script, voice, or music.

The production agent does the research, writing, asset sourcing, editing and quality checks; do not delegate routine manual work to the user. AI judgments and technical checks are not proof of factual, transcription, pronunciation, visual or licensing accuracy. If a necessary check cannot be done reliably, disclose the blocker instead of calling the output finished. Preserve the user's explicit final-export approval.

1. Define the topic, audience, platform, duration, and budget. Research and fact-check claims. Write an original script, not a close paraphrase of a book or reel. Avoid promising investment returns. Do not send private text to external providers without permission.
2. Write the reel as a beat script, following `docs/reel-pipeline.md` and `examples/reel/jensen-huang.json`:
   - one short authoritative caption per beat (10 words or fewer), with a keyword and optional per-word pronunciation overrides;
   - an animated component per beat (photo, card, swap, counter, stamp, checklist/list, timeline), cued to spoken words;
   - optional numbered steps;
   - a final outro that asks for a comment.

   Use the configured brand kit (`brand/brand.json`; Saffron Signal is the selected palette, while the name and mark remain provisional). Avoid unrelated stock footage and copying a reference's artwork, wording or music.
3. Use only original or properly licensed photos, with a credit. Check attribution, reuse rights and likeness restrictions. A source reel is inspiration only. No AI-video model is bundled.
4. Run `python -m katha reel <project.json>`. It does all of the following:
   - narrates with the configured edge-tts voice (default `ne-NP-SagarNeural`; script text goes to Microsoft's online service, so use only with permission);
   - aligns provider timings to the written caption, failing rather than guessing on ambiguous alignment;
   - writes a timed storyboard before the preview and rejects gaps over three seconds between planned story-content reveals, excluding the outro;
   - renders with HyperFrames;
   - mixes an original music bed and SFX with ducking and loudness normalisation;
   - writes QA results and a storyboard.

   If the build fails, fix the script (alignment, keywords, cues) or the layout and re-run. Do not hand the problem to the user.
5. Watch the preview and the storyboard. Check facts, pronunciation, visual relevance, caption sync and the mix, as well as the automated QA. Show the user the storyboard and preview.
6. Only after the user explicitly says `final export गर`, run `python -m katha reel <project.json> --approval "final export गर"`. This copies the passing, unchanged preview to `Exports`. Disclose synthetic speech and credit sources. Do not publish unchecked output.

For footage-based scene videos, use the older `render`, `prepare`, `fetch`, `generate`, `narrate` and `transcribe` commands described in `docs/usage.md`.

For optional raw-footage edits, transcription, cuts, punch-ins and badges still require editing outside the CLI. `transcribe` produces only an unverified draft; never use it as final captions, and never ask the user to repair it. For a before/after comparison, use real source and edited footage. Show the voiceover script first, then the storyboard, before the export gate. Neither face-touch detection nor ElevenLabs is integrated.

Consult `docs/brand-and-production.md` for the channel direction and production standards. Treat the name, logo, and handle as proposals until approved. For commands, configuration details, dependencies, and limitations, see `docs/usage.md`.
