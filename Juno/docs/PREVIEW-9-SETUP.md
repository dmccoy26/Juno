# Juno preview 9 — work planning

The work Mac's development application is already updated. Open **Plan** in Juno to start. Keep Juno open and this Mac awake for your laptop's connected features.

## Laptop update

Quit Juno on the laptop, then install `Juno-0.1.0-preview.9-macOS-arm64.pkg` and reopen `/Applications/Juno.app`. Existing pairing and application-support data are retained; an existing paired laptop should reconnect without a new invitation. Follow the institution's normal installation process: this internal installer is not Developer ID signed or notarized.

The work desktop currently uses `~/Applications/Juno.app` with development data. Its separate `/Applications/Juno.app` packaged installation uses a different data directory. Installing the laptop package on the desktop is not a migration of the existing work host.

## First planning trial

1. Check your saved TaskDock tasks and calendar in Juno. If necessary, finish the approved connection setup from [the connection setup guide](PREVIEW-8-SETUP.md).
2. Open **Plan** and confirm work windows for the next few days. Allow time for interruptions with the editable reserve.
3. Choose one real task. Review its estimate, room access, relevant employee availability/capability and dependencies. Apply the details and save planning.
4. Review Juno's question or next-task suggestion. For a Dean/operations conflict, explicitly confirm the priority for that planning date. Chat can help discuss scope and estimates; confirmed planning changes remain reviewable in Plan.
5. At the end of the day, open **Daily check-in**. Expand the saved-context starter, then answer the five questions. Review and confirm the diary.
6. For your Dean meeting, choose the seven-day period you want to report and prepare the weekly draft. Review/edit and copy it before leaving the screen. Juno does not send it.

See [the planning guide](PLANNING.md) for rules, source limitations and exact behavior.

## Remaining acceptance

- Review the new native Plan screen hands-on. Its compiled application and native API decoding are verified; native UI automation was unavailable during this session.
- Confirm approved provider credentials, consent, selected resources and a real TaskDock/calendar read. Synthetic tests do not replace this setup.
- On the actual laptop, disconnect from the work network, save a diary entry and memory correction, restart Juno, reconnect and verify synchronization. Existing pairing was preserved; this full physical-device trial is still pending.
- Try a normal end-of-day interview and assess whether it fits about 15 minutes and reduces the effort of choosing tomorrow's work.

Planning facts join the laptop cache and confirmed availability is visible offline. Task-detail review, planning edits and recommendation generation need the work Mac connection. Offline memory and diary editing still work. Unconfirmed durations use a broad discussion range; estimates are not statistically calibrated. This is one-next-task guidance, not an automatically booked or fully allocated week.
