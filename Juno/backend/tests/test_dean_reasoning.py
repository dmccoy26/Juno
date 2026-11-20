"""Local triage selects source evidence while the renderer owns factual claims."""
import json,unittest
from juno.dean_reasoning import assess
from juno.local_model import ModelError

class TriageTests(unittest.TestCase):
    def plan(self):
        return {'connection':('http://127.0.0.1:1234/v1','synthetic-model'),'items':[
            {'id':'task:space','title':'Borrowed space for service crew','state':'open'},
            {'id':'task:paper','title':'Printer needs paper','state':'open'}], 'agenda':[],'omitted':4}
    def model(self,answer):
        class Fake:
            def __init__(self,origin):pass
            def complete(self,messages,model):return answer
        return Fake
    def test_selects_novel_project_using_only_ids_and_records_coverage(self):
        result=assess(self.plan(),self.model(json.dumps({'include':[{'id':'e001','section':'progress'}],'clarify':[{'id':'e001','field':'approval'}]})))
        self.assertEqual(result['selected'],{'task:space':'progress'})
        self.assertEqual(result['reviewed'],2);self.assertEqual(result['omitted'],4)
        self.assertEqual(result['questions'][0]['field'],'approval')
    def test_rejects_invented_ids_facts_categories_and_duplicate_selection(self):
        for body in [
            {'include':[{'id':'invented','section':'progress'}]},
            {'include':[{'id':'e001','section':'progress','cost':'$9999'}]},
            {'include':[{'id':'e001','section':'approved'}]},
            {'include':[{'id':'e001','section':'progress'}]*2},
            {'clarify':[{'id':'e001','field':'approval'}]},
            {'include':[],'claim':'The Dean approved everything'},
        ]:
            with self.subTest(body=body):
                result=assess(self.plan(),self.model(json.dumps(body)))
                self.assertEqual(result['state'],'rules_only');self.assertEqual(result['selected'],{})
    def test_model_outage_malformed_output_and_missing_connection_keep_fallback(self):
        class Offline:
            def __init__(self,origin):pass
            def complete(self,*args):raise ModelError('Fixture offline')
        for factory in [Offline,self.model('Not JSON')]:
            self.assertEqual(assess(self.plan(),factory)['state'],'rules_only')
        self.assertEqual(assess(self.plan()|{'connection':None},self.model('{}'))['state'],'rules_only')
