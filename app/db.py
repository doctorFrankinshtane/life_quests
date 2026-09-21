"""Соединение с SQLite и создание пустой базы."""

import sqlite3

# Характеристики героя. Набор фиксирован: он задаёт язык, на котором
# описываются все квесты, и менять его на ходу нельзя без миграции.
# Названия живут в словарях интерфейса — база хранит только ключи.
STAT_KEYS = ("body", "mind", "craft", "soul", "bonds")

# Облики интерфейса. Проверяются здесь, а не CHECK-ом в схеме, чтобы новый
# облик не требовал миграции базы.
SKINS = ("win98", "platinum", "plum")

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

# Таблица архива: снимок квеста на момент ухода с доски. Дублируется строкой
# из schema.sql, чтобы старая база догоняла схему той же командой migrate.
ARCHIVE_SQL = """CREATE TABLE archive (
  id           INTEGER PRIMARY KEY,
  kind         TEXT    NOT NULL CHECK (kind IN ('main', 'side', 'boss')),
  title        TEXT    NOT NULL CHECK (length(trim(title)) > 0),
  why          TEXT    NOT NULL DEFAULT '',
  stat         TEXT    NOT NULL,
  due_date     TEXT,
  xp           INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0),
  hp_max       INTEGER CHECK (hp_max IS NULL OR hp_max > 0),
  hp_left      INTEGER CHECK (hp_left IS NULL OR hp_left >= 0),
  hit_xp       INTEGER CHECK (hit_xp IS NULL OR hit_xp > 0),
  repeat_unit  TEXT    CHECK (repeat_unit IS NULL OR repeat_unit IN ('day', 'week', 'month')),
  repeat_every INTEGER NOT NULL DEFAULT 1,
  period_start TEXT,
  streak       INTEGER NOT NULL DEFAULT 0,
  done         INTEGER NOT NULL DEFAULT 0,
  closed_at    TEXT,
  reason       TEXT    NOT NULL CHECK (reason IN ('closed', 'deleted')),
  chapters     TEXT    NOT NULL DEFAULT '[]',
  archived_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
)"""


def columns_of(con, table):
    return {row["name"] for row in con.execute(f"PRAGMA table_info({table})")}


def tables_of(con):
    return {
        row["name"]
        for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def migrate(con):
    """Доводит старую базу до текущей схемы. Возвращает список изменений."""
    changes = []
    with con:
        if "archive" not in tables_of(con):
            con.execute(ARCHIVE_SQL)
            changes.append("archive (таблица)")

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
