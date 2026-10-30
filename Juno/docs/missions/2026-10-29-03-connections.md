# Mission 3: both connection paths

Status: completed. Both connection paths, native setup, isolated/native/packaged verification and installer distribution are delivered. Live credentials/consent remain tomorrow’s setup by request. Dan authorized autonomous implementation of both paths, with connection information and sign-in to be supplied tomorrow. Work within the available five-hour session; deliver verified useful software, not placeholder forms or a claim of unconfigured live access.

## Outcomes

1. TaskDock remains the task system of record. Extend its supported authenticated local Juno bridge with a sanitized source catalog and consistent paged reads of additional **stored** operational evidence. Events, notes, recorded time and expenses require separately reviewed opt-in grants; old task-only tokens stay task-only. Never export provider credentials or trigger upstream refresh/writeback. Clearly distinguish TaskDock's selected task-email/Slack imports and outgoing calendar delivery from broader provider data.
2. Juno gains direct read-only provider readers and native setup for Gmail, Google Calendar, Google Tasks, Google Chat, Slack and Smartsheet, alongside its existing Beacon reader; Outlook Calendar is included if its verified public-client flow fits the session. Use minimal read scopes, fixed HTTPS destinations, explicit resource selection, bounded pagination/windowing, account identity review, privacy-conscious plain text, stale/error retention and no provider writes.
3. Interactive sign-in uses a browser only for provider consent, with native application setup and loopback PKCE/state handling. Store persistent secrets in macOS Keychain, keep them out of PostgreSQL/export/model/logs, and leave all live credentials and consent for tomorrow. Do not copy existing TaskDock secrets or access external work accounts during tests.
4. Dated normalized evidence enters the existing owner-scoped local model/cache workflow. Provider data stays on the approved work host; paired laptops read saved evidence and cannot administer connections. Distinguish direct and bridged copies and avoid recommending duplicate provider actions. Support remove/disconnect/credential-forget and explicit reauthentication states.
5. Verify using isolated fictional provider transports/databases, actual Juno/TaskDock API compatibility, OAuth failure/replay/state/expiry/PKCE protections, native Keychain/forms/browser launch validation and packaged runtimes. Build standalone Apple Silicon installers and document precisely what information Dan must enter tomorrow. Push Juno changes and TaskDock changes/artifacts to GitHub, preserving unrelated work and live identities.

## Execution boundaries

Use an isolated TaskDock branch/worktree so the separate TaskDock project and installed build 14 remain intact. No unsolicited external messages, account creation, permission grants, upstream writes, cloud LLMs, credential discovery, attachment/image fetching or public listeners. Do not invent full-provider access from a task cache. Keep Juno's current work data, host certificate and paired laptop intact. Respect its pre-existing unrelated repository-root README deletion.

## Acceptance

Both connection paths must have working readers and end-to-end native configuration paths, not just a requirements document. Missing live credentials must be reported as setup remaining, not treated as a reason to stop independent implementation/testing. Unsupported provider behaviors must fail clearly while retaining the last good source. Explicitly record actual-device/HumanLab/live-consent gaps and any unimplemented scope. Preserve credential and account boundaries across restart and package updates.

## Implementation evidence

See [connection mission report](../reports/connections-2026-10-29.md), [morning setup](../PREVIEW-8-SETUP.md), [provider setup](../CONNECTIONS.md), [actual two-app bridge report](../reports/connections-bridge-preview-8.json) and the final package reports. Live credentials, consent and explicit TaskDock sharing remain Dan’s setup tomorrow, as requested.
