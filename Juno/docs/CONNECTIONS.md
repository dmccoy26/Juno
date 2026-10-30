# Connections in preview 8

Juno is a native Mac application. **Connections** provides two routes. TaskDock remains the task system of record. All refreshes are manual in this preview; no background provider polling, upstream writes or automatic task creation is enabled.

## Through TaskDock

The existing TaskDock tab continues to read consolidated tasks, subtasks, history and source freshness using the dedicated Juno credential already saved in Juno's Keychain. That credential is not a Gmail/Slack/Smartsheet credential.

The TaskDock build 15 candidate adds a supported source catalog and optional stored evidence. Install the candidate on the work Mac after quitting TaskDock, then use **TaskDock Settings → Connections → Juno**. Existing task-only access stays task-only. Select any additional sections, check the review acknowledgment and save:

| Grant | Shared stored content | Exclusions |
|---|---|---|
| Events | Nonarchived events, scheduled sessions, recurrence definitions | Archived events; budget; recurrence definitions are not expanded personal-calendar commitments |
| Notes | Nonarchived notebook titles and bodies | Archived notes |
| Recorded time | Nonvoided time records, worker, minutes and notes | Hourly rates, private fingerprints; recorded time is not a skill/performance score |
| Expenses | Nonvoided amounts, worker and notes | Currency is not established by this ledger; do not infer one |

In **Juno Connections → Through TaskDock**, discover with the local TaskDock API address and dedicated Juno token. A blank credential field reuses only Juno's own saved bridge token. Review the workspace/installation identity and selected sections, then read shared saved evidence. The API reads consistent pages; changed identity, changed revision, missing permission or incomplete pagination rejects replacement. Revoked permission retains a clearly inactive historical copy.

TaskDock's Gmail/Slack connections supply only records already imported as tasks. They do not provide a full inbox, all message bodies or conversation threads. TaskDock calendar delivery publishes its events outward; it does not read a personal calendar. Catalog buttons can open the corresponding direct setup form without moving any provider token or authorization.

TaskDock source changes are on branch `codex/juno-saved-evidence`, separately from Juno. The installed TaskDock build 14 and original checkout were not silently replaced or granted broader sharing.

## Direct programs

Configure these **on the approved work Mac**, in **Connections → Direct programs**. Persistent client details, access/refresh tokens, resource choices and cooldowns live in a separate macOS Keychain namespace owned by Juno. They are not copied from TaskDock, saved in PostgreSQL, sent to the model or synchronized to the laptop. Credential fields are secure and blank fields reuse the saved value. Saved normalized evidence includes account labels and the selected content, so use only approved accounts/resources.

Every direct read requires discovery of the account identity, your explicit resource/query selection and the review checkbox. Discovery reads account/resource labels, not message bodies. Changing coverage clears review. An account change requires another review before content can replace the current copy.

| Program | What to enter | Read coverage |
|---|---|---|
| Gmail | Approved Google Desktop OAuth client; sign in | Matching messages, safe plain-text body excerpts, unread-at-read flag. Default `in:inbox is:unread`; query controls coverage. No attachment/image fetch or mark-read |
| Google Calendar | Approved Google Desktop OAuth client; sign in | Selected calendars, explicit date window, expanded recurrences/exceptions; cancelled/self-declined events omitted |
| Google Tasks | Approved Google Desktop OAuth client; sign in | Selected lists, API-visible completed/hidden/assigned tasks, date-only due fields |
| Google Chat | Approved Google Desktop OAuth client; sign in | Selected `spaces/ID`, messages created in a date window; readable thread messages; no cards/attachments/membership changes |
| Slack | Institution-approved user/bot token | Selected conversation IDs and history window; optional readable replies to parents in the window. Older-parent replies can be missing |
| Smartsheet | Institution-approved API token | Selected sheet IDs, primary-column titles, readable cell excerpts; version consistency checked; no comments/attachments/checkbox writes |
| Outlook Calendar | Approved Microsoft public desktop client ID and tenant; sign in | Selected calendars via calendarView, explicit window, expanded occurrences; no invitations/attendee actions |

### Google setup

Use your institution-approved Google Cloud project. Enable the corresponding APIs: Gmail, Calendar, Tasks and/or Chat. Configure the consent audience and required organization/test users according to workplace policy. Create an OAuth client with application type **Desktop app**. Download its JSON and choose **Load Google Desktop client JSON…**, or enter the client ID and client secret from that approved registration. A web-client JSON is rejected. Juno uses fixed Google endpoints rather than any endpoints embedded in the file.

You can reuse one approved Desktop client registration across the four Google setup forms, but each provider has its own saved authorization and minimal scope request. Save setup, choose **Sign in for read access…**, finish provider consent in the system browser, then return to Juno. Browser consent does not turn Juno into a browser-tab application. The private callback is `http://127.0.0.1:<Juno-helper-port>/v1/providers/oauth/callback/google`; Desktop loopback clients support the dynamically selected port. Do not register a hosted callback or expose the helper publicly.

Requested scopes include `openid`, `email`, plus:

- Gmail: `https://www.googleapis.com/auth/gmail.readonly`
- Google Calendar: `https://www.googleapis.com/auth/calendar.calendarlist.readonly` and `https://www.googleapis.com/auth/calendar.events.readonly`
- Google Tasks: `https://www.googleapis.com/auth/tasks.readonly`
- Google Chat: `https://www.googleapis.com/auth/chat.spaces.readonly` and `https://www.googleapis.com/auth/chat.messages.readonly`

Organization policy/API enablement/consent verification can require administrator action. No live client registration or permission grant was created during development. Google testing-mode authorizations may expire according to Google's policy; use an approved production/internal configuration as appropriate. Refer to [Google's desktop OAuth instructions](https://developers.google.com/identity/protocols/oauth2/native-app), [loopback guidance](https://developers.google.com/identity/protocols/oauth2/resources/loopback-migration) and [Google Chat user authorization](https://developers.google.com/workspace/chat/authenticate-authorize).

### Slack setup

Use an approved Slack app/token with access only to the conversations needed. Juno does not create an app, install it into a workspace, join channels or request new workspace permissions. A token can itself hold broader privileges than Juno uses; the connector only issues the allowlisted read methods.

Typical scopes depend on conversation type: `channels:read`/`channels:history`, `groups:read`/`groups:history`, `im:read`/`im:history`, `mpim:read`/`mpim:history`. Grant only needed types under workplace policy. Public/private thread replies may require an approved **user token**, even when a bot token can read parent history. If discovery lacks list permission, Juno permits exact accessible conversation IDs rather than widening access automatically. If thread reads are denied, either obtain approved scope or explicitly exclude threads; Juno does not call a partial result complete. [Slack history](https://docs.slack.dev/reference/methods/conversations.history/) and [reply requirements](https://docs.slack.dev/reference/methods/conversations.replies/).

### Smartsheet setup

Enter your approved API token, discover account/sheet labels, and select up to ten sheets or enter exact numeric sheet IDs. Juno only performs GET `/2.0/users/me`, `/2.0/sheets` and `/2.0/sheets/{id}`. No task-column mappings are required for this evidence reader; it uses the sheet's primary column and readable cell labels. A sheet changing between pages rejects the new copy. Use a smaller sheet if the row/request bound is exceeded. [Official sheet API](https://developers.smartsheet.com/api/smartsheet/openapi/sheets/getsheet).

### Microsoft setup

Use an approved Microsoft Entra app registration for a public desktop client. Register the **Mobile and desktop applications** loopback redirect `http://localhost/v1/providers/oauth/callback/microsoft`, and configure public-client authorization as required by your institution. Juno supplies its helper port at sign-in; Microsoft documents localhost loopback port matching for native clients. Enter the client ID and approved tenant ID/domain (default `organizations`). Juno does not use a confidential web-client secret for Microsoft.

Juno requests delegated `User.Read`, `Calendars.Read` and `offline_access`. Read access includes event body excerpts, so this uses Calendars.Read rather than a basic-details scope. Administrator consent may be required. [Authorization-code/PKCE flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow), [redirect URI rules](https://learn.microsoft.com/en-us/entra/identity-platform/reply-url) and [calendarView API](https://learn.microsoft.com/en-us/graph/api/calendar-list-calendarview?view=graph-rest-1.0).

## Reading, failures and removal

After sign-in/token save: **Discover account and resources → select resources/query and date window → review → Refresh read-only copy**. Credentials renew on a requested read when possible; rotating refresh tokens are saved before continuing. OAuth uses state + S256 PKCE, a bounded ten-minute in-memory session and protected native token delivery. Juno acknowledges delivery only after Keychain save; dropped polling responses can be retried. Cancel closes the pending Juno session; it does not revoke permissions in the provider's settings.

Direct source reads are capped at 5,000 normalized records / 8 MB, 50 pages, 250 requests and 90 seconds. Timed sources require a 1–366 day window; at most ten resources are selected. Gmail also caps matching message reads at 500. Responses/text/MIME depth are bounded. Source APIs are often sequential rather than atomic; coverage and known omissions are displayed. Rate limiting preserves the old copy and shows a retry time. Narrow selection rather than repeatedly requesting an oversized feed.

Each owner keeps one current copy per provider; replacing/removing it invalidates derived saved AI replies. Transient outages retain dated evidence with the error. Revoked authorization/unavailable resources mark retained content inactive and exclude it from new model context. Disconnect and authorization denial also advance the source version: a refresh that started earlier cannot reactivate the copy afterward. Its retained text and original read time do not change. **Disconnect and forget** removes this Mac's credential and marks its copy inactive; **Evidence → Remove copy** removes the imported text. Removing a network-source copy erases its source text and account/resource metadata from canonical storage, retaining only a content-free version marker to reject older in-flight reads. That marker is available only to local connection setup, and is excluded from Evidence, model context and laptop exports. It also protects a cancelled first read before any copy existed. Neither action deletes original provider data or revokes provider authorization. For complete provider-side revocation, use that provider's account settings.

TaskDock and direct providers can overlap. Juno labels routes and warns the local model to use TaskDock as the task authority and avoid duplicate actions. This is not a universal cross-system deduplication engine. Date-window absence is not proof a person/room is free, and reported work time does not establish employee skill or job performance.

The laptop receives dated evidence in its existing private cache. It cannot administer providers or refresh sources remotely. Offline removal cannot wipe an already disconnected laptop; synchronize to receive updates. No cloud model fallback or credential sync was introduced.

## Verification scope

Automated tests use fictional transports and disposable PostgreSQL/SQLite data. They cover all seven readers, account review, safe text/MIME handling, fixed read destinations, pagination/version/next-link failures, scope/expiry/cancellation/replay, native Keychain persistence and protected delivery. An actual local-HTTP test runs the two real applications' APIs together with 501 synthetic notes, permission revocation and owner isolation. Relocated bundled Python runs provider fixtures with networking disabled. Native UI acceptance covers discovery, selection, refresh and review reset. Live consent, institutional policy, retention behavior on real accounts and actual laptop offline acceptance remain to be tested by Dan.
