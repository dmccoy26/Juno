# Mission 17 — start small and return after interruptions

Status: started November 18, 2026. Dan selected getting started and returning after interruptions as the first priorities. Keep 0.2.X increments, preserve existing records and laptop pairing, and do not push to GitHub.

## First shipping increment: 0.2.27 / build 73

Put one personal work bookmark at the top of Today. Dan chooses the work; Juno does not rank competing priorities or silently start a TaskDock task. The bookmark records a small first action, a concrete finish point, where work stopped and any blocker. Existing reviewed planning notes can seed a step after Dan selects an exact saved issue. A tiny editable starting-step template works without LM Studio.

- **Help me get started** opens a short form. A title, first action and finish point are required. **Start this** saves the step as working. Starting different work explicitly parks the previous step without losing its notes.
- **I was interrupted** saves the current step immediately, keeping its action and finish point. An optional stopping note can be added afterward, so urgent classroom problems do not require filling out a form first.
- **Help me restart** offers a smaller step, a recorded blocker, or deliberately parking the current work and switching. **Resume this step** returns to the saved action. **Step finished** records completion of this personal step, without changing TaskDock or asserting equipment recovery.
- Parked bookmarks remain available for deliberate resumption. Finished steps retain their records. Nothing is automatically purged to make room.

Use a separate owner-private store rather than operational evidence, chat prompts or an imported task status. There is no diagnosis field, model-health context, automatic email/report addition or university-source write. Meeting mode hides the work bookmark and recovered draft. This increment adds no timer, repeated alert, notification schedule or automatic prioritization.

## Cross-Mac and recovery contract

The work Mac stores the canonical bookmark. A connected paired laptop can read and explicitly update its owner's step through narrowly permitted endpoints. A dated offline copy can display the saved bookmark. Offline mutation is disabled in this increment and explained in the UI; no false queued-edit claim or replacement pairing is introduced. Memory/diary offline queues remain unchanged.

Owner-level optimistic revisions prevent two Macs from overwriting each other's notes. A durable operation ID makes a lost-response retry idempotent. Stale drafts keep the local text and require a comparison with the latest saved bookmark before saving again. Draft recovery is scoped to owner, editor mode and bookmark. Cancel can retain the local draft or explicitly discard that draft; neither choice deletes canonical bookmarks. Existing identities, source settings, drafts, routines and receipts are unchanged by migration.

## Verification and acceptance

1. Use disposable PostgreSQL for start/interruption/smaller-step/resume/finish, park-and-switch, reconnect/replay, concurrent revisions, owner/device isolation and dated offline-copy projection.
2. Verify TaskDock references against the exact saved snapshot; stale references fail without losing typed text. Confirm no task, diary, report or upstream mutation occurs as a side effect.
3. Test the actual native draft/first-step helpers, recovery scope, Meeting-mode gates, laptop/offline controls and readable layout at normal Air-sized bounds. Test keyboard saving and cancellation without using live classroom records.
4. Build and verify a relocated standalone 0.2.27 package. Make a restore-tested encrypted backup and capture record/device/HTTPS identities before installation. Verify additive migration preserves every old record projection and existing pairing, then reopen the desktop sync host.
5. Record native/fixture results separately from a physical Air check. VoiceOver remains waived. A physical new laptop result must not be inferred from backend or cache tests.

## Reassess after Dan uses the first increment

Ask whether choosing one small action makes starting easier and whether the bookmark makes returning after real interruptions easier. Saved start/resume timestamps describe app actions, not productivity or medical outcomes. Record Dan's feedback separately from test results. Adjust wording and the size of first steps before adding more controls.

Later Mission 17 candidates: optional 15–25-minute focus periods, quick capture that returns to the active step, selective transition reminders with walking/setup time, quiet periods and a midday reset that explicitly parks/defer work displaced by urgent issues. Use existing calendar/capacity features and reviewed preferences. These are future increments, not enabled by 0.2.27.


## 0.2.27 implementation and acceptance in progress

Implemented an additive schema-0020 store for work bookmarks and durable action receipts, separate from operational evidence and report/model context. Today now leads with the chosen first action and finish point. Existing TaskDock/planning notes can seed an explicitly selected issue; changing a source selection retains nonempty typed notes. Connected laptop access is narrowly permitted; the offline cache contains the dated bookmark, while mutation stays disabled offline or while memory/diary edits await sync.

The full backend suite passed **449 tests**, followed by an additional focused exact-source-reference test. The actual JunoStore offline regression passed, including reading a cached bookmark and rejecting its mutation without entering the existing memory/diary queue. Actual native small-step/access/recovery checks passed. The initial package passed its native build and is being verified, with final refinements following the walkthrough.

The disposable native walkthrough exercised Command-S start/save, one-click interruption, Cancel/keep-draft/reopen recovery, smaller-step editing, resumption and deliberate park/switch/return with the old stopping note retained. Simulated offline state disabled update controls and explained its limits. Meeting mode removed personal titles, actions, parked notes and editors from the rendered bookmark; leaving Meeting mode restored the private view. These are fixture results, not a physical Air check.

A second-client edit during a native draft correctly rejected the stale save and retained its text. Review found that the comparison omitted the stopping note and blocker, and that a recorded blocker needed a clear-after-resolution control. The final candidate now compares every saved detail and permits clearing the personal blocker without changing TaskDock. Actual native comparison helpers and backend clear/revision behavior are tested; final native recheck and package verification remain required before deployment.


### Refined native acceptance

The actual refined editor restored the earlier stale draft after app restart and showed **both stopping notes**: the local typed note above and the newer saved note in the comparison, together with the saved action, finish point and blocker. Save stayed disabled until explicit acceptance of the latest revision. The resolved blocker was cleared, the reviewed draft saved with Command-S, and the resulting card retained its stopping point with no blocker. Resume and Step finished returned to the empty-current view with the finished step recorded and other parked work retained. The fixture window closed normally; its server and random PostgreSQL workspace were then stopped. No live task or bookmark was used.

The 16 focused work-support tests passed, including source identity retention, clearing a blocker and two-client conflicts. The initial distribution passed all 15 installer groups; a final package incorporating the comparison/clear controls remains under verification. No physical Air result is inferred.


### Release scope

0.2.27 delivers the first starting/resuming workflow only. It does not claim that timers, quick capture, transition reminders, quiet-period controls or a midday reset are complete. These remain later Mission 17 work after Dan's first-use feedback. No additional reminders, AI health context, automatically selected priority or recurring operational task was enabled.


Help was updated to explain the first-step/interruption controls and to remove the obsolete claim that recurring TaskDock writes were not connected. The shipping 0.2.27 candidate is being rebuilt with that Help text; no 0.2.27 payload has been installed or published yet. The native data-entry/refinement walkthrough and backend results above remain applicable; the exact final installer will be verified separately.


## 0.2.27 installed — first increment accepted, November 18

The exact shipping package passed **15 installer groups** including **340 bundled-runtime tests**. The full backend suite passed **449 tests** before the additional exact-source-reference test; that new case and all **16 focused bookmark cases** passed afterward. Native starting-step/access/recovery/comparison helpers and the actual JunoStore offline regression passed. Source and UI checks above used disposable records and no live operational task writes.

Before updating, desktop Juno was normally quit, the encrypted backup passed restore validation at schema 0019, saved row/device projections and host/worker identity hashes were captured, and the 0.2.26 application was retained. macOS Installer succeeded after Dan approved its administrator prompt. The installed bundle reports **0.2.27/build 73**, passes deep/strict signature verification and opened at **Connected · This Mac**. Schema 0020 is present. Today showed the new starting card; the actual first-step form opened with source-copy dating and a disabled Start button until required fields are supplied, then cancelled cleanly without creating a test bookmark.

The post-migration strict comparison flagged **routine_occurrences**. A native pre-update dump was restored into an isolated temporary audit database; its receipt projection matched the original pre-install baseline hashes. Field comparison proved the only change was **updated_at**, refreshed when the normal managed-task monitor read back the already-created paused pilot. Task ID, occurrence/payload/scope/status, every other old table projection and paired-device identities matched. HTTPS/worker configuration and certificate/key hashes were unchanged. The initial strict check is retained alongside the reviewed timestamp exception; no exact all-row match is falsely claimed. The audit database was dropped afterward. The existing HTTPS sync listener is reachable, zero live synthetic bookmarks exist and zero recurring routines are active.

Private evidence: `.local/mission17-0227-ship-verification.json`, `.local/mission17-0227-backup.log`, `.local/mission17-0227-preservation.log`, `.local/mission17-0227-preservation-reviewed.json`, `.local/mission17-0227-preservation-summary.json`, `.local/mission17-work-support-final.log`, `.local/mission17-native-policy-final.log` and `.local/mission17-offline-client.log`. Final package/checksum/first-use notes: `~/Downloads/Juno-0.2.27`. These verification artifacts are not commit content.

**Next acceptance is user experience:** Dan should try one real small step, interrupt it and resume from the saved bookmark. Record whether the opening action is easy enough and the stopping note is sufficient. No new physical Air synchronization or sleep/wake result is asserted; earlier pairing/physical-copy evidence remains separate. VoiceOver remains waived. Later timers, quick capture, transition reminders and midday reset are not marked implemented. Mission 17 is active, with this first shipping increment accepted. No GitHub push.


## GitHub publication — November 18

Dan authorized publishing the Juno changes after first-increment acceptance. The release includes Juno code, migrations, tests and documentation through 0.2.27/build 73. Private interface-review output, installers, runtime state and other projects are excluded. Machine-specific documentation details were replaced with placeholders. The optional real-HTTP TaskDock bridge now takes checkout/runtime paths from environment variables; all four focused bridge cases passed after that portability change. Earlier “no push” entries describe the pre-publication development period.
