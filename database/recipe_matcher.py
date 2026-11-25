"""Database-backed recipe matching, ranking, and seasoning calculations.

Example::

    with RecipeMatcher.from_path("data/菜就多煉.sqlite3") as matcher:
        results = matcher.match(
            user_id="demo-user",
            available_ingredient_ids=[1, 2, 3],
            available_seasoning_ids=[1, 2, 5],
            cuisine_filter="chinese",
        )

All recipe content and substitute suggestions come from SQLite. The matcher
does not generate recipes or infer unrecorded ingredient substitutions.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable
_TASTE_FACTORS = {
    "light": Decimal("0.8"),
    "medium": Decimal("1.0"),
    "strong": Decimal("1.2"),
}
_VOLUME_ML = {
    "ml": Decimal("1"),
    "tsp": Decimal("5"),
    "tbsp": Decimal("15"),
}
_SUPPORTED_SEASONING_UNITS = ("g", "tsp", "tbsp", "ml")


def _decimal_text(value: Decimal) -> str:
    """Format an internal Decimal without insignificant trailing zeroes."""
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _display_decimal(value: Decimal) -> str:
    """Round only at the response/display boundary, to 0.001 unit."""
    rounded = value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return _decimal_text(rounded)


def _as_id_set(values: Iterable[int] | None, label: str) -> set[int]:
    if values is None:
        return set()
    result: set[int] = set()
    for value in values:
        if type(value) is not int or value <= 0:
            raise ValueError(f"{label} must contain positive integer database IDs")
        result.add(value)
    return result


class RecipeMatcher:
    """Match stored recipes to pantry, seasoning, equipment, and taste inputs.

    Scoring is deterministic and totals 100 points:

    * required ingredients: 60 points; an exact match earns full credit and
      an available, registered substitute earns 75% credit;
    * required seasonings: 20 points;
    * equipment: 20 points when every required equipment group is satisfied.

    Each equipment group accepts any one of its listed devices. All groups
    must be satisfied for an equipment-compatible recipe.
    """

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.connection.row_factory = sqlite3.Row

    @classmethod
    def from_path(cls, path: str | Path) -> "RecipeMatcher":
        connection = sqlite3.connect(str(path))
        connection.execute("PRAGMA foreign_keys = ON")
        return cls(connection)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "RecipeMatcher":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def match(
        self,
        *,
        available_ingredient_ids: Iterable[int] = (),
        available_seasoning_ids: Iterable[int] = (),
        available_equipment_ids: Iterable[int] | None = None,
        cuisine_filter: str = "any",
        user_id: str | None = None,
        servings: int | None = None,
        taste_level: str | None = None,
        eats_spicy: bool | None = None,
    ) -> list[dict[str, object]]:
        """Return cuisine-matching recipes, best score first.

        When ``available_equipment_ids`` is omitted and ``user_id`` is given,
        the user's saved equipment is used. An explicit empty iterable means
        that no equipment is currently available. Taste and default serving
        settings are loaded from ``personal_settings`` for that user; explicit
        overrides are useful for previews and tests.
        """
        if cuisine_filter not in {"any", "chinese", "western"}:
            raise ValueError("cuisine_filter must be any, chinese, or western")

        ingredient_ids = _as_id_set(available_ingredient_ids, "available_ingredient_ids")
        seasoning_ids = _as_id_set(available_seasoning_ids, "available_seasoning_ids")
        preferences = self._load_preferences(user_id)

        if available_equipment_ids is None:
            equipment_ids = self._load_saved_equipment(user_id) if user_id else set()
        else:
            equipment_ids = _as_id_set(available_equipment_ids, "available_equipment_ids")

        selected_taste = taste_level if taste_level is not None else preferences["taste_level"]
        if selected_taste not in _TASTE_FACTORS:
            raise ValueError("taste_level must be light, medium, or strong")
        selected_spicy = preferences["eats_spicy"] if eats_spicy is None else eats_spicy
        if type(selected_spicy) is not bool:
            raise ValueError("eats_spicy must be a bool")

        recipe_rows = self.connection.execute(
            "SELECT * FROM recipes WHERE (? = 'any' OR cuisine_type = ?) ORDER BY id",
            (cuisine_filter, cuisine_filter),
        ).fetchall()
        recipes: list[dict[str, object]] = []

        for recipe in recipe_rows:
            base_servings = int(recipe["base_servings"])
            target_servings = servings if servings is not None else int(preferences["default_servings"] or base_servings)
            if type(target_servings) is not int or target_servings <= 0:
                raise ValueError("servings must be a positive integer")
            recipes.append(
                self._match_one(
                    recipe=recipe,
                    ingredient_ids=ingredient_ids,
                    seasoning_ids=seasoning_ids,
                    equipment_ids=equipment_ids,
                    taste_level=selected_taste,
                    eats_spicy=selected_spicy,
                    servings=target_servings,
                )
            )

        recipes.sort(
            key=lambda item: (
                -float(item["score"]),
                not bool(item["ingredients_complete"]),
                -int(item["required_seasonings_matched"]),
                int(item["cook_time_min"]),
                int(item["id"]),
            )
        )
        return recipes

    def _load_preferences(self, user_id: str | None) -> dict[str, object]:
        defaults: dict[str, object] = {
            "taste_level": "medium",
            "eats_spicy": False,
            "default_servings": 2,
        }
        if user_id is None:
            return defaults
        row = self.connection.execute(
            """SELECT taste_level, eats_spicy, default_servings
               FROM personal_settings WHERE user_id = ?""",
            (user_id,),
        ).fetchone()
        if row is None:
            exists = self.connection.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone()
            if exists is None:
                raise ValueError(f"unknown user_id: {user_id}")
            return defaults
        return {
            "taste_level": row["taste_level"],
            "eats_spicy": bool(row["eats_spicy"]),
            "default_servings": int(row["default_servings"]),
        }

    def _load_saved_equipment(self, user_id: str | None) -> set[int]:
        if user_id is None:
            return set()
        return {
            int(row["equipment_id"])
            for row in self.connection.execute(
                "SELECT equipment_id FROM user_equipment WHERE user_id = ?", (user_id,)
            )
        }

    def _match_one(
        self,
        *,
        recipe: sqlite3.Row,
        ingredient_ids: set[int],
        seasoning_ids: set[int],
        equipment_ids: set[int],
        taste_level: str,
        eats_spicy: bool,
        servings: int,
    ) -> dict[str, object]:
        recipe_id = int(recipe["id"])
        ingredient_rows = self.connection.execute(
            """SELECT ri.*, i.name, i.aliases_json
               FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
               WHERE ri.recipe_id = ? ORDER BY ri.is_primary DESC, i.name""",
            (recipe_id,),
        ).fetchall()
        seasoning_rows = self.connection.execute(
            """SELECT rs.*, s.name, s.is_spicy, s.grams_per_ml, s.density_quality
               FROM recipe_seasonings rs JOIN seasonings s ON s.id = rs.seasoning_id
               WHERE rs.recipe_id = ? ORDER BY s.name""",
            (recipe_id,),
        ).fetchall()

        exact_ingredient_ids: set[int] = set()
        missing_ingredients: list[dict[str, object]] = []
        required_ingredient_count = 0
        required_ingredient_credit = Decimal("0")
        required_ingredients_complete = True
        required_ingredients_actionable = True

        for row in ingredient_rows:
            ingredient_id = int(row["ingredient_id"])
            required = bool(row["is_required"])
            if required:
                required_ingredient_count += 1
            if ingredient_id in ingredient_ids:
                exact_ingredient_ids.add(ingredient_id)
                if required:
                    required_ingredient_credit += Decimal("1")
                continue

            alternatives = self._substitutes_for(ingredient_id, ingredient_ids)
            has_available_alternative = any(bool(item["available"]) for item in alternatives)
            if required:
                required_ingredients_complete = False
                if has_available_alternative:
                    required_ingredient_credit += Decimal("0.75")
                else:
                    required_ingredients_actionable = False
            missing_ingredients.append(
                {
                    "id": ingredient_id,
                    "name": row["name"],
                    "quantity": str(row["quantity_value"]),
                    "unit": row["unit"],
                    "required": required,
                    "primary": bool(row["is_primary"]),
                    "preparation_note": row["preparation_note"],
                    "available_substitutes": alternatives,
                    "substitution_available": has_available_alternative,
                }
            )

        required_seasoning_count = 0
        required_seasonings_matched = 0
        missing_seasonings: list[dict[str, object]] = []
        adjusted_seasonings: list[dict[str, object]] = []
        taste_factor = _TASTE_FACTORS[taste_level]
        serving_factor = Decimal(servings) / Decimal(int(recipe["base_servings"]))

        for row in seasoning_rows:
            seasoning_id = int(row["seasoning_id"])
            required = bool(row["is_required"])
            is_spicy = bool(row["is_spicy"])
            skipped_for_preference = is_spicy and not eats_spicy
            present = seasoning_id in seasoning_ids

            # A seasoning deliberately reduced to zero is not a missing pantry item.
            if not skipped_for_preference and required:
                required_seasoning_count += 1
                if present:
                    required_seasonings_matched += 1

            if not present and not skipped_for_preference:
                missing_seasonings.append(
                    {
                        "id": seasoning_id,
                        "name": row["name"],
                        "quantity": str(row["quantity_value"]),
                        "unit": row["unit"],
                        "required": required,
                        "spicy": is_spicy,
                    }
                )

            base_amount = Decimal(str(row["quantity_value"]))
            adjusted = base_amount * serving_factor
            if bool(row["taste_adjustable"]):
                adjusted *= taste_factor
            if skipped_for_preference:
                adjusted = Decimal("0")
            unit = str(row["unit"])
            adjusted_seasonings.append(
                {
                    "id": seasoning_id,
                    "name": row["name"],
                    "base_amount": str(row["quantity_value"]),
                    "base_unit": unit,
                    "amount": _display_decimal(adjusted),
                    "unit": unit,
                    "taste_adjustable": bool(row["taste_adjustable"]),
                    "spicy": is_spicy,
                    "omitted_for_preference": skipped_for_preference,
                    "equivalents": self._equivalents(adjusted, unit, row),
                    "unavailable_conversions": self._unavailable_conversions(unit, row),
                }
            )

        equipment = self._equipment_status(recipe_id, equipment_ids)
        ingredient_score = (
            Decimal("60") * required_ingredient_credit / Decimal(required_ingredient_count)
            if required_ingredient_count
            else Decimal("60")
        )
        seasoning_score = (
            Decimal("20") * Decimal(required_seasonings_matched) / Decimal(required_seasoning_count)
            if required_seasoning_count
            else Decimal("20")
        )
        equipment_score = Decimal("20") if equipment["compatible"] else Decimal("0")
        score = (ingredient_score + seasoning_score + equipment_score).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

        if required_ingredients_complete:
            ingredient_status = "complete"
        elif required_ingredients_actionable:
            ingredient_status = "substitution_available"
        else:
            ingredient_status = "missing_required"

        all_missing: list[dict[str, object]] = [
            {**item, "kind": "ingredient"} for item in missing_ingredients
        ] + [{**item, "kind": "seasoning"} for item in missing_seasonings]

        return {
            "id": recipe_id,
            "slug": recipe["slug"],
            "name": recipe["name"],
            "cuisine_type": recipe["cuisine_type"],
            "description": recipe["description"],
            "cook_time_min": int(recipe["cook_time_min"]),
            "base_servings": int(recipe["base_servings"]),
            "requested_servings": servings,
            "score": float(score),
            "score_breakdown": {
                "ingredients": float(ingredient_score.quantize(Decimal("0.1"))),
                "seasonings": float(seasoning_score.quantize(Decimal("0.1"))),
                "equipment": float(equipment_score),
                "maximum": 100,
            },
            "ingredients_complete": required_ingredients_complete,
            "ingredients_actionable": required_ingredients_actionable,
            "ingredient_status": ingredient_status,
            "matched_ingredients": sorted(exact_ingredient_ids),
            "missing_ingredients": missing_ingredients,
            "missing_seasonings": missing_seasonings,
            "missing_materials": all_missing,
            "required_seasonings_matched": required_seasonings_matched,
            "required_seasonings_total": required_seasoning_count,
            "equipment_status": "compatible" if equipment["compatible"] else "inapplicable",
            "equipment_compatible": bool(equipment["compatible"]),
            "matched_equipment": equipment["matched"],
            "missing_equipment_groups": equipment["missing_groups"],
            "taste_settings": {
                "taste_level": taste_level,
                "eats_spicy": eats_spicy,
                "servings": servings,
            },
            "adjusted_seasonings": adjusted_seasonings,
        }

    def _substitutes_for(self, ingredient_id: int, available_ids: set[int]) -> list[dict[str, object]]:
        rows = self.connection.execute(
            """SELECT sub.substitute_ingredient_id AS id, i.name,
                      sub.usage_note, sub.cooking_adjustment
               FROM ingredient_substitutions sub
               JOIN ingredients i ON i.id = sub.substitute_ingredient_id
               WHERE sub.source_ingredient_id = ? ORDER BY i.name""",
            (ingredient_id,),
        ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "name": row["name"],
                "available": int(row["id"]) in available_ids,
                "usage_note": row["usage_note"],
                "cooking_adjustment": row["cooking_adjustment"],
            }
            for row in rows
        ]

    def _equipment_status(self, recipe_id: int, available_ids: set[int]) -> dict[str, object]:
        rows = self.connection.execute(
            """SELECT re.requirement_group, e.id, e.name
               FROM recipe_equipment re JOIN equipment e ON e.id = re.equipment_id
               WHERE re.recipe_id = ? ORDER BY re.requirement_group, e.name""",
            (recipe_id,),
        ).fetchall()
        groups: dict[int, list[sqlite3.Row]] = defaultdict(list)
        for row in rows:
            groups[int(row["requirement_group"])].append(row)
        matched: list[dict[str, object]] = []
        missing: list[dict[str, object]] = []
        for group_id, options in groups.items():
            selected = [row for row in options if int(row["id"]) in available_ids]
            if selected:
                matched.append(
                    {
                        "requirement_group": group_id,
                        "name": selected[0]["name"],
                        "id": int(selected[0]["id"]),
                    }
                )
            else:
                missing.append(
                    {
                        "requirement_group": group_id,
                        "options": [
                            {"id": int(row["id"]), "name": row["name"]} for row in options
                        ],
                    }
                )
        return {"compatible": not missing, "matched": matched, "missing_groups": missing}

    @staticmethod
    def _verified_density(row: sqlite3.Row) -> Decimal | None:
        if row["density_quality"] != "verified" or row["grams_per_ml"] is None:
            return None
        density = Decimal(str(row["grams_per_ml"]))
        return density if density > 0 else None

    def _equivalents(self, amount: Decimal, unit: str, row: sqlite3.Row) -> dict[str, str]:
        result: dict[str, str] = {}
        density = self._verified_density(row)
        if unit == "g":
            result["g"] = _display_decimal(amount)
            if density is not None:
                milliliters = amount / density
                for volume_unit, ml_per_unit in _VOLUME_ML.items():
                    result[volume_unit] = _display_decimal(milliliters / ml_per_unit)
            return result

        milliliters = amount * _VOLUME_ML[unit]
        for volume_unit, ml_per_unit in _VOLUME_ML.items():
            result[volume_unit] = _display_decimal(milliliters / ml_per_unit)
        if density is not None:
            result["g"] = _display_decimal(milliliters * density)
        return {key: result[key] for key in _SUPPORTED_SEASONING_UNITS if key in result}

    def _unavailable_conversions(self, unit: str, row: sqlite3.Row) -> dict[str, str]:
        density = self._verified_density(row)
        cross_dimension_missing = density is None
        unavailable: dict[str, str] = {}
        for target in _SUPPORTED_SEASONING_UNITS:
            if target == unit:
                continue
            if (unit == "g") != (target == "g") and cross_dimension_missing:
                unavailable[target] = "缺少已確認的品項密度，不能可靠地在克數與體積間換算。"
        return unavailable
