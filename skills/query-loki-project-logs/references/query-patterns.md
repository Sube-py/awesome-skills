# Query Patterns

## Common Discovery Commands

List projects:

```bash
export LOKI_ADDR=http://your-loki:3100
logcli labels project --since=720h
```

List filenames for one project:

```bash
logcli series '{project="pd_router_test"}' --since=24h
```

List filenames and inspect label diversity:

```bash
logcli series '{project="pd_router_test"}' --since=24h --analyze-labels
```

## Common Query Commands

Query a specific stream:

```bash
logcli query --limit=50 --since=1h '{project="pd_router_test", filename="/var/log/projects/pd_router_test/pd_router-web-stderr.log"}'
```

Search for likely errors in web stderr:

```bash
logcli query --limit=80 --since=1h '{project="pd_router_test", filename="/var/log/projects/pd_router_test/pd_router-web-stderr.log"} |~ "(ERROR|Error|Exception|Traceback|panic|FATAL|CRITICAL|sqlalchemy\\.exc\\.|asyncpg\\.exceptions\\.)"'
```

Search for a request path in web stdout:

```bash
logcli query --limit=100 --since=1h '{project="pd_router_test", filename="/var/log/projects/pd_router_test/pd_router-web-stdout.log"} |= "/api/v1/service-catalog/categories"'
```

## Stream Heuristics

- Prefer `web-stderr` for Python tracebacks and uncaught exceptions.
- Prefer `web-stdout` for request logs and info messages around an error.
- Prefer `worker-stderr` for async or background task failures.
- Prefer `nginx-stderr` for upstream and config failures.
- Prefer `nginx-stdout` for access-log confirmation of status codes and request volume.

## Example User Requests

- "看一下 `pd_router_test` 近一个小时的 web 日志有没有报错"
- "列一下 `chatdoc_test` 现在有哪些日志文件"
- "帮我搜 `chatdoc_biz_test` worker 最近 24 小时的 Traceback"
- "看 `pd_router_test` nginx 有没有 5xx 相关日志"
