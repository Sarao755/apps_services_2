from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from app.utils.tiempo import a_hora_colombia


class SensorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    categoria: str
    ubicacion: str
    activo: bool
    fecha_registro: datetime

    @field_serializer("fecha_registro")
    def _fecha_local(self, v: datetime) -> str:
        return a_hora_colombia(v)
