# awesome-skills

A small, practical collection of reusable agent skills for local workflows and automation.

This repository currently contains **2 skills**:

| Skill | Description | Path |
|-------|-------------|------|
| `check-workday-cn` | Determine whether a date is a working day in mainland China using official holiday override data plus weekday fallback rules. | [`skills/check-workday-cn/`](./skills/check-workday-cn/) |
| `codex-session-history` | List and inspect local Codex session history by session id, title, project, workspace, source, and local time window. | [`skills/codex-session-history/`](./skills/codex-session-history/) |

## Installation

Install all skills from this repository with `npx skills`:

```bash
# Install globally for supported agents
npx skills add Sube-py/awesome-skills --all -g

# Install for the current project only
npx skills add Sube-py/awesome-skills --all
```

## Available Skills

### check-workday-cn

Use this skill when you need a reliable mainland China workday check for today or a specific date.

Examples:

```bash
python3 skills/check-workday-cn/scripts/check_today_workday.py
python3 skills/check-workday-cn/scripts/check_today_workday.py --date 2026-02-15
python3 skills/check-workday-cn/scripts/check_today_workday.py --json
```

Output fields:

- `date`
- `is_workday`
- `reason`
- `source_url`

### codex-session-history

Use this skill to inspect local Codex sessions stored under `~/.codex/`, especially when you need session ids, workspace paths, project names, or time-window filtering.

Examples:

```bash
python3 skills/codex-session-history/scripts/list_codex_sessions.py
python3 skills/codex-session-history/scripts/list_codex_sessions.py --source all
python3 skills/codex-session-history/scripts/list_codex_sessions.py --project PlayGround
python3 skills/codex-session-history/scripts/list_codex_sessions.py --date 2026-03-19 --from 11:00 --to 12:00
python3 skills/codex-session-history/scripts/list_codex_sessions.py --json
```

Default table columns:

- `id`
- `project`
- `started_at`
- `updated_at`
- `source`
- `title`

## Repository Layout

```text
awesome-skills/
├── README.md
└── skills/
    ├── check-workday-cn/
    │   ├── SKILL.md
    │   ├── agents/
    │   └── scripts/
    └── codex-session-history/
        ├── SKILL.md
        └── scripts/
```

## Publishing Notes

If you want this repository to be indexed by skills directories such as SkillsMP, check the maintainer checklist in [`docs/skillsmp-readiness.md`](./docs/skillsmp-readiness.md).
