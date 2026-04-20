---
name: query-loki-project-logs
description: Query Grafana Loki logs that are organized by `project` and `filename`, where `filename` distinguishes `nginx`, `web`, `worker`, `stdout`, and `stderr` streams. Use when Codex needs to inspect logs with `logcli`, discover available projects, list a project's log files, narrow to a specific component such as web or worker, or check a recent time window for errors in test or local environments.
---

# Query Loki Project Logs

Use this skill to inspect Loki logs with the house convention:

- `project` identifies the service or deployment
- `filename` identifies the concrete stream, such as `pd_router-web-stderr.log` or `pd_router-nginx-stdout.log`

## Quick Start

1. Resolve the Loki address.
2. List available `project` values.
3. List the target project's `filename` values.
4. Pick the stream that matches the question.
5. Query the time window and summarize findings.

Prefer the helper script first:

```bash
python3 scripts/loki_project_logs.py projects --since 720h
python3 scripts/loki_project_logs.py files --project pd_router_test --since 24h
python3 scripts/loki_project_logs.py errors --project pd_router_test --component web --since 1h
```

Run these commands from the skill root directory.

The `errors` subcommand narrows to matching `stderr` streams by default.

If the script is not appropriate, use raw `logcli` commands from [references/query-patterns.md](references/query-patterns.md).

## Workflow

### 1. Resolve Loki

Prefer `LOKI_ADDR` from the current environment.
If it is missing, check common shell config files such as `~/.zshrc` for `export LOKI_ADDR=...`.
Do not assume `http://localhost:3100` is correct unless the user confirms it.

### 2. Discover Projects

List `project` label values before guessing names.
This gives the set of known deployments in Loki for the chosen lookback window.

### 3. Discover Streams

List `filename` values for the chosen project.
Use the filename to distinguish the stream type:

- `*-web-stderr.log`: application errors and Python tracebacks
- `*-web-stdout.log`: application request and info logs
- `*-worker-stderr.log`: worker exceptions
- `*-worker-stdout.log`: worker info logs
- `*-nginx-stderr.log`: nginx errors
- `*-nginx-stdout.log`: access logs or proxy output
- `init.log`: startup output

Use exact filenames when querying once the right stream is known.

### 4. Triage Errors

When the user asks whether there are errors:

1. Start with `stderr` for the requested component.
2. Search for obvious error markers such as `ERROR`, `Exception`, `Traceback`, `panic`, `sqlalchemy.exc`, and `asyncpg.exceptions`.
3. Pull a broader context query if the first pass shows stack traces or repeated failures.
4. Report the result with exact timestamps, stream filename, and the dominant error type.

If the request is about web issues, check both:

- `*-web-stderr.log` for exceptions
- `*-web-stdout.log` for the request path or surrounding request logs

If the request is about nginx, include both nginx streams because routing failures often show up in `stdout` access logs while configuration issues show up in `stderr`.

## Response Pattern

When answering the user, include:

- Whether errors were found
- The exact time window used
- The project name
- The exact filename(s) queried
- One or two representative error lines or a concise paraphrase
- A short root-cause hypothesis when the logs support it

Avoid claiming absence of errors unless you checked the relevant stream for the requested component.

## Resources

- Scripted helper: [scripts/loki_project_logs.py](scripts/loki_project_logs.py)
- Query cookbook: [references/query-patterns.md](references/query-patterns.md)
