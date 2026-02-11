from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, create_engine

DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, echo=False)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CheckHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")

    net_income: float
    fixed_expenses: float
    today_expense: float
    days_left: int

    daily_budget: float
    status: str
    message: str

    created_at: datetime = Field(default_factory=datetime.utcnow)


class Profile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    first_name: Optional[str] = Field(default="")
    last_name: Optional[str] = Field(default="")
    address: Optional[str] = Field(default="")
    city: Optional[str] = Field(default="")
    country: Optional[str] = Field(default="")
    phone: Optional[str] = Field(default="")


def init_db():
    SQLModel.metadata.create_all(engine)
