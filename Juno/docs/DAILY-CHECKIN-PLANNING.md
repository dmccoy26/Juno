# Daily check-in and next-workday preview — Mission 12 development increment

Open Daily check-in and choose the day (today by default). Juno shows a compact review of dated saved evidence, then asks the existing five questions one at a time. Guidance uses saved context without pre-answering the questions. No model is required. Answers save as you continue; skips stay Not provided.

Completion timestamps identify recorded task completions on the selected America/Chicago day; a completed flag without a usable timestamp does not establish work done that day. Unreported work remains unknown. Blocker checks with later dates are deferred. Source freshness and draft/confirmed diary status stay explicit.

After the five questions, review/edit and optionally confirm the diary. The next-workday panel finds the first recorded workday in the following seven days. If none is recorded, the next calendar day is labeled availability unknown. It evaluates only that day's windows, including saved calendar, room, staff, supervision and capacity constraints. A disclosed proportional share of the weekly interruption reserve is used for this preview. It does not change the saved reserve or allocate an entire week.

A Dean/operations conflict asks for clarification before a recommendation. Missing estimates, stale sources or unavailable windows can prevent a suggestion. At most three alternatives are shown, each with reviewed duration, possible time in 12-hour Chicago format and saved resumption context. Alternatives are choices, not concurrent allocations, reservations or assignments.

Review this issue in Plan opens its date and task. Open Plan for this day opens that date without changing task facts. Existing unsaved Plan drafts block this handoff. A workspace change prevents applying the old preview to a colliding task ID. Update facts using the normal Apply to draft → Save planning steps. Returning to check-in or reloading refreshes the briefing; saving a diary alone never silently updates planning facts.

Manual diary corrections supersede original interview wording: when diary text was edited after the interview, original interruption/tomorrow answers are not automatically repeated as current carry-forward evidence. The reviewed diary remains visible and authoritative.

Offline memory/diary edits remain available. A fresh briefing and planning calculations require the work Mac; offline mode clears the online preview and explains this limitation. This increment adds no cloud model, notification, automatic assignment, TaskDock hub change or database migration.

Status: implemented and verified in an isolated native development candidate. The installed work app, latest preview.15 laptop installer, host identity/pairing, certificate/key and real work records were not replaced or edited for this increment. Next phases are reviewed task-specific carry-forward, persistent weekly Dean drafts and a timed real-user walkthrough. See [Mission 12](missions/2026-11-03-12-daily-planning.md).

## November 4 — reviewed carry-forward

The next development candidate adds **Carry a reviewed detail into Plan…** after a diary is confirmed. Save any diary edits first. Select an exact excerpt from the saved diary and the intended task, using title, room/equipment/parent context or reference to distinguish similar tasks. Select only the fields to change: resumption note, blocker, dependency, next action/check date or reviewed duration. Unselected fields keep their existing values. An empty selected field explicitly clears that Juno value; it does not clear TaskDock's source facts.

Review the before-and-after values, then choose **Save reviewed planning detail**. This final action saves the selected fields and their diary provenance together. It does not add actual-work time, assign a worker, infer capability, change TaskDock or modify the diary. Planning/diary revisions and the selected TaskDock snapshot/workspace are checked again at save. Changes from another device require a fresh comparison. An uncertain save retains its operation identity for explicit retry; it cannot apply twice. Cancel before saving writes nothing.

Plan's **Reviewed check-in sources** disclosure shows the excerpt, diary date/revision and historical before/after values. A later diary correction is flagged for review; it does not silently rewrite the separately reviewed planning facts. Existing unsaved Plan drafts block starting a carry-forward review.

## November 4 — saved weekly Dean drafts

In Plan, choose **Open weekly Dean drafts…** and select the seven-day period. Existing saved text opens automatically. **Prepare draft** uses confirmed diary entries and dated task/planning context; missing diary dates remain unknown. Edit the draft and choose **Save draft** to store it on the work Mac. A saved draft reopens across app/service restarts and authorized devices. **Copy reviewed draft** only copies text for you to share; Juno does not send it.

**Prepare fresh comparison** shows newly prepared text separately and keeps your writing. Changes in the diary/task evidence are indicated without regenerating over saved text. **Compare saved copy** presents the current server copy alongside your local writing; you explicitly choose which text to keep before saving against its revision. Local unsaved writing and uncertain save identities have owner/period-scoped recovery. Close can retain that recovery for later. This local copy is distinct from a confirmed work-Mac save.

Saved drafts are included in the bounded paired-laptop read cache. Opening an uncached period, preparing new text, carrying a detail or saving a Dean draft requires the work Mac connection. Dean draft writes are not added to the existing offline diary/memory queue. Migration `0012_daily_planning` adds provenance/draft/receipt tables; existing diaries/planning are preserved.

Implementation status: both November 4 features are built and verified in an isolated development candidate at `.local/continuity-final/Juno.app`. The actual work application and portable preview.15 installer have not been replaced by this work. See [verification](reports/planning-continuity-2026-11-04.md).

## Preview 16 delivery

November 4: these features are now installed in the active work-host app (`~/Applications/Juno.app`), with the release version beside Juno's name. The portable preview.16 installer is verified. The root-owned standalone copy and physical laptop installation remain separate administrator/user actions; see [setup and exact delivery status](PREVIEW-16-SETUP.md). Earlier development-only status above describes the pre-delivery increment.

## Preview.17 — question-first daily interview

Daily check-in displays one prominent “Juno asks” question above the answer area. Enter your answer there and choose **Save answer and continue**; **Skip for now** records unknown and advances. The saved-answer count updates after a successful save. Saved work context and freshness are available in a collapsed disclosure below, instead of preceding the interview. After five responses, review the diary before confirming. This is the Daily check-in workspace, not Chat. Existing daily records resume at their next unanswered question; completed interviews keep their diary review rather than starting over.

The implementation and isolated checks pass; preview.17 installation and another real-user walkthrough remain pending.

## Current delivery — preview.19

The question-first interview is installed in `/Applications/Juno.app` as part of preview.19, alongside the approved Juno logo/icon, clear TaskDock connection fields and Today refresh-on-return. Backend, isolated native and extracted-package checks pass; see [build status](BUILD-STATUS.md). Earlier development/install-pending notes are historical. The timed real-user check-in remains open following the original prompt-placement confusion; no completion time or user acceptance is inferred from synthetic checks.
