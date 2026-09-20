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

    def test_main_limit_is_enforced(self):
        for n in range(api.MAX_ACTIVE_MAINS):
            self.make_main(title=f"Цель {n}")
        with self.assertRaises(api.Bad) as caught:
            self.make_main(title="Лишняя")
        self.assertEqual(caught.exception.status, 409)

    def test_closing_a_main_frees_the_slot(self):
        for n in range(api.MAX_ACTIVE_MAINS):
            quest = self.make_main(title=f"Цель {n}")
        api.add_chapter(self.con, quest["id"], {"name": "Единственный шаг"})
        chapter = self.state()["mains"][-1]["chapters"][0]
        api.toggle_chapter(self.con, chapter["id"], {})

        self.make_main(title="Новая цель")          # слот освободился
        self.assertEqual(len(self.state()["mains"]), api.MAX_ACTIVE_MAINS)

    def test_side_takes_custom_xp_and_daily_flag(self):
        side = self.make_side(xp=25, daily=True)
        self.assertEqual(side["xp"], 25)
        self.assertTrue(side["daily"])

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

    def test_reopening_a_chapter_reopens_the_quest(self):
        for chapter in self.chapters():
            api.toggle_chapter(self.con, chapter["id"], {})
        closed = self.con.execute(
            "SELECT id FROM chapters ORDER BY sort DESC LIMIT 1"
        ).fetchone()["id"]

        api.toggle_chapter(self.con, closed, {})
        self.assertEqual(len(self.state()["mains"]), 1)


class Sides(Base):
    def test_daily_streak_grows_and_shrinks(self):
        side = self.make_side(daily=True, xp=10)
        api.toggle_side(self.con, side["id"], {})
        self.assertEqual(self.state()["sides"][0]["streak"], 1)

        api.toggle_side(self.con, side["id"], {})
        self.assertEqual(self.state()["sides"][0]["streak"], 0)

    def test_one_off_side_has_no_streak(self):
        side = self.make_side(daily=False)
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
        self.assertEqual(caught.exception.status, 409)

    def test_boss_phases_are_chapters(self):
        api.add_chapter(self.con, self.boss["id"], {"name": "Фаза 1", "xp": 30})
        self.assertEqual(len(self.state()["bosses"][0]["phases"]), 1)

    def test_closing_all_phases_does_not_kill_the_boss(self):
        api.add_chapter(self.con, self.boss["id"], {"name": "Фаза 1", "xp": 30})
        phase = self.state()["bosses"][0]["phases"][0]
        api.toggle_chapter(self.con, phase["id"], {})
        self.assertEqual(self.hp(), 3)                       # здоровье решает, а не фазы


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
        chapter = self.state()["mains"][0]["chapters"][0]
        api.toggle_chapter(self.con, chapter["id"], {})

        earned = 20 + round(20 * api.CLOSE_BONUS_SHARE)   # глава плюс бонус за закрытие
        self.assertEqual(self.xp_total(), earned)

        api.delete_quest(self.con, quest["id"], {})
        self.assertEqual(self.xp_total(), earned)


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


class Migration(unittest.TestCase):
    """Старая база догоняет схему без переноса вручную."""

    def test_missing_column_is_added(self):
        con = db.memory(SCHEMA)
        con.execute("ALTER TABLE profile DROP COLUMN notepad")   # откатываем к прежней схеме
        self.assertEqual(db.migrate(con), ["profile.notepad"])
        self.assertEqual(api.read_state(con)["profile"]["notepad"], "")
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
