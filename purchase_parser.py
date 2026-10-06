"""
Extract a purchase history from Gmail messages.

Stage 1 scores each email and skips obvious non-purchases.
Stage 2 sends possible purchases to the model.
Stage 3 merges emails about the same order.
Stage 4 saves the purchase history.
"""

from openai import OpenAI
from dotenv import load_dotenv
from gmail import get_email_text, get_pdf_text

import argparse
import html
import json
import os
import re
from datetime import datetime, timezone

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# subject matches count more, but they don't decide by themselves
STRONG_SUBJECT_PHRASES = [
    "order confirmation",
    "order confirmed",
    "purchase confirmation",
    "has been placed",
    "has been approved",
    "thank you for your order",
    "thank you for shopping",
    "receipt",
    "shipment invoice",
    "invoice",
    "credit card charged",
    "has been charged",
    "your order",
    "order has arrived",
    "has arrived",
]

POSITIVE_PHRASES = STRONG_SUBJECT_PHRASES + [
    "order number",
    "order #",
    "amount paid",
    "order total",
]

POSITIVE_WORDS = [
    "total",
    "subtotal",
    "payment",
]

NEGATIVE_PHRASES = [
    "discount",
    "coupon",
    "promotion",
    "promotional",
    "shop now",
    "limited time",
    "don't miss",
    "clearance",
    "rewards",
    "newsletter",
    "subscribe",
    "unsubscribe",
]

NEGATIVE_WORDS = [
    "sale",
    "promo",
]

HARD_NEGATIVE_SUBJECT = [
    "% off",
    "coupon",
    "newsletter",
    "rewards",
    "subscribe",
    "shop now",
    "limited time",
    "clearance",
    "don't miss",
]

PERCENT_OFF = re.compile(r"\d+\s*%\s*off")

# matches "order #123456", "order (123456)", "order number: ABC123"
ORDER_NUMBER_RE = re.compile(
    r"\border\s*(?:number|no\.?|#)?\s*[:#]?\s*\(?([A-Z0-9-]{6,})\)?",
    re.IGNORECASE,
)

PURCHASE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "is_purchase": {"type": "boolean"},
        "store": {"type": ["string", "null"]},
        "order_number": {"type": ["string", "null"]},
        "date": {"type": ["string", "null"]},
        "total": {"type": ["number", "null"]},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "product": {"type": ["string", "null"]},
                    "quantity": {"type": ["integer", "null"]},
                    "price": {"type": ["number", "null"]},
                },
                "required": ["product", "quantity", "price"],
            },
        },
    },
    "required": [
        "is_purchase",
        "store",
        "order_number",
        "date",
        "total",
        "items",
    ],
}


def prepare_email(email):
    """Get the subject, sender, and body. Use the snippet when the body is missing."""
    email_text = get_email_text(email)

    text = html.unescape(email_text["body"] or "")
    text = text.replace("\u034f", "")
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    body = text.strip()
    used_snippet = False

    if not body:
        text = html.unescape(email.get("snippet") or "")
        text = text.replace("\u034f", "")
        text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        body = text.strip()
        used_snippet = True

    pdf_text = get_pdf_text(email)
    if pdf_text:
        body = f"{body}\n\nAttached receipt:\n{pdf_text[:8000]}".strip()
        used_snippet = False

    raw_date = email.get("internalDate")
    if not raw_date:
        received_date = None
    else:
        received = datetime.fromtimestamp(int(raw_date) / 1000, tz=timezone.utc)
        received_date = received.strftime("%Y-%m-%d")

    return {
        "subject": email_text["subject"] or "",
        "from": email_text["from"] or "",
        "body": body,
        "used_snippet": used_snippet,
        "received_date": received_date,
    }


def find_order_number(subject, body):
    """Return the first order number and whether it was found in the subject.

    The match has to include a digit so words like "receipt" are ignored.
    """
    for source, in_subject in ((subject, True), (body, False)):
        for match in ORDER_NUMBER_RE.finditer(source or ""):
            value = match.group(1)
            if any(character.isdigit() for character in value):
                return value, in_subject

    return None, False


def screen_email(prepared):
    """Decide whether this email is worth sending to the model."""
    subject_l = prepared["subject"].lower()
    body_l = prepared["body"].lower()

    if "cancel" in subject_l or "refund" in subject_l:
        return {
            "candidate": False,
            "score": 0,
            "reason": "cancellation or refund",
            "signals": [],
        }

    if any(phrase in subject_l for phrase in (
        "tell us how we did",
        "how was your",
        "rate your",
    )):
        return {
            "candidate": False,
            "score": 0,
            "reason": "review request, not a receipt",
            "signals": [],
        }

    score = 0
    signals = []

    for phrase in POSITIVE_PHRASES:
        if phrase in subject_l:
            score += 3
            signals.append(f"+ {phrase} (subject)")
        elif phrase in body_l:
            score += 1
            signals.append(f"+ {phrase}")

    for word in POSITIVE_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", subject_l) is not None:
            score += 2
            signals.append(f"+ {word} (subject)")
        elif re.search(rf"\b{re.escape(word)}\b", body_l) is not None:
            score += 1
            signals.append(f"+ {word}")

    for phrase in NEGATIVE_PHRASES:
        if phrase in subject_l:
            score -= 3
            signals.append(f"- {phrase} (subject)")
        elif phrase in body_l:
            score -= 1
            signals.append(f"- {phrase}")

    for word in NEGATIVE_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", subject_l) is not None:
            score -= 3
            signals.append(f"- {word} (subject)")
        elif re.search(rf"\b{re.escape(word)}\b", body_l) is not None:
            score -= 1
            signals.append(f"- {word}")

    if PERCENT_OFF.search(subject_l):
        score -= 3
        signals.append("- percent off (subject)")
    elif PERCENT_OFF.search(body_l):
        score -= 1
        signals.append("- percent off")

    order_number, order_in_subject = find_order_number(
        prepared["subject"],
        prepared["body"],
    )
    if order_number and order_in_subject:
        score += 3
        signals.append(f"+ order number {order_number} (subject)")
    elif order_number:
        score += 1
        signals.append(f"+ order number {order_number}")

    strong_subject = any(phrase in subject_l for phrase in STRONG_SUBJECT_PHRASES)
    hard_negative = (
        any(phrase in subject_l for phrase in HARD_NEGATIVE_SUBJECT)
        or PERCENT_OFF.search(subject_l) is not None
        or re.search(r"\bsale\b", subject_l) is not None
        or re.search(r"\bpromo\b", subject_l) is not None
    )

    if strong_subject:
        candidate = True
        reason = "subject looks like an order or receipt"
    elif hard_negative:
        candidate = False
        reason = "subject looks promotional"
    elif score >= 3:
        candidate = True
        reason = "purchase signals in the email text"
    else:
        candidate = False
        reason = "not enough evidence of a purchase"

    return {
        "candidate": candidate,
        "score": score,
        "reason": reason,
        "signals": signals,
    }


def extract_purchase(email):
    """Run stage 1, then stage 2 only if the email might be a purchase."""
    prepared = prepare_email(email)
    screen = screen_email(prepared)

    if not screen["candidate"]:
        return {
            "is_purchase": False,
            "reason": screen["reason"],
        }

    extracted = extract_with_model(prepared)
    return clean_purchase(extracted, prepared)


def extract_with_model(prepared):
    """Ask the model for strict JSON."""
    snippet_note = ""
    if prepared["used_snippet"]:
        snippet_note = """
    The text below is only a short preview, not the full email.
    Extract only facts that are written in this text.
    """

    prompt = f"""
    Decide whether this email documents an actual purchase made by the user.

    Count it as a purchase when it is an order confirmation, receipt, invoice,
    payment/charge notice, or a shipping or delivery update for an order the
    user placed.

    Do not count marketing, advertisements, sales, coupons, newsletters,
    review requests, cancellations, or refunds.

    Do not invent products, prices, dates, or order numbers.
    Use null when a value is not written in the email.
    Use an empty items list when no products are listed.
    Use YYYY-MM-DD for the date when you can tell the order date.
    The received date is when Gmail got the email. It is not automatically
    the order date. If the email does not state an order date, use null.
    {snippet_note}
    EMAIL RECEIVED:
    {prepared["received_date"]}

    EMAIL SUBJECT:
    {prepared["subject"]}

    EMAIL FROM:
    {prepared["from"]}

    EMAIL BODY:
    {prepared["body"][:12000]}
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "purchase_extraction",
                "strict": True,
                "schema": PURCHASE_SCHEMA,
            }
        },
    )

    try:
        return json.loads(response.output_text)
    except json.JSONDecodeError:
        return {
            "is_purchase": False,
            "error": "Model returned invalid JSON",
        }


def clean_purchase(extracted, prepared):
    if extracted.get("error"):
        return extracted

    if not extracted.get("is_purchase"):
        return {"is_purchase": False}

    order_number = extracted.get("order_number")
    if order_number is None or (isinstance(order_number, str) and not order_number.strip()):
        order_number, _ = find_order_number(prepared["subject"], prepared["body"])

    store = extracted.get("store")
    if store is None or (isinstance(store, str) and not store.strip()):
        store = None
        sender = prepared["from"]
        if sender:
            display = re.match(r'\s*"?([^"<]+?)"?\s*<', sender)
            if display:
                name = display.group(1).strip()
                if name and "@" not in name:
                    store = name
            if store is None:
                domain = re.search(r"@([A-Za-z0-9.-]+)", sender)
                if domain:
                    name = domain.group(1).split(".")[0].lower()
                    if name not in {"gmail", "yahoo", "outlook", "hotmail", "icloud", "googlemail"}:
                        store = name.title()

    items = []
    for item in extracted.get("items") or []:
        product = item.get("product")
        if product is None or (isinstance(product, str) and not product.strip()):
            product = None
        price = item.get("price")
        quantity = item.get("quantity")
        if product is None and price is None:
            continue
        items.append({
            "product": product,
            "quantity": quantity,
            "price": price,
        })

    date = extracted.get("date")
    if date is None or (isinstance(date, str) and not date.strip()):
        date = None

    return {
        "is_purchase": True,
        "store": store,
        "order_number": order_number,
        "date": date,
        "total": extracted.get("total"),
        "items": items,
    }


def purchase_key(purchase):
    """Use the order number when there is one. Otherwise use store, date, total, and products."""
    store = purchase.get("store")
    if not store:
        store = ""
    else:
        store = store.lower()
        store = re.sub(r"\.com\b", "", store)
        store = re.sub(r"[^a-z0-9]", "", store)

    order_number = purchase.get("order_number")
    if not order_number:
        order_number = ""
    else:
        order_number = str(order_number).strip().lstrip("#").upper()

    if order_number:
        return ("order", store, order_number)

    names = []
    for item in purchase.get("items") or []:
        name = (item.get("product") or "").strip().lower()
        if name:
            names.append(name)

    return (
        "fallback",
        store,
        purchase.get("date"),
        purchase.get("total"),
        tuple(sorted(names)),
    )


def dedupe_purchases(purchases):
    """Keep one record per order and fill gaps from the other emails."""
    def completeness(purchase):
        score = 0
        if purchase.get("store"):
            score += 1
        if purchase.get("order_number"):
            score += 2
        if purchase.get("date"):
            score += 2
        if purchase.get("total") is not None:
            score += 3

        for item in purchase.get("items") or []:
            if item.get("product"):
                score += 2
            if item.get("price") is not None:
                score += 1
            if item.get("quantity") is not None:
                score += 1

        return score

    def richer_items(current, incoming):
        def item_score(items):
            score = 0
            for item in items:
                if item.get("product"):
                    score += 2
                if item.get("price") is not None:
                    score += 1
            return score

        if item_score(incoming) > item_score(current):
            return incoming
        return current

    groups = {}
    order = []

    for purchase in purchases:
        key = purchase_key(purchase)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(purchase)

    deduped = []
    for key in order:
        group = sorted(groups[key], key=completeness, reverse=True)
        merged = {
            "store": None,
            "order_number": None,
            "date": None,
            "total": None,
            "items": [],
        }

        for purchase in group:
            for field in ("store", "order_number", "date", "total"):
                value = purchase.get(field)
                if merged[field] in (None, "") and value not in (None, ""):
                    merged[field] = value
            merged["items"] = richer_items(merged["items"], purchase.get("items") or [])

        deduped.append(merged)

    return deduped


def print_screen(index, prepared, screen):
    label = "candidate" if screen["candidate"] else "skip"
    signals = ", ".join(screen["signals"]) if screen["signals"] else "none"
    print(f"[{index}] {label:9} score={screen['score']:3}  {prepared['subject']}")
    print(f"         {screen['reason']}")
    print(f"         signals: {signals}")


def main():
    parser = argparse.ArgumentParser(
        description="Score or extract purchases from emails.json"
    )
    parser.add_argument(
        "index",
        nargs="?",
        type=int,
        help="Extract one email at this index in emails.json",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Extract every likely purchase, dedupe, and save purchases.json",
    )
    parser.add_argument(
        "--file",
        default="emails.json",
        help="Saved Gmail messages to read. Defaults to emails.json",
    )
    args = parser.parse_args()

    if args.index is not None and args.all:
        parser.error("Pass either an index or --all, not both.")

    with open(args.file, "r") as f:
        emails = json.load(f)

    if args.index is not None:
        if args.index < 0 or args.index >= len(emails):
            parser.error(f"Index {args.index} is outside 0..{len(emails) - 1}.")

        prepared = prepare_email(emails[args.index])
        screen = screen_email(prepared)
        print_screen(args.index, prepared, screen)

        if not screen["candidate"]:
            print("\nStage 1 stopped here, so the model was not called.")
            print(json.dumps({"is_purchase": False, "reason": screen["reason"]}, indent=2))
            return

        result = extract_purchase(emails[args.index])
        print("\nEXTRACTION:")
        print(json.dumps(result, indent=2))
        return

    if args.all:
        extracted = []

        for index, email in enumerate(emails):
            prepared = prepare_email(email)
            screen = screen_email(prepared)
            print_screen(index, prepared, screen)

            if not screen["candidate"]:
                continue

            result = extract_purchase(email)
            print(json.dumps(result, indent=2))

            if result.get("is_purchase"):
                extracted.append({
                    "store": result.get("store"),
                    "order_number": result.get("order_number"),
                    "date": result.get("date"),
                    "total": result.get("total"),
                    "items": result.get("items") or [],
                })

        purchases = dedupe_purchases(extracted)

        with open("purchases.json", "w") as f:
            json.dump(purchases, f, indent=2)

        print(f"\nExtracted {len(extracted)} purchase emails.")
        print(f"Saved {len(purchases)} deduplicated purchases to purchases.json")
        return

    print("Stage 1 only. No OpenAI calls.\n")
    for index, email in enumerate(emails):
        prepared = prepare_email(email)
        screen = screen_email(prepared)
        print_screen(index, prepared, screen)


if __name__ == "__main__":
    main()
