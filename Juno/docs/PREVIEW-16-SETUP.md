# Preview 16 — daily check-in, reviewed planning and saved Dean drafts

Release: `0.1.0-preview.16`, build 16. Juno's version is visible beside her name in the main header and in About/footer.

## This work Mac

The active work-host copy at `~/Applications/Juno.app` is updated, connected and uses its established data root. Its owner, existing records, prior paired devices, worker configuration and certificate/key passed private before/after checks. Startup made a readable pre-migration backup before adding schema `0012_daily_planning`. Only the temporary local app credential rotated normally. No real task/diary was used for a mutation test.

The older root-owned `/Applications/Juno.app` is a separate standalone installation. macOS requires administrator authentication to replace it; it was not updated by the direct work-host replacement. Its existing `~/Library/Application Support/Juno` data is unchanged. Continue opening `~/Applications/Juno.app` for the current work host. Installing/reopening the standalone copy does not automatically merge these two established data roots.

## Portable installer

Verified installer: `dist/Juno-0.1.0-preview.16-macOS-arm64.pkg`, with SHA-256 sidecar. A copy, checksum and this guide are in `~/Downloads/Juno-0.1.0-preview.16`.

Quit Juno before running the installer, then approve macOS's administrator authentication as the authorized user. It replaces the application bundle at `/Applications/Juno.app`; it does not relocate or merge Juno databases. A paired laptop retains its existing profile and data root; connect to the updated work Mac for new planning/Dean-draft actions. Physical laptop upgrade/outage acceptance remains separate from local package verification.

This is the existing internal Apple Silicon preview distribution: ad-hoc app signature, no Developer ID notarization. It includes Python/PostgreSQL and needs no source checkout on a recipient Mac.

## New workflow

1. Open Daily check-in, review saved context and answer/skip the five questions.
2. Review and confirm the diary. Next-workday proposals stay separate from recorded accomplishments and do not book or assign work.
3. Choose Carry a reviewed detail into Plan, select the exact task/excerpt and fields, review before/after, then save. Read the provenance later under Plan → Reviewed check-in sources.
4. Open Plan → Open weekly Dean drafts. Choose the period, prepare/edit and save. Reopening keeps reviewed writing; fresh preparation appears separately. Compare saved copy resolves concurrent or recovered writing. Juno does not send the draft.

See [full workflow and limits](DAILY-CHECKIN-PLANNING.md), [mission](missions/2026-11-03-12-daily-planning.md), [feature evidence](reports/planning-continuity-2026-11-04.md) and [installer evidence](reports/installer-preview-16.json).
