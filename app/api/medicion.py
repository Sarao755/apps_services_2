from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud import medicion as crud_medicion
from app.crud import sensor as crud_sensor
from app.crud import sensor_magnitud as crud_sm
from app.database.connection import get_db
from app.schemas.medicion import MedicionOut, medicion_a_schema
from app.utils.tiempo import a_utc

router = APIRouter(tags=["Mediciones"])


def _validar_sensor_y_magnitud(db: Session, sensor_id: int, magnitud: str | None):
    if not crud_sensor.get_sensor(db, sensor_id):
        raise HTTPException(404, f"No existe el sensor con id {sensor_id}")
    if magnitud and not crud_sm.get_by_sensor_y_magnitud(db, sensor_id, magnitud):
        raise HTTPException(404, f"El sensor {sensor_id} no tiene la magnitud '{magnitud}'")


@router.get("/mediciones/{medicion_id}", response_model=MedicionOut)
def obtener_medicion(medicion_id: int, db: Session = Depends(get_db)):
    m = crud_medicion.get_medicion(db, medicion_id)
    if not m:
        raise HTTPException(404, f"No existe la medición con id {medicion_id}")
    return medicion_a_schema(m)


@router.get("/sensores/{sensor_id}/mediciones", response_model=list[MedicionOut])
def historico(
    sensor_id: int,
    magnitud: str | None = None,
    desde: datetime | None = Query(None, description="ISO 8601. Sin zona horaria = hora Colombia"),
    hasta: datetime | None = Query(None, description="ISO 8601. Sin zona horaria = hora Colombia"),
    limit: int | None = Query(None, ge=1, le=1000, description="Últimas N mediciones"),
    db: Session = Depends(get_db),
):
    _validar_sensor_y_magnitud(db, sensor_id, magnitud)
    desde_utc = a_utc(desde) if desde else None
    hasta_utc = a_utc(hasta) if hasta else None
    if desde_utc and hasta_utc and desde_utc > hasta_utc:
        raise HTTPException(400, "El parámetro 'desde' no puede ser mayor que 'hasta'")
    mediciones = crud_medicion.list_mediciones(db, sensor_id, magnitud, desde_utc, hasta_utc, limit)
    return [medicion_a_schema(m) for m in mediciones]


@router.get("/sensores/{sensor_id}/ultima-medicion", response_model=list[MedicionOut])
def ultima_medicion(sensor_id: int, magnitud: str | None = None, db: Session = Depends(get_db)):
    _validar_sensor_y_magnitud(db, sensor_id, magnitud)
    mediciones = crud_medicion.get_ultima_medicion(db, sensor_id, magnitud)
    if not mediciones:
        raise HTTPException(404, f"El sensor {sensor_id} aún no tiene mediciones")
    return [medicion_a_schema(m) for m in mediciones]
