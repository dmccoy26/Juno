# Automatic backup setup — November 2, 2026

User requested automatic backups to `/Volumes/personal_folder`. Scope implemented: Juno's approved work-Mac workspace at `/Users/dmccoy/Ai/Juno/.local`. TaskDock/Beacon/whole-Mac backups were not changed.

## Completed

- Verified the existing personal SMB share is mounted and writable. Created only `Juno Backups/Work Mac` and a destination identity marker under it.
- Added an isolated backup runtime and AES-256-GCM authenticated encrypted snapshot script, separate from application dependencies. Pinned cryptography/runtime dependencies; no provider credentials or machine keys entered Git.
- Included a consistent PostgreSQL custom dump plus owner/host/worker/offline-copy recovery files and checksummed manifest. Excluded raw live database files, test/debug data, app/code bundles, logs, Keychain secrets and ephemeral local app tokens.
- First encrypted snapshot saved November 2 at approximately 5:36 PM America/Chicago. Database schema 0011. No work content was printed during verification.
- Restored the actual first database dump into a unique temporary database; checked schema and owner, then removed only that temporary database. Original work database was not replaced or interrupted.
- Read the saved network archive back, authenticated/decrypted/extracted it, checked every manifest hash and verified its PostgreSQL archive contents.
- Synthetic tests passed encryption round-trip, wrong-key and modified-ciphertext rejection, retention selection and missing-volume refusal. A cold synthetic cluster was started only under the desktop lock, dumped/restored into an isolated verification database, and stopped afterward.
- Installed `com.dmccoy.juno.backup` as a per-user hourly LaunchAgent with RunAtLoad. Private script/runtime/config/status live in `~/Library/Application Support/Juno Backups`; logs in `~/Library/Logs/Juno Backups`.
- Retention: 48 newest successful snapshots, daily snapshots for 30 days and monthly snapshots for current/previous 11 calendar months, with deletion only after a new verified success. No existing backup/history/report data was pruned.
- Private encryption key remains local; a separate recovery kit is at `~/Downloads/Juno-Backup-Recovery`. Owner must keep an approved secure copy separate from the encrypted destination. No key was put on the NAS or in Git.

## Scheduled-run acceptance still blocked

The LaunchAgent's first run started but blocked opening a file before creating a temporary dump. Process sampling showed a blocked `open`; macOS TCC logs attributed an access request to the background Python process. Native inspection reported the Mac locked. An asynchronous request asked the owner to unlock and allow the network-volume prompt if displayed. No privacy settings were bypassed or silently broadened.

The manual end-to-end backup is verified. The hourly LaunchAgent is installed, but unattended execution is **not yet verified**. After the owner approves the narrow network-volume access, check the job's exit status, a new successful status/log entry and a new authenticated snapshot. Keep this gate open until observed. Do not confuse the first manual success with a scheduled success. The current manual backup remains available regardless of that pending permission.

## Limits

The job runs while the user is logged in and the Mac is awake; it does not mount the share, store SMB credentials or wake/login the Mac. Missing destinations fail safely and retry at a later scheduled run. macOS permission denial must be resolved by the owner. There are no outbound notifications or cloud copies. Keychain source connections and unsynchronized laptop-only edits require separate recovery. Replacement-Mac recovery and production restore/cutover were not performed.

See [operator and recovery guide](../AUTOMATIC-BACKUPS.md). Deployment is local to this work Mac; no application rebuild or laptop installation is needed for this host job.
