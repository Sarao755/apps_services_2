import math
from datetime import datetime, timezone
from typing import Union

from pydantic import BaseModel, StrictFloat, StrictInt, StrictStr, field_validator

from app.models.medicion import Medicion
from app.utils.tiempo import a_hora_colombia

Numero = Union[StrictInt, StrictFloat]  # rechaza "24.6" (texto) y true/false


# ---------- Payload que llega por MQTT ----------
class MedidaMQTT(BaseModel):
    value: Numero
    unit: StrictStr

    @field_validator("value")
    @classmethod
    def _finito(cls, v):
        if not math.isfinite(v):
            raise ValueError("el valor debe ser un número finito")
        return v


class PayloadMQTT(BaseModel):
    sensor_id: StrictStr
    timestamp: datetime
    measurements: dict[str, MedidaMQTT]

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp(cls, v):
        if not isinstance(v, str):
            raise ValueError("timestamp debe ser un texto ISO 8601")
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("formato de timestamp inválido (se espera ISO 8601)")
        if dt.tzinfo is None:  # el sensor publica en UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @field_validator("measurements")
    @classmethod
    def _no_vacio(cls, v):
        if not v:
            raise ValueError("measurements no puede estar vacío")
        return v


# ---------- Respuesta de la API ----------
class MedicionOut(BaseModel):
    id: int
    sensor_id: int
    sensor_codigo: str
    magnitud: str
    unidad: str
    valor: float
    timestamp_local: str  # hora Colombia
    fecha_recepcion_local: str  # hora Colombia


def medicion_a_schema(m: Medicion) -> MedicionOut:
    sm = m.sensor_magnitud
    return MedicionOut(
        id=m.id,
        sensor_id=sm.sensor_id,
        sensor_codigo=sm.sensor.codigo,
        magnitud=sm.magnitud,
        unidad=sm.unidad,
        valor=float(m.valor),
        timestamp_local=a_hora_colombia(m.timestamp_utc),
        fecha_recepcion_local=a_hora_colombia(m.fecha_recepcion),
    )
