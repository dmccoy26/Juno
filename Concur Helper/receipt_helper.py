"""Search exported email and propose receipt attachments for existing expenses."""

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date
from decimal import Decimal
from email import policy
from email.parser import BytesParser
from pathlib import Path


FORMATS = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


def normalize(merchant):
    return " ".join(re.findall(r"\w+", merchant.casefold()))


def receipt_from_email(path):
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    body = message.get_body(preferencelist=("plain",))
    if body is None:
        return None
    content = body.get_content()
    fields = {}
    for label in ("Merchant", "Transaction date", "Total"):
        values = re.findall(rf"^{label}:[ \t]*([^\r\n]+)$", content, re.M | re.I)
        if len(values) != 1:
            return None
        fields[label] = values[0].strip()
    total = re.fullmatch(r"([A-Z]{3}) ([0-9]+(?:\.[0-9]{1,3})?)", fields["Total"])
    if total is None:
        return None
    try:
        transaction_date = date.fromisoformat(fields["Transaction date"])
    except ValueError:
        return None
    attachments = [part for part in message.iter_attachments()
                   if part.get_content_type() in FORMATS]
    if len(attachments) != 1:
        return None
    attachment = attachments[0]
    payload = attachment.get_payload(decode=True)
    if not payload:
        return None
    return {
        "key": (normalize(fields["Merchant"]), transaction_date,
                total[1], Decimal(total[2])),
        "source": str(path),
        "hash": hashlib.sha256(payload).hexdigest(),
        "suffix": FORMATS[attachment.get_content_type()],
        "payload": payload,
    }


def expense_key(expense):
    amount = Decimal(str(expense["amount"]))
    merchant = normalize(expense["merchant"])
    currency = expense["currency"]
    if not amount.is_finite() or amount < 0 or not merchant or not re.fullmatch("[A-Z]{3}", currency):
        raise ValueError(f"Invalid expense fields for {expense['id']}")
    return merchant, date.fromisoformat(expense["date"]), currency, amount


def build_plan(mailbox, expenses, output, source_prefix=None):
    entries = [(expense, expense_key(expense)) for expense in expenses]
    if len({expense["id"] for expense, _ in entries}) != len(entries):
        raise ValueError("Expense IDs must be unique")
    counts = Counter(key for _, key in entries)

    receipts = {}
    skipped = []
    for path in sorted(mailbox.rglob("*.eml")):
        source = source_prefix + path.stem if source_prefix else str(path)
        receipt = receipt_from_email(path)
        if receipt is None:
            skipped.append(source)
            continue
        receipt["source"] = source
        receipts.setdefault(receipt["key"], {})[receipt["hash"]] = receipt

    hash_counts = Counter(digest for candidates in receipts.values() for digest in candidates)
    output.mkdir(parents=True, exist_ok=True)
    plan = []
    for expense, key in entries:
        row = {
            "expense_id": expense["id"], "payment_type": expense.get("payment_type"),
            "merchant": expense["merchant"], "date": expense["date"],
            "currency": expense["currency"], "amount": str(expense["amount"]),
            "report_url": expense.get("report_url"),
        }
        candidates = receipts.get(key, {})
        if expense.get("has_receipt"):
            row["status"] = "already_attached"
        elif counts[key] > 1 or len(candidates) > 1:
            row["status"] = "ambiguous"
        elif not candidates:
            row["status"] = "missing_receipt"
        else:
            receipt = next(iter(candidates.values()))
            if hash_counts[receipt["hash"]] > 1:
                row["status"] = "ambiguous"
            else:
                path = output / (receipt["hash"] + receipt["suffix"])
                path.write_bytes(receipt["payload"])
                row.update(status="review", email=receipt["source"], attachment=str(path),
                           sha256=receipt["hash"])
        plan.append(row)
    return {"expenses": plan, "skipped_emails": skipped}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mailbox", type=Path, help="Directory of exported .eml files")
    parser.add_argument("expenses", type=Path, help="Expense list in JSON format")
    parser.add_argument("output", type=Path, help="Directory for the proposal and attachments")
    args = parser.parse_args()
    if not args.mailbox.is_dir():
        parser.error("mailbox must be an existing directory")
    print(write_plan(args.mailbox, args.expenses, args.output))


def write_plan(mailbox, expenses_file, output, source_prefix=None):
    expenses = json.loads(expenses_file.read_text(), parse_float=Decimal)
    result = build_plan(mailbox, expenses, output.resolve(), source_prefix)
    plan_path = output / "plan.json"
    plan_path.write_text(json.dumps(result, indent=2) + "\n")
    return plan_path


if __name__ == "__main__":
    main()
