"""Verify actual native recovery serialization, owner isolation and stable retries."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'desktop/Routines.swift').read_text()
recovery = source[source.index('enum EditorRecovery {'):source.index('private struct RoutineEditor:')]
definition = source[source.index('struct RoutineDefinition:'):source.index('struct RoutineOccurrence:')]
selection = source[source.index('struct ReportEvidenceSelection:'):source.index('struct ReportEvidencePreview:')]
checks = r'''
let suite = "JunoRecoveryFixture." + UUID().uuidString
let defaults = UserDefaults(suiteName: suite)!
defer { defaults.removePersistentDomain(forName: suite) }
let key = EditorRecovery.key(owner: "owner-a", kind: "routine", record: "new")
let other = EditorRecovery.key(owner: "owner-b", kind: "routine", record: "new")
var rule = RoutineDefinition(); rule.title = "Fictional monthly review"; rule.frequency = "monthly"
let id = UUID().uuidString
EditorRecovery.save(RoutineEditorDraft(rule: rule, requestID: id, revision: 3), key: key, defaults: defaults)
let restarted = UserDefaults(suiteName: suite)!
let recovered = EditorRecovery.load(RoutineEditorDraft.self, key: key, defaults: restarted)!
precondition(recovered.rule == rule && recovered.requestID == id && recovered.revision == 3)
precondition(EditorRecovery.load(RoutineEditorDraft.self, key: other, defaults: restarted) == nil)
let emailKey = EditorRecovery.key(owner: "owner-a", kind: "chair", record: "2026-11-16:visu")
let amyKey = EditorRecovery.key(owner: "owner-a", kind: "chair", record: "2026-11-16:lwr")
let email = ChairEditorDraft(subject: "Fictional update", body: "Howdy Alex,\n\nUnsent edits.\n\n-Dan", revision: 8,
    selection: ReportEvidenceSelection(token: String(repeating: "a", count: 64), selected_ids: ["fictional-evidence"]))
EditorRecovery.save(email, key: emailKey, defaults: defaults)
let restored = EditorRecovery.load(ChairEditorDraft.self, key: emailKey, defaults: restarted)!
precondition(restored.body == email.body && restored.revision == 8 && restored.selection == email.selection)
precondition(EditorRecovery.load(ChairEditorDraft.self, key: amyKey, defaults: restarted) == nil)
precondition(EditorRecovery.key(owner: "a:b", kind: "c", record: "d") != EditorRecovery.key(owner: "a", kind: "b:c", record: "d"))
defaults.set(Data("corrupt".utf8), forKey: emailKey)
precondition(EditorRecovery.load(ChairEditorDraft.self, key: emailKey, defaults: restarted) == nil)
EditorRecovery.clear(key, defaults: defaults)
precondition(EditorRecovery.load(RoutineEditorDraft.self, key: key, defaults: restarted) == nil)
print("PASS restart recovery, unchanged request identity/base revision, exact evidence selection, owner/recipient isolation, corruption and explicit discard")
'''
with tempfile.TemporaryDirectory(prefix='juno-editor-recovery-') as temp:
    folder = Path(temp)
    (folder / 'main.swift').write_text('import Foundation\nstruct CheckInReminder { static func day(_ date: Date) -> String { "2026-11-18" } }\n' + definition + selection + recovery + checks)
    subprocess.run(['xcrun', 'swiftc', str(folder/'main.swift'), '-o', str(folder/'verify')], check=True)
    subprocess.run([str(folder/'verify')], check=True)
