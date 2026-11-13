# Preview.29 interaction inventory

Source baseline `201acb8`. Each row is a source declaration or a native command. Dynamic rows, menu options and conditional states need runtime checks during Mission 15. A declaration does not establish that an action works.

## Companion.swift

| Line | Control or interaction | Source excerpt |
| ---: | --- | --- |
| 217 | `Button` | `Button { showSidebar.toggle() } label: { Image(systemName:"sidebar.left") }.help("Show or hide navigation")` |
| 228 | `Toggle` | `Toggle("Meeting mode",isOn:$store.meeting).toggleStyle(.switch).help("Professional tone; private-mode replies stay hidden.")` |
| 235 | `Button` | `Button("Sync") { store.reconnectShared() }.disabled(store.syncing)` |
| 242 | `List` | `List(selection:$store.section) {` |
| 245 | `Button` | `Button { NotificationCenter.default.post(name:Notification.Name("JunoSettings"),object:nil) } label: { Label("Settings…",systemImage:"gearshape") }.buttonStyle(.plain) }` |
| 255 | `Button` | `Button("Dismiss") { store.problem = nil } }.padding(12) }` |
| 260 | `.alert` | `.alert("Keep your existing chat draft?",isPresented:Binding(get:{store.proposedChatDraft != nil},set:{if !$0 {store.proposedChatDraft = nil}})) {` |
| 261 | `Button` | `Button("Keep draft",role:.cancel) { store.proposedChatDraft = nil }` |
| 262 | `Button` | `Button("Add question to draft") { if let proposal = store.proposedChatDraft { store.chatDraft += "\n\n" + proposal };store.proposedChatDraft = nil;store.section = "Chat" }` |
| 275 | `Button` | `Button { store.chooseConversation(nil) } label: { Label("New conversation", systemImage: "plus") }.disabled(store.chatSending)` |
| 276 | `List` | `List(selection: Binding(get: { store.currentConversation }, set: { store.chooseConversation($0) })) {` |
| 278 | `.contextMenu` | `.contextMenu {` |
| 279 | `Button` | `Button("Delete conversation…",role:.destructive) { deleteTarget = row;deleteIssue = nil }.disabled(store.offline &#124;&#124; store.chatSending &#124;&#124; deletingConversation)` |
| 284 | `Button` | `Button("Delete conversation…",role:.destructive) { deleteTarget = row;deleteIssue = nil }.disabled(store.offline &#124;&#124; store.chatSending &#124;&#124; deletingConversation)` |
| 288 | `Button` | `Button("Older conversations") { Task { do { try await store.loadConversations(more: true) } catch { store.report(error) } } } }` |
| 292 | `Button` | `Button("Connect model") { store.openSettings("Model") } }.padding(12).background(.purple.opacity(0.1))` |
| 297 | `Button` | `Button("Load older messages") { if let id = store.currentConversation { Task { do { try await store.loadMessages(id, older: true) } catch { store.report(error) } } } } }` |
| 310 | `Button` | `Button("Review memory") { Task { do {` |
| 316 | `Button` | `Button("Save as memory…") { store.memoryReviewOriginal = nil;store.memoryReviewMessageID = message.id;store.memoryReviewText = memoryRequestText(message.text) ?? message.text;store.memo` |
| 319 | `Button` | `Button("Retry this reply") { store.sendChat(retry: message) }.disabled(store.chatSending) }` |
| 326 | `Button` | `Button("Review memory") { store.section = "Memories" };` |
| 326 | `Button` | `Button("Dismiss") { store.memoryNotice = nil } } }` |
| 329 | `TextEditor` | `TextEditor(text: $store.chatDraft).frame(height: 75).padding(6).overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary)).accessibilityLabel("Message to Juno")` |
| 331 | `Button` | `Button(memoryRequestText(store.chatDraft) == nil ? "Send" : "Review memory") { store.sendChat() }` |
| 331 | `.keyboardShortcut` | `.keyboardShortcut(.return, modifiers: .command).disabled(!store.connected &#124;&#124; (store.offline && memoryRequestText(store.chatDraft) == nil) &#124;&#124; (!store.pendingEdits.isEmpty && memoryReques` |
| 333 | `Button` | `Button("Refresh chat") { if let id = store.currentConversation { Task { try? await store.loadMessages(id) } } }.disabled(store.chatSending) }` |
| 336 | `.alert` | `.alert("Delete this conversation?",isPresented:Binding(get:{deleteTarget != nil},set:{if !$0 {deleteTarget = nil}})) {` |
| 337 | `Button` | `Button("Cancel",role:.cancel) { deleteTarget = nil }` |
| 338 | `Button` | `Button("Delete conversation",role:.destructive) {` |
| 343 | `.sheet` | `.sheet(isPresented:Binding(get:{store.memoryReviewText != nil},set:{if !$0 {store.memoryReviewText = nil;store.memoryReviewOriginal = nil;store.memoryReviewMessageID = nil}})) {` |
| 361 | `TextField` | `TextField("Local server", text: $store.modelBase).textFieldStyle(.roundedBorder).accessibilityLabel("Local model server address")` |
| 362 | `Button` | `Button("Find models") { store.probeModel() }.disabled(!store.connected &#124;&#124; store.modelBusy)` |
| 364 | `Picker` | `Picker("Chat model", selection: $store.modelName) { ForEach(store.modelOptions, id: \.self) { Text($0).tag($0) } }` |
| 365 | `TextField` | `TextField("Model identifier", text: $store.modelName).textFieldStyle(.roundedBorder) }` |
| 366 | `Button` | `Button("Save connection") { store.saveModel() }.disabled(!store.connected &#124;&#124; store.modelBusy &#124;&#124; store.modelName.isEmpty)` |
| 434 | `DatePicker` | `DatePicker("Day", selection: $day, displayedComponents: .date).environment(\.timeZone, workTimeZone).fixedSize().disabled(store.checkBusy) }` |
| 447 | `TextEditor` | `TextEditor(text: $store.checkAnswer).frame(minHeight: 160).padding(8).overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary)).accessibilityLabel("Check-in answer")` |
| 449 | `Button` | `Button("Skip for now") { store.saveAnswer(skip: true) }; Spacer();` |
| 449 | `Button` | `Button("Save answer and continue") { store.saveAnswer() }.disabled(store.checkAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty &#124;&#124; store.checkAnswer.count &gt; 10000) }.disabl` |
| 452 | `TextEditor` | `TextEditor(text: $store.diaryDraft).frame(minHeight: 220).padding(8).overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary)).accessibilityLabel("Diary draft")` |
| 454 | `Button` | `Button("Carry a reviewed detail into Plan…") { showCarry = true }.disabled(row.status != "confirmed" &#124;&#124; store.diaryDraft != row.diary_text &#124;&#124; store.offline &#124;&#124; store.unsavedSections.cont` |
| 455 | `Button` | `Button("Save draft") { store.saveDiary(confirm: false) }; Spacer();` |
| 455 | `Button` | `Button(row.status == "confirmed" ? "Save confirmed changes" : "Confirm diary") { store.saveDiary(confirm: true) } }.disabled(store.checkBusy &#124;&#124; store.diaryDraft.trimmingCharacters(in: .` |
| 459 | `DisclosureGroup` | `DisclosureGroup("Saved work context & freshness") {` |
| 464 | `DisclosureGroup` | `DisclosureGroup("Evidence & freshness") {` |
| 487 | `Button` | `Button("Review this issue in Plan") { openPlan(brief,task.id) }.disabled(store.offline &#124;&#124; store.checkBusy &#124;&#124; store.unsavedSections.contains("Plan"))` |
| 491 | `Button` | `Button("Open Plan for this day") { openPlan(brief,nil) }.disabled(store.offline &#124;&#124; store.checkBusy &#124;&#124; store.unsavedSections.contains("Plan"))` |
| 499 | `Button` | `Button("Reload saved check-in") { briefRefresh = UUID();store.loadCheckIn(day: dayKey) }.disabled(!store.connected &#124;&#124; store.checkBusy)` |
| 512 | `.sheet` | `.sheet(isPresented:$showCarry,onDismiss:{briefRefresh=UUID()}) { CarryForwardEditor(store:store,dayKey:dayKey,planDay:brief?.next_day ?? dayKey) }` |
| 603 | `Button` | `Button { filter = selection } label: {` |
| 613 | `Button` | `Button("Refresh overview") { Task { await load() } }.disabled(busy &#124;&#124; !store.connected)` |
| 616 | `Button` | `Button("Talk it through") { store.section = "Chat" };` |
| 616 | `Button` | `Button("Rooms & people") { store.section = "Schedules" };` |
| 616 | `Button` | `Button("Daily check-in") { store.section = "Check-in" };` |
| 616 | `Button` | `Button("Remember something") { remember = true }.disabled(!store.connected) }` |
| 629 | `Picker` | `Picker("Show",selection:$filter) { Text("Due / overdue").tag("Due / overdue");Text("Recorded blockers").tag("Recorded blockers");Text("All unfinished").tag("All unfinished") };` |
| 629 | `TextField` | `TextField("Find an issue",text:$search).textFieldStyle(.roundedBorder) }` |
| 633 | `Button` | `Button("Review") { store.planningTaskID = task.id;store.section = "Plan" } }` |
| 640 | `Button` | `Button("Open all TaskDock records") { store.section = "TaskDock" }` |
| 646 | `Button` | `Button("Open TaskDock") { store.section = "TaskDock" }` |
| 659 | `Button` | `Button("Review schedules") { store.section = "Schedules" }` |
| 669 | `.sheet` | `.sheet(isPresented:$remember) { Editor(store:store,original:nil) }` |
| 682 | `Picker` | `Picker("Appearance",selection:$appearance) { Text("Follow system").tag("system");Text("Light").tag("light");Text("Dark").tag("dark") };Text("Juno uses standard Mac fonts and controls. T` |
| 683 | `Toggle` | `Toggle("Meeting mode",isOn:$store.meeting);Text("Meeting mode uses a professional tone and hides private-mode replies. You control when it changes.").foregroundStyle(.secondary) }.paddi` |
| 689 | `List` | `List(selection:$store.settingsSection) {` |
| 790 | `DisclosureGroup` | `DisclosureGroup("Read the saved diary — revision \(source.diary_revision)") { Text(source.text).textSelection(.enabled) }` |
| 792 | `TextEditor` | `TextEditor(text:$quote).frame(height:100).accessibilityLabel("Carry-forward diary excerpt").overlay(RoundedRectangle(cornerRadius:8).stroke(.quaternary))` |
| 793 | `TextField` | `TextField("Find task by title or reference",text:$query).textFieldStyle(.roundedBorder)` |
| 794 | `Picker` | `Picker("Task to update", selection: $taskID) {` |
| 804 | `Toggle` | `Toggle("Where to resume",isOn:toggle("resume"));if selectedFields.contains("resume") {` |
| 804 | `TextField` | `TextField("Reviewed resumption note",text:$resume).textFieldStyle(.roundedBorder);` |
| 804 | `Button` | `Button("Use diary excerpt as resumption note"){resume=quote}}` |
| 805 | `Toggle` | `Toggle("Blocker",isOn:toggle("blocker"));if selectedFields.contains("blocker"){` |
| 805 | `TextField` | `TextField("Reviewed blocker — blank explicitly clears",text:$blocker).textFieldStyle(.roundedBorder)}` |
| 806 | `Toggle` | `Toggle("Waiting on",isOn:toggle("waiting_on"));if selectedFields.contains("waiting_on"){` |
| 806 | `TextField` | `TextField("Reviewed dependency",text:$waiting).textFieldStyle(.roundedBorder)}` |
| 807 | `Toggle` | `Toggle("Next action",isOn:toggle("next_action"));if selectedFields.contains("next_action"){` |
| 807 | `TextField` | `TextField("Reviewed next action",text:$next).textFieldStyle(.roundedBorder)}` |
| 808 | `Toggle` | `Toggle("Next check date",isOn:toggle("next_check"));if selectedFields.contains("next_check"){` |
| 808 | `TextField` | `TextField("YYYY-MM-DD — blank explicitly clears",text:$check).textFieldStyle(.roundedBorder)}` |
| 809 | `Toggle` | `Toggle("Estimated minutes",isOn:toggle("minutes"));if selectedFields.contains("minutes"){` |
| 809 | `TextField` | `TextField("Reviewed estimate — blank explicitly clears",text:$minutes).textFieldStyle(.roundedBorder)}` |
| 816 | `Button` | `Button(receipt == nil ? "Cancel" : "Close") { dismiss() }.disabled(busy &#124;&#124; pending != nil)` |
| 816 | `.keyboardShortcut` | `.keyboardShortcut(.cancelAction)` |
| 817 | `Button` | `Button("Reload source & compare",action:load).disabled(busy &#124;&#124; pending != nil &#124;&#124; receipt != nil)` |
| 818 | `Button` | `Button("Retry same save",action:retry).disabled(busy &#124;&#124; store.offline);` |
| 818 | `Button` | `Button("Keep pending save & close"){dismiss()}.disabled(busy)}` |
| 820 | `Button` | `Button("Review changes",action:review).disabled(busy &#124;&#124; taskID.isEmpty &#124;&#124; quote.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty &#124;&#124; selectedFields.isEmpty &#124;&#124; pending != nil &#124;&#124; rec` |
| 821 | `Button` | `Button("Save reviewed planning detail",action:save).disabled(busy &#124;&#124; previewPayload == nil &#124;&#124; pending != nil &#124;&#124; receipt != nil &#124;&#124; store.offline)` |
| 845 | `DisclosureGroup` | `DisclosureGroup(card.title+(card.stale ? " · needs refresh" : "")) {` |
| 851 | `Button` | `Button("View "+evidence.app+" evidence"){selectedEvidence=evidence}.font(.caption)}` |
| 863 | `Button` | `Button("Reload saved operational evidence") {refreshing=true;Task {defer{refreshing=false};do{current=try await store.decode(OperationalBrief.self,"/v1/operations")}catch{current=nil}}}` |
| 864 | `Button` | `Button("Review alert–task links…"){manage=true}.disabled(store.offline &#124;&#124; store.sharedProfile != nil)` |
| 866 | `DisclosureGroup` | `DisclosureGroup("Recent planning choices") {ForEach(Array(value.feedback.suffix(10).reversed())){item in Text(item.planning_day+" · "+item.outcome+" · Task "+item.task_id+" · "+item.rat` |
| 874 | `.sheet` | `.sheet(isPresented:$manage){OperationalLinkEditor(store:store,value:value){current=$0}}` |
| 875 | `.sheet` | `.sheet(item:$selectedEvidence){OperationalEvidenceSheet(store:store,evidence:$0)}` |
| 890 | `Picker` | `Picker("Beacon observation",selection:$alert){Text("Choose observation").tag("");ForEach(value.alert_choices){Text($0.title+" · "+String($0.id.suffix(8))).tag($0.id)}}` |
| 891 | `TextField` | `TextField("Search task titles or references",text:$search).textFieldStyle(.roundedBorder)` |
| 892 | `Picker` | `Picker("TaskDock task",selection:$task){Text("Choose task").tag("");ForEach(choices){Text($0.title+" · "+String($0.id.suffix(12))).tag($0.id)}}` |
| 893 | `TextField` | `TextField("Why these records belong together (optional)",text:$rationale).textFieldStyle(.roundedBorder)` |
| 896 | `Button` | `Button("Remove reviewed link") {` |
| 899 | `Button` | `Button("Cancel"){dismiss()}` |
| 899 | `.keyboardShortcut` | `.keyboardShortcut(.cancelAction);Spacer();` |
| 899 | `Button` | `Button("Save reviewed link"){` |
| 916 | `Button` | `Button("Close"){dismiss()}` |
| 916 | `.keyboardShortcut` | `.keyboardShortcut(.cancelAction)` |
| 934 | `Button` | `Button("Record planning choice…"){show=true}.disabled(store.offline &#124;&#124; store.sharedProfile != nil)` |
| 934 | `.sheet` | `.sheet(isPresented:$show){RecommendationFeedbackEditor(store:store,taskID:taskID,day:day)}}` |
| 944 | `Picker` | `Picker("Choice",selection:$outcome){Text("Accepted proposal").tag("accepted");Text("Dismissed").tag("dismissed");Text("Reschedule proposal").tag("rescheduled")}.disabled(pending != nil ` |
| 945 | `TextField` | `TextField("Reason (optional)",text:$rationale).textFieldStyle(.roundedBorder).disabled(pending != nil &#124;&#124; saved)` |
| 946 | `TextField` | `TextField("Proposed date · YYYY-MM-DD",text:$reschedule).textFieldStyle(.roundedBorder).disabled(pending != nil &#124;&#124; saved)}` |
| 949 | `Button` | `Button(saved ? "Close" : "Cancel"){dismiss()}` |
| 949 | `.keyboardShortcut` | `.keyboardShortcut(.cancelAction);Spacer();if !saved {` |
| 949 | `Button` | `Button(pending == nil ? "Save choice" : "Retry same choice"){` |
| 969 | `DisclosureGroup` | `DisclosureGroup("Procedures & longer-term repair review") {` |
| 971 | `Button` | `Button("Load authorized references") {load()}.disabled(store.offline &#124;&#124; busy)` |
| 976 | `DisclosureGroup` | `DisclosureGroup(reference.label+((reference.changed &#124;&#124; reference.stale) ? " · review source" : "")) {` |
| 981 | `Button` | `Button("Remove reference") {` |
| 987 | `Button` | `Button("Designate a saved reference…"){choose=true}.disabled(store.sharedProfile != nil &#124;&#124; procedures.choices.isEmpty &#124;&#124; busy)` |
| 1003 | `.sheet` | `.sheet(isPresented:$choose) {` |
| 1007 | `Picker` | `Picker("Saved record",selection:$selected){Text("Choose record").tag("");ForEach(procedures?.choices ?? []){Text($0.kind+" · "+$0.title+" · "+String($0.record_id.suffix(10))).tag($0.id)` |
| 1008 | `TextField` | `TextField("Reference label",text:$label).textFieldStyle(.roundedBorder)` |
| 1010 | `Button` | `Button("Cancel"){choose=false}` |
| 1010 | `.keyboardShortcut` | `.keyboardShortcut(.cancelAction);Spacer();` |
| 1010 | `Button` | `Button("Save reference"){` |

## Connections.swift

| Line | Control or interaction | Source excerpt |
| ---: | --- | --- |
| 112 | `Picker` | `Picker("Connection route",selection:$route) { Text("Through TaskDock").tag("taskdock");Text("Direct programs").tag("direct") }.pickerStyle(.segmented).padding(20)` |
| 342 | `TextField` | `TextField("OAuth client ID",text:$saved.clientID).disabled(busy &#124;&#124; waiting).onChange(of:saved.clientID) { _ in reviewed = false }` |
| 344 | `SecureField` | `SecureField("Client secret (blank uses saved value)",text:$secretField).disabled(busy &#124;&#124; waiting)` |
| 345 | `Button` | `Button("Load Google Desktop client JSON…") { importGoogleClient() }.disabled(busy &#124;&#124; waiting)` |
| 346 | `TextField` | `TextField("Tenant: organizations, common, or approved tenant ID",text:$saved.tenant).disabled(busy &#124;&#124; waiting) }` |
| 348 | `Button` | `Button("Save app setup") { busy = true;Task { defer { busy = false };do { try await saveForm();notice = "Setup saved in this Mac's Keychain. Sign in when ready." } catch { record(error)` |
| 349 | `Button` | `Button("Sign in for read access…") { startSignIn() }.disabled(busy &#124;&#124; waiting &#124;&#124; saved.clientID.isEmpty)` |
| 350 | `Button` | `Button("Cancel sign-in") { cancelSignIn();notice = "Sign-in cancelled in Juno. You can close the provider page." } }` |
| 352 | `DisclosureGroup` | `DisclosureGroup("Granted authorization scopes") { Text(saved.scope).font(.caption).textSelection(.enabled) } }` |
| 354 | `SecureField` | `SecureField(provider == .slack ? "Approved Slack token (blank uses Keychain)" : "Approved Smartsheet API token (blank uses Keychain)",text:$tokenField).disabled(busy &#124;&#124; waiting).onChang` |
| 355 | `Button` | `Button("Save credential in Keychain") { busy = true;Task { defer { busy = false };do { try await saveForm();notice = "Credential saved on this Mac. Discover and review the account befor` |
| 357 | `Button` | `Button("Discover account and resources") { discoverResources() }.disabled(busy &#124;&#124; waiting &#124;&#124; cooldown)` |
| 367 | `TextField` | `TextField("in:inbox is:unread",text:$saved.query).onChange(of:saved.query) { _ in reviewed = false }` |
| 372 | `TextField` | `TextField("Filter discovered resources",text:$resourceFilter)` |
| 374 | `Toggle` | `Toggle(resource.label,isOn:Binding(get:{ saved.resources.contains(resource.id) },set:{ yes in` |
| 383 | `DisclosureGroup` | `DisclosureGroup("Enter exact resource IDs instead") {` |
| 384 | `TextField` | `TextField(provider == .google_chat ? "spaces/SPACE_ID, spaces/ANOTHER_ID" : "Comma-separated resource IDs",text:$manualIDs).onChange(of:manualIDs) { _ in reviewed = false }` |
| 390 | `DatePicker` | `DatePicker("From",selection:dayBinding(\.start),displayedComponents:.date).labelsHidden() }` |
| 391 | `DatePicker` | `DatePicker("Until",selection:dayBinding(\.end),displayedComponents:.date).labelsHidden() }` |
| 393 | `TextField` | `TextField("IANA timezone",text:$saved.zone)` |
| 396 | `Toggle` | `Toggle("Include readable replies to parents in this window",isOn:$saved.includeThreads);Text("Replies to older parents may be missing. Bot/user scope and provider retention limits still` |
| 399 | `TextField` | `TextField("Archive sheet ID (optional)",text:$saved.completionArchiveID)` |
| 401 | `TextField` | `TextField("Exact completion-date column name (optional)",text:$saved.completionDateColumn)` |
| 411 | `Toggle` | `Toggle("I reviewed this account, resource selection and coverage.",isOn:$reviewed).toggleStyle(.checkbox).disabled(saved.accountID.isEmpty &#124;&#124; busy &#124;&#124; waiting)` |
| 412 | `Button` | `Button("Refresh read-only copy") { refresh() }.disabled(busy &#124;&#124; waiting &#124;&#124; !reviewed &#124;&#124; cooldown)` |
| 420 | `Picker` | `Picker("Program",selection:$provider) { ForEach(WorkProvider.allCases) { p in Text(p.label).tag(p) } }.disabled(busy &#124;&#124; waiting)` |
| 431 | `Button` | `Button("Disconnect and forget this Mac's credential…",role:.destructive) { forget = true }.disabled(busy &#124;&#124; waiting)` |
| 441 | `.alert` | `.alert("Forget this connection on this Mac?",isPresented:$forget) {` |
| 442 | `Button` | `Button("Cancel",role:.cancel) {}` |
| 443 | `Button` | `Button("Disconnect and forget",role:.destructive) {` |
| 522 | `TextField` | `TextField("Local TaskDock API address",text:$origin).disabled(busy).onChange(of:origin) { _ in catalog = nil;reviewed = false }` |
| 523 | `SecureField` | `SecureField("Dedicated Juno token (blank uses Juno's saved TaskDock key)",text:$tokenField).disabled(busy).onChange(of:tokenField) { _ in catalog = nil;reviewed = false }` |
| 524 | `Button` | `Button("Discover TaskDock connections") { discover() }.disabled(busy)` |
| 532 | `Button` | `Button("Set up direct " + provider.label + " access…") { onDirect(provider) }.disabled(busy) }` |
| 537 | `Toggle` | `Toggle(label(kind),isOn:Binding(get:{ selected.contains(kind) },set:{ yes in if yes { selected.append(kind) } else { selected.removeAll { $0 == kind } };reviewed = false })).toggleStyle` |
| 539 | `Toggle` | `Toggle("I reviewed this TaskDock workspace and selected saved sections.",isOn:$reviewed).toggleStyle(.checkbox)` |
| 540 | `Button` | `Button("Read shared saved evidence") { readSaved() }.disabled(busy &#124;&#124; !reviewed &#124;&#124; selected.isEmpty)` |

## Integrations.swift

| Line | Control or interaction | Source excerpt |
| ---: | --- | --- |
| 155 | `DisclosureGroup` | `DisclosureGroup("Import a dated copy") {` |
| 157 | `Picker` | `Picker("Source",selection:$kind) { Text("Calendar (.ics)").tag("calendar");Text("Semester schedule (.csv)").tag("schedules");Text("Beacon alerts (.json)").tag("beacon") }.pickerStyle(.s` |
| 160 | `DatePicker` | `DatePicker("From",selection:scheduleDayBinding($start),displayedComponents:.date).labelsHidden() }` |
| 161 | `DatePicker` | `DatePicker("Until",selection:scheduleDayBinding($end),displayedComponents:.date).labelsHidden() }` |
| 163 | `TextField` | `TextField("Timezone, e.g. America/Chicago",text:$zone)` |
| 166 | `Button` | `Button("Choose file and import…") { importFile() };` |
| 166 | `Button` | `Button("Save schedule CSV template…") { template() } }.disabled(busy)` |
| 170 | `DisclosureGroup` | `DisclosureGroup("Beacon connection & refresh") {` |
| 172 | `TextField` | `TextField("Loopback API address",text:$origin)` |
| 173 | `SecureField` | `SecureField("Dedicated read-only integration key (blank uses Keychain)",text:$token)` |
| 174 | `DisclosureGroup` | `DisclosureGroup("Retained equipment issues") {` |
| 175 | `SecureField` | `SecureField("Asset-scoped issue key (blank uses Keychain)",text:$retainedIssueToken)` |
| 176 | `Toggle` | `Toggle("Include the authorized inventory’s retained issues",isOn:$includeIssueSnapshot)` |
| 180 | `Button` | `Button("Refresh Beacon") { refreshBeacon() }.disabled(busy)` |
| 181 | `Button` | `Button("Forget saved keys…",role:.destructive) { forgettingKey = true }.disabled(busy)` |
| 194 | `TextField` | `TextField("Filter saved items",text:$search)` |
| 202 | `Button` | `Button("Remove copy…",role:.destructive) { deleting = source }.disabled(busy) }` |
| 212 | `DisclosureGroup` | `DisclosureGroup("Recorded busy time by day (overlaps counted once)") {` |
| 219 | `DisclosureGroup` | `DisclosureGroup(row.heading + (row.location?.isEmpty == false ? " · " + row.location! : "")) {` |
| 251 | `.alert` | `.alert("Forget Beacon access on this Mac?",isPresented:$forgettingKey) {` |
| 252 | `Button` | `Button("Cancel",role:.cancel) { }` |
| 253 | `Button` | `Button("Forget keys",role:.destructive) { let address = origin;busy = true;Task { defer { busy = false };do { try await credentialWork { try BeaconKeychain.forget(address);try BeaconKey` |
| 255 | `.alert` | `.alert("Remove this imported copy?",isPresented:Binding(get:{ deleting != nil },set:{ if !$0 { deleting = nil } })) {` |
| 256 | `Button` | `Button("Cancel",role:.cancel) { deleting = nil }` |
| 257 | `Button` | `Button("Remove copy",role:.destructive) {` |

## Juno.swift

| Line | Control or interaction | Source excerpt |
| ---: | --- | --- |
| 317 | `TextEditor` | `TextEditor(text: $text).font(.body).frame(height: 160).padding(6).overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary))` |
| 319 | `TextField` | `TextField("Source", text: $source).textFieldStyle(.roundedBorder)` |
| 320 | `Picker` | `Picker("How do we know?", selection: $confidence) {` |
| 325 | `Button` | `Button("Load latest saved version") {` |
| 336 | `Button` | `Button("Use latest values") { text = latest.text;source = latest.source;confidence = latest.confidence;base = latest;comparison = nil;conflict = false;issue = nil }` |
| 337 | `Button` | `Button("Keep my draft for review") { base = latest;comparison = nil;conflict = false;issue = "Review your draft, then Save memory. Nothing has been overwritten." }` |
| 343 | `Button` | `Button("Cancel") { dismiss() }` |
| 343 | `.keyboardShortcut` | `.keyboardShortcut(.cancelAction).disabled(saving)` |
| 345 | `Button` | `Button(saving ? "Saving…" : "Save memory") {` |
| 351 | `.keyboardShortcut` | `.keyboardShortcut(.defaultAction).disabled(saving &#124;&#124; text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty &#124;&#124; text.count &gt; 10000 &#124;&#124; source.trimmingCharacters(in: .whitespacesAndN` |
| 373 | `TextField` | `TextField("Search memories", text: $store.query).focused($searchFocused).onReceive(NotificationCenter.default.publisher(for:Notification.Name("JunoFind"))) { _ in if store.section == "M` |
| 373 | `.onSubmit` | `.onSubmit { store.refresh() }.disabled(!store.connected)` |
| 374 | `Button` | `Button("Search") { store.refresh() };` |
| 374 | `Button` | `Button("Clear") { store.query = ""; store.refresh() } }.disabled(!store.connected &#124;&#124; store.busy)` |
| 375 | `List` | `List(selection: $store.selected) {` |
| 383 | `Button` | `Button("Load more") { store.refresh(more: true) }.disabled(store.busy) }` |
| 384 | `Button` | `Button { editRequest = MemoryEditRequest(original:nil) } label: { Label("Add memory", systemImage: "plus") }.disabled(!store.connected &#124;&#124; store.busy)` |
| 394 | `Button` | `Button("Correct memory") { editRequest = MemoryEditRequest(original:row) }` |
| 395 | `Button` | `Button("Delete…", role: .destructive) { deleteTarget = row; deleting = true }` |
| 407 | `.sheet` | `.sheet(item:$editRequest) { request in Editor(store:store,original:request.original).id(request.id) }` |
| 408 | `.alert` | `.alert("Delete this memory?", isPresented: $deleting) {` |
| 409 | `Button` | `Button("Cancel", role: .cancel) { deleteTarget = nil }` |
| 410 | `Button` | `Button("Delete memory", role: .destructive) {` |
| 428 | `.addItem(withTitle:` | `.addItem(withTitle: "About Juno", action: #selector(about), keyEquivalent: "").target = self` |
| 429 | `.addItem(withTitle:` | `.addItem(withTitle:"Settings…",action:#selector(showSettings),keyEquivalent:",").target = self` |
| 431 | `.addItem(withTitle:` | `.addItem(withTitle: "Hide Juno", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")` |
| 432 | `.addItem(withTitle:` | `.addItem(withTitle: "Quit Juno", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")` |
| 434 | `.addItem(withTitle:` | `.addItem(withTitle: name, action: Selector(action), keyEquivalent: key) }` |
| 435 | `.addItem(withTitle:` | `.addItem(withTitle:"Find…",action:#selector(findInWorkspace),keyEquivalent:"f");find.target = self` |
| 436 | `.addItem(withTitle:` | `.addItem(withTitle:"Redo",action:Selector(("redo:")),keyEquivalent:"z");redo.keyEquivalentModifierMask = [.command,.shift]` |
| 439 | `.addItem(withTitle:` | `.addItem(withTitle:title == "Check-in" ? "Daily check-in" : title == "Workers" ? "Worker updates" : title,action:#selector(navigate(_:)),keyEquivalent:String(index+1));item.representedO` |
| 442 | `.addItem(withTitle:` | `.addItem(withTitle: "Minimize", action: #selector(minimizeCurrent(_:)), keyEquivalent: "m").target = self` |
| 443 | `.addItem(withTitle:` | `.addItem(withTitle: "Close Window", action: #selector(closeCurrent(_:)), keyEquivalent: "w").target = self` |
| 444 | `.addItem(withTitle:` | `.addItem(withTitle:"Bring All to Front",action:#selector(NSApplication.arrangeInFront(_:)),keyEquivalent:"").target = NSApp` |
| 446 | `.addItem(withTitle:` | `.addItem(withTitle:"Juno Help",action:#selector(showHelp),keyEquivalent:"?").target = self` |

## Planning.swift

| Line | Control or interaction | Source excerpt |
| ---: | --- | --- |
| 228 | `Menu` | `Menu {` |
| 229 | `Button` | `Button("Reload saved planning") { Task { await load() } }.disabled(busy &#124;&#124; dirty)` |
| 230 | `Button` | `Button("Discard changes and reload") { Task { await load(discard: true) } }.disabled(busy) }` |
| 235 | `Button` | `Button("Save planning") { Task { await save() } }` |
| 241 | `Picker` | `Picker("Plan view", selection: $page) {` |
| 246 | `DatePicker` | `DatePicker("Starting", selection: $day, displayedComponents: .date)` |
| 290 | `Button` | `Button("Prioritize " + task.title) {` |
| 303 | `Button` | `Button("Review issue") { inspect(next) }` |
| 320 | `Button` | `Button("Review issue") { inspect(task) }` |
| 327 | `DisclosureGroup` | `DisclosureGroup("About these suggestions") {` |
| 332 | `Button` | `Button("Browse issues (\(plan.tasks.count))") { page = .issues }` |
| 333 | `DisclosureGroup` | `DisclosureGroup("Sources and availability limits") {` |
| 342 | `Button` | `Button("Open daily check-in") { store.section = "Check-in" }` |
| 363 | `Button` | `Button("Open TaskDock") { store.section = "TaskDock" }` |
| 366 | `TextField` | `TextField("Search issues by title or room", text: $taskSearch)` |
| 369 | `Picker` | `Picker("Status", selection: $taskFilter) {` |
| 406 | `Button` | `Button { inspected = expanded ? nil : task.id } label: {` |
| 433 | `Button` | `Button("Planning details") { choose(task) }` |
| 434 | `Button` | `Button("Clarify with Juno") { choose(task, guidedMode: true) }` |
| 435 | `Menu` | `Menu("More actions") {` |
| 436 | `Button` | `Button("Discuss estimate") {` |
| 439 | `Button` | `Button("Request worker update…") {` |
| 452 | `DisclosureGroup` | `DisclosureGroup("\(task.missing.count) details to confirm") {` |
| 459 | `DisclosureGroup` | `DisclosureGroup("Reviewed check-in sources") {` |
| 479 | `DisclosureGroup` | `DisclosureGroup("Staff workload") {` |
| 494 | `DisclosureGroup` | `DisclosureGroup("Planning settings and dated availability") {` |
| 499 | `Stepper` | `Stepper("\(record.reserve_minutes)", value: Binding(get: { self.record?.reserve_minutes ?? 240 }, set: { self.record?.reserve_minutes = $0; dirty = true }), in: 0...2400, step: 30)` |
| 504 | `Button` | `Button("Remove") { self.record?.windows.remove(at: index); dirty = true }` |
| 508 | `Picker` | `Picker("Window", selection: $windowKind) { Text("My work").tag("work"); Text("Room access").tag("room"); Text("Staff available").tag("staff") }.frame(width: 220)` |
| 509 | `TextField` | `TextField("Exact room or employee name", text: $windowName) }` |
| 511 | `DatePicker` | `DatePicker("Start", selection: $windowStart)` |
| 512 | `DatePicker` | `DatePicker("End", selection: $windowEnd)` |
| 513 | `Button` | `Button("Add confirmed window") {` |
| 565 | `.sheet` | `.sheet(isPresented:$showDeanDraft) { WeeklyDeanEditor(store:store,initialDay:DeanMeetingSchedule(now:Date()).week) }` |
| 566 | `.sheet` | `.sheet(isPresented: Binding(get:{ selected != nil },set:{ if !$0 { selected = nil } }),onDismiss:{ estimateTask?.cancel();estimating = false }) {` |
| 570 | `Button` | `Button(guided ? "Show all fields" : "Guide me through this") { guided.toggle();guideStep = 0 } }.padding(.horizontal,20).padding(.vertical,8)` |
| 575 | `Button` | `Button("Cancel",role:.cancel) { estimateTask?.cancel();estimating = false;selected = nil }` |
| 575 | `.keyboardShortcut` | `.keyboardShortcut(.cancelAction)` |
| 577 | `Button` | `Button("Back") { guideStep -= 1 } }` |
| 578 | `Button` | `Button("Next") { guideStep += 1 } }` |
| 579 | `Button` | `Button("Apply to draft") { if applyFacts() { estimateTask?.cancel();estimating = false;selected = nil } }` |
| 579 | `.keyboardShortcut` | `.keyboardShortcut(.defaultAction).disabled(store.offline &#124;&#124; estimating &#124;&#124; (guided && guideStep &lt; 5))` |
| 596 | `TextField` | `TextField("Estimated minutes — leave blank if unknown",text:$estimate).textFieldStyle(.roundedBorder)` |
| 600 | `TextField` | `TextField("Room — leave blank if not room-related or unknown",text:$facts.room).textFieldStyle(.roundedBorder)` |
| 601 | `Button` | `Button("Use suggested room: " + hint) { facts.room = hint };Text("Confirm that the suggested room is correct before applying it.").font(.caption) }` |
| 604 | `TextField` | `TextField("Possible employee — leave blank if not confirmed",text:$facts.employee).textFieldStyle(.roundedBorder)` |
| 608 | `TextField` | `TextField("Relevant experience or training",text:$facts.capability).textFieldStyle(.roundedBorder)` |
| 609 | `Toggle` | `Toggle("Confirmed able to work independently",isOn:$facts.independent)` |
| 610 | `Toggle` | `Toggle("Needs my supervision / collaboration",isOn:Binding(get:{facts.supervision ?? false},set:{facts.supervision = $0}))` |
| 614 | `TextField` | `TextField("Blocker — parts, approval, research or access",text:$facts.blocker).textFieldStyle(.roundedBorder)` |
| 615 | `TextField` | `TextField("Waiting on whom or what?",text:$facts.waiting_on).textFieldStyle(.roundedBorder)` |
| 616 | `TextField` | `TextField("Next step to unblock it",text:$facts.next_action).textFieldStyle(.roundedBorder)` |
| 636 | `TextField` | `TextField("Estimate (minutes)", text: $estimate);` |
| 636 | `TextField` | `TextField("Actual work (minutes, optional)", text: $actual) }` |
| 637 | `Button` | `Button("Suggest a duration range") {` |
| 649 | `Button` | `Button("Use midpoint in this draft") { estimate = String((suggestion.minimum + suggestion.maximum)/2) }` |
| 652 | `Toggle` | `Toggle("Dean request", isOn: $facts.dean)` |
| 653 | `Toggle` | `Toggle("Teaching or operations need", isOn: $facts.operational)` |
| 656 | `TextField` | `TextField("Room needing confirmed access", text: $facts.room)` |
| 657 | `Button` | `Button("Use suggested room: " + hint) { facts.room = hint } }` |
| 658 | `TextField` | `TextField("Possible employee", text: $facts.employee)` |
| 659 | `TextField` | `TextField("Confirmed relevant experience / capability", text: $facts.capability)` |
| 660 | `Toggle` | `Toggle("I confirm this employee can do this independently", isOn: $facts.independent)` |
| 661 | `Toggle` | `Toggle("Needs my supervision / collaboration", isOn: Binding(get:{facts.supervision ?? false},set:{facts.supervision = $0}))` |
| 664 | `TextField` | `TextField("Blocker / dependency (parts, approval, bill, research…)", text: $facts.blocker)` |
| 665 | `TextField` | `TextField("Waiting on whom or what?", text: $facts.waiting_on)` |
| 666 | `TextField` | `TextField("Next unblocking action", text: $facts.next_action)` |
| 667 | `TextField` | `TextField("Next check date, YYYY-MM-DD (optional)", text: $checkDate)` |
| 668 | `TextField` | `TextField("Where we stopped and how to resume", text: $facts.resume)` |
| 669 | `Button` | `Button("Remove saved details from draft",role:.destructive) { record?.tasks.removeAll { $0.task_id == facts.task_id }; selected = nil; dirty = true }.disabled(store.offline)` |
| 705 | `Button` | `Button("Discuss this detail") { clarify(question) }` |
| 709 | `DisclosureGroup` | `DisclosureGroup("Request details & source") {` |
| 944 | `DatePicker` | `DatePicker("Week of", selection: $day, displayedComponents: .date)` |
| 948 | `Menu` | `Menu("Draft actions", systemImage: "ellipsis.circle") {` |
| 949 | `Button` | `Button(saved.basis.meeting_window != nil ? "Prepare seven-day comparison" :` |
| 952 | `Button` | `Button("Compare saved copy", action: compare)` |
| 955 | `Button` | `Button("Show prepared comparison") { comparison = nil; showFresh = true }` |
| 958 | `Button` | `Button(showDetails ? "Hide source details" : "Show source details") { showDetails.toggle() }` |
| 971 | `DisclosureGroup` | `DisclosureGroup(isExpanded: $showDetails) {` |
| 1017 | `TextEditor` | `TextEditor(text: Binding(get: { text }, set: { text = $0; dirty = true; recoverable() }))` |
| 1037 | `Button` | `Button("Prepare draft", action: prepare).disabled(store.offline)` |
| 1039 | `Button` | `Button("Try again") { Task { await load() } }` |
| 1060 | `Button` | `Button(comparisonOpen ? "Back to briefing" : "Close") {` |
| 1064 | `.keyboardShortcut` | `.keyboardShortcut(.cancelAction)` |
| 1067 | `Button` | `Button("Keep my writing") { adoptSavedCopy(comparison, keepWriting: true) }.disabled(pending != nil)` |
| 1068 | `Button` | `Button("Use saved text") { adoptSavedCopy(comparison, keepWriting: false) }.disabled(pending != nil)` |
| 1070 | `Button` | `Button("Copy briefing") {` |
| 1075 | `Button` | `Button("Retry save", action: retry).disabled(busy &#124;&#124; store.offline)` |
| 1077 | `Button` | `Button("Preview") { editing = false }.disabled(busy)` |
| 1079 | `Button` | `Button("Edit briefing") { editing = true }.disabled(busy)` |
| 1082 | `Button` | `Button("Save draft", action: save)` |
| 1120 | `.alert` | `.alert("Keep this unsaved writing for later?",isPresented:$confirmClose) {` |
| 1120 | `Button` | `Button("Keep local recovery and close") { recoverable();dismiss() };` |
| 1120 | `Button` | `Button("Return to draft",role:.cancel){} } message:{Text("Your work-Mac draft changes only after Save succeeds. A local recovery copy keeps this writing for the next time you open this ` |
| 1336 | `Toggle` | `Toggle("Prepare automatically at 9:00 AM Central on Thursdays",isOn:$store.deanAutomatic)` |
| 1341 | `Button` | `Button("Correct last meeting…") { actual=overridden ?? schedule.previous;correcting=true }.disabled(store.deanPreparing)` |
| 1345 | `Button` | `Button("Open this week’s draft…") { open() }` |
| 1346 | `Button` | `Button("Meeting follow-up…") { followUp = true }` |
| 1348 | `Button` | `Button("Refresh sources and prepare now") { Task { await store.prepareDeanMeeting(automatic:false) } }` |
| 1355 | `.sheet` | `.sheet(isPresented: $followUp) { DeanFollowUpEditor(store: store, onSave: refreshPlan) }` |
| 1356 | `.sheet` | `.sheet(isPresented:$correcting) {` |
| 1360 | `DatePicker` | `DatePicker("Last meeting",selection:$actual,in:...Date(),displayedComponents:[.date,.hourAndMinute])` |
| 1362 | `Button` | `Button("Cancel",role:.cancel) { correcting=false }` |
| 1362 | `.keyboardShortcut` | `.keyboardShortcut(.cancelAction)` |
| 1363 | `Button` | `Button("Use usual Thursday") { store.deanOverride=nil;store.deanOverrideWeek="";correcting=false } }` |
| 1365 | `Button` | `Button("Use this meeting") { store.deanOverride=actual;store.deanOverrideWeek=schedule.key;correcting=false }` |
| 1366 | `.keyboardShortcut` | `.keyboardShortcut(.defaultAction)` |
| 1437 | `DatePicker` | `DatePicker("Meeting date", selection: $day, displayedComponents: .date)` |
| 1446 | `TextEditor` | `TextEditor(text: $notes)` |
| 1451 | `Button` | `Button("Find Dean requests") { Task { await extract() } }` |
| 1453 | `Button` | `Button("Add request") { items.append(DeanFollowUpItem()) }.disabled(items.count &gt;= 24)` |
| 1465 | `Button` | `Button("Close") { if changed { confirmClose = true } else { dismiss() } }` |
| 1466 | `.keyboardShortcut` | `.keyboardShortcut(.cancelAction).disabled(working)` |
| 1470 | `Button` | `Button("Save follow-up") { Task { await save() } }` |
| 1471 | `.keyboardShortcut` | `.keyboardShortcut(.defaultAction).disabled(!canSave &#124;&#124; working &#124;&#124; store.offline)` |
| 1478 | `.confirmationDialog` | `.confirmationDialog("Discard unsaved follow-up changes?", isPresented: $confirmClose) {` |
| 1479 | `Button` | `Button("Discard changes", role: .destructive) { dismiss() }` |
| 1480 | `Button` | `Button("Keep editing", role: .cancel) {}` |
| 1553 | `TextField` | `TextField("Request", text: $item.title)` |
| 1555 | `TextField` | `TextField("Owner", text: $item.owner)` |
| 1556 | `TextField` | `TextField("Deadline or timing", text: $item.timing)` |
| 1558 | `TextField` | `TextField("Waiting on", text: $item.waiting_on)` |
| 1559 | `TextField` | `TextField("Exact quote from your notes", text: $item.quote, axis: .vertical)` |
| 1566 | `Button` | `Button("Unlink") { item.task_id = nil; item.workspace_id = nil }` |
| 1574 | `TextField` | `TextField("Search existing TaskDock cards", text: $search)` |
| 1575 | `Menu` | `Menu(matches.isEmpty ? "Link card" : "Choose card") {` |
| 1577 | `Button` | `Button(task.title + " · " + task.id.suffix(8)) {` |
| 1587 | `Toggle` | `Toggle("Closed for briefing", isOn: $item.closed)` |
| 1589 | `Button` | `Button("Remove request", role: .destructive, action: remove)` |
| 1609 | `Toggle` | `Toggle("Prepare Fridays at 9:00 AM Central", isOn: $store.chairsAutomatic)` |
| 1614 | `Button` | `Button("Review email draft…") { showDraft = true }` |
| 1616 | `Button` | `Button("Prepare this week’s draft") { Task { await store.prepareChairsDraft(automatic: false) } }` |
| 1622 | `.sheet` | `.sheet(isPresented: $showDraft) { ChairsReportEditor(store: store) }` |
| 1655 | `DatePicker` | `DatePicker("Reporting week", selection: $day, in: ...Date(), displayedComponents: .date)` |
| 1659 | `Picker` | `Picker("Recipient", selection: $recipient) {` |
| 1668 | `DisclosureGroup` | `DisclosureGroup("Source coverage") {` |
| 1674 | `TextField` | `TextField("Subject", text: $subject).textFieldStyle(.roundedBorder).disabled(store.offline &#124;&#124; busy)` |
| 1675 | `TextEditor` | `TextEditor(text: $draftBody).font(.body).accessibilityLabel("Department chairs email body")` |
| 1684 | `Button` | `Button("Close") { if changed { confirmClose = true } else { dismiss() } }` |
| 1685 | `.keyboardShortcut` | `.keyboardShortcut(.cancelAction).disabled(busy)` |
| 1687 | `Button` | `Button("Copy email") {` |
| 1692 | `Button` | `Button("Save edits") { Task { await save() } }` |
| 1693 | `.keyboardShortcut` | `.keyboardShortcut(.defaultAction).disabled(!ready &#124;&#124; !changed &#124;&#124; busy &#124;&#124; store.offline)` |
| 1699 | `.confirmationDialog` | `.confirmationDialog("Discard unsaved email edits?", isPresented: $confirmClose) {` |
| 1700 | `Button` | `Button("Discard edits", role: .destructive) { dismiss() }` |
| 1701 | `Button` | `Button("Keep editing", role: .cancel) {}` |

## Schedules.swift

| Line | Control or interaction | Source excerpt |
| ---: | --- | --- |
| 50 | `DatePicker` | `DatePicker(title,selection:Binding(get:{formatter.date(from:value) ?? Date()},set:{value = formatter.string(from:$0)}),displayedComponents:.hourAndMinute)` |
| 115 | `Button` | `Button("Reload saved schedules") { Task { await load() } }.disabled(dirty &#124;&#124; busy)` |
| 116 | `Button` | `Button("Save schedules") { Task { await save() } }.disabled(!dirty &#124;&#124; busy &#124;&#124; store.offline)` |
| 117 | `Button` | `Button("Discard draft") { Task { await load() } } }` |
| 123 | `Picker` | `Picker("Schedule view", selection:$scheduleView) {` |
| 132 | `DatePicker` | `DatePicker("Compare date",selection:$comparisonDate,displayedComponents:.date)` |
| 134 | `Button` | `Button("Previous day") { moveComparisonDay(-1) }` |
| 135 | `Button` | `Button("Today") { comparisonDate = Date() }` |
| 136 | `Button` | `Button("Next day") { moveComparisonDay(1) }` |
| 149 | `Button` | `Button("Edit schedules and people") { scheduleView = "List & edit" }` |
| 154 | `Button` | `Button("Edit") { person = p;editingPersonName = p.name;limitHours = String(p.weekly_limit_minutes/60);desiredHours = p.desired_minutes.map { String($0/60) } ?? "";personEditor = true } ` |
| 156 | `Button` | `Button("Add person / candidate") { person = StaffSchedule();editingPersonName = nil;limitHours = "20";desiredHours = "";personEditor = true }` |
| 162 | `Button` | `Button("Edit") { rule = r;ruleEditor = true };` |
| 162 | `Button` | `Button("Remove rule") { self.record?.rules.removeAll { $0.id == r.id };dirty = true } }` |
| 164 | `Button` | `Button("Add recurring schedule") { rule = RecurringSchedule();ruleEditor = true }` |
| 171 | `Button` | `Button("Edit") { exception = e;exceptionEditor = true };` |
| 171 | `Button` | `Button("Remove exception") { self.record?.exceptions.removeAll { $0.id == e.id };dirty = true } }` |
| 173 | `Button` | `Button("Add closure / shift exception") { exception = DailyScheduleException();exceptionEditor = true }` |
| 181 | `Button` | `Button("Release hold") {` |
| 192 | `.sheet` | `.sheet(isPresented:$ruleEditor) { ruleForm }` |
| 193 | `.sheet` | `.sheet(isPresented:$personEditor) { personForm }` |
| 194 | `.sheet` | `.sheet(isPresented:$exceptionEditor) { exceptionForm }` |
| 204 | `Picker` | `Picker("Kind",selection:$rule.kind) { Text("My work hours").tag("work");Text("Building access").tag("room");Text("Classroom occupied").tag("classroom_busy");Text("Staff shift").tag("sta` |
| 205 | `TextField` | `TextField("Room, employee or course name",text:$rule.name)` |
| 206 | `TextField` | `TextField("Room location",text:$rule.location) }` |
| 207 | `DatePicker` | `DatePicker("First date",selection:scheduleDayBinding($rule.start_date),displayedComponents:.date);` |
| 207 | `DatePicker` | `DatePicker("Last date",selection:scheduleDayBinding($rule.end_date),displayedComponents:.date) }` |
| 208 | `Toggle` | `Toggle(weekdays[d],isOn:Binding(get:{rule.days.contains(d)},set:{ yes in if yes { rule.days.append(d) } else { rule.days.removeAll { $0 == d } } })).toggleStyle(.checkbox) } }` |
| 210 | `TextField` | `TextField("Timezone",text:$rule.timezone)` |
| 215 | `Button` | `Button("Cancel") { ruleEditor = false };Spacer();` |
| 215 | `Button` | `Button("Apply to draft") { record?.rules.removeAll { $0.id == rule.id };record?.rules.append(rule);dirty = true;ruleEditor = false }.disabled(store.offline &#124;&#124; rule.days.isEmpty &#124;&#124; sched` |
| 220 | `TextField` | `TextField("Name",text:$person.name).disabled(editingPersonName != nil)` |
| 221 | `Picker` | `Picker("Status",selection:$person.status) { Text("Active").tag("active");Text("Schedule unsettled").tag("tentative");Text("Candidate — not hired").tag("candidate") }` |
| 222 | `TextField` | `TextField("Funded weekly limit, whole hours",text:$limitHours).frame(width:100) }` |
| 223 | `TextField` | `TextField("Agreed hours, optional",text:$desiredHours).frame(width:100) }` |
| 224 | `TextField` | `TextField("Notes / unresolved details",text:$person.notes)` |
| 227 | `Button` | `Button("Cancel") { personEditor = false };Spacer();` |
| 227 | `Button` | `Button("Apply to draft") {` |
| 237 | `Picker` | `Picker("Kind",selection:$exception.kind) { Text("My hours").tag("work");Text("Building access").tag("room");Text("Staff shift").tag("staff_available");Text("Class occupancy").tag("class` |
| 238 | `TextField` | `TextField("Exact room or employee name",text:$exception.name);` |
| 238 | `DatePicker` | `DatePicker("Date",selection:scheduleDayBinding($exception.day),displayedComponents:.date)` |
| 239 | `Toggle` | `Toggle(exception.kind == "classroom_busy" ? "No classes on this date" : "Unavailable / closed on this date",isOn:$exception.closed)` |
| 241 | `TextField` | `TextField("Reason / note",text:$exception.note)` |
| 245 | `Button` | `Button("Cancel") { exceptionEditor = false };Spacer();` |
| 245 | `Button` | `Button("Apply to draft") { record?.exceptions.removeAll { $0.id == exception.id };record?.exceptions.append(exception);dirty = true;exceptionEditor = false }.disabled(store.offline &#124;&#124; e` |
| 271 | `Picker` | `Picker("Room",selection:$room) { Text("Choose room").tag("");ForEach(rosterRooms,id:\.self) { Text($0).tag($0) } }` |
| 272 | `Picker` | `Picker("Person",selection:$employee) { Text("Me").tag("");ForEach(rosterPeople) { Text($0.name+" • "+$0.status).tag($0.name) } }` |
| 275 | `TextField` | `TextField("Duration (minutes)", text: $minutes).frame(width: 65)` |
| 278 | `Toggle` | `Toggle("Needs my supervision / collaboration",isOn:$supervision) }` |
| 279 | `Button` | `Button("Find possible windows") { Task { await find() } }.disabled(busy &#124;&#124; store.offline);` |
| 279 | `Button` | `Button("Manage schedules") { store.section = "Schedules" };if busy { ProgressView().controlSize(.small) } }` |
| 285 | `Picker` | `Picker("Issue to reserve",selection:$taskID) { Text("Explore windows only").tag("");ForEach(tasks) { Text($0.title).tag($0.id) } }` |
| 290 | `Button` | `Button("Reserve reviewed task") {` |
| 299 | `DisclosureGroup` | `DisclosureGroup("Availability sources and limits") {` |
| 384 | `Picker` | `Picker(byRoom ? "Room" : "Person",selection:Binding(get:{selection},set:{selected = $0; selectionBinding?.wrappedValue = $0})) {` |
| 389 | `Button` | `Button("Previous week") { moveWeek(-7) }` |
| 390 | `Button` | `Button("This week") { anchor = Date();weekBinding?.wrappedValue = anchor }` |
| 391 | `Button` | `Button("Next week") { moveWeek(7) }` |
| 395 | `DatePicker` | `DatePicker("Week containing",selection:Binding(get:{weekBinding?.wrappedValue ?? anchor},set:{anchor = $0;weekBinding?.wrappedValue = $0}),displayedComponents:.date).environment(\.timeZ` |
| 402 | `DisclosureGroup` | `DisclosureGroup("Schedule notes") { Text(p.notes).font(.caption).foregroundStyle(.secondary) } }` |
| 490 | `DisclosureGroup` | `DisclosureGroup("Source dates") { ForEach(result.source_notices,id:\.self) { Text($0).font(.caption) } }` |
| 492 | `Button` | `Button("Review task in Plan") { store.section = "Plan" }` |
| 494 | `Button` | `Button("Refresh matching times") { Task { await load() } }.disabled(loading &#124;&#124; store.offline &#124;&#124; dirty)` |
| 561 | `TextField` | `TextField("Search issues",text:$search).textFieldStyle(.roundedBorder)` |
| 562 | `Toggle` | `Toggle("Show all rooms / unlinked issues",isOn:$showAll)` |
| 563 | `Button` | `Button("Reload saved issues") { Task { await load() } }.disabled(busy)` |
| 575 | `Button` | `Button("Open planning details") { store.planningTaskID = task.id;store.section = "Plan" } }` |
| 577 | `DisclosureGroup` | `DisclosureGroup("Shared TaskDock request information") { TaskDockRequestFacts(task:task) }` |
| 578 | `DisclosureGroup` | `DisclosureGroup("Planning context & blockers") {` |
| 587 | `DisclosureGroup` | `DisclosureGroup("TaskDock record details") { TaskDockDetails(task:task,info:snapshot.info) }` |

## Shared.swift

| Line | Control or interaction | Source excerpt |
| ---: | --- | --- |
| 553 | `Button` | `Button("Import a new pairing file…") { importInvitation() }.disabled(busy &#124;&#124; store.syncing)` |
| 554 | `Button` | `Button(store.syncing ? "Synchronizing…" : "Reconnect and synchronize") { store.reconnectShared() }.disabled(store.syncing)` |
| 560 | `Button` | `Button("Compare with current work Mac record") { review(edit) }.disabled(busy &#124;&#124; store.syncing)` |
| 568 | `Button` | `Button("Apply queued changes to the reviewed revision") { resolve(edit,keepLaptop:true) }.disabled(reviewed == nil)` |
| 569 | `Button` | `Button("Use work Mac version for this record…",role:.destructive) { discardRecord = true }` |
| 571 | `Button` | `Button("Preserve laptop memory as a new record") {` |
| 583 | `DisclosureGroup` | `DisclosureGroup(edit.kind + " · " + edit.createdAt.formatted()) {` |
| 587 | `Button` | `Button("Export queued edits…") {` |
| 593 | `Button` | `Button("Discard queued edits and use the work Mac's versions…",role:.destructive) { discard = true }` |
| 595 | `Button` | `Button("Use standalone Juno on this Mac") {` |
| 610 | `Button` | `Button(host.enabled ? "Stop hosting" : "Host Juno on this Mac") { toggleHost(!host.enabled) }.disabled(busy)` |
| 611 | `Button` | `Button("Create laptop pairing file…") { exportInvitation() }.disabled(busy &#124;&#124; !host.enabled)` |
| 615 | `Button` | `Button("Import work Mac pairing file…") { importInvitation() }.disabled(busy &#124;&#124; host?.enabled == true)` |
| 620 | `Button` | `Button("Revoke access") {` |
| 630 | `.alert` | `.alert("Use the work Mac version for this record?",isPresented:$discardRecord) {` |
| 631 | `Button` | `Button("Keep laptop edits",role:.cancel) {}` |
| 632 | `Button` | `Button("Use work Mac version",role:.destructive) {` |
| 636 | `.alert` | `.alert("Discard all queued edits?",isPresented:$discard) {` |
| 637 | `Button` | `Button("Keep edits",role:.cancel) {}` |
| 638 | `Button` | `Button("Discard queued edits",role:.destructive) {` |

## TaskDock.swift

| Line | Control or interaction | Source excerpt |
| ---: | --- | --- |
| 178 | `Button` | `Button("Refresh from TaskDock") { reviewing = nil;refresh() }.disabled(busy &#124;&#124; !store.connected); if busy { ProgressView().controlSize(.small) } }` |
| 179 | `DisclosureGroup` | `DisclosureGroup("TaskDock connection settings",isExpanded:$settingsExpanded) {` |
| 186 | `TextField` | `TextField("http://127.0.0.1:8100", text: $origin)` |
| 191 | `SecureField` | `SecureField("Paste token here", text: $token)` |
| 198 | `Button` | `Button("Connect / refresh snapshot") { reviewing = nil; refresh() }.disabled(busy &#124;&#124; !store.connected)` |
| 199 | `Button` | `Button("Forget saved token…",role:.destructive) { forgetting = true }.disabled(busy)` |
| 206 | `Button` | `Button("Use this workspace and installation") { refresh(accept: true) }.disabled(busy &#124;&#124; origin.trimmingCharacters(in: CharacterSet(charactersIn: "/")) != reviewOrigin)` |
| 215 | `DisclosureGroup` | `DisclosureGroup("Shared information groups") { Text(snapshot.info.sharing?.pretty ?? "Unknown selection").font(.caption).textSelection(.enabled) }` |
| 226 | `DisclosureGroup` | `DisclosureGroup("TaskDock source freshness (separate from Juno’s read time)") { Text(snapshot.sources.pretty).font(.caption.monospaced()).textSelection(.enabled).frame(maxHeight: 110) }` |
| 229 | `TextField` | `TextField("Filter saved tasks", text: $search).focused($searchFocused).onReceive(NotificationCenter.default.publisher(for:Notification.Name("JunoFind"))) { _ in if store.section == "Tas` |
| 230 | `List` | `List(selection: $selected) {` |
| 241 | `Button` | `Button("Request worker update…") {store.workerTaskID=task.id;store.section="Workers"}.disabled(store.sharedProfile != nil)` |
| 242 | `Button` | `Button("Plan this task in Juno") { store.planningTaskID = task.id; store.section = "Plan" }.disabled(["completed","archived","done"].contains(task.text("behavior") ?? ""))` |
| 245 | `Button` | `Button("Read updates") { readHistory(task: task, kind: "updates") }.disabled(busy) }` |
| 246 | `Button` | `Button("Read activity") { readHistory(task: task, kind: "activity") }.disabled(busy) }` |
| 254 | `DisclosureGroup` | `DisclosureGroup("Original recorded fields") { Text(task.fields.pretty).font(.caption.monospaced()).textSelection(.enabled) }` |
| 259 | `DisclosureGroup` | `DisclosureGroup("Field definitions", isExpanded: $definitions) { ScrollView { Text(snapshot.info.definitions.pretty).font(.caption.monospaced()).textSelection(.enabled) }.frame(maxHeigh` |
| 265 | `.alert` | `.alert("Forget TaskDock access on this Mac?",isPresented:$forgetting) {` |
| 266 | `Button` | `Button("Cancel",role:.cancel) { }` |
| 267 | `Button` | `Button("Forget token",role:.destructive) {` |
| 350 | `DisclosureGroup` | `DisclosureGroup("Saved source comment sample (\(comments.count))") {` |

## Workers.swift

| Line | Control or interaction | Source excerpt |
| ---: | --- | --- |
| 44 | `TextField` | `TextField("Search tasks by title, room, equipment or parent",text:$search).textFieldStyle(.roundedBorder).focused($searching).accessibilityLabel("Search tasks to share");if !search.isEm` |
| 44 | `Button` | `Button("Clear search"){search="";searching=true}}}` |
| 46 | `List` | `List(selection:Binding&lt;String?&gt;(get:{selected.isEmpty ? nil:selected},set:{selected=$0 ?? ""})){` |
| 135 | `Button` | `Button("Reload inbox"){perform{try await load()}}.disabled(busy&#124;&#124;sheet != nil)}` |
| 139 | `DisclosureGroup` | `DisclosureGroup("Worker access · " + (data.enabled ? (data.host.running ? "Enabled" : "Unavailable") : "Disabled")) {` |
| 143 | `Button` | `Button("Copy portal address"){copy(data.host.address+"/worker")}}` |
| 145 | `Button` | `Button(data.enabled ? "Disable worker access…" : "Enable worker access…"){confirmation=data.enabled ? "disable" : "enable"}.disabled(busy &#124;&#124; (!data.enabled && !data.host.ready))` |
| 147 | `Picker` | `Picker("Saved schedule person",selection:$person){Text("Choose a person").tag("");ForEach(data.people,id:\.self){Text($0).tag($0)}};` |
| 147 | `Button` | `Button("Add portal identity"){perform{_ = try await store.request("/v1/workers",method:"POST",body:["name":person]);try await load()}}.disabled(person.isEmpty&#124;&#124;busy)}` |
| 148 | `Button` | `Button("Create invitation…"){chosenWorker=worker.id;link=nil;sheet=WorkerSheet(kind:"invite")}.disabled(!data.enabled &#124;&#124; !data.host.running&#124;&#124;busy);` |
| 148 | `Button` | `Button("Revoke access…"){targetID=worker.id;confirmation="worker"}.disabled(busy)}}}` |
| 151 | `Picker` | `Picker("TaskDock identity",selection:Binding(get:{worker.assignment_keys?.first ?? ""},set:{key in perform{_ = try await store.request("/v1/workers/"+worker.id+"/assignment",method:"PUT` |
| 156 | `Button` | `Button("Request help on a task…"){openShare()}.disabled(data.workers.filter{$0.active}.isEmpty&#124;&#124;snapshot==nil&#124;&#124;busy)` |
| 157 | `DisclosureGroup` | `DisclosureGroup("Shared tasks (latest 200)"){ForEach(data.grants){grant in HStack {VStack(alignment:.leading){Text(grant.excerpt["title"] ?? "Task excerpt withdrawn");Text((data.workers` |
| 157 | `Button` | `Button("Copy task link"){copy(data.host.address+"/worker#task="+grant.id)}.disabled(!data.enabled &#124;&#124; !data.host.running);if grant.mode != "assigned"{` |
| 157 | `Button` | `Button("Revoke task…"){targetID=grant.id;confirmation="grant"}}}}};if data.more_grants {Text("Older grants are not listed here. Revoke the worker identity to withdraw all of their acces` |
| 161 | `DisclosureGroup` | `DisclosureGroup("Repair history & patterns · \(history.reviewed_reports) included reports") {` |
| 170 | `DisclosureGroup` | `DisclosureGroup("Supporting reports"){ForEach(group.evidence){evidence in` |
| 170 | `Button` | `Button(evidence.work_date+" · "+evidence.summary){perform{let report=try await store.decode(WorkerReportRecord.self,"/v1/workers/reports/"+evidence.id);if !reports.contains(where:{$0.id` |
| 173 | `Button` | `Button("Show more repair groups"){historyLimit+=20}}` |
| 179 | `TextField` | `TextField("Find worker, task or room",text:$query).textFieldStyle(.roundedBorder);` |
| 179 | `Picker` | `Picker("Show",selection:$filter){Text("Unread").tag("unread");Text("Needs follow-up").tag("needs_follow_up");Text("All updates").tag("all")}` |
| 180 | `List` | `List(selection:$selected){ForEach(visible){r in VStack(alignment:.leading,spacing:4){Text(r.worker_name+" · "+r.title).lineLimit(2);Text(r.data.status.replacingOccurrences(of:"_",with:"` |
| 181 | `Button` | `Button("Load older updates"){perform{let page=try await store.decode(WorkerReceiptPage.self,"/v1/workers/reports?offset=\(reports.count)");reports+=page.items.filter{r in !reports.conta` |
| 187 | `.sheet` | `.sheet(item:$sheet,onDismiss:{preview=nil;link=nil;issue=nil}){request in editor(request).id(request.id)}` |
| 188 | `.alert` | `.alert(alertTitle,isPresented:Binding(get:{confirmation != nil},set:{if !$0{confirmation=nil}})) {` |
| 189 | `Button` | `Button("Cancel",role:.cancel){confirmation=nil}` |
| 190 | `Button` | `Button("Confirm"){let action=confirmation;confirmation=nil;perform{` |
| 210 | `DisclosureGroup` | `DisclosureGroup("What was shared"){if r.shared_excerpt.isEmpty {Text("Task excerpt expired or withdrawn.")}else{ForEach(r.shared_excerpt.keys.sorted(),id:\.self){key in Text(key.replaci` |
| 211 | `Button` | `Button("Review update…"){prepareReview(r);sheet=WorkerSheet(kind:"review",report:r)};` |
| 211 | `Button` | `Button("Review planning changes…"){perform{plan=try await store.decode(PlanningRecord.self,"/v1/planning");applyFields=[];sheet=WorkerSheet(kind:"apply",report:r)}}.disabled(!r.grant_ac` |
| 211 | `Button` | `Button("Copy TaskDock summary"){copy("Worker report — "+r.worker_name+"\n"+r.title+"\n"+r.data.work_date+" · "+r.data.status+"\n"+r.data.text+"\nBlockers: "+r.data.blocker_state+" "+r.d` |
| 214 | `Button` | `Button("Delete retained report…",role:.destructive){targetID=r.id;confirmation="delete"}.font(.caption)` |
| 220 | `Button` | `Button("Create private invitation"){perform{link=try await store.decode(WorkerLink.self,"/v1/workers/"+chosenWorker+"/invitations",method:"POST",body:[:])}}}}` |
| 226 | `Button` | `Button("Copy task link"){copy((overview?.host.address ?? "")+"/worker#task="+grant.id)}.disabled(overview?.host.running != true)` |
| 228 | `Button` | `Button("Request help from another worker…"){openShare()}` |
| 233 | `Button` | `Button("Back to task"){self.preview=nil};` |
| 233 | `Button` | `Button("Create task link"){perform{link=try await store.decode(WorkerLink.self,"/v1/workers/grants",method:"POST",body:grantBody());try await load()}}.disabled(overview?.enabled != true` |
| 235 | `Picker` | `Picker("Worker",selection:$chosenWorker){Text("Choose worker").tag("");ForEach(overview?.workers.filter{$0.active} ?? []){Text($0.name).tag($0.id)}}` |
| 238 | `TextField` | `TextField("Instructions for this worker (optional)",text:$instructions).textFieldStyle(.roundedBorder);` |
| 238 | `Stepper` | `Stepper("Share for \(shareDays) days",value:$shareDays,in:1...30)` |
| 244 | `Toggle` | `Toggle(isOn:binding($applyFields,key)){VStack(alignment:.leading){Text(label);Text("Current: "+currentValue(r,key)+" → Reported: "+value).font(.caption).foregroundStyle(.secondary)}}}}` |
| 246 | `Button` | `Button("Save selected planning changes"){perform{_ = try await store.request("/v1/workers/reports/"+r.id+"/apply",method:"POST",body:["expected_revision":r.revision,"expected_planning_r` |
| 248 | `Picker` | `Picker("Outcome",selection:$outcome){Text("Reviewed").tag("reviewed");Text("Needs follow-up").tag("needs_follow_up");if r.data.status=="reported_complete"{Text("Completion verified by m` |
| 248 | `TextField` | `TextField("Private review note (optional)",text:$reviewNote).textFieldStyle(.roundedBorder)` |
| 250 | `Toggle` | `Toggle("Use this report for repair history and future estimates",isOn:$includeRepair)` |
| 253 | `TextField` | `TextField("Confirmed room (or supply equipment)",text:$repairRoom).textFieldStyle(.roundedBorder)` |
| 254 | `TextField` | `TextField("Equipment / asset identifier",text:$repairEquipment).textFieldStyle(.roundedBorder)` |
| 255 | `Picker` | `Picker("Repair type",selection:$repairCategory){Text("Printer / cutter").tag("printer");Text("Network / offline computer").tag("offline computer");Text("Driver / display / input").tag("` |
| 256 | `TextField` | `TextField("Repair / symptom summary",text:$repairSummary).textFieldStyle(.roundedBorder)` |
| 257 | `Toggle` | `Toggle("Reported minutes cover the complete repair",isOn:$completeEffort).disabled(r.data.actual_minutes==nil)` |
| 261 | `Button` | `Button("Save review"){perform{_ = try await store.request("/v1/workers/reports/"+r.id+"/review",method:"POST",body:reviewBody(r));sheet=nil;try await load()}}.disabled(busy &#124;&#124; (includeR` |
| 264 | `Button` | `Button("Copy private link"){copy(link.url)};Text("Share it yourself with the intended worker. Nothing has been sent.").font(.caption)}` |
| 267 | `Button` | `Button("Preview worker view"){perform{preview=try await store.decode(WorkerGrantPreview.self,"/v1/workers/grants/preview",method:"POST",body:grantBody())}}.disabled(chosenWorker.isEmpty` |
| 267 | `Button` | `Button(link==nil ? "Cancel" : "Done"){sheet=nil}` |
| 267 | `.keyboardShortcut` | `.keyboardShortcut(.cancelAction).disabled(busy)}` |

## Worker portal

| Line in index.html | Element | ID, type or mode |
| ---: | --- | --- |
| 3 | `button` | `signout` |
| 5 | `button` | `retry` |
| 6 | `button` | `reconnect` |
| 6 | `button` | `task` |
| 6 | `button` | `shift` |
| 6 | `button` | `unexpected` |
| 7 | `form` | `report` |
| 7 | `select` | `task` |
| 8 | `input` | `work-date` |
| 9 | `textarea` | `work-text` |
| 10 | `select` | `state` |
| 11 | `input` | `actual` |
| 11 | `input` | `remaining` |
| 13 | `select` | `blocker-state` |
| 14 | `textarea` | `blocker` |
| 15 | `textarea` | `next` |
| 16 | `textarea` | `handoff` |
| 17 | `input` | `location` |
| 18 | `select` | `correction` |
| 20 | `button` | `submit` |
| 21 | `button` | `back` |
| 21 | `button` | `submit` |
| 22 | `button` | `another` |

The portal also renders state and options from `worker_web/app.js`. The acceptance pass must exercise generated options, system window controls, dynamic menus and OS dialogs.
