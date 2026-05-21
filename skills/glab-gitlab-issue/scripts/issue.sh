#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/issue.sh commits --repo <repo> --author <username> [--limit <n>] [--json] [--dry-run]
  bash scripts/issue.sh view --repo <repo> --issue <id> [--comments] [--system-logs] [--cache-dir <dir>] [--no-cache] [--json] [--dry-run]
  bash scripts/issue.sh images --repo <repo> --issue <id> [--download-dir <dir>] [--json] [--dry-run]
  bash scripts/issue.sh note --repo <repo> --issue <id> --message <text> [--dry-run]
  bash scripts/issue.sh note-file --repo <repo> --issue <id> --file <path> [--dry-run]
  bash scripts/issue.sh assignee --repo <repo> --issue <id> --assignee <users> [--dry-run]
  bash scripts/issue.sh labels --repo <repo> --issue <id> [--add <labels>] [--remove <labels>] [--dry-run]
  bash scripts/issue.sh estimate --repo <repo> --issue <id> --duration <duration> [--dry-run]
  bash scripts/issue.sh add-spent --repo <repo> --issue <id> --duration <duration> [--summary <text>] [--spent-at <time>] [--dry-run]
  bash scripts/issue.sh list-spent --repo <repo> --issue <id> [--limit <n>] [--dry-run]
  bash scripts/issue.sh delete-spent --repo <repo> --issue <id> --timelog-id <gid://gitlab/Timelog/...> [--limit <n>] [--allow-other-user] [--dry-run]
  bash scripts/issue.sh reset-estimate --repo <repo> --issue <id> [--dry-run]
  bash scripts/issue.sh reset-spent --repo <repo> --issue <id> [--dry-run]

Notes:
  - <repo> accepts OWNER/REPO or GROUP/NAMESPACE/REPO.
  - <duration> example: 30m, 2h, 3h30m.
  - add-spent uses GraphQL and returns created timelog id.
  - view caches Markdown /uploads files from the issue description and notes by default.
  - images lists/downloads cached upload candidates as a lower-level helper.
  - Use list-spent first to get timelog IDs for delete-spent.
  - delete-spent verifies timelog owner is current user by default.
  - Use --dry-run to print commands without executing.
USAGE
}

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

require_glab() {
  command -v glab >/dev/null 2>&1 || die "glab command not found"
}

require_jq() {
  command -v jq >/dev/null 2>&1 || die "jq command not found"
}

run_cmd() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[DRY-RUN]'
    printf ' %q' "$@"
    printf '\n'
    return
  fi
  "$@"
}

require_python3() {
  command -v python3 >/dev/null 2>&1 || die "python3 command not found"
}

script_dir() {
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd
}

default_cache_dir() {
  local repo_slug="$1"
  local issue_id="$2"
  local cache_base="${XDG_CACHE_HOME:-$HOME/.cache}"
  printf '%s\n' "${cache_base%/}/codex/glab-gitlab-issue/${repo_slug}/${issue_id}"
}

encode_project_path() {
  local repo="$1"
  echo "${repo//\//%2F}"
}

validate_common() {
  [[ -n "$REPO" ]] || die "--repo is required"
  [[ -n "$ISSUE_ID" ]] || die "--issue is required"
}

validate_repo_only() {
  [[ -n "$REPO" ]] || die "--repo is required"
}

ACTION="${1:-help}"
shift || true

if [[ "$ACTION" == "help" || "$ACTION" == "-h" || "$ACTION" == "--help" ]]; then
  usage
  exit 0
fi

require_glab

REPO=""
ISSUE_ID=""
DRY_RUN=0
WITH_COMMENTS=0
WITH_SYSTEM_LOGS=0
OUTPUT_JSON=0
MESSAGE=""
MESSAGE_FILE=""
ASSIGNEE=""
LABELS_ADD=""
LABELS_REMOVE=""
DURATION=""
LIMIT="20"
TIMELOG_ID=""
SUMMARY=""
SPENT_AT=""
ALLOW_OTHER_USER=0
AUTHOR=""
DOWNLOAD_DIR=""
CACHE_DIR=""
NO_CACHE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    --issue)
      ISSUE_ID="${2:-}"
      shift 2
      ;;
    --comments)
      WITH_COMMENTS=1
      shift
      ;;
    --system-logs)
      WITH_SYSTEM_LOGS=1
      shift
      ;;
    --json)
      OUTPUT_JSON=1
      shift
      ;;
    --message)
      MESSAGE="${2:-}"
      shift 2
      ;;
    --file)
      MESSAGE_FILE="${2:-}"
      shift 2
      ;;
    --download-dir)
      DOWNLOAD_DIR="${2:-}"
      shift 2
      ;;
    --cache-dir)
      CACHE_DIR="${2:-}"
      shift 2
      ;;
    --no-cache)
      NO_CACHE=1
      shift
      ;;
    --assignee)
      ASSIGNEE="${2:-}"
      shift 2
      ;;
    --add)
      LABELS_ADD="${2:-}"
      shift 2
      ;;
    --remove)
      LABELS_REMOVE="${2:-}"
      shift 2
      ;;
    --duration)
      DURATION="${2:-}"
      shift 2
      ;;
    --summary)
      SUMMARY="${2:-}"
      shift 2
      ;;
    --spent-at)
      SPENT_AT="${2:-}"
      shift 2
      ;;
    --limit)
      LIMIT="${2:-}"
      shift 2
      ;;
    --timelog-id)
      TIMELOG_ID="${2:-}"
      shift 2
      ;;
    --allow-other-user)
      ALLOW_OTHER_USER=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --author)
      AUTHOR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown flag: $1"
      ;;
  esac
done

case "$ACTION" in
  commits)
    validate_repo_only
    [[ -n "$AUTHOR" ]] || die "--author is required for commits"
    [[ "$LIMIT" =~ ^[0-9]+$ ]] || die "--limit must be an integer"
    repo_encoded="$(encode_project_path "$REPO")"
    api_path="/projects/${repo_encoded}/repository/commits?author=${AUTHOR}&per_page=${LIMIT}"
    if [[ "$OUTPUT_JSON" == "1" || "$DRY_RUN" == "1" ]]; then
      run_cmd glab api "$api_path"
    else
      require_jq
      glab api "$api_path" | jq -r '.[] | "committed_date: \(.committed_date)\nauthor_name: \(.author_name)\nmessage:\n\(.message)\n---"'
    fi
    ;;
  view)
    validate_common
    if [[ "$NO_CACHE" == "1" ]]; then
      cmd=(glab issue view "$ISSUE_ID" -R "$REPO")
      if [[ "$WITH_COMMENTS" == "1" ]]; then
        cmd+=(--comments)
      fi
      if [[ "$WITH_SYSTEM_LOGS" == "1" ]]; then
        cmd+=(--system-logs)
      fi
      if [[ "$OUTPUT_JSON" == "1" ]]; then
        cmd+=(--output json)
      fi
      run_cmd "${cmd[@]}"
      exit 0
    fi

    require_python3
    repo_encoded="$(encode_project_path "$REPO")"
    cache_repo="${REPO//\//__}"
    if [[ -z "$CACHE_DIR" ]]; then
      CACHE_DIR="$(default_cache_dir "$cache_repo" "$ISSUE_ID")"
    fi
    helper_script="$(script_dir)/issue_uploads.py"
    issue_api_path="/projects/${repo_encoded}/issues/${ISSUE_ID}"
    notes_api_path="/projects/${repo_encoded}/issues/${ISSUE_ID}/notes?per_page=100"
    issue_json_path="${CACHE_DIR%/}/issue.raw.json"
    notes_json_path="${CACHE_DIR%/}/notes.raw.json"

    if [[ "$DRY_RUN" == "1" ]]; then
      run_cmd mkdir -p "$CACHE_DIR" "${CACHE_DIR%/}/uploads"
      run_cmd glab api "$issue_api_path"
      run_cmd glab api --paginate "$notes_api_path"
      run_cmd python3 "$helper_script" prepare --repo "$REPO" --issue-json "$issue_json_path" --notes-json "$notes_json_path" --cache-dir "$CACHE_DIR"
      run_cmd glab api "/projects/${repo_encoded}/uploads/<upload_hash>/<filename>"
      run_cmd python3 "$helper_script" print --cache-dir "$CACHE_DIR"
      exit 0
    fi

    mkdir -p "$CACHE_DIR" "${CACHE_DIR%/}/uploads"
    glab api "$issue_api_path" > "$issue_json_path"
    glab api --paginate "$notes_api_path" > "$notes_json_path"

    prepare_cmd=(python3 "$helper_script" prepare --repo "$REPO" --issue-json "$issue_json_path" --notes-json "$notes_json_path" --cache-dir "$CACHE_DIR")
    if [[ "$WITH_COMMENTS" == "1" ]]; then
      prepare_cmd+=(--include-comments)
    fi
    if [[ "$WITH_SYSTEM_LOGS" == "1" ]]; then
      prepare_cmd+=(--include-system-logs)
    fi
    "${prepare_cmd[@]}"

    while IFS=$'\t' read -r relative_path output_path; do
      [[ -n "$relative_path" ]] || continue
      glab api "/projects/${repo_encoded}/uploads/${relative_path}" > "$output_path"
    done < "${CACHE_DIR%/}/uploads.tsv"

    print_cmd=(python3 "$helper_script" print --cache-dir "$CACHE_DIR")
    if [[ "$OUTPUT_JSON" == "1" ]]; then
      print_cmd+=(--json)
    fi
    "${print_cmd[@]}"
    ;;
  images)
    validate_common
    require_python3
    repo_encoded="$(encode_project_path "$REPO")"
    cache_repo="${REPO//\//__}"
    if [[ -z "$DOWNLOAD_DIR" ]]; then
      CACHE_DIR="$(default_cache_dir "$cache_repo" "$ISSUE_ID")"
    else
      CACHE_DIR="$DOWNLOAD_DIR"
    fi
    helper_script="$(script_dir)/issue_uploads.py"
    issue_api_path="/projects/${repo_encoded}/issues/${ISSUE_ID}"
    notes_api_path="/projects/${repo_encoded}/issues/${ISSUE_ID}/notes?per_page=100"
    issue_json_path="${CACHE_DIR%/}/issue.raw.json"
    notes_json_path="${CACHE_DIR%/}/notes.raw.json"
    if [[ "$DRY_RUN" == "1" ]]; then
      run_cmd mkdir -p "$CACHE_DIR" "${CACHE_DIR%/}/uploads"
      run_cmd glab api "$issue_api_path"
      run_cmd glab api --paginate "$notes_api_path"
      run_cmd python3 "$helper_script" prepare --repo "$REPO" --issue-json "$issue_json_path" --notes-json "$notes_json_path" --cache-dir "$CACHE_DIR"
      run_cmd glab api "/projects/${repo_encoded}/uploads/<upload_hash>/<filename>"
      exit 0
    fi

    mkdir -p "$CACHE_DIR" "${CACHE_DIR%/}/uploads"
    glab api "$issue_api_path" > "$issue_json_path"
    glab api --paginate "$notes_api_path" > "$notes_json_path"
    python3 "$helper_script" prepare --repo "$REPO" --issue-json "$issue_json_path" --notes-json "$notes_json_path" --cache-dir "$CACHE_DIR" --include-comments --include-system-logs

    while IFS=$'\t' read -r relative_path output_path; do
      [[ -n "$relative_path" ]] || continue
      glab api "/projects/${repo_encoded}/uploads/${relative_path}" > "$output_path"
      if [[ "$OUTPUT_JSON" != "1" ]]; then
        file_summary="$(file "$output_path" 2>/dev/null || true)"
        printf '/uploads/%s -> %s\n' "$relative_path" "$file_summary"
      fi
    done < "${CACHE_DIR%/}/uploads.tsv"

    if [[ "$OUTPUT_JSON" == "1" ]]; then
      cat "${CACHE_DIR%/}/uploads.json"
    elif [[ ! -s "${CACHE_DIR%/}/uploads.tsv" ]]; then
      echo "No upload files found."
    fi
    ;;
  note)
    validate_common
    [[ -n "$MESSAGE" ]] || die "--message is required for note"
    run_cmd glab issue note "$ISSUE_ID" -R "$REPO" -m "$MESSAGE"
    ;;
  note-file)
    validate_common
    [[ -n "$MESSAGE_FILE" ]] || die "--file is required for note-file"
    [[ -f "$MESSAGE_FILE" ]] || die "file not found: $MESSAGE_FILE"
    MESSAGE_CONTENT="$(cat "$MESSAGE_FILE")"
    run_cmd glab issue note "$ISSUE_ID" -R "$REPO" -m "$MESSAGE_CONTENT"
    ;;
  assignee)
    validate_common
    [[ -n "$ASSIGNEE" ]] || die "--assignee is required for assignee"
    run_cmd glab issue update "$ISSUE_ID" -R "$REPO" --assignee "$ASSIGNEE"
    ;;
  labels)
    validate_common
    [[ -n "$LABELS_ADD" || -n "$LABELS_REMOVE" ]] || die "use --add and/or --remove for labels"
    cmd=(glab issue update "$ISSUE_ID" -R "$REPO")
    if [[ -n "$LABELS_ADD" ]]; then
      cmd+=(--label "$LABELS_ADD")
    fi
    if [[ -n "$LABELS_REMOVE" ]]; then
      cmd+=(--unlabel "$LABELS_REMOVE")
    fi
    run_cmd "${cmd[@]}"
    ;;
  estimate)
    validate_common
    [[ -n "$DURATION" ]] || die "--duration is required for estimate"
    repo_encoded="$(encode_project_path "$REPO")"
    run_cmd glab api --method POST "/projects/${repo_encoded}/issues/${ISSUE_ID}/time_estimate?duration=${DURATION}"
    ;;
  add-spent)
    validate_common
    [[ -n "$DURATION" ]] || die "--duration is required for add-spent"
    if [[ "$DRY_RUN" == "1" ]]; then
      run_cmd glab issue view "$ISSUE_ID" -R "$REPO" --output json
      if [[ -n "$SPENT_AT" ]]; then
        run_cmd glab api graphql \
          -f 'query=mutation($issuableId: IssuableID!, $timeSpent: String!, $summary: String!, $spentAt: Time!) { timelogCreate(input: { issuableId: $issuableId, timeSpent: $timeSpent, summary: $summary, spentAt: $spentAt }) { errors timelog { id spentAt timeSpent user { username } } } }' \
          -f 'issuableId=gid://gitlab/Issue/<issue_rest_id>' \
          -f "timeSpent=${DURATION}" \
          -f "summary=${SUMMARY}" \
          -f "spentAt=${SPENT_AT}"
      else
        run_cmd glab api graphql \
          -f 'query=mutation($issuableId: IssuableID!, $timeSpent: String!, $summary: String!) { timelogCreate(input: { issuableId: $issuableId, timeSpent: $timeSpent, summary: $summary }) { errors timelog { id spentAt timeSpent user { username } } } }' \
          -f 'issuableId=gid://gitlab/Issue/<issue_rest_id>' \
          -f "timeSpent=${DURATION}" \
          -f "summary=${SUMMARY}"
      fi
      exit 0
    fi
    require_python3
    issue_view_json="$(glab issue view "$ISSUE_ID" -R "$REPO" --output json)"
    issue_rest_id="$(
      printf '%s' "$issue_view_json" | python3 -c 'import json,sys; data=json.load(sys.stdin); print(data.get("id", ""))'
    )"
    [[ -n "$issue_rest_id" ]] || die "failed to resolve issue REST id for ${REPO}#${ISSUE_ID}"
    issuable_gid="gid://gitlab/Issue/${issue_rest_id}"
    if [[ -n "$SPENT_AT" ]]; then
      glab api graphql \
        -f 'query=mutation($issuableId: IssuableID!, $timeSpent: String!, $summary: String!, $spentAt: Time!) { timelogCreate(input: { issuableId: $issuableId, timeSpent: $timeSpent, summary: $summary, spentAt: $spentAt }) { errors timelog { id spentAt timeSpent summary user { username } issue { iid projectId } } } }' \
        -f "issuableId=${issuable_gid}" \
        -f "timeSpent=${DURATION}" \
        -f "summary=${SUMMARY}" \
        -f "spentAt=${SPENT_AT}"
    else
      glab api graphql \
        -f 'query=mutation($issuableId: IssuableID!, $timeSpent: String!, $summary: String!) { timelogCreate(input: { issuableId: $issuableId, timeSpent: $timeSpent, summary: $summary }) { errors timelog { id spentAt timeSpent summary user { username } issue { iid projectId } } } }' \
        -f "issuableId=${issuable_gid}" \
        -f "timeSpent=${DURATION}" \
        -f "summary=${SUMMARY}"
    fi
    ;;
  list-spent)
    validate_common
    [[ "$LIMIT" =~ ^[0-9]+$ ]] || die "--limit must be an integer"
    query='query($fullPath: ID!, $iid: String!, $first: Int!) { project(fullPath: $fullPath) { issue(iid: $iid) { timelogs(first: $first) { nodes { id spentAt timeSpent summary user { username } } } } } }'
    run_cmd glab api graphql \
      -f "query=${query}" \
      -f "fullPath=${REPO}" \
      -f "iid=${ISSUE_ID}" \
      -F "first=${LIMIT}"
    ;;
  delete-spent)
    validate_common
    [[ -n "$TIMELOG_ID" ]] || die "--timelog-id is required for delete-spent"
    [[ "$LIMIT" =~ ^[0-9]+$ ]] || die "--limit must be an integer"
    if [[ "$DRY_RUN" != "1" ]]; then
      require_python3
      verify_query='query($fullPath: ID!, $iid: String!, $first: Int!) { currentUser { username } project(fullPath: $fullPath) { issue(iid: $iid) { timelogs(first: $first) { nodes { id user { username } } } } } }'
      verify_json="$(
        glab api graphql \
          -f "query=${verify_query}" \
          -f "fullPath=${REPO}" \
          -f "iid=${ISSUE_ID}" \
          -F "first=${LIMIT}"
      )"
      verify_result="$(
        printf '%s' "$verify_json" | python3 -c 'import json,sys
target_id=sys.argv[1]
allow_other=sys.argv[2] == "1"
data=json.load(sys.stdin)
project=data.get("data", {}).get("project")
if project is None:
    print("project_not_found")
    raise SystemExit(20)
issue=project.get("issue")
if issue is None:
    print("issue_not_found")
    raise SystemExit(21)
current_user=data.get("data", {}).get("currentUser", {}).get("username", "")
for node in issue.get("timelogs", {}).get("nodes", []):
    if node.get("id") == target_id:
        owner=node.get("user", {}).get("username", "")
        if owner != current_user and not allow_other:
            print(f"owner_mismatch:{owner}:{current_user}")
            raise SystemExit(22)
        print(owner)
        raise SystemExit(0)
print("timelog_not_found")
raise SystemExit(23)
' "$TIMELOG_ID" "$ALLOW_OTHER_USER"
      )" || {
        case "$?" in
          20) die "project not found: $REPO" ;;
          21) die "issue not found: $REPO#${ISSUE_ID}" ;;
          22) die "timelog owner mismatch (${verify_result}). Refusing delete without --allow-other-user." ;;
          23) die "timelog not found in first ${LIMIT} entries for ${REPO}#${ISSUE_ID}; increase --limit." ;;
          *) die "failed to verify timelog owner" ;;
        esac
      }
      : "${verify_result:?failed to verify timelog owner}"
    fi
    query='mutation($id: TimelogID!) { timelogDelete(input: { id: $id }) { errors } }'
    run_cmd glab api graphql -f "query=${query}" -f "id=${TIMELOG_ID}"
    ;;
  reset-estimate)
    validate_common
    repo_encoded="$(encode_project_path "$REPO")"
    run_cmd glab api --method POST "/projects/${repo_encoded}/issues/${ISSUE_ID}/reset_time_estimate"
    ;;
  reset-spent)
    validate_common
    repo_encoded="$(encode_project_path "$REPO")"
    run_cmd glab api --method POST "/projects/${repo_encoded}/issues/${ISSUE_ID}/reset_spent_time"
    ;;
  *)
    die "unknown action: $ACTION"
    ;;
esac
