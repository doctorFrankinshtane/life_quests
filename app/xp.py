"""Механика опыта. Чистые функции без базы и без HTTP.

Правила баланса собраны здесь, чтобы их можно было менять в одном месте
и проверять тестами отдельно от всего остального.
"""

# Порог уровня растёт линейно: 1-й стоит 120 опыта, каждый следующий на 40 дороже.
BASE_XP = 120
STEP_XP = 40

# Сколько очков характеристики даёт опыт. Делитель держит рост шкал медленнее уровня.
STAT_DIVISOR = 8

# Звание меняется раз в TITLE_EVERY уровней. Сами названия — в словарях
# интерфейса; сервер отдаёт только номер звания.
TITLE_EVERY = 3
TITLE_COUNT = 6


def xp_needed(level):
    """Сколько опыта нужно, чтобы закрыть уровень `level`."""
    if level < 1:
        raise ValueError("уровень начинается с единицы")
    return BASE_XP + (level - 1) * STEP_XP


def level_for(xp_total):
    """Уровень и остаток опыта внутри него по общему накопленному опыту."""
    if xp_total < 0:
        raise ValueError("опыт не бывает отрицательным")
    level, rest = 1, xp_total
    while rest >= xp_needed(level):
        rest -= xp_needed(level)
        level += 1
    return level, rest


def title_index(level):
    """Номер звания: 0 для первых уровней, дальше по одному за TITLE_EVERY."""
    return min(TITLE_COUNT - 1, (level - 1) // TITLE_EVERY)


def progress(xp_total):
    """Всё, что нужно листу героя: уровень, остаток, порог, звание."""
    level, rest = level_for(xp_total)
    return {
        "level": level,
        "xp": rest,
        "xpNeeded": xp_needed(level),
        "xpTotal": xp_total,
        "titleIndex": title_index(level),
    }


def stat_points(amount):
    """Очки характеристики за начисленный опыт. Минимум одно за любое действие."""
    return max(1, round(amount / STAT_DIVISOR))
