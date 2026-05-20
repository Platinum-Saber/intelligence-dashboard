"""
Sri Lanka monsoon calendar and seasonal context for weather alerts.

Southwest monsoon (Yala): May–September — affects western, southern, and central districts.
Northeast monsoon (Maha): October–January — affects northern and eastern districts.
"""

MONSOON_CALENDAR: dict[str, dict] = {
    "southwest": {
        "months": [5, 6, 7, 8, 9],
        "districts": ["Western", "Southern", "Sabaragamuwa", "Central", "North Western", "Uva"],
    },
    "northeast": {
        "months": [10, 11, 12, 1],
        "districts": ["Northern", "Eastern", "North Central"],
    },
}


def is_monsoon_season(location_name: str, month: int) -> bool:
    for season in MONSOON_CALENDAR.values():
        if month in season["months"] and location_name in season["districts"]:
            return True
    return False


def seasonal_context(location_name: str, month: int) -> str:
    """
    Returns a human-readable seasonal context string to append to weather alert messages.
    Helps the procurement team distinguish routine monsoon peaks from anomalous events.
    """
    if is_monsoon_season(location_name, month):
        season_name = None
        for name, data in MONSOON_CALENDAR.items():
            if month in data["months"] and location_name in data["districts"]:
                season_name = "Southwest" if name == "southwest" else "Northeast"
                break
        return (
            f"[Seasonal context: rainfall elevated during expected {season_name} Monsoon period — "
            f"monitor for above-average intensity]"
        )
    return (
        f"[Seasonal context: ANOMALOUS — flood/drought risk elevated outside normal monsoon window. Investigate.]"
    )
