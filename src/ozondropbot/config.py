from dataclasses import dataclass
import os


@dataclass(slots=True)
class Config:
    bot_token: str
    database_path: str = "ozondropbot.sqlite3"
    default_check_interval_minutes: int = 30
    free_products_limit: int = 10
    default_drop_threshold_percent: float = 5.0
    drops_feed_threshold_percent: float = 10.0
    drops_feed_limit: int = 10

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("BOT_TOKEN", "")
        if not token:
            raise RuntimeError("BOT_TOKEN is required")
        return cls(
            bot_token=token,
            database_path=os.getenv("DATABASE_PATH", "ozondropbot.sqlite3"),
            default_check_interval_minutes=int(os.getenv("CHECK_INTERVAL_MINUTES", "30")),
        )
