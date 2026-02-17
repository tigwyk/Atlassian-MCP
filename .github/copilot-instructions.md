# Copilot Custom Instructions — Atlassian MCP Workspace

## Jira & Confluence Access

This workspace contains a CLI that talks to Lululemon's Atlassian Cloud instance (Jira + Confluence). All commands should be run from the workspace root (`c:\Users\lingram\Documents\Scripts\Atlassian-MCP`).

### How to use the CLI

The CLI is invoked via:

```
uv run python -m atlassian_mcp <command> [args]
```

### Available Commands

| Command | Purpose | Example |
|---|---|---|
| `test-connection` | Verify Jira & Confluence connectivity | `uv run python -m atlassian_mcp test-connection` |
| `jira-search` | Search issues with JQL | `uv run python -m atlassian_mcp jira-search "project = RFID ORDER BY updated DESC"` |
| `jira-get` | Get single issue details | `uv run python -m atlassian_mcp jira-get RFID-42` |
| `jira-get --comments` | Get issue with comments | `uv run python -m atlassian_mcp jira-get RFID-42 --comments` |
| `jira-create` | Create a new issue | `uv run python -m atlassian_mcp jira-create --project RFID --summary "Fix reader" --type Bug --priority High` |
| `jira-comment` | Comment on an issue | `uv run python -m atlassian_mcp jira-comment RFID-42 "Comment text here"` |
| `confluence-search` | Search Confluence pages | `uv run python -m atlassian_mcp confluence-search "RFID architecture"` |
| `confluence-search --space` | Search within a space | `uv run python -m atlassian_mcp confluence-search "deployment" --space RFID` |
| `confluence-get` | Get full page content | `uv run python -m atlassian_mcp confluence-get 12345678` |
| `confluence-create` | Create a new page | `uv run python -m atlassian_mcp confluence-create --space RFID --title "My Page" --body "<p>Hello</p>"` |
| `confluence-create` (nested) | Create under a parent | `uv run python -m atlassian_mcp confluence-create --space RFID --title "Child" --body "content" --parent 12345678` |
| `confluence-update` | Update a page | `uv run python -m atlassian_mcp confluence-update 12345678 --title "Updated Title" --body "<p>New body</p>"` |
| `confluence-comment` | Comment on a page | `uv run python -m atlassian_mcp confluence-comment 12345678 "Great doc!"` |

### Important behaviors

- **Always run these from the terminal** using `uv run python -m atlassian_mcp ...` — never try to import the module inline.
- All output is **JSON**. Parse it to extract relevant information for the user.
- **For long text (HTML bodies, multi-line descriptions):** write content to a temp file, then use `--body-file`, `--description-file`, or `--comment-file` instead of inline arguments. This avoids shell quoting issues. Use `-` to pipe from stdin.
  ```
  uv run python -m atlassian_mcp confluence-update 12345678 --title "My Page" --body-file content.html
  ```
- For `jira-create`, `--project` and `--summary` are required. `--type` defaults to "Task". `--labels` accepts comma-separated values (e.g. `--labels rfid-cloud,backend`).
- When asked to look something up on Jira/Confluence, use these CLI commands proactively.
- When the user references a Jira issue key (e.g. RFID-123), fetch it with `jira-get` to provide context.
- When creating issues, confirm the project key and summary with the user before executing.
- When searching, prefer specific JQL over broad queries. Common useful JQL patterns:
  - `project = RFID AND status = "In Progress"` — active work
  - `project = RFID AND assignee = currentUser()` — my issues
  - `project = RFID AND sprint in openSprints()` — current sprint
  - `project = RFID AND labels = "rfid-cloud"` — by label
  - `project = RFID AND created >= -7d` — recent issues
- Confluence page IDs are numeric. Use `confluence-search` first, then `confluence-get` with the ID from search results.
