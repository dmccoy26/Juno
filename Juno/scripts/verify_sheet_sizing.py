"""Verify that modal footers fit a bounded display without launching an app."""
from pathlib import Path
import subprocess
import tempfile
source = (Path(__file__).resolve().parents[1] / 'desktop/Routines.swift').read_text()
function = source[source.index('func junoSheetHeight('):source.index('private func routineDate(')]
checks = '''
precondition(junoSheetHeight(760, visibleHeight: 1000) == 760)
precondition(junoSheetHeight(760, visibleHeight: 640) == 540)
precondition(junoSheetHeight(620, visibleHeight: 600) == 500)
precondition(junoSheetHeight(580, visibleHeight: 900) == 580)
precondition(junoSheetHeight(700, visibleHeight: 350) == 260)
print("PASS modal height preserves screen clearance and keeps preferred size when it fits")
'''
with tempfile.TemporaryDirectory(prefix='juno-sheet-sizing-') as temp:
    folder = Path(temp)
    (folder / 'main.swift').write_text('import AppKit\n' + function + checks)
    subprocess.run(['xcrun', 'swiftc', str(folder/'main.swift'), '-o', str(folder/'check')], check=True)
    subprocess.run([str(folder/'check')], check=True)
