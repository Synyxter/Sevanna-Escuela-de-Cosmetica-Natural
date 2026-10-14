"""Reprice cursos into the 150.000–230.000 COP range

Revision ID: 0002_course_prices_2026_10
Revises: 0001_initial
Create Date: 2026-10-14

Data-only migration. The catalog seeder never overwrites existing courses, so
price changes for databases that are already populated (production) ship as a
migration, which the container applies on every deploy. Fresh databases get the
same prices from ``scripts/catalog_data.json``.

New prices keep the previous ordering (level + duration): the old 250k–400k
range is mapped linearly onto 150k–230k and rounded to 5.000 COP. Talleres are
not repriced.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_course_prices_2026_10"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (slug, old price, new price) in COP.
PRICES: list[tuple[str, int, int]] = [
    # BEGINNER
    ("curso-de-bisuteria", 250000, 150000),
    ("curso-de-sales-de-bano", 300000, 175000),
    ("curso-de-tecnica-de-cepillado", 300000, 175000),
    ("curso-de-jabon-melt-pour", 310000, 180000),
    ("curso-de-jabon-natural", 320000, 185000),
    ("curso-de-jabon-para-mascotas", 320000, 185000),
    # INTERMEDIATE
    ("curso-de-jabon-decorativo", 340000, 200000),
    ("curso-de-jabon-de-olato", 340000, 200000),
    ("curso-de-labiales-veganos", 340000, 200000),
    ("curso-de-jabon-crema", 350000, 205000),
    ("curso-de-jabon-gema", 350000, 205000),
    ("curso-de-jabon-jelly-terapeutico", 350000, 205000),
    ("curso-de-jabon-macerado", 350000, 205000),
    ("curso-de-jabon-de-carbon-activado", 350000, 205000),
    ("curso-de-tintes-naturales", 350000, 205000),
    ("curso-de-velas-de-arte", 350000, 205000),
    ("curso-de-champu-y-tratamiento-capilar", 360000, 210000),
    ("curso-de-cierre-de-cabello", 360000, 210000),
    ("curso-de-jabon-aclarante-para-manchas", 360000, 210000),
    ("curso-de-maquillaje-natural", 360000, 210000),
    ("curso-de-maquillaje-vegano", 360000, 210000),
    # ADVANCED
    ("curso-de-ritual-capilar-para-caida-de-cabello", 380000, 220000),
    ("curso-de-fitocosmetica", 390000, 225000),
    ("curso-de-perfumeria", 400000, 230000),
]

courses = sa.table(
    "courses",
    sa.column("slug", sa.String),
    sa.column("price", sa.Numeric(12, 2)),
)


def _set_prices(pick: int) -> None:
    for row in PRICES:
        op.execute(courses.update().where(courses.c.slug == row[0]).values(price=row[pick]))


def upgrade() -> None:
    _set_prices(2)


def downgrade() -> None:
    _set_prices(1)
