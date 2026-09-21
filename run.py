#!/usr/bin/env python3
"""Запуск Life Quests.

    python run.py                      запустить сервер
    python run.py --demo               залить демо-квесты и запустить
    python run.py --demo --demo-lang en   демо на английском
    python run.py --demo-only          только залить демо-квесты

Настройки читаются из окружения: LIFE_QUESTS_DB, LIFE_QUESTS_HOST,
LIFE_QUESTS_PORT, LIFE_QUESTS_HERO.
"""

import argparse
import sys

from app import db, seed
from app.config import Config
from app.server import serve


def main(argv=None):
    parser = argparse.ArgumentParser(description="Life Quests")
    parser.add_argument("--demo", action="store_true", help="залить демо-квесты перед запуском")
    parser.add_argument("--demo-only", action="store_true", help="залить демо-квесты и выйти")
    parser.add_argument("--demo-lang", choices=db.LANGS, default="en", help="язык демо-квестов")
    args = parser.parse_args(argv)

    config = Config.load()

    if args.demo or args.demo_only:
        con, fresh = db.open_or_create(config)
        if fresh:
            print(f"База создана: {config.db_path}")
        try:
            added = seed.fill(con, args.demo_lang)
        except seed.AlreadyFilled as err:
            print(f"Демо не залито: {err}")
        else:
            print(f"Демо залито: квестов {added}")
        finally:
            con.close()

    if args.demo_only:
        return 0

    serve(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
