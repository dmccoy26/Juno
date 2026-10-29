"""Read-only TaskDock workspace connector. Never reads private configuration.

The caller supplies an approved endpoint and optional token. No source sync,
task mutation, direct SQLite access, or credential discovery is performed.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class TaskDockError(RuntimeError):
    """A refresh failed; the previous snapshot must remain marked stale."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _get(url: str, headers: dict[str, str]) -> dict:
    # Do not forward credentials to a redirect destination. Bound response size.
    try:
        with build_opener(_NoRedirect).open(
            Request(url, headers=headers, method="GET"), timeout=10
        ) as response:
            raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise TaskDockError("TaskDock response exceeded the size limit.")
            result = json.loads(raw)
    except HTTPError as error:
        # Never expose response bodies, URLs containing data, or credentials.
        raise TaskDockError(f"TaskDock returned HTTP {error.code}.") from None
    except (URLError, TimeoutError, OSError):
        raise TaskDockError("TaskDock is unavailable; refresh did not complete.") from None
    except (ValueError, UnicodeError):
        raise TaskDockError("TaskDock returned invalid JSON.") from None
    if not isinstance(result, dict):
        raise TaskDockError("TaskDock returned an invalid workspace response.")
    return result


@dataclass(frozen=True)
class WorkspaceSnapshot:
    items: tuple[dict, ...]
    revision: str
    fetched_at: str


class TaskDockReader:
    def __init__(
        self, base_url: str, token: str = "",
        transport: Callable[[str, dict[str, str]], dict] = _get,
    ):
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username or parsed.password
            or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("Use a TaskDock server origin without credentials or a path.")
        if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Non-loopback TaskDock endpoints require HTTPS.")
        self.base_url = base_url.rstrip("/")
        self._headers = {"Accept": "application/json"}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"
        self._transport = transport

    def fetch(self, max_pages: int = 100) -> WorkspaceSnapshot:
        if max_pages < 1:
            raise ValueError("max_pages must be positive.")
        items: list[dict] = []
        ids: set[str] = set()
        revision = None
        total = None
        for _ in range(max_pages):
            query = {
                "include_completed": "true", "include_archived": "false",
                "show_subtasks": "true", "sort": "manual",
                "limit": 500, "offset": len(items),
            }
            if revision is not None:
                query["expected_snapshot"] = revision
            page = self._transport(
                self.base_url + "/workspace/tasks?" + urlencode(query),
                dict(self._headers),
            )
            rows = page.get("items")
            current_revision = page.get("snapshot")
            current_total = page.get("total")
            if (
                not isinstance(rows, list) or len(rows) > 500
                or not isinstance(current_revision, str) or not current_revision
                or type(current_total) is not int or current_total < 0
                or page.get("offset") != len(items)
                or type(page.get("has_more")) is not bool
            ):
                raise TaskDockError("TaskDock workspace pagination is invalid.")
            if revision is not None and (revision != current_revision or total != current_total):
                raise TaskDockError("TaskDock changed during refresh. Retry the refresh.")
            revision, total = current_revision, current_total
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
                    raise TaskDockError("TaskDock returned an invalid task.")
                if row["id"] in ids:
                    raise TaskDockError("TaskDock returned duplicate tasks during refresh.")
                ids.add(row["id"])
                items.append(row)
            if len(items) > total:
                raise TaskDockError("TaskDock returned inconsistent task counts.")
            if not page["has_more"]:
                if len(items) != total:
                    raise TaskDockError("TaskDock refresh ended before all tasks were read.")
                return WorkspaceSnapshot(
                    tuple(items), revision, datetime.now(timezone.utc).isoformat()
                )
            if not rows or len(items) >= total:
                raise TaskDockError("TaskDock returned inconsistent pagination.")
        raise TaskDockError("TaskDock refresh exceeded the page limit.")
