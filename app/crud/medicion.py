from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session, selectinload

from app.models.medicion import Medicion
from app.models.sensor_magnitud import SensorMagnitud


def create_mediciones(db: Session, items: list[tuple[int, Decimal]], timestamp_utc: datetime) -> list[Medicion]:
    """Guarda todas las magnitudes de un payload en una sola transacción (mismo timestamp_utc)."""
    objs = [Medicion(sensor_magnitud_id=sm_id, valor=valor, timestamp_utc=timestamp_utc) for sm_id, valor in items]
    try:
        db.add_all(objs)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return objs


def get_medicion(db: Session, medicion_id: int) -> Medicion | None:
    return (
        db.query(Medicion)
        .options(selectinload(Medicion.sensor_magnitud).selectinload(SensorMagnitud.sensor))
        .filter(Medicion.id == medicion_id)
        .first()
    )


def _query_sensor(db: Session, sensor_id: int, magnitud: str | None = None):
    q = (
        db.query(Medicion)
        .join(SensorMagnitud, Medicion.sensor_magnitud_id == SensorMagnitud.id)
        .options(selectinload(Medicion.sensor_magnitud).selectinload(SensorMagnitud.sensor))
        .filter(SensorMagnitud.sensor_id == sensor_id)
    )
    if magnitud:
        q = q.filter(SensorMagnitud.magnitud == magnitud)
    return q


def list_mediciones(
    db: Session,
    sensor_id: int,
    magnitud: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limit: int | None = None,
) -> list[Medicion]:
    q = _query_sensor(db, sensor_id, magnitud)
    if desde:
        q = q.filter(Medicion.timestamp_utc >= desde)
    if hasta:
        q = q.filter(Medicion.timestamp_utc <= hasta)
    q = q.order_by(Medicion.timestamp_utc.desc(), Medicion.id.desc())  # más recientes primero
    if limit:
        q = q.limit(limit)
    return q.all()


def get_ultima_medicion(db: Session, sensor_id: int, magnitud: str | None = None) -> list[Medicion]:
    """Mediciones del payload más reciente (una por magnitud, mismo timestamp)."""
    base = _query_sensor(db, sensor_id, magnitud)
    ultima = base.order_by(Medicion.timestamp_utc.desc(), Medicion.id.desc()).first()
    if ultima is None:
        return []
    return base.filter(Medicion.timestamp_utc == ultima.timestamp_utc).order_by(Medicion.id).all()
