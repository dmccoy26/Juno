# Juno native review — November 1, 2026

Preview.12, build 12. Mission 10 delivers a tested usability increment. This report does not certify every possible interaction or literal perfection.

## Design evidence and resulting changes

Reviewed Apple's [macOS guidance](https://developer.apple.com/design/human-interface-guidelines/designing-for-macos), [Settings](https://developer.apple.com/design/human-interface-guidelines/settings), [layout](https://developer.apple.com/design/human-interface-guidelines/layout) and [feedback](https://developer.apple.com/design/human-interface-guidelines/feedback). Applied native navigation/menu conventions, clear content hierarchy, grouped preferences and explicit feedback before losing drafts. This is an interpretation of guidance, not Apple certification.

Also inspected TaskDock's separate native Beta 4 worktree, build 52 (`8a97d37`), particularly its stabilization review. Stable editor identity, explicit save/discard, native date controls and separation of test evidence from physical acceptance informed this increment. The older maintenance checkout's web-based entry point is not the native Beta 4 implementation.

Juno now has a native sidebar; grouped Settings in a separate window; local Help; working workspace shortcuts (Command-1 through 8), contextual Find and explicit Close/Minimize handling. Plan displays compact issue rows and one expanded inspector, request description/outcome, one clarification and detailed provenance on demand. Setup no longer occupies daily navigation. Appearance supports system/light/dark, with short preference pages aligned at the top.

Visited workspaces preserve view state and unfinished planning/schedule drafts. Prompt handoff asks before adding to an existing chat draft. Quitting with unsaved planning changes offers Return to Juno. Potentially blocking Keychain reads/writes run away from the main actor. File reads likewise run in background work. Authorization, TLS and sharing controls remain in force.

Native date pickers and local validation improve schedule/provider forms. Daily and weekly schedule views share the chosen date. Visible memory timestamps use Chicago time, AM/PM and year. Weekly load distinguishes raw scheduled hours from funded limits; this is not an employee performance assessment.

## Defects found through native use

- An initial short Settings form was vertically centered in a large empty window. Replaced it with a top-aligned native control group and visually rechecked light/dark.
- Correct memory could reuse editor state initialized without the selected record: the title said Correct while the text/base revision were empty. Replaced the Boolean sheet plus separate draft with an identified edit request and unique editor identity. The final native retest prefills the selected text, rejects a stale revision, retains the draft, compares revision 3 and explicitly saves the same record as revision 4. The memory count stays unchanged in that retest.
- Stale memory saves previously offered no convenient comparison path. Added Load latest saved version, Use latest values and Keep my draft for review; saving remains explicit.
- Window commands previously relied on nil-target responder behavior and appeared disabled during inspection. Explicit active-window handlers now close Settings, recover the main window through View navigation and restore a minimized window.
- Direct-provider form switches clear prior credentials before asynchronous loading. A failed read cannot leave another provider's secret in the form. TaskDock/Beacon credential-forget actions now have explicit confirmations.
- Context freshness timestamps are normalized to UTC for API/database comparison; user-facing work dates remain Chicago. This fixes the midnight boundary found by the integration suite.

## Native interaction evidence

All mutation tests used a separately identified Juno Lab app, isolated database, synthetic records and disabled hosting. Real work records were not test fixtures. AX inspection and actual screenshots were both used. Screen captures included a 2160×1536-pixel main window and 1720×1364-pixel Settings window; these are observed captures, not a physical M5 laptop acceptance claim.

| Workflow | Actual observed result | Boundary |
| --- | --- | --- |
| Daily navigation | Today, Chat, Plan, Schedules, check-in, Memories, TaskDock and Evidence reachable; Command-1–8; contextual Find focuses TaskDock/Memory search | Not every OS-provided submenu entry exercised |
| Plan | One expanded inspector, source/unknown/none details, estimate validation, guided questions, Cancel, Apply draft, navigation retention and Save | Suggestions remain reviewed; no automatic assignments |
| Draft handoff | Existing Chat draft retained on Keep; explicit append works | Not a durable saved conversation until sent |
| Unsaved quit | Planning warning appears; Return to Juno retains draft; explicit Save succeeds | Destructive Quit without saving not clicked |
| Memory | Add/review/correct/search; selected record prefill; actual concurrent save → 409; latest comparison; keep draft; save same record revision 4 | Use latest values branch reviewed in source, not separately clicked in final run |
| Check-in | All five questions, Back/Skip, draft continuity, review, confirm and restart retention | No judgment of human comprehensibility from automation alone |
| Chat/model | Local model discovery and synthetic reply; context change removes stale reply; edit clipboard/Undo/Redo | No external model or cloud fallback |
| Schedules | Four views, room/person selectors, previous/next week/day, shared selected date, staff-hours validation, exceptions, Save/Discard | Final example: class to 10:45 plus imported meeting to 11 gives 11 AM–5 PM; following Monday gives 10:45 AM–5 PM |
| Evidence/file panels | Actual ICS Open imports one synthetic meeting; native Save exports CSV template; dated busy-time details | File-picker AX quirks required screenshot/coordinate navigation |
| Settings | Group navigation, missing-auth gating, all seven direct-provider forms, local model, meeting mode, Light/Dark/System | No new real account grants or live provider mutation |
| Confirmations | Memory/conversation deletion, remove imported copy, provider disconnect and TaskDock forget token: Cancel retains state | Final permanent actions not clicked through UI; isolated API/native tests cover deletion |
| Native windows/help | About release/build; actual Help window; Close Settings; main-window recovery; minimize/restore | Help-menu search shortcut opens OS search; actual Juno Help selected separately |

The [control inventory](native-controls-2026-11-01.json) records 306 declarations, **not 306 passing interaction tests**. It includes dynamically reused controls; state combinations are not exhaustively enumerated. No destructive action was performed on production records, no staff message sent and no upstream TaskDock source refreshed by these tests.

## Automated evidence

- 121 backend tests, zero skips; final run passed.
- Exact native planning decoding and editor numeric/date bounds; Today completion/deadline handling; room alias/isolation checks passed.
- Native scheduling projections, exceptions, candidate status, supervised holds, semester/DST boundaries, form validation and shared week navigation passed.
- Native offline create/edit/delete, diary chains, restart, ID remapping, conflicts, badges and private cache permissions passed, including actual JunoStore operations without a reachable host.
- Semaphore-delayed credential operation leaves the main actor responsive and returns its result.
- Keychain persistence across native processes, provider isolation, OAuth state/private callback/S256 and atomic token replacement passed using disposable credentials.
- Pinned TLS pairing, wrong-certificate rejection, advertised IP/hostname verification, actual host outage, offline writes, restart and idempotent synchronization passed against isolated services.
- Package acceptance and host preservation are recorded separately below and in the installer report.

[HumanLab preflight](humanlab-juno-native-preflight-2026-11-01.json) is blocked because its current terminal instrument lacks native-app, visual and focus capabilities. No HumanLab native experiment is claimed. Native inspection supplied separate evidence.

## Remaining acceptance and limits

Physical M5 laptop upgrade, real wired/Wi-Fi outage/reconnect, actual VoiceOver speech, larger-text and full keyboard-only walkthroughs remain open. Real provider OAuth accounts and every authentication failure cannot be inferred from synthetic contract checks. No representative high-volume latency benchmark was completed; planning still evaluates a bounded candidate set (up to 500) and explicitly reports a task outside that set. This increment is not a whole-week optimizer. Further responsive resizing and common-scale timeline work may follow user observation.

The installer is an internal Apple Silicon preview, ad-hoc signed without Developer ID notarization. Follow institutional installation policy. Schema remains 0008; identities, data roots and pairing protocol are unchanged. Packaged and development installations keep their established separate data locations.

## Delivery and preservation

The [actual preview.12 installer report](installer-preview-12.json) passed extraction/relocation, 239 Mach-O dependency checks, bundled isolated fixtures, schema-1 upgrade with readable backup, restart/offline persistence and resource-seal checks. SHA-256: `a7c9f4127d6a7abc8237e3f358a8dddd9785ad5b2f0e3fa24ddb552c95645e13`. A byte-verified copy, checksum, report and instructions are in `~/Downloads/Juno-0.1.0-preview.12`.

Updated the existing development work-host app separately, retaining its old bundle privately. Read-only before/after invariants passed: owner, work-record counts, prior paired-device revocation states and certificate/private-key digests unchanged. Only the app's temporary local credential rotated normally. The native work app reopened Connected · This Mac with its saved TaskDock overview and preview.12 footer. No production source refresh or test-record writes were needed. Lab app was quit and only its isolated database stopped; the work host remains running.
