"""initial_schema

Revision ID: 4302b1b001a2
Revises:
Create Date: 2026-04-07 20:12:38.938181

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4302b1b001a2"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "keyword",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_keyword_name"),
    )
    op.create_index(op.f("ix_keyword_name"), "keyword", ["name"], unique=False)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_table(
        "paper",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("authors", sa.String(), nullable=False),
        sa.Column("doi", sa.String(), nullable=True),
        sa.Column("arxiv_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("search_document", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_opened_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_paper_arxiv_id"), "paper", ["arxiv_id"], unique=False)
    op.create_index(op.f("ix_paper_doi"), "paper", ["doi"], unique=False)
    op.create_table(
        "dailylog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["paper.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dailylog_activity_date"), "dailylog", ["activity_date"], unique=False)
    op.create_index(op.f("ix_dailylog_user_id"), "dailylog", ["user_id"], unique=False)
    op.create_table(
        "paperkeyword",
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("keyword_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["keyword_id"], ["keyword.id"]),
        sa.ForeignKeyConstraint(["paper_id"], ["paper.id"]),
        sa.PrimaryKeyConstraint("paper_id", "keyword_id"),
    )


def downgrade() -> None:
    op.drop_table("paperkeyword")
    op.drop_index(op.f("ix_dailylog_user_id"), table_name="dailylog")
    op.drop_index(op.f("ix_dailylog_activity_date"), table_name="dailylog")
    op.drop_table("dailylog")
    op.drop_index(op.f("ix_paper_doi"), table_name="paper")
    op.drop_index(op.f("ix_paper_arxiv_id"), table_name="paper")
    op.drop_table("paper")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_keyword_name"), table_name="keyword")
    op.drop_table("keyword")
