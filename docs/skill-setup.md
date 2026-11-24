# Portable production skill

The canonical [short-video-production skill](../.agents/skills/short-video-production/SKILL.md)
uses the open [Agent Skills format](https://agentskills.io/specification):
a folder containing a `SKILL.md` with `name` and `description` metadata. Its
instructions are agent-neutral; they describe this repository's actual tools,
workflow, approval gate, limitations and quality standards.

## Discovering the skill

- Agents that support project skills under `.agents/skills` can load it directly
  from this repository. Discovery depends on the client and version; see its
  documentation.
- Claude Code discovers project skills under `.claude/skills`. To install the
  current version locally in PowerShell, from the repository root:

  ```powershell
  New-Item -ItemType Directory -Force .claude\skills | Out-Null
  Copy-Item -Recurse .agents\skills\short-video-production .claude\skills\
  ```

  Restart the agent if it does not discover the skill. After updates, replace
  the installed copy with the new canonical directory. The local Claude copy is
  ignored by Git; do not edit it as the source of truth. See
  [Claude Code skill locations](https://code.claude.com/docs/en/skills#choose-where-skills-load).
- For any other Agent Skills-compatible client, install or load the canonical
  skill directory using that client's own discovery mechanism. Do not assume
  every client scans the same directory. The agent must also have access to
  this repository because the skill refers to `docs` and CLI commands.

The skill is instructions, not a video model or a guarantee of output quality.
See [usage](usage.md) for dependencies and [project status](project-status.md)
for unfinished capabilities.
