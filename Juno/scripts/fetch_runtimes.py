"""Download pinned public build runtimes and verify publisher release digests."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from helper_http import open_download, validate_https

ROOT = Path(__file__).resolve().parents[1]


def fetch():
    cache = ROOT/'.local/runtime-cache'
    cache.mkdir(parents=True, exist_ok=True)
    for item in json.loads((ROOT/'packaging/runtimes-arm64.json').read_text()):
        filename = item['file']
        if not isinstance(filename, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]*', filename):
            raise ValueError('Runtime filename must be a plain filename.')
        validate_https(item['url'])
        if not re.fullmatch(r'[0-9a-f]{64}', item['sha256']):
            raise ValueError('Runtime SHA-256 must be a pinned lowercase digest.')
        dest = cache/filename
        if dest.is_symlink():
            raise ValueError('Runtime cache entries cannot be symlinks.')
        if not dest.exists():
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=cache, prefix='runtime-', suffix='.download', delete=False) as stream:
                    temporary = Path(stream.name)
                    with open_download(item['url']) as response:
                        shutil.copyfileobj(response, stream)
                with temporary.open('rb') as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                if digest != item['sha256']:
                    raise RuntimeError('Runtime digest mismatch: ' + item['name'])
                temporary.replace(dest)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        with dest.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != item['sha256']:
            raise RuntimeError('Runtime digest mismatch: ' + item['name'])
        print('Verified ' + item['name'], flush=True)
    return cache


if __name__ == '__main__':
    fetch()
