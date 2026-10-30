"""Provider dispatch without configurable remote origins."""
from .http import ProviderHTTP,ReadError
import json
from . import google,other

PROVIDERS=('gmail','google_calendar','google_tasks','google_chat','slack','smartsheet','outlook_calendar')
GOOGLE=('gmail','google_calendar','google_tasks','google_chat')


def discover(provider,token,transport=None):
    if provider not in PROVIDERS:raise ReadError('Unsupported provider.',422)
    http=ProviderHTTP(token,transport)
    if provider in GOOGLE:account,resources=google.discover(http,provider);manual=False
    elif provider=='slack':account,resources,manual=other.discover_slack(http)
    elif provider=='smartsheet':account,resources=other.discover_smart(http);manual=False
    else:account,resources=other.discover_microsoft(http);manual=False
    return {'provider':provider,'account':account,'resources':resources,'manual_selection_required':manual,
        'notice':'Discovery reads account/resource labels only. Review the account and choose explicit resources before saving content. No TaskDock credentials were imported.'}


def read(provider,token,config,transport=None):
    if provider not in PROVIDERS:raise ReadError('Unsupported provider.',422)
    if len(token)>=8 and token in json.dumps(config):raise ReadError('A credential was entered in a resource/query field. Keep it only in the credential field.',422)
    http=ProviderHTTP(token,transport)
    if provider in GOOGLE:
        account=google.profile(http,provider)
        handler={'gmail':google.read_gmail,'google_calendar':google.read_calendar,'google_tasks':google.read_tasks,'google_chat':google.read_chat}[provider]
    elif provider=='slack':account=other.slack_profile(http);handler=other.read_slack
    elif provider=='smartsheet':account=other.smart_profile(http);handler=other.read_smart
    else:
        value=http.get('https://graph.microsoft.com','/v1.0/me',{'$select':'id,displayName,mail,userPrincipalName'})
        from .common import identity,required,text
        account={'id':identity(provider,required(value.get('id'))),'label':text(value.get('mail') or value.get('userPrincipalName') or value.get('displayName') or 'Microsoft account',300)};handler=other.read_microsoft
    if config.get('reviewed_account')!=account['id']:return {'review_required':True,'account':account}
    rows,details=handler(http,config,account)
    return {'review_required':False,'account':account,'items':rows,'details':{**details,'provider':provider,'route':'direct',
        'overlap_notice':'Direct records may overlap TaskDock task imports or manual calendar copies. Do not count matching evidence as additional tasks or commitments. TaskDock remains the task system of record.'}}
