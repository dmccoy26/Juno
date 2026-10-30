"""Exercise native memory write intent; recall questions must remain chat."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'desktop/Companion.swift').read_text()
function='func memoryRequestText'+s.split('func memoryRequestText',1)[1].split('extension JunoStore',1)[0]
checks=r'''
precondition(memoryRequestText("Remember this: Fictional note") == "Fictional note")
precondition(memoryRequestText("Can you remember that the fictional cutter is TEST-42?") == "the fictional cutter is TEST-42?")
precondition(memoryRequestText("Please remember this:\nFirst line\nSecond line") == "First line\nSecond line")
precondition(memoryRequestText("Do you remember that printer?") == nil)
precondition(memoryRequestText("Remember when we fixed the printer?") == nil)
precondition(memoryRequestText("Tell me what you remember") == nil)
precondition(memoryRequestText("Remember this") == "")
print("PASS native explicit memory-review intent, multiline text and recall-question boundaries")
'''
with tempfile.TemporaryDirectory(prefix='juno-memory-intent-') as tmp:
    path=Path(tmp);(path/'main.swift').write_text('import Foundation\n'+function+checks)
    subprocess.run(['xcrun','swiftc',str(path/'main.swift'),'-o',str(path/'check')],check=True)
    subprocess.run([str(path/'check')],check=True)
