"""Atlassian (Jira & Confluence) API client.

Connects to Atlassian Cloud using email + API token authentication.
All methods are async and return parsed JSON responses.
"""

import os
import logging
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class AtlassianConfig:
    """Atlassian Cloud configuration loaded from environment variables."""

    def __init__(self):
        self.base_url: str = os.getenv(
            "ATLASSIAN_BASE_URL", "https://lululemon.atlassian.net"
        ).rstrip("/")
        self.email: str = os.getenv("ATLASSIAN_EMAIL", "")
        self.api_token: str = os.getenv("ATLASSIAN_API_TOKEN", "")
        self.timeout: int = int(os.getenv("ATLASSIAN_TIMEOUT", "30"))

        missing: list[str] = []
        if not self.email:
            missing.append("ATLASSIAN_EMAIL")
        if not self.api_token:
            missing.append("ATLASSIAN_API_TOKEN")
        if missing:
            raise ValueError(
                f"Missing required Atlassian env vars: {', '.join(missing)}. "
                "Please add them to your .env file."
            )

    @property
    def jira_rest_url(self) -> str:
        return f"{self.base_url}/rest/api/3"

    @property
    def confluence_rest_url(self) -> str:
        return f"{self.base_url}/wiki/api/v2"

    @property
    def auth(self) -> tuple[str, str]:
        """Basic-auth credentials tuple (email, api_token)."""
        return (self.email, self.api_token)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class AtlassianClient:
    """Async wrapper around Jira & Confluence REST APIs (Atlassian Cloud)."""

    def __init__(self, config: AtlassianConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    # -- lifecycle -----------------------------------------------------------

    async def initialize(self):
        """Create the underlying httpx client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                auth=self.config.auth,
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )

    async def close(self):
        """Close the underlying httpx client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_client(self):
        if self._client is None:
            await self.initialize()

    # -- helpers -------------------------------------------------------------

    async def _get(self, url: str, params: Optional[dict] = None) -> Any:
        await self._ensure_client()
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def _post(self, url: str, json_body: dict) -> Any:
        await self._ensure_client()
        resp = await self._client.post(url, json=json_body)
        resp.raise_for_status()
        return resp.json()

    async def _put(self, url: str, json_body: dict) -> Any:
        await self._ensure_client()
        resp = await self._client.put(url, json=json_body)
        resp.raise_for_status()
        return resp.json()

    # ======================================================================
    # Jira
    # ======================================================================

    async def test_jira_connection(self) -> bool:
        """Quick connectivity check against Jira."""
        try:
            await self._get(f"{self.config.jira_rest_url}/myself")
            return True
        except Exception:
            return False

    async def search_issues(
        self,
        jql: str,
        fields: Optional[List[str]] = None,
        max_results: int = 50,
        start_at: int = 0,
    ) -> Dict[str, Any]:
        """Search Jira issues using JQL."""
        if max_results > 100:
            max_results = 100

        default_fields = [
            "summary", "status", "assignee", "reporter",
            "priority", "issuetype", "created", "updated", "labels",
        ]

        params = {
            "jql": jql,
            "maxResults": str(max_results),
            "startAt": str(start_at),
            "fields": ",".join(fields or default_fields),
        }
        return await self._get(f"{self.config.jira_rest_url}/search/jql", params=params)

    async def get_issue(
        self, issue_key: str, fields: Optional[List[str]] = None, expand: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch a single Jira issue by key (e.g. RFID-123)."""
        params: dict[str, str] = {}
        if fields:
            params["fields"] = ",".join(fields)
        if expand:
            params["expand"] = expand

        return await self._get(
            f"{self.config.jira_rest_url}/issue/{issue_key}", params=params or None
        )

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        description: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignee_account_id: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new Jira issue."""
        fields_payload: Dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }

        if description:
            if isinstance(description, str):
                fields_payload["description"] = {
                    "version": 1,
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                }
            else:
                fields_payload["description"] = description

        if priority:
            fields_payload["priority"] = {"name": priority}
        if labels:
            fields_payload["labels"] = labels
        if assignee_account_id:
            fields_payload["assignee"] = {"accountId": assignee_account_id}
        if extra_fields:
            fields_payload.update(extra_fields)

        return await self._post(
            f"{self.config.jira_rest_url}/issue",
            {"fields": fields_payload},
        )

    async def add_comment(
        self, issue_key: str, body_text: str
    ) -> Dict[str, Any]:
        """Add a comment to a Jira issue."""
        adf_body = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": body_text}],
                }
            ],
        }
        return await self._post(
            f"{self.config.jira_rest_url}/issue/{issue_key}/comment",
            {"body": adf_body},
        )

    # ======================================================================
    # Confluence
    # ======================================================================

    async def test_confluence_connection(self) -> bool:
        """Quick connectivity check against Confluence."""
        try:
            await self._get(f"{self.config.confluence_rest_url}/spaces", params={"limit": "1"})
            return True
        except Exception:
            return False

    async def search_confluence(
        self,
        query: str,
        space_key: Optional[str] = None,
        limit: int = 25,
        start: int = 0,
    ) -> Dict[str, Any]:
        """Search Confluence pages via CQL."""
        if limit > 100:
            limit = 100

        cql_parts: list[str] = ['type = "page"']
        if space_key:
            cql_parts.append(f'space = "{space_key}"')

        if any(op in query for op in ["=", "~", "AND", "OR", "IN"]):
            cql_parts.append(f"({query})")
        else:
            cql_parts.append(f'text ~ "{query}"')

        cql = " AND ".join(cql_parts)

        params = {
            "cql": cql,
            "limit": str(limit),
            "start": str(start),
        }
        return await self._get(
            f"{self.config.base_url}/wiki/rest/api/content/search", params=params
        )

    async def get_confluence_page(
        self, page_id: str, expand: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve a single Confluence page by ID."""
        default_expand = "body.storage,version,space"
        params = {"expand": expand or default_expand}
        return await self._get(
            f"{self.config.base_url}/wiki/rest/api/content/{page_id}", params=params
        )

    async def create_confluence_page(
        self,
        space_key: str,
        title: str,
        body_html: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Confluence page."""
        payload: Dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": body_html,
                    "representation": "storage",
                }
            },
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]

        return await self._post(
            f"{self.config.base_url}/wiki/rest/api/content", payload
        )

    async def update_confluence_page(
        self,
        page_id: str,
        title: str,
        body_html: str,
        version_number: int,
    ) -> Dict[str, Any]:
        """Update an existing Confluence page."""
        payload = {
            "type": "page",
            "title": title,
            "version": {"number": version_number},
            "body": {
                "storage": {
                    "value": body_html,
                    "representation": "storage",
                }
            },
        }
        return await self._put(
            f"{self.config.base_url}/wiki/rest/api/content/{page_id}", payload
        )

    async def add_confluence_comment(
        self,
        page_id: str,
        body_html: str,
    ) -> Dict[str, Any]:
        """Add a comment to a Confluence page."""
        payload = {
            "type": "comment",
            "container": {"id": page_id, "type": "page"},
            "body": {
                "storage": {
                    "value": body_html,
                    "representation": "storage",
                }
            },
        }
        return await self._post(
            f"{self.config.base_url}/wiki/rest/api/content", payload
        )


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_atlassian_client: Optional[AtlassianClient] = None


def get_atlassian_client() -> AtlassianClient:
    """Get or create a global AtlassianClient singleton."""
    global _atlassian_client
    if _atlassian_client is None:
        config = AtlassianConfig()
        _atlassian_client = AtlassianClient(config)
    return _atlassian_client
