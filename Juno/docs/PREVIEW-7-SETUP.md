# Juno preview 7 — morning setup

Both overnight missions are implemented. This release remains a native Mac application. The installer includes Python/PostgreSQL and requires no source checkout, Homebrew or browser tab on the laptop.

## Work Mac

The existing development host at `/Users/dmccoy/Applications/Juno.app` was rebuilt and relaunched against its existing `/Users/dmccoy/Ai/Juno/.local` workspace. Hosting resumed at `https://10.3.66.50:8443`. Owner identity, work-record counts, existing paired-device states and certificate/private-key hashes were verified unchanged. Only the app's temporary local credential rotated normally. Schema 5 was applied after the existing readable pre-migration backup. The previous app is retained privately under `.local/host-app-before-preview7` for rollback investigation.

Keep this Juno app open and the work Mac awake. No sleep, firewall, router or certificate-trust settings were changed. Do not install the packaged app as a replacement host on this desktop: `/Applications/Juno.app` uses separate `~/Library/Application Support/Juno` data. The existing development host is the approved shared workspace.

## Laptop update

1. Transfer `Juno-0.1.0-preview.7-macOS-arm64.pkg` from the preview 7 Downloads folder to the laptop.
2. Quit Juno on the laptop, install the package, then open `/Applications/Juno.app`. Follow normal macOS/institution software approval; this private package is unsigned/not notarized.
3. Keep the existing pairing and application-support data. A normal update preserves the laptop credential, queue and history; a new pairing file is not needed just for this release.
4. While connected to the work network, choose **Computers → Reconnect and synchronize**. The shared host still needs to be open/awake. The last complete-copy timestamp should update.
5. For actual-device acceptance, disconnect the laptop from the work network, create a fictional memory and daily check-in answer, quit/reopen, then reconnect. Verify that both appear once on the work Mac. The equivalent automated native outage/process-restart path passes, but your actual laptop offline-edit acceptance has not yet been reported.

The laptop can read imported evidence offline; import/refresh/removal belongs to the work Mac. An offline laptop does not generate new AI replies. If both computers edit one memory/diary, **Computers** preserves the queued work and asks for an explicit comparison/decision. Export before discarding anything you want to keep separately. A fresh verified invitation can repair a changed host address while retaining the same host certificate/owner queue.

## Add operational evidence on the work Mac

- **Beacon:** in **Evidence**, enter its local address and your dedicated read-only integration key, then **Read Beacon alerts**. The key stays in this Mac's Keychain. No key was created or extracted overnight. Alternatively import a complete schema-1 alert-feed JSON file.
- **Calendar:** export a calendar `.ics` file, choose a 1–366 day date window and timezone, then import it. This is a dated copy; reimport when it changes.
- **Classrooms/employees:** save the schedule CSV template from **Evidence**, replace all fictional rows with the current semester's actual weekly intervals, then import it. Classroom occupancy, employee scheduled availability and your meetings remain distinct.

See `INTEGRATIONS.md` for supported recurrence, date/DST behavior and source limits. Juno does not infer employee skills or assume unlisted rooms/times are free. These imports do not create or modify TaskDock tasks. Email/Slack are not connected by this release.

## Evidence

59 backend tests passed with actual isolated PostgreSQL; native queue/store and exact-certificate TLS outage/restart checks passed; an isolated native app displayed all three fictional sources and successfully imported a CSV through the macOS file picker. The final installer was extracted, relocated and verified using bundled runtimes, including migration backup, source readers/cache/restart/removal, pairing/revocation and resource signatures. Machine-readable final report: `docs/reports/installer-preview-7.json`.

No real Beacon/calendar feed, HumanLab native run, new cloud approval or multi-day laptop acceptance is claimed. This is the next internal preview, not completion of the full beta 0.1.0 mission.
