"""add username to users

Revision ID: c8f3a1d2e4b5
Revises: ae9a82eda00e
Create Date: 2026-04-16

"""
from __future__ import annotations

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8f3a1d2e4b5"
down_revision: Union[str, None] = "ae9a82eda00e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(), nullable=True))
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, email FROM users")).mappings().all()
    assigned: set[str] = set()
    for row in rows:
        uid = row["id"]
        local = str(row["email"]).split("@", 1)[0]
        base = re.sub(r"[^a-zA-Z0-9_-]", "_", local).strip("_").lower()[:28]
        if len(base) < 3:
            base = f"user{uid}"
        candidate = base
        n = 0
        while candidate in assigned:
            n += 1
            candidate = f"{base[:24]}_{n}"
        assigned.add(candidate)
        conn.execute(
            sa.text("UPDATE users SET username = :u WHERE id = :id"),
            {"u": candidate, "id": uid},
        )
    op.alter_column(
        "users",
        "username",
        existing_type=sa.String(),
        nullable=False,
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "username")
