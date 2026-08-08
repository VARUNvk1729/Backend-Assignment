from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Optional, Dict

# Use a Decimal context with sufficient precision
getcontext().prec = 28

TWO = Decimal("0.01")

def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWO, rounding=ROUND_HALF_UP)

def compute_line(quantity: Decimal, unit_price: Decimal, discount_amount: Optional[Decimal], discount_percent: Optional[Decimal], tax_percent: Optional[Decimal]) -> Dict[str, Decimal]:
    # Ensure Decimals
    q = Decimal(quantity)
    up = Decimal(unit_price)
    subtotal = quantize_money(q * up)

    if discount_amount is not None and discount_percent is not None:
        raise ValueError("Line cannot have both discount_amount and discount_percent")

    if discount_amount is not None:
        disc = Decimal(discount_amount)
        if disc < 0:
            raise ValueError("Discount amount cannot be negative")
        # clamp to subtotal
        if disc > subtotal:
            disc = subtotal
    elif discount_percent is not None:
        dp = Decimal(discount_percent) / Decimal(100)
        if dp < 0:
            raise ValueError("Discount percent cannot be negative")
        disc = quantize_money(subtotal * dp)
    else:
        disc = Decimal("0.00")

    after_discount = quantize_money(subtotal - disc)

    if tax_percent is not None:
        tp = Decimal(tax_percent) / Decimal(100)
        if tp < 0:
            raise ValueError("Tax percent cannot be negative")
        tax_amount = quantize_money(after_discount * tp)
    else:
        tax_amount = Decimal("0.00")

    line_total = quantize_money(after_discount + tax_amount)

    return {
        "subtotal": subtotal,
        "discount": disc,
        "after_discount": after_discount,
        "tax": tax_amount,
        "line_total": line_total,
    }

def compute_document(lines: list) -> Dict[str, Decimal]:
    subtotal = Decimal("0.00")
    total_discount = Decimal("0.00")
    total_tax = Decimal("0.00")
    grand_total = Decimal("0.00")

    for line in lines:
        res = compute_line(
            Decimal(line["quantity"]),
            Decimal(line["unit_price"]),
            Decimal(line["discount_amount"]) if line.get("discount_amount") is not None else None,
            Decimal(line["discount_percent"]) if line.get("discount_percent") is not None else None,
            Decimal(line["tax_percent"]) if line.get("tax_percent") is not None else None,
        )
        subtotal += res["subtotal"]
        total_discount += res["discount"]
        total_tax += res["tax"]
        grand_total += res["line_total"]

    # Quantize totals
    return {
        "subtotal": quantize_money(subtotal),
        "total_discount": quantize_money(total_discount),
        "total_tax": quantize_money(total_tax),
        "grand_total": quantize_money(grand_total),
    }
