from __future__ import annotations

import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import scripts.seed_catalog as seed_module
from slugify import slugify

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "prices_migration", ROOT / "migrations/versions/0002_course_prices_2026_10.py"
)
migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migration)

DATA = json.loads(seed_module.DATA_FILE.read_text(encoding="utf-8"))
CURSOS = {
    slugify(c["title"]): c for c in DATA["courses"] if not slugify(c["title"]).startswith("taller-")
}
LEVEL_RANK = {"BEGINNER": 0, "INTERMEDIATE": 1, "ADVANCED": 2}


def test_migration_covers_exactly_the_catalog_cursos() -> None:
    assert {slug for slug, _, _ in migration.PRICES} == set(CURSOS)


def test_seed_data_matches_migration_prices() -> None:
    for slug, _, new in migration.PRICES:
        assert Decimal(CURSOS[slug]["price"]) == new, slug


def test_curso_prices_are_in_range() -> None:
    for slug, course in CURSOS.items():
        assert 150_000 <= Decimal(course["price"]) <= 230_000, slug


def test_higher_level_never_costs_less() -> None:
    by_level: dict[int, list[Decimal]] = {0: [], 1: [], 2: []}
    for course in CURSOS.values():
        by_level[LEVEL_RANK[course["level"]]].append(Decimal(course["price"]))
    assert max(by_level[0]) < min(by_level[1])
    assert max(by_level[1]) < min(by_level[2])
