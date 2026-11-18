"""Read a Concur expense report or attach one reviewed receipt."""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from receipt_helper import expense_key


REPORT = re.compile(r"https://us2\.concursolutions\.com/nui/expense/reports/[A-Z0-9]+")
ROW = '[role="row"][id]'
HEADERS = ("Receipt", "Vendor Details", "Payment Type")


def open_report(page, url, *, require_draft=True):
    if not REPORT.fullmatch(url):
        raise ValueError("Use the full Concur expense report URL")
    page.goto(url, wait_until="domcontentloaded")
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    vendor = page.get_by_role("button", name="Vendor Details", exact=True)
    try:
        vendor.wait_for(timeout=8000)
    except PlaywrightTimeoutError:
        print("CONCUR_SSO_REQUIRED", flush=True)
        input("Complete university SSO in the browser, then continue here. ")
        if page.url != url:
            page.goto(url, wait_until="domcontentloaded")
        vendor.wait_for(timeout=15000)
    if page.url != url:
        raise RuntimeError("Concur did not open the requested report")
    if require_draft:
        page.get_by_text("Not Submitted", exact=True).wait_for(timeout=10000)
    page.locator(ROW).first.wait_for(timeout=10000)


def snapshot(page):
    headers = page.get_by_role("columnheader").all_inner_texts()
    columns = {name: headers.index(name) for name in HEADERS}
    date_column = next((headers.index(name) for name in ("Transaction Date", "Date") if name in headers), None)
    if date_column is None:
        raise RuntimeError("Could not identify the Concur date column")
    amount_column = next((headers.index(name) for name in ("Requested", "Amount") if name in headers), None)
    if amount_column is None:
        raise RuntimeError("Could not identify the Concur amount column")
    expenses = []
    for row in page.locator(ROW).all():
        row_id = row.get_attribute("id")
        if not re.fullmatch(r"[A-Z0-9]{20,40}", row_id):
            continue
        cells = row.get_by_role("cell").all_inner_texts()
        amount = cells[amount_column].strip()
        if not re.fullmatch(r"\$-?[0-9,]+\.[0-9]{2}", amount):
            raise ValueError("Expected a USD amount on every expense row")
        date_text = cells[date_column].strip()
        receipt_cell = row.get_by_role("cell").nth(columns["Receipt"])
        receipt_button = receipt_cell.get_by_role("button", name=re.compile(r"^View receipt ", re.I))
        has_receipt = receipt_button.count() == 1
        expenses.append({
            "id": row_id,
            "report_url": page.url,
            "merchant": cells[columns["Vendor Details"]].splitlines()[0].strip(),
            "date": datetime.strptime(date_text, "%m/%d/%Y").date().isoformat(),
            "currency": "USD",
            "amount": amount[1:].replace(",", ""),
            "payment_type": cells[columns["Payment Type"]].strip(),
            "has_receipt": has_receipt,
            "can_attach": receipt_cell.get_by_role("button", name="Attach Receipt", exact=True).count() == 1,
        })
    return expenses


def usd_amount(value):
    value = value.strip()
    if re.fullmatch(r"\(\$[0-9,]+\.[0-9]{2}\)", value):
        value = "-" + value[1:-1]
    if not re.fullmatch(r"(?:-\$|\$-?)?[0-9,]+\.[0-9]{2}", value) and not re.fullmatch(
        r"-?[0-9,]+\.[0-9]{2}", value
    ):
        raise ValueError("Allocation amount is not an unambiguous USD value")
    return Decimal(value.replace("$", "").replace(",", ""))


def org_totals(headers, rows, expected_total):
    """Accept only an explicit Org breakdown that reconciles to the report."""
    columns = [label.strip().casefold() for label in headers]
    org_column = next(i for i, value in enumerate(columns) if value in ("org", "organization", "org code"))
    amount_column = next(i for i, value in enumerate(columns) if value in
                         ("allocated amount", "amount", "total amount", "allocated", "total"))
    totals = {}
    for row in rows:
        org_text, amount_text = row[org_column].strip(), row[amount_column]
        if org_text.casefold() in ("total", "grand total"):
            if usd_amount(amount_text) != expected_total:
                raise ValueError("Allocation summary total differs from the report")
            continue
        org = re.match(r"^\(?([0-9]{5})(?:\)|\s|$)", org_text)
        if not org:
            raise ValueError("An allocation is missing its Org code")
        code = org[1]
        totals[code] = totals.get(code, Decimal(0)) + usd_amount(amount_text)
    if not totals or sum(totals.values(), Decimal(0)) != expected_total:
        raise ValueError("Org amounts do not reconcile to the report total")
    return [{"org": code, "amount": format(amount, ".2f")} for code, amount in sorted(totals.items())]


def report_header(page):
    page.get_by_role("button", name=re.compile(r"Report Number:.*open report header details", re.I)).press("Enter")
    header = page.get_by_role("dialog", name="Report Header", exact=True)
    def field(name):
        return header.get_by_role("textbox", name=name, exact=True).input_value(timeout=8000).strip()
    try:
        return {
            "title": field("Report/Trip Name"),
            "source_status": field("Approval Status"),
            "currency_label": field("Report Currency"),
            "total": format(usd_amount(field("Report Total")), ".2f"),
            "period_start": datetime.strptime(field("Report/Trip Start Date"), "%m/%d/%Y").date().isoformat(),
            "period_end": datetime.strptime(field("Report/Trip End Date"), "%m/%d/%Y").date().isoformat(),
            "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    finally:
        close = header.get_by_role("button", name=re.compile(r"^(Cancel|Close)$"))
        close.press("Enter", timeout=8000)
        header.wait_for(state="hidden", timeout=8000)


def read_org_summary(page, expected_total):
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    try:
        page.get_by_role("button", name="Report Details", exact=True).press("Enter", timeout=4000)
        page.get_by_text("Allocation Summary", exact=True).press("Enter", timeout=4000)
        dialog = page.get_by_role("dialog", name="Allocation Summary", exact=True)
        dialog.wait_for(timeout=8000)
        headers = dialog.get_by_role("columnheader").all_inner_texts()
        rows = [r.get_by_role("cell").all_inner_texts() for r in dialog.get_by_role("row").all()]
        return "verified", org_totals(headers, [row for row in rows if row], expected_total)
    except (PlaywrightTimeoutError, IndexError, StopIteration, ValueError):
        return "unavailable", []


def read_report(page):
    rows = snapshot(page)
    if not rows:
        raise RuntimeError("No supported expense rows were visible")
    report = report_header(page)
    if not report["source_status"]:
        raise RuntimeError("Concur did not show an approval status")
    if report.pop("currency_label") != "US, Dollar":
        raise RuntimeError("The report currency is not USD")
    total = Decimal(report["total"])
    if sum((Decimal(row["amount"]) for row in rows), Decimal(0)) != total:
        raise RuntimeError("Visible expense rows do not reconcile to the report total")
    accounting, totals = read_org_summary(page, total)
    report.update(currency="USD", total=format(total, ".2f"),
                  allocation_state=accounting, org_totals=totals)
    for row in rows:
        row.update(expense_id=row["id"], status="already_attached" if row["has_receipt"] else "not_checked")
    return {"expenses": rows, "report_observation": report}


def attach(page, item):
    current = next((row for row in snapshot(page) if row["id"] == item["expense_id"]), None)
    if (current is None or expense_key(current) != expense_key(dict(item, id=item["expense_id"]))
            or not current["payment_type"] or current["payment_type"] != item["payment_type"]):
        raise RuntimeError("Expense or payment type changed since review")
    if current["has_receipt"] or not current["can_attach"]:
        raise RuntimeError("The row no longer offers Attach Receipt. Check it in Concur.")
    path = Path(item["attachment"])
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != item["sha256"]:
        raise RuntimeError("The attachment changed since review")
    row = page.locator(f'{ROW}[id="{current["id"]}"]')
    button = row.get_by_role("button", name="Attach Receipt", exact=True)
    button.press("Enter")
    with page.expect_file_chooser() as chooser:
        page.get_by_role("button", name="Upload New Receipt", exact=True).click()
    import mimetypes

    chooser.value.set_files({
        "name": path.name,
        "mimeType": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "buffer": payload,
    })
    receipt = row.get_by_role("button", name=f"View receipt {path.name}", exact=True)
    receipt.wait_for(timeout=20000)
    # Use a fresh page load to verify the filename on the same expense.
    open_report(page, current["report_url"])
    receipt.wait_for(timeout=15000)
    saved = next((entry for entry in snapshot(page) if entry["id"] == current["id"]), None)
    if (saved is None or not saved["has_receipt"]
            or expense_key(saved) != expense_key(current)
            or saved["payment_type"] != current["payment_type"]):
        raise RuntimeError("Could not verify the saved receipt and payment type")
    print(f"Receipt attached to {current['id']} ({saved['payment_type']}).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=Path("local/concur-browser"))
    commands = parser.add_subparsers(dest="command", required=True)
    read = commands.add_parser("snapshot")
    read.add_argument("report")
    read.add_argument("output", type=Path)
    report_read = commands.add_parser("report-read")
    report_read.add_argument("report")
    report_read.add_argument("output", type=Path)
    scan = commands.add_parser("pcard-scan")
    scan.add_argument("report")
    scan.add_argument("folder", type=Path)
    scan.add_argument("output", type=Path)
    scan.add_argument("--start")
    scan.add_argument("--end")
    apply = commands.add_parser("attach")
    apply.add_argument("plan", type=Path)
    apply.add_argument("expense_id")
    args = parser.parse_args()
    item = None
    if args.command == "attach":
        plan = json.loads(args.plan.read_text())
        item = next((row for row in plan["expenses"] if row["expense_id"] == args.expense_id), None)
        if not item or item["status"] != "review" or not item["report_url"]:
            parser.error("Provide an expense ID from a Concur review row")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(args.profile, headless=False)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            open_report(page, item["report_url"] if item else args.report,
                        require_draft=args.command != "report-read")
            if item:
                attach(page, item)
            elif args.command == "report-read":
                result = read_report(page)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, indent=2) + "\n")
            else:
                rows = snapshot(page)
                if args.command == "pcard-scan":
                    print("CONCUR_REPORT_READ", flush=True)
                if not rows:
                    raise RuntimeError("No supported expense rows were visible")
                args.output.parent.mkdir(parents=True, exist_ok=True)
                if args.command == "pcard-scan":
                    from pcard_receipts import build_plan

                    result = build_plan(args.folder, rows)
                    result["report_observation"] = {
                        "source_status": page.get_by_text("Not Submitted", exact=True).inner_text().strip(),
                        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    }
                    result["expenses"] = [
                        row for row in result["expenses"]
                        if (args.start is None or row["date"] >= args.start)
                        and (args.end is None or row["date"] <= args.end)
                    ]
                else:
                    result = rows
                args.output.write_text(json.dumps(result, indent=2) + "\n")
                print(f"Read {len(rows)} expenses into {args.output}.")
        finally:
            context.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        message = str(error).splitlines()
        print(f"CONCUR_ERROR: {message[0] if message else type(error).__name__}", file=sys.stderr)
        raise SystemExit(1)
