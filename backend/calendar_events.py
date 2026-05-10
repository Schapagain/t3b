import os
import requests
from datetime import date, datetime
from icalendar import Calendar

CALENDAR_URL = os.getenv("GOOGLE_CALENDAR_URL")


def _to_date(dt) -> date:
    """
    Normalize a datetime or date value to a date.

    Args:
        dt: A datetime or date object.

    Returns:
        A date object.
    """
    return dt.date() if isinstance(dt, datetime) else dt


def get_named_events(event_name: str) -> list[dict]:
    """
    Get all future events from the calendar matching the given title.

    Args:
        event_name: the title of the event to retrieve

    Returns:
        List of dicts with start and end date keys for each matched future event
    """
    if not CALENDAR_URL:
        raise EnvironmentError("GOOGLE_CALENDAR_URL not configured.")

    response = requests.get(CALENDAR_URL)
    cal = Calendar.from_ical(response.content)
    today = date.today()

    events = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        summary = str(component.get("SUMMARY", ""))
        if summary.lower() != event_name.lower():
            continue

        start = _to_date(component.decoded("dtstart"))
        end = _to_date(component.decoded("dtend"))

        if end >= today:
            events.append({"start": start, "end": end})

    return events
