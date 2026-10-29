"""Download pinned public build runtimes and verify publisher release digests."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def fetch():
    cache = ROOT/'.local/runtime-cache'
    cache.mkdir(parents=True, exist_ok=True)
    for item in json.loads((ROOT/'packaging/runtimes-arm64.json').read_text()):
        dest = cache/item['file']
        if not dest.exists():
            temporary = dest.with_suffix('.download')
            print('Downloading ' + item['name'], flush=True)
            urllib.request.urlretrieve(item['url'], temporary)
            temporary.replace(dest)
        with dest.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != item['sha256']:
            raise RuntimeError('Runtime digest mismatch: ' + item['name'])
        print('Verified ' + item['name'], flush=True)
    return cache


if __name__ == '__main__':
    fetch()
