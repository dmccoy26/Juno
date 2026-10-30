# Local work evidence — preview 7

Open the native **Evidence** tab. TaskDock remains the task system of record. These inputs supply dated observations and commitments to Juno's local model; they never create tasks, change inventory or send messages.

## Beacon

On the work Mac, enter Beacon's loopback address (normally `http://127.0.0.1:12108`) and a dedicated read-only integration key supplied through Beacon's existing administration process. **Read Beacon alerts** issues only GET `/api/alerts`. Juno does not provision or discover a key. A successful key is stored in this Mac's separate Beacon Keychain namespace; an empty field reuses that saved key. **Forget saved key** removes the credential, while **Remove copy** removes imported evidence.

Only loopback HTTP/HTTPS is supported. Plain HTTP to the desktop's LAN IP is rejected so the credential does not cross the campus network unencrypted. Proxies and redirects are disabled. This connector is for the work Mac running Beacon locally. If Beacon is hosted elsewhere, use a manually supplied complete alert-feed JSON file until an approved authenticated transport is implemented.

The adapter accepts schema version 1, `complete: true`, matching total/row counts, unique alert IDs and an aware generated-at timestamp. Nullable observed times/locations stay unknown. It keeps physical checks separate from telemetry and preserves source, observation evidence and cartridge references. It never interprets an empty failed read as a resolved alert. On failures, the last good snapshot stays visible with an error. Source-generated and Juno-imported timestamps are distinct.

No live Beacon key was supplied for the overnight mission. The complete HTTP reader was verified against a disposable local fixture, including redirect denial, partial feeds and outage retention. This is not a claim of a live connection.

## Calendar exports

Export a calendar as `.ics`, choose **Calendar (.ics)**, enter an explicit date window and timezone, then choose the file. The import window's end date is exclusive; at most 366 days are accepted. This is a manual dated import, not a live Google Calendar connection or subscription. Reimport when the calendar changes or the coverage window expires.

Timezone-aware events retain their source timezone/offset; floating times use the selected timezone (or a calendar-supplied X-WR-TIMEZONE). All-day events occupy their date interval with an exclusive end. Recurrences, EXDATE omissions and moved instances are expanded within the selected window. Cancelled events are omitted; transparent events remain visible but do not count as busy. Tentative opaque events count as recorded commitments, not confirmed attendance. The import is not tied to an attendee identity and does not infer whether you declined an invitation.

Daily/weekly/monthly/yearly recurrence is supported. Dense sub-day rules, BYSECOND/BYMINUTE/BYHOUR, EXRULE, unresolved timezones, duplicate event versions and ambiguous floating DST times are rejected. A rejected file retains the previous import. Limits: 2 MB calendar input, 1,000 event definitions, 1,000 recurrence dates per definition, 20,000 expanded events and 16 MB normalized source. Links, attachments and alarms are never fetched or executed. Imported display text is plain text.

Busy-time totals count overlapping intervals once **within each source**. They are recorded commitments, not remaining work hours: Juno does not assume a 9-to-5 schedule, subtract from 40 hours without your work windows, merge personal and staff calendars, or infer that a room is accessible just because no class was listed.

The pinned parser dependencies use the maintainers' APIs: [icalendar](https://icalendar.readthedocs.io/) and [recurring-ical-events](https://recurring-ical-events.readthedocs.io/en/v3.8.2/). No cloud calendar SDK or OAuth scope was introduced.

## Semester schedules

Choose **Save schedule CSV template…**. Replace every fictional row with your real semester information, then import it as **Semester schedule (.csv)**. Use these exact columns, in order:

```
kind,name,location,start_date,end_date,days,start_time,end_time,timezone
```

- `kind`: `classroom_busy`, `staff_available` or `meeting`.
- `name` and `location`: class/employee/meeting label and its room.
- Semester dates: ISO `YYYY-MM-DD`; the row's end date is **inclusive**.
- `days`: `MO|TU|WE|TH|FR|SA|SU`, selecting the needed weekday abbreviations with `|`.
- Times: same-day 24-hour values, for example `09:00` and `10:30`. Split overnight periods into separate rows.
- `timezone`: an IANA name such as `America/Chicago`, supplied in every row.

The separate import window still has an exclusive end. Rows expand only where semester and import windows overlap, retaining each row's local time across DST. Duplicate/invalid rows reject the complete import. At most 1,000 weekly rows and 20,000 expanded intervals are accepted. A semester lasts at most 366 days. An empty template with just its header can explicitly replace the source with zero rows.

Classroom intervals mean **occupied**, staff intervals mean **scheduled availability**, and only meeting rows count as your personal busy time. None establishes actual attendance, independent capability or performance. Missing intervals are unknown. Use TaskDock and conversation to supply operational issues, skills and blockers separately.

## Shared host, model context and removal

Each owner has one current validated copy of each source. Replacing it removes superseded source text and invalidates saved replies that used it. Deletes also invalidate derived replies; a model response already in flight is rejected if its source changed. There is no hidden integration archive. Database backups made before migrations may contain earlier work data and retain their existing lifecycle.

The approved work Mac imports/refreshes sources. Paired laptops can read the host's dated copies and receive them in the bounded offline export; they cannot upload imports or supply integration credentials through the LAN API. A laptop that is offline retains its prior dated copy until reconnection; removal is not a remote wipe.

The local model receives bounded selected excerpts, timestamps, coverage, source notice and refresh errors. Imported text is explicitly untrusted evidence. Selection does not imply completeness, and imported source text is not promoted automatically into personal memories. Keys, arbitrary provider URLs, alarms and unknown extension fields are excluded. No cloud fallback is enabled.
