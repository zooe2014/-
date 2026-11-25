"""Build the local SQLite database from schema.sql and seed.sql."""

from pathlib import Path
import argparse
import sqlite3


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "菜就多煉.sqlite3"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
SEED_PATH = Path(__file__).with_name("seed.sql")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace the existing generated database file",
    )
    args = parser.parse_args()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        if not args.force:
            raise SystemExit(f"{DB_PATH} already exists; pass --force to rebuild it")
        DB_PATH.unlink()

    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.executescript(SEED_PATH.read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()

    print(f"Built {DB_PATH}")


if __name__ == "__main__":
    main()
