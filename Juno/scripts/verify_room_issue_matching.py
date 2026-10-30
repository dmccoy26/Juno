"""Check native room-title matching without reading real tasks."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
source=(root/'desktop/Schedules.swift').read_text()
functions='func scheduleRoomKey'+source.split('func scheduleRoomKey',1)[1].split('struct RoomTaskDockIssues',1)[0]
checks=r'''
precondition(scheduleTitleMentionsRoom("A121M03 offline","ARTS 121"))
precondition(scheduleTitleMentionsRoom("Airprint in ARTS 121","A121"))
precondition(scheduleTitleMentionsRoom("LIB115 instructor tablet","LIBR 115"))
precondition(scheduleTitleMentionsRoom("TH108M19 offline","TRUS 108"))
precondition(!scheduleTitleMentionsRoom("A1210 offline","ARTS 121"))
precondition(!scheduleTitleMentionsRoom("A140M03 offline","ARTS 121"))
precondition(!scheduleTitleMentionsRoom("BA121 problem","ARTS 121"))
precondition(!scheduleTitleMentionsRoom("Unlinked issue","ARTS 121"))
precondition(!scheduleTitleMentionsRoom("Unlinked issue",""))
print("PASS native room issue aliases, device suffixes, room isolation and unlinked tasks")
'''
with tempfile.TemporaryDirectory(prefix='juno-room-issues-') as tmp:
    path=Path(tmp)
    (path/'main.swift').write_text('import Foundation\n'+functions+checks)
    subprocess.run(['xcrun','swiftc',str(path/'main.swift'),'-o',str(path/'check')],check=True)
    subprocess.run([str(path/'check')],check=True)
