# glab GitLab Issue Commands

## Inputs

- `repo`: `OWNER/REPO` or `GROUP/NAMESPACE/REPO`
- `issue_id`: issue IID in that repo
- `author`: GitLab username for commit query

## Repo Encoding Rule

- For `glab issue ... -R <repo>`, use plain repo path.
- For `glab api "/projects/<repo_encoded>/..."`, `<repo_encoded>` must be URL-encoded (replace `/` with `%2F`).
- In bundled script `scripts/issue.sh`, pass plain `--repo`; script auto-encodes when needed.

## Query Commits by Author

Get recent commits by repo + author:

```bash
glab api "/projects/<repo_encoded>/repository/commits?author=<author>&per_page=20" \
| jq -r '.[] | "committed_date: \(.committed_date)\nauthor_name: \(.author_name)\nmessage:\n\(.message)\n---"'
```

JSON output:

```bash
glab api "/projects/<repo_encoded>/repository/commits?author=<author>&per_page=20"
```

## Read Issue

Show issue details. The helper caches `/uploads/...` files from the issue description and notes under `${XDG_CACHE_HOME:-$HOME/.cache}/codex/glab-gitlab-issue/` by default, then prints Markdown with local links:

```bash
bash scripts/issue.sh view --repo <repo> --issue <issue_id>
```

Show issue details with comments and activity:

```bash
bash scripts/issue.sh view --repo <repo> --issue <issue_id> --comments
```

Show JSON output with `cached_uploads`, `rewritten_description`, and `rewritten_notes`:

```bash
bash scripts/issue.sh view --repo <repo> --issue <issue_id> --comments --json
```

Use a custom cache directory:

```bash
bash scripts/issue.sh view --repo <repo> --issue <issue_id> --comments --cache-dir /tmp/issue-cache
```

Bypass caching and call `glab issue view` directly:

```bash
bash scripts/issue.sh view --repo <repo> --issue <issue_id> --no-cache
```

## Issue Upload Files

Refresh or download issue upload files through the same cache flow without printing the issue body:

```bash
bash scripts/issue.sh images --repo <repo> --issue <issue_id> --download-dir ./issue-images
```

JSON output includes upload paths, source locations, MIME guesses, and local paths:

```bash
bash scripts/issue.sh images --repo <repo> --issue <issue_id> --download-dir ./issue-images --json
```

## Comment

Post comment:

```bash
glab issue note <issue_id> -R <repo> -m "<comment>"
```

Post from file:

```bash
glab issue note <issue_id> -R <repo> -m "$(cat ./comment.md)"
```

## Update Assignee and Labels

Set or update assignee:

```bash
glab issue update <issue_id> -R <repo> --assignee <username>
```

Add assignee without replacing existing:

```bash
glab issue update <issue_id> -R <repo> --assignee +<username>
```

Add labels:

```bash
glab issue update <issue_id> -R <repo> --label bug,backend
```

Remove labels:

```bash
glab issue update <issue_id> -R <repo> --unlabel triage
```

## Time Tracking (via GitLab API)

`glab issue update` does not expose all time-tracking operations, so use `glab api`.

Encode repo path for API (`group/subgroup/project` -> `group%2Fsubgroup%2Fproject`), then call:

Set estimate:

```bash
glab api --method POST "/projects/<repo_encoded>/issues/<issue_id>/time_estimate?duration=3h"
```

Add spent time:

```bash
glab api graphql -f 'query=mutation($issuableId: IssuableID!, $timeSpent: String!, $summary: String!) { timelogCreate(input: { issuableId: $issuableId, timeSpent: $timeSpent, summary: $summary }) { errors timelog { id spentAt timeSpent user { username } } } }' -f "issuableId=gid://gitlab/Issue/<issue_rest_id>" -f "timeSpent=45m" -f "summary="
```

List timelogs (GraphQL):

```bash
glab api graphql -f 'query=query($fullPath: ID!, $iid: String!, $first: Int!) { project(fullPath: $fullPath) { issue(iid: $iid) { timelogs(first: $first) { nodes { id spentAt timeSpent summary user { username } } } } } }' -f "fullPath=<repo>" -f "iid=<issue_id>" -F "first=20"
```

Delete one timelog by ID (GraphQL):

```bash
glab api graphql -f 'query=mutation($id: TimelogID!) { timelogDelete(input: { id: $id }) { errors } }' -f "id=gid://gitlab/Timelog/<timelog_id>"
```

Owner-safe delete flow:

1. Call `list-spent` and confirm `user.username` plus `timelog id`.
2. Delete with `delete-spent --repo <repo> --issue <issue_id> --timelog-id <id>`.
3. Script blocks deletion when timelog owner != current user (unless `--allow-other-user`).

Reset estimate:

```bash
glab api --method POST "/projects/<repo_encoded>/issues/<issue_id>/reset_time_estimate"
```

Reset spent time:

```bash
glab api --method POST "/projects/<repo_encoded>/issues/<issue_id>/reset_spent_time"
```

## Helper Script Mapping

Use the bundled helper to avoid remembering raw flags:

```bash
bash scripts/issue.sh view --repo <repo> --issue <issue_id> --comments
bash scripts/issue.sh commits --repo <repo> --author <author> --limit 20
bash scripts/issue.sh note --repo <repo> --issue <issue_id> --message "text"
bash scripts/issue.sh assignee --repo <repo> --issue <issue_id> --assignee alice
bash scripts/issue.sh labels --repo <repo> --issue <issue_id> --add bug --remove triage
bash scripts/issue.sh estimate --repo <repo> --issue <issue_id> --duration 2h
bash scripts/issue.sh add-spent --repo <repo> --issue <issue_id> --duration 2h --summary "daily"
bash scripts/issue.sh list-spent --repo <repo> --issue <issue_id> --limit 20
bash scripts/issue.sh delete-spent --repo <repo> --issue <issue_id> --timelog-id gid://gitlab/Timelog/<timelog_id>
```
