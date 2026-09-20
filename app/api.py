"""Действия над базой и сборка состояния для интерфейса.

Здесь живёт вся игровая логика. Браузер ничего не вычисляет: он отправляет
намерение («отметить главу»), получает новое состояние целиком и рисует его.

Сообщения сервер отдаёт кодами, а не готовыми фразами: `{"code": "level_up",
"params": {...}}`. Тексты лежат в словарях интерфейса, поэтому смена языка
переписывает и уведомления, и весь журнал задним числом.
"""

import json
import re
from datetime import date

from . import xp as xp_rules
from .db import LANGS, SKINS, STAT_KEYS

# --- границы ввода -------------------------------------------------------
MAX_TITLE = 120
MAX_NAME = 40
MAX_WHY = 300
MAX_CHAPTER_XP = 500
MAX_HP = 999
MAX_EVENTS = 40
MAX_NOTEPAD = 20_000

# --- правила игры --------------------------------------------------------
# Больше трёх мейн-квестов разом — это уже список дел, а не игра.
MAX_ACTIVE_MAINS = 3
# Глубина шагов: шаг и подшаг. Дальше дробить — значит, мейн-квест выбран
# слишком крупно, и его пора разбивать на два.
MAX_DEPTH = 2
# Бонус за полностью закрытый мейн — доля от суммы его глав.
CLOSE_BONUS_SHARE = 0.25
# Значения по умолчанию, если поле не пришло из формы.
DEFAULT_SIDE_XP = 10
DEFAULT_CHAPTER_XP = 20
DEFAULT_HIT_XP = 10


class Bad(Exception):
    """Ошибка, которую не стыдно показать человеку."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def note(code, **params):
    """Уведомление для всплывающего окна."""
    return {"code": code, "params": params}


# --------------------------------------------------------------------------
# Разбор и проверка ввода
# --------------------------------------------------------------------------

def want_text(body, key, *, limit, required=True, default=""):
    value = body.get(key, default)
    if not isinstance(value, str):
        raise Bad(f"Поле «{key}» должно быть строкой")
    value = value.strip()
    if required and not value:
        raise Bad(f"Поле «{key}» не заполнено")
    if len(value) > limit:
        raise Bad(f"Поле «{key}» длиннее {limit} символов")
    return value


def want_int(body, key, *, low, high, default=None):
    value = body.get(key, default)
    if value is None:
        raise Bad(f"Поле «{key}» не заполнено")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value):
        raise Bad(f"Поле «{key}» должно быть целым числом")
    value = int(value)
    if not low <= value <= high:
        raise Bad(f"Поле «{key}» должно быть от {low} до {high}")
    return value


def want_choice(body, key, allowed, default=None):
    value = body.get(key, default)
    if value not in allowed:
        raise Bad(f"Поле «{key}» должно быть одним из: {', '.join(allowed)}")
    return value


def want_date(body, key):
    """Срок в виде ГГГГ-ММ-ДД либо пусто."""
    value = body.get(key) or None
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise Bad("Срок должен быть в виде ГГГГ-ММ-ДД")
    try:
        date.fromisoformat(value)
    except ValueError as err:
        raise Bad("Такой даты не существует") from err
    return value


# --------------------------------------------------------------------------
# Журнал и опыт
# --------------------------------------------------------------------------

def log(con, code, **params):
    con.execute(
        "INSERT INTO events (code, params) VALUES (?, ?)",
        (code, json.dumps(params, ensure_ascii=False)),
    )


def grant_xp(con, amount, stat):
    """Начисляет опыт и очки характеристике. Возвращает уведомления о новых уровнях."""
    if amount <= 0:
        return []

    before = con.execute("SELECT xp_total FROM profile WHERE id = 1").fetchone()["xp_total"]
    after = before + amount
    con.execute("UPDATE profile SET xp_total = ? WHERE id = 1", (after,))
    con.execute(
        "UPDATE stats SET value = value + ? WHERE key = ?",
        (xp_rules.stat_points(amount), stat),
    )

    was = xp_rules.level_for(before)[0]
    now = xp_rules.level_for(after)[0]

    flash = []
    for level in range(was + 1, now + 1):
        index = xp_rules.title_index(level)
        flash.append(note("level_up", level=level, titleIndex=index))
        log(con, "level_up", level=level, titleIndex=index)
    return flash


def take_xp(con, amount, stat):
    """Полная отмена начисления: опыт и очки характеристики возвращаются назад."""
    if amount <= 0:
        return
    con.execute("UPDATE profile SET xp_total = max(0, xp_total - ?) WHERE id = 1", (amount,))
    con.execute(
        "UPDATE stats SET value = max(0, value - ?) WHERE key = ?",
        (xp_rules.stat_points(amount), stat),
    )


# --------------------------------------------------------------------------
# Чтение состояния
# --------------------------------------------------------------------------

def days_left(due_date, today=None):
    if not due_date:
        return None
    return (date.fromisoformat(due_date) - (today or date.today())).days


def fetch_chapter(con, chapter_id):
    row = con.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
    if row is None:
        raise Bad("Шага с таким номером нет", 404)
    return row


def children_of(con, chapter_id):
    return con.execute(
        "SELECT * FROM chapters WHERE parent_id = ? ORDER BY sort, id", (chapter_id,)
    ).fetchall()


def depth_of(con, chapter_row):
    """Уровень шага: 1 — обычный шаг, 2 — подшаг."""
    depth = 1
    parent_id = chapter_row["parent_id"]
    while parent_id is not None:
        depth += 1
        parent_id = con.execute(
            "SELECT parent_id FROM chapters WHERE id = ?", (parent_id,)
        ).fetchone()["parent_id"]
    return depth


def close_bonus(con, quest_id):
    """Бонус за полностью закрытый мейн — доля от суммы всех его шагов."""
    total = con.execute(
        "SELECT coalesce(sum(xp), 0) AS n FROM chapters WHERE quest_id = ?", (quest_id,)
    ).fetchone()["n"]
    return round(total * CLOSE_BONUS_SHARE)


def reopen_quest(con, quest):
    """Возвращает квест на доску и снимает бонус, выданный за его закрытие."""
    if not quest["done"]:
        return
    take_xp(con, close_bonus(con, quest["id"]), quest["stat"])
    con.execute("UPDATE quests SET done = 0, done_at = NULL WHERE id = ?", (quest["id"],))


def close_upwards(con, chapter_row, quest):
    """Закрывает родителя, если все его подшаги готовы. Идёт вверх до квеста."""
    flash = []
    parent_id = chapter_row["parent_id"]

    while parent_id is not None:
        parent = fetch_chapter(con, parent_id)
        left = con.execute(
            "SELECT count(*) AS n FROM chapters WHERE parent_id = ? AND done = 0", (parent_id,)
        ).fetchone()["n"]
        if left or parent["done"]:
            return flash

        con.execute(
            "UPDATE chapters SET done = 1, done_at = datetime('now', 'localtime') WHERE id = ?",
            (parent_id,),
        )
        flash += grant_xp(con, parent["xp"], quest["stat"])
        log(con, "step_closed", name=parent["name"], xp=parent["xp"])
        parent_id = parent["parent_id"]

    return flash


def open_upwards(con, chapter_row, quest):
    """Снимает отметку с родителей: подшаг открыт — значит, шаг не сделан."""
    parent_id = chapter_row["parent_id"]

    while parent_id is not None:
        parent = fetch_chapter(con, parent_id)
        if not parent["done"]:
            return
        con.execute("UPDATE chapters SET done = 0, done_at = NULL WHERE id = ?", (parent_id,))
        take_xp(con, parent["xp"], quest["stat"])
        parent_id = parent["parent_id"]


def fetch_quest(con, quest_id, kind=None):
    sql = "SELECT * FROM quests WHERE id = ?"
    args = [quest_id]
    if kind:
        sql += " AND kind = ?"
        args.append(kind)
    quest = con.execute(sql, args).fetchone()
    if quest is None:
        raise Bad("Квеста с таким номером нет", 404)
    return quest


def read_state(con, today=None):
    profile = con.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    stats = con.execute("SELECT key, value FROM stats ORDER BY sort").fetchall()

    # Шаги собираются в дерево: верхний уровень квеста и подшаги внутри.
    chapters, nodes, weight = {}, {}, {}
    rows = con.execute("SELECT * FROM chapters ORDER BY sort, id").fetchall()

    for row in rows:
        nodes[row["id"]] = {
            "id": row["id"],
            "name": row["name"],
            "xp": row["xp"],
            "done": bool(row["done"]),
            "children": [],
        }
        weight[row["quest_id"]] = weight.get(row["quest_id"], 0) + row["xp"]

    for row in rows:
        node = nodes[row["id"]]
        parent = nodes.get(row["parent_id"])
        if parent is None:
            chapters.setdefault(row["quest_id"], []).append(node)
        else:
            parent["children"].append(node)

    mains, sides, bosses = [], [], []
    for quest in con.execute("SELECT * FROM quests WHERE done = 0 ORDER BY sort, id"):
        own = chapters.get(quest["id"], [])
        base = {
            "id": quest["id"],
            "title": quest["title"],
            "stat": quest["stat"],
            "dueDate": quest["due_date"],
            "daysLeft": days_left(quest["due_date"], today),
        }

        if quest["kind"] == "main":
            mains.append({
                **base,
                "why": quest["why"],
                "fog": not own,                      # мейн без глав — в тумане
                "chapters": own,
                "xpTotal": weight.get(quest["id"], 0),
                "doneCount": sum(1 for chapter in own if chapter["done"]),
            })
        elif quest["kind"] == "side":
            sides.append({
                **base,
                "xp": quest["xp_reward"],
                "daily": bool(quest["daily"]),
                "streak": quest["streak"],
                "done": False,
            })
        else:
            bosses.append({
                **base,
                "hpMax": quest["hp_max"],
                "hpLeft": quest["hp_left"],
                "hitXp": quest["hit_xp"],
                "xpReward": quest["xp_reward"],
                "phases": own,
            })

    # Сайд-квесты показываются и закрытыми — галочку можно снять в тот же день.
    for quest in con.execute(
        "SELECT * FROM quests WHERE kind = 'side' AND done = 1 ORDER BY sort, id"
    ):
        sides.append({
            "id": quest["id"],
            "title": quest["title"],
            "stat": quest["stat"],
            "dueDate": quest["due_date"],
            "daysLeft": days_left(quest["due_date"], today),
            "xp": quest["xp_reward"],
            "daily": bool(quest["daily"]),
            "streak": quest["streak"],
            "done": True,
        })

    events = con.execute(
        "SELECT at, code, params FROM events ORDER BY id DESC LIMIT ?", (MAX_EVENTS,)
    ).fetchall()

    return {
        "profile": {
            "name": profile["name"],
            **xp_rules.progress(profile["xp_total"]),
            "streak": profile["streak"],
            "resting": bool(profile["resting"]),
            "skin": profile["skin"],
            "lang": profile["lang"],
            "introSeen": bool(profile["intro_seen"]),
            "notepad": profile["notepad"],
            "places": json.loads(profile["places"]),
        },
        "stats": [dict(row) for row in stats],
        "mains": mains,
        "bosses": bosses,
        "sides": sides,
        "events": [
            {"at": row["at"][11:], "code": row["code"], "params": json.loads(row["params"])}
            for row in reversed(events)
        ],
        "limits": {
            "maxMains": MAX_ACTIVE_MAINS,
            "skins": list(SKINS),
            "langs": list(LANGS),
            "stats": list(STAT_KEYS),
        },
    }


# --------------------------------------------------------------------------
# Действия
# --------------------------------------------------------------------------

def next_sort(con, kind):
    return con.execute(
        "SELECT coalesce(max(sort), 0) + 1 AS n FROM quests WHERE kind = ?", (kind,)
    ).fetchone()["n"]


def create_quest(con, _target, body):
    kind = want_choice(body, "kind", ("main", "side", "boss"))
    title = want_text(body, "title", limit=MAX_TITLE)
    stat = want_choice(body, "stat", STAT_KEYS)
    due = want_date(body, "dueDate")

    if kind == "main":
        active = con.execute(
            "SELECT count(*) AS n FROM quests WHERE kind = 'main' AND done = 0"
        ).fetchone()["n"]
        if active >= MAX_ACTIVE_MAINS:
            raise Bad(
                f"Активных мейн-квестов уже {MAX_ACTIVE_MAINS}. "
                "Закройте один, прежде чем брать новый.",
                409,
            )
        why = want_text(body, "why", limit=MAX_WHY, required=False)
        con.execute(
            """INSERT INTO quests (kind, title, why, stat, due_date, sort)
               VALUES ('main', ?, ?, ?, ?, ?)""",
            (title, why, stat, due, next_sort(con, "main")),
        )
        log(con, "main_created", title=title)
        return [note("main_created", title=title)]

    if kind == "side":
        reward = want_int(body, "xp", low=1, high=MAX_CHAPTER_XP, default=DEFAULT_SIDE_XP)
        daily = 1 if body.get("daily") else 0
        con.execute(
            """INSERT INTO quests (kind, title, stat, due_date, xp_reward, daily, sort)
               VALUES ('side', ?, ?, ?, ?, ?, ?)""",
            (title, stat, due, reward, daily, next_sort(con, "side")),
        )
        log(con, "side_created", title=title, xp=reward)
        return [note("side_created", title=title, xp=reward)]

    hp = want_int(body, "hp", low=1, high=MAX_HP)
    hit_xp = want_int(body, "hitXp", low=1, high=MAX_CHAPTER_XP, default=DEFAULT_HIT_XP)
    # Приз за победу по умолчанию равен всей сумме ударов: финал весит столько же,
    # сколько дорога к нему.
    reward = want_int(body, "xp", low=0, high=MAX_HP * MAX_CHAPTER_XP, default=hp * hit_xp)
    con.execute(
        """INSERT INTO quests (kind, title, stat, due_date, xp_reward, hp_max, hp_left, hit_xp, sort)
           VALUES ('boss', ?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, stat, due, reward, hp, hp, hit_xp, next_sort(con, "boss")),
    )
    log(con, "boss_created", title=title, hp=hp)
    return [note("boss_created", title=title, hp=hp)]


def add_chapter(con, quest_id, body):
    quest = fetch_quest(con, quest_id)
    if quest["kind"] == "side":
        raise Bad("У сайд-квеста не бывает шагов", 409)

    # Новый шаг у закрытого квеста означает, что работа не закончена:
    # квест возвращается на доску, бонус за закрытие снимается.
    if quest["done"]:
        reopen_quest(con, quest)
        quest = fetch_quest(con, quest_id)

    name = want_text(body, "name", limit=MAX_TITLE)
    amount = want_int(body, "xp", low=1, high=MAX_CHAPTER_XP, default=DEFAULT_CHAPTER_XP)

    parent = None
    parent_id = body.get("parentId")
    if parent_id is not None:
        parent = fetch_chapter(con, want_int(body, "parentId", low=1, high=2**31))
        if parent["quest_id"] != quest_id:
            raise Bad("Этот шаг принадлежит другому квесту", 409)
        if depth_of(con, parent) >= MAX_DEPTH:
            raise Bad(
                "Глубже подшага дробить нельзя. Если шагов слишком много, "
                "квест взят слишком крупно — разбейте его на два.",
                409,
            )
        parent_id = parent["id"]

    # Подшаг у закрытого шага снова его открывает: работа опять не закончена.
    # Откат идёт до вставки, чтобы бонус за закрытие снялся ровно тот, что выдан.
    if parent is not None and parent["done"]:
        reopen_quest(con, fetch_quest(con, quest_id))
        con.execute("UPDATE chapters SET done = 0, done_at = NULL WHERE id = ?", (parent["id"],))
        take_xp(con, parent["xp"], quest["stat"])
        open_upwards(con, parent, quest)

    sort = con.execute(
        """SELECT coalesce(max(sort), 0) + 1 AS n FROM chapters
            WHERE quest_id = ? AND parent_id IS ?""",
        (quest_id, parent_id),
    ).fetchone()["n"]

    con.execute(
        "INSERT INTO chapters (quest_id, parent_id, name, xp, sort) VALUES (?, ?, ?, ?, ?)",
        (quest_id, parent_id, name, amount, sort),
    )

    if parent is None:
        log(con, "phase_added" if quest["kind"] == "boss" else "chapter_added",
            title=quest["title"], name=name, xp=amount)
        if sort == 1 and quest["kind"] == "main":
            return [note("fog_lifted", title=quest["title"])]
        return []

    log(con, "substep_added", parent=parent["name"], name=name, xp=amount)
    return []


def toggle_chapter(con, chapter_id, _body):
    chapter = fetch_chapter(con, chapter_id)
    quest = fetch_quest(con, chapter["quest_id"])

    # Шаг с подшагами закрывается сам — иначе можно получить опыт за работу,
    # которая внутри него ещё не сделана.
    if children_of(con, chapter_id):
        raise Bad(
            "У этого шага есть подшаги. Он закроется сам, когда все они будут отмечены.",
            409,
        )

    if chapter["done"]:
        reopen_quest(con, quest)          # бонус за закрытие тоже возвращается
        con.execute("UPDATE chapters SET done = 0, done_at = NULL WHERE id = ?", (chapter_id,))
        take_xp(con, chapter["xp"], quest["stat"])
        open_upwards(con, chapter, quest)
        log(con, "chapter_undone", name=chapter["name"], xp=chapter["xp"])
        return []

    con.execute(
        "UPDATE chapters SET done = 1, done_at = datetime('now', 'localtime') WHERE id = ?",
        (chapter_id,),
    )
    flash = grant_xp(con, chapter["xp"], quest["stat"])
    flash += close_upwards(con, chapter, quest)

    left = steps_left(con, quest["id"])
    if left:
        log(con, "chapter_done", name=chapter["name"], xp=chapter["xp"], left=left)
        return flash

    if quest["kind"] != "main":
        # У босса решает здоровье, а не фазы.
        log(con, "phases_done", title=quest["title"], name=chapter["name"], xp=chapter["xp"])
        return flash

    return flash + settle_main(con, quest)


def steps_left(con, quest_id):
    return con.execute(
        "SELECT count(*) AS n FROM chapters WHERE quest_id = ? AND done = 0", (quest_id,)
    ).fetchone()["n"]


def settle_main(con, quest):
    """Закрывает мейн-квест, если все его шаги отмечены."""
    total = con.execute(
        "SELECT count(*) AS n FROM chapters WHERE quest_id = ?", (quest["id"],)
    ).fetchone()["n"]
    if quest["done"] or not total or steps_left(con, quest["id"]):
        return []

    bonus = close_bonus(con, quest["id"])
    flash = grant_xp(con, bonus, quest["stat"])
    con.execute(
        "UPDATE quests SET done = 1, done_at = datetime('now', 'localtime') WHERE id = ?",
        (quest["id"],),
    )
    log(con, "main_closed", title=quest["title"], bonus=bonus)
    flash.append(note("main_closed", title=quest["title"], bonus=bonus))
    return flash


def delete_chapter(con, chapter_id, _body):
    """Убирает шаг вместе с его подшагами. Заработанный опыт остаётся."""
    chapter = fetch_chapter(con, chapter_id)
    quest = fetch_quest(con, chapter["quest_id"])

    con.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))
    log(con, "step_deleted", name=chapter["name"])

    # Родитель мог доукомплектоваться: лишний подшаг больше не держит его открытым.
    flash = close_upwards(con, chapter, quest)
    if quest["kind"] == "main":
        flash += settle_main(con, fetch_quest(con, quest["id"]))
    return flash


def toggle_side(con, quest_id, _body):
    quest = fetch_quest(con, quest_id, "side")
    done = 0 if quest["done"] else 1

    streak = quest["streak"]
    if quest["daily"]:
        streak = streak + 1 if done else max(0, streak - 1)

    con.execute(
        """UPDATE quests
              SET done = ?, streak = ?,
                  done_at = CASE WHEN ? = 1 THEN datetime('now', 'localtime') END
            WHERE id = ?""",
        (done, streak, done, quest_id),
    )

    if done:
        log(con, "side_done", title=quest["title"], xp=quest["xp_reward"])
        return grant_xp(con, quest["xp_reward"], quest["stat"])

    take_xp(con, quest["xp_reward"], quest["stat"])
    log(con, "side_undone", title=quest["title"], xp=quest["xp_reward"])
    return []


def hit_boss(con, quest_id, _body):
    quest = fetch_quest(con, quest_id, "boss")
    if quest["hp_left"] <= 0:
        raise Bad("Босс уже повержен", 409)

    hp = quest["hp_left"] - 1
    con.execute("UPDATE quests SET hp_left = ? WHERE id = ?", (hp, quest_id))
    flash = grant_xp(con, quest["hit_xp"], quest["stat"])

    if hp:
        log(con, "boss_hit", title=quest["title"], left=hp, xp=quest["hit_xp"])
        return flash

    flash += grant_xp(con, quest["xp_reward"], quest["stat"])
    con.execute(
        "UPDATE quests SET done = 1, done_at = datetime('now', 'localtime') WHERE id = ?",
        (quest_id,),
    )
    con.execute("UPDATE chapters SET done = 1 WHERE quest_id = ?", (quest_id,))
    log(con, "boss_defeated", title=quest["title"], xp=quest["xp_reward"])
    flash.append(note("boss_defeated", title=quest["title"], xp=quest["xp_reward"]))
    return flash


def delete_quest(con, quest_id, _body):
    quest = fetch_quest(con, quest_id)
    con.execute("DELETE FROM quests WHERE id = ?", (quest_id,))   # главы уйдут каскадом
    log(con, "quest_deleted", title=quest["title"])
    return [note("quest_deleted", title=quest["title"])]


def update_profile(con, _target, body):
    flash = []

    if "skin" in body:
        skin = want_choice(body, "skin", SKINS)
        con.execute("UPDATE profile SET skin = ? WHERE id = 1", (skin,))
        log(con, "skin_changed", skin=skin)

    if "lang" in body:
        lang = want_choice(body, "lang", LANGS)
        con.execute("UPDATE profile SET lang = ? WHERE id = 1", (lang,))
        log(con, "lang_changed", lang=lang)

    if "name" in body:
        name = want_text(body, "name", limit=MAX_NAME)
        con.execute("UPDATE profile SET name = ? WHERE id = 1", (name,))
        log(con, "name_changed", name=name)

    if "introSeen" in body:
        con.execute(
            "UPDATE profile SET intro_seen = ? WHERE id = 1",
            (1 if body["introSeen"] else 0,),
        )

    if "resting" in body:
        resting = 1 if body["resting"] else 0
        con.execute("UPDATE profile SET resting = ? WHERE id = 1", (resting,))
        streak = con.execute("SELECT streak FROM profile WHERE id = 1").fetchone()["streak"]
        code = "rest_on" if resting else "rest_off"
        log(con, code, streak=streak)
        flash.append(note(code, streak=streak))

    # Блокнот пишется на каждой паузе в наборе, поэтому в журнал не идёт:
    # иначе он забьёт собой всё остальное.
    if "notepad" in body:
        text = want_text(body, "notepad", limit=MAX_NOTEPAD, required=False)
        con.execute("UPDATE profile SET notepad = ? WHERE id = 1", (text,))

    if "places" in body:
        places = body["places"]
        if not isinstance(places, dict):
            raise Bad("Раскладка окон должна быть объектом")
        con.execute(
            "UPDATE profile SET places = ? WHERE id = 1",
            (json.dumps(places, ensure_ascii=False),),
        )

    return flash


# --------------------------------------------------------------------------
# Маршруты
# --------------------------------------------------------------------------

ROUTES = (
    (r"^/api/quests$", create_quest),
    (r"^/api/quests/(\d+)/chapters$", add_chapter),
    (r"^/api/quests/(\d+)/hit$", hit_boss),
    (r"^/api/quests/(\d+)/toggle$", toggle_side),
    (r"^/api/quests/(\d+)/delete$", delete_quest),
    (r"^/api/chapters/(\d+)/toggle$", toggle_chapter),
    (r"^/api/chapters/(\d+)/delete$", delete_chapter),
    (r"^/api/profile$", update_profile),
)

COMPILED = tuple((re.compile(pattern), action) for pattern, action in ROUTES)


def dispatch(con, path, body):
    """Находит действие по адресу и выполняет его. Возвращает список уведомлений."""
    for pattern, action in COMPILED:
        match = pattern.match(path)
        if match:
            target = int(match.group(1)) if match.groups() else None
            return action(con, target, body)
    raise Bad("Нет такого адреса", 404)
