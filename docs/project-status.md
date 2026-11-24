# Project status and handoff

## What we are building

Katha Studio is intended to help a production agent create original, faceless,
short vertical videos from a topic: research and script, storyboard, find or
generate moving visuals, narrate, add captions and motion, verify quality, and
deliver a platform-ready video. The viewer should not have to supply images,
record a voiceover, correct transcripts, or perform routine editing.

The initial audience is Nepali-speaking, but the workflow should be configurable
for other audiences and subjects. It should support recurring series and
standalone topics, approximately three two-minute videos per week, and TikTok,
Instagram, YouTube Shorts, and Facebook. A budget below NPR 5,000/month is a
goal, not a software-enforced limit or a promise of provider pricing.

The channel identity **छेउबाट | Chheubata** is a proposal, not an approved
name or logo; see [brand and production](brand-and-production.md). Its name,
handles and trademark availability have not been verified.

## What works today

| Area | Implemented | Boundary |
| --- | --- | --- |
| Projects | JSON scenes; configurable dimensions, frame rate, fonts, text and visuals | The agent creates the script and scene plan; there is no topic-to-project generator |
| Visual assets | Pexels photo/video downloads with provenance, local files, and an external generator command | Pexels requires a key; no AI-video provider, model or credentials are bundled; visual relevance and rights are not automatically verified |
| Preparation | `prepare` prints a scene plan, acquires configured video assets, checks video streams and generates configured narration | It does not create a full storyboard, evaluate the quality of footage, or edit a cinematic video; partial runs can leave assets behind |
| Narration | Optional online Nepali Microsoft Edge voices via `edge-tts`, with provider word boundaries | Script text is sent online; pronunciation is not guaranteed |
| Captions | White text and yellow active word for generated narration, checked against the script and audio timing | Does not consume raw-speech transcripts; accurate glyph bounds, pronunciation and readability are not guaranteed |
| Video assembly | FFmpeg assembles images, colors or video, crops, adds captions and audio, and checks final streams and decoding | Basic cuts and looping, not cinematic editing, motion graphics or music mixing |
| HyperFrames | A separately editable, four-second layout/animation starter | Not connected to JSON scene rendering; not a finished production template |
| Speech transcription | Local whisper.cpp command and multilingual models | Tested Nepali results contained serious errors; output is an unverified draft, not final captions |
| Export | Renderer requires the explicit `final export गर` approval string | This safeguard does not prove a storyboard was reviewed; direct external tools such as HyperFrames cannot enforce it |

No polished two-minute pilot has been completed. Earlier slideshow/animation
experiments were rejected; do not present them as evidence of production quality.

## Pending work

1. Build an agent-driven research and original-script workflow with source and
   claim tracking, plus a complete timed storyboard tied to actual shots.
2. Select and integrate a usable licensed stock source and/or video generation
   provider, with costs, quotas, provenance and visual-quality checks. No
   licensed moving footage is bundled. Avoid substituting slides for real shots.
3. Implement and evaluate a proper motion-editing pipeline: HyperFrames project
   generation, shot selection, transitions, animation, branded graphics,
   optional badges and punch-ins, and music/SFX mixing. Respect asset licenses.
4. Evaluate Nepali speech and transcription against a representative benchmark;
   improve pronunciation, word alignment and caption layout. Do not silently
   treat ASR guesses or model self-assessments as ground truth.
5. Add automated technical, audio and visual quality checks, including actual
   text bounds and platform safe areas, and flag issues that cannot be verified.
   The production agent, not the user, should do routine checking and repairs.
6. Design an end-to-end optional raw-footage and before/after workflow. Mistake,
   face-touch and look-away detection, synchronized comparisons, and ElevenLabs
   are not implemented. Do not invent unavailable footage or outcomes.
7. Finalize the brand only after approval and availability checks; add platform
   adaptation, tracking, scheduling/publishing only if deliberately designed.
8. Produce and assess a representative original pilot once tools, assets and
   permissions are available. Show the storyboard first; only render/export a
   final after the user explicitly says `final export गर`.

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

Clone the repository and check out the **pushed working branch**, not just the
default branch, until that work has been merged. Obtain the branch name from the
GitHub branch list or the push handoff. In PowerShell:

```powershell
git clone https://github.com/kriteshpokhrel/katha-studio.git
Set-Location katha-studio
git switch --track origin/<pushed-branch-name>
python --version
ffmpeg -version
ffprobe -version
node --version
npm --version
```

Replace `<pushed-branch-name>` with the actual branch name. Install Python 3.9+
and FFmpeg/ffprobe on PATH. The bundled examples have Windows-specific font
paths; change them to installed fonts on the new machine. Node 22+, npm and a
compatible Chrome installation are needed for HyperFrames:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
npm ci
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
$env:HYPERFRAMES_NO_TELEMETRY = "1"
$env:HYPERFRAMES_NO_UPDATE_CHECK = "1"
$env:HYPERFRAMES_NO_ORPHAN_CLEANUP = "1"
.\node_modules\.bin\hyperframes.cmd lint examples\hyperframes
.\node_modules\.bin\hyperframes.cmd check examples\hyperframes --no-craft
```

For Windows x64 Whisper binaries and a model, download and verify the artifacts
as described in the [README](../README.md#ffmpeg-hyperframes-and-whisper).
Set provider credentials only in the environment or a secure local store, not
in committed files. A separate Pexels key and/or external generator is needed
for actual stock/generated video. Confirm provider terms, privacy, licensing and
costs before sending scripts or prompts externally. Narration also requires
internet access. For macOS/Linux, use the platform's virtual-environment Python
and executable paths and follow the upstream tool installation instructions.

Resume with [README](../README.md), then the
[production skill](../.github/skills/short-video-production/SKILL.md).
The repository does not automatically schedule or publish videos.
