"""Bounded local-only model adapter; no tools or cloud fallback."""
import json
import re
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
from urllib.error import URLError, HTTPError
from .taskdock import _NoRedirect


class ModelError(RuntimeError):
    pass


def validate_origin(value):
    p = urlsplit(value)
    if (p.scheme != 'http' or p.hostname not in ('127.0.0.1', 'localhost', '::1')
        or p.username or p.password or p.query or p.fragment or p.path.rstrip('/') != '/v1'):
        raise ValueError('Use a local model address such as http://127.0.0.1:1234/v1. Remote services are not enabled in this preview.')
    try:
        _ = p.port
    except ValueError:
        raise ValueError('Invalid model server port.') from None
    return value.rstrip('/')


class LocalModel:
    def __init__(self, base_url):
        self.base_url = validate_origin(base_url)

    def request(self, path, body=None):
        headers = {'Accept': 'application/json'}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        try:
            request = Request(self.base_url+path, data=data, headers=headers)
            with build_opener(_NoRedirect).open(request, timeout=65) as response:
                raw = response.read(1_000_001)
                if len(raw)>1_000_000: raise ModelError('The model response was too large.')
                return json.loads(raw)
        except (HTTPError, URLError, OSError, ValueError, UnicodeError):
            raise ModelError('Could not reach the local model. Check that its server is running and the selected model is available.') from None

    def models(self):
        value = self.request('/models')
        if not isinstance(value, dict) or not isinstance(value.get('data'), list):
            raise ModelError('The local server returned an invalid model list.')
        return [r['id'] for r in value['data'] if isinstance(r, dict) and isinstance(r.get('id'), str)
                and len(r['id'])<=200 and 'embed' not in r['id'].lower()][:100]

    def complete(self, messages, model):
        value = self.request('/chat/completions', {'model': model, 'messages': messages,
                                                  'temperature': .3, 'max_tokens': 1536, 'stream': False})
        try:
            answer = value['choices'][0]['message']['content']
            if not isinstance(answer, str): raise ValueError()
            # Some local servers combine scratch text with the final answer.
            answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.S).strip()
            if '<think>' in answer or not answer or len(answer)>12000: raise ValueError()
            return answer
        except (TypeError, KeyError, IndexError, ValueError):
            raise ModelError('The model did not return a complete final answer. Try again or select another model.') from None
