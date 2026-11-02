# Worker HTTPS and 10/8 restriction

November 2, 2026. Preview.14 configures the owner-requested work-Mac worker endpoint at `https://10.3.66.50:8444/worker`. Worker hosting is now enabled at the owner's explicit request. No invitation was generated or sent by this setup.

## Configuration and boundaries

- Literal-IP listener binds only `10.3.66.50:8444`, confirmed by the actual listening socket. Laptop pairing at port 8443 and its certificate remain unchanged.
- Remote worker requests require an actual IPv4 peer in `10.0.0.0/8`. Local loopback diagnostics remain allowed. Other private ranges, public addresses and remote IPv6 are denied. Forwarded-IP headers do not alter the decision; proxy-header interpretation is disabled. This is an application restriction, not a new macOS firewall/router policy or a claim that an outside client cannot initiate a TLS handshake.
- TLS leaf certificate has only the IP SAN `10.3.66.50`; it does not use an IP wildcard. Its separate private issuing CA has a 10/8 IP name constraint, path length zero and a reserved `juno-worker.invalid` DNS constraint. The leaf CN uses that reserved name to satisfy the CA's DNS constraint; connection identity is the exact IP SAN.
- The server leaf lasts one year; its private CA lasts ten years. Both private keys remain under the work Mac's private Juno state with restrictive permissions and are not in the installer, repository or public trust-file folder. Renew the leaf before expiry; a changed server IP requires updated configuration/certificate.
- No system/browser trust, password, firewall rule, router or public tunnel was changed. The public CA still requires installation through each device's approved certificate/managed-profile process. A private CA is not a public certificate or evidence of institutional approval. Never bypass browser warnings.
- Public-only `.cer`/`.pem` files, fingerprint and instructions are in `~/Downloads/Juno-Worker-HTTPS`. No private key or worker invitation is included.

## Verification

139 backend tests pass with no skips, including accepted 10/8 boundaries and rejection of 192.168/16, 172.16/12, public IPv4, ULA/link-local IPv6 and spoofed forwarded headers. Existing owner/worker authorization and report/history tests remain passing.

Actual configuration checks passed: the dedicated private CA rejects an otherwise signed certificate for an address outside 10/8; exact-IP TLS verification succeeds for the configured leaf. The running Juno helper serves the worker page over verified HTTPS with an explicitly scoped test CA context. Owner memory API access on that listener returns 403. A client using default trust rejects the private CA, demonstrating that browser/device trust still needs provisioning rather than being silently bypassed.

A short-lived owner setup credential was provisioned for the existing local service and revoked immediately afterward. No worker session, invitation, task share, report or source refresh was created. Before/after guards preserved owner, work-record counts, worker identity, planning/schedule hashes, existing paired-device states and original pairing certificate/key; only the local app credential rotated normally. Reports remain indefinitely retained.

The work app is updated to preview.14 and connected. Native state inspection confirmed the release and connection; live API/listener checks, rather than browser-warning bypass, establish worker hosting. Real worker-browser trust installation and campus Wi-Fi reachability remain to be checked on the participating devices. See [the operator guide](../WORKER-UPDATES.md) and [installer verification](installer-preview-14.json).

The actual extracted/relocated preview.14 installer passed 101 bundled-runtime fixtures with external networking disabled, 239 Mach-O dependency checks, migrations/backups, persistence and existing TLS/pairing checks. Verified package/checksum and guides are in `~/Downloads/Juno-0.1.0-preview.14`. No machine certificate or private key is bundled.
