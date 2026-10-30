"""No proxies, redirects, arbitrary origins, provider writes, or raw provider diagnostics."""
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode,urlsplit
from urllib.request import Request,build_opener,ProxyHandler
from ..taskdock import _NoRedirect

class ReadError(RuntimeError):
    def __init__(self,message,status=502,retry_after=None):
        super().__init__(message);self.status=status;self.retry_after=retry_after

GET_PATHS={
 'https://openidconnect.googleapis.com':r'/v1/userinfo',
 'https://gmail.googleapis.com':r'/gmail/v1/users/me/(?:profile|messages(?:/[A-Za-z0-9_-]+)?)',
 'https://www.googleapis.com':r'/calendar/v3/(?:users/me/calendarList(?:/primary)?|calendars/[^/]+/events)',
 'https://tasks.googleapis.com':r'/tasks/v1/(?:users/@me/lists|lists/[^/]+/tasks)',
 'https://chat.googleapis.com':r'/v1/spaces(?:/[A-Za-z0-9_-]+/messages)?',
 'https://slack.com':r'/api/(?:auth\.test|conversations\.(?:list|info|history|replies))',
 'https://api.smartsheet.com':r'/2\.0/(?:users/me|sheets(?:/[0-9]+)?)',
 'https://graph.microsoft.com':r'/v1\.0/me(?:/calendars(?:/[^/]+/calendarView)?)?',
}


def validate_request(method,url):
    try:
        parts=urlsplit(url);port=parts.port
    except ValueError:raise ReadError('The provider request destination is invalid.',422) from None
    if parts.username or parts.password or parts.fragment or parts.scheme!='https' or port not in (None,443):raise ReadError('The provider request destination is invalid.',422)
    origin=parts.scheme+'://'+parts.netloc
    if method=='GET':
        if origin not in GET_PATHS or not re.fullmatch(GET_PATHS[origin],parts.path):raise ReadError('This request is outside Juno’s read-only provider scope.',422)
    elif method=='POST':
        if not (url=='https://oauth2.googleapis.com/token' or re.fullmatch(r'https://login\.microsoftonline\.com/(?:common|organizations|consumers|[A-Za-z0-9.-]{1,150})/oauth2/v2\.0/token',url)):
            raise ReadError('This request is outside Juno’s token-exchange scope.',422)
    else:raise ReadError('Provider writes are unavailable in Juno.',403)


def request_json(method,url,headers,body=None,timeout=10):
    validate_request(method,url)
    try:
        with build_opener(ProxyHandler({}),_NoRedirect).open(Request(url,data=body,headers=headers,method=method),timeout=timeout) as response:
            raw=response.read(8_000_001)
            if len(raw)>8_000_000:raise ReadError('The provider response exceeded 8 MB. Narrow the selected resources.',413)
            value=json.loads(raw)
    except HTTPError as error:
        code=error.code
        try:retry=max(1,min(86400,int(error.headers.get('Retry-After','60'))))
        except (ValueError,TypeError):retry=60
        error.close()
        if code==401:raise ReadError('Provider authorization expired or was revoked. Reconnect this account.',401) from None
        if code==403:raise ReadError('The provider denied this read. Check the selected resource, read scopes and workplace policy.',403) from None
        if code==404:raise ReadError('A selected provider resource is unavailable. The previous copy has been retained.',404) from None
        if code==429:raise ReadError('The provider is rate limiting this connection. Wait before refreshing again.',429,retry) from None
        raise ReadError('The provider could not complete the read or token exchange. The previous copy has been retained.',502) from None
    except (URLError,TimeoutError,OSError):raise ReadError('The provider is unavailable. The previous copy has been retained.',502) from None
    except (UnicodeError,ValueError):raise ReadError('The provider returned invalid JSON. The previous copy has been retained.',502) from None
    if not isinstance(value,dict):raise ReadError('The provider returned an invalid response.',502)
    return value


class ProviderHTTP:
    def __init__(self,token,transport=None,seconds=90):
        if not isinstance(token,str) or not token or len(token)>16384 or any(c.isspace() or ord(c)<32 or ord(c)==127 for c in token):raise ReadError('Enter or authorize a valid provider credential.',422)
        self.token=token;self.transport=transport;self.deadline=time.monotonic()+seconds;self.calls=0
    def get(self,origin,path,params=None,headers=None):
        url=origin+path+('?' + urlencode(params,doseq=True) if params else '')
        validate_request('GET',url);self.calls+=1
        if self.calls>250 or time.monotonic()>=self.deadline:raise ReadError('The read reached its request/time limit. Narrow the query, date window or resource selection.',413)
        request_headers={'Authorization':'Bearer '+self.token,'Accept':'application/json',**(headers or {})}
        value=self.transport('GET',url,request_headers,None) if self.transport else request_json('GET',url,request_headers,timeout=max(1,min(10,self.deadline-time.monotonic())))
        if not isinstance(value,dict):raise ReadError('The provider returned an invalid response.')
        encoded=json.dumps(value,ensure_ascii=False)
        if len(encoded.encode())>8_000_000:raise ReadError('The provider response exceeded 8 MB. Narrow the selection.',413)
        if len(self.token)>=8 and self.token in encoded:raise ReadError('The provider returned credential-bearing content. The previous copy has been retained.')
        return value
