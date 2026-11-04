# Preview 19 — approved Juno logo and matching icon

`0.1.0-preview.19`, build 19. The approved two-tone apricot/violet symbol replaces the earlier J-and-star artwork. The full Juno logo appears on a light badge beside the version in the header; the matching plum-tile icon is included in the native app iconset. Both light and dark appearances retain a readable wordmark and accessible Juno label. No user data is sent to image services at runtime; the bundled artwork is local.

Includes preview.18's clear TaskDock token form and Today reload-on-return, and preview.17's question-first daily check-in. No new database migration or TaskDock write is introduced.

Quit Juno normally, run `Juno-0.1.0-preview.19-macOS-arm64.pkg`, and complete macOS administrator authentication if requested. It updates `/Applications/Juno.app`; user data remains outside the application bundle. Open that exact copy and verify preview.19 and the new logo. Installation does not merge development and packaged data roots or rotate pairing certificates. Existing Keychain access may need ordinary confirmation after an ad hoc signed update.

This is an internal Apple Silicon preview with bundled Python/PostgreSQL, ad hoc app signing, and no Developer ID notarization. Physical laptop acceptance remains separate. The public artwork and generation prompts are in `desktop/branding/`; private installation preservation evidence stays in ignored `.local`.
