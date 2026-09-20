-- Life Quests · схема базы
--
-- Пять таблиц. Квесты всех типов лежат в одной таблице: мейн, сайд и босс
-- отличаются набором заполненных полей, а не отдельными сущностями.
--
-- Уровень героя нигде не хранится — он выводится из xp_total (app/xp.py).
-- Поэтому отмена главы возвращает ровно то состояние, что было до отметки.
--
-- Ни одной человеческой строки, кроме того, что ввёл сам человек: названия
-- характеристик, званий и сообщений журнала живут в словарях интерфейса
-- (static/js/i18n.js), а база хранит только коды. Иначе переключение языка
-- оставляло бы старые записи на прежнем языке.

PRAGMA foreign_keys = ON;

-- Профиль. Одна строка, id = 1. Таблица users появится вместе со вторым человеком.
CREATE TABLE profile (
  id         INTEGER PRIMARY KEY CHECK (id = 1),
  name       TEXT    NOT NULL CHECK (length(trim(name)) > 0),
  xp_total   INTEGER NOT NULL DEFAULT 0 CHECK (xp_total >= 0),
  streak     INTEGER NOT NULL DEFAULT 0 CHECK (streak >= 0),
  resting    INTEGER NOT NULL DEFAULT 0 CHECK (resting IN (0, 1)),
  skin       TEXT    NOT NULL DEFAULT 'win98',
  lang       TEXT    NOT NULL DEFAULT 'ru',
  intro_seen INTEGER NOT NULL DEFAULT 0 CHECK (intro_seen IN (0, 1)),
  notepad    TEXT    NOT NULL DEFAULT '',    -- блокнот: один свободный лист
  places     TEXT    NOT NULL DEFAULT '{}'   -- раскладка окон, JSON
);

-- Характеристики. Набор ключей задан в app/db.py, названия — в словарях.
CREATE TABLE stats (
  key   TEXT    PRIMARY KEY,
  value INTEGER NOT NULL DEFAULT 0 CHECK (value >= 0),
  sort  INTEGER NOT NULL DEFAULT 0
);

-- Квесты.
--   main — цель с главами; мейн без глав считается «в тумане» и не даёт опыта
--   side — мелкое дело или ежедневка, цена в xp_reward
--   boss — жёсткая цель: hp_max ударов, hit_xp за удар, xp_reward за победу,
--          главы у босса играют роль фаз
CREATE TABLE quests (
  id         INTEGER PRIMARY KEY,
  kind       TEXT    NOT NULL CHECK (kind IN ('main', 'side', 'boss')),
  title      TEXT    NOT NULL CHECK (length(trim(title)) > 0),
  why        TEXT    NOT NULL DEFAULT '',
  stat       TEXT    NOT NULL REFERENCES stats(key),
  due_date   TEXT             CHECK (due_date IS NULL OR
                                     due_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  xp_reward  INTEGER NOT NULL DEFAULT 0 CHECK (xp_reward >= 0),
  hp_max     INTEGER          CHECK (hp_max IS NULL OR hp_max > 0),
  hp_left    INTEGER          CHECK (hp_left IS NULL OR hp_left >= 0),
  hit_xp     INTEGER          CHECK (hit_xp IS NULL OR hit_xp > 0),
  -- Повторение сайд-квеста: раз в repeat_every единиц repeat_unit.
  -- NULL — разовое дело. period_start хранит начало текущего периода,
  -- по нему квест сам открывается заново (app/api.py: roll_periods).
  repeat_unit  TEXT         CHECK (repeat_unit IN ('day', 'week', 'month')),
  repeat_every INTEGER NOT NULL DEFAULT 1 CHECK (repeat_every > 0),
  period_start TEXT,
  streak     INTEGER NOT NULL DEFAULT 0 CHECK (streak >= 0),
  done       INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
  sort       INTEGER NOT NULL DEFAULT 0,
  created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
  done_at    TEXT,

  CHECK (hp_left IS NULL OR hp_max IS NULL OR hp_left <= hp_max),
  CHECK (repeat_unit IS NULL OR period_start IS NOT NULL),
  CHECK (kind <> 'boss' OR (hp_max IS NOT NULL AND hp_left IS NOT NULL AND hit_xp IS NOT NULL))
);
CREATE INDEX quests_kind ON quests (kind, done, sort, id);

-- Шаги мейн-квеста и фазы босса. Шаг, выполнимый за один заход.
-- parent_id даёт второй уровень: у шага могут быть подшаги. Шаг с подшагами
-- вручную не отмечается — он закрывается сам, когда закрыты все подшаги.
CREATE TABLE chapters (
  id        INTEGER PRIMARY KEY,
  quest_id  INTEGER NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
  parent_id INTEGER          REFERENCES chapters(id) ON DELETE CASCADE,
  name      TEXT    NOT NULL CHECK (length(trim(name)) > 0),
  xp        INTEGER NOT NULL CHECK (xp > 0),
  done      INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
  sort      INTEGER NOT NULL DEFAULT 0,
  done_at   TEXT,

  CHECK (parent_id IS NULL OR parent_id <> id)
);
CREATE INDEX chapters_quest ON chapters (quest_id, sort, id);
CREATE INDEX chapters_parent ON chapters (parent_id, sort, id);

-- Журнал системы. code — что случилось, params — подставляемые значения.
CREATE TABLE events (
  id     INTEGER PRIMARY KEY,
  at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  code   TEXT NOT NULL,
  params TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX events_recent ON events (id DESC);
