import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from juno.taskdock import TaskDockError, TaskDockReader

FIXTURE = json.loads((Path(__file__).parent/'fixtures/taskdock-v1.json').read_text())


def info(workspace=None):
    result = copy.deepcopy(FIXTURE['info'])
    if workspace: result['workspace_id'] = workspace
    return result


def page(ids, *, offset=0, total=None, more=False, revision='r1'):
    return dict(items=[{'id': ident} for ident in ids], offset=offset, limit=500,
                total=len(ids) if total is None else total, has_more=more, snapshot=revision)


class Transport:
    def __init__(self, pages=None):
        self.calls = []; self.pages = pages if pages is not None else [copy.deepcopy(FIXTURE['tasks'])]
        if pages is None: self.pages[0]['limit'] = 500  # fixture uses the dashboard's default 100
        self.discovery = info(); self.fail = None; self.info_count = 0; self.change_final = False
    def __call__(self, url, headers):
        self.calls.append((url, headers))
        if self.fail: raise self.fail
        path = urlsplit(url).path
        if path == '/integrations/juno/v1/info':
            self.info_count += 1
            result = copy.deepcopy(self.discovery)
            if self.change_final and self.info_count % 2 == 0: result['device_id'] = 'different-device'
            return result
        if path == '/integrations/juno/v1/sources': return copy.deepcopy(FIXTURE['sources'])
        value = self.pages.pop(0)
        if isinstance(value, Exception): raise value
        return value


class TaskDockTests(unittest.TestCase):
    def test_delivered_synthetic_fixture_preserves_fields_and_freshness(self):
        transport=Transport()
        result=TaskDockReader('http://127.0.0.1:8100','synthetic-token',transport).fetch()
        self.assertEqual(list(result.items), FIXTURE['tasks']['items'])
        self.assertEqual(list(result.sources), FIXTURE['sources']['items'])
        self.assertNotIn('synthetic-token',repr(result))
        paths=[urlsplit(url).path for url,_ in transport.calls]
        self.assertEqual(paths,['/integrations/juno/v1/info','/integrations/juno/v1/sources','/workspace/tasks','/integrations/juno/v1/info'])
        for url,headers in transport.calls:
            self.assertNotIn('Origin',headers)
            self.assertEqual(headers['Authorization'],'Bearer synthetic-token')
            self.assertNotIn('synthetic-token',url)

    def test_full_collection_pagination_uses_explicit_scope_and_snapshot(self):
        transport=Transport([page([str(i) for i in range(500)],total=501,more=True),page(['last'],offset=500,total=501)])
        result=TaskDockReader('http://localhost:8100','synthetic',transport).fetch()
        self.assertEqual(len(result.items),501)
        calls=[parse_qs(urlsplit(url).query) for url,_ in transport.calls if urlsplit(url).path=='/workspace/tasks']
        self.assertEqual(calls[0],dict(include_completed=['true'],include_archived=['false'],show_subtasks=['true'],parents_only=['false'],limit=['500'],offset=['0']))
        self.assertEqual(calls[1]['expected_snapshot'],['r1'])
        self.assertEqual(calls[1]['offset'],['500'])

    def test_changed_run_restarts_without_mixed_items(self):
        transport=Transport([page([str(i) for i in range(500)],total=501,more=True),TaskDockError('Changed',409),page(['new'],revision='r2')])
        with patch('juno.taskdock.time.sleep'):
            result=TaskDockReader('http://localhost','synthetic',transport).fetch()
        self.assertEqual(result.items,({'id':'new'},))
        self.assertEqual(result.revision,'r2')

    def test_auth_and_scope_failures_do_not_retry(self):
        for code in (401,403,404,422,500):
            transport=Transport();transport.fail=TaskDockError('Synthetic failure',code)
            with self.subTest(code=code), self.assertRaises(TaskDockError):
                TaskDockReader('http://localhost','synthetic',transport).fetch()
            self.assertEqual(len(transport.calls),1)

    def test_invalid_pages_are_never_partial_success(self):
        cases=[page([],total=1),page(['a','a']),page(['a'],total=2,more=True),
               {**page(['a']), 'offset':True},{**page(['a']),'limit':1},
               {**page(['a']), 'items':[{'id':'a','parent_id':'a'}]},
               {**page(['a','b']), 'items':[{'id':'a','parent_id':'b'},{'id':'b','parent_id':'a'}]}]
        for case in cases:
            with self.subTest(case=case),self.assertRaises(TaskDockError):
                TaskDockReader('http://localhost','synthetic',Transport([case])).fetch()

    def test_duplicate_across_pages_and_page_limit(self):
        first=page([str(i) for i in range(500)],total=501,more=True)
        with self.assertRaises(TaskDockError):
            TaskDockReader('http://localhost','synthetic',Transport([first,page(['0'],offset=500,total=501)])).fetch()
        with self.assertRaises(TaskDockError):
            TaskDockReader('http://localhost','synthetic',Transport([first])).fetch(max_pages=1)

    def test_empty_workspace_and_external_parent_are_valid(self):
        self.assertEqual(TaskDockReader('http://localhost','synthetic',Transport([page([])])).fetch().items,())
        data=page(['child']);data['items'][0]['parent_id']='out-of-scope'
        self.assertEqual(TaskDockReader('http://localhost','synthetic',Transport([data])).fetch().items[0]['parent_id'],'out-of-scope')

    def test_identity_change_during_read_never_promotes(self):
        transport=Transport();transport.change_final=True
        with self.assertRaises(TaskDockError):
            TaskDockReader('http://localhost','synthetic',transport).fetch(attempts=1)

    def test_version_and_capabilities_are_required(self):
        for override in ({'api_version':'2'},{'capabilities':{'read_tasks':False}},{'workspace_id':None},{'definitions':{}}):
            transport=Transport();transport.discovery.update(override)
            with self.subTest(override=override),self.assertRaises(TaskDockError):
                TaskDockReader('http://localhost','synthetic',transport).fetch()
            self.assertEqual(len(transport.calls),1)

    def test_missing_freshness_capability_does_not_probe(self):
        transport=Transport([page([])]);transport.discovery['capabilities']['read_source_freshness']=False
        result=TaskDockReader('http://localhost','synthetic',transport).fetch()
        self.assertEqual(result.sources,())
        self.assertNotIn('/integrations/juno/v1/sources',[urlsplit(u).path for u,_ in transport.calls])

    def test_remote_urls_and_empty_or_header_injected_tokens_rejected(self):
        for origin in ['http://example.com','https://example.com','http://127.0.0.1.evil.test','http://localhost:bad','http://localhost:0','https://user:secret@localhost','http://localhost?token=secret','file:///tmp/tasks']:
            with self.subTest(origin=origin),self.assertRaises(ValueError): TaskDockReader(origin,'synthetic')
        for token in ('','secret\r\nX-Header: attack',' space','\x7f'):
            with self.subTest(token=repr(token)),self.assertRaises(ValueError):TaskDockReader('http://localhost',token)

    def test_history_opaque_id_cursor_dedup_and_capability(self):
        transport=Transport([{'items':[{'id':'a'}],'next_cursor':'a'},{'items':[{'id':'b'}],'next_cursor':None}])
        rows=TaskDockReader('http://localhost','synthetic',transport).history('local id/1','updates')
        self.assertEqual([r['id'] for r in rows],['a','b'])
        self.assertIn('/workspace/tasks/local%20id%2F1/timeline',transport.calls[1][0])
        self.assertIn('before_id=a',transport.calls[2][0])
        for pages in ([{'items':[{'id':'a'}],'next_cursor':'a'},{'items':[{'id':'a'}],'next_cursor':None}],
                      [{'items':[],'next_cursor':'a'}]):
            with self.assertRaises(TaskDockError):TaskDockReader('http://localhost','synthetic',Transport(pages)).history('x','activity')
        transport=Transport();transport.discovery['capabilities']['read_activity']=False
        with self.assertRaises(TaskDockError):TaskDockReader('http://localhost','synthetic',transport).history('x','activity')

    def test_history_conflict_restarts_only_history_without_mixed_records(self):
        transport=Transport([{'items':[{'id':'old'}],'next_cursor':'old'},TaskDockError('Changed cursor',409),{'items':[{'id':'new'}],'next_cursor':None}])
        with patch('juno.taskdock.time.sleep'):
            rows=TaskDockReader('http://localhost','synthetic',transport).history('x','updates')
        self.assertEqual(rows,[{'id':'new'}])
        self.assertNotIn('/workspace/tasks?',str(transport.calls))

    def test_real_http_does_not_follow_redirects_or_use_environment_proxy(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread
        seen=[]
        class Destination(BaseHTTPRequestHandler):
            def log_message(self,*_): pass
            def do_GET(self):
                seen.append(self.headers.get('Authorization'))
                self.send_response(200);self.end_headers();self.wfile.write(b'{}')
        destination=ThreadingHTTPServer(('127.0.0.1',0),Destination)
        class Origin(BaseHTTPRequestHandler):
            redirect=True
            def log_message(self,*_): pass
            def do_GET(self):
                if self.redirect:
                    self.send_response(302);self.send_header('Location','http://127.0.0.1:'+str(destination.server_port)+'/redirect');self.end_headers()
                else:
                    self.send_response(200);self.end_headers();self.wfile.write(json.dumps(info()).encode())
        origin=ThreadingHTTPServer(('127.0.0.1',0),Origin)
        threads=[Thread(target=s.serve_forever,daemon=True) for s in (origin,destination)]
        for thread in threads:thread.start()
        try:
            reader=TaskDockReader('http://127.0.0.1:'+str(origin.server_port),'synthetic-header')
            with self.assertRaises(TaskDockError) as failed:reader.discover()
            self.assertEqual(failed.exception.status,302);self.assertEqual(seen,[])
            Origin.redirect=False
            with patch.dict('os.environ',{'http_proxy':'http://127.0.0.1:'+str(destination.server_port),'no_proxy':''}):
                self.assertEqual(reader.discover()['workspace_id'],info()['workspace_id'])
            self.assertEqual(seen,[])
        finally:
            for server in (origin,destination):server.shutdown();server.server_close()
            for thread in threads:thread.join(3)
