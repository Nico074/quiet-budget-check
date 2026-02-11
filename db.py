from datetime import datetime
from typing import Optional

import sqlite3
from sqlmodel import SQLModel, Field, create_engine

DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, echo=False)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    plan: str = Field(default="free")
    stripe_customer_id: Optional[str] = Field(default=None)
    stripe_subscription_id: Optional[str] = Field(default=None)
    stripe_status: Optional[str] = Field(default=None)
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


class HealthScoreHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    score: int
    label: str
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


def init_db():
    SQLModel.metadata.create_all(engine)
    _ensure_columns()


def _ensure_columns():
    with sqlite3.connect("app.db") as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(user)")
        cols = {row[1] for row in cur.fetchall()}
        needed = {
            "plan": "TEXT DEFAULT 'free'",
            "stripe_customer_id": "TEXT",
            "stripe_subscription_id": "TEXT",
            "stripe_status": "TEXT",
        }
        for col, ddl in needed.items():
            if col not in cols:
                cur.execute(f"ALTER TABLE user ADD COLUMN {col} {ddl}")
        conn.commit()
