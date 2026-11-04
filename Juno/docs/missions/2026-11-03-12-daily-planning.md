# Mission 12 — daily check-in to tomorrow's plan

Started November 3, 2026 at Dan's request. Product objective: spend less time deciding what to do, using an approximately 15-minute end-of-day conversation that resumes after interruptions.

## Experience

1. Orient Dan with a compact dated review: saved TaskDock completion evidence, diary status, blockers due for review and source freshness. A saved task's current completion state alone does not establish when it was completed. Diary statements remain attributed to Dan, with draft/confirmed status.
2. Keep the existing five questions, one at a time: accomplishments, unexpected work/time, blockers, known employee contributions and tomorrow. Add relevant saved context to each question, without pre-answering, inventing work or treating a missing update as inactivity. Future blocker check dates stay deferred unless something changed.
3. Review and confirm the diary separately from any planning decision. Skips mean unknown. Preserve offline diary editing, revision conflicts and answer drafts; no model is required for the core interview.
4. Preview a short list for the next scheduled workday. Show the reason, reviewed estimate, room/person, possible time and resumption note. A priority conflict requires a question before a recommendation. Alternatives are not simultaneous allocations, calendar reservations or employee assignments. Unknown/stale inputs remain visible and block unsupported recommendations.
5. Open the selected date/issue in Plan for reviewed changes. Existing Plan drafts must survive this handoff. Chat/diary answers do not silently change confirmed task facts, deadlines, assignments or capability.
6. Make a weekly Dean update from confirmed diary evidence and clearly dated current task context, for review before copying/sharing. Preserve the draft across ordinary navigation/restart in a later increment if needed; never send it automatically.

## First implementation increment

Add an owner-scoped read-only daily briefing API and native presentation that connects the existing check-in with the existing planning engine. Include question-specific context, next-workday detection, bounded alternatives, actual single-day time constraints and explicit Plan handoff. Reuse existing persisted check-in answers and planning facts; do not add another task store. Clearly expose offline/unavailable state rather than showing an old online briefing as current.

Tests must cover date/owner/workspace isolation, completion timestamps, unknowns, deferred blockers, next-workday/weekend selection, calendar and room/person limits, conflicts and stale inputs, no writes/model calls, native decoding and handoff draft safety. Use isolated fictional PostgreSQL data and an isolated native candidate. Do not use real work for mutation tests.

## Follow-on increments

- Reviewed task-specific carry-forward from the interview into existing planning facts, with explicit before/after values, revision checks and source provenance.
- Persisted, editable weekly Dean drafts with clear source dates and missing-day coverage.
- A timed walkthrough with Dan or suitable HumanLab/native testing, measuring whether he can finish the interview and understand tomorrow's first action in about 15 minutes.
- TaskDock worker-report consumption after its separate hub/contract is ready; this mission does not deploy or modify TaskDock.

## Boundaries and completion

Keep Juno a standalone native Mac app. Real work stays on approved local systems with the approved local model; no cloud fallback. Preserve host identity, paired devices, certificate/key, canonical records, encrypted backups and existing workers/report history. TaskDock remains the task/assignment authority. Do not change its hub or worker enrollment here.

Finish each increment with implementation/test evidence, updated build status and explicit remaining limits. A built development candidate is not an installed update or a verified laptop installer. Do not claim full weekly scheduling, predictive repair accuracy, automatic employee assessment or exhaustive UI perfection.

## First increment result

Implemented and verified November 3: see [workflow](../DAILY-CHECKIN-PLANNING.md) and [actual verification](../reports/daily-planning-2026-11-03.md). 159 backend tests pass without skips, native model/time/offline/planning checks pass, and the isolated native interview/draft-protection/date/task/refresh flow was observed. The development candidate is built; production app installation, a portable installer and remaining mission phases are not claimed complete.

## November 4 — next phases implemented

Dan authorized reviewed carry-forward and persisted weekly Dean drafts. Both are implemented and verified in an isolated native candidate: [workflow](../DAILY-CHECKIN-PLANNING.md) and [evidence](../reports/planning-continuity-2026-11-04.md). Selective field review, diary/plan/workspace/snapshot fences, atomic provenance/receipts, saved weekly text, source-basis warnings, comparison and recovery are delivered. 186 backend tests pass with no skips; native data/interaction/offline checks pass. Installation, portable packaging and the timed real-user acceptance remain separate delivery work.

## Preview 16 installed work-host delivery

At Dan's request on November 4, the active work-host app was updated to preview.16 and the version added beside Juno in the header. Installer and preservation checks passed; see [delivery evidence](../reports/preview-16-delivery-2026-11-04.md). Administrator installation of the older root-owned standalone copy, physical laptop acceptance and the timed real-user walkthrough remain open.
