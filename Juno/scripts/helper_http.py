"""Restricted HTTP transports for build and disposable verification helpers."""
import ipaddress
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


def validate_https(url):
    parts = urlsplit(url)
    if (parts.scheme != 'https' or not parts.hostname or parts.username is not None
            or parts.password is not None or parts.fragment or parts.port not in (None, 443)):
        raise ValueError('Runtime downloads require credential-free HTTPS on port 443.')
    return url


class HTTPSRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_https(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def open_download(url):
    validate_https(url)
    return build_opener(ProxyHandler({}), HTTPSRedirects()).open(url, timeout=60)


def open_loopback(request, *, timeout=3):
    parts = urlsplit(request.full_url)
    try:
        local = ipaddress.ip_address(parts.hostname).is_loopback
    except (ValueError, TypeError):
        local = False
    if (parts.scheme != 'http' or not local or not parts.port
            or parts.username is not None or parts.password is not None or parts.fragment):
        raise ValueError('Verification requests require a literal loopback HTTP address and explicit port.')
    return build_opener(ProxyHandler({}), NoRedirects()).open(request, timeout=timeout)


def loopback_request(base, path, **kwargs):
    parts = urlsplit(base)
    if parts.path not in ('', '/') or parts.query or parts.fragment:
        raise ValueError('Verification base must be an origin.')
    if not path.startswith('/') or path.startswith('//') or '#' in path:
        raise ValueError('Verification path must be local to the service.')
    return Request(base.rstrip('/') + path, **kwargs)
