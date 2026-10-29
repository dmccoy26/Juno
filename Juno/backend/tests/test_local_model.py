import unittest
from unittest.mock import patch
from juno.local_model import LocalModel, ModelError


class LocalModelTests(unittest.TestCase):
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
