import sqlite3
import unittest
from pathlib import Path

from database.recipe_matcher import RecipeMatcher


ROOT = Path(__file__).resolve().parents[1]


class RecipeMatcherTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(
            (ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
        )
        self.connection.executescript(
            (ROOT / "database" / "seed.sql").read_text(encoding="utf-8")
        )
        self.matcher = RecipeMatcher(self.connection)

    def tearDown(self):
        self.connection.close()

    def ids(self, table, names):
        return [
            self.connection.execute(f"SELECT id FROM {table} WHERE name = ?", (name,)).fetchone()[0]
            for name in names
        ]

    def result(self, results, name):
        return next(recipe for recipe in results if recipe["name"] == name)

    def test_complete_pantry_recipe_ranks_first(self):
        results = self.matcher.match(
            available_ingredient_ids=self.ids("ingredients", ["板豆腐", "雞蛋", "蒜頭", "青蔥"]),
            available_seasoning_ids=self.ids("seasonings", ["醬油", "鹽", "食用油"]),
            available_equipment_ids=self.ids("equipment", ["瓦斯爐", "平底鍋／炒鍋"]),
            cuisine_filter="chinese",
            user_id="demo-user",
        )

        self.assertEqual(results[0]["name"], "蒜香豆腐炒蛋")
        self.assertEqual(results[0]["score"], 100.0)
        self.assertTrue(results[0]["ingredients_complete"])
        self.assertEqual(results[0]["equipment_status"], "compatible")

    def test_missing_bok_choy_shows_available_spinach_substitute(self):
        results = self.matcher.match(
            available_ingredient_ids=self.ids("ingredients", ["雞蛋", "菠菜"]),
            available_seasoning_ids=self.ids("seasonings", ["鹽"]),
            available_equipment_ids=self.ids("equipment", ["瓦斯爐", "湯鍋"]),
            cuisine_filter="chinese",
        )
        soup = self.result(results, "青江菜蛋花湯")
        missing_bok_choy = next(item for item in soup["missing_ingredients"] if item["name"] == "青江菜")

        self.assertEqual(soup["ingredient_status"], "substitution_available")
        self.assertFalse(soup["ingredients_complete"])
        self.assertTrue(soup["ingredients_actionable"])
        self.assertEqual(missing_bok_choy["available_substitutes"][0]["name"], "菠菜")
        self.assertTrue(missing_bok_choy["available_substitutes"][0]["available"])

    def test_unavailable_cooking_device_is_flagged(self):
        results = self.matcher.match(
            available_ingredient_ids=self.ids("ingredients", ["馬鈴薯"]),
            available_seasoning_ids=self.ids("seasonings", ["鹽", "食用油"]),
            available_equipment_ids=self.ids("equipment", ["瓦斯爐", "平底鍋／炒鍋"]),
            cuisine_filter="western",
        )
        potato = self.result(results, "氣炸馬鈴薯塊")

        self.assertEqual(potato["equipment_status"], "inapplicable")
        self.assertEqual(potato["missing_equipment_groups"][0]["options"][0]["name"], "氣炸鍋")
        self.assertEqual(potato["score_breakdown"]["equipment"], 0.0)

    def test_taste_servings_and_spicy_preference_are_applied(self):
        results = self.matcher.match(
            available_ingredient_ids=self.ids("ingredients", ["板豆腐", "雞蛋", "蒜頭"]),
            available_seasoning_ids=self.ids("seasonings", ["醬油", "鹽", "食用油"]),
            available_equipment_ids=self.ids("equipment", ["瓦斯爐", "平底鍋／炒鍋"]),
            cuisine_filter="chinese",
            user_id="demo-user",
            taste_level="light",
            eats_spicy=False,
            servings=3,
        )
        tofu_egg = self.result(results, "蒜香豆腐炒蛋")
        amounts = {item["name"]: item for item in tofu_egg["adjusted_seasonings"]}

        self.assertEqual(amounts["醬油"]["amount"], "12")
        self.assertEqual(amounts["醬油"]["unit"], "ml")
        self.assertEqual(amounts["鹽"]["amount"], "1.2")
        self.assertEqual(amounts["辣椒粉"]["amount"], "0")
        self.assertTrue(amounts["辣椒粉"]["omitted_for_preference"])
        self.assertNotIn("tsp", amounts["鹽"]["equivalents"])
        self.assertIn("tsp", amounts["醬油"]["equivalents"])

    def test_spoon_conversions_are_volume_exact(self):
        results = self.matcher.match(
            available_ingredient_ids=self.ids("ingredients", ["板豆腐", "蒜頭"]),
            available_seasoning_ids=self.ids("seasonings", ["醬油", "蠔油", "砂糖", "食用油"]),
            available_equipment_ids=self.ids("equipment", ["瓦斯爐", "平底鍋／炒鍋"]),
            cuisine_filter="chinese",
            taste_level="medium",
            eats_spicy=True,
            servings=3,
        )
        braised = self.result(results, "醬燒豆腐")
        amounts = {item["name"]: item for item in braised["adjusted_seasonings"]}

        self.assertEqual(amounts["醬油"]["amount"], "1.5")
        self.assertEqual(amounts["醬油"]["unit"], "tbsp")
        self.assertEqual(amounts["醬油"]["equivalents"]["ml"], "22.5")
        self.assertEqual(amounts["蠔油"]["equivalents"]["ml"], "15")

    def test_spicy_preference_keeps_chili_and_scales_it_by_servings(self):
        results = self.matcher.match(
            available_ingredient_ids=self.ids("ingredients", ["板豆腐", "雞蛋", "蒜頭"]),
            available_seasoning_ids=self.ids("seasonings", ["醬油", "鹽", "食用油", "辣椒粉"]),
            available_equipment_ids=self.ids("equipment", ["瓦斯爐", "平底鍋／炒鍋"]),
            cuisine_filter="chinese",
            eats_spicy=True,
            servings=4,
        )
        tofu_egg = self.result(results, "蒜香豆腐炒蛋")
        chili = next(item for item in tofu_egg["adjusted_seasonings"] if item["name"] == "辣椒粉")

        self.assertEqual(chili["amount"], "2")
        self.assertFalse(chili["omitted_for_preference"])

    def test_saved_equipment_is_used_when_not_overridden(self):
        results = self.matcher.match(
            available_ingredient_ids=self.ids("ingredients", ["青江菜", "雞蛋"]),
            available_seasoning_ids=self.ids("seasonings", ["鹽"]),
            user_id="demo-user",
            cuisine_filter="chinese",
        )
        soup = self.result(results, "青江菜蛋花湯")
        self.assertEqual(soup["equipment_status"], "compatible")


if __name__ == "__main__":
    unittest.main()
