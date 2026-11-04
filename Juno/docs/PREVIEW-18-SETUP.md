# Preview 18 — clearer connections, refreshed Today and Juno identity

Version `0.1.0-preview.18`, build 18. Includes preview.17's prominent one-question-at-a-time daily check-in, plus:

- A custom purple, white and gold Juno icon in the Dock and the application header, beside the name/version.
- Permanently labeled, stacked TaskDock address and secure token inputs. The token hint explains Keychain reuse and why the field clears after saving.
- Today reloads Juno's saved snapshot when returning from another section, so a newly connected TaskDock no longer leaves the pre-connection empty state visible. Canceled/superseded loads are fenced. Errors do not claim the user never connected.

Quit Juno normally before installation. Open `Juno-0.1.0-preview.18-macOS-arm64.pkg`, continue through the installer, and authenticate to macOS as an administrator when asked. The target is `/Applications/Juno.app`; data remains outside the bundle. Open that exact application after installation and verify preview.18 in the header and the new icon. Installation requires administrator access; a verified package is not an installed update.

No database migration, new cloud connection, TaskDock task change, or credential rotation is introduced by this release. Existing application data roots remain separate; installation does not merge the development app's `.local` database with the packaged app's `~/Library/Application Support/Juno` data. Keychain may ask for normal existing-credential access after an ad hoc signed update.

Today reads Juno's already-saved TaskDock copy. To fetch newer TaskDock information, use Refresh from TaskDock in the TaskDock section. Source/provider refresh still happens in TaskDock.

Internal Apple Silicon preview with bundled runtimes; app is ad hoc signed and not Developer ID notarized. Follow normal institutional approval. Physical laptop acceptance remains separate.
