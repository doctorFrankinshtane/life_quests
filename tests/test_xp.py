"""Механика опыта: пороги, уровни, звания, очки характеристик."""

import unittest

from app import xp


class Thresholds(unittest.TestCase):
    def test_first_level_costs_base(self):
        self.assertEqual(xp.xp_needed(1), xp.BASE_XP)

    def test_each_level_costs_more(self):
        costs = [xp.xp_needed(level) for level in range(1, 12)]
        self.assertEqual(costs, sorted(costs))
        self.assertEqual(costs[1] - costs[0], xp.STEP_XP)

    def test_level_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            xp.xp_needed(0)


class Levels(unittest.TestCase):
    def test_zero_xp_is_first_level(self):
        self.assertEqual(xp.level_for(0), (1, 0))

    def test_one_short_of_threshold_stays(self):
        self.assertEqual(xp.level_for(xp.xp_needed(1) - 1), (1, xp.xp_needed(1) - 1))

    def test_exact_threshold_levels_up(self):
        self.assertEqual(xp.level_for(xp.xp_needed(1)), (2, 0))

    def test_remainder_carries_over(self):
        level, rest = xp.level_for(xp.xp_needed(1) + 7)
        self.assertEqual((level, rest), (2, 7))

    def test_rest_never_reaches_next_threshold(self):
        for total in range(0, 5000, 37):
            level, rest = xp.level_for(total)
            self.assertLess(rest, xp.xp_needed(level), f"опыт {total}")

    def test_total_is_recoverable(self):
        for total in range(0, 3000, 53):
            level, rest = xp.level_for(total)
            spent = sum(xp.xp_needed(n) for n in range(1, level))
            self.assertEqual(spent + rest, total)

    def test_negative_is_rejected(self):
        with self.assertRaises(ValueError):
            xp.level_for(-1)


class Titles(unittest.TestCase):
    def test_first_level_is_first_title(self):
        self.assertEqual(xp.title_index(1), 0)

    def test_title_changes_every_few_levels(self):
        self.assertEqual(xp.title_index(xp.TITLE_EVERY), 0)
        self.assertEqual(xp.title_index(xp.TITLE_EVERY + 1), 1)

    def test_high_levels_do_not_overflow(self):
        self.assertEqual(xp.title_index(10_000), xp.TITLE_COUNT - 1)


class StatPoints(unittest.TestCase):
    def test_any_action_gives_at_least_one_point(self):
        self.assertEqual(xp.stat_points(1), 1)

    def test_points_grow_with_xp(self):
        self.assertLess(xp.stat_points(10), xp.stat_points(100))


class Progress(unittest.TestCase):
    def test_shape_is_complete(self):
        data = xp.progress(1640)
        self.assertEqual(data["level"], 7)
        self.assertEqual(data["xp"], 320)
        self.assertEqual(data["xpNeeded"], xp.xp_needed(7))
        self.assertEqual(data["xpTotal"], 1640)
        self.assertEqual(data["titleIndex"], 2)


if __name__ == "__main__":
    unittest.main()
