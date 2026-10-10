import json
import logging
import os
import uuid
from decimal import Decimal

import paho.mqtt.client as mqtt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.crud import medicion as crud_medicion
from app.crud import sensor as crud_sensor
from app.crud import sensor_magnitud as crud_sm
from app.database.connection import SessionLocal
from app.schemas.medicion import PayloadMQTT

log = logging.getLogger("mqtt")


def procesar_payload(db: Session, raw: bytes | str) -> tuple[bool, str]:
    """Valida un mensaje MQTT y lo guarda solo si TODO es válido. Devuelve (ok, motivo)."""
    # 1) JSON
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as e:
        return False, f"JSON inválido: {e}"

    # 2) Pydantic: estructura, obligatorios, tipos, timestamp
    try:
        payload = PayloadMQTT.model_validate(data)
    except ValidationError as e:
        detalle = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
        return False, f"Estructura inválida -> {detalle}"

    # 3) ORM + lógica de negocio
    sensor = crud_sensor.get_sensor_by_codigo(db, payload.sensor_id)
    if sensor is None:
        return False, f"Sensor inexistente: '{payload.sensor_id}'"
    if not sensor.activo:
        return False, f"Sensor inactivo: '{sensor.codigo}'"

    a_guardar: list[tuple[int, Decimal]] = []
    for nombre, medida in payload.measurements.items():
        sm = crud_sm.get_by_sensor_y_magnitud(db, sensor.id, nombre)
        if sm is None:
            return False, f"Magnitud '{nombre}' no pertenece al sensor '{sensor.codigo}'"
        if medida.unit != sm.unidad:
            return False, f"Unidad incorrecta en '{nombre}': recibida '{medida.unit}', esperada '{sm.unidad}'"
        valor = Decimal(str(medida.value))
        if not (sm.valor_minimo <= valor <= sm.valor_maximo):
            return False, f"Valor fuera de rango en '{nombre}': {valor} (permitido {sm.valor_minimo} a {sm.valor_maximo})"
        a_guardar.append((sm.id, valor))

    # 4) Todo válido -> una fila por magnitud, mismo timestamp_utc
    crud_medicion.create_mediciones(db, a_guardar, payload.timestamp)
    return True, f"{len(a_guardar)} medición(es) almacenada(s) para '{sensor.codigo}' ({payload.timestamp.isoformat()})"


def _on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        log.error("No se pudo conectar al broker: %s", reason_code)
        return
    topic = os.getenv("MQTT_TOPIC")
    client.subscribe(topic)
    log.info("Conectado al broker. Suscrito a '%s'", topic)


def _on_message(client, userdata, msg):
    log.info("Mensaje recibido en '%s': %s", msg.topic, msg.payload.decode(errors="replace"))
    db = SessionLocal()
    try:
        ok, motivo = procesar_payload(db, msg.payload)
        (log.info if ok else log.warning)("%s: %s", "ACEPTADO" if ok else "RECHAZADO", motivo)
    except Exception:
        db.rollback()
        log.exception("Error inesperado procesando el mensaje")
    finally:
        db.close()


_client: mqtt.Client | None = None


def start_mqtt():
    global _client
    _client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"taller2-{uuid.uuid4().hex[:8]}")
    user = os.getenv("MQTT_USERNAME")
    if user:
        _client.username_pw_set(user, os.getenv("MQTT_PASSWORD"))
    _client.on_connect = _on_connect
    _client.on_message = _on_message
    _client.connect_async(
        os.getenv("MQTT_BROKER"), int(os.getenv("MQTT_PORT", "1883")), int(os.getenv("MQTT_KEEPALIVE", "60"))
    )
    _client.loop_start()


def stop_mqtt():
    if _client:
        _client.loop_stop()
        _client.disconnect()
