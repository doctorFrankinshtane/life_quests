"""Действия над базой: создание, отметки, босс, лимиты, проверка ввода."""

import json
import unittest
from datetime import date, timedelta

from app import api, db, seed, xp
from app.config import Config

SCHEMA = Config.load().schema_path.read_text(encoding="utf-8")


class Base(unittest.TestCase):
    """Пустая база в памяти на каждый тест."""

    demo = False

    def setUp(self):
        self.con = db.memory(SCHEMA)
        if self.demo:
            seed.fill(self.con)

    def tearDown(self):
        self.con.close()

    # --- удобства ---------------------------------------------------------
    def state(self):
        return api.read_state(self.con)

    def xp_total(self):
        return self.con.execute("SELECT xp_total FROM profile WHERE id = 1").fetchone()["xp_total"]

    def stat(self, key):
        return self.con.execute("SELECT value FROM stats WHERE key = ?", (key,)).fetchone()["value"]

    def make_main(self, title="Цель", stat="craft", **extra):
        api.create_quest(self.con, None, {"kind": "main", "title": title, "stat": stat, **extra})
        return self.state()["mains"][-1]

    def make_side(self, title="Дело", stat="soul", **extra):
        api.create_quest(self.con, None, {"kind": "side", "title": title, "stat": stat, **extra})
        return self.state()["sides"][-1]

    def make_boss(self, title="Босс", stat="mind", hp=3, **extra):
        api.create_quest(self.con, None, {"kind": "boss", "title": title, "stat": stat, "hp": hp, **extra})
        return self.state()["bosses"][-1]


class EmptyState(Base):
    def test_fresh_base_has_no_quests(self):
        state = self.state()
        self.assertEqual(state["mains"], [])
        self.assertEqual(state["sides"], [])
        self.assertEqual(state["bosses"], [])
        self.assertEqual(state["archive"], [])
        self.assertEqual(state["profile"]["level"], 1)
        self.assertEqual(state["profile"]["xpTotal"], 0)

    def test_state_is_json_serialisable(self):
        json.dumps(self.state(), ensure_ascii=False)

    def test_all_stats_present_and_zero(self):
        stats = self.state()["stats"]
        self.assertEqual([s["key"] for s in stats], list(db.STAT_KEYS))
        self.assertTrue(all(s["value"] == 0 for s in stats))

    def test_hero_name_comes_from_settings(self):
        con = db.memory(SCHEMA, "Тестовый герой")
        self.assertEqual(api.read_state(con)["profile"]["name"], "Тестовый герой")
        con.close()

    def test_stats_carry_no_human_text(self):
        """Названия живут в словарях интерфейса, иначе язык не переключить."""
        self.assertEqual(set(self.state()["stats"][0]), {"key", "value"})


class CreateQuest(Base):
    def test_new_main_starts_in_fog(self):
        quest = self.make_main()
        self.assertTrue(quest["fog"])
        self.assertEqual(quest["chapters"], [])
        self.assertEqual(quest["xpTotal"], 0)

    def test_mains_have_no_limit(self):
        """Лимит трёх мейнов убрали: сколько целей держать — решает человек."""
        for n in range(5):
            self.make_main(title=f"Цель {n}")
        self.assertEqual(len(self.state()["mains"]), 5)

    def test_side_takes_custom_xp_and_repeat(self):
        side = self.make_side(xp=25, repeat={"unit": "week", "every": 2})
        self.assertEqual(side["xp"], 25)
        self.assertEqual(side["repeat"], {"unit": "week", "every": 2})

    def test_side_xp_defaults(self):
        self.assertEqual(self.make_side()["xp"], api.DEFAULT_SIDE_XP)

    def test_boss_reward_defaults_to_full_grind(self):
        boss = self.make_boss(hp=10, hitXp=7)
        self.assertEqual(boss["hpMax"], 10)
        self.assertEqual(boss["hpLeft"], 10)
        self.assertEqual(boss["xpReward"], 70)

    def test_due_date_returns_days_left(self):
        soon = (date.today() + timedelta(days=5)).isoformat()
        self.make_main(dueDate=soon)
        self.assertEqual(self.state()["mains"][-1]["daysLeft"], 5)

    def test_past_due_date_is_negative(self):
        past = (date.today() - timedelta(days=3)).isoformat()
        self.make_main(dueDate=past)
        self.assertEqual(self.state()["mains"][-1]["daysLeft"], -3)


class InputValidation(Base):
    def test_bad_quest_bodies_are_rejected(self):
        cases = [
            ({"kind": "main", "title": "   ", "stat": "body"}, "пустое название"),
            ({"kind": "epic", "title": "Тест", "stat": "body"}, "неизвестный тип"),
            ({"kind": "side", "title": "Тест", "stat": "удача"}, "неизвестная характеристика"),
            ({"kind": "side", "title": "я" * 200, "stat": "body"}, "слишком длинно"),
            ({"kind": "main", "title": 42, "stat": "body"}, "название не строка"),
            ({"kind": "main", "title": "Тест", "stat": "body", "dueDate": "01.06.2026"}, "формат даты"),
            ({"kind": "main", "title": "Тест", "stat": "body", "dueDate": "2026-02-31"}, "нет такой даты"),
            ({"kind": "boss", "title": "Тест", "stat": "body"}, "босс без hp"),
            ({"kind": "boss", "title": "Тест", "stat": "body", "hp": 0}, "hp ниже нуля"),
            ({"kind": "boss", "title": "Тест", "stat": "body", "hp": 1.5}, "hp не целое"),
            ({"kind": "boss", "title": "Тест", "stat": "body", "hp": True}, "булево вместо числа"),
        ]
        for body, why in cases:
            with self.subTest(why=why), self.assertRaises(api.Bad):
                api.create_quest(self.con, None, body)

    def test_empty_chapter_name_is_rejected(self):
        quest = self.make_main()
        with self.assertRaises(api.Bad):
            api.add_chapter(self.con, quest["id"], {"name": "  "})

    def test_chapter_xp_out_of_range_is_rejected(self):
        quest = self.make_main()
        for amount in (0, -5, api.MAX_CHAPTER_XP + 1):
            with self.subTest(xp=amount), self.assertRaises(api.Bad):
                api.add_chapter(self.con, quest["id"], {"name": "Шаг", "xp": amount})

    def test_unknown_ids_give_404(self):
        for call in (
            lambda: api.toggle_chapter(self.con, 999, {}),
            lambda: api.toggle_side(self.con, 999, {}),
            lambda: api.hit_boss(self.con, 999, {}),
            lambda: api.add_chapter(self.con, 999, {"name": "Шаг"}),
            lambda: api.delete_quest(self.con, 999, {}),
        ):
            with self.assertRaises(api.Bad) as caught:
                call()
            self.assertEqual(caught.exception.status, 404)

    def test_side_quest_cannot_have_chapters(self):
        side = self.make_side()
        with self.assertRaises(api.Bad) as caught:
            api.add_chapter(self.con, side["id"], {"name": "Шаг"})
        self.assertEqual(caught.exception.status, 409)


class Chapters(Base):
    def setUp(self):
        super().setUp()
        self.quest = self.make_main(stat="craft")
        for name, amount in (("Первый шаг", 20), ("Второй шаг", 30)):
            api.add_chapter(self.con, self.quest["id"], {"name": name, "xp": amount})

    def chapters(self):
        return self.state()["mains"][0]["chapters"]

    def test_first_chapter_lifts_the_fog(self):
        self.assertFalse(self.state()["mains"][0]["fog"])

    def test_toggle_grants_and_returns_xp(self):
        chapter = self.chapters()[0]
        api.toggle_chapter(self.con, chapter["id"], {})
        self.assertEqual(self.xp_total(), 20)

        api.toggle_chapter(self.con, chapter["id"], {})
        self.assertEqual(self.xp_total(), 0)

    def test_toggle_is_fully_reversible_including_level(self):
        """Главная причина, по которой уровень не хранится, а выводится."""
        api.add_chapter(self.con, self.quest["id"], {"name": "Дорогой шаг", "xp": 200})
        before = self.state()["profile"]
        chapter = self.chapters()[-1]

        api.toggle_chapter(self.con, chapter["id"], {})
        self.assertGreater(self.state()["profile"]["level"], before["level"])

        api.toggle_chapter(self.con, chapter["id"], {})
        self.assertEqual(self.state()["profile"], before)

    def test_stat_points_return_on_undo(self):
        chapter = self.chapters()[0]
        api.toggle_chapter(self.con, chapter["id"], {})
        self.assertEqual(self.stat("craft"), xp.stat_points(20))
        api.toggle_chapter(self.con, chapter["id"], {})
        self.assertEqual(self.stat("craft"), 0)

    def test_last_chapter_closes_quest_with_bonus(self):
        for chapter in self.chapters():
            flash = api.toggle_chapter(self.con, chapter["id"], {})

        self.assertEqual(self.state()["mains"], [])          # закрытый уходит с доски
        bonus = round(50 * api.CLOSE_BONUS_SHARE)
        self.assertEqual(self.xp_total(), 50 + bonus)

        closed = [f for f in flash if f["code"] == "main_closed"]
        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0]["params"]["bonus"], bonus)

        archive = self.state()["archive"]
        self.assertEqual(len(archive), 1)
        self.assertEqual(archive[0]["reason"], "closed")
        self.assertEqual(archive[0]["xp"], 50)

    def test_closed_quest_comes_back_from_archive(self):
        for chapter in self.chapters():
            api.toggle_chapter(self.con, chapter["id"], {})
        entry = self.state()["archive"][0]

        api.restore_archived(self.con, entry["id"], {})
        self.assertEqual(len(self.state()["mains"]), 1)
        # 50 за шаги; бонус за закрытие вернулся: квест снова открыт
        self.assertEqual(self.xp_total(), 50)


class Substeps(Base):
    """Второй уровень: у шага есть подшаги, и он закрывается сам."""

    def setUp(self):
        super().setUp()
        self.quest = self.make_main(stat="craft")
        api.add_chapter(self.con, self.quest["id"], {"name": "Получить загранпаспорт", "xp": 40})
        self.step = self.steps()[0]

    def steps(self):
        mains = self.state()["mains"]
        return mains[0]["chapters"] if mains else []

    def step_done(self, chapter_id):
        return bool(self.con.execute(
            "SELECT done FROM chapters WHERE id = ?", (chapter_id,)).fetchone()["done"])

    def add_sub(self, name, xp=10):
        api.add_chapter(self.con, self.quest["id"],
                        {"name": name, "xp": xp, "parentId": self.step["id"]})
        return self.steps()[0]["children"][-1]

    def test_substep_lands_inside_its_step(self):
        self.add_sub("Забрать военный билет")
        step = self.steps()[0]
        self.assertEqual(len(step["children"]), 1)
        self.assertEqual(step["children"][0]["name"], "Забрать военный билет")

    def test_step_with_substeps_cannot_be_ticked_by_hand(self):
        self.add_sub("Забрать военный билет")
        with self.assertRaises(api.Bad) as caught:
            api.toggle_chapter(self.con, self.step["id"], {})
        self.assertEqual(caught.exception.status, 409)

    def test_step_closes_itself_when_substeps_are_done(self):
        first = self.add_sub("Забрать военный билет", 10)
        second = self.add_sub("Подать заявление", 10)

        api.toggle_chapter(self.con, first["id"], {})
        self.assertFalse(self.steps()[0]["done"], "рано закрывать: остался подшаг")
        self.assertEqual(self.xp_total(), 10)

        api.toggle_chapter(self.con, second["id"], {})
        # 10 + 10 за подшаги, 40 за шаг, четверть от 60 за закрытие квеста
        self.assertEqual(self.xp_total(), 10 + 10 + 40 + round(60 * api.CLOSE_BONUS_SHARE))
        self.assertEqual(self.state()["mains"], [], "все подшаги отмечены — квест закрылся")
        self.assertEqual(self.state()["archive"][0]["stepsDone"], 1,
                         "шаг закрылся сам вместе с квестом")

    def test_restore_keeps_closed_steps_closed(self):
        first = self.add_sub("Забрать военный билет", 10)
        second = self.add_sub("Подать заявление", 10)
        api.toggle_chapter(self.con, first["id"], {})
        api.toggle_chapter(self.con, second["id"], {})
        self.assertEqual(self.state()["mains"], [], "квест закрылся")

        api.restore_archived(self.con, self.state()["archive"][0]["id"], {})
        self.assertEqual(len(self.state()["mains"]), 1, "квест вернулся на доску")
        self.assertTrue(self.step_done(self.step["id"]),
                        "шаг остаётся закрытым: работа сделана")
        # 10 + 10 за подшаги и 40 за шаг; бонус за закрытие вернулся назад
        self.assertEqual(self.xp_total(), 10 + 10 + 40)

    def test_substep_of_a_substep_is_rejected(self):
        sub = self.add_sub("Забрать военный билет")
        with self.assertRaises(api.Bad) as caught:
            api.add_chapter(self.con, self.quest["id"],
                            {"name": "Найти папку", "parentId": sub["id"]})
        self.assertEqual(caught.exception.status, 409)

    def test_parent_from_another_quest_is_rejected(self):
        other = self.make_main(title="Другая цель", stat="soul")
        with self.assertRaises(api.Bad) as caught:
            api.add_chapter(self.con, other["id"],
                            {"name": "Чужой подшаг", "parentId": self.step["id"]})
        self.assertEqual(caught.exception.status, 409)

    def test_substep_added_to_a_restored_step_reopens_it(self):
        api.toggle_chapter(self.con, self.step["id"], {})
        self.assertEqual(self.state()["mains"], [], "квест закрылся единственным шагом")

        api.restore_archived(self.con, self.state()["archive"][0]["id"], {})
        api.add_chapter(self.con, self.quest["id"],
                        {"name": "Забрать военный билет", "parentId": self.step["id"], "xp": 10})

        self.assertFalse(self.step_done(self.step["id"]), "шаг снова открыт: работа не закончена")
        self.assertEqual(len(self.state()["mains"]), 1)
        self.assertEqual(self.xp_total(), 0, "опыт за шаг вернулся")

    def test_deleting_the_quest_removes_substeps(self):
        self.add_sub("Забрать военный билет")
        api.delete_quest(self.con, self.quest["id"], {})
        left = self.con.execute("SELECT count(*) AS n FROM chapters").fetchone()["n"]
        self.assertEqual(left, 0)

    def test_quest_progress_counts_only_top_level_steps(self):
        self.add_sub("Забрать военный билет")
        api.add_chapter(self.con, self.quest["id"], {"name": "Купить билеты", "xp": 20})

        quest = self.state()["mains"][0]
        self.assertEqual(len(quest["chapters"]), 2, "подшаг не должен быть отдельной строкой")
        self.assertEqual(quest["xpTotal"], 40 + 10 + 20, "цена квеста считает и подшаги")

    def test_unknown_parent_is_rejected(self):
        with self.assertRaises(api.Bad) as caught:
            api.add_chapter(self.con, self.quest["id"], {"name": "Шаг", "parentId": 9999})
        self.assertEqual(caught.exception.status, 404)


class DeleteStep(Base):
    """Удаление шага: без него опечатка в подшаге навсегда держит шаг открытым."""

    def setUp(self):
        super().setUp()
        self.quest = self.make_main(stat="craft")
        api.add_chapter(self.con, self.quest["id"], {"name": "Получить загранпаспорт", "xp": 40})
        self.step = self.state()["mains"][0]["chapters"][0]

    def steps(self):
        mains = self.state()["mains"]
        return mains[0]["chapters"] if mains else []

    def test_step_is_removed(self):
        api.delete_chapter(self.con, self.step["id"], {})
        self.assertEqual(self.steps(), [])

    def test_substeps_go_with_the_step(self):
        api.add_chapter(self.con, self.quest["id"],
                        {"name": "Забрать военный билет", "parentId": self.step["id"]})
        api.delete_chapter(self.con, self.step["id"], {})
        self.assertEqual(self.con.execute("SELECT count(*) AS n FROM chapters").fetchone()["n"], 0)

    def test_earned_experience_stays(self):
        api.add_chapter(self.con, self.quest["id"], {"name": "Купить билеты", "xp": 10})
        api.toggle_chapter(self.con, self.step["id"], {})
        earned = self.xp_total()
        api.delete_chapter(self.con, self.step["id"], {})
        self.assertEqual(self.xp_total(), earned)

    def test_removing_the_last_open_substep_closes_the_step(self):
        done = api.add_chapter(self.con, self.quest["id"],
                               {"name": "Забрать военный билет", "xp": 10,
                                "parentId": self.step["id"]}) or None
        api.add_chapter(self.con, self.quest["id"],
                        {"name": "Опечатка", "xp": 10, "parentId": self.step["id"]})

        children = self.steps()[0]["children"]
        api.toggle_chapter(self.con, children[0]["id"], {})
        self.assertFalse(self.steps()[0]["done"], "опечатка всё ещё держит шаг открытым")

        api.delete_chapter(self.con, children[1]["id"], {})
        self.assertEqual(self.state()["mains"], [], "шаг закрылся сам и закрыл квест")
        self.assertEqual(self.state()["archive"][0]["stepsDone"], 1,
                         "шаг закрылся сам: открытых подшагов не осталось")

    def test_unknown_step_is_404(self):
        with self.assertRaises(api.Bad) as caught:
            api.delete_chapter(self.con, 9999, {})
        self.assertEqual(caught.exception.status, 404)


class Sides(Base):
    def test_daily_streak_grows_and_shrinks(self):
        side = self.make_side(repeat={"unit": "day", "every": 1}, xp=10)
        api.toggle_side(self.con, side["id"], {})
        self.assertEqual(self.state()["sides"][0]["streak"], 1)

        api.toggle_side(self.con, side["id"], {})
        self.assertEqual(self.state()["sides"][0]["streak"], 0)

    def test_one_off_side_has_no_streak(self):
        side = self.make_side()
        api.toggle_side(self.con, side["id"], {})
        self.assertEqual(self.state()["sides"][0]["streak"], 0)

    def test_done_side_stays_visible(self):
        side = self.make_side()
        api.toggle_side(self.con, side["id"], {})
        listed = self.state()["sides"]
        self.assertEqual(len(listed), 1)
        self.assertTrue(listed[0]["done"])

    def test_xp_returns_on_undo(self):
        side = self.make_side(xp=15)
        api.toggle_side(self.con, side["id"], {})
        self.assertEqual(self.xp_total(), 15)
        api.toggle_side(self.con, side["id"], {})
        self.assertEqual(self.xp_total(), 0)


class Repeats(Base):
    """Периодичность: квест сам открывается, когда период закончился."""

    def side_row(self):
        return self.state()["sides"][0]

    def db_row(self, quest_id):
        return self.con.execute("SELECT * FROM quests WHERE id = ?", (quest_id,)).fetchone()

    def test_period_arithmetic(self):
        start = date(2026, 1, 31)
        self.assertEqual(api.add_period(start, "day", 3), date(2026, 2, 3))
        self.assertEqual(api.add_period(start, "week", 2), date(2026, 2, 14))
        # 31 января плюс месяц — конец февраля, а не выдуманное 31 февраля
        self.assertEqual(api.add_period(start, "month", 1), date(2026, 2, 28))
        self.assertEqual(api.add_period(date(2026, 11, 30), "month", 2), date(2027, 1, 30))

    def test_one_off_side_never_rolls(self):
        side = self.make_side()
        api.toggle_side(self.con, side["id"], {})
        api.roll_periods(self.con, date.today() + timedelta(days=365))
        self.assertTrue(self.side_row()["done"], "разовое дело не открывается заново")

    def test_weekly_quest_reopens_after_a_week(self):
        side = self.make_side(repeat={"unit": "week", "every": 1}, xp=10)
        api.toggle_side(self.con, side["id"], {})
        self.assertTrue(self.side_row()["done"])

        api.roll_periods(self.con, date.today() + timedelta(days=6))
        self.assertTrue(self.side_row()["done"], "неделя ещё не прошла")

        api.roll_periods(self.con, date.today() + timedelta(days=7))
        row = self.side_row()
        self.assertFalse(row["done"], "новая неделя — квест снова открыт")
        self.assertEqual(row["streak"], 1, "серия держится: период закрыли вовремя")

    def test_missed_period_resets_the_streak(self):
        side = self.make_side(repeat={"unit": "day", "every": 1}, xp=10)
        api.toggle_side(self.con, side["id"], {})

        api.roll_periods(self.con, date.today() + timedelta(days=1))
        self.assertEqual(self.side_row()["streak"], 1)

        # день прошёл, а квест не закрыли
        api.roll_periods(self.con, date.today() + timedelta(days=2))
        self.assertEqual(self.side_row()["streak"], 0, "пропуск обнуляет серию")

    def test_long_absence_resets_once(self):
        side = self.make_side(repeat={"unit": "day", "every": 1}, xp=10)
        api.toggle_side(self.con, side["id"], {})

        api.roll_periods(self.con, date.today() + timedelta(days=40))
        row = self.side_row()
        self.assertEqual(row["streak"], 0)
        self.assertFalse(row["done"])
        self.assertEqual(
            self.db_row(side["id"])["period_start"],
            (date.today() + timedelta(days=40)).isoformat(),
            "период должен догнать сегодняшний день, а не остаться в прошлом",
        )

    def test_every_three_days_waits_three_days(self):
        side = self.make_side(repeat={"unit": "day", "every": 3}, xp=10)
        api.toggle_side(self.con, side["id"], {})

        api.roll_periods(self.con, date.today() + timedelta(days=2))
        self.assertTrue(self.side_row()["done"])

        api.roll_periods(self.con, date.today() + timedelta(days=3))
        self.assertFalse(self.side_row()["done"])

    def test_renews_in_counts_down(self):
        self.make_side(repeat={"unit": "week", "every": 1})
        self.assertEqual(self.side_row()["renewsIn"], 7)

    def test_changing_the_rhythm_restarts_the_count(self):
        side = self.make_side(repeat={"unit": "day", "every": 1}, xp=10)
        api.toggle_side(self.con, side["id"], {})
        self.assertEqual(self.side_row()["streak"], 1)

        api.update_quest(self.con, side["id"], {"repeat": {"unit": "month", "every": 1}})
        row = self.side_row()
        self.assertEqual(row["repeat"], {"unit": "month", "every": 1})
        self.assertEqual(row["streak"], 0, "новый ритм — новый отсчёт")

    def test_bad_repeat_is_rejected(self):
        cases = [
            {"unit": "year", "every": 1},
            {"unit": "day", "every": 0},
            {"unit": "day", "every": api.MAX_REPEAT_EVERY + 1},
            {"every": 2},
        ]
        for repeat in cases:
            with self.subTest(repeat=repeat), self.assertRaises(api.Bad):
                self.make_side(title="Плохой ритм", repeat=repeat)


class Boss(Base):
    def setUp(self):
        super().setUp()
        self.boss = self.make_boss(hp=3, hitXp=10, xp=100)

    def hp(self):
        rows = self.state()["bosses"]
        return rows[0]["hpLeft"] if rows else 0

    def test_hit_drops_one_hp_and_pays(self):
        api.hit_boss(self.con, self.boss["id"], {})
        self.assertEqual(self.hp(), 2)
        self.assertEqual(self.xp_total(), 10)

    def test_final_hit_pays_reward_and_closes(self):
        for _ in range(3):
            flash = api.hit_boss(self.con, self.boss["id"], {})

        self.assertEqual(self.state()["bosses"], [])
        self.assertEqual(self.xp_total(), 3 * 10 + 100)
        self.assertTrue(any(f["code"] == "boss_defeated" for f in flash))

    def test_dead_boss_cannot_be_hit(self):
        for _ in range(3):
            api.hit_boss(self.con, self.boss["id"], {})
        with self.assertRaises(api.Bad) as caught:
            api.hit_boss(self.con, self.boss["id"], {})
        self.assertEqual(caught.exception.status, 404,
                         "побеждённый босс уже уехал в архив")

    def test_boss_phases_are_chapters(self):
        api.add_chapter(self.con, self.boss["id"], {"name": "Фаза 1", "xp": 30})
        self.assertEqual(len(self.state()["bosses"][0]["phases"]), 1)

    def test_closing_all_phases_does_not_kill_the_boss(self):
        api.add_chapter(self.con, self.boss["id"], {"name": "Фаза 1", "xp": 30})
        phase = self.state()["bosses"][0]["phases"][0]
        api.toggle_chapter(self.con, phase["id"], {})
        self.assertEqual(self.hp(), 3)                       # здоровье решает, а не фазы


class EditQuest(Base):
    def test_title_and_reason_change(self):
        quest = self.make_main(title="Цель", stat="craft")
        api.update_quest(self.con, quest["id"], {"title": "  Новая цель  ", "why": "чтобы не бросить"})

        fresh = self.state()["mains"][0]
        self.assertEqual(fresh["title"], "Новая цель")
        self.assertEqual(fresh["why"], "чтобы не бросить")

    def test_only_sent_fields_change(self):
        quest = self.make_main(title="Цель", stat="craft")
        api.update_quest(self.con, quest["id"], {"title": "Другая"})

        fresh = self.state()["mains"][0]
        self.assertEqual(fresh["stat"], "craft", "характеристику не трогали")

    def test_due_date_can_be_set_and_cleared(self):
        quest = self.make_main()
        soon = (date.today() + timedelta(days=9)).isoformat()

        api.update_quest(self.con, quest["id"], {"dueDate": soon})
        self.assertEqual(self.state()["mains"][0]["daysLeft"], 9)

        api.update_quest(self.con, quest["id"], {"dueDate": None})
        self.assertIsNone(self.state()["mains"][0]["daysLeft"])

    def test_earned_experience_survives_an_edit(self):
        quest = self.make_main(stat="craft")
        api.add_chapter(self.con, quest["id"], {"name": "Шаг", "xp": 20})
        api.add_chapter(self.con, quest["id"], {"name": "Ещё шаг", "xp": 10})
        api.toggle_chapter(self.con, self.state()["mains"][0]["chapters"][0]["id"], {})
        earned = self.xp_total()

        points = xp.stat_points(20)

        api.update_quest(self.con, quest["id"], {"stat": "soul", "title": "Переименовали"})
        self.assertEqual(self.xp_total(), earned)
        self.assertEqual(self.stat("craft"), points, "очки остались на прежней шкале")
        self.assertEqual(self.stat("soul"), 0, "новая шкала не получает чужую работу")

    def test_side_xp_and_repeat_change(self):
        side = self.make_side(xp=10, repeat={"unit": "day", "every": 1})
        api.toggle_side(self.con, side["id"], {})
        api.update_quest(self.con, side["id"], {"xp": 25, "repeat": None})

        fresh = self.state()["sides"][0]
        self.assertEqual(fresh["xp"], 25)
        self.assertIsNone(fresh["repeat"])
        self.assertEqual(fresh["streak"], 0, "без повторения серия теряет смысл")

    def test_boss_hit_count_keeps_the_damage_dealt(self):
        boss = self.make_boss(hp=10, hitXp=5)
        api.hit_boss(self.con, boss["id"], {})
        api.hit_boss(self.con, boss["id"], {})          # нанесено 2 удара

        api.update_quest(self.con, boss["id"], {"hp": 20})
        fresh = self.state()["bosses"][0]
        self.assertEqual(fresh["hpMax"], 20)
        self.assertEqual(fresh["hpLeft"], 18, "два удара не должны пропасть")

    def test_boss_cannot_shrink_below_damage_dealt(self):
        boss = self.make_boss(hp=10, hitXp=5)
        for _ in range(4):
            api.hit_boss(self.con, boss["id"], {})

        with self.assertRaises(api.Bad) as caught:
            api.update_quest(self.con, boss["id"], {"hp": 3})
        self.assertEqual(caught.exception.status, 409)

    def test_bad_edits_are_rejected(self):
        quest = self.make_main()
        cases = [
            ({"title": "   "}, "пустое название"),
            ({"title": "я" * 200}, "слишком длинно"),
            ({"stat": "удача"}, "неизвестная характеристика"),
            ({"dueDate": "31.12.2026"}, "формат даты"),
        ]
        for body, why in cases:
            with self.subTest(why=why), self.assertRaises(api.Bad):
                api.update_quest(self.con, quest["id"], body)

    def test_empty_edit_changes_nothing(self):
        quest = self.make_main(title="Цель")
        before = len(self.state()["events"])
        self.assertEqual(api.update_quest(self.con, quest["id"], {}), [])
        self.assertEqual(len(self.state()["events"]), before, "пустая правка не пишется в журнал")

    def test_unknown_quest_is_404(self):
        with self.assertRaises(api.Bad) as caught:
            api.update_quest(self.con, 9999, {"title": "Нет такого"})
        self.assertEqual(caught.exception.status, 404)


class Deletion(Base):
    def test_delete_removes_quest_and_chapters(self):
        quest = self.make_main()
        api.add_chapter(self.con, quest["id"], {"name": "Шаг"})
        api.delete_quest(self.con, quest["id"], {})

        self.assertEqual(self.state()["mains"], [])
        left = self.con.execute("SELECT count(*) AS n FROM chapters").fetchone()["n"]
        self.assertEqual(left, 0)

    def test_delete_keeps_earned_xp(self):
        quest = self.make_main()
        api.add_chapter(self.con, quest["id"], {"name": "Шаг", "xp": 20})
        api.add_chapter(self.con, quest["id"], {"name": "Ещё шаг", "xp": 10})
        chapter = self.state()["mains"][0]["chapters"][0]
        api.toggle_chapter(self.con, chapter["id"], {})

        self.assertEqual(self.xp_total(), 20)

        api.delete_quest(self.con, quest["id"], {})
        self.assertEqual(self.xp_total(), 20, "заработанный опыт остаётся")


class Profile(Base):
    def test_skin_whitelist(self):
        api.update_profile(self.con, None, {"skin": "platinum"})
        self.assertEqual(self.state()["profile"]["skin"], "platinum")
        with self.assertRaises(api.Bad):
            api.update_profile(self.con, None, {"skin": "amber"})

    def test_rest_toggles_and_reports(self):
        flash = api.update_profile(self.con, None, {"resting": True})
        self.assertTrue(self.state()["profile"]["resting"])
        self.assertEqual(flash[0]["code"], "rest_on")

        api.update_profile(self.con, None, {"resting": False})
        self.assertFalse(self.state()["profile"]["resting"])

    def test_places_round_trip(self):
        places = {"boss": {"x": 10, "y": 20, "w": "500px", "h": ""}}
        api.update_profile(self.con, None, {"places": places})
        self.assertEqual(self.state()["profile"]["places"], places)

    def test_notepad_round_trip(self):
        self.assertEqual(self.state()["profile"]["notepad"], "")
        api.update_profile(self.con, None, {"notepad": "купить гантели"})
        self.assertEqual(self.state()["profile"]["notepad"], "купить гантели")

    def test_notepad_keeps_line_breaks(self):
        sheet = "купить гантели\nидея: таймер помидорками"
        api.update_profile(self.con, None, {"notepad": sheet})
        self.assertEqual(self.state()["profile"]["notepad"], sheet)

    def test_notepad_can_be_emptied(self):
        api.update_profile(self.con, None, {"notepad": "черновик"})
        api.update_profile(self.con, None, {"notepad": ""})
        self.assertEqual(self.state()["profile"]["notepad"], "")

    def test_notepad_stays_out_of_the_journal(self):
        before = len(self.state()["events"])
        api.update_profile(self.con, None, {"notepad": "тишина"})
        self.assertEqual(len(self.state()["events"]), before)

    def test_oversized_notepad_is_rejected(self):
        with self.assertRaises(api.Bad):
            api.update_profile(self.con, None, {"notepad": "я" * (api.MAX_NOTEPAD + 1)})

    def test_places_must_be_object(self):
        with self.assertRaises(api.Bad):
            api.update_profile(self.con, None, {"places": "[]"})

    def test_empty_name_is_rejected(self):
        with self.assertRaises(api.Bad):
            api.update_profile(self.con, None, {"name": "   "})

    def test_name_is_saved_and_logged(self):
        api.update_profile(self.con, None, {"name": "  Максим  "})
        self.assertEqual(self.state()["profile"]["name"], "Максим")

        last = self.state()["events"][-1]
        self.assertEqual(last["code"], "name_changed")
        self.assertEqual(last["params"], {"name": "Максим"})

    def test_too_long_name_is_rejected(self):
        with self.assertRaises(api.Bad):
            api.update_profile(self.con, None, {"name": "я" * (api.MAX_NAME + 1)})


class Archive(Base):
    """Закрытые и удалённые квесты уходят в архив и возвращаются из него."""

    def entry(self):
        return self.state()["archive"][0]

    def test_closed_main_lands_in_archive(self):
        quest = self.make_main()
        api.add_chapter(self.con, quest["id"], {"name": "Шаг", "xp": 40})
        chapter = self.state()["mains"][0]["chapters"][0]
        api.toggle_chapter(self.con, chapter["id"], {})

        self.assertEqual(self.state()["mains"], [])
        entry = self.entry()
        self.assertEqual(entry["kind"], "main")
        self.assertEqual(entry["reason"], "closed")
        self.assertEqual(entry["xp"], 40)
        self.assertEqual(entry["stepsDone"], 1)
        self.assertEqual(entry["stepsTotal"], 1)

        left = self.con.execute("SELECT count(*) AS n FROM quests").fetchone()["n"]
        self.assertEqual(left, 0, "строка квеста уходит из базы в снимок")

    def test_defeated_boss_lands_in_archive(self):
        boss = self.make_boss(hp=1)
        api.hit_boss(self.con, boss["id"], {})

        self.assertEqual(self.state()["bosses"], [])
        entry = self.entry()
        self.assertEqual(entry["kind"], "boss")
        self.assertEqual(entry["reason"], "closed")

    def test_deleted_side_lands_in_archive(self):
        side = self.make_side(xp=7)
        api.delete_quest(self.con, side["id"], {})

        entry = self.entry()
        self.assertEqual(entry["kind"], "side")
        self.assertEqual(entry["reason"], "deleted")
        self.assertEqual(entry["xp"], 7)

    def test_done_side_stays_out_of_archive(self):
        side = self.make_side()
        api.toggle_side(self.con, side["id"], {})
        self.assertEqual(self.state()["archive"], [],
                         "закрытая ежедневка остаётся на доске до конца периода")

    def test_restore_returns_bonus_and_reopens_quest(self):
        quest = self.make_main()
        api.add_chapter(self.con, quest["id"], {"name": "Шаг", "xp": 40})
        chapter = self.state()["mains"][0]["chapters"][0]
        api.toggle_chapter(self.con, chapter["id"], {})
        bonus = round(40 * api.CLOSE_BONUS_SHARE)
        self.assertEqual(self.xp_total(), 40 + bonus)

        api.restore_archived(self.con, self.entry()["id"], {})
        self.assertEqual(len(self.state()["mains"]), 1)
        self.assertEqual(self.xp_total(), 40, "бонус за закрытие вернулся")
        self.assertTrue(self.state()["mains"][0]["chapters"][0]["done"],
                        "сделанный шаг остаётся сделанным")
        self.assertEqual(self.state()["archive"], [])

    def test_restore_of_boss_revives_it(self):
        boss = self.make_boss(hp=5, xp=30, hitXp=10)
        for _ in range(5):
            api.hit_boss(self.con, boss["id"], {})
        self.assertEqual(self.xp_total(), 50 + 30)   # пять ударов по 10 и награда 30

        api.restore_archived(self.con, self.entry()["id"], {})
        revived = self.state()["bosses"][0]
        self.assertEqual(revived["hpLeft"], 5, "босс возвращается живым")
        self.assertEqual(self.xp_total(), 50, "награда за победу вернулась, удары остались")

    def test_restore_of_deleted_side_returns_it_as_it_was(self):
        side = self.make_side(title="Полить цветы", xp=7,
                              repeat={"unit": "day", "every": 1})
        api.toggle_side(self.con, side["id"], {})   # закрыт, серия 1
        api.delete_quest(self.con, side["id"], {})

        api.restore_archived(self.con, self.entry()["id"], {})
        restored = self.state()["sides"][-1]
        self.assertTrue(restored["done"], "сделанное дело не сбрасывают")
        self.assertEqual(restored["streak"], 1, "серия возвращается")
        self.assertEqual(restored["xp"], 7)
        self.assertEqual(self.xp_total(), 7, "опыт за сделанное дело остаётся")

    def test_deleted_main_with_substeps_restores_the_tree(self):
        quest = self.make_main()
        api.add_chapter(self.con, quest["id"], {"name": "Шаг", "xp": 40})
        step = self.state()["mains"][0]["chapters"][0]
        api.add_chapter(self.con, quest["id"],
                        {"name": "Подшаг", "xp": 10, "parentId": step["id"]})
        api.delete_quest(self.con, quest["id"], {})

        api.restore_archived(self.con, self.entry()["id"], {})
        step = self.state()["mains"][0]["chapters"][0]
        self.assertEqual([child["name"] for child in step["children"]], ["Подшаг"])
        self.assertEqual(step["children"][0]["xp"], 10)

    def test_purge_erases_entry_forever(self):
        side = self.make_side()
        api.delete_quest(self.con, side["id"], {})
        entry = self.entry()

        api.purge_archive(self.con, entry["id"], {})
        self.assertEqual(self.state()["archive"], [])
        with self.assertRaises(api.Bad) as caught:
            api.purge_archive(self.con, entry["id"], {})
        self.assertEqual(caught.exception.status, 404)

    def test_restore_of_unknown_entry_is_404(self):
        with self.assertRaises(api.Bad) as caught:
            api.restore_archived(self.con, 999, {})
        self.assertEqual(caught.exception.status, 404)

    def test_archive_routes_reach_actions(self):
        side = self.make_side()
        api.delete_quest(self.con, side["id"], {})
        entry = self.entry()

        api.dispatch(self.con, f"/api/archive/{entry['id']}/restore", {})
        self.assertEqual(len(self.state()["sides"]), 1)

        api.delete_quest(self.con, self.state()["sides"][0]["id"], {})
        entry = self.entry()
        api.dispatch(self.con, f"/api/archive/{entry['id']}/delete", {})
        self.assertEqual(self.state()["archive"], [])


class Migration(unittest.TestCase):
    """Старая база догоняет схему без переноса вручную."""

    def test_missing_column_is_added(self):
        con = db.memory(SCHEMA)
        con.execute("ALTER TABLE profile DROP COLUMN notepad")   # откатываем к прежней схеме
        self.assertEqual(db.migrate(con), ["profile.notepad"])
        self.assertEqual(api.read_state(con)["profile"]["notepad"], "")
        con.close()

    def test_missing_archive_table_is_added(self):
        con = db.memory(SCHEMA)
        con.execute("DROP TABLE archive")
        self.assertEqual(db.migrate(con), ["archive (таблица)"])
        self.assertEqual(api.read_state(con)["archive"], [])
        con.close()

    def test_migration_is_idempotent(self):
        con = db.memory(SCHEMA)
        self.assertEqual(db.migrate(con), [])
        self.assertEqual(db.migrate(con), [])
        con.close()


class Dispatch(Base):
    def test_routes_reach_their_actions(self):
        api.dispatch(self.con, "/api/quests", {"kind": "side", "title": "Через маршрут", "stat": "soul"})
        self.assertEqual(self.state()["sides"][0]["title"], "Через маршрут")

    def test_unknown_route_is_404(self):
        with self.assertRaises(api.Bad) as caught:
            api.dispatch(self.con, "/api/nope", {})
        self.assertEqual(caught.exception.status, 404)


class Journal(Base):
    def test_every_action_leaves_a_line(self):
        before = len(self.state()["events"])
        self.make_side(title="Записать в журнал")
        self.assertGreater(len(self.state()["events"]), before)

    def test_events_are_capped(self):
        for n in range(api.MAX_EVENTS + 10):
            api.log(self.con, "side_done", title=f"Дело {n}", xp=1)
        self.assertEqual(len(self.state()["events"]), api.MAX_EVENTS)

    def test_event_keeps_code_and_params(self):
        side = self.make_side(title="Полить цветы", xp=7)
        api.toggle_side(self.con, side["id"], {})
        last = self.state()["events"][-1]
        self.assertEqual(last["code"], "side_done")
        self.assertEqual(last["params"], {"title": "Полить цветы", "xp": 7})

    def test_journal_has_no_human_text(self):
        """Ни одной готовой фразы: иначе журнал застрянет на языке записи."""
        self.make_main(title="Цель")
        for event in self.state()["events"]:
            self.assertRegex(event["code"], r"^[a-z_]+$")


class Demo(Base):
    demo = True

    def test_demo_fills_the_board(self):
        state = self.state()
        self.assertEqual(len(state["mains"]), 2)
        self.assertEqual(len(state["bosses"]), 1)
        self.assertEqual(len(state["sides"]), 5)
        self.assertEqual(state["profile"]["level"], 7)

    def test_demo_has_a_quest_in_fog(self):
        self.assertTrue(any(q["fog"] for q in self.state()["mains"]))

    def test_demo_is_not_applied_twice(self):
        with self.assertRaises(seed.AlreadyFilled):
            seed.fill(self.con)


class DemoEnglish(Base):
    def setUp(self):
        super().setUp()
        seed.fill(self.con, "en")

    def test_english_demo_sets_language_and_titles(self):
        state = self.state()
        self.assertEqual(state["profile"]["lang"], "en")
        self.assertEqual(state["profile"]["name"], seed.HERO["en"])
        self.assertIn("Ship my own product", [q["title"] for q in state["mains"]])

    def test_both_demos_have_the_same_shape(self):
        english = self.state()
        other = db.memory(SCHEMA)
        seed.fill(other, "ru")
        russian = api.read_state(other)
        other.close()

        for key in ("mains", "sides", "bosses"):
            self.assertEqual(len(english[key]), len(russian[key]), key)
        self.assertEqual(english["profile"]["level"], russian["profile"]["level"])


if __name__ == "__main__":
    unittest.main()
