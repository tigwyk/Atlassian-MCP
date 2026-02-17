"""CLI for Jira & Confluence operations.

Usage:
    uv run python -m atlassian_mcp <command> [args]

Commands:
    test-connection      Test Jira & Confluence connectivity
    jira-search          Search issues via JQL
    jira-get             Get a single issue by key
    jira-create          Create a new issue
    jira-comment         Add a comment to an issue
    confluence-search    Search Confluence pages
    confluence-get       Get a Confluence page by ID
    confluence-create    Create a new Confluence page
    confluence-update    Update an existing Confluence page
    confluence-comment   Comment on a Confluence page

Examples:
    uv run python -m atlassian_mcp test-connection
    uv run python -m atlassian_mcp jira-search "project = RFID ORDER BY updated DESC"
    uv run python -m atlassian_mcp jira-get RFID-42 --comments
    uv run python -m atlassian_mcp jira-create --project RFID --summary "Fix reader" --type Bug
    uv run python -m atlassian_mcp jira-comment RFID-42 "Comment text"
    uv run python -m atlassian_mcp confluence-search "RFID architecture"
    uv run python -m atlassian_mcp confluence-get 12345678
    uv run python -m atlassian_mcp confluence-create --space RFID --title "Page" --body "<p>Hi</p>"
    uv run python -m atlassian_mcp confluence-update 12345678 --title "Updated" --body "New body"
    uv run python -m atlassian_mcp confluence-comment 12345678 "Great doc!"
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from atlassian_mcp.client import get_atlassian_client


def _resolve_text(inline: str | None, file_path: str | None) -> str | None:
    """Return text from *inline* or by reading *file_path*.

    If *file_path* is ``"-"``, reads from stdin.  This lets callers
    avoid passing long strings through the shell::

        --body-file content.html   # read from file
        --body-file -              # read from stdin (pipe)
    """
    if file_path is not None:
        if file_path == "-":
            return sys.stdin.read()
        return Path(file_path).read_text(encoding="utf-8")
    return inline


def _print_json(data: Any) -> None:
    """Pretty-print a dict/list as JSON."""
    print(json.dumps(data, indent=2, default=str))


def _adf_to_plain_text(adf: dict) -> str:
    """Recursively extract plain text from an Atlassian Document Format node."""
    if not isinstance(adf, dict):
        return str(adf) if adf else ""
    text = adf.get("text", "")
    for child in adf.get("content", []):
        text += _adf_to_plain_text(child)
    return text


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def cmd_test_connection() -> None:
    atl = get_atlassian_client()
    await atl.initialize()
    jira_ok = await atl.test_jira_connection()
    conf_ok = await atl.test_confluence_connection()
    print(f"Jira:       {'connected' if jira_ok else 'FAILED'}")
    print(f"Confluence: {'connected' if conf_ok else 'FAILED'}")
    await atl.close()


async def cmd_jira_search(jql: str, max_results: int = 25) -> None:
    atl = get_atlassian_client()
    await atl.initialize()
    data = await atl.search_issues(jql, max_results=max_results)
    issues = []
    for issue in data.get("issues", []):
        f = issue.get("fields", {})
        issues.append({
            "key": issue["key"],
            "summary": f.get("summary"),
            "status": (f.get("status") or {}).get("name"),
            "priority": (f.get("priority") or {}).get("name"),
            "type": (f.get("issuetype") or {}).get("name"),
            "assignee": (f.get("assignee") or {}).get("displayName"),
            "labels": f.get("labels", []),
            "updated": f.get("updated"),
            "url": f"{atl.config.base_url}/browse/{issue['key']}",
        })
    _print_json({"total": data.get("total", 0), "issues": issues})
    await atl.close()


async def cmd_jira_get(issue_key: str, include_comments: bool = False) -> None:
    atl = get_atlassian_client()
    await atl.initialize()
    data = await atl.get_issue(issue_key, expand="renderedFields")
    f = data.get("fields", {})
    rf = data.get("renderedFields", {})

    result: dict[str, Any] = {
        "key": data["key"],
        "summary": f.get("summary"),
        "status": (f.get("status") or {}).get("name"),
        "priority": (f.get("priority") or {}).get("name"),
        "type": (f.get("issuetype") or {}).get("name"),
        "assignee": (f.get("assignee") or {}).get("displayName"),
        "reporter": (f.get("reporter") or {}).get("displayName"),
        "labels": f.get("labels", []),
        "created": f.get("created"),
        "updated": f.get("updated"),
        "description_html": rf.get("description", ""),
        "url": f"{atl.config.base_url}/browse/{data['key']}",
    }

    if include_comments:
        comment_data = f.get("comment", {}).get("comments", [])
        result["comments"] = [
            {
                "author": (c.get("author") or {}).get("displayName"),
                "created": c.get("created"),
                "body": _adf_to_plain_text(c.get("body", {})),
            }
            for c in comment_data
        ]

    _print_json(result)
    await atl.close()


async def cmd_jira_create(
    project_key: str,
    summary: str,
    issue_type: str = "Task",
    description: str | None = None,
    priority: str | None = None,
    labels: list[str] | None = None,
) -> None:
    atl = get_atlassian_client()
    await atl.initialize()
    data = await atl.create_issue(
        project_key=project_key,
        summary=summary,
        issue_type=issue_type,
        description=description,
        priority=priority,
        labels=labels,
    )
    _print_json({
        "key": data["key"],
        "id": data["id"],
        "url": f"{atl.config.base_url}/browse/{data['key']}",
    })
    await atl.close()


async def cmd_jira_comment(issue_key: str, comment: str) -> None:
    atl = get_atlassian_client()
    await atl.initialize()
    data = await atl.add_comment(issue_key, comment)
    _print_json({
        "comment_id": data.get("id"),
        "created": data.get("created"),
        "issue_key": issue_key,
    })
    await atl.close()


async def cmd_confluence_search(
    query: str, space_key: str | None = None, limit: int = 25
) -> None:
    atl = get_atlassian_client()
    await atl.initialize()
    data = await atl.search_confluence(query, space_key=space_key, limit=limit)
    pages = []
    for r in data.get("results", []):
        pages.append({
            "id": r.get("id"),
            "title": r.get("title"),
            "space": (r.get("space") or {}).get("key"),
            "url": f"{atl.config.base_url}/wiki{r.get('_links', {}).get('webui', '')}",
        })
    _print_json({"total": data.get("totalSize", data.get("size", len(pages))), "pages": pages})
    await atl.close()


async def cmd_confluence_get(page_id: str) -> None:
    atl = get_atlassian_client()
    await atl.initialize()
    data = await atl.get_confluence_page(page_id)
    body = (data.get("body") or {}).get("storage", {}).get("value", "")
    _print_json({
        "id": data.get("id"),
        "title": data.get("title"),
        "space": (data.get("space") or {}).get("key"),
        "version": (data.get("version") or {}).get("number"),
        "body_html": body,
        "url": f"{atl.config.base_url}/wiki{data.get('_links', {}).get('webui', '')}",
    })
    await atl.close()


async def cmd_confluence_create(
    space_key: str, title: str, body: str, parent_id: str | None = None
) -> None:
    atl = get_atlassian_client()
    await atl.initialize()
    if not body.strip().startswith("<"):
        body = f"<p>{body}</p>"
    data = await atl.create_confluence_page(space_key, title, body, parent_id=parent_id)
    _print_json({
        "id": data.get("id"),
        "title": data.get("title"),
        "space": (data.get("space") or {}).get("key"),
        "url": f"{atl.config.base_url}/wiki{data.get('_links', {}).get('webui', '')}",
    })
    await atl.close()


async def cmd_confluence_update(page_id: str, title: str, body: str) -> None:
    atl = get_atlassian_client()
    await atl.initialize()
    current = await atl.get_confluence_page(page_id)
    current_version = (current.get("version") or {}).get("number", 1)
    if not body.strip().startswith("<"):
        body = f"<p>{body}</p>"
    data = await atl.update_confluence_page(page_id, title, body, current_version + 1)
    _print_json({
        "id": data.get("id"),
        "title": data.get("title"),
        "version": (data.get("version") or {}).get("number"),
        "url": f"{atl.config.base_url}/wiki{data.get('_links', {}).get('webui', '')}",
    })
    await atl.close()


async def cmd_confluence_comment(page_id: str, comment: str) -> None:
    atl = get_atlassian_client()
    await atl.initialize()
    if not comment.strip().startswith("<"):
        comment = f"<p>{comment}</p>"
    data = await atl.add_confluence_comment(page_id, comment)
    _print_json({
        "id": data.get("id"),
        "page_id": page_id,
        "created": (data.get("version") or {}).get("when"),
    })
    await atl.close()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atlassian_mcp",
        description="CLI for Jira & Confluence (Atlassian Cloud)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # test-connection
    sub.add_parser("test-connection", help="Test Jira & Confluence connectivity")

    # jira-search
    p = sub.add_parser("jira-search", help="Search Jira issues via JQL")
    p.add_argument("jql", help="JQL query string")
    p.add_argument("--max", type=int, default=25, help="Max results (default 25)")

    # jira-get
    p = sub.add_parser("jira-get", help="Get a Jira issue by key")
    p.add_argument("issue_key", help="Issue key (e.g. RFID-42)")
    p.add_argument("--comments", action="store_true", help="Include comments")

    # jira-create
    p = sub.add_parser("jira-create", help="Create a new Jira issue")
    p.add_argument("--project", required=True, help="Project key (e.g. RFID)")
    p.add_argument("--summary", required=True, help="Issue summary")
    p.add_argument("--type", default="Task", help="Issue type (default: Task)")
    p.add_argument("--description", default=None, help="Description text")
    p.add_argument("--description-file", default=None,
                   help="Read description from file (use '-' for stdin)")
    p.add_argument("--priority", default=None, help="Priority (e.g. High)")
    p.add_argument("--labels", default=None, help="Comma-separated labels")

    # jira-comment
    p = sub.add_parser("jira-comment", help="Add a comment to a Jira issue")
    p.add_argument("issue_key", help="Issue key (e.g. RFID-42)")
    p.add_argument("comment", nargs="?", default=None, help="Comment text")
    p.add_argument("--comment-file", default=None,
                   help="Read comment from file (use '-' for stdin)")

    # confluence-search
    p = sub.add_parser("confluence-search", help="Search Confluence pages")
    p.add_argument("query", help="Search keywords or CQL")
    p.add_argument("--space", default=None, help="Space key to filter by")
    p.add_argument("--max", type=int, default=25, help="Max results (default 25)")

    # confluence-get
    p = sub.add_parser("confluence-get", help="Get a Confluence page by ID")
    p.add_argument("page_id", help="Numeric page ID")

    # confluence-create
    p = sub.add_parser("confluence-create", help="Create a new Confluence page")
    p.add_argument("--space", required=True, help="Space key (e.g. RFID)")
    p.add_argument("--title", required=True, help="Page title")
    p.add_argument("--body", default=None, help="Page body (HTML or plain text)")
    p.add_argument("--body-file", default=None,
                   help="Read body from file (use '-' for stdin)")
    p.add_argument("--parent", default=None, help="Parent page ID (optional)")

    # confluence-update
    p = sub.add_parser("confluence-update", help="Update an existing Confluence page")
    p.add_argument("page_id", help="Numeric page ID")
    p.add_argument("--title", required=True, help="Page title")
    p.add_argument("--body", default=None, help="Updated body (HTML or plain text)")
    p.add_argument("--body-file", default=None,
                   help="Read body from file (use '-' for stdin)")

    # confluence-comment
    p = sub.add_parser("confluence-comment", help="Add a comment to a Confluence page")
    p.add_argument("page_id", help="Numeric page ID")
    p.add_argument("comment", nargs="?", default=None, help="Comment text")
    p.add_argument("--comment-file", default=None,
                   help="Read comment from file (use '-' for stdin)")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        match args.command:
            case "test-connection":
                asyncio.run(cmd_test_connection())
            case "jira-search":
                asyncio.run(cmd_jira_search(args.jql, max_results=args.max))
            case "jira-get":
                asyncio.run(cmd_jira_get(args.issue_key, include_comments=args.comments))
            case "jira-create":
                labels = args.labels.split(",") if args.labels else None
                description = _resolve_text(args.description, args.description_file)
                asyncio.run(cmd_jira_create(
                    project_key=args.project,
                    summary=args.summary,
                    issue_type=args.type,
                    description=description,
                    priority=args.priority,
                    labels=labels,
                ))
            case "jira-comment":
                comment = _resolve_text(args.comment, args.comment_file)
                if not comment:
                    parser.error("jira-comment requires comment text or --comment-file")
                asyncio.run(cmd_jira_comment(args.issue_key, comment))
            case "confluence-search":
                asyncio.run(cmd_confluence_search(args.query, space_key=args.space, limit=args.max))
            case "confluence-get":
                asyncio.run(cmd_confluence_get(args.page_id))
            case "confluence-create":
                body = _resolve_text(args.body, args.body_file)
                if not body:
                    parser.error("confluence-create requires --body or --body-file")
                asyncio.run(cmd_confluence_create(
                    space_key=args.space,
                    title=args.title,
                    body=body,
                    parent_id=args.parent,
                ))
            case "confluence-update":
                body = _resolve_text(args.body, args.body_file)
                if not body:
                    parser.error("confluence-update requires --body or --body-file")
                asyncio.run(cmd_confluence_update(
                    page_id=args.page_id,
                    title=args.title,
                    body=body,
                ))
            case "confluence-comment":
                comment = _resolve_text(args.comment, args.comment_file)
                if not comment:
                    parser.error("confluence-comment requires comment text or --comment-file")
                asyncio.run(cmd_confluence_comment(args.page_id, comment))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
