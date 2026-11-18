from datetime import datetime,timezone,timedelta
import json,uuid,copy
from test_memory_api import MemoryTests
from juno.purchasing_export import read


def export():
    stamp=(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat()
    report='a'*64
    return {'schema_version':1,'helper_instance_id':str(uuid.uuid4()),'export_id':str(uuid.uuid4()),'created_at':stamp,
        'observation_window':{'state':'observed','start':'2026-10-01','end':'2026-10-31'},
        'completeness':{'expenses':'complete','reports':'partial','orders':'not_searched','runs':'current_session'},
        'expenses':[{'id':'credit','report_id':report,'merchant':'Fictional supplier','date':'2026-10-23','amount':'-18.14','currency':'USD','status':'already_attached',
            'receipt_search_outcome':'already_attached','account_coding_status':'not_searched','attachment':'PRIVATE_PATH'}],
        'reports':[{'id':report,'title':'Fictional October','source_status':'Pending External Validation','observed_at':stamp,
            'reporting_period':{'state':'observed','start':'2026-10-01','end':'2026-10-31'},'currency':'USD','total':'-18.14',
            'allocation_state':'verified','org_totals':[{'org':'30405','amount':'-18.14'}],'submission_time_state':'not_searched','report_url':'PRIVATE_URL'}],
        'orders':[],'runs':[{'id':str(uuid.uuid4()),'operation':'scan','started_at':stamp,'ended_at':stamp,'outcome':'success',
            'coverage':{'concur':'complete','pcard':'complete','gmail':'not_searched','orders':'not_searched','PRIVATE_EMAIL':'complete'},
            'sign_in_state':'completed_manually','log':'PRIVATE_LOG'}]}


class PurchasingExportTests(MemoryTests):
    def body(self,data,expected=None):
        result={'content':json.dumps(data),'observed_at':datetime.now(timezone.utc).isoformat()}
        if expected:result['expected_id']=expected
        return result

    def test_envelope_preview_import_exact_status_credit_privacy_and_replay(self):
        data=export();body=self.body(data)
        preview=self.client.post('/v1/purchasing/preview',json=body)
        self.assertEqual(preview.status_code,200,preview.text)
        self.assertEqual(self.client.get('/v1/purchasing').json()['items'],[])
        saved=self.client.post('/v1/purchasing/import',json=body)
        self.assertEqual(saved.status_code,200,saved.text)
        current=saved.json();self.assertEqual(current['items'][0]['amount'],'-18.14')
        self.assertEqual(current['reports'][0]['source_status'],'Pending External Validation')
        self.assertEqual(current['reports'][0]['org_totals'],[{'org':'30405','amount':'-18.14'}])
        self.assertEqual(current['helper_export']['completeness']['orders'],'not_searched')
        self.assertNotIn('PRIVATE_',saved.text)
        replay=self.client.post('/v1/purchasing/import',json=body)
        self.assertEqual(replay.status_code,200,replay.text);self.assertEqual(replay.json()['id'],current['id'])
        changed=copy.deepcopy(data);changed['expenses'][0]['merchant']='Changed'
        self.assertEqual(self.client.post('/v1/purchasing/import',json=self.body(changed,current['id'])).status_code,409)
        self.assertEqual(self.client.get('/v1/purchasing',headers={'Authorization':'Bearer '+self.other_token}).json()['items'],[])

    def test_failed_scan_diagnostics_retain_previous_rows_and_observation(self):
        data=export();saved=self.client.post('/v1/purchasing/import',json=self.body(data)).json()
        failed=copy.deepcopy(data);failed['export_id']=str(uuid.uuid4());failed['expenses']=None
        failed['completeness']['expenses']='unknown';failed['runs'][0]['outcome']='failure';failed['runs'][0]['coverage']['concur']='failed'
        failed['runs'][0]['sign_in_state']='manual_sign_in_needed'
        preview=self.client.post('/v1/purchasing/preview',json=self.body(failed))
        self.assertEqual(preview.status_code,200,preview.text);self.assertTrue(preview.json()['preserves_expenses'])
        result=self.client.post('/v1/purchasing/import',json=self.body(failed,saved['id']))
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['items'],saved['items']);self.assertEqual(result.json()['observed_at'],saved['observed_at'])
        self.assertEqual(result.json()['helper_export']['runs'][0]['outcome'],'failure')
        self.assertIn('earlier expense',result.json()['notice'])

    def test_bad_version_time_run_identity_and_inconsistent_completion_rejected(self):
        data=export()
        invalid=[]
        v=copy.deepcopy(data);v['schema_version']=True;invalid.append(v)
        v=copy.deepcopy(data);v['runs'][0]['ended_at']='2099-01-01T00:00:00Z';invalid.append(v)
        v=copy.deepcopy(data);v['helper_instance_id']='missing';invalid.append(v)
        v=copy.deepcopy(data);v['expenses']=None;invalid.append(v)
        v=copy.deepcopy(data);v['expenses'][0]['report_id']='wrong';invalid.append(v)
        v=copy.deepcopy(data);v['expenses'][0]['report_id']=[];invalid.append(v)
        v=copy.deepcopy(data);v['completeness']['reports']=[];invalid.append(v)
        for item in invalid:
            with self.subTest(item=item['export_id']):
                response=self.client.post('/v1/purchasing/import',json=self.body(item));self.assertEqual(response.status_code,422,response.text)
        self.assertEqual(self.client.get('/v1/purchasing').json()['items'],[])

    def test_new_export_needs_current_snapshot_and_older_report_is_rejected(self):
        data=export();saved=self.client.post('/v1/purchasing/import',json=self.body(data)).json()
        new=copy.deepcopy(data);new['export_id']=str(uuid.uuid4())
        self.assertEqual(self.client.post('/v1/purchasing/import',json=self.body(new)).status_code,409)
        new['reports'][0]['observed_at']='2026-01-01T00:00:00Z'
        self.assertEqual(self.client.post('/v1/purchasing/import',json=self.body(new,saved['id'])).status_code,409)

    def test_report_status_only_does_not_clear_expense_scan(self):
        data=export();saved=self.client.post('/v1/purchasing/import',json=self.body(data)).json()
        report=copy.deepcopy(data);report['export_id']=str(uuid.uuid4());report['expenses']=None
        report['completeness']['expenses']='unknown';report['runs'][0]['operation']='read_report_status'
        report['runs'][0]['coverage']['pcard']='not_searched'
        result=self.client.post('/v1/purchasing/import',json=self.body(report,saved['id']))
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['items'],saved['items'])
        self.assertEqual(result.json()['observed_at'],saved['observed_at'])
        self.assertEqual(result.json()['helper_export']['runs'][0]['operation'],'read_report_status')
