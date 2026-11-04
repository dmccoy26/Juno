"""Synthetic network boundary and runtime-integrity regressions; no publisher traffic."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.request import Request

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from helper_http import HTTPSRedirects, loopback_request, open_loopback, validate_https
import fetch_runtimes
import verify_installer


class HelperSecurityTests(unittest.TestCase):
    def test_rejects_nonlocal_destinations_before_network(self):
        for url in ('http://example.com:80', 'http://127.0.0.1.evil:80', 'https://127.0.0.1:80',
                    'http://127.0.0.1', 'http://user:secret@127.0.0.1:80', 'file:///tmp/test',
                    'http://10.3.66.50:8443', 'http://localhost:80'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                open_loopback(Request(url))
        for base, path in [('http://127.0.0.1:80/evil', '/v1/ping'),
                           ('http://127.0.0.1:80', '//evil'), ('http://127.0.0.1:80', '/x#fragment')]:
            with self.assertRaises(ValueError):
                loopback_request(base, path)

    def test_loopback_api_works_and_redirect_never_receives_token(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                received.append(self.path)
                if self.path == '/redirect':
                    self.send_response(302)
                    self.send_header('Location', '/stolen')
                    self.end_headers()
                else:
                    self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            base = 'http://127.0.0.1:' + str(server.server_port)
            with patch.dict('os.environ', {'http_proxy': 'http://127.0.0.1:1', 'no_proxy': ''}):
                self.assertEqual(verify_installer.api(base, 'synthetic', '/ok'), {})
                verify_installer.api(base, 'synthetic', '/redirect', expected=302)
            self.assertEqual(received, ['/ok', '/redirect'])
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_download_transport_and_redirect_require_https(self):
        validate_https('https://github.com/example')
        for url in ('http://github.com/x', 'file:///tmp/x', 'https://user:secret@example.com/x',
                    'https://example.com:8443/x', 'https://example.com/x#fragment'):
            with self.subTest(url=url), self.assertRaises(ValueError): validate_https(url)
        with self.assertRaises(ValueError):
            HTTPSRedirects().redirect_request(Request('https://example.com'), None, 302, '', {}, 'http://example.com/x')

    def test_runtime_integrity_and_bad_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'packaging').mkdir()
            item = dict(name='synthetic', file='runtime.tar.gz', url='https://example.com/runtime',
                        sha256=hashlib.sha256(b'expected').hexdigest())
            config = root/'packaging/runtimes-arm64.json'
            def write(value): config.write_text(json.dumps([value]))
            with patch.object(fetch_runtimes, 'ROOT', root):
                write(item)
                with patch.object(fetch_runtimes, 'open_download', return_value=io.BytesIO(b'changed')):
                    with self.assertRaises(RuntimeError): fetch_runtimes.fetch()
                cache = root/'.local/runtime-cache'
                self.assertEqual(list(cache.iterdir()), [])
                with patch.object(fetch_runtimes, 'open_download', return_value=io.BytesIO(b'expected')):
                    fetch_runtimes.fetch()
                dest = cache/item['file']; self.assertEqual(dest.read_bytes(), b'expected')
                dest.write_bytes(b'corrupt')
                with self.assertRaises(RuntimeError): fetch_runtimes.fetch()
                dest.unlink(); dest.symlink_to(root/'outside')
                with self.assertRaises(ValueError): fetch_runtimes.fetch()
                dest.unlink()
                for updates in ({'file':'../escape'}, {'file':'/tmp/escape'}, {'url':'http://example.com'}, {'sha256':'bad'}):
                    write({**item, **updates})
                    with patch.object(fetch_runtimes, 'open_download') as network:
                        with self.assertRaises(ValueError): fetch_runtimes.fetch()
                        network.assert_not_called()
