from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from .db import init_db, get_session
from .models import User, Document, LineItem
from .auth import hash_password, verify_password, create_access_token, get_current_user, PWD_CTX
from .calculations import compute_line, compute_document
from typing import List
from decimal import Decimal

app = FastAPI(title="Multi-Rate Pricing Calculator")


@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/signup")
def signup(email: str, password: str, session: Session = Depends(get_session)):
    try:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        user = User(email=email, hashed_password=hash_password(password))
        session.add(user)
        session.commit()
        session.refresh(user)
        return {"id": user.id, "email": user.email}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Surface the error during development; in production hide internals.
        raise HTTPException(status_code=500, detail=f"Signup error: {e}")


@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")

    # First try standard verify
    if not verify_password(form_data.password, user.hashed_password):
        # Fallback: some older hashes may have been created with a truncated password
        # due to bcrypt 72-byte limit. Try verifying a truncated version and upgrade
        # to the preferred hashing algorithm on success.
        try:
            b = form_data.password.encode("utf-8")
        except Exception:
            b = str(form_data.password).encode("utf-8", errors="ignore")
        if len(b) > 72:
            truncated = b[:72].decode("utf-8", errors="ignore")
        else:
            truncated = form_data.password

        try:
            if PWD_CTX.verify(truncated, user.hashed_password):
                # upgrade stored hash to preferred algorithm using full password
                user.hashed_password = hash_password(form_data.password)
                session.add(user)
                session.commit()
            else:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


def check_ownership(doc: Document, user: User):
    if doc.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")


@app.post("/documents")
def create_document(title: str, customer: str = None, issue_date: str = None, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    doc = Document(title=title, customer=customer, issue_date=issue_date, owner_id=user.id)
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return {"id": doc.id}


@app.get("/documents/{doc_id}")
def get_document(doc_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    doc = session.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    check_ownership(doc, user)
    lines = []
    for l in doc.lines:
        lines.append({
            "id": l.id,
            "description": l.description,
            "quantity": str(l.quantity),
            "unit_price": str(l.unit_price),
            "discount_amount": str(l.discount_amount) if l.discount_amount is not None else None,
            "discount_percent": str(l.discount_percent) if l.discount_percent is not None else None,
            "tax_percent": str(l.tax_percent) if l.tax_percent is not None else None,
        })
    totals = compute_document([{
        "quantity": l["quantity"],
        "unit_price": l["unit_price"],
        "discount_amount": l["discount_amount"],
        "discount_percent": l["discount_percent"],
        "tax_percent": l["tax_percent"],
    } for l in lines])
    return {"id": doc.id, "title": doc.title, "status": doc.status, "lines": lines, "totals": {k: str(v) for k, v in totals.items()}}


@app.post("/documents/{doc_id}/lines")
def add_line(doc_id: int, description: str, quantity: Decimal, unit_price: Decimal, discount_amount: Decimal = None, discount_percent: Decimal = None, tax_percent: Decimal = None, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    doc = session.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    check_ownership(doc, user)
    if doc.status != "draft":
        raise HTTPException(400, "Cannot modify a finalized document")
    # Validation
    if quantity < 1:
        raise HTTPException(400, "Quantity must be >= 1")
    if unit_price < 0:
        raise HTTPException(400, "Unit price must be >= 0")
    if discount_amount is not None and discount_percent is not None:
        raise HTTPException(400, "Provide either discount_amount or discount_percent, not both")
    line = LineItem(document_id=doc.id, description=description, quantity=quantity, unit_price=unit_price, discount_amount=discount_amount, discount_percent=discount_percent, tax_percent=tax_percent)
    session.add(line)
    session.commit()
    session.refresh(line)
    return {"id": line.id}


@app.post("/documents/{doc_id}/finalize")
def finalize_document(doc_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    doc = session.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    check_ownership(doc, user)
    if doc.status == "finalized":
        raise HTTPException(400, "Document already finalized")
    # validate lines
    for l in doc.lines:
        if l.quantity <= 0:
            raise HTTPException(400, detail=f"Line {l.id} has invalid quantity")
        if l.unit_price < 0:
            raise HTTPException(400, detail=f"Line {l.id} has invalid unit price")
    doc.status = "finalized"
    session.add(doc)
    session.commit()
    return {"id": doc.id, "status": doc.status}


@app.get("/report")
def report(start_date: str, end_date: str, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    # simple date filter by string matching; in production, use proper dates
    docs = session.exec(select(Document).where(Document.owner_id == user.id)).all()
    filtered = [d for d in docs if d.issue_date and start_date <= d.issue_date <= end_date]
    count = len(filtered)
    sum_grand = Decimal("0.00")
    sum_tax = Decimal("0.00")
    sum_discount = Decimal("0.00")
    for d in filtered:
        lines = []
        for l in d.lines:
            lines.append({
                "quantity": str(l.quantity),
                "unit_price": str(l.unit_price),
                "discount_amount": str(l.discount_amount) if l.discount_amount is not None else None,
                "discount_percent": str(l.discount_percent) if l.discount_percent is not None else None,
                "tax_percent": str(l.tax_percent) if l.tax_percent is not None else None,
            })
        totals = compute_document(lines)
        sum_grand += totals["grand_total"]
        sum_tax += totals["total_tax"]
        sum_discount += totals["total_discount"]
    return {"count": count, "sum_grand_total": str(sum_grand), "sum_tax": str(sum_tax), "sum_discount": str(sum_discount)}
