"""Download pinned public build runtimes and verify publisher release digests."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import os
import secrets
import stat
from contextlib import contextmanager
from helper_http import open_download, validate_https

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def cache_directory(*, create=True):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptors = [os.open(ROOT, flags)]
    try:
        for name in ('.local', 'runtime-cache'):
            parent = descriptors[-1]
            if create:
                try:
                    os.mkdir(name, mode=0o700, dir_fd=parent)
                except FileExistsError:
                    pass
            try:
                descriptors.append(os.open(name, flags, dir_fd=parent))
            except OSError as error:
                raise ValueError('Runtime cache path must contain real directories.') from error
        yield descriptors[-1]
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def verify_entry(directory, filename, item):
    try:
        descriptor = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise ValueError('Cannot safely open runtime cache entry.') from error
    with os.fdopen(descriptor, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('Runtime cache entries must be regular files.')
        verify_digest(stream, item)
    return True


def verify_digest(stream, item):
    if hashlib.file_digest(stream, 'sha256').hexdigest() != item['sha256']:
        raise RuntimeError('Runtime digest mismatch: ' + item['name'])


def verify_directory(directory):
    with cache_directory(create=False) as current:
        if not os.path.samestat(os.fstat(directory), os.fstat(current)):
            raise ValueError('Runtime cache directory changed during download.')


def download(directory, filename, item):
    temporary = 'runtime-' + secrets.token_hex(16) + '.download'
    descriptor = os.open(temporary, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         mode=0o600, dir_fd=directory)
    try:
        with os.fdopen(descriptor, 'w+b') as stream:
            with open_download(item['url']) as response:
                shutil.copyfileobj(response, stream)
            stream.seek(0)
            verify_digest(stream, item)
            verify_directory(directory)
            try:
                os.link(temporary, filename, src_dir_fd=directory, dst_dir_fd=directory,
                        follow_symlinks=False)
            except FileExistsError:
                # A concurrent download may already have published this entry.
                pass
    finally:
        os.unlink(temporary, dir_fd=directory)


def fetch():
    items = json.loads((ROOT/'packaging/runtimes-arm64.json').read_text())
    with cache_directory() as directory:
        for item in items:
            filename = item['file']
            if not isinstance(filename, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]*', filename):
                raise ValueError('Runtime filename must be a plain filename.')
            validate_https(item['url'])
            if not re.fullmatch(r'[0-9a-f]{64}', item['sha256']):
                raise ValueError('Runtime SHA-256 must be a pinned lowercase digest.')
            if not verify_entry(directory, filename, item):
                download(directory, filename, item)
                if not verify_entry(directory, filename, item):
                    raise RuntimeError('Runtime cache entry disappeared after publication.')
            print('Verified ' + item['name'], flush=True)
        verify_directory(directory)
    return ROOT/'.local/runtime-cache'


if __name__ == '__main__':
    fetch()
