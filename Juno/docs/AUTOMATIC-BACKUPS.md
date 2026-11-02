# Automatic work-Mac backups

Configured November 2, 2026 for the current Juno work-Mac workspace. This is a host backup service, independent of Juno's app installer and the laptop. It does not back up TaskDock, Beacon or the entire Mac; existing backup jobs for those programs are unchanged.

## Schedule and location

- Destination: `/Volumes/personal_folder/Juno Backups/Work Mac` on the owner's mounted personal SMB share.
- Runs hourly while the user is logged in and the Mac is awake, plus at job load/login. macOS may delay a run during sleep; this does not wake the Mac or log the user in.
- A missing/unmounted share is an error. No substitute directory is created on the Mac. The destination marker must match; the next scheduled run retries. No share password, automatic remount or network/security setting was added.
- Retention keeps the 48 newest successful snapshots, plus the newest available snapshot per day for 30 days and per month for the current and previous 11 calendar months. It cannot create historical coverage before backups started. Only this job's strictly named backup files are pruned, after a new backup succeeds; unrelated files and pre-migration backups remain untouched.
- Every retained snapshot contains the complete then-current report history. Snapshot rotation does not impose an age limit on live worker reports. Deleted/corrected source material can remain in older backups until those versions rotate out.

## Contents and protection

Each `.junobak` is an AES-256-GCM authenticated encrypted archive containing a consistent PostgreSQL custom-format dump, a manifest with checksums/schema, and recovery configuration: desktop owner identity, laptop-host settings/certificate/key, worker-host settings/certificates/keys and any host-local offline copies. Files are explicitly selected; raw running PostgreSQL files, debug/test data, source checkout, app bundles, logs and temporary desktop bearer credentials are excluded.

macOS Keychain credentials, source-provider passwords, LM Studio model files and unsynchronized laptop-only edits are not backed up by this host job. Some source connections may need reauthorization after recovery. Existing app/source installers remain separate from data backups. The configuration files can contain absolute paths that require review on a replacement computer.

Backup records and private recovery keys never belong in GitHub. The encryption key is a private 32-byte file at `~/Library/Application Support/Juno Backups/recovery.key`. A separate private copy and instructions are in `~/Downloads/Juno-Backup-Recovery/`. Move/copy that recovery kit to an approved secure place separate from the backup share. Loss of all copies of the key makes these encrypted backups unreadable. Do not place the key beside the encrypted files, email it or include it in diagnostics. No Keychain secrets were exported.

Before publishing a snapshot, the job restores its dump into a uniquely named disposable database, verifies its schema and work-owner identity, then drops only that verification database. It never restores over Juno. It copies the encrypted archive to a partial network file, reads it back, compares checksums, authenticates/decrypts it and compares plaintext archive hashes before finalizing the filename. A `.sha256` companion aids transfer checks; authenticated decryption is the stronger integrity check.

When PostgreSQL is stopped, the job obtains Juno's desktop lock, temporarily starts the private Unix-socket-only cluster and stops it afterward. When Juno's database is already running, `pg_dump` takes a consistent online snapshot without quitting Juno. An app/database shutdown mid-run can fail that attempt; earlier backups remain. Recovery-file changes during a run also reject that run for safe retry. Ordinary failures clean up temporary plaintext files, which stay in a private local temporary directory while needed.

## Status and manual run

LaunchAgent: `~/Library/LaunchAgents/com.dmccoy.juno.backup.plist`.

Private configuration, deployed script, isolated Python runtime and latest attempt status: `~/Library/Application Support/Juno Backups/`.

Logs: `~/Library/Logs/Juno Backups/backup.log` and `backup-error.log`. A successful status names the completed backup and marks `restore_tested: true`. A failure is not a successful snapshot; check the last successful log entry as well as the most recent attempt. There are no automatic email/Slack alerts.

Run a backup manually:

```sh
"$HOME/Library/Application Support/Juno Backups/runtime/bin/python" \
  "$HOME/Library/Application Support/Juno Backups/automatic_backup.py" \
  --config "$HOME/Library/Application Support/Juno Backups/config.json"
```

The job's lock prevents concurrent scheduled/manual runs. The script/runtime are deployed outside the checkout, so ordinary Git changes do not silently alter the scheduled job. Script updates need review, verification and copying to the deployed location. Runtime dependencies are pinned in `scripts/backup-requirements.lock`; application backend dependencies are unchanged.

## Recovery procedure

Preserve the original archive, checksum and recovery key before doing anything else. Choose a new private local directory for authenticated extraction:

```sh
"$HOME/Library/Application Support/Juno Backups/runtime/bin/python" \
  "$HOME/Library/Application Support/Juno Backups/automatic_backup.py" \
  --config "$HOME/Library/Application Support/Juno Backups/config.json" \
  --extract "/absolute/path/to/chosen.junobak" \
  --output "/absolute/path/to/new-private-recovery-directory"
```

Extraction requires the correct key and refuses an existing output directory. It does not alter any database. On a replacement Mac, prepare Python plus the pinned backup dependencies, script and private config pointing to the saved recovery key first. Decryption/extraction does not require the original network mount.

Verify manifest hashes and use PostgreSQL 17's `pg_restore` to restore `database.dump` into a **new isolated database**, checking schema and records against the manifest and expected work history. Have the matching Juno software/schema available. Review certificates, absolute paths, permissions and connection reauthorization. Restoring old authentication records can revive formerly revoked access: keep host listeners disabled, invalidate old enrollment/browser sessions and review/re-enroll paired devices before any production cutover. Do not replace a live data directory, restore private keys into a running host or enable another laptop host automatically. Preserve current data and a rollback backup until the recovered workspace is approved.

The initial real backup passed an isolated database restore and remote authenticated readback. Synthetic tests cover encryption round-trip, changed ciphertext/wrong-key rejection, retention selection, missing-drive refusal and cold-cluster lifecycle. The first actual LaunchAgent run is checked separately in the implementation report. These checks do not establish recovery on a physically different replacement Mac.
