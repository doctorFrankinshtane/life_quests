"""Соединение с SQLite и создание пустой базы."""

import sqlite3

# Характеристики героя. Набор фиксирован: он задаёт язык, на котором
# описываются все квесты, и менять его на ходу нельзя без миграции.
# Названия живут в словарях интерфейса — база хранит только ключи.
STAT_KEYS = ("body", "mind", "craft", "soul", "bonds")

# Облики интерфейса. Проверяются здесь, а не CHECK-ом в схеме, чтобы новый
# облик не требовал миграции базы.
SKINS = ("win98", "platinum")

# Языки интерфейса. Словари лежат в static/js/i18n.js.
LANGS = ("ru", "en")


def connect(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def create(con, schema_sql, hero_name):
    """Разворачивает схему и заводит профиль с нулевым опытом."""
    with con:
        con.executescript(schema_sql)
        con.execute("INSERT INTO profile (id, name) VALUES (1, ?)", (hero_name,))
        con.executemany(
            "INSERT INTO stats (key, value, sort) VALUES (?, 0, ?)",
            [(key, sort) for sort, key in enumerate(STAT_KEYS, 1)],
        )
        con.execute("INSERT INTO events (code) VALUES ('base_created')")
    return con


def open_or_create(config):
    """Открывает базу, создавая её при первом запуске."""
    fresh = not config.db_path.exists()
    con = connect(config.db_path)
    if fresh:
        config.db_path.parent.mkdir(parents=True, exist_ok=True)
        create(con, config.schema_path.read_text(encoding="utf-8"), config.hero_name)
        con.execute("PRAGMA journal_mode = WAL")
    return con, fresh


def memory(schema_sql, hero_name="Hero"):
    """База в памяти — для тестов."""
    return create(connect(":memory:"), schema_sql, hero_name)
