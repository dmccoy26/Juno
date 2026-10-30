# Preview 8 — tomorrow's setup

Juno remains a standalone native app. This preview adds **Connections**, with a TaskDock bridge and seven separate direct read-only provider readers. Nothing signed into a work account or copied TaskDock's provider secrets overnight.

1. On the work Mac, the existing development Juno app has been rebuilt to preview 8 and resumed hosting at `https://10.3.66.50:8443`. Work-record counts, owner, certificate/key and existing paired-device states were verified preserved. Use that existing workspace. Its shared-host identity and paired laptop must stay intact. Do not replace this host with the packaged `/Applications/Juno.app`, which uses different application-support data.
2. For the laptop, quit Juno and install `Juno-0.1.0-preview.8-macOS-arm64.pkg`, then open `/Applications/Juno.app`. Keep its existing pairing and data; synchronize while on the work network. Credentials for providers belong on the work Mac, so laptop Connections explains that restriction.
3. Optional TaskDock expansion: quit TaskDock, install the separate **build 15 candidate**, open `/Applications/TaskDock.app`, and confirm build 15 in About. In Settings → Connections → Juno, review any optional notes/events/recorded-time/expense sharing. Existing tasks continue through the old scoped bridge. In Juno Connections → Through TaskDock, discover and review the installation before reading those saved sections.
4. Direct providers: in Juno Connections → Direct programs, enter approved OAuth client information for Google/Microsoft or approved Slack/Smartsheet tokens. Save, sign in where applicable, discover, select and review before refreshing. Start with one small resource/query. See [the provider-by-provider guide](CONNECTIONS.md) for exact scopes, callback registration and limitations.
5. Review the dated content in Evidence and ask Juno about it. TaskDock remains the task hub. Calendar imports and semester CSVs still work in Evidence, including schedules Juno cannot access through a service.

Both installers are internal Apple Silicon previews, ad hoc signed app bundles with unsigned/not-notarized packages. Use the normal institution/macOS approval process; no trust or security settings were changed. TaskDock's candidate is distributed separately and its source is on a review branch. Its existing live installation was not silently updated or granted additional access.

Still manual: actual Google/Microsoft consent with your registration, Slack/Smartsheet live authorization and resource policy, HumanLab interaction testing, and the real laptop offline edit/reconnect check. Automated isolated equivalents and packaged-runtime checks are recorded with the release. No background provider refresh is enabled; use the explicit Refresh action.

## Downloads and source

Installers and both setup guides are in `/Users/dmccoy/Downloads/Juno-0.1.0-preview.8`; the TaskDock candidate has its own `TaskDock-build-15-candidate` subfolder. Both were extracted and verified; GitHub package byte counts and SHA-256 digests match the local reports.

- [Juno preview 8 draft release](https://github.com/dmccoy26/Juno/releases/tag/untagged-5293b211c9510fd8c7c5)
- [TaskDock build 15 draft release](https://github.com/dmccoy26/TaskDock/releases/tag/untagged-26bc656c6d8593c9a698) and [review PR #1](https://github.com/dmccoy26/TaskDock/pull/1)

Draft releases are accessible to repository owners/collaborators and have not been publicly published. Source changes are pushed; the TaskDock PR is deliberately unmerged.
