"""Настройки. Значения берутся из окружения, в коде только умолчания."""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ENV_PREFIX = "LIFE_QUESTS_"


def _env(name, default):
    return os.environ.get(ENV_PREFIX + name, default)


def _env_int(name, default):
    raw = _env(name, None)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as err:
        raise SystemExit(f"{ENV_PREFIX}{name} должно быть числом, получено {raw!r}") from err


@dataclass(frozen=True)
class Config:
    db_path: Path
    schema_path: Path
    static_dir: Path
    host: str
    port: int
    hero_name: str

    @classmethod
    def load(cls):
        return cls(
            db_path=Path(_env("DB", ROOT / "life_quests.db")).resolve(),
            schema_path=ROOT / "schema.sql",
            static_dir=ROOT / "static",
            host=_env("HOST", "127.0.0.1"),
            port=_env_int("PORT", 8000),
            hero_name=_env("HERO", "Герой"),
        )

    @property
    def url(self):
        return f"http://{self.host}:{self.port}"
