# Juno preview 10 — schedules and work windows

The work Mac is updated to preview 10. Quit and reopen Juno once to load the final helper update. Its existing owner, records, shared-host certificate and laptop pairing are preserved. The approved classroom, building and staff information is stored privately on that host as recurring rules and staff-status records.

## First use

1. Open **Schedules**. Review recurring work hours, building access, class times, staff shifts and effective dates. Review active, unsettled and candidate statuses and weekly limits. Add holiday/leave exceptions when known.
2. Open **TaskDock**. Read-only access is now enabled with your approval; Juno stores its dedicated credential in macOS Keychain. Refresh the saved snapshot when needed. This does not refresh TaskDock's upstream sources.
3. Select an open task and choose **Plan this task in Juno**. Review room suggestions, duration, assigned helper, capability/supervision and prerequisites. A suggested estimate is not saved until you apply/save it.
4. In **Plan → When could we work on this?**, select a room, person, duration and seven-day period. Find possible windows. These are alternatives, not assignments.
5. If appropriate, select the reviewed task and reserve one window. This creates only a local planning hold. Review/release holds in Schedules if conditions change.

For full rules and limitations, read [Schedules and repair planning](SCHEDULES-AND-REPAIR-PLANNING.md).

## Laptop installer

Quit Juno on the laptop, install `Juno-0.1.0-preview.10-macOS-arm64.pkg`, then reopen `/Applications/Juno.app`. Python and PostgreSQL are bundled. Existing pairing and application-support data should remain; the laptop receives schedules on its next full sync. Apply the institution's normal installation process: this internal package is not Developer ID signed or notarized.

Keep using `~/Applications/Juno.app` on the development work Mac. Its separate `/Applications/Juno.app` packaged installation has a different data directory; installing the laptop package there does not migrate the current work host.

## Still needs your trial

- Review the new Schedules and work-window screens hands-on. Native automation could verify pairing/import but became unreliable during the new-screen tests.
- Confirm real calendar consent/resources and meeting coverage. The manual work hours are boundaries, not a full calendar of free time.
- Complete the physical laptop offline memory/diary edit, restart and reconnect trial.
- Review duration suggestions and confirm staff capabilities before reserving actual work. No real task assignments or calendar events were created automatically.
