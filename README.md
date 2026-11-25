# Katha Studio

An agent-assisted workflow for original, faceless short videos: Nepali-first,
configurable for other audiences, with a consistent branded canvas, animated
story components, narration, sound design, and kinetic captions. The production agent handles
the work; the user need not supply footage or do routine editing.

**Status:** Early prototype. `python -m katha reel` builds a branded,
narrated, sound-designed vertical reel from a beat script, with automated
quality checks. The voice is synthetic, the Saffron Signal palette is selected,
the channel identity remains provisional, and
research/scripting is still done by the production agent. Show the storyboard
first; do not export until the user says **final export गर**.

For the visual-storytelling proof, run
`python -m katha reel examples\reel\moon.json`. It uses original persistent
Sun/Earth/Moon diagrams, narration-cued motion, a continuous music bed and sparse
explicit effects. The pipeline also accepts local licensed images/recordings
through its media manifest; see the reel documentation.

## Documentation

- [Branded reel pipeline (recommended)](docs/reel-pipeline.md)
- [Project status and new-machine handoff](docs/project-status.md)
- [Setup, other commands, providers and limitations](docs/usage.md)
- [Portable production skill and agent setup](docs/skill-setup.md)
- [Brand and production standard](docs/brand-and-production.md)

The proposed channel name, mark and handle are not yet approved.
