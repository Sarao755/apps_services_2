from sqlalchemy.orm import Session

from app.models.sensor_magnitud import SensorMagnitud


def get_sensor_magnitud(db: Session, sm_id: int) -> SensorMagnitud | None:
    return db.get(SensorMagnitud, sm_id)


def list_by_sensor(db: Session, sensor_id: int) -> list[SensorMagnitud]:
    return db.query(SensorMagnitud).filter(SensorMagnitud.sensor_id == sensor_id).order_by(SensorMagnitud.id).all()


def get_by_sensor_y_magnitud(db: Session, sensor_id: int, magnitud: str) -> SensorMagnitud | None:
    return (
        db.query(SensorMagnitud)
        .filter(SensorMagnitud.sensor_id == sensor_id, SensorMagnitud.magnitud == magnitud)
        .first()
    )
