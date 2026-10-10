from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import sensor_magnitud as crud_sm
from app.database.connection import get_db
from app.schemas.sensor_magnitud import SensorMagnitudOut

router = APIRouter(tags=["Sensor-Magnitudes"])


@router.get("/sensor-magnitudes/{sm_id}", response_model=SensorMagnitudOut)
def obtener_sensor_magnitud(sm_id: int, db: Session = Depends(get_db)):
    sm = crud_sm.get_sensor_magnitud(db, sm_id)
    if not sm:
        raise HTTPException(404, f"No existe la sensor-magnitud con id {sm_id}")
    return sm
