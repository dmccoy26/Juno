# Receipt Helper → Juno read contract

November 18, 2026 · Mission 16 dependency

## Verified current integration

The local Receipt Helper builds `plan.json` with an `expenses` array. Juno imports a deliberately limited projection after explicit preview and confirmation. Both a bare expense array and a helper plan are accepted. Required fields are stable `expense_id` (or `id`), `merchant`, `date` (ISO local date), `amount` (decimal with at most two places), and ISO-style three-letter `currency`. Receipt statuses are `already_attached`, `ambiguous`, `missing_receipt`, `review` and `not_checked`. A bare expense without a completed search remains `not_checked`.

Juno keeps observation and import times separately, uses revision checks when replacing a snapshot, and rejects duplicate IDs, nonfinite amounts, excessive precision, oversized exports and future observation times. Paths, email contents, attachment paths, credentials and unrecognized fields are discarded. Credits retain their sign. Importing does not submit a report, attach a receipt or pay anything in Concur.

Implementation: `backend/src/juno/purchasing.py`, `desktop/Routines.swift`. Current helper inspected at `$HOME/Ai/Concur Helper/receipt_helper.py`. No helper source was changed by this mission.

## Additional contract needed from the helper

Publish a versioned export envelope containing `schema_version`, stable helper instance ID, export ID, creation time, observation window and completeness. Keep stable IDs across repeated exports. Separate entities:

- Expenses: statement/report IDs, decimal amount and currency, charge date, merchant, receipt-search outcome, account coding status and scoped institution-approved external reference.
- Reports: stable ID, reporting period, submission time and exact source status. Distinguish submitted, pending external validation, approved and paid. Never infer one from another.
- Orders: stable ID, requested/approved/ordered/shipped/received/verified status with observation times. Estimated delivery is separate from actual receipt and equipment readiness.
- Runs: start/end, source-specific coverage, success/partial/failure, and actionable sign-in state. A failed search is not zero matches. Name the sources actually searched without embedding credentials or private email bodies.

An export must distinguish unknown, explicitly none and not searched. Keep financial account numbers and unrelated email content outside Juno. Use a local reviewed file export initially. A watched directory needs explicit opt-in, safe no-follow reads, a bounded file size and atomic publisher writes. A later API requires its own scoped authenticated contract.

## Juno follow-up after contract exists

Add reports, orders and helper-run tabs only when populated by actual fields. Provide reviewed exact links to TaskDock task/workspace IDs and Beacon equipment IDs, preserving IDs through renames. Suggestions never count as confirmed links. Purchasing details remain hidden in Meeting mode and excluded from worker views. Reviewed, audience-scoped summaries can then inform reports and prerequisites. Current import intentionally does not claim these capabilities.

Acceptance includes unknown versus missing/search failure, credits and currencies, duplicate export replay, stale replacement, wrong-owner isolation, malformed data, receipt-path exclusion, report status fidelity and unapproved links excluded from summaries.


## November 18 dependency recheck

Rechecked the current Concur Helper source: the expense/receipt plan exists, but the versioned report/order/run export in this contract is still absent. Juno 0.2.25 expense import and reviewed task/equipment links are available; richer producer-compatible integration remains blocked. This recheck changed only Juno documentation; the owning application was not modified.
