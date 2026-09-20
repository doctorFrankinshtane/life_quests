"""Демо-квесты — чтобы пустой экран не пугал на первом запуске.

Данные живут только здесь и заливаются явной командой `python run.py --demo`.
Обычный запуск создаёт пустую базу.

Названия квестов человек пишет сам, поэтому перевести их словарём нельзя —
для каждого языка лежит свой набор.
"""

from datetime import date, timedelta

# Профиль демо: седьмой уровень и шестидневная серия.
DEMO_XP_TOTAL = 1640
DEMO_STREAK = 6
DEMO_STATS = {"body": 22, "mind": 31, "craft": 40, "soul": 12, "bonds": 9}


class AlreadyFilled(Exception):
    """В базе уже есть квесты — второй раз не заливаем."""


def _due(days):
    return (date.today() + timedelta(days=days)).isoformat()


HERO = {"ru": "Максим", "en": "Alex"}


def _quests(lang):
    """Демо-набор: мейн с главами, мейн в тумане, босс и пять сайдов."""
    if lang == "en":
        return [
            {
                "kind": "main",
                "title": "Get back in shape by summer",
                "why": "Stop gasping for air on the fourth floor.",
                "stat": "body",
                "due_date": _due(74),
                "chapters": [
                    ("Buy a gym pass and actually walk in", 15, 1),
                    ("Four sessions in a row, no misses", 40, 1),
                    ("Eight pull-ups", 60, 0),
                    ("Run 5 km without stopping", 60, 0),
                    ("Hold the weight for three weeks", 65, 0),
                ],
            },
            {
                "kind": "main",
                "title": "Ship my own product",
                "why": "Stop building other people's ideas and test mine.",
                "stat": "craft",
                "chapters": [],          # мейн без глав — показывает «туман»
            },
            {
                "kind": "boss",
                "title": "English up to C1",
                "stat": "mind",
                "due_date": _due(162),
                "hp_max": 30,
                "hp_left": 16,
                "hit_xp": 12,
                "xp_reward": 180,
                "chapters": [
                    ("Phase 1 · 500 words", 40, 1),
                    ("Phase 2 · 16 speaking sessions", 80, 0),
                    ("Phase 3 · pass the exam", 120, 0),
                ],
            },
            {"kind": "side", "title": "10,000 steps", "stat": "body", "xp_reward": 8, "repeat": "day", "streak": 6},
            {"kind": "side", "title": "20 pages of a book", "stat": "mind", "xp_reward": 10, "repeat": "day", "streak": 3, "done": 1},
            {"kind": "side", "title": "Call my parents", "stat": "bonds", "xp_reward": 12},
            {"kind": "side", "title": "Clear the desk", "stat": "craft", "xp_reward": 6},
            {"kind": "side", "title": "Lights out by 23:00", "stat": "soul", "xp_reward": 10, "repeat": "day", "streak": 1},
        ]

    return [
        {
            "kind": "main",
            "title": "Вернуть форму к лету",
            "why": "Перестать задыхаться на четвёртом этаже.",
            "stat": "body",
            "due_date": _due(74),
            "chapters": [
                ("Купить абонемент и дойти до зала", 15, 1),
                ("4 тренировки подряд без пропуска", 40, 1),
                ("Подтянуться 8 раз", 60, 0),
                ("Пробежать 5 км без остановки", 60, 0),
                ("Держать вес 3 недели подряд", 65, 0),
            ],
        },
        {
            "kind": "main",
            "title": "Выпустить свой продукт",
            "why": "Перестать делать чужие идеи и проверить свою.",
            "stat": "craft",
            "chapters": [],
        },
        {
            "kind": "boss",
            "title": "Английский до C1",
            "stat": "mind",
            "due_date": _due(162),
            "hp_max": 30,
            "hp_left": 16,
            "hit_xp": 12,
            "xp_reward": 180,
            "chapters": [
                ("Фаза 1 · 500 слов", 40, 1),
                ("Фаза 2 · 16 разговорных сессий", 80, 0),
                ("Фаза 3 · сдать экзамен", 120, 0),
            ],
        },
        {"kind": "side", "title": "10 000 шагов", "stat": "body", "xp_reward": 8, "repeat": "day", "streak": 6},
        {"kind": "side", "title": "20 страниц книги", "stat": "mind", "xp_reward": 10, "repeat": "day", "streak": 3, "done": 1},
        {"kind": "side", "title": "Позвонить родителям", "stat": "bonds", "xp_reward": 12},
        {"kind": "side", "title": "Разобрать рабочий стол", "stat": "craft", "xp_reward": 6},
        {"kind": "side", "title": "Лечь до 23:00", "stat": "soul", "xp_reward": 10, "repeat": "day", "streak": 1},
    ]


def fill(con, lang="ru"):
    """Заливает демо-набор на выбранном языке. Возвращает число квестов."""
    if con.execute("SELECT count(*) AS n FROM quests").fetchone()["n"]:
        raise AlreadyFilled("в базе уже есть квесты")

    quests = _quests(lang)

    with con:
        con.execute(
            """UPDATE profile
                  SET name = ?, lang = ?, xp_total = ?, streak = ?, intro_seen = 1
                WHERE id = 1""",
            (HERO.get(lang, HERO["ru"]), lang, DEMO_XP_TOTAL, DEMO_STREAK),
        )
        con.executemany(
            "UPDATE stats SET value = ? WHERE key = ?",
            [(value, key) for key, value in DEMO_STATS.items()],
        )

        for sort, quest in enumerate(quests, 1):
            quest_id = con.execute(
                """INSERT INTO quests
                       (kind, title, why, stat, due_date, xp_reward,
                        hp_max, hp_left, hit_xp, repeat_unit, period_start,
                        streak, done, sort)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    quest["kind"],
                    quest["title"],
                    quest.get("why", ""),
                    quest["stat"],
                    quest.get("due_date"),
                    quest.get("xp_reward", 0),
                    quest.get("hp_max"),
                    quest.get("hp_left"),
                    quest.get("hit_xp"),
                    quest.get("repeat"),
                    date.today().isoformat() if quest.get("repeat") else None,
                    quest.get("streak", 0),
                    quest.get("done", 0),
                    sort,
                ),
            ).lastrowid

            con.executemany(
                "INSERT INTO chapters (quest_id, name, xp, done, sort) VALUES (?, ?, ?, ?, ?)",
                [
                    (quest_id, name, xp, done, index)
                    for index, (name, xp, done) in enumerate(quest.get("chapters", []), 1)
                ],
            )

        con.execute("INSERT INTO events (code) VALUES ('demo_filled')")

    return len(quests)
