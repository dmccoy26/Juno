# Work planning

Preview 10 adds recurring schedules, possible repair windows, local-model ranges and reviewed planning holds. Start with [Schedules and repair planning](SCHEDULES-AND-REPAIR-PLANNING.md). The original preview 9 workflow and limitations below are historical where superseded.

Open **Plan** in the native Juno app. TaskDock stays authoritative for tasks; Juno records planning context alongside its dated task copy.

## First use

1. Refresh the authorized TaskDock connection and connected calendar. Complete approved sign-in/resource selection in Connections if not already configured.
2. In Plan, enter confirmed work windows for individual days. Set an interruption reserve for the selected seven-day horizon; the initial suggestion is 240 minutes and is editable. Times entered in the native controls use the Mac's timezone; the planning date uses America/Chicago.
3. Add explicit room-access and staff-availability windows where needed. Imported semester schedules supply occupied classroom periods and scheduled employee availability. Missing classroom occupancy does **not** prove access. Match room and employee names consistently, including locations in the semester CSV. Explicit dated windows can express exceptions; occupied classroom periods still win.
4. Open a task's **Planning details**. Review duration, actual reported minutes if known, Dean/operations importance, possible employee and confirmed independent capability, dependencies, next unblocking action, next check date and resumption note. Apply the details, then **Save planning**.
5. Review the question and suggestions. A Dean/operations conflict requires your choice before Juno recommends a task. The explicit choice applies to the selected planning date and expires for other dates. Discuss estimates or conflicts in Chat; enter confirmed changes in Plan. Conversation alone does not silently change planning facts.

Juno merges overlapping calendar commitments, intersects confirmed room/staff windows and rejects blocked, unestimated or impossible work. It subtracts recorded meetings only once, caps remaining capacity at 40 hours for the seven-day period, then subtracts the interruption reserve. Past work windows are excluded. It requires a contiguous interval that fits the reviewed estimate. A connected calendar or task copy over 24 hours old, or with a failed last refresh, requires review/refresh before actionability.

The result is **one next-task suggestion**, not a calendar booking or a complete weekly assignment schedule. Multiple suggestions must not be treated as simultaneous allocations. The task list is bounded to 500 candidates; a larger saved workspace shows that limitation. TaskDock due dates, priority, completed/waiting status and supplied blockers remain relevant. Dean requests lead unless you explicitly resolve a competing operations priority.

## Estimates and employee work

A task without a confirmed estimate starts with a deliberately broad **30–90 minute** discussion range, represented as a 60-minute candidate. This is an uncalibrated fallback, not a claim to understand task scope. **Discuss estimate** prepares a Chat question for the approved local model; review its suggestion and enter the chosen duration in Plan. User corrections persist across devices/restarts. Facts are bound to the reviewed TaskDock workspace; switching workspaces excludes prior task facts even if task IDs collide. Actual reported minutes are stored separately; this release does not claim statistical learning or automatic estimates from work history.

Employee workload totals cover only supplied planning assignments. Unknown estimates and blocked tasks are shown separately from recorded availability. This is not a complete accounting of employees' weeks, proof of attendance, or a performance/intelligence score. Independent capability must be confirmed with supporting context. Juno never sends assignments or employee messages.

## End of day and weekly continuity

Daily check-in remains a five-question, approximately 15-minute interview with saved drafts. Its expandable starter shows dated priorities and blockers due for review. Blockers with a later check date are counted without asking for the same unchanged explanation. Missing diary days remain unknown; no accomplishments are invented.

Plan can prepare a weekly Dean draft for the selected seven-day period from confirmed diaries and the current task/blocker copy. Select the period you want to report, including earlier days. The draft is editable **for this screen session**; copy it before leaving. It is not automatically sent or archived. Sensitive employee details and current status need your review.

## Storage and limits

Planning facts are owner-scoped, revision-checked structured records on the work Mac. A competing edit gets a reload/conflict error rather than overwriting. Remove individual facts/windows through Plan and save to delete that context. This changes Juno's planning record, not TaskDock, the source diary or its backups. Planning corrections invalidate assistant replies that depended on old facts, including in-flight replies. Existing backup retention still applies.

The laptop's next complete sync includes planning facts. The native Plan screen shows cached availability offline; task guidance and task-detail review need the connection. New planning edits/recommendations and weekly drafts require the host connection; offline memory and diary editing continue unchanged. There is no background collection while Juno is closed and no cloud fallback. Scheduling a whole week, automatic reassignment, calibrated duration learning, missed-day provisional drafts, reminders and native HumanLab instrumentation remain later work.

Real-account connection acceptance, an actual laptop offline-edit/reconnect trial and hands-on acceptance of the new Plan screen remain required before beta signoff.
