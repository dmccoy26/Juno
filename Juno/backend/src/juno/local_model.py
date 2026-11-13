"""Bounded local-only model adapter; no tools or cloud fallback."""
import json
import re
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener
from urllib.error import URLError, HTTPError
from .taskdock import _NoRedirect


class ModelError(RuntimeError):
    pass


class ModelContextError(ModelError):
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

    def request(self, path, body=None, *, origin=None):
        headers = {'Accept': 'application/json'}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        try:
            request = Request((origin or self.base_url)+path, data=data, headers=headers)
            with build_opener(ProxyHandler({}), _NoRedirect).open(request, timeout=65) as response:
                raw = response.read(1_000_001)
                if len(raw)>1_000_000: raise ModelError('The model response was too large.')
                return json.loads(raw)
        except HTTPError as error:
            if error.code in (400, 413, 422):
                try:
                    detail = json.loads(error.read(8192)).get('error')
                except (ValueError, OSError, AttributeError):
                    detail = None
                if isinstance(detail, dict) and (
                    detail.get('type') == 'exceed_context_size_error'
                    or detail.get('code') == 'context_length_exceeded'
                    or 'exceeds the available context size' in str(detail.get('message', '')).lower()
                ):
                    raise ModelContextError(
                        'This message exceeds the loaded model’s context window. Shorten it or load the model with a larger context in LM Studio.'
                    ) from None
            raise ModelError('LM Studio rejected the request. Check that the selected model is loaded.') from None
        except (URLError, OSError, ValueError, UnicodeError):
            raise ModelError('Could not reach the local model. Check that its server is running and the selected model is available.') from None

    def models(self):
        value = self.request('/models')
        if not isinstance(value, dict) or not isinstance(value.get('data'), list):
            raise ModelError('The local server returned an invalid model list.')
        return [r['id'] for r in value['data'] if isinstance(r, dict) and isinstance(r.get('id'), str)
                and len(r['id'])<=200 and 'embed' not in r['id'].lower()][:100]

    def compose_email(self, messages, model):
        if 'qwen3' not in model.casefold():
            return self.complete(messages, model)
        try:
            result = self.request('/api/v1/chat', {
                'model': model, 'system_prompt': messages[0]['content'], 'input': messages[1]['content'],
                'reasoning': 'off', 'store': False, 'max_output_tokens': 2048,
            }, origin=self.base_url.removesuffix('/v1'))
        except ModelError:
            return self.complete(messages, model)
        output = result.get('output') if isinstance(result, dict) else None
        if not isinstance(output, list):
            raise ModelError('LM Studio did not return a complete email.')
        return '\n'.join(item['content'] for item in output
                         if isinstance(item, dict) and item.get('type') == 'message'
                         and isinstance(item.get('content'), str)).strip()

    def complete(self, messages, model):
        body = {'model': model, 'messages': messages,
                'temperature': .3, 'max_tokens': 4096, 'stream': False}
        if 'qwen3' in model.casefold():
            body['reasoning_effort'] = 'none'
        value = self.request('/chat/completions', body)
        try:
            if value['choices'][0].get('finish_reason') == 'length':
                raise ValueError('Incomplete final answer')
            answer = value['choices'][0]['message']['content']
            if not isinstance(answer, str): raise ValueError()
            # Some local servers combine scratch text with the final answer.
            answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.S).strip()
            if '<think>' in answer or not answer or len(answer)>12000: raise ValueError()
            return answer
        except (TypeError, KeyError, IndexError, ValueError):
            raise ModelError('The model did not return a complete final answer. Try again or select another model.') from None
