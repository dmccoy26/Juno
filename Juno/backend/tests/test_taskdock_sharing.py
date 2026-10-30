"""Synthetic Beta 3.17 controlled-sharing contract checks."""
import copy
import unittest
from urllib.parse import urlsplit,parse_qs
from test_taskdock import Transport,page
from juno.taskdock import TaskDockReader,TaskDockError
from juno.taskdock_planning import validate_task,provided,blockers

class Controlled(Transport):
    def __init__(self,pages=None):
        super().__init__(pages)
        self.discovery['capabilities'].update(controlled_sharing=True,read_planning_details=True)
        self.discovery.update(sharing_version=7,sharing={'controlled':True,'channels':['title','source','updates'],'planning_fields':['room','blockers','dependencies']})
        for value in self.pages:
            value.update(sharing_version=7,sharing=copy.deepcopy(self.discovery['sharing']))
            for row in value['items']:
                row['planning_details']={key:{'state':'unknown','value':None} for key in self.discovery['sharing']['planning_fields']}
    def __call__(self,url,headers):
        value=super().__call__(url,headers)
        if urlsplit(url).path.endswith('/sources'):value['sharing_version']=self.discovery['sharing_version']
        return value

class SharingTests(unittest.TestCase):
    def test_every_page_pins_version_and_preserves_quality(self):
        transport=Controlled([page([str(i) for i in range(500)],total=501,more=True),page(['last'],offset=500,total=501)])
        facts=transport.pages[0]['items'][0]['planning_details']
        facts['room']={'state':'provided','value':'ARTS 121','origin':'reviewed','source_updated_at':'2026-10-30T12:00:00Z'}
        facts['blockers']={'state':'none','value':None}
        result=TaskDockReader('http://localhost','synthetic',transport).fetch()
        self.assertEqual(result.items[0]['planning_details'],facts)
        self.assertEqual(provided(result.items[0],'room'),'ARTS 121')
        self.assertEqual(blockers(result.items[0]),'')
        calls=[parse_qs(urlsplit(url).query) for url,_ in transport.calls if urlsplit(url).path=='/workspace/tasks']
        self.assertEqual([q['expected_sharing_version'] for q in calls],[['7'],['7']])
        self.assertEqual(calls[1]['expected_snapshot'],['r1'])

    def test_changed_version_or_selection_discards_collection(self):
        for field,value in [('sharing_version',8),('sharing',{'controlled':True,'channels':[],'planning_fields':[]})]:
            transport=Controlled([page(['task'])]);transport.pages[0][field]=value
            with self.assertRaises(TaskDockError) as error:TaskDockReader('http://localhost','synthetic',transport).fetch(attempts=1)
            self.assertEqual(error.exception.status,409)

    def test_legacy_does_not_gain_new_fields(self):
        transport=Transport([page(['task'])]);transport.pages[0]['items'][0]['planning_details']={'room':{'state':'provided','value':'private'}}
        result=TaskDockReader('http://localhost','synthetic',transport).fetch()
        self.assertNotIn('planning_details',result.items[0])

    def test_invalid_facts_and_unshared_comments_rejected(self):
        transport=Controlled([page(['task'])]);row=transport.pages[0]['items'][0]
        row['planning_details']['room']={'state':'none','value':'ARTS 121'}
        with self.assertRaises(ValueError):validate_task(row,transport.discovery)
        row['planning_details']['room']={'state':'unknown','value':None}
        row['source_updates']={'complete':False,'items':[{'body':'sample'}],'scope':'bounded sample'}
        self.assertFalse(validate_task(row,transport.discovery)['source_updates']['complete'])
        transport.discovery['sharing']['channels'].remove('updates')
        with self.assertRaises(ValueError):validate_task(row,transport.discovery)

    def test_readiness_does_not_imply_staffing_is_confirmed(self):
        transport=Controlled([page(['task'])]);row=transport.pages[0]['items'][0]
        row['planning_readiness']={'state':'request_details_complete','missing':[],'staffing_review_required':False}
        with self.assertRaises(ValueError):validate_task(row,transport.discovery)

    def test_history_version_checked_before_accepting_rows(self):
        transport=Controlled([])
        transport.discovery['capabilities']['read_updates']=True
        def send(url,headers):
            if '/timeline?' in url:
                self.assertEqual(parse_qs(urlsplit(url).query)['expected_sharing_version'],['7'])
                return {'items':[{'id':'sample','body':'unaccepted'}],'next_cursor':None,'sharing_version':8}
            return transport(url,headers)
        from unittest.mock import patch
        with patch('juno.taskdock.time.sleep'),self.assertRaises(TaskDockError) as error:
            TaskDockReader('http://localhost','synthetic',send).history('task','updates')
        self.assertEqual(error.exception.status,409)
