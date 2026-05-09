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
EXPORT_PATTERN = re.compile(r"^export\s+([A-Za-z_][A-Za-z0-9_]*)=(.+)$")
ERROR_PATTERN = r"(ERROR|Error|Exception|Traceback|panic|FATAL|CRITICAL|sqlalchemy\\.exc\\.|asyncpg\\.exceptions\\.)"
DEFAULT_PROJECT_LABEL_CANDIDATES = ("project_name", "project")
DEFAULT_ENV_LABEL = "env"
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
    parser.add_argument("--username", help="Loki basic auth username. Defaults to LOKI_USERNAME or shell config export.")
    parser.add_argument("--password", help="Loki basic auth password. Defaults to LOKI_PASSWORD or shell config export.")
    parser.add_argument("--org-id", help="Optional Loki tenant / X-Scope-OrgID.")
    parser.add_argument(
        "--project-label",
        help="Project label name. Defaults to LOKI_PROJECT_LABEL or auto-detecting project_name/project.",
    )
    parser.add_argument(
        "--env-label",
        default=DEFAULT_ENV_LABEL,
        help=f"Environment label name. Defaults to {DEFAULT_ENV_LABEL}.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    projects_parser = subparsers.add_parser("projects", help="List project labels.")
    projects_parser.add_argument("--since", default="168h", help="Lookback window, for example 1h or 30d.")

    envs_parser = subparsers.add_parser("envs", help="List environment labels.")
    envs_parser.add_argument("--since", default="168h", help="Lookback window, for example 1h or 30d.")

    files_parser = subparsers.add_parser("files", help="List filenames for a project.")
    files_parser.add_argument("--project", required=True, help="Project label value.")
    files_parser.add_argument("--env", help="Environment label value, for example test or prod.")
    files_parser.add_argument("--since", default="24h", help="Lookback window, for example 1h or 7d.")
    files_parser.add_argument("--contains", help="Only print filenames containing this substring.")

    query_parser = subparsers.add_parser("query", help="Query one or more streams for a project.")
    query_parser.add_argument("--project", required=True, help="Project label value.")
    query_parser.add_argument("--env", help="Environment label value, for example test or prod.")
    query_parser.add_argument("--since", default="1h", help="Lookback window, for example 1h or 24h.")
    query_parser.add_argument("--limit", type=int, default=50, help="Maximum number of log lines.")
    query_parser.add_argument("--filename", action="append", default=[], help="Exact filename to query. Repeatable.")
    query_parser.add_argument("--component", help="Filename substring such as web, worker, nginx, stdout, stderr.")
    query_parser.add_argument("--grep", help="Plain-text Loki filter added with |= .")
    query_parser.add_argument("--regex", help="Regex Loki filter added with |~ .")

    errors_parser = subparsers.add_parser("errors", help="Query likely error lines for a component.")
    errors_parser.add_argument("--project", required=True, help="Project label value.")
    errors_parser.add_argument("--env", help="Environment label value, for example test or prod.")
    errors_parser.add_argument("--component", default="web", help="Filename substring such as web, worker, or nginx.")
    errors_parser.add_argument("--since", default="1h", help="Lookback window, for example 1h or 24h.")
    errors_parser.add_argument("--limit", type=int, default=80, help="Maximum number of log lines.")

    return parser.parse_args()


def read_shell_export(name: str) -> str | None:
    for shell_file in DEFAULT_SHELL_FILES:
        if not shell_file.exists():
            continue
        for raw_line in shell_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            match = EXPORT_PATTERN.match(line)
            if not match:
                continue
            export_name = match.group(1)
            if export_name != name:
                continue
            value = match.group(2).strip().strip('"').strip("'")
            if value:
                return value
    return None


def resolve_setting(cli_value: str | None, env_name: str) -> str | None:
    if cli_value:
        return cli_value

    env_value = os.environ.get(env_name, "").strip()
    if env_value:
        return env_value

    return read_shell_export(env_name)


def resolve_loki_addr(cli_addr: str | None) -> str:
    addr = resolve_setting(cli_addr, "LOKI_ADDR")
    if addr:
        return addr

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


def run_logcli(
    addr: str,
    extra_args: list[str],
    org_id: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> str:
    logcli = shutil.which("logcli")
    if not logcli:
        raise SystemExit("logcli not found in PATH.")

    env = os.environ.copy()
    env["LOKI_ADDR"] = addr
    if org_id:
        env["LOKI_ORG_ID"] = org_id
    if username:
        env["LOKI_USERNAME"] = username
    if password:
        env["LOKI_PASSWORD"] = password

    command = [logcli, *extra_args]
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        quoted = shlex.join(command)
        raise SystemExit(f"logcli command failed: {quoted}\n{stderr}")
    return result.stdout


def list_label_values(
    addr: str,
    label: str,
    since: str,
    org_id: str | None,
    username: str | None,
    password: str | None,
    *,
    print_output: bool = True,
) -> list[str]:
    output = run_logcli(
        addr,
        ["labels", label, f"--since={since}"],
        org_id=org_id,
        username=username,
        password=password,
    )
    values = clean_output_lines(output)
    if print_output:
        for line in values:
            print(line)
    return values


def resolve_project_label(
    addr: str,
    since: str,
    cli_project_label: str | None,
    org_id: str | None,
    username: str | None,
    password: str | None,
) -> str:
    configured = resolve_setting(cli_project_label, "LOKI_PROJECT_LABEL")
    if configured:
        return configured

    for candidate in DEFAULT_PROJECT_LABEL_CANDIDATES:
        values = list_label_values(
            addr,
            candidate,
            since,
            org_id,
            username,
            password,
            print_output=False,
        )
        if values:
            return candidate

    supported = ", ".join(DEFAULT_PROJECT_LABEL_CANDIDATES)
    raise SystemExit(f"Unable to detect project label automatically. Tried: {supported}")


def list_projects(
    addr: str,
    project_label: str,
    since: str,
    org_id: str | None,
    username: str | None,
    password: str | None,
) -> int:
    list_label_values(
        addr,
        project_label,
        since,
        org_id,
        username,
        password,
    )
    return 0


def build_selector(project_label: str, project: str, env_label: str, env: str | None) -> str:
    selector_parts = [f'{project_label}="{project}"']
    if env:
        selector_parts.append(f'{env_label}="{env}"')
    return "{" + ", ".join(selector_parts) + "}"


def list_files(
    addr: str,
    project_label: str,
    project: str,
    env_label: str,
    env: str | None,
    since: str,
    contains: str | None,
    org_id: str | None,
    username: str | None,
    password: str | None,
    *,
    print_output: bool = True,
) -> list[str]:
    selector = build_selector(project_label, project, env_label, env)
    output = run_logcli(
        addr,
        ["series", selector, f"--since={since}"],
        org_id=org_id,
        username=username,
        password=password,
    )
    filenames = sorted({match.group(1) for match in FILENAME_PATTERN.finditer(output)})
    if contains:
        filenames = [name for name in filenames if contains in name]
    if print_output:
        for name in filenames:
            print(name)
    return filenames


def build_query(
    project_label: str,
    project: str,
    env_label: str,
    env: str | None,
    filename: str | None,
    grep: str | None,
    regex: str | None,
) -> str:
    selector_parts = [f'{project_label}="{project}"']
    if env:
        selector_parts.append(f'{env_label}="{env}"')
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
    project_label: str,
    project: str,
    env_label: str,
    env: str | None,
    since: str,
    filenames: list[str],
    component: str | None,
    org_id: str | None,
    username: str | None,
    password: str | None,
    *,
    stderr_only: bool = False,
) -> list[str]:
    if filenames:
        return filenames
    available = list_files(
        addr,
        project_label,
        project,
        env_label,
        env,
        since,
        component,
        org_id,
        username,
        password,
        print_output=False,
    )
    if stderr_only:
        available = [name for name in available if "stderr" in name]
    if available:
        return available
    if component:
        raise SystemExit(f"No filenames matched component substring: {component}")
    return []


def query_logs(
    addr: str,
    project_label: str,
    project: str,
    env_label: str,
    env: str | None,
    since: str,
    limit: int,
    filenames: list[str],
    component: str | None,
    grep: str | None,
    regex: str | None,
    org_id: str | None,
    username: str | None,
    password: str | None,
    stderr_only: bool = False,
) -> int:
    targets = resolve_target_filenames(
        addr,
        project_label,
        project,
        env_label,
        env,
        since,
        filenames,
        component,
        org_id,
        username,
        password,
        stderr_only=stderr_only,
    )
    if not targets:
        query = build_query(project_label, project, env_label, env, None, grep, regex)
        print(f"# query: {query}")
        output = run_logcli(
            addr,
            ["query", f"--limit={limit}", f"--since={since}", query],
            org_id=org_id,
            username=username,
            password=password,
        )
        sys.stdout.write(output)
        return 0

    for index, filename in enumerate(targets, start=1):
        if index > 1:
            print()
        query = build_query(project_label, project, env_label, env, filename, grep, regex)
        print(f"# file: {filename}")
        print(f"# query: {query}")
        output = run_logcli(
            addr,
            ["query", f"--limit={limit}", f"--since={since}", query],
            org_id=org_id,
            username=username,
            password=password,
        )
        sys.stdout.write(output)
    return 0


def main() -> int:
    args = parse_args()
    addr = resolve_loki_addr(args.addr)
    username = resolve_setting(args.username, "LOKI_USERNAME")
    password = resolve_setting(args.password, "LOKI_PASSWORD")

    if args.command == "envs":
        list_label_values(
            addr,
            args.env_label,
            args.since,
            args.org_id,
            username,
            password,
        )
        return 0

    project_label = resolve_project_label(
        addr,
        args.since,
        args.project_label,
        args.org_id,
        username,
        password,
    )

    if args.command == "projects":
        return list_projects(addr, project_label, args.since, args.org_id, username, password)

    if args.command == "files":
        list_files(
            addr,
            project_label,
            args.project,
            args.env_label,
            args.env,
            args.since,
            args.contains,
            args.org_id,
            username,
            password,
        )
        return 0

    if args.command == "query":
        return query_logs(
            addr=addr,
            project_label=project_label,
            project=args.project,
            env_label=args.env_label,
            env=args.env,
            since=args.since,
            limit=args.limit,
            filenames=args.filename,
            component=args.component,
            grep=args.grep,
            regex=args.regex,
            org_id=args.org_id,
            username=username,
            password=password,
        )

    if args.command == "errors":
        return query_logs(
            addr=addr,
            project_label=project_label,
            project=args.project,
            env_label=args.env_label,
            env=args.env,
            since=args.since,
            limit=args.limit,
            filenames=[],
            component=args.component,
            grep=None,
            regex=ERROR_PATTERN,
            org_id=args.org_id,
            username=username,
            password=password,
            stderr_only=True,
        )

    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
