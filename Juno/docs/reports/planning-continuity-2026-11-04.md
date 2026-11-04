# Mission 12 — reviewed carry-forward and saved Dean drafts

November 4, 2026. Both requested phases implemented in source and a separately built native development candidate. This report extends the November 3 first increment.

## Behavior and storage

Confirmed diary excerpts can be explicitly mapped to one current TaskDock task. Only selected Juno planning fields change. Preview is read-only; final save atomically updates planning facts and records the reviewed source, original/selected values and receipt. Revision/snapshot/workspace fences reject stale intent. Selected-field presence is included in the operation fingerprint, so retrying with an extra clearing field conflicts rather than being treated as the original intent. Receipt retries never reapply facts. Source history is available in the native inspector, with a warning when the diary has since changed.

Weekly drafts are owner/period scoped, revision checked and stored independently of generated comparisons. Preparation records confirmed diary revisions, TaskDock snapshot/workspace/read time, planning revision and source uncertainty. Old preparation metadata is conservatively treated as unverified. Evidence changes produce a warning without overwriting reviewed writing. Local recovery is owner/period scoped; saved text and recovered text have an explicit comparison flow. Stable save identities recover lost receipts. Nothing is sent to the Dean automatically.

Migration `0012_daily_planning` is additive: `planning_carry`, `dean_drafts`, `dean_draft_operations`. Existing planning saves and carry-forward share the same validated persistence function. Planning facts and provenance commit together. Saved Dean drafts enter the bounded owner-only offline read export; new writes/preparation/carry-forward remain online. No new cloud model or TaskDock mutation is introduced.

## Verification

- **186 backend/PostgreSQL tests passed; zero skips.** Existing Starlette/httpx deprecation warning remains. Cases include preview without writes, selected-only changes, explicit clearing, corrected/unconfirmed diary denial, owner/workspace/snapshot/revision fences, preserved unrelated facts, retry identity and provenance.
- Injected provenance insertion failure rolls back the planning change. Concurrent weekly edits yield one success and one revision conflict. Drafts reopen after service recreation and from a second authorized device. A new generation cannot replace saved writing. Missing days are reported; forged or changed source basis is rejected for new drafts.
- A separate database upgraded from schema 0011 preserves its prior confirmed diary text/revision and planning facts. SQLAlchemy/Alembic model comparison passes at the new head. This is an isolated upgrade rehearsal, not a production migration/restore claim.
- Exact Swift carry/weekly models decode real fictional API responses and send the native-encoded source basis back successfully, including explicit null values. Existing daily briefing/planning wire checks, native offline memory/diary queue and planning-editor validation pass.
- Optimized SwiftUI candidate built and signature verified: `.local/continuity-final/Juno.app`. It depends on this checkout; no portable installer was produced.
- Native interaction lab used an independent owner, preferences/Keychain namespace and private synthetic database, with shared hosting disabled. Confirmed a fictional diary; selected a task and exact excerpt; reviewed before/after; saved one resumption note. After full app restart, Plan displayed the note and its diary date/revision, excerpt and historical change.
- Native Dean editor prepared, edited, saved and reopened a weekly draft. Fresh preparation appeared as a separate comparison. Unsaved local writing survived explicit close/reopen; Compare showed both versions and Use saved text restored only the local editor. A full app restart retained the canonical edited writing. Older preparation metadata opened with an uncertainty warning.
- Native testing/compiler feedback fixed a shadowed Swift state variable, and source-history/recovery layouts use scrolling with persistent actions. No claim that every UI state, physical laptop or all accessibility modes has been tested.

## Scope and remaining delivery

Only fictional records were used for mutation checks. Existing work records, pairing, certificate/key, worker portal and TaskDock code/configuration were not changed. The lab was quit after review and its separate PostgreSQL cluster stopped. Unrelated repository changes were preserved.

The installed Juno app and preview.15 laptop package remain unchanged. Source changes are reviewable; no GitHub push was requested for this increment. Remaining Mission 12 acceptance: timed real-user/native walkthrough of the approximately 15-minute routine, deployment/installer verification when updating the work app/laptop, and eventual TaskDock report consumption under its separate contract. Full weekly scheduling and autonomous assignments are not claimed.
