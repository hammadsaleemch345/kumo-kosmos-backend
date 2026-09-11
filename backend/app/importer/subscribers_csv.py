import csv
from dataclasses import dataclass
from io import StringIO


@dataclass
class SubscriberRow:
    email: str
    is_veteran: bool  # has any paid history on Substack; gets email-only import into the veteran segment


def parse_subscribers_csv(csv_text: str) -> list[SubscriberRow]:
    """Parse the subscriber export and classify each row as free or veteran (had paid history).

    Veteran status is driven by `first_payment_at` being populated, the clearest signal that real
    money changed hands at some point, backed up by `plan` being a real plan rather than "other".
    Only the email is kept for veteran rows, no plan or payment data, per the client's explicit
    instruction (partly for legal reasons around handling payment data).
    """
    reader = csv.DictReader(StringIO(csv_text))
    rows = []
    for row in reader:
        email = row["email"].strip().lower()
        if not email:
            continue
        has_paid_history = bool(row["first_payment_at"].strip()) or row["plan"].strip().lower() not in (
            "",
            "other",
        )
        rows.append(SubscriberRow(email=email, is_veteran=has_paid_history))
    return rows
