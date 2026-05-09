from datetime import datetime, timezone


def iso_to_timestamp(iso: str | None) -> float | None:
    """
    Convert ISO formatted date to a unix timestamp.

    Args:
        iso: The ISO date to convert

    Returns: Unix timestamp or None if provided date is falsy
    """
    if not iso:
        return None
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def timestamp_to_date(ts: float | None) -> str:
    """
    Convert a unix timestamp to a formatted date.

    Args:
        ts: The unix timestamp to convert

    Returns: Formatted date string or N/A if provided timestamp is falsy
    """
    if not ts:
        return "N/A"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
