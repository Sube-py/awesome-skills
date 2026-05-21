# awesome-skills

A small, practical collection of reusable agent skills for local workflows and automation.

This repository currently contains **4 skills**:

| Skill | Description | Path |
|-------|-------------|------|
| `check-workday-cn` | Determine whether a date is a working day in mainland China using official holiday override data plus weekday fallback rules. | [`skills/check-workday-cn/`](./skills/check-workday-cn/) |
| `codex-session-history` | List and inspect local Codex session history by session id, title, project, workspace, source, and local time window. | [`skills/codex-session-history/`](./skills/codex-session-history/) |
| `glab-gitlab-issue` | Read and manage GitLab issues with `glab`, including comments, uploaded files, assignees, labels, and time tracking. | [`skills/glab-gitlab-issue/`](./skills/glab-gitlab-issue/) |
| `query-loki-project-logs` | Query Grafana Loki logs by project, environment, and stream labels with a helper for common triage workflows. | [`skills/query-loki-project-logs/`](./skills/query-loki-project-logs/) |

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

### glab-gitlab-issue

Use this skill to inspect and update GitLab issues from the CLI. When viewing an issue, uploaded files referenced from the description or notes are cached under `${XDG_CACHE_HOME:-$HOME/.cache}/codex/glab-gitlab-issue/` and rewritten to local links in the output.

Examples:

```bash
bash skills/glab-gitlab-issue/scripts/issue.sh view --repo example-org/example-app --issue 42 --comments
bash skills/glab-gitlab-issue/scripts/issue.sh view --repo example-org/example-app --issue 42 --comments --json
bash skills/glab-gitlab-issue/scripts/issue.sh note --repo example-org/example-app --issue 42 --message "Added an update."
bash skills/glab-gitlab-issue/scripts/issue.sh estimate --repo example-org/example-app --issue 42 --duration 3h
```

Supported operations include:

- viewing issue details and comments
- caching uploaded files referenced by issue Markdown
- posting comments
- updating assignees and labels
- setting estimates and managing spent time

### query-loki-project-logs

Use this skill to inspect Loki logs that are organized by labels such as `project_name` or `project`, `env`, and `filename`.

Examples:

```bash
export LOKI_ADDR="https://loki.example.com"
export LOKI_USERNAME="demo-user"
export LOKI_PASSWORD="demo-password"

python3 skills/query-loki-project-logs/scripts/loki_project_logs.py projects --since 720h
python3 skills/query-loki-project-logs/scripts/loki_project_logs.py envs --since 720h
python3 skills/query-loki-project-logs/scripts/loki_project_logs.py files --project example-app --env test --since 24h
python3 skills/query-loki-project-logs/scripts/loki_project_logs.py errors --project example-app --env test --component web --since 1h
```

Typical triage flow:

- discover project values
- discover environment values
- list log stream filenames for a project and environment
- query errors or custom text in the relevant stream
- summarize exact timestamps, filenames, and representative log lines

## Repository Layout

```text
awesome-skills/
├── README.md
└── skills/
    ├── check-workday-cn/
    │   ├── SKILL.md
    │   ├── agents/
    │   └── scripts/
    ├── codex-session-history/
    │   ├── SKILL.md
    │   └── scripts/
    ├── glab-gitlab-issue/
    │   ├── SKILL.md
    │   ├── agents/
    │   ├── references/
    │   └── scripts/
    └── query-loki-project-logs/
        ├── SKILL.md
        ├── agents/
        ├── references/
        └── scripts/
```
