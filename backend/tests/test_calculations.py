from backend.app.calculations import compute_line, compute_document
from decimal import Decimal


def test_sample_document():
    lines = [
        {"quantity": Decimal("2"), "unit_price": Decimal("100.00"), "discount_percent": Decimal("10"), "tax_percent": Decimal("5")},
        {"quantity": Decimal("1"), "unit_price": Decimal("50.00"), "tax_percent": Decimal("5")},
        {"quantity": Decimal("1"), "unit_price": Decimal("200.00"), "discount_amount": Decimal("20.00")},
    ]
    doc_totals = compute_document(lines)
    assert doc_totals["subtotal"] == Decimal("450.00")
    assert doc_totals["total_discount"] == Decimal("40.00")
    assert doc_totals["total_tax"] == Decimal("11.50")
    assert doc_totals["grand_total"] == Decimal("421.50")
