# Mission 7 — reliable memory saves and guided task clarification

## Outcome

Explicit “remember this/that” requests open a reviewable memory form. Only a successful canonical memory save (or an explicitly labeled offline queue save) produces an app confirmation. A model cannot execute a memory write. Task details can be clarified one question at a time without inventing missing estimates or employee capability.

## Implementation

- Native write-intent recognition routes supported explicit phrases to the existing memory editor, including while offline or without a configured model. Recall questions such as “Do you remember…” and “Remember when…” remain chat.
- Cancel retains the original composer text and creates no memory. Save errors stay visible. Successful saves have a review link; offline saves are labeled queued for sync. User messages can also be manually saved as memory.
- The chat API responds deterministically to supported explicit remember requests without calling the model or writing a memory. Its response explains the review/save action. Other model replies are instructed not to claim memory writes; no general semantic intent classifier or autonomous memory extraction is introduced.
- Clarify with Juno opens five focused draft questions: duration, room, person, support/capability, blockers. A review step precedes Apply to draft, followed by the existing Save planning action. Unknowns can remain blank. No assignment, notification or reservation is created.

## Verification

Completed: optimized native build installed at `~/Applications/Juno.app` from `.local/memory-guidance-reviewed/Juno.app`; 105 PostgreSQL tests passed with zero skips. Native interaction checks verified prefilled memory review, Cancel retaining the original message, all five guided steps, review-before-Apply, and Cancel leaving Save planning disabled. No real memory/task records were saved during the UI checks. Host owner, work-record counts, pinned certificate/key and prior paired-device states match the private pre-update baseline. Backend tests cover explicit intent, recall boundaries, no-model handling, retry identity and a separately reviewed canonical save. Native tests cover phrase/multiline boundaries and offline intent opening without a queued write. Existing memory ownership/conflict/correction/deletion and offline regressions remain required.

## Limits

Supported phrases are intentionally narrow and reviewable; indirect requests stay ordinary chat. Past model statements claiming a saved memory are historical text, not evidence of a canonical memory record. Structured memory review and explicit user correction/deletion remain authoritative. Laptop installer refresh and physical-device acceptance are separate follow-up work.

## Result

Implementation, automated checks, native review/Cancel verification, desktop update and GitHub push are complete. Canonical save success and no-model/duplicate/retry behavior were verified with synthetic integration tests; the native production UI test intentionally canceled instead of creating a real test memory. Offline intent review and existing offline memory/diary queue regressions pass. The portable installer and physical laptop trial are unchanged and remain follow-up work.
