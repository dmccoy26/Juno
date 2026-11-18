# Connect a work Google Calendar to Juno

Juno uses a reviewed read-only calendar connection. Keep OAuth configuration and tokens private in macOS Keychain. Busy/free-only storage omits event titles, descriptions and locations. Automatic refresh is opt-in and runs on the awake work Mac while Juno is open; the paired laptop uses its dated copy.

## Create the Google configuration

1. Open [Google Cloud Console](https://console.cloud.google.com/) with the work account. Select an authorized university project or create **Juno Work Companion** if permitted.
2. Open **APIs & Services → Library**, find **Google Calendar API**, and enable it. This follows Google’s [Calendar setup guide](https://developers.google.com/workspace/calendar/api/quickstart/python).
3. Open **Google Auth platform → Branding**. Set the app name to **Juno Work Companion**, select the support email and enter the developer contact email.
4. In **Audience**, choose **Internal** when the project belongs to the university’s Google Workspace organization. If project creation or the appropriate organization setup is unavailable, ask IET to provision it. Google documents the organization and audience options in its [consent-screen guide](https://developers.google.com/workspace/guides/configure-oauth-consent).
5. If a Data Access scope selection is needed, use Juno’s actual calendar scopes: `https://www.googleapis.com/auth/calendar.calendarlist.readonly` and `https://www.googleapis.com/auth/calendar.events.readonly`. Juno also uses `openid` and `email` for account identity. The source of truth is `backend/src/juno/providers/oauth.py`; these are the scopes Juno requests at sign-in.
6. In **Google Auth platform → Clients → Create client**, choose **Desktop app** and name the client **Juno Work Mac**. Download the JSON configuration and retain it privately on the Mac. Google’s [credential instructions](https://developers.google.com/workspace/guides/create-credentials) explain Desktop app clients. Juno expects a JSON file containing an `installed` section. Juno handles its own local browser callback.

For an externally configured testing app, Google can expire calendar refresh tokens after seven days. Use the organization’s approved deployment configuration for ongoing use rather than treating a testing authorization as permanent. See [Google’s token-expiration documentation](https://developers.google.com/identity/protocols/oauth2#expiration).

## Finish in Juno

1. Open **Settings → Connections → Direct programs → Google Calendar**.
2. Choose **Load Google Desktop client JSON…**, select the downloaded file, then **Save app setup**. Credentials remain in this Mac’s Keychain.
3. Choose **Sign in for read access…** and complete Google’s account selection and consent in the browser. Select the work account.
4. Choose **Discover account and resources**. Confirm the account and select the main work calendar. `primary` is the exact resource ID for the signed-in account’s primary calendar; a discovered named calendar is easier to verify visually.
5. Choose a coverage window including today and the upcoming planning weeks. Set **America/Chicago**. The Until date is exclusive. Juno accepts 1–366 days.
6. In 0.2.22 or later, keep **Save busy/free times only** on to omit titles, descriptions and locations before storage and model context. Busy/free times and all-day status still support planning.
7. Check **I reviewed the account, selection and coverage**, then choose **Refresh read-only copy**.

Verify that Sources shows a successful Google Calendar read and Today lists the expected commitments. Compare at least one actual meeting time against Google Calendar before relying on work-window suggestions. Busy time excludes the owner’s work and supervised work; independently qualified staff can still have their own available windows. Classes, staff shifts, room access, holds and weekly limits remain additional constraints. Calendar data does not grant room access or establish staff capability.

### Automatic refresh in 0.2.24

After discovering the account, selecting the calendars and reviewing the coverage/privacy choice, choose **Enable automatic calendar refresh**. Close Settings to allow the first automatic read. Juno checks every 30 seconds and refreshes when 15 minutes have elapsed since its last attempt. Keep Juno open on the work Mac and the Mac awake. A restart or wake catches up at the next check; missed intervals do not create a backlog. This does not run a separate cloud service or refresh on the paired Air.

Each read requests **seven days back through 90 days ahead**, calculated as Central calendar days (exclusive end: today + 91 days), including daylight-saving changes. Existing account, selected calendars and busy/free-only choice are retained. OAuth access renews through the saved Keychain credential; no broader scopes are requested. Changing the approved account, calendar IDs, client, timezone or privacy setting pauses automatic reads until reviewed again. Disconnecting turns them off. Settings offers **Turn off automatic calendar refresh**.

Today shows automatic-refresh status and the last successful copy/coverage. A successful automatic read reloads Today and the room/person availability calculation. Failures retain the earlier copy and successful timestamp, show a retry notice, and retry after at least 15 minutes (or a longer provider rate limit). Authorization denial or a changed account pauses automatic reads and requests sign-in/review. Personal or supervised work cannot be reserved outside the calendar’s saved date range or when the calendar has a recorded refresh failure. Independently qualified staff remain governed by their own availability.

**Reload agenda/status** reads saved data only. The manual **Refresh read-only copy** remains available; after automatic refresh is enabled for the saved selection, it also uses the rolling date window. Before using suggestions, review warnings and compare a known meeting against Google Calendar.

## IET request, if needed

Please provision an approved Google Desktop OAuth client for Juno Work Companion, accessing my primary work calendar. Juno uses Calendar API read-only calendar-list and event scopes plus basic account identity, local browser sign-in with PKCE, macOS Keychain credential storage, and approved local processing. I need the downloadable Desktop client JSON or the university’s supported equivalent. Event changes, attendee changes and email access are outside this calendar connection.
