#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

LOGCLI_URL_PATTERN = re.compile(r"^\d{4}/\d{2}/\d{2} ")
FILENAME_PATTERN = re.compile(r'filename="([^"]+)"')
EXPORT_PATTERN = re.compile(r"^export\s+LOKI_ADDR=(.+)$")
ERROR_PATTERN = r"(ERROR|Error|Exception|Traceback|panic|FATAL|CRITICAL|sqlalchemy\\.exc\\.|asyncpg\\.exceptions\\.)"
DEFAULT_SHELL_FILES = (
    Path.home() / ".zshrc",
    Path.home() / ".zprofile",
    Path.home() / ".zshenv",
    Path.home() / ".bashrc",
    Path.home() / ".bash_profile",
    Path.home() / ".profile",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Helper for querying Loki project logs via logcli.")
    parser.add_argument("--addr", help="Loki address. Defaults to LOKI_ADDR or shell config export.")
    parser.add_argument("--org-id", help="Optional Loki tenant / X-Scope-OrgID.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    projects_parser = subparsers.add_parser("projects", help="List project labels.")
    projects_parser.add_argument("--since", default="168h", help="Lookback window, for example 1h or 30d.")

    files_parser = subparsers.add_parser("files", help="List filenames for a project.")
    files_parser.add_argument("--project", required=True, help="Project label value.")
    files_parser.add_argument("--since", default="24h", help="Lookback window, for example 1h or 7d.")
    files_parser.add_argument("--contains", help="Only print filenames containing this substring.")

    query_parser = subparsers.add_parser("query", help="Query one or more streams for a project.")
    query_parser.add_argument("--project", required=True, help="Project label value.")
    query_parser.add_argument("--since", default="1h", help="Lookback window, for example 1h or 24h.")
    query_parser.add_argument("--limit", type=int, default=50, help="Maximum number of log lines.")
    query_parser.add_argument("--filename", action="append", default=[], help="Exact filename to query. Repeatable.")
    query_parser.add_argument("--component", help="Filename substring such as web, worker, nginx, stdout, stderr.")
    query_parser.add_argument("--grep", help="Plain-text Loki filter added with |= .")
    query_parser.add_argument("--regex", help="Regex Loki filter added with |~ .")

    errors_parser = subparsers.add_parser("errors", help="Query likely error lines for a component.")
    errors_parser.add_argument("--project", required=True, help="Project label value.")
    errors_parser.add_argument("--component", default="web", help="Filename substring such as web, worker, or nginx.")
    errors_parser.add_argument("--since", default="1h", help="Lookback window, for example 1h or 24h.")
    errors_parser.add_argument("--limit", type=int, default=80, help="Maximum number of log lines.")

    return parser.parse_args()


def resolve_loki_addr(cli_addr: str | None) -> str:
    if cli_addr:
        return cli_addr

    env_addr = os.environ.get("LOKI_ADDR", "").strip()
    if env_addr:
        return env_addr

    for shell_file in DEFAULT_SHELL_FILES:
        if not shell_file.exists():
            continue
        for raw_line in shell_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            match = EXPORT_PATTERN.match(line)
            if not match:
                continue
            value = match.group(1).strip().strip('"').strip("'")
            if value:
                return value

    raise SystemExit("Unable to resolve LOKI_ADDR from --addr, environment, or shell config.")


def clean_output_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if LOGCLI_URL_PATTERN.match(line):
            continue
        lines.append(line)
    return lines


def run_logcli(addr: str, extra_args: list[str], org_id: str | None = None) -> str:
    logcli = shutil.which("logcli")
    if not logcli:
        raise SystemExit("logcli not found in PATH.")

    env = os.environ.copy()
    env["LOKI_ADDR"] = addr
    if org_id:
        env["LOKI_ORG_ID"] = org_id

    command = [logcli, *extra_args]
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        quoted = shlex.join(command)
        raise SystemExit(f"logcli command failed: {quoted}\n{stderr}")
    return result.stdout


def list_projects(addr: str, since: str, org_id: str | None) -> int:
    output = run_logcli(addr, ["labels", "project", f"--since={since}"], org_id=org_id)
    for line in clean_output_lines(output):
        print(line)
    return 0


def list_files(
    addr: str,
    project: str,
    since: str,
    contains: str | None,
    org_id: str | None,
    *,
    print_output: bool = True,
) -> list[str]:
    selector = f'{{project="{project}"}}'
    output = run_logcli(addr, ["series", selector, f"--since={since}"], org_id=org_id)
    filenames = sorted({match.group(1) for match in FILENAME_PATTERN.finditer(output)})
    if contains:
        filenames = [name for name in filenames if contains in name]
    if print_output:
        for name in filenames:
            print(name)
    return filenames


def build_query(project: str, filename: str | None, grep: str | None, regex: str | None) -> str:
    selector_parts = [f'project="{project}"']
    if filename:
        selector_parts.append(f'filename="{filename}"')
    query = "{" + ", ".join(selector_parts) + "}"
    if grep:
        query += f' |= "{grep}"'
    if regex:
        query += f' |~ "{regex}"'
    return query


def resolve_target_filenames(
    addr: str,
    project: str,
    since: str,
    filenames: list[str],
    component: str | None,
    org_id: str | None,
    *,
    stderr_only: bool = False,
) -> list[str]:
    if filenames:
        return filenames
    available = list_files(addr, project, since, component, org_id, print_output=False)
    if stderr_only:
        available = [name for name in available if "stderr" in name]
    if available:
        return available
    if component:
        raise SystemExit(f"No filenames matched component substring: {component}")
    return []


def query_logs(
    addr: str,
    project: str,
    since: str,
    limit: int,
    filenames: list[str],
    component: str | None,
    grep: str | None,
    regex: str | None,
    org_id: str | None,
    stderr_only: bool = False,
) -> int:
    targets = resolve_target_filenames(
        addr,
        project,
        since,
        filenames,
        component,
        org_id,
        stderr_only=stderr_only,
    )
    if not targets:
        query = build_query(project, None, grep, regex)
        print(f"# query: {query}")
        output = run_logcli(addr, ["query", f"--limit={limit}", f"--since={since}", query], org_id=org_id)
        sys.stdout.write(output)
        return 0

    for index, filename in enumerate(targets, start=1):
        if index > 1:
            print()
        query = build_query(project, filename, grep, regex)
        print(f"# file: {filename}")
        print(f"# query: {query}")
        output = run_logcli(addr, ["query", f"--limit={limit}", f"--since={since}", query], org_id=org_id)
        sys.stdout.write(output)
    return 0


def main() -> int:
    args = parse_args()
    addr = resolve_loki_addr(args.addr)

    if args.command == "projects":
        return list_projects(addr, args.since, args.org_id)

    if args.command == "files":
        list_files(addr, args.project, args.since, args.contains, args.org_id)
        return 0

    if args.command == "query":
        return query_logs(
            addr=addr,
            project=args.project,
            since=args.since,
            limit=args.limit,
            filenames=args.filename,
            component=args.component,
            grep=args.grep,
            regex=args.regex,
            org_id=args.org_id,
        )

    if args.command == "errors":
        return query_logs(
            addr=addr,
            project=args.project,
            since=args.since,
            limit=args.limit,
            filenames=[],
            component=args.component,
            grep=None,
            regex=ERROR_PATTERN,
            org_id=args.org_id,
            stderr_only=True,
        )

    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
