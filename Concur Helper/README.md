# Receipt Helper

Receipt Helper searches a local directory of exported email and prepares a review
plan for attaching receipts to existing expenses. The current CLI uses Python
3.10 or later and has no third-party dependencies.

## Run the local workflow

```sh
python3 receipt_helper.py local/mail local/expenses.json local/review
```

The expense JSON is an array. Each entry uses this format.

```json
[
  {
    "id": "expense-123",
    "merchant": "Example Café",
    "date": "2026-11-15",
    "currency": "USD",
    "amount": "18.42",
    "payment_type": "Corporate Card",
    "has_receipt": false
  }
]
```

The initial email parser accepts plain-text receipts with exactly one PDF, JPEG
or PNG attachment and these labeled lines in the email body.

```text
Merchant: Example Café
Transaction date: 2026-11-15
Total: USD 18.42
```

The plan matches on normalized merchant, transaction date, currency and exact
amount. Duplicate copies of the same attachment are grouped by SHA-256.
Conflicting matches and already-attached entries get their own statuses.
Review rows include the source email path and local attachment path.
Payment type is copied from the expense snapshot for review.

## Gmail and SAP Concur

Install the runtime dependencies into a virtual environment.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

Enable the Gmail API and create a Desktop OAuth client using the
[Google Gmail Python quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python).
Save the desktop client JSON as `local/gmail-client.json`. The first Gmail run
opens Google's consent screen for read-only access and stores the token locally.

1. Open an existing draft expense report in Concur and copy its report URL
   from the address bar. Run the snapshot command with that URL. A dedicated
   local browser profile opens. Complete university SSO there if prompted.
2. Run the Gmail search with an appropriate date range. Review each proposed
   match and open its local attachment to verify the receipt and payment details.
3. Apply a reviewed receipt by specifying its expense ID from the plan. Use one
   expense ID per run.

```sh
.venv/bin/python concur_portal.py snapshot 'YOUR_CONCUR_REPORT_URL' local/expenses.json
.venv/bin/python gmail_receipts.py 'newer_than:90d has:attachment {receipt invoice}' local/expenses.json local/review
.venv/bin/python concur_portal.py attach local/review/plan.json 'REVIEWED_EXPENSE_ID'
```

The Concur reader targets the US2 report layout and expects USD rows and
US-format dates. The attachment command checks the report, expense ID,
merchant, date, amount, existing payment type and attachment hash before upload.
It preserves the payment type assigned to imported transactions. The command
uploads one receipt to a draft expense row. Report submission is manual.

The Gmail search can return messages that the current parser skips, including
HTML-only messages and receipts whose transaction details appear solely in an
attachment.

## Search a monthly PCARD folder

```sh
.venv/bin/python pcard_receipts.py "$HOME/Desktop/PCARD/november 2026" local/expenses.json local/pcard-review.json
```

Use the folder for the report month. Filenames such as `AHMX-700.76.pdf`
supply an amount hint. Confirm the merchant, date and total before applying
an amount-only candidate. For PDFs with selectable text, the command can
also match the merchant, date and labeled total when the filename omits
the amount. Multiple candidates or a file shared by multiple rows require
manual resolution. Use the Concur attach command above with the PCARD
review plan after verifying the receipt. The department prefix in the file
name is kept as part of the file name.

## Run the SwiftUI Mac app

From the project directory, set up the Python virtual environment and Chromium
using the install commands above, then run:

```sh
./build-mac-app.sh
open "local/Concur Helper.app"
```

The local app requires macOS 14 or later and uses the virtual environment at
the project’s current path. Rebuild if you move the project. It stores its own
Concur browser profile in `~/Library/Application Support/Concur Helper`.

1. Paste the URL of an existing, unsubmitted US2 Concur expense report and
   choose the monthly receipt folder under Desktop → PCARD.
2. Click **Find Matches**. If the Concur browser prompts for university SSO,
   sign in there, then click **Continue after SSO** in the app.
3. Select a row and open the proposed receipt. Use **Review Upload…** and
   **Attach and Verify** only after verifying the selected document.
4. The row changes to **Attachment verified in Concur** when the app reloads
   the report and finds the exact filename on the same expense.

This version uses local PCARD files. The app leaves existing receipts in place
and sends conflicts, missing receipts, and rows without a grid upload control
to review. An interrupted or unverified upload requires a new scan so a
successful server-side upload is recognized on retry. Submit reports manually
in Concur. The GUI does not change expense fields, payment types, or allocations.

## Request a reconciliation from Juno

In a Juno build that includes the Concur integration, use **Purchasing → Request
Concur Job**, or type `/concur week` or `/concur month` in Juno Chat on the work Mac.
Open the current Concur Helper app once so macOS can find it.

Concur Helper opens the requested Chicago calendar week (Monday–Sunday) or
month. For a period within one month, it preselects the corresponding PCARD
folder when it finds a unique match. Paste the Concur draft URL and scan.
A week that spans months requires selecting the relevant folder. Use the
corresponding draft and month folder for each part of that week.

Review the candidates and the total by recorded payment type, which includes
credits. Each upload requires confirmation in Concur Helper. Sign in and
submit manually in Concur. When done, **Export for Juno…** saves the review
status and amounts for Juno’s **Purchasing → Import helper export…** preview.
The export excludes receipt files, local paths, report URLs and credentials.
A job persists if the helper closes. Choose **End Job** after exporting.

## Juno export contract, version 1

**Export for Juno…** writes an atomic, reviewed JSON file. The envelope adds a
persistent helper instance ID, a unique export ID, timestamps, any requested
date range, and source coverage. The expense array in a completed scan retains
the existing Juno Purchasing fields. It also includes the helper's stable report
identifier and explicit receipt-search and accounting observation states.
Amount strings preserve currency and the sign of credits.

- A completed search with no candidates records `missing_receipt` for an
  expense. Rows that require manual attachment project to `not_checked`.
  An unverified upload projects to `not_checked` with an unknown receipt outcome.
- A failed or partial scan has `expenses: null`, so older versions of Juno
  reject diagnostics instead of replacing a saved snapshot with an empty scan.
- Reports carry the exact source status observed by this draft-only workflow.
  Report period and submission time are not derived from the request window.
  Orders, statement IDs, account coding and external links are not searched
  by this version. An empty orders array with `not_searched` is not an
  observation that there were no orders.
- Run coverage identifies Concur, PCARD, and sources not searched. A manual
  university sign-in prompt is recorded without account details. Runs cover
  the current scan and its upload attempts.
- Local paths, report URLs, PDFs, email contents, account numbers and
  credentials are excluded. Juno continues to preview and confirm expense
  imports. The existing importer discards the added fields.

No watched directory, report submission, or external write interface is
enabled by the export.

### Report status and Org totals

Use **Read Report Status** with a Concur report URL, including a submitted
report. The PCARD folder is optional for this operation. The helper reads the
report header and uses **Report Details → Allocation Summary** for Org totals.
It exports totals only when the summary supplies explicit Org codes and amounts
that reconcile to the full report. The read records Concur's exact approval
status and report dates, and preserves signed credits.

In a Juno build with report imports enabled, preview and import the export in
**Purchasing**. Juno retains the latest reviewed observation per report. Open
**Concur meeting update…**, select the reports, and copy the resulting text
into the appropriate chair or dean draft. Exact Concur status, observation
time and amounts are included. Unavailable allocations are labeled as such.

Report-status reads export a `read_report_status` run with `expenses: null`. They preserve Juno’s previous expense rows and their scan date; the report’s own status, period and verified Org totals can still update. A report-status read is not a receipt search.
