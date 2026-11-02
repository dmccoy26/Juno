"""Do not turn a token-truncated reasoning response into a completed work answer."""
import unittest
from juno.local_model import LocalModel,ModelError


class LocalModelOutputTests(unittest.TestCase):
    def model(self,content,finish='stop'):
        model=LocalModel('http://127.0.0.1:1234/v1')
        def request(path,body):
            self.assertEqual(body['max_tokens'],4096)
            return {'choices':[{'message':{'content':content},'finish_reason':finish}]}
        model.request=request
        return model
    def test_final_answer_excludes_scratch(self):
        self.assertEqual(self.model('<think>Private scratch</think>Review the paper path.').complete([], 'synthetic'),'Review the paper path.')
    def test_truncated_or_unfinished_answer_is_not_saved_as_complete(self):
        for content,finish in [('Partial recommendation','length'),('<think>Still reasoning','stop'),('', 'stop')]:
            with self.assertRaises(ModelError):self.model(content,finish).complete([], 'synthetic')
