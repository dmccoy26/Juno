"""Fixed-path local TaskDock v2 adapter. Tokens exist for one native request only."""
from urllib.parse import urlsplit,quote
import httpx
from .routine_delivery import Lookup,DeliveryConflict


WriteConflict=DeliveryConflict


def origin(value):
    parsed=urlsplit(value)
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:
        raise ValueError('Use the local TaskDock API address on this work Mac.')
    if not parsed.port:raise ValueError('Include TaskDock’s local API port.')
    return value.rstrip('/')


class Writer:
    def __init__(self,base_url,token,connection=None,transport=None):
        self.base=origin(base_url)
        if not token.startswith('tdjw1_'):raise PermissionError('Use a separate TaskDock managed-write credential.')
        self.client=httpx.Client(base_url=self.base,headers={'Authorization':'Bearer '+token},timeout=12,trust_env=False,follow_redirects=False,transport=transport)
        self.connection=connection;self.payload=None;self.known_task=None;self.pending={}
        try:
            self.info=self.request('GET','/info')
            if self.info.get('api_version')!='2' or any(self.info.get('capabilities',{}).get(k) is not True for k in ('create_managed_tasks','read_managed_tasks','lookup_operations','reviewed_routines','durable_occurrence_uniqueness')):
                raise ValueError('Install TaskDock with reviewed recurring-task support first.')
            for key in ('instance_id','workspace_id','column_id','grant_id','owner_id','column_name'):
                if not isinstance(self.info.get(key),str) or not 0<len(self.info[key])<=500:raise ValueError('TaskDock returned incomplete write scope.')
            if connection and any(self.info[k]!=connection[k] for k in ('instance_id','workspace_id','column_id','grant_id','owner_id')):
                raise PermissionError('TaskDock’s approved write scope changed. Review the connection again.')
        except Exception:
            self.client.close();raise

    def close(self):self.client.close()

    def request(self,method,path,body=None):
        try:
            with self.client.stream(method,'/integrations/juno/v2'+path,json=body) as response:
                if response.status_code in (401,403):raise PermissionError('TaskDock write access was denied or revoked.')
                if response.status_code==409:raise WriteConflict('TaskDock requires a fresh scope or routine review.')
                response.raise_for_status()
                data=b''
                for chunk in response.iter_bytes():
                    data+=chunk
                    if len(data)>2_000_000:raise ValueError('TaskDock response exceeded the read limit.')
            import json
            result=json.loads(data)
            if not isinstance(result,dict):raise ValueError('TaskDock response was not structured.')
            return result
        except (httpx.HTTPError,ValueError) as error:
            raise RuntimeError('TaskDock managed-task request did not complete. Retained operations will be reconciled before retry.') from None

    def remote_payload(self,scope,operation,payload):
        if any(scope[k]!=self.info[k] for k in ('instance_id','workspace_id','column_id')):raise PermissionError('Occurrence target differs from the approved write scope.')
        return {'instance_id':scope['instance_id'],'workspace_id':scope['workspace_id'],'column_id':scope['column_id'],
            'operation_id':operation,'routine_id':payload['routine_id'],'rule_revision':str(payload['rule_revision']),
            'occurrence_key':payload['occurrence_key'],'occurrence_date':payload['occurrence_date'],
            'due_date':payload['due_date'],'title':payload['title'],'description':payload['description'],
            'assignee':None,'room':None,'rule':payload['rule']}

    def checked(self,remote,scope,operation,routine,period):
        if remote.get('state')!='applied':return None
        fields=remote.get('saved_fields',{})
        if (remote.get('owner_id')!=self.info['owner_id'] or remote.get('column_id')!=scope['column_id']
            or fields.get('instance_id')!=scope['instance_id'] or fields.get('workspace_id')!=scope['workspace_id']
            or fields.get('routine_id')!=routine or fields.get('occurrence_key')!=period):
            raise PermissionError('TaskDock receipt identity did not match the approved occurrence.')
        if self.payload:
            expected=self.remote_payload(scope,operation,self.payload);expected.pop('operation_id')
            if fields!=expected:raise WriteConflict('TaskDock retained a different occurrence payload; review instead of overwriting it.')
        return Lookup('found',{'scope':scope,'operation_id':operation,'routine_id':routine,'occurrence_key':period,
            'task_id':remote.get('task_id'),'completed':remote.get('completed',False),'deleted':remote.get('deleted',False)})

    def lookup(self,scope,operation,routine,period):
        if self.known_task:
            remote=self.request('GET','/tasks/'+quote(self.known_task,safe=''))
            return self.checked(remote,scope,operation,routine,period) or Lookup('pending')
        remote=self.request('GET','/operations/'+quote(operation,safe=''))
        found=self.checked(remote,scope,operation,routine,period)
        if found:return found
        from urllib.parse import urlencode
        occurrence=self.request('GET','/occurrences?'+urlencode({'routine_id':routine,'occurrence_key':period}))
        found=self.checked(occurrence,scope,operation,routine,period)
        if found:return found
        if remote.get('state')=='pending':
            if remote.get('approved') is True:
                self.pending[operation]=remote['preview_id'];return Lookup('retryable')
            return Lookup('pending')
        # This is not a declaration of remote failure. Both lookups preceded an
        # unchanged idempotent operation retry under TaskDock's durable uniqueness.
        return Lookup('retryable')

    def create(self,scope,operation,payload):
        proposal=self.remote_payload(scope,operation,payload)
        preview_id=self.pending.get(operation)
        if not preview_id:
            result=self.request('POST','/previews',proposal)
            if result.get('proposed_task')!=proposal:raise WriteConflict('TaskDock preview changed the proposed task.')
            if result.get('approval_required') is not False:raise WriteConflict('This routine needs a new owner approval in TaskDock.')
            preview_id=result['preview_id']
        remote=self.request('POST','/tasks',{'preview_id':preview_id})
        return self.checked(remote,scope,operation,payload['routine_id'],payload['occurrence_key']) or Lookup('pending')
