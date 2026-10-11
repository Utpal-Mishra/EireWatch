"""Bounded HTTPS JSON collection; no crawling, shell commands or implicit trust."""
import hashlib
import ipaddress
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from .core import instant, utc

MAX_BYTES=2_000_000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect blocked: review the configured source URL')


def check_url(url, allowed_hosts):
    p=urllib.parse.urlsplit(url)
    if p.scheme!='https' or p.username or p.password or p.fragment or p.port not in (None,443):
        raise ValueError('Only HTTPS port 443 without credentials/fragments is allowed')
    if p.hostname not in allowed_hosts:
        raise ValueError('Source host is not allowlisted')
    addresses=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Non-public destination blocked')
    # Production must ALSO enforce network egress policy; DNS prechecks alone
    # cannot defeat rebinding between resolution and connection.
    return p


def fetch_json(config):
    check_url(config['url'],config['allowed_hosts'])
    request=urllib.request.Request(config['url'],headers={'User-Agent':'EireWatchMonitor/0.1','Accept':'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=15) as response:
        if 'json' not in response.headers.get('Content-Type','').lower():
            raise ValueError('Unexpected content type')
        raw=response.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES: raise ValueError('Response exceeds size limit')
    return json.loads(raw),hashlib.sha256(raw).hexdigest()


def collect(monitor, config, now=None, fetch=fetch_json):
    """One independent source attempt. Later runs retry with capped backoff."""
    now=now or utc(); monitor.register(config)
    if not config['approved_for_ingestion']: return 'disabled'
    previous=monitor.db.execute('SELECT * FROM sources WHERE id=?',(config['id'],)).fetchone()
    delay=min(3600,60*2**min(previous['failures'],6)) if previous['failures'] else 0
    if delay and previous['checked'] and (instant(now)-instant(previous['checked'])).total_seconds()<delay:
        return 'backoff'
    try:
        payload,raw_hash=fetch(config)
        if config['adapter']!='normalized-json-v1': raise ValueError('Unsupported adapter')
        if not isinstance(payload,dict) or payload.get('schema_version')!=1 or not isinstance(payload.get('incidents'),list):
            raise ValueError('Unexpected feed schema')
        monitor.ingest(config['id'],payload['incidents'],now,raw_hash)
        return 'healthy'
    except (ValueError,TypeError,KeyError,OSError,urllib.error.URLError):
        # Do not leak URL credentials, provider response bodies or personal data.
        monitor.failure(config['id'],'Collection or validation failed; inspect the source privately',now)
        return 'unavailable'
