"""Player accounts in SQL (Postgres in production, any SQLAlchemy URL locally).

Rows are never mutated in place by callers: each method returns a fresh frozen User.
"""

import time
from dataclasses import dataclass

from sqlalchemy import (
    Column, Float, Integer, MetaData, String, Table, Text, UniqueConstraint, create_engine, insert, select,
    update,
)

from accounts.keys import SealedWallet

STATUSES = ("pending", "funding", "registering", "registered", "failed")

_meta = MetaData()
users = Table(
    "users", _meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("clerk_user_id", String(64), nullable=False),
    Column("email", String(255), nullable=False, server_default=""),
    Column("display_name", String(64), nullable=False, server_default="player"),
    Column("coldkey_ss58", String(64), nullable=False),
    Column("hotkey_ss58", String(64), nullable=False),
    Column("enc_coldkey", Text, nullable=False),
    Column("enc_hotkey", Text, nullable=False),
    Column("uid", Integer),
    Column("reg_status", String(16), nullable=False, server_default="pending"),
    Column("reg_error", Text, nullable=False, server_default=""),
    Column("created_at", Float, nullable=False),
    UniqueConstraint("clerk_user_id"), UniqueConstraint("hotkey_ss58"),
)


@dataclass(frozen=True)
class User:
    id: int
    clerk_user_id: str
    email: str
    display_name: str
    wallet: SealedWallet
    uid: int | None
    reg_status: str
    reg_error: str
    created_at: float


def _user(row) -> User:
    return User(
        id=row.id, clerk_user_id=row.clerk_user_id, email=row.email, display_name=row.display_name,
        wallet=SealedWallet(row.coldkey_ss58, row.hotkey_ss58, row.enc_coldkey, row.enc_hotkey),
        uid=row.uid, reg_status=row.reg_status, reg_error=row.reg_error, created_at=row.created_at,
    )


class AccountStore:
    def __init__(self, url: str) -> None:
        self._engine = create_engine(url, pool_pre_ping=True)
        _meta.create_all(self._engine)

    def by_clerk_id(self, clerk_user_id: str) -> User | None:
        with self._engine.connect() as conn:
            row = conn.execute(select(users).where(users.c.clerk_user_id == clerk_user_id)).first()
        return _user(row) if row else None

    def by_hotkey(self, hotkey: str) -> User | None:
        with self._engine.connect() as conn:
            row = conn.execute(select(users).where(users.c.hotkey_ss58 == hotkey)).first()
        return _user(row) if row else None

    def hotkeys(self) -> set[str]:
        with self._engine.connect() as conn:
            return {row[0] for row in conn.execute(select(users.c.hotkey_ss58))}

    def create(self, clerk_user_id: str, email: str, display_name: str, wallet: SealedWallet) -> User:
        with self._engine.begin() as conn:
            conn.execute(insert(users).values(
                clerk_user_id=clerk_user_id, email=email, display_name=display_name[:64],
                coldkey_ss58=wallet.coldkey_ss58, hotkey_ss58=wallet.hotkey_ss58,
                enc_coldkey=wallet.enc_coldkey, enc_hotkey=wallet.enc_hotkey, created_at=time.time(),
            ))
        created = self.by_clerk_id(clerk_user_id)
        assert created is not None
        return created

    def next_pending(self) -> User | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(users).where(users.c.reg_status.in_(("pending", "funding", "registering")))
                .order_by(users.c.id).limit(1)
            ).first()
        return _user(row) if row else None

    def set_status(self, user_id: int, status: str, error: str = "", uid: int | None = None) -> None:
        if status not in STATUSES:
            raise ValueError(f"unknown registration status {status!r}")
        values: dict = {"reg_status": status, "reg_error": error[:500]}
        if uid is not None:
            values["uid"] = uid
        with self._engine.begin() as conn:
            conn.execute(update(users).where(users.c.id == user_id).values(**values))

    def registered_today(self) -> int:
        cutoff = time.time() - 86400
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(users.c.id).where(users.c.reg_status != "pending", users.c.created_at > cutoff)
            ).all()
        return len(rows)
