from datetime import datetime, timezone


def iso_to_timestamp(iso: str | None) -> float | None:
    if not iso:
        return None
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def timestamp_to_date(ts: float | None) -> str:
    if not ts:
        return "no due date"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
