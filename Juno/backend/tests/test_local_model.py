import unittest
from unittest.mock import patch
from juno.local_model import LocalModel, ModelError


class LocalModelTests(unittest.TestCase):
    def test_qwen_chat_requests_no_reasoning(self):
        response = {'choices': [{'message': {'content': 'Final answer.'}}]}
        client = LocalModel('http://127.0.0.1:1234/v1')
        with patch.object(client, 'request', return_value=response) as request:
            for model, expected in [('juno-qwen3.5-9b-gguf', 'none'), ('synthetic', None)]:
                with self.subTest(model=model):
                    self.assertEqual(client.complete([], model), 'Final answer.')
                    self.assertEqual(request.call_args.args[1].get('reasoning_effort'), expected)

    def test_only_final_answer_is_returned(self):
        response={'choices':[{'message':{'content':'<think>synthetic scratch</think> Final answer.', 'reasoning_content':'other scratch'}}]}
        with patch.object(LocalModel,'request',return_value=response):
            self.assertEqual(LocalModel('http://127.0.0.1:1234/v1').complete([], 'synthetic'), 'Final answer.')

    def test_unfinished_reasoning_is_not_a_reply(self):
        for content in ['<think>unfinished', '', None]:
            with self.subTest(content=content), patch.object(LocalModel,'request',return_value={'choices':[{'message':{'content':content}}]}):
                with self.assertRaises(ModelError): LocalModel('http://127.0.0.1:1234/v1').complete([], 'synthetic')

    def test_embedding_models_are_not_offered_for_chat(self):
        with patch.object(LocalModel,'request',return_value={'data':[{'id':'synthetic-chat'},{'id':'text-embedding-synthetic'}]}):
            self.assertEqual(LocalModel('http://127.0.0.1:1234/v1').models(),['synthetic-chat'])
