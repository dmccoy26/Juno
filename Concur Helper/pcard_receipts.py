"""Find receipt candidates in a monthly PCARD folder."""

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from receipt_helper import expense_key, normalize


FILENAME_AMOUNT = re.compile(r"(?<![\w.,])(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}(?![\d.,])")
TOTAL = re.compile(r"(?im)^\s*(?:grand total|order total|total)\s*\$([\d,]+\.\d{2})\s*$")
FORMATS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def matches(path, merchant, day, amount):
    if any(Decimal(value.replace(",", "")) == amount
           for value in FILENAME_AMOUNT.findall(path.stem)):
        return "filename_amount"
    if path.suffix.lower() != ".pdf":
        return None
    try:
        text = "\n".join(page.extract_text() for page in PdfReader(path).pages)
    except (OSError, PyPdfError):
        return None
    vendor = re.sub(r" (?:\d+ )+\d+$", "", merchant)
    dates = (f"{day:%B} {day.day}, {day.year}", day.isoformat(),
             f"{day.month}/{day.day}/{day.year}", day.strftime("%m/%d/%Y"))
    if (vendor and f" {vendor} " in " " + normalize(path.stem + " " + text) + " "
            and any(value.casefold() in text.casefold() for value in dates)
            and {Decimal(value.replace(",", "")) for value in TOTAL.findall(text)} == {amount}):
        return "pdf_vendor_date_total"
    return None


def build_plan(folder, expenses):
    files = sorted(path for path in folder.iterdir()
                   if path.is_file() and path.suffix.lower() in FORMATS)
    rows = []
    for expense in expenses:
        row = dict(expense, expense_id=expense["id"], amount=str(expense["amount"]))
        rows.append(row)
        if expense.get("has_receipt"):
            row["status"] = "already_attached"
            continue
        if not expense.get("can_attach", True) or Decimal(row["amount"]) < 0:
            row["status"] = "manual_attachment"
            continue
        merchant, day, currency, amount = expense_key(expense)
        candidates = []
        if currency == "USD":
            for path in files:
                evidence = matches(path, merchant, day, amount)
                if evidence:
                    candidates.append({"path": str(path.resolve()), "evidence": evidence})
        row["candidates"] = candidates
        row["status"] = "ambiguous" if candidates else "missing_receipt"

    for row in rows:
        candidates = row.get("candidates", [])
        if len(candidates) != 1:
            continue
        candidate = candidates[0]
        if sum(candidate["path"] == other["path"] for entry in rows
               for other in entry.get("candidates", [])) != 1:
            continue
        path = Path(candidate["path"])
        row.update(status="review", attachment=str(path),
                   sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return {"expenses": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Monthly PCARD folder")
    parser.add_argument("expenses", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if not args.folder.is_dir():
        parser.error("The monthly PCARD folder must exist")
    expenses = json.loads(args.expenses.read_text(), parse_float=Decimal)
    plan = build_plan(args.folder, expenses)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
