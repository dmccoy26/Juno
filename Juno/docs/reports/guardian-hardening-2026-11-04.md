# Juno response to Guardian — November 4, 2026

## Conclusion

The reviewed warnings did not establish an exploitable production vulnerability. We nevertheless hardened the build/download and disposable verification helpers and tested the boundaries. Original Guardian reports were preserved. No credentials were rotated, no Git history was rewritten, and no installed app, network hosting configuration, or institutional service was changed.

## Changes and finding disposition

- **ab567d572d9ec54d — runtime downloads:** require credential-free HTTPS on the standard port for the initial URL and every redirect. Only plain filenames and pinned SHA-256 digests are accepted. Cache symlinks are rejected. Downloads use unique temporary files, must match the digest before becoming the cached artifact, and are removed on failure. Existing cached files are rechecked. Publisher URLs remain project-controlled; publisher fingerprint provenance is not independently certified by this change. HTTPS redirects to other hosts remain permitted for publisher/CDN delivery; the pinned digest determines accepted content.
- **6f6538e288c8c0a4 — TaskDock bridge verifier:** the warned permission-changing request now uses the restricted local HTTP helper. It accepts literal loopback addresses with explicit ports, rejects credentials and fragments in URLs, refuses redirects, and disables environment proxies. The bridge still uses synthetic keys/data. The original live bridge was not rerun; its request transport was exercised through shared-helper regression tests. The existing free-port allocation race is not eliminated.
- **c0a2b930a3936b08 — installer verifier:** uses the same restricted local helper, plus origin/path validation. Non-loopback destinations fail before network access. HTTP error responses are explicitly closed. A local HTTP server test proves the verifier can read the expected endpoint and will not follow a redirect to another path. The whole installer verifier was not rerun and no package was rebuilt for these helper-only changes.
- **934516e20b8d3ca9 — all-interface shared listener:** unchanged and still flagged. This is intentional opt-in LAN hosting, protected by TLS, private-client address checks, route restrictions, and authenticated work-data endpoints. It permits standard private ranges, not only 10/8. Source review and synthetic tests support these controls; this is not an independent penetration test. Binding broadly continues to expose the TLS listener to reachable interfaces.

## Executed checks

**190 backend tests passed, zero failures/errors/skips**, including four new helper regression tests. Tests ran against a separate, disposable PostgreSQL cluster over a private Unix socket. The cluster was stopped afterward. Work databases and real user records were not used.

Coverage includes invalid/revoked authentication, owner isolation, single-use/expired invitations, restricted host administration, offline retry/conflict handling, worker-access boundaries, planning continuity, and the new helper boundaries. Passing this suite is evidence for the tested paths, not proof of every security requirement.

New helper tests cover: nonlocal destinations rejected before network access; real local HTTP success; redirects refused without hitting their target; environment proxies ignored; insecure runtime URLs/redirects rejected; unsafe filenames/digests rejected; corrupted downloads and cache rejected; temporary cleanup; and cache symlink rejection. Downloads in these tests were mocked; no publisher was contacted by the tests.

**Semgrep 1.183.0**, `p/security-audit`, metrics/version checks disabled: scanned the four helper files and shared-host module, **zero scanner errors and one remaining finding**, the intentional `0.0.0.0` listener. The three original dynamic-urllib warnings were not reported by this targeted rescan. This does not make relocation into a helper, by itself, proof of safety; validation and regressions provide the additional evidence. Other Juno files were not rescanned with Semgrep in this run.

**Trivy 0.76.1**: vulnerability database updated successfully. A direct scan of `requirements.lock` completed but recognized zero dependencies and is not counted as a successful dependency assessment. Unchanged copies of the backend and backup lockfiles named `requirements.txt` were then scanned: **29 backend package entries plus 3 backup package entries recognized; zero known vulnerabilities reported**. This assesses the pinned Python dependencies recognized by Trivy as of the scan database, not all bundled native libraries, Python/PostgreSQL runtime components, or future advisories. It does not establish the cause of Guardian's earlier Trivy exit 1.

`git diff --check` passed. No new live work-service requests were made; the scanners downloaded public rules/advisory data.

## Remaining checks

- Git history and secret scanning were not run.
- Full installed-app, binary dependency, macOS permissions/Keychain, and release-signing assessment were not repeated.
- Publisher fingerprint provenance and runtime archive extraction remain separate supply-chain review topics.
- The full TaskDock bridge and relocated installer end-to-end runs were not repeated.
- Rate limiting, denial-of-service resistance, hostile LAN tests, and a complete privacy/AI-action audit are outside this patch's verification.

The companion JSON contains exact source fingerprints and compact test/scanner results so Guardian can invalidate this review if the relevant source changes. This is a targeted hardening report, not a whole-app security certification.

## Reproduction

```sh
# Set JUNO_TEST_ADMIN_URL to a disposable PostgreSQL cluster, never a work database.
.venv/bin/python -m unittest discover -s backend/tests -v
semgrep scan --config p/security-audit --metrics off --disable-version-check \
  scripts/helper_http.py scripts/fetch_runtimes.py scripts/verify_installer.py \
  scripts/verify_connections_bridge.py backend/src/juno/shared_host.py
# Copy each requirements.lock unchanged to a separate temporary requirements.txt,
# then scan the temporary directory, confirming recognized package counts.
trivy fs --scanners vuln --list-all-pkgs /path/to/temporary-dependency-copies
```
