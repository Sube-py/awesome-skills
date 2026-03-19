# SkillsMP Readiness

This checklist is for repository-level setup that cannot be enforced by files alone.

## What Is Already Good In This Repo

- Skills are stored under `skills/<skill-name>/`.
- Each skill has a `SKILL.md`.
- Skill metadata is defined in frontmatter.
- The root `README.md` now lists all published skills and basic installation examples.

## What Still Needs To Be Done On GitHub

- Add repository topics:
  - `claude-skills`
  - `claude-code-skill`
- Add a short repository description.
- Make sure every skill you want indexed is committed and pushed to the default branch.
- Wait for the next daily sync after updating repository metadata.

## Quality Signals Worth Improving

- Keep `README.md` aligned with the actual published skills.
- Add concise usage examples for each skill.
- Prefer clear English descriptions for public discovery pages.
- Ask a few real users to star the repository if they find it useful.

## Current Manual Check

Before expecting indexing, confirm:

1. The skill directory exists on GitHub, not only locally.
2. The default branch contains the latest `SKILL.md`.
3. GitHub topics are visible on the repository homepage.
4. The repository homepage shows a non-empty description.
