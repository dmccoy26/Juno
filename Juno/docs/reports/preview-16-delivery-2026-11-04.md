# Preview 16 delivery — November 4, 2026

User authorized updating the installed Juno app, adding its version beside the name and pushing the Juno work to GitHub. Release `0.1.0-preview.16`, build/receipt `16` / `0.1.0.16`.

## Verified delivery

- Header reads the bundled release metadata and displays `0.1.0-preview.16` immediately beside Juno. The actual work-host window was visually inspected and showed Connected · This Mac.
- Complete backend/PostgreSQL suite: 186 passed, zero skips. Extracted/relocated installer: 148 bundled-runtime fixture tests passed with external networking disabled, including daily briefing and reviewed carry/Dean-draft suites. Existing deprecation/runtime annotation warnings did not fail these checks.
- Installer verification passed extraction/preinstall guards, application resource seals, 239 Mach-O dependency checks, bundled API/provider/planning/worker isolation, restart/offline/pairing behavior, parent-loss cleanup and schema-1 upgrade with a readable pre-upgrade backup and preserved memory. Full evidence: `installer-preview-16.json`.
- Installer SHA-256: `0abc51cf1d200b32c16349bbee22504cd117161c67c020fba62284be5a102ec3`.
- Active development work-host installation `~/Applications/Juno.app` was updated with a signature-verified replacement and reopened successfully. Earlier bundles are retained privately for rollback. Private read-only before/after comparisons match all prior work records, owner, planning/schedule context, existing paired-device states, worker configuration and shared/worker TLS files. Startup's normal local credential rotation is excluded from the preserved paired-device invariant.
- The pre-0012 dump created by normal startup passed `pg_restore --list`. The new provenance/draft tables are empty on the work host; no fictional records were inserted there. Existing encrypted backup scheduling was not changed.

## Administrator installation boundary

The root-owned standalone copy `/Applications/Juno.app` could not be renamed/replaced without administrator authentication. An attempted two-copy replacement was rolled back before applying the work-host update separately. `sudo -n` confirmed authentication is required; no password was requested or security protection bypassed. The root-owned copy remains its prior version. Its separate Application Support data matches its pre-update file fingerprints exactly.

The verified preview.16 package and setup/checksum files are available locally for an administrator-approved standalone/laptop installation. Updating that copy has not been reported as completed. A physical M5 laptop trial and broader Mission 12 timed acceptance remain open. No TaskDock service, cloud grant, source refresh, worker message or automatic employee assignment was performed.

GitHub publication scope is Juno source, release metadata, tests and public documentation. Private databases, backups, certificates/keys, owner/credential files, real-work screenshots and installer binaries are excluded. Unrelated root README/Guardian/SnapShot changes are preserved.
