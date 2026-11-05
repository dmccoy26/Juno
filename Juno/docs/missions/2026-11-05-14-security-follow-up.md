# Mission 14 — Secure Juno’s runtime cache and verify LAN sharing

**Outcome**

The runtime downloader keeps writes inside its intended cache, and current LAN sharing passes access and certificate checks in a disposable environment. A fresh Guardian scan records what changed and which checks still need coverage.

Use the November 5 Guardian 0.14.0 build 25 rescan as the starting point. It reported one remaining LAN warning, three earlier address warnings that did not recur, and zero verified fixes in Scan History. A separate helper test reproduced the cache folder issue. [Rescan summary](/Volumes/Ai/Guardian/Development/Juno-rescan-20261105.Gtw5fJ/Summary.md)

## 1. Close the runtime cache write escape

- Harden `scripts/fetch_runtimes.py` so symlinks in the cache path cannot redirect temporary downloads, final writes, or cached reads. Account for the directory being swapped between validation and use. Use directory-relative file operations anchored to an opened, verified directory where supported.
- Preserve pinned SHA-256 checks, atomic publication after verification, reuse of a valid cache entry, cleanup after failed downloads, and permitted HTTPS publisher-to-CDN redirects.
- In a disposable fixture, place symlinks at the cache directory, an intermediate component such as `.local`, and the destination entry. Test replacement during download. Confirm the outside folder stays untouched, including when a download fails. Also test a normal download and cache hit using synthetic bytes.
- Rerun the installer and bridge helper checks. Confirm allowed loopback requests still work and outside addresses, redirects and proxy settings cannot reroute them.

## 2. Retest current LAN sharing

- Treat the listener in `backend/src/juno/shared_host.py` as an open exposure question. Check whether sharing needs to listen on every IPv4 interface. Narrow the binding if supported workflows allow it. If the broader binding is required, document why and verify which clients and routes are reachable.
- Use a disposable macOS VM or isolated lab with fictional users, devices and records. Confirm sharing starts off by default, listens only after opt-in, and stops accepting connections when disabled. Exercise successful pairing and profile restoration as well as invalid, expired and replayed invitations.
- Check that the client rejects a wrong or changed certificate and that an unpaired or revoked device cannot read records after reconnecting or restoring its saved profile. With two fictional users, attempt cross-user reads in both directions, including direct requests by record ID. Confirm each user can still read their own authorized records and that remote clients cannot call local-only administration routes.

## 3. Account for the scan gaps

- Rescan with the updated Guardian. Record which files and package manifests were checked. If Trivy fails again, capture its failure reason separately and retain the offline dependency results with their scope.
- Review the Swift paths involved in pairing, certificate handling and access checks. Record which paths Guardian traced and which needed manual review or focused tests. Hand parser and cross-file resolution gaps back to Guardian with a small synthetic reproducer when possible.
- Establish Juno’s Git history boundary before running Gitleaks. Use an authorized Juno-only history scope or record the gap. Keep findings redacted and exclude unrelated projects in the enclosing checkout.

## Acceptance

- The previously failing cache-folder test passes on the updated source. The outside fixture remains untouched during link replacement, and normal downloads and cache reuse still pass.
- The LAN lab records pass or fail results for authorized access, bad certificates, revoked devices, cross-user reads and local-only administration. If the listener still binds to every interface, the evidence explains why and documents the restrictions tested.
- The follow-up separates verified fixes, warnings that disappeared, intentional behavior and open coverage gaps. Attach the commit or source fingerprints, commands, scoped test results and the new Guardian report so each conclusion can be checked.
- Keep new evidence in a separate folder under `/Volumes/Ai/Guardian`. Preserve the original reports and evidence. Use command-line tests on the Mac and run any UI interaction inside the disposable VM.
