# Katha Studio

A configurable, agent-assisted workflow for making original faceless vertical videos. The basic example needs no supplied images, voiceover, credentials, or paid AI service: it renders text over generated color backgrounds. Optional Pexels stock videos, an external visual generator, and Nepali neural narration support more developed videos. This is a production assistant, not a fully automatic research, cinematic video-generation, editing, or publishing service.

The production agent should handle research, writing, asset acquisition and review rather than asking the audience to do these tasks. The `prepare` command automates asset acquisition and narration for an agent-created project, but it does not write or fact-check the script, evaluate footage quality, create cinematic edits, or guarantee a correct video. When these steps cannot be completed reliably, report the blocker instead of passing the work to the user as a finished result.

**Starting on another machine?** See the [project status and handoff](docs/project-status.md) for the goal, implemented capabilities, pending work, branch checkout, dependencies, and files that are not included in Git.

## Requirements

- Python 3.9 or later and FFmpeg with `libx264`, AAC, `drawtext`, and `ass`, plus ffprobe, available on your PATH. `ffmpeg -filters` lists filters; `ffmpeg -encoders` lists encoders.
- A locally installed TrueType/OpenType font with glyphs for your chosen language. Specify its absolute path in the project JSON. For Nepali, choose a font that supports Devanagari. Text rendering depends on your FFmpeg build's shaping support.
- The basic workflow needs no Python packages. Stock downloads need an internet connection and a Pexels API key; generated images or videos need a separately installed and configured generator. Narration needs the optional dependencies below and an internet connection.

## Quick start

1. Research and write an original script. Show a storyboard for approval before producing a final video: use the shot-plan fields in [the production standard](docs/brand-and-production.md). The user need not supply reference footage or images.
2. Copy `examples\project.json` to your own project directory and edit the story, captions, scene lengths, and font path. Paths in the project are relative to the project file unless absolute. The color-only example is a technical test, not a finished-quality video.
3. Only after the user says **final export गर**, run `python -m katha render path\to\project.json --approval "final export गर"`. The Python renderer enforces the same approval parameter; the separate HyperFrames CLI cannot enforce Katha's approval state, so do not use it to create a final export before approval. The output is `output\video.mp4` relative to the project, or the configured output path. The flag is not proof that a storyboard was reviewed.
4. The production agent checks the complete video, text, claims, visual rights, music and platform requirements; the user only needs to provide the already-requested final-export approval. The sample is a short test, not a complete two-minute video: increase scene durations and add original scenes for your intended runtime.

For three approximately two-minute videos weekly, create and review three separate projects. Make captions readable for their full duration, and check retention and pacing in an editor. The default 1080 × 1920 export is vertical; platform rules and maximum lengths change, so check TikTok, Instagram, YouTube and Facebook before publishing. There is no scheduler or automatic publishing.

## Visuals and voice

Each scene's `visual.type` may be:

- `color`: locally generated solid background, no download.
- `stock`: set `query`, optionally set `media` to `video` (default `image`), set environment variable `PEXELS_API_KEY`, then run `python -m katha fetch path\to\project.json`. It downloads one Pexels asset per stock scene into `assets`, with `assets\provenance.json` recording the source and creator. Review the asset, its license, and any depicted people, brands, or places before publication. Search results can change; rerunning fetch overwrites corresponding downloads and provenance. Pexels API limits and terms apply. Display a prominent link to [Pexels](https://www.pexels.com/) when using the API, and credit creators where possible.
- `generated`: set `prompt`, optionally set `media` to `video` (default `image`), and configure `generator.command` as an argument list. Run `python -m katha generate path\to\project.json` to invoke your own generator once per generated scene. Arguments can contain `{prompt}` and `{output}`; the adapter must write a PNG for an image or MP4 for a video to `{output}` and exit successfully. No shell is used. **Only run generator commands from projects you trust.** The adapter, model, credentials, terms, compute, availability, safety, and cost are yours to assess; no AI provider is bundled. Example: `"generator": {"command": ["python", "my_generator.py", "--prompt", "{prompt}", "--output", "{output}"]}`.
- `file`: set `path` to an image you have rights to use, including a generated image obtained outside the CLI.

After fetching or generating, run `render`. Stock and generated scenes fail explicitly if their assets are missing. After changing a stock query or scene order, fetch again; generated assets should likewise be regenerated after changing their prompts. Visuals are center-cropped; videos loop if shorter than a scene and their original audio is discarded. Captions are burned in and wrapping is approximate: check for clipping and language shaping, especially for Nepali. The optional `voiceover` path accepts an audio file: when omitted, output has no audio unless generated narration is configured; when provided, it is padded with silence or trimmed to video length. Music is not generated; add appropriately licensed music in an editor if desired.

For example, replace a scene's `visual` object with one of:

```json
{"type": "stock", "query": "Kathmandu street"}
{"type": "stock", "media": "video", "query": "city street people walking"}
{"type": "generated", "prompt": "An original illustration of a mountain village"}
{"type": "generated", "media": "video", "prompt": "A street market at dawn"}
{"type": "file", "path": "my-licensed-image.png"}
```

In PowerShell, set a stock key for the current process with `$env:PEXELS_API_KEY = "your-key"`; on macOS/Linux use `export PEXELS_API_KEY="your-key"`. Never commit credentials. To use a generated visual, install a provider or local model separately and configure its command as described above; adding the `generated` scene alone does not generate a visual.

### Nepali narration and word highlights

The optional `narrate` command sends each scene's `narration` text (or its `text` when omitted) to the online Microsoft Edge speech service through [`edge-tts`](https://github.com/rany2/edge-tts). It records audio and word timings in `assets`. Do not send sensitive text. This third-party service, voice availability, terms, and charges may change; verify suitability for your use. It is not an offline model. `ne-NP-HemkalaNeural` is the default; `ne-NP-SagarNeural` is another available voice.

On Windows, install the optional package into a virtual environment and use that environment's Python for the commands:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
.\.venv\Scripts\python.exe -m katha fetch examples\narrated-video.json
.\.venv\Scripts\python.exe -m katha narrate examples\narrated-video.json
# Only after storyboard review and the user's "final export गर" approval:
.\.venv\Scripts\python.exe -m katha render examples\narrated-video.json --approval "final export गर"
```

Set `PEXELS_API_KEY` before `fetch`; alternatively use appropriately licensed local video files. On other platforms use `.venv/bin/python`. Edit the example's `font` path and `caption_font` family name for your system. For each scene, narration and its word timings must match the text and voice; rerun `narrate` after changes. Render extends short scenes to fit speech. With generated narration, the active spoken word is yellow and surrounding words are white, with a dark outline; `font_size` controls size. Review pronunciation, caption fit and synchronization on a phone. An existing `voiceover` file cannot be combined with generated narration; word-timed captions require the narration workflow.

The repository's [short-video-production skill](.github/skills/short-video-production/SKILL.md) describes the repeatable research, visuals, narration, captions and review process. It does not install an AI model or create footage by itself.

See the proposed [brand and production standard](docs/brand-and-production.md) for a channel identity, series structure, visual direction, editorial rules, and quality gate. The branding is a proposal pending review, not a finalized identity.

### Automated preparation

After the production agent has researched and written a project and presented the full storyboard, it can run `python -m katha prepare path\to\project.json`. This prints a scene plan, fetches configured stock videos, runs configured video generators, validates video streams, and creates configured narration. It rejects color/image scenes instead of silently substituting a slideshow, refuses to overwrite existing assets, and does not render a video. Use a fresh project directory for another attempt after a partially completed preparation. It requires the same keys, provider permissions, packages and font as the underlying commands; generated narration sends the script to Microsoft.

Generated narration uses the speech provider's word boundaries rather than transcribing its own audio. The code checks that the returned words match the narration text (ignoring punctuation and spacing), that timings are ordered, and that they fit the audio. These checks do **not** prove pronunciation, semantic accuracy, actual motion, visual relevance or license suitability. The printed scene plan is not a full storyboard, and this command is not an autonomous video editor. Agents must perform those creative and factual checks themselves, report unresolved risks, and honor the final-export gate. Whisper remains useful for supplied audio, but neither Whisper nor the available local language model reliably corrected the tested Nepali sample; the pipeline does not silently use AI guesses as verified captions.

## FFmpeg, HyperFrames and Whisper

FFmpeg assembles and encodes the existing JSON projects and converts input audio for transcription. HyperFrames is a separate editable HTML motion-composition tool; it does not automatically turn a Katha JSON project into a composition. whisper.cpp transcribes local audio or video; it does not cut footage or create synchronized Katha captions automatically.

On Windows, install Python, Node.js 22+, and an FFmpeg build on `PATH` first. From the repository root run:

```powershell
ffmpeg -version
ffprobe -version
npm ci
$env:HYPERFRAMES_NO_TELEMETRY = "1"
$env:HYPERFRAMES_NO_UPDATE_CHECK = "1"
$env:HYPERFRAMES_NO_ORPHAN_CLEANUP = "1"
.\node_modules\.bin\hyperframes.cmd --version
.\node_modules\.bin\hyperframes.cmd lint examples\hyperframes
.\node_modules\.bin\hyperframes.cmd check examples\hyperframes --no-craft
```

The environment settings apply only to the current shell. Disabling orphan cleanup avoids stopping other HyperFrames browser processes in a shared environment, but crashed browser processes may then need manual cleanup. HyperFrames requires a compatible browser for `check` and preview. The editable starter in `examples\hyperframes\index.html` is a **four-second layout and animation test**, not a storyboard or finished video. Its pinned GSAP script is loaded from jsDelivr and needs internet access; the CDN receives the usual network request. Replace the placeholder with actual licensed moving footage and a reviewed, timed script before considering production. Font availability and safe areas must be checked on the actual device and platform. HyperFrames can render independently, but **do not render a final or write to `Exports` until the user explicitly says `final export गर`**.

For local transcription, install [whisper.cpp](https://github.com/ggml-org/whisper.cpp) and a multilingual model. For example, on Windows x64, download the official [b5907 CPU release](https://github.com/ggml-org/whisper.cpp/releases/tag/b5907) asset `whisper-bin-x64.zip`, verify its SHA-256 `ecca07b277d943e9b9f4712856a144b857271a6b333104e511e1988e80db582b`, and extract it under `.tools\whisper` (the executable is `.tools\whisper\Release\whisper-cli.exe`). Download the [large-v3-turbo-q5_0 model](https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin) to `.tools\models\ggml-large-v3-turbo-q5_0.bin`; verify its SHA-1 against the [official model list](https://huggingface.co/ggerganov/whisper.cpp#available-models): `e050f7970618a659205450ad97eb95a18d69c9ee`. The model is approximately 547 MiB; CPU inference may be slow. Other platforms should follow the upstream build or binary instructions and pass their executable and model paths below. These files are local and ignored by Git.

```powershell
.\.tools\whisper\Release\whisper-cli.exe --help
python -m katha transcribe "path\to\audio-or-video.mp4" --whisper .tools\whisper\Release\whisper-cli.exe --model .tools\models\ggml-large-v3-turbo-q5_0.bin --output transcripts\draft.json --language ne
```

FFmpeg converts the input to temporary mono 16 kHz WAV, and Whisper writes full JSON with estimated timing information. The temporary WAV is removed afterward; an existing transcript is never overwritten. Change `--language` for another language or use `auto`. Whisper runs locally after installation, but downloads require internet. **Do not use Whisper's Nepali output as final captions:** even the larger model badly misheard a short Nepali sample on this machine, and reliable automatic correction is not implemented. Full JSON token times are not guaranteed word boundaries; the renderer never consumes those drafts as captions. The production agent should create narration from a script it can substantiate and generate captions from the exact spoken text; for supplied raw speech, report that accurate transcript/captions cannot be guaranteed rather than asking the user to correct it or silently using guessed words. Optional Kokoro TTS, MusicGen and Docker reported by HyperFrames doctor are not needed for this workflow.

Before saving a rendered file, the renderer checks its video dimensions, frame rate, duration, audio-stream presence and full decodability; invalid output is rejected. These are technical checks only. They cannot establish that the narration is properly pronounced, that the visuals fit the story, or that a script's claims are true.

Raw-footage edits and before/after comparisons are not implemented end-to-end: no face-touch or look-away detector, automatic mistake removal, punch-in editor, numbered badges, graphic insertion, music/SFX mixing, ElevenLabs integration, or automatic synchronized comparison is available. If raw footage is supplied, the production agent may try local transcription, but the tested Nepali recognizer is not accurate enough for publication; do not make the user correct it or call it a finished edit. A before/after workflow also requires an actual edited video, which must not be fabricated or inferred from references. The only manual user action retained is the previously requested `final export गर` approval.

## Research, rights, and budget

Use public reels only as inspiration for topics and pacing; do not download, reproduce, or assume rights to their footage, music, narration, or scripts. Write an original script, independently verify facts and claims, review generated content and likenesses, and keep source/license records. This tool does not ingest reel URLs or perform research for you.

Start with the included free local workflow and monitor actual provider charges, stock API quotas, internet and compute costs before opting into external services. NPR 5,000/month is a planning target, not a guarantee or enforced limit. Check current exchange rates, pricing and terms before each production; keep a manual spending ledger.

References for the methods and further editing:

- [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html) and [FFmpeg documentation](https://ffmpeg.org/ffmpeg.html): scaling, cropping, drawtext, concat and audio handling used here.
- [HyperFrames composition schema](https://hyperframes.heygen.com/reference/html-schema.md), [CLI](https://hyperframes.heygen.com/developers/cli.md), and [faceless explainer guide](https://hyperframes.heygen.com/guides/faceless-explainer.md): editable timed compositions, animation and review.
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp) and its [model list](https://huggingface.co/ggerganov/whisper.cpp#available-models): local multilingual transcription and model choices.
- [Pexels API](https://www.pexels.com/api/documentation/) and [Pexels license](https://www.pexels.com/license/): photo search, downloads and usage restrictions.
- [DaVinci Resolve training](https://www.blackmagicdesign.com/products/davinciresolve/training): manual editing and finishing.
- [CapCut AI video generator](https://www.capcut.com/tools/ai-video-generator) and [Runway credits](https://help.runwayml.com/hc/en-us/articles/15124877443219-How-do-credits-work): examples of external AI-assisted tools and their changing access/cost constraints; neither is integrated.
- [YouTube Shorts guidance](https://support.google.com/youtube/answer/15424877?hl=en), [copyright](https://support.google.com/youtube/answer/2797466?hl=en), and [monetization policies](https://support.google.com/youtube/answer/1311392?hl=en): check current platform requirements and rights. YouTube says Shorts over one minute with an active copyright claim are blocked globally.

## Validation

Run `python -m unittest discover -s tests -v`. The integration test renders a short no-voice/no-image project when a suitable FFmpeg and font are installed; otherwise it reports a skip.
