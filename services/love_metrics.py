"""Record and summarize how often a user remembers their partner."""

from datetime import datetime, timedelta, timezone

from repositories import love_metrics

PERIODS = {
    "Hour": (timedelta(hours=1), 5),
    "Day": (timedelta(days=1), 20),
    "Week": (timedelta(days=7), 100),
    "Month": (timedelta(days=30), 400),
    "Year": (timedelta(days=365), 5000),
}


def remember(user_id: int) -> None:
    love_metrics.insert_reminder(user_id, datetime.now(timezone.utc).isoformat())


def summary(user_id: int) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    return {
        label: love_metrics.count_since(user_id, (now - duration).isoformat())
        for label, (duration, _) in PERIODS.items()
    }