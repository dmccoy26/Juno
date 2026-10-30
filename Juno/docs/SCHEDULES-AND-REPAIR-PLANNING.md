# Schedules and repair planning — preview 10

Juno stays a native Mac application. TaskDock remains authoritative for tasks; Juno holds schedule context and local planning reservations.

## Review recurring schedules

Open **Schedules** to review people, recurring rules, dated exceptions and planning holds. A rule specifies its kind, name/location, weekdays, same-day start/end times, timezone and inclusive effective dates. Supported rules cover personal work hours, building access, classroom occupancy and employee shifts. Change a recurring Wednesday once instead of editing every date.

Choose **Edit**, apply the change to the draft, then **Save schedules**. Concurrent changes return a conflict rather than overwriting another device. Saving schedule changes marks existing holds for review. Removing a managed rule does not resurrect older imported availability. Earlier Juno clients cannot silently change the legacy dated hours for an entity now managed by recurring rules; use Schedules instead.

Daily exceptions can close a building, remove a shift, change a day's hours or record that classes do not meet on a particular date. Exceptions use America/Chicago. A no-classes exception does not open a closed building. Holidays, leave and one-off changes must be supplied; Juno does not infer them from a blank calendar.

People have **Active**, **Schedule unsettled** or **Candidate** status, a funded weekly limit and optional agreed weekly hours. Candidates and unsettled schedules contribute no confirmed capacity. A funded limit is not a requirement to work that many hours. An active employee also needs actual shifts. The native hours editor accepts whole hours; the service stores minutes. Staff names identify linked shifts and cannot be renamed through this editor. No skill or performance score is inferred.

## Find possible repair windows

In **Plan**, use **When could we work on this?**:

1. Choose the first day of a seven-day horizon, room and required duration.
2. Select yourself or an employee. For employee work, explicitly indicate whether your supervision/collaboration is needed.
3. Select **Find possible windows**. Changing an input hides the previous results until you search again.

Juno starts with confirmed room access, removes all overlapping classes, intersects the selected person's shifts, and removes conflicting planning holds. Personal/supervised work also intersects your normal hours and subtracts recorded meetings. Independent employee work does not require you to be present. Results are alternatives, not simultaneous assignments or proof that an employee has the required skills.

Room aliases can be matched for the known facilities. Task-title room matches are labeled suggestions requiring review; Juno does not silently infer a confirmed assignment from a computer name. Unknown rooms require supplied access information.

## Link TaskDock issues and reserve work

Refresh Juno's **TaskDock** snapshot on the work Mac. Select an open task and choose **Plan this task in Juno**. Review its room, employee, duration, prerequisites/blocker and independent capability or supervision requirement. Apply and save the planning details.

Back in the window finder, select that task and choose **Reserve reviewed task**. The service rechecks current task identity/status, duration, blockers, availability, competing holds and weekly hour limits. Room/person overlap is rejected. Employee reservations cannot exceed the funded limit or lower agreed hours. Personal/supervised reservations also respect the weekly interruption reserve and 40-hour ceiling. A connected calendar with a failed or over-24-hour-old read must be refreshed before booking personal/supervised work.

A reservation is a **local Juno planning hold**. It never changes TaskDock, sends an assignment, creates a calendar event or messages an employee. Release holds through Schedules when plans change. Existing holds are conservative blockers until reviewed/released, including after a task is completed or its schedule changes. This is an incremental planning tool, not a whole-week optimization solver. A single hold supports 5–480 whole minutes.

## Review estimates

Task planning details include **Suggest a duration range**. If the approved local model is configured, it receives bounded task evidence and returns a reviewable range and scope question. An invalid/unavailable model leaves a clearly labeled fallback. Comparable reported durations may inform the fallback after at least three completed tasks in the same heuristic work group; comparisons can have different scope and are not performance measures.

Using the midpoint updates only your draft. Apply/save it explicitly before reserving work. No cloud fallback, custom training or automatic task-duration writeback is enabled.

## Current boundaries and acceptance

- The work Mac remains authoritative and must be awake with Juno open. A full laptop sync includes schedules; schedule editing, estimates and reservation changes require a connection. Offline memory/diary editing remains available.
- TaskDock reads are manual and read-only. A new Juno read does not refresh its upstream providers. Review provider freshness separately.
- The Google/Outlook readers exist, but real account approval, client registration, consent and selected calendar coverage still need acceptance. No recorded meeting does not prove free time.
- The approved operational schedules were migrated privately. Real work records, staff details, credentials and task payloads are excluded from the repository and installer.
- Actual laptop installation/offline-reconnect and hands-on acceptance of all new controls remain required. The native automation service failed intermittently during the new-screen checks; compiled Swift/model decoding and API/package verification are separate evidence, not a substitute for those interaction checks.
