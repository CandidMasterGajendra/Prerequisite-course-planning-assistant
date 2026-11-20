"""Load optional local credentials without overriding explicit environment values."""

from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]


def load_local_env() -> None:
    load_dotenv(ROOT / ".env", override=False)
