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


# Колонки, появившиеся после первых выпусков. Каждая добавляется отдельным
# ALTER-ом, чтобы старая база не требовала переноса вручную.
LATER_COLUMNS = (
    ("profile", "notepad", "TEXT NOT NULL DEFAULT ''"),
    ("chapters", "parent_id", "INTEGER REFERENCES chapters(id) ON DELETE CASCADE"),
    ("quests", "repeat_unit", "TEXT"),
    ("quests", "repeat_every", "INTEGER NOT NULL DEFAULT 1"),
    ("quests", "period_start", "TEXT"),
)

# Колонки, которые заменены и больше не нужны.
DROPPED_COLUMNS = (("quests", "daily"),)


def columns_of(con, table):
    return {row["name"] for row in con.execute(f"PRAGMA table_info({table})")}


def migrate(con):
    """Доводит старую базу до текущей схемы. Возвращает список изменений."""
    changes = []
    with con:
        for table, column, definition in LATER_COLUMNS:
            if column in columns_of(con, table):
                continue
            con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            changes.append(f"{table}.{column}")

        # Бывшая галочка «ежедневка» становится повторением раз в день.
        if "daily" in columns_of(con, "quests"):
            con.execute(
                """UPDATE quests
                      SET repeat_unit = 'day',
                          repeat_every = 1,
                          period_start = coalesce(period_start, date(created_at))
                    WHERE daily = 1 AND repeat_unit IS NULL"""
            )

        for table, column in DROPPED_COLUMNS:
            if column in columns_of(con, table):
                con.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
                changes.append(f"{table}.{column} (убрана)")

    return changes


def open_or_create(config):
    """Открывает базу, создавая её при первом запуске."""
    fresh = not config.db_path.exists()
    con = connect(config.db_path)
    if fresh:
        config.db_path.parent.mkdir(parents=True, exist_ok=True)
        create(con, config.schema_path.read_text(encoding="utf-8"), config.hero_name)
        con.execute("PRAGMA journal_mode = WAL")
    else:
        for column in migrate(con):
            print(f"База обновлена: добавлена колонка {column}")
    return con, fresh


def memory(schema_sql, hero_name="Hero"):
    """База в памяти — для тестов."""
    return create(connect(":memory:"), schema_sql, hero_name)
