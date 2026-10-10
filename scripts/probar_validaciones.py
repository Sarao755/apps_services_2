"""Evidencias 3-7 (y rango): envía payloads inválidos a procesar_payload y verifica que NO se guarde nada.
Uso (desde la raíz del proyecto):  python -m scripts.probar_validaciones TU-CODIGO
"""
import json
import sys

from app.database.connection import SessionLocal
import app.models  # noqa: F401
from app.crud import sensor as crud_sensor
from app.crud import sensor_magnitud as crud_sm
from app.models.medicion import Medicion
from app.mqtt.client import procesar_payload

codigo = sys.argv[1]
db = SessionLocal()
sensor = crud_sensor.get_sensor_by_codigo(db, codigo)
sm = crud_sm.list_by_sensor(db, sensor.id)[0]
TS = "2026-10-09T15:00:00Z"


def payload(sensor_id=codigo, ts=TS, mag=sm.magnitud, value=float(sm.valor_minimo), unit=sm.unidad):
    return json.dumps({"sensor_id": sensor_id, "timestamp": ts, "measurements": {mag: {"value": value, "unit": unit}}})


casos = {
    "3. Sensor inexistente": payload(sensor_id="NO-EXISTE-999"),
    "4. Unidad incorrecta": payload(unit="UNIDAD_MALA"),
    "5. Tipo de dato incorrecto": payload(value="abc"),
    "6. Magnitud incorrecta": payload(mag="magnitud_falsa"),
    "7. Timestamp inválido": payload(ts="ayer por la tarde"),
    "Extra. Valor fuera de rango": payload(value=float(sm.valor_maximo) + 1000),
}

antes = db.query(Medicion).count()
for nombre, raw in casos.items():
    ok, motivo = procesar_payload(db, raw)
    print(f"{nombre}\n  entrada : {raw}\n  resultado: {'ACEPTADO' if ok else 'RECHAZADO'} -> {motivo}\n")
despues = db.query(Medicion).count()
print(f"Mediciones antes: {antes} | después: {despues} | {'OK, no se guardó nada' if antes == despues else 'ERROR: se guardó algo'}")
db.close()
