# Agent Onboarding — Atlassian MCP

This file gets you (the AI agent) up and running with the Atlassian MCP CLI as
fast as possible. Read this first, then start using the CLI.

## What This Project Is

A Python CLI that talks to Atlassian Cloud (Jira + Confluence) REST APIs. You
use it to search, read, create, update, and comment on Jira issues and
Confluence pages — all from the terminal.

## Pre-flight Checklist

Before you can run any commands, the human needs a `.env` file with credentials.
Check if it exists:

```
Test-Path .env          # PowerShell
test -f .env            # bash
```

### If `.env` is missing or empty, walk the human through this:

1. **Copy the template:**
   ```
   cp .env.example .env
   ```

2. **Fill in `ATLASSIAN_EMAIL`** — their Atlassian account email (usually their
   work email, e.g. `first.last@lululemon.com`).

3. **Generate `ATLASSIAN_API_TOKEN`** — direct them to:
   > **https://id.atlassian.com/manage-profile/security/api-tokens**
   >
   > Click **"Create API token"**, give it a label like `copilot-cli`, copy the
   > token, and paste it into `.env`.

4. **Verify `ATLASSIAN_BASE_URL`** — defaults to `https://lululemon.atlassian.net`.
   Only change this if targeting a different Atlassian instance.

5. **Test connectivity:**
   ```
   uv run python -m atlassian_mcp test-connection
   ```
   You should see `Jira: connected` and `Confluence: connected`. If not, the
   token or email is wrong — have the human double-check.

### If `uv` is not installed

The human needs [uv](https://docs.astral.sh/uv/getting-started/installation/):
```
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then run `uv sync` once inside the project directory to install dependencies.

## How to Use the CLI

Every command follows this pattern:

```
uv run python -m atlassian_mcp <command> [args]
```

### Quick Reference

| Command | What it does |
|---|---|
| `test-connection` | Verify Jira & Confluence connectivity |
| `jira-search "<JQL>"` | Search issues with JQL |
| `jira-get <KEY> [--comments]` | Get issue details |
| `jira-create --project KEY --summary "text" [--type T] [--priority P] [--labels a,b] [--description-file F]` | Create an issue |
| `jira-comment <KEY> "text"` or `--comment-file F` | Comment on an issue |
| `confluence-search "query" [--space KEY]` | Search pages |
| `confluence-get <PAGE-ID>` | Get page content (returns HTML) |
| `confluence-create --space KEY --title "T" [--body HTML \| --body-file F] [--parent ID]` | Create a page |
| `confluence-update <PAGE-ID> --title "T" [--body HTML \| --body-file F]` | Update a page (auto-increments version) |
| `confluence-comment <PAGE-ID> "text"` or `--comment-file F` | Comment on a page |
| `confluence-attach <PAGE-ID> <FILE-PATH>` | Upload a file attachment |

### Shell Safety: Use `--*-file` Flags for Long Content

The shell **will mangle** long strings with quotes, HTML, or special characters.
For any body, description, or comment longer than a short sentence:

1. Write the content to a temp file first.
2. Pass it with `--body-file`, `--description-file`, or `--comment-file`.
3. Clean up the temp file after.

```bash
# Example: update a Confluence page with HTML from a file
uv run python -m atlassian_mcp confluence-update 12345678 --title "My Page" --body-file content.html

# Stdin also works (pass "-" as the file path)
cat content.html | uv run python -m atlassian_mcp confluence-update 12345678 --title "My Page" --body-file -
```

**Never pass raw HTML as an inline argument.** It will break.

## All Output Is JSON

Every command prints JSON to stdout. Parse it to extract what you need.
Errors go to stderr with a non-zero exit code.

## Common Patterns

### Look up an issue the human mentions
```
uv run python -m atlassian_mcp jira-get RFID-123 --comments
```

### Search for recent work in a project
```
uv run python -m atlassian_mcp jira-search "project = RFID AND updated >= -7d ORDER BY updated DESC"
```

### Find a Confluence page, then read it
```
uv run python -m atlassian_mcp confluence-search "deployment guide" --space RFID
# Take the page ID from the results, then:
uv run python -m atlassian_mcp confluence-get <PAGE-ID>
```

### Create a Jira issue (confirm project + summary with the human first)
```
uv run python -m atlassian_mcp jira-create --project RFID --summary "Fix reader timeout" --type Bug --priority High
```

### Update a Confluence page with rich content
```
# 1. Write HTML to a temp file
# 2. Push it
uv run python -m atlassian_mcp confluence-update <PAGE-ID> --title "Page Title" --body-file content.html
# 3. Remove the temp file
```

## Useful JQL Patterns

| Pattern | JQL |
|---|---|
| Active work | `project = RFID AND status = "In Progress"` |
| My issues | `project = RFID AND assignee = currentUser()` |
| Current sprint | `project = RFID AND sprint in openSprints()` |
| By label | `project = RFID AND labels = "rfid-cloud"` |
| Recent issues | `project = RFID AND created >= -7d` |
| Specific type | `project = RFID AND issuetype = Bug` |

## Project Structure

```
atlassian_mcp/
  __init__.py        # Package metadata
  __main__.py        # Entry point (python -m atlassian_mcp)
  cli.py             # CLI command definitions + argument parser
  client.py          # Async Atlassian REST API client (httpx)
.github/
  copilot-instructions.md   # Copilot Chat custom instructions
.env.example         # Template for credentials
pyproject.toml       # Python project config (hatchling build)
```

## Things to Watch Out For

- **Never hardcode or print credentials.** The `.env` file is gitignored.
- **Confluence page IDs are numeric.** Search first to find the ID, then get/update.
- **Confluence page updates require a title.** Always pass `--title` even if unchanged.
- **HTML auto-wrap:** If you pass plain text to `--body` or `comment`, the CLI wraps
  it in `<p>` tags. If your text starts with `<`, it's assumed to be HTML already.
- **Confirm before creating:** Always confirm the project key and summary with the
  human before running `jira-create`.
