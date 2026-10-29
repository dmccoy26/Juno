"""Build a native Juno development app for this Mac; no browser tab required."""
from pathlib import Path
import plistlib
import subprocess
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEST = Path.home() / 'Applications/Juno.app'


def main():
    if DEST.exists():
        # Only replace a Juno app previously built by this script.
        info = plistlib.loads((DEST/'Contents/Info.plist').read_bytes())
        if info.get('JunoProjectRoot') != str(ROOT):
            raise RuntimeError('An unrelated Juno installation exists; refusing to replace it.')
        running = subprocess.run(['pgrep', '-x', 'Juno'], stdout=subprocess.DEVNULL).returncode == 0
        if running:
            raise RuntimeError('Quit Juno before rebuilding.')
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='juno-build-', dir=DEST.parent) as temp:
        bundle = Path(temp)/'Juno.app'
        contents = bundle/'Contents'
        (contents/'MacOS').mkdir(parents=True)
        subprocess.run(['xcrun','swiftc','-parse-as-library','-swift-version','5','-O','-target','arm64-apple-macosx13.5',
                        str(ROOT/'desktop/Juno.swift'),str(ROOT/'desktop/Companion.swift'),str(ROOT/'desktop/TaskDock.swift'),'-o',str(contents/'MacOS/Juno')], check=True)
        resources = contents/'Resources'
        resources.mkdir()
        iconset = Path(temp)/'Juno.iconset'
        iconset.mkdir()
        master = Path(temp)/'icon.png'
        subprocess.run(['xcrun','swift',str(ROOT/'desktop/icon.swift'),str(master)], check=True)
        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                suffix = '@2x' if scale == 2 else ''
                subprocess.run(['sips','-z',str(size*scale),str(size*scale),str(master),
                                '--out',str(iconset/f'icon_{size}x{size}{suffix}.png')],
                               check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['iconutil','-c','icns',str(iconset),'-o',str(resources/'Juno.icns')], check=True)
        info = dict(CFBundleIconFile='Juno', CFBundleName='Juno', CFBundleDisplayName='Juno', CFBundleIdentifier='com.dmccoy.juno.development',
                    CFBundleExecutable='Juno', CFBundlePackageType='APPL', CFBundleShortVersionString='0.1.0',
                    CFBundleVersion='3', LSMinimumSystemVersion='13.5', NSHighResolutionCapable=True,
                    NSAppTransportSecurity={'NSAllowsLocalNetworking':True}, JunoProjectRoot=str(ROOT))
        (contents/'Info.plist').write_bytes(plistlib.dumps(info))
        subprocess.run(['codesign','--force','--sign','-',str(bundle)], check=True)
        if DEST.exists():
            shutil.rmtree(DEST)
        shutil.move(str(bundle), str(DEST))
    print(f'Built {DEST}')
    print('Development app: uses this checkout, its Python environment, and local PostgreSQL. Not a portable distribution yet.')


if __name__ == '__main__':
    main()
