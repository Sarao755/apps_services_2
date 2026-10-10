from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import sensor as crud_sensor
from app.crud import sensor_magnitud as crud_sm
from app.database.connection import get_db
from app.schemas.sensor import SensorOut
from app.schemas.sensor_magnitud import SensorMagnitudOut

router = APIRouter(tags=["Sensores"])


@router.get("/sensores", response_model=list[SensorOut])
def listar_sensores(db: Session = Depends(get_db)):
    return crud_sensor.list_sensores(db)


@router.get("/sensores/por-codigo/{codigo}", response_model=SensorOut)
def sensor_por_codigo(codigo: str, db: Session = Depends(get_db)):
    sensor = crud_sensor.get_sensor_by_codigo(db, codigo)
    if not sensor:
        raise HTTPException(404, f"No existe un sensor con código '{codigo}'")
    return sensor


@router.get("/sensores/{sensor_id}", response_model=SensorOut)
def obtener_sensor(sensor_id: int, db: Session = Depends(get_db)):
    sensor = crud_sensor.get_sensor(db, sensor_id)
    if not sensor:
        raise HTTPException(404, f"No existe el sensor con id {sensor_id}")
    return sensor


@router.get("/sensores/{sensor_id}/magnitudes", response_model=list[SensorMagnitudOut])
def magnitudes_del_sensor(sensor_id: int, db: Session = Depends(get_db)):
    if not crud_sensor.get_sensor(db, sensor_id):
        raise HTTPException(404, f"No existe el sensor con id {sensor_id}")
    return crud_sm.list_by_sensor(db, sensor_id)
