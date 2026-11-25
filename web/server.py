"""Small standard-library HTTP server for the recipe UI and RecipeMatcher API."""

from __future__ import annotations

import json
import sqlite3
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = Path(__file__).with_name("static")
DATABASE_PATH = PROJECT_ROOT / "data" / "菜就多煉.sqlite3"
DEFAULT_USER_ID = "demo-user"
sys.path.insert(0, str(PROJECT_ROOT))

from database.recipe_matcher import RecipeMatcher  # noqa: E402


def connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def require_user(connection: sqlite3.Connection, user_id: str) -> None:
    if connection.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
        raise ValueError(f"找不到使用者：{user_id}")


class RecipeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:
        # Keep the local development terminal quiet except for API errors.
        if args and str(args[1]).startswith("5"):
            super().log_message(format, *args)

    def send_json(self, payload: object, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("請求內容過大")
        raw = self.rfile.read(length)
        body = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(body, dict):
            raise ValueError("請求內容格式錯誤")
        return body

    @staticmethod
    def get_user(query: dict[str, list[str]]) -> str:
        return query.get("user_id", [DEFAULT_USER_ID])[0]

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        if path == "/api/bootstrap":
            self.get_bootstrap(self.get_user(query))
        elif path == "/api/favorites":
            self.get_favorites(self.get_user(query), query.get("folder_id", [None])[0])
        elif path == "/api/folders":
            self.get_folders(self.get_user(query))
        else:
            super().do_GET()

    def do_POST(self) -> None:
        path = unquote(urlsplit(self.path).path)
        try:
            body = self.read_json()
            if path == "/api/match":
                self.post_match(body)
            elif path == "/api/recipe-detail":
                self.post_recipe_detail(body)
            elif path == "/api/favorites":
                self.post_favorite(body)
            elif path == "/api/folders":
                self.post_folder(body)
            else:
                self.send_json({"error": "找不到這個 API"}, 404)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
            self.send_json({"error": str(error)}, 400)
        except sqlite3.IntegrityError as error:
            self.send_json({"error": f"資料未能儲存：{error}"}, 400)
        except Exception as error:  # noqa: BLE001 - return a useful local API response
            self.send_json({"error": f"伺服器發生錯誤：{error}"}, 500)

    def do_PUT(self) -> None:
        path = unquote(urlsplit(self.path).path)
        try:
            body = self.read_json()
            if path == "/api/settings":
                self.put_settings(body)
            elif path == "/api/favorites":
                self.post_favorite(body)
            else:
                self.send_json({"error": "找不到這個 API"}, 404)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
            self.send_json({"error": str(error)}, 400)
        except sqlite3.IntegrityError as error:
            self.send_json({"error": f"資料未能儲存：{error}"}, 400)
        except Exception as error:  # noqa: BLE001
            self.send_json({"error": f"伺服器發生錯誤：{error}"}, 500)

    def do_DELETE(self) -> None:
        path = unquote(urlsplit(self.path).path)
        query = parse_qs(urlsplit(self.path).query)
        user_id = self.get_user(query)
        try:
            if path.startswith("/api/favorites/"):
                self.delete_favorite(path.rsplit("/", 1)[-1], user_id)
            elif path.startswith("/api/folders/"):
                self.delete_folder(path.rsplit("/", 1)[-1], user_id)
            else:
                self.send_json({"error": "找不到這個 API"}, 404)
        except (ValueError, TypeError) as error:
            self.send_json({"error": str(error)}, 400)
        except Exception as error:  # noqa: BLE001
            self.send_json({"error": f"伺服器發生錯誤：{error}"}, 500)

    def get_bootstrap(self, user_id: str) -> None:
        with connect_db() as connection:
            require_user(connection, user_id)
            settings = connection.execute(
                "SELECT taste_level, eats_spicy, default_servings FROM personal_settings WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if settings is None:
                settings = {"taste_level": "medium", "eats_spicy": 0, "default_servings": 2}
            payload = {
                "user_id": user_id,
                "settings": {
                    "taste_level": settings["taste_level"],
                    "eats_spicy": bool(settings["eats_spicy"]),
                    "default_servings": int(settings["default_servings"]),
                },
                "equipment_ids": [
                    row[0]
                    for row in connection.execute(
                        "SELECT equipment_id FROM user_equipment WHERE user_id = ?", (user_id,)
                    )
                ],
                "equipment": [dict(row) for row in connection.execute(
                    "SELECT id, name, category FROM equipment ORDER BY category, id"
                )],
                "ingredients": [dict(row) for row in connection.execute(
                    "SELECT id, name, category FROM ingredients ORDER BY category, name"
                )],
                "seasonings": [dict(row) for row in connection.execute(
                    "SELECT id, name, category, is_spicy FROM seasonings ORDER BY category, id"
                )],
            }
        self.send_json(payload)

    def put_settings(self, body: dict[str, object]) -> None:
        user_id = str(body.get("user_id", DEFAULT_USER_ID))
        taste_level = body.get("taste_level")
        eats_spicy = body.get("eats_spicy")
        servings = body.get("default_servings", 2)
        equipment_ids = body.get("equipment_ids", [])
        if taste_level not in {"light", "medium", "strong"}:
            raise ValueError("口味濃淡請選清淡、適中或重口味")
        if type(eats_spicy) is not bool:
            raise ValueError("是否吃辣必須是布林值")
        if type(servings) is not int or servings < 1 or servings > 20:
            raise ValueError("預設份數需介於 1 至 20")
        if not isinstance(equipment_ids, list) or any(type(item) is not int for item in equipment_ids):
            raise ValueError("器具清單格式錯誤")
        with connect_db() as connection:
            require_user(connection, user_id)
            connection.execute(
                """INSERT INTO personal_settings (user_id, taste_level, eats_spicy, default_servings)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET taste_level=excluded.taste_level,
                     eats_spicy=excluded.eats_spicy, default_servings=excluded.default_servings,
                     updated_at=CURRENT_TIMESTAMP""",
                (user_id, taste_level, int(eats_spicy), servings),
            )
            connection.execute("DELETE FROM user_equipment WHERE user_id = ?", (user_id,))
            connection.executemany(
                "INSERT INTO user_equipment (user_id, equipment_id) VALUES (?, ?)",
                [(user_id, equipment_id) for equipment_id in sorted(set(equipment_ids))],
            )
        self.send_json({"saved": True})

    def post_match(self, body: dict[str, object]) -> None:
        user_id = str(body.get("user_id", DEFAULT_USER_ID))
        ingredient_ids = body.get("ingredient_ids", [])
        seasoning_ids = body.get("seasoning_ids", [])
        servings = body.get("servings")
        if not isinstance(ingredient_ids, list) or not isinstance(seasoning_ids, list):
            raise ValueError("食材與調味料請使用清單格式")
        with RecipeMatcher.from_path(DATABASE_PATH) as matcher:
            results = matcher.match(
                user_id=user_id,
                available_ingredient_ids=ingredient_ids,
                available_seasoning_ids=seasoning_ids,
                cuisine_filter=str(body.get("cuisine_filter", "any")),
                servings=servings if servings is None else int(servings),
            )
        self.send_json({"results": results})

    def post_recipe_detail(self, body: dict[str, object]) -> None:
        slug = str(body.get("slug", ""))
        user_id = str(body.get("user_id", DEFAULT_USER_ID))
        with connect_db() as connection:
            require_user(connection, user_id)
            recipe = connection.execute("SELECT * FROM recipes WHERE slug = ?", (slug,)).fetchone()
            if recipe is None:
                self.send_json({"error": "找不到這道食譜"}, 404)
                return
            ingredients = [dict(row) for row in connection.execute(
                """SELECT i.id AS ingredient_id, i.name, i.category, ri.quantity_value,
                          ri.unit, ri.is_required, ri.is_primary, ri.preparation_note
                   FROM recipe_ingredients ri JOIN ingredients i ON i.id=ri.ingredient_id
                   WHERE ri.recipe_id=? ORDER BY ri.is_primary DESC, i.name""",
                (recipe["id"],),
            )]
            seasonings = [dict(row) for row in connection.execute(
                """SELECT s.id AS seasoning_id, s.name, s.category, s.is_spicy,
                          rs.quantity_value, rs.unit, rs.is_required, rs.taste_adjustable
                   FROM recipe_seasonings rs JOIN seasonings s ON s.id=rs.seasoning_id
                   WHERE rs.recipe_id=? ORDER BY s.name""",
                (recipe["id"],),
            )]
            equipment_rows = connection.execute(
                """SELECT e.id, e.name, re.requirement_group
                   FROM recipe_equipment re JOIN equipment e ON e.id=re.equipment_id
                   WHERE re.recipe_id=? ORDER BY re.requirement_group, e.name""",
                (recipe["id"],),
            ).fetchall()
            equipment_groups: dict[int, list[dict[str, object]]] = {}
            for row in equipment_rows:
                equipment_groups.setdefault(int(row["requirement_group"]), []).append(
                    {"id": row["id"], "name": row["name"]}
                )
            steps = [dict(row) for row in connection.execute(
                "SELECT step_number, instruction, duration_min FROM recipe_steps WHERE recipe_id=? ORDER BY step_number",
                (recipe["id"],),
            )]
            favorite = connection.execute(
                "SELECT folder_id FROM recipe_favorites WHERE user_id=? AND recipe_id=?",
                (user_id, recipe["id"]),
            ).fetchone()

        available_ingredients = body.get("ingredient_ids", [item["ingredient_id"] for item in ingredients])
        available_seasonings = body.get("seasoning_ids", [item["seasoning_id"] for item in seasonings])
        with RecipeMatcher.from_path(DATABASE_PATH) as matcher:
            match = next(
                item for item in matcher.match(
                    user_id=user_id,
                    available_ingredient_ids=available_ingredients,
                    available_seasoning_ids=available_seasonings,
                    cuisine_filter=str(recipe["cuisine_type"]),
                    servings=body.get("servings"),
                ) if item["slug"] == slug
            )
        self.send_json({
            "recipe": {
                "id": recipe["id"], "slug": recipe["slug"], "name": recipe["name"],
                "cuisine_type": recipe["cuisine_type"], "description": recipe["description"],
                "cook_time_min": recipe["cook_time_min"], "base_servings": recipe["base_servings"],
            },
            "ingredients": ingredients,
            "seasonings": seasonings,
            "equipment_groups": [
                {"requirement_group": group_id, "options": options}
                for group_id, options in equipment_groups.items()
            ],
            "steps": steps,
            "favorite_folder_id": favorite["folder_id"] if favorite else None,
            "match": match,
        })

    def get_folders(self, user_id: str) -> None:
        with connect_db() as connection:
            require_user(connection, user_id)
            folders = [dict(row) for row in connection.execute(
                """SELECT ff.id, ff.name, COUNT(rf.recipe_id) AS recipe_count
                   FROM favorite_folders ff LEFT JOIN recipe_favorites rf ON rf.folder_id=ff.id
                   WHERE ff.user_id=? GROUP BY ff.id ORDER BY ff.id""",
                (user_id,),
            )]
        self.send_json({"folders": folders})

    def get_favorites(self, user_id: str, folder_id_value: str | None) -> None:
        with connect_db() as connection:
            require_user(connection, user_id)
            sql = """SELECT r.id, r.slug, r.name, r.cuisine_type, r.description,
                            r.cook_time_min, r.base_servings, rf.folder_id, ff.name AS folder_name
                     FROM recipe_favorites rf JOIN recipes r ON r.id=rf.recipe_id
                     LEFT JOIN favorite_folders ff ON ff.id=rf.folder_id
                     WHERE rf.user_id=?"""
            parameters: list[object] = [user_id]
            if folder_id_value not in (None, "all", ""):
                folder_id = int(folder_id_value)
                sql += " AND rf.folder_id=?"
                parameters.append(folder_id)
            sql += " ORDER BY rf.created_at DESC, r.name"
            favorites = [dict(row) for row in connection.execute(sql, parameters)]
        self.send_json({"favorites": favorites})

    def post_folder(self, body: dict[str, object]) -> None:
        user_id = str(body.get("user_id", DEFAULT_USER_ID))
        name = " ".join(str(body.get("name", "")).split())
        if not name or len(name) > 24:
            raise ValueError("資料夾名稱請填 1 至 24 個字")
        with connect_db() as connection:
            require_user(connection, user_id)
            cursor = connection.execute(
                "INSERT INTO favorite_folders (user_id, name) VALUES (?, ?)", (user_id, name)
            )
            folder_id = cursor.lastrowid
        self.send_json({"id": folder_id, "name": name}, 201)

    def delete_folder(self, folder_id_value: str, user_id: str) -> None:
        folder_id = int(folder_id_value)
        with connect_db() as connection:
            cursor = connection.execute(
                "DELETE FROM favorite_folders WHERE id=? AND user_id=?", (folder_id, user_id)
            )
            if cursor.rowcount == 0:
                raise ValueError("找不到這個收藏資料夾")
        self.send_json({"deleted": True})

    def post_favorite(self, body: dict[str, object]) -> None:
        user_id = str(body.get("user_id", DEFAULT_USER_ID))
        recipe_slug = str(body.get("recipe_slug", ""))
        folder_id = body.get("folder_id")
        with connect_db() as connection:
            require_user(connection, user_id)
            recipe = connection.execute("SELECT id FROM recipes WHERE slug=?", (recipe_slug,)).fetchone()
            if recipe is None:
                raise ValueError("找不到這道食譜")
            if folder_id is not None:
                owned = connection.execute(
                    "SELECT 1 FROM favorite_folders WHERE id=? AND user_id=?", (folder_id, user_id)
                ).fetchone()
                if owned is None:
                    raise ValueError("收藏資料夾不存在")
            connection.execute(
                """INSERT INTO recipe_favorites (user_id, recipe_id, folder_id) VALUES (?, ?, ?)
                   ON CONFLICT(user_id, recipe_id) DO UPDATE SET folder_id=excluded.folder_id""",
                (user_id, recipe["id"], folder_id),
            )
        self.send_json({"saved": True})

    def delete_favorite(self, recipe_slug: str, user_id: str) -> None:
        with connect_db() as connection:
            cursor = connection.execute(
                """DELETE FROM recipe_favorites WHERE user_id=?
                   AND recipe_id=(SELECT id FROM recipes WHERE slug=?)""",
                (user_id, recipe_slug),
            )
        self.send_json({"saved": False, "removed": cursor.rowcount > 0})


def main() -> None:
    if not DATABASE_PATH.exists():
        raise SystemExit(f"找不到資料庫：{DATABASE_PATH}；請先執行 python database/build_db.py")
    server = ThreadingHTTPServer(("127.0.0.1", 8000), RecipeHandler)
    print("菜就多煉已啟動：http://127.0.0.1:8000")
    print("按 Ctrl+C 結束")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n伺服器已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
