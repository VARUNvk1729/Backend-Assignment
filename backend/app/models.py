from decimal import Decimal
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str

    documents: List["Document"] = Relationship(back_populates="owner")


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    customer: Optional[str] = None
    issue_date: Optional[str] = None
    status: str = Field(default="draft")  # draft or finalized

    owner_id: int = Field(foreign_key="user.id")
    owner: Optional[User] = Relationship(back_populates="documents")
    lines: List["LineItem"] = Relationship(back_populates="document")


class LineItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id")
    description: str
    quantity: Decimal = Field(default=Decimal("1"))
    unit_price: Decimal = Field(default=Decimal("0"))

    # Discount: either discount_amount OR discount_percent
    discount_amount: Optional[Decimal] = None
    discount_percent: Optional[Decimal] = None
    tax_percent: Optional[Decimal] = None

    document: Optional[Document] = Relationship(back_populates="lines")