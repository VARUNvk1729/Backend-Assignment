import os
import sys
import requests
from decimal import Decimal

BASE = os.getenv("BASE", "http://127.0.0.1:8000")

def signup(email, password):
    return requests.post(f"{BASE}/signup", params={"email": email, "password": password})

def login(email, password):
    return requests.post(f"{BASE}/token", data={"username": email, "password": password})

def create_doc(token, title, customer=None, issue_date=None):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.post(f"{BASE}/documents", headers=headers, params={"title": title, "customer": customer, "issue_date": issue_date})

def add_line(token, doc_id, **kwargs):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.post(f"{BASE}/documents/{doc_id}/lines", headers=headers, params=kwargs)

def finalize(token, doc_id):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.post(f"{BASE}/documents/{doc_id}/finalize", headers=headers)

def get_doc(token, doc_id):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(f"{BASE}/documents/{doc_id}", headers=headers)

def report(token, start_date, end_date):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(f"{BASE}/report", headers=headers, params={"start_date": start_date, "end_date": end_date})


def main():
    print("Running API smoke tests against:", BASE)

    # Use a short password to avoid bcrypt 72-byte issue
    email = "smoketest@example.com"
    password = "test123"

    r = signup(email, password)
    if r.status_code != 200:
        print("Signup failed:", r.status_code, r.text)
        sys.exit(2)
    print("Signup OK")

    r = login(email, password)
    if r.status_code != 200:
        print("Login failed:", r.status_code, r.text)
        sys.exit(3)
    token = r.json().get("access_token")
    if not token:
        print("No access token returned")
        sys.exit(4)
    print("Login OK, token received")

    # Create document
    r = create_doc(token, "Sample", customer="Acme", issue_date="2026-08-01")
    if r.status_code != 200:
        print("Create doc failed:", r.status_code, r.text)
        sys.exit(5)
    doc_id = r.json().get("id")
    print("Created document id", doc_id)

    # Add sample lines
    lines = [
        {"description": "Widget A", "quantity": "2", "unit_price": "100.00", "discount_percent": "10", "tax_percent": "5"},
        {"description": "Widget B", "quantity": "1", "unit_price": "50.00", "tax_percent": "5"},
        {"description": "Service fee", "quantity": "1", "unit_price": "200.00", "discount_amount": "20.00"},
    ]
    for ln in lines:
        r = add_line(token, doc_id, **ln)
        if r.status_code != 200:
            print("Add line failed:", r.status_code, r.text)
            sys.exit(6)
    print("Added sample lines")

    # Fetch doc and verify totals
    r = get_doc(token, doc_id)
    if r.status_code != 200:
        print("Get document failed:", r.status_code, r.text)
        sys.exit(7)
    data = r.json()
    totals = data.get("totals", {})
    expected = {"subtotal": "450.00", "total_discount": "40.00", "total_tax": "11.50", "grand_total": "421.50"}
    print("Document totals:", totals)
    for k, v in expected.items():
        if totals.get(k) != v:
            print(f"Mismatch for {k}: expected {v} got {totals.get(k)}")
            sys.exit(8)
    print("Totals match expected values")

    # Finalize
    r = finalize(token, doc_id)
    if r.status_code != 200:
        print("Finalize failed:", r.status_code, r.text)
        sys.exit(9)
    print("Finalize OK")

    # Attempt to add line to finalized doc (should fail)
    r = add_line(token, doc_id, description="Extra", quantity="1", unit_price="1.00")
    if r.status_code == 200:
        print("ERROR: was able to modify finalized document")
        sys.exit(10)
    print("Immutability enforced (add line rejected)")

    # Report
    r = report(token, "2026-08-01", "2026-08-31")
    if r.status_code != 200:
        print("Report failed:", r.status_code, r.text)
        sys.exit(11)
    rep = r.json()
    print("Report:", rep)

    print("Smoke tests passed")


if __name__ == "__main__":
    main()
