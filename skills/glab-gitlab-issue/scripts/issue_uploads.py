#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import shutil
from pathlib import Path
from typing import Any


UPLOAD_RE = re.compile(r"(?:https?://[^\s)\"']+)?/uploads/([A-Za-z0-9]+)/([^)\s}\"']+)")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def note_author(note: dict[str, Any]) -> str:
    author = note.get("author") or {}
    return author.get("username") or author.get("name") or "unknown"


def add_upload(
    uploads: dict[str, dict[str, Any]],
    upload_hash: str,
    filename: str,
    source: dict[str, Any],
    cache_dir: Path,
) -> None:
    upload_path = f"/uploads/{upload_hash}/{filename}"
    local_path = cache_dir / "uploads" / f"{upload_hash}_{Path(filename).name}"
    entry = uploads.setdefault(
        upload_path,
        {
            "path": upload_path,
            "relative_path": f"{upload_hash}/{filename}",
            "hash": upload_hash,
            "filename": filename,
            "local_path": str(local_path.resolve()),
            "mime_type": mimetypes.guess_type(filename)[0] or "application/octet-stream",
            "sources": [],
        },
    )
    if source not in entry["sources"]:
        entry["sources"].append(source)


def scan_text(
    uploads: dict[str, dict[str, Any]],
    text: str | None,
    source: dict[str, Any],
    cache_dir: Path,
) -> None:
    if not text:
        return
    for match in UPLOAD_RE.finditer(text):
        add_upload(uploads, match.group(1), match.group(2), source, cache_dir)


def rewrite_uploads(text: str | None, uploads: dict[str, dict[str, Any]]) -> str:
    if not text:
        return ""

    def replace(match: re.Match[str]) -> str:
        upload_path = f"/uploads/{match.group(1)}/{match.group(2)}"
        upload = uploads.get(upload_path)
        if not upload:
            return match.group(0)
        return upload["local_path"]

    return UPLOAD_RE.sub(replace, text)


def source_label(source: dict[str, Any]) -> str:
    source_type = source.get("type", "unknown")
    note_id = source.get("note_id")
    if note_id:
        return f"{source_type}:{note_id}"
    return source_type


def filtered_notes(notes: list[dict[str, Any]], include_comments: bool, include_system_logs: bool) -> list[dict[str, Any]]:
    if not include_comments and not include_system_logs:
        return []
    if include_comments and include_system_logs:
        return notes
    if include_comments:
        return [note for note in notes if not note.get("system")]
    return [note for note in notes if note.get("system")]


def render_markdown(
    repo: str,
    issue: dict[str, Any],
    notes: list[dict[str, Any]],
    uploads: dict[str, dict[str, Any]],
    cache_dir: Path,
    include_comments: bool,
    include_system_logs: bool,
) -> str:
    title = issue.get("title") or ""
    iid = issue.get("iid") or issue.get("id") or ""
    labels = ", ".join(issue.get("labels") or [])
    assignees = ", ".join(
        assignee.get("username", "")
        for assignee in issue.get("assignees", [])
        if assignee.get("username")
    )
    lines = [
        f"# {repo}#{iid} {title}".rstrip(),
        "",
        f"- State: {issue.get('state', '')}",
        f"- URL: {issue.get('web_url', '')}",
        f"- Author: {(issue.get('author') or {}).get('username', '')}",
        f"- Assignees: {assignees}",
        f"- Labels: {labels}",
        f"- Updated: {issue.get('updated_at', '')}",
        f"- Cache: {cache_dir.resolve()}",
        "",
        "## Description",
        "",
        rewrite_uploads(issue.get("description", ""), uploads),
        "",
    ]

    if uploads:
        lines.extend(["## Cached Uploads", ""])
        for upload in uploads.values():
            sources = ", ".join(source_label(source) for source in upload["sources"])
            local_path = upload["local_path"]
            filename = Path(upload["filename"]).name
            lines.append(f"- `{upload['path']}` -> [{filename}]({local_path}) ({sources})")
            if upload["mime_type"].startswith("image/"):
                lines.append(f"  ![{filename}]({local_path})")
        lines.append("")

    shown_notes = filtered_notes(notes, include_comments, include_system_logs)
    if shown_notes:
        lines.extend(["## Notes", ""])
        for note in shown_notes:
            system_suffix = " system" if note.get("system") else ""
            lines.append(f"### Note {note.get('id')} by {note_author(note)} at {note.get('created_at', '')}{system_suffix}")
            lines.append("")
            lines.append(rewrite_uploads(note.get("body", ""), uploads))
            attachment = note.get("attachment")
            if attachment:
                lines.append("")
                lines.append(f"Attachment: {rewrite_uploads(attachment, uploads)}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def prepare(args: argparse.Namespace) -> None:
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "uploads").mkdir(parents=True, exist_ok=True)

    issue = load_json(Path(args.issue_json))
    notes = load_json(Path(args.notes_json))
    if not isinstance(notes, list):
        notes = []

    uploads: dict[str, dict[str, Any]] = {}
    scan_text(uploads, issue.get("description", ""), {"type": "description"}, cache_dir)
    for note in notes:
        note_id = note.get("id")
        scan_text(uploads, note.get("body", ""), {"type": "note", "note_id": note_id}, cache_dir)
        attachment = note.get("attachment")
        if attachment:
            scan_text(uploads, attachment, {"type": "note_attachment", "note_id": note_id}, cache_dir)

    upload_list = list(uploads.values())
    issue_with_cache = dict(issue)
    issue_with_cache["cache_dir"] = str(cache_dir.resolve())
    issue_with_cache["cached_uploads"] = upload_list
    issue_with_cache["rewritten_description"] = rewrite_uploads(issue.get("description", ""), uploads)
    issue_with_cache["Notes"] = filtered_notes(notes, args.include_comments, args.include_system_logs)
    issue_with_cache["rewritten_notes"] = [
        {
            **note,
            "rewritten_body": rewrite_uploads(note.get("body", ""), uploads),
            "rewritten_attachment": rewrite_uploads(note.get("attachment", ""), uploads),
        }
        for note in issue_with_cache["Notes"]
    ]

    write_json(cache_dir / "issue.json", issue)
    write_json(cache_dir / "notes.json", notes)
    write_json(cache_dir / "uploads.json", upload_list)
    write_json(cache_dir / "view.json", issue_with_cache)
    (cache_dir / "view.md").write_text(
        render_markdown(
            repo=args.repo,
            issue=issue,
            notes=notes,
            uploads=uploads,
            cache_dir=cache_dir,
            include_comments=args.include_comments,
            include_system_logs=args.include_system_logs,
        ),
        encoding="utf-8",
    )
    with (cache_dir / "uploads.tsv").open("w", encoding="utf-8") as output:
        for upload in upload_list:
            output.write(f"{upload['relative_path']}\t{upload['local_path']}\n")


def print_cache(args: argparse.Namespace) -> None:
    cache_dir = Path(args.cache_dir)
    source = cache_dir / ("view.json" if args.json else "view.md")
    if args.json:
        print(source.read_text(encoding="utf-8"), end="")
    else:
        print(source.read_text(encoding="utf-8"), end="")


def copy_json(args: argparse.Namespace) -> None:
    source = Path(args.source)
    target = Path(args.target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare cached GitLab issue uploads.")
    subparsers = parser.add_subparsers(dest="action", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--repo", required=True)
    prepare_parser.add_argument("--issue-json", required=True)
    prepare_parser.add_argument("--notes-json", required=True)
    prepare_parser.add_argument("--cache-dir", required=True)
    prepare_parser.add_argument("--include-comments", action="store_true")
    prepare_parser.add_argument("--include-system-logs", action="store_true")
    prepare_parser.set_defaults(func=prepare)

    print_parser = subparsers.add_parser("print")
    print_parser.add_argument("--cache-dir", required=True)
    print_parser.add_argument("--json", action="store_true")
    print_parser.set_defaults(func=print_cache)

    copy_parser = subparsers.add_parser("copy-json")
    copy_parser.add_argument("--source", required=True)
    copy_parser.add_argument("--target", required=True)
    copy_parser.set_defaults(func=copy_json)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
