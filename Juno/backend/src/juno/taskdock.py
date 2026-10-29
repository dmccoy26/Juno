"""Scoped local TaskDock API v1 client. Credentials are supplied, never discovered."""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, quote
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class TaskDockError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_origin(base_url):
    try:
        parsed = urlsplit(base_url)
        valid = (parsed.scheme in {'http', 'https'} and
                 parsed.hostname in {'127.0.0.1', 'localhost', '::1'} and
                 not parsed.username and not parsed.password and not parsed.query and
                 not parsed.fragment and parsed.path in {'', '/'} and
                 (parsed.port is None or 1 <= parsed.port <= 65535))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Use the local TaskDock API address on this Mac, without credentials or a path.')
    return base_url.rstrip('/')


def _get(url: str, headers: dict[str, str]) -> dict:
    try:
        # Ignore proxy environment settings: credentials must stay on this Mac.
        with build_opener(ProxyHandler({}), _NoRedirect).open(
            Request(url, headers=headers, method='GET'), timeout=10
        ) as response:
            raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise TaskDockError('TaskDock response exceeded the size limit.')
            result = json.loads(raw)
    except HTTPError as error:
        code = error.code
        error.close()
        messages = {401: 'TaskDock access expired or was revoked. Pair again with a dedicated Juno token.',
                    403: 'TaskDock denied this read-only scope. Check the integration build.',
                    404: 'TaskDock integration or record was not found. Check the installed build.',
                    409: 'TaskDock changed during the read. Refresh again.',
                    422: 'TaskDock rejected connector parameters. Check the API contract.'}
        raise TaskDockError(messages.get(code, f'TaskDock returned HTTP {code}.'), code) from None
    except (URLError, TimeoutError, OSError):
        raise TaskDockError('TaskDock is unavailable. The previous snapshot has been kept.') from None
    except (ValueError, UnicodeError):
        raise TaskDockError('TaskDock returned invalid JSON.') from None
    if not isinstance(result, dict):
        raise TaskDockError('TaskDock returned an invalid response.')
    return result


@dataclass(frozen=True)
class WorkspaceSnapshot:
    items: tuple[dict, ...]
    revision: str
    fetched_at: str
    info: dict
    sources: tuple[dict, ...]


class TaskDockReader:
    def __init__(self, base_url: str, token: str,
                 transport: Callable[[str, dict[str, str]], dict] = _get):
        self.base_url = validate_origin(base_url)
        if not token or len(token) > 4096 or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in token):
            raise ValueError('Enter the dedicated Juno token from TaskDock Connections.')
        self._headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}'}
        self._transport = transport

    def get(self, path, params=None):
        return self._transport(self.base_url + path + ('?' + urlencode(params) if params else ''), dict(self._headers))

    def discover(self):
        info = self.get('/integrations/juno/v1/info')
        if (info.get('api_version') != '1' or not isinstance(info.get('capabilities'), dict)
                or info['capabilities'].get('read_tasks') is not True
                or any(not isinstance(info.get(k), str) or not info[k] or len(info[k]) > 200 for k in ('workspace_id', 'device_id'))
                or not isinstance(info.get('definitions'), dict)
                or any(not isinstance(info['definitions'].get(k), list) for k in ('statuses', 'categories', 'custom_fields', 'priorities'))):
            raise TaskDockError('TaskDock does not advertise a supported read-only API v1 workspace.')
        # Fixed supported paths, never follow arbitrary discovery-supplied URLs.
        return {k: info[k] for k in ('api_version', 'workspace_id', 'device_id', 'capabilities', 'definitions')} | {'taskdock': info.get('taskdock', {})}

    def fetch(self, max_pages=100, attempts=3):
        if max_pages < 1 or not 1 <= attempts <= 3:
            raise ValueError('Invalid refresh limits.')
        for attempt in range(attempts):
            try:
                return self._fetch(max_pages)
            except TaskDockError as error:
                if error.status != 409 or attempt + 1 == attempts:
                    raise
                time.sleep(0.1 * (attempt + 1))

    def _fetch(self, max_pages):
        info = self.discover()
        sources = []
        if info['capabilities'].get('read_source_freshness') is True:
            sources = self.get('/integrations/juno/v1/sources').get('items')
            if not isinstance(sources, list) or any(not isinstance(s, dict) or not isinstance(s.get('id'), str) for s in sources):
                raise TaskDockError('TaskDock source freshness response is invalid.')
            sources = [{k: s.get(k) for k in ('id', 'mode', 'health', 'last_attempt_at', 'last_success_at')} for s in sources]
        items, ids = [], set()
        revision = total = None
        offset = 0
        for _ in range(max_pages):
            query = dict(include_completed='true', include_archived='false', show_subtasks='true',
                         parents_only='false', limit=500, offset=offset)
            if revision is not None:
                query['expected_snapshot'] = revision
            page = self.get('/workspace/tasks', query)
            rows, current, count = page.get('items'), page.get('snapshot'), page.get('total')
            if (not isinstance(rows, list) or len(rows) > 500 or
                not isinstance(current, str) or not current or type(count) is not int or count < 0 or
                type(page.get('offset')) is not int or page['offset'] != offset or
                type(page.get('limit')) is not int or page['limit'] != 500 or
                type(page.get('has_more')) is not bool):
                raise TaskDockError('TaskDock workspace pagination is invalid.')
            if revision is not None and (revision != current or total != count):
                raise TaskDockError('TaskDock changed during refresh.', 409)
            revision, total = current, count
            for row in rows:
                if (not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'] or
                    row['id'] in ids or row.get('parent_id') == row['id'] or
                    row.get('parent_id') is not None and not isinstance(row['parent_id'], str)):
                    raise TaskDockError('TaskDock returned invalid or duplicate task identities.')
                ids.add(row['id']); items.append(row)
            if len(items) > total:
                raise TaskDockError('TaskDock returned inconsistent task counts.')
            if not page['has_more']:
                if len(items) != total:
                    raise TaskDockError('TaskDock refresh ended before all tasks were read.')
                parents = {r['id']: r.get('parent_id') for r in items}
                done = set()
                for identity in parents:
                    trail = set(); node = identity
                    while node in parents and node not in done:
                        if node in trail: raise TaskDockError('TaskDock returned a cyclic task hierarchy.')
                        trail.add(node); node = parents[node]
                    done.update(trail)
                final = self.discover()
                if any(final[k] != info[k] for k in ('workspace_id', 'device_id', 'definitions', 'capabilities')):
                    raise TaskDockError('TaskDock workspace or definitions changed during refresh.', 409)
                return WorkspaceSnapshot(tuple(items), revision, datetime.now(timezone.utc).isoformat(), info, tuple(sources))
            if not rows or len(items) >= total or len(rows) != page['limit']:
                raise TaskDockError('TaskDock returned inconsistent pagination.')
            offset += page['limit']
        raise TaskDockError('TaskDock refresh exceeded the page limit.')

    def history(self, task_id, kind, max_pages=100):
        for attempt in range(3):
            try:
                return self._history(task_id, kind, max_pages)
            except TaskDockError as error:
                if error.status != 409 or attempt == 2: raise
                time.sleep(0.1 * (attempt + 1))

    def _history(self, task_id, kind, max_pages):
        if kind not in {'updates', 'activity'} or not task_id or max_pages < 1:
            raise ValueError('Invalid history request.')
        info = self.discover()
        if info['capabilities'].get('read_' + kind) is not True:
            raise TaskDockError('TaskDock does not support this history scope.')
        items, ids, cursors = [], set(), set()
        cursor = None
        for _ in range(max_pages):
            params = {'kind': kind, 'limit': 100}
            if cursor is not None: params['before_id'] = cursor
            page = self.get('/workspace/tasks/' + quote(task_id, safe='') + '/timeline', params)
            rows = page.get('items'); cursor = page.get('next_cursor')
            if not isinstance(rows, list) or len(rows) > 100 or cursor is not None and (not isinstance(cursor, (str, int)) or isinstance(cursor, bool)):
                raise TaskDockError('TaskDock returned invalid history pagination.')
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get('id'), (str, int)) or isinstance(row['id'], bool) or str(row['id']) in ids:
                    raise TaskDockError('TaskDock returned duplicate or invalid history.')
                ids.add(str(row['id'])); items.append(row)
            if cursor is None:
                final = self.discover()
                if any(final[k] != info[k] for k in ('workspace_id', 'device_id')):
                    raise TaskDockError('TaskDock identity changed during the history read.')
                return items
            if not rows or str(cursor) in cursors: raise TaskDockError('TaskDock history did not advance.')
            cursors.add(str(cursor))
        raise TaskDockError('TaskDock history exceeded the page limit.')
