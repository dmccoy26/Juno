"""Compile actual native starting-step, permission and recovery helpers."""
from pathlib import Path
import tempfile,subprocess
root=Path(__file__).resolve().parents[1]
source=(root/'desktop/WorkSupport.swift').read_text()
models=source[source.index('struct WorkSourceRef:'):source.index('private struct WorkEditorRequest:')]
recovery=(root/'desktop/Routines.swift').read_text()
recovery=recovery[recovery.index('enum EditorRecovery {'):recovery.index('struct RoutineEditorDraft:')]
checks='''
var draft=WorkStepDraft()
precondition(!draft.canStart)
draft.title="Synthetic work";draft.useTinyStep();precondition(draft.canStart)
precondition(draft.first_action.contains("notes") && draft.finish_point.contains("written down"))
draft.source_ref=WorkSourceRef(task_id:"synthetic",workspace_id:"fixture",snapshot_id:"copy")
draft.useTinyStep();precondition(draft.first_action.contains("issue"))
precondition(WorkSupportAccess.canEdit(connected:true,offline:false,meeting:false,syncing:false,queued:0))
precondition(!WorkSupportAccess.canEdit(connected:true,offline:true,meeting:false,syncing:false,queued:0))
precondition(!WorkSupportAccess.canEdit(connected:true,offline:false,meeting:true,syncing:false,queued:0))
precondition(!WorkSupportAccess.canEdit(connected:true,offline:false,meeting:false,syncing:true,queued:0))
precondition(!WorkSupportAccess.canEdit(connected:true,offline:false,meeting:false,syncing:false,queued:1))
let bookmark=WorkBookmark(id:"fixture",title:"Synthetic work",first_action:"Open list",finish_point:"List visible",where_stopped:"The other Mac stopping point",blocker:"Synthetic access blocker",status:"interrupted",source_ref:nil,resume_count:1,created_at:"2026-11-18T20:00:00Z",updated_at:"2026-11-18T20:00:00Z")
precondition(bookmark.comparisonText.contains("The other Mac stopping point") && bookmark.comparisonText.contains("Synthetic access blocker") && bookmark.comparisonText.contains("List visible"))
let suite="juno.synthetic.mission17."+UUID().uuidString
let defaults=UserDefaults(suiteName:suite)!
let key=EditorRecovery.key(owner:"fictional-owner",kind:"work-step",record:"start:new")
EditorRecovery.save(draft,key:key,defaults:defaults)
precondition(EditorRecovery.load(WorkStepDraft.self,key:key,defaults:defaults)==draft)
precondition(EditorRecovery.load(WorkStepDraft.self,key:EditorRecovery.key(owner:"other",kind:"work-step",record:"start:new"),defaults:defaults)==nil)
EditorRecovery.clear(key,defaults:defaults)
precondition(EditorRecovery.load(WorkStepDraft.self,key:key,defaults:defaults)==nil)
defaults.removePersistentDomain(forName:suite)
print("PASS actual native small-step templates, offline/Meeting/queue gates and owner-scoped draft recovery")
'''
with tempfile.TemporaryDirectory(prefix='juno-work-support-') as folder:
    p=Path(folder);(p/'main.swift').write_text('import Foundation\n'+models+recovery+checks)
    subprocess.run(['xcrun','swiftc',str(p/'main.swift'),'-o',str(p/'check')],check=True)
    subprocess.run([str(p/'check')],check=True)
