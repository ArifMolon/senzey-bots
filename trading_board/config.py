"""Configuration helpers for trading board components."""

from dataclasses import dataclass
import os


def _env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class TradingBoardConfig:
    redis_url: str
    redis_channel: str
    postgres_dsn: str
    create_tables_on_boot: bool

    @classmethod
    def from_env(cls):
        return cls(
            redis_url=os.getenv("TRADING_BOARD_REDIS_URL", "redis://localhost:6379/0"),
            redis_channel=os.getenv("TRADING_BOARD_REDIS_CHANNEL", "trading:orders"),
            postgres_dsn=os.getenv(
                "TRADING_BOARD_POSTGRES_DSN",
                "postgresql://postgres:postgres@localhost:5432/trading_board",
            ),
            create_tables_on_boot=_env_bool(
                "TRADING_BOARD_CREATE_TABLES_ON_BOOT",
                True,
            ),
        )
