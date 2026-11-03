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

## Initial scheduled-run blocker — resolved November 3

The LaunchAgent's first run started but blocked opening a file before creating a temporary dump. Process sampling showed a blocked `open`; macOS TCC logs attributed an access request to the background Python process. Native inspection reported the Mac locked. An asynchronous request asked the owner to unlock and allow the network-volume prompt if displayed. No privacy settings were bypassed or silently broadened.

At the end of November 2, the manual end-to-end backup was verified and the hourly LaunchAgent was installed, but unattended execution remained unverified. The acceptance gate required a successful background exit/status and a new authenticated snapshot. The November 3 results below close that gate; the initial manual backup remained available throughout.

## Limits

The job runs while the user is logged in and the Mac is awake; it does not mount the share, store SMB credentials or wake/login the Mac. Missing destinations fail safely and retry at a later scheduled run. macOS permission denial must be resolved by the owner. There are no outbound notifications or cloud copies. Keychain source connections and unsynchronized laptop-only edits require separate recovery. Replacement-Mac recovery and production restore/cutover were not performed.

See [operator and recovery guide](../AUTOMATIC-BACKUPS.md). Deployment is local to this work Mac; no application rebuild or laptop installation is needed for this host job.

## November 3 acceptance result

Owner unlocked the Mac and requested a retry. The actual LaunchAgent had already completed multiple overnight backups, with its latest recorded success at 8:47 AM America/Chicago. Triggered the same installed job with `launchctl kickstart`, not a foreground substitute. Run 10 completed at 9:11 AM America/Chicago (15:11:23 UTC), exit code 0, and produced a new encrypted archive in the configured network directory. Its status and manifest marked the isolated database restore check successful. Independently read the remote file, checked its companion SHA-256, authenticated/decrypted the archive and verified the database payload hash.

The scheduled-run acceptance gate is now closed successfully. Hourly interval remains 3600 seconds. No permission, trust, mount, firewall, database or job configuration change was needed for this retry. Existing sleep/login/share-availability limitations and recovery-key requirements still apply.

## Computer-named destination — November 3

At the owner's request, confirmed the actual macOS ComputerName and LocalHostName are `AHMX-danielmc-MacStudio`. Paused the idle LaunchAgent, held its backup lock, renamed `Work Mac` to `AHMX-danielmc-MacStudio` and atomically updated its private destination configuration. All 23 existing files and the destination identity marker were preserved. The encryption key and retention policy were unchanged.

Reloaded the same hourly job. Its next actual background run completed at 9:13 AM America/Chicago with exit code 0 in `/Volumes/personal_folder/Juno Backups/AHMX-danielmc-MacStudio`. Isolated database restore was marked successful; independent remote checksum, authenticated decryption and database payload hash verification passed. No computer hostname was changed.
