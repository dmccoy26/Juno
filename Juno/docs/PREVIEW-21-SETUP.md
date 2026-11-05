# Preview.21 — workspace continuity safeguards

Installs the native Juno app at `/Applications/Juno.app`; the active workspace remains `~/Library/Application Support/Juno`. No schema migration is added.

Startup pins the established workspace path and owner. Missing identity settings, a missing established database or a mismatched owner produce an explicit recovery error instead of an empty replacement workspace. Device credentials continue rotating normally. New installations are allowed only with an empty database and no established identity.

Before starting a different release, Juno creates a private PostgreSQL dump and settings archive, including hosting certificates/configuration and owner identity, even if the schema is unchanged. Startup stops if that backup fails. Existing encrypted automatic backups remain independently configured; this Mac's destination is unchanged.

Updates require a private before/after baseline, verified package, actual installation and native checks. See [preservation gate](INSTALLER-PREVIEW.md) and `scripts/check_update_preservation.py`. A changed record or schema requires review; the tool does not reset data or treat differences as automatic permission to repair.

An intentional move to another Mac or data root needs an explicit recovery/pairing workflow; copying only identity settings is insufficient. Preserve source data and resolve conflicts before updating the pin. This release does not automatically merge development databases or change worker/laptop permissions.
