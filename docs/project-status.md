# Project status and handoff

## What we are building

Katha Studio is intended to help a production agent create original, faceless,
short vertical videos from a topic: research and script, storyboard, source or
create story-specific assets, narrate, add sound, captions and motion, verify quality, and
deliver a platform-ready video. The viewer should not have to supply images,
record a voiceover, correct transcripts, or perform routine editing.

The initial audience is Nepali-speaking, but the workflow should be configurable
for other audiences and subjects. It should support recurring series and
standalone topics, approximately three two-minute videos per week, and TikTok,
Instagram, YouTube Shorts, and Facebook. A budget below NPR 5,000/month is a
goal, not a software-enforced limit or a promise of provider pricing.

The preferred format uses a consistent static branded canvas and animated
story-specific components, a Nepali male voice, a kinetic headline caption with
a highlighted keyword, and an original music bed with sound effects. It must
remain configurable for others. The shipped `brand/brand.json` uses the
production name **Katha Studio** as a placeholder. The channel name
**छेउबाट | Chheubata** is a separate, unapproved proposal; see
[brand and production](brand-and-production.md). No name, handle or trademark
has been checked for availability.

## What works today

| Area | Implemented | Boundary |
| --- | --- | --- |
| Branded reels | `reel` command: beat script → edge-tts narration → word-aligned HyperFrames/GSAP composition (brand canvas, kinetic headline with keyword marker, cue-timed components, numbered steps, branded outro) → original procedural music and SFX, ducked and loudness-normalised → QA, storyboard and gated export. See [reel pipeline](reel-pipeline.md) | Agent writes the beat script; voice is synthetic; QA measures timing, loudness, motion and safe area, not facts or taste |
| Brand kit | `brand/brand.json` colours, mark, handle, outro text; bundled OFL fonts | Identity is a proposal pending approval |
| Projects | JSON scenes; configurable dimensions, frame rate, fonts, text and visuals | The agent creates the script and scene plan; there is no topic-to-project generator |
| Visual assets | Pexels photo/video downloads with provenance, local files, and an external generator command | Pexels requires a key; no AI-video provider, model or credentials are bundled; visual relevance and rights are not automatically verified |
| Preparation | `prepare` prints a scene plan, acquires configured video assets, checks video streams and generates configured narration | It requires video scenes and cannot make the preferred static-background storyboard; partial runs can leave assets behind |
| Narration | Optional online Nepali Microsoft Edge voices via `edge-tts`, with provider word boundaries | Script text is sent online; pronunciation is not guaranteed |
| Captions | White text and yellow active word for generated narration, checked against the script and audio timing | Does not consume raw-speech transcripts; accurate glyph bounds, pronunciation and readability are not guaranteed |
| Video assembly | FFmpeg assembles images, colors or video, crops, adds captions and audio, and checks final streams and decoding | Basic cuts and looping, not a branded storyboard, motion graphics or music mixing |
| HyperFrames | Generated per reel by the `reel` command; plus a separate four-second starter in `examples/hyperframes` | The older `render` command does not use HyperFrames |
| Speech transcription | Local whisper.cpp command and multilingual models | Tested Nepali results contained serious errors; output is an unverified draft, not final captions |
| Export | `render` and `reel` require the explicit `final export गर` approval string; `reel` also requires a passing, unchanged QA preview | This safeguard does not prove a human watched the preview; direct external tools cannot enforce it |

Earlier slideshow/animation experiments and the first Jensen Huang preview were
rejected. They were replaced by the `reel` pipeline. Its sample,
`examples/reel/jensen-huang.json`, renders a ~39 s reel that passes all
automated checks. It has not been approved as a finished template, and its
synthetic voice has not been reviewed by a native listener.

## Pending work

1. Approve or replace the proposed brand (name, mark, colours, handle) and check availability.
2. Build a research and original-script workflow that outputs a reel project: topic → sources and claim tracking → beat script. Today the agent writes the JSON by hand.
3. Choose a more natural Nepali male voice provider, if budget allows. Keep edge-tts as the free default, and disclose synthetic speech.
4. Add more component types (charts, maps, quote cards, image galleries). Support longer formats (about 2 minutes) with more steps, and tune the pacing.
5. Platform adaptations: cover image, titles and descriptions, and per-platform caption and safe-area variants. Scheduling and publishing are not implemented.
6. Evaluate Nepali transcription for the optional raw-footage workflow. Mistake, face-touch and look-away detection, before/after reels and ElevenLabs are not implemented.
7. Use vision-model QA to judge layout and visual relevance beyond the current pixel checks.

AI can assist research, editing and review but cannot guarantee that claims,
pronunciation, licensing or visual choices are correct. Stop and report an
unresolved quality or provider blocker instead of calling an incomplete video
finished or asking the user to do routine correction.

## Moving to another machine

The repository contains source code, examples, documentation, a production
skill, and a locked HyperFrames npm dependency. It does **not** contain the
Python virtual environment, `node_modules`, downloaded whisper.cpp binaries or
models, stock/generated assets, narration files, output videos, transcripts, the
`Raw Footage` and `Exports` directories,
credentials, or temporary session artifacts. They are ignored by Git and must
be installed, regenerated or transferred separately, subject to their licenses.
Prior conversation scripts and previews are not included; recreate or
deliberately transfer any needed production materials.

Clone the repository and check out the feature branch containing these changes,
not just the default branch, until that work has been merged. In PowerShell:

```powershell
git clone https://github.com/kriteshpokhrel/katha-studio.git
Set-Location katha-studio
git switch --track origin/feature/storyboard-production-standards
python --version
ffmpeg -version
ffprobe -version
node --version
npm --version
```

Install Python 3.9+ and FFmpeg/ffprobe on PATH. The bundled examples have Windows-specific font
paths; change them to installed fonts on the new machine. Node 22+, npm and a
compatible Chrome installation are needed for HyperFrames:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-reel.txt
npm ci
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -m katha reel examples\reel\jensen-huang.json
$env:HYPERFRAMES_NO_TELEMETRY = "1"
$env:HYPERFRAMES_NO_UPDATE_CHECK = "1"
$env:HYPERFRAMES_NO_ORPHAN_CLEANUP = "1"
.\node_modules\.bin\hyperframes.cmd lint examples\hyperframes
.\node_modules\.bin\hyperframes.cmd check examples\hyperframes --no-craft
```

For Windows x64 Whisper binaries and a model, download and verify the artifacts
as described in [usage](usage.md#ffmpeg-hyperframes-and-whisper).
Set provider credentials only in the environment or a secure local store, not
in committed files. A separate Pexels key and/or external generator is needed
for actual stock/generated video. Confirm provider terms, privacy, licensing and
costs before sending scripts or prompts externally. Narration also requires
internet access. For macOS/Linux, use the platform's virtual-environment Python
and executable paths and follow the upstream tool installation instructions.

Resume with [README](../README.md), then the
[production skill](../.agents/skills/short-video-production/SKILL.md) and
[agent-specific setup](skill-setup.md).
The repository does not automatically schedule or publish videos.
