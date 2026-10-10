from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TZ_COLOMBIA = ZoneInfo("America/Bogota")


def a_hora_colombia(dt: datetime | None) -> str | None:
    """UTC -> texto legible en hora de Colombia: 2026-10-07 11:25:30-05:00"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ_COLOMBIA).isoformat(sep=" ", timespec="seconds")


def a_utc(dt: datetime) -> datetime:
    """Filtros de consulta: si vienen sin zona horaria se asumen hora Colombia."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_COLOMBIA)
    return dt.astimezone(timezone.utc)
