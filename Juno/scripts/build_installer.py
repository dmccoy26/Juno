"""Build a self-contained internal Apple Silicon preview without user data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tarfile

from fetch_runtimes import fetch

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0-preview.2'


def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def clean_env():
    result = {key: value for key, value in os.environ.items()
              if key in ('HOME', 'USER', 'LOGNAME', 'TMPDIR', 'LANG', 'LC_ALL')}
    result.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin', PYTHONDONTWRITEBYTECODE='1',
                  PYTHONNOUSERSITE='1', PIP_CONFIG_FILE='/dev/null')
    return result


def copy_source(source, destination):
    shutil.copytree(source, destination, symlinks=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))


def build(output):
    if os.uname().machine != 'arm64' or sys.platform != 'darwin':
        raise RuntimeError('Build on an Apple Silicon Mac.')
    cache = fetch()
    work = ROOT/'.local/installer-build'
    if work.exists(): shutil.rmtree(work)
    work.mkdir(parents=True)
    app = work/'payload/Applications/Juno.app'
    contents = app/'Contents'
    resources = contents/'Resources'
    (contents/'MacOS').mkdir(parents=True)
    resources.mkdir()
    code = resources/'app'
    (code/'backend/src').mkdir(parents=True)
    copy_source(ROOT/'backend/src/juno', code/'backend/src/juno')
    copy_source(ROOT/'backend/migrations', code/'backend/migrations')
    shutil.copy2(ROOT/'backend/alembic.ini', code/'backend/alembic.ini')
    (code/'scripts').mkdir()
    for name in ('desktop_service.py', 'dev_database.py'):
        shutil.copy2(ROOT/'scripts'/name, code/'scripts'/name)
    runtime = resources/'runtime'
    runtime.mkdir()
    runtime_key = hashlib.sha256((ROOT/'packaging/runtimes-arm64.json').read_bytes() + (ROOT/'backend/requirements.lock').read_bytes()).hexdigest()[:16]
    prepared = cache/('prepared-' + runtime_key)
    if prepared.exists():
        for item in prepared.iterdir():
            copy_source(item, runtime/item.name)
    else:
        with tarfile.open(cache/'cpython-3.14.10-arm64.tar.gz') as archive:
            archive.extractall(runtime, filter='data')
        mount = work/'postgres-mount'
        mount.mkdir()
        run('hdiutil', 'attach', cache/'Postgres-2.9.6-17.dmg', '-readonly', '-nobrowse', '-mountpoint', mount,
            stdout=subprocess.DEVNULL)
        try:
            copy_source(mount/'Postgres.app/Contents/Versions/17', runtime/'postgres')
        finally:
            run('hdiutil', 'detach', mount, stdout=subprocess.DEVNULL)
        python = runtime/'python/bin/python3'
        run(python, '-m', 'pip', 'install', '--only-binary=:all:', '--no-cache-dir',
            '-r', ROOT/'backend/requirements.lock', env=clean_env())
        run(python, '-m', 'pip', 'check', env=clean_env())
        copy_source(runtime, prepared)
    # These optional server extensions require an external Python.framework.
    # Juno uses psycopg from its own runtime and does not use PL/Python.
    for path in (runtime/'postgres').rglob('*plpython3*'):
        if path.is_file() or path.is_symlink():
            path.unlink()
    run('xcrun', 'swiftc', '-parse-as-library', '-swift-version', '5', '-O', '-target',
        'arm64-apple-macosx13.5', ROOT/'desktop/Juno.swift', ROOT/'desktop/Companion.swift', '-o', contents/'MacOS/Juno')
    icons = work/'Juno.iconset'; icons.mkdir()
    master = work/'icon.png'
    run('xcrun', 'swift', ROOT/'desktop/icon.swift', master)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            suffix = '@2x' if scale == 2 else ''
            run('sips', '-z', size*scale, size*scale, master, '--out',
                icons/f'icon_{size}x{size}{suffix}.png', stdout=subprocess.DEVNULL)
    run('iconutil', '-c', 'icns', icons, '-o', resources/'Juno.icns')
    info = dict(CFBundleName='Juno', CFBundleDisplayName='Juno', CFBundleIconFile='Juno',
                CFBundleIdentifier='com.dmccoy.juno', CFBundleExecutable='Juno',
                CFBundlePackageType='APPL', CFBundleVersion='2', CFBundleShortVersionString='0.1.0',
                JunoReleaseVersion=VERSION, JunoPackaged=True, LSMinimumSystemVersion='13.5',
                NSHighResolutionCapable=True, NSAppTransportSecurity={'NSAllowsLocalNetworking': True})
    (contents/'Info.plist').write_bytes(plistlib.dumps(info))
    shutil.copy2(ROOT/'packaging/runtimes-arm64.json', resources/'runtime-provenance.json')
    (resources/'PREVIEW.txt').write_text(
        'Juno '+VERSION+'\nInternal preview. Apple Silicon. Synthetic data only.\n'
        'Includes its own Python and PostgreSQL. No Homebrew or checkout required.\n'
        'Data: ~/Library/Application Support/Juno (local to each Mac).\n'
        'Local model chat and guided check-ins. No live integrations or cross-device sync yet.\n'
        'Ad hoc signed; not Developer ID signed or notarized.\n')
    # No developer bytecode, private configuration, database, or external links.
    for path in list(app.rglob('__pycache__')):
        if path.is_dir(): shutil.rmtree(path)
    for path in app.rglob('*'):
        if path.is_symlink() and not path.resolve().is_relative_to(app.resolve()):
            raise RuntimeError('External runtime symlink: '+str(path.relative_to(app)))
        vendor_reference = path == runtime/'postgres/share/proj/proj.db'
        if path.is_file() and (path.name == '.env' or (path.suffix in ('.db', '.sqlite', '.sqlite3') and not vendor_reference)):
            raise RuntimeError('Private data entered app payload.')
    # Re-sign every Mach-O after redistribution, then seal the outer bundle.
    macho = (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbf')
    for path in app.rglob('*'):
        if path.is_file() and not path.is_symlink():
            with path.open('rb') as stream: magic = stream.read(4)
            if magic in macho:
                run('codesign', '--force', '--sign', '-', path,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run('codesign', '--force', '--deep', '--sign', '-', app)
    run('codesign', '--verify', '--deep', '--strict', app)
    installer = work/'installer-scripts'; installer.mkdir()
    preinstall = installer/'preinstall'
    preinstall.write_text('#!/bin/sh\nif /usr/bin/pgrep -x Juno >/dev/null; then\n'
                         '  echo "Quit Juno before installing this update." >&2\n  exit 1\nfi\nexit 0\n')
    preinstall.chmod(0o755)
    components = work/'components.plist'
    run('pkgbuild', '--analyze', '--root', work/'payload', components)
    definitions = plistlib.loads(components.read_bytes())
    for definition in definitions:
        definition.update(BundleIsRelocatable=False, BundleHasStrictIdentifier=True, BundleOverwriteAction='upgrade')
    components.write_bytes(plistlib.dumps(definitions))
    component = work/'component.pkg'
    run('pkgbuild', '--root', work/'payload', '--component-plist', components,
        '--identifier', 'com.dmccoy.juno.pkg', '--version', '0.1.0.2', '--install-location', '/',
        '--ownership', 'recommended', '--scripts', installer, component)
    (work/'Distribution.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
 <title>Juno — Internal Preview</title>
 <options customize="never" require-scripts="false" hostArchitectures="arm64"/>
 <allowed-os-versions><os-version min="13.5"/></allowed-os-versions>
 <welcome file="welcome.html"/>
 <choices-outline><line choice="default"><line choice="juno"/></line></choices-outline>
 <choice id="default"/><choice id="juno" visible="false"><pkg-ref id="com.dmccoy.juno.pkg"/></choice>
 <pkg-ref id="com.dmccoy.juno.pkg" version="0.1.0.2">component.pkg</pkg-ref>
</installer-gui-script>
''')
    (work/'welcome.html').write_text('''<html><body><h1>Juno — First Mac Preview</h1>
<p>Installs a standalone application at <b>/Applications/Juno.app</b>, including Python and PostgreSQL. No Homebrew, developer tools, source checkout, or internet downloads are needed at first launch.</p>
<p><b>Quit Juno before installing.</b> Open the installed app as your normal user. Your memories are kept separately in your own Library/Application Support/Juno folder.</p>
<p><b>Synthetic data only.</b> This preview supports persistent chat through a local LM Studio server, guided daily check-ins and memory review/editing/deletion. Model weights are not bundled; chat needs a local model server. The check-in works without one. Live work integrations and cross-device synchronization are not connected yet. Each Mac has independent local data.</p>
<p>Apple Silicon; macOS 13.5 or later. Intended first laptop: M5 Air running macOS 26.5. This internal preview is not Developer ID signed or notarized; follow your institution's normal software approval process.</p></body></html>''')
    output.mkdir(parents=True, exist_ok=True)
    package = output/f'Juno-{VERSION}-macOS-arm64.pkg'
    run('productbuild', '--distribution', work/'Distribution.xml', '--package-path', work,
        '--resources', work, package)
    with package.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    package.with_suffix('.pkg.sha256').write_text(digest+'  '+package.name+'\n')
    print('Package: '+str(package), flush=True)
    print('Staged app: '+str(app), flush=True)
    return app, package


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'dist')
    args = parser.parse_args()
    build(args.output.resolve())
