# Atlassian MCP — Jira & Confluence CLI

A standalone CLI tool and Python library for interacting with Atlassian Cloud
(Jira & Confluence) REST APIs. This package provides a lightweight, async client backed by
[httpx](https://www.python-httpx.org/).

## Features

- **Jira** — search issues (JQL), get issue details, create issues, add comments
- **Confluence** — search pages, get page content, create pages, update pages, add comments
- **File-based input** — `--body-file`, `--description-file`, `--comment-file` flags to avoid shell quoting issues
- Built-in connection test
- Designed as a VS Code Copilot workaround via custom instructions + terminal CLI

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Copy and fill in your credentials
cp .env.example .env

# 3. Test connectivity
uv run python -m atlassian_mcp test-connection

# 4. Search Jira
uv run python -m atlassian_mcp jira-search "project = MYPROJ ORDER BY updated DESC"

# 5. Search Confluence
uv run python -m atlassian_mcp confluence-search "architecture docs"
```

## Available Commands

| Command | Description |
|---|---|
| `test-connection` | Verify Jira & Confluence connectivity |
| `jira-search <jql>` | Search issues with JQL |
| `jira-get <issue-key> [--comments]` | Get full issue details |
| `jira-create --project KEY --summary TEXT [--type TYPE] [--description-file FILE]` | Create an issue |
| `jira-comment <issue-key> <comment> [--comment-file FILE]` | Add a comment |
| `confluence-search <query> [--space SPACE]` | Search pages |
| `confluence-get <page-id>` | Get page content |
| `confluence-create --space KEY --title T [--body HTML \| --body-file FILE]` | Create a page |
| `confluence-update <page-id> --title T [--body HTML \| --body-file FILE]` | Update a page |
| `confluence-comment <page-id> <comment> [--comment-file FILE]` | Comment on a page |

All commands that accept long text support reading from a file (`--body-file`,
`--description-file`, `--comment-file`). Pass `-` to read from stdin.

## Environment Variables

See [.env.example](.env.example) for required configuration.

## VS Code Copilot Integration

The [.github/copilot-instructions.md](.github/copilot-instructions.md) file teaches
GitHub Copilot Chat how to invoke the CLI via terminal, enabling Jira/Confluence
operations directly from the editor.
