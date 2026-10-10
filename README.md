# Taller 2 — API IoT (FastAPI + MQTT + PostgreSQL)

## 1. Información general
- **Proyecto:** API para adquisición, validación y consulta de datos IoT
- **Integrantes:** [COMPLETAR]
- **Asignatura:** Aplicaciones y Servicios Web
- **Fecha:** [COMPLETAR]
- **Sensor asignado (codigo):** [COMPLETAR]
- **Tópico MQTT:** `iot/sensors/[CODIGO]/data` en `emqx.coriotlab.co`

## 2. Descripción del sistema
**Problema:** recibir mediciones de un sensor IoT por MQTT, validarlas, guardarlas en PostgreSQL solo si son válidas y consultarlas por HTTP.

**Arquitectura:** `Sensor → Broker MQTT → mqtt/client.py (Pydantic + ORM) → PostgreSQL ← crud/ ← api/ (FastAPI)`

**Magnitudes y unidades recibidas:** [COMPLETAR: tabla magnitud / unidad / rango]

**Payload real del sensor:**
```json
[PEGAR UN PAYLOAD REAL]
```

## 3. Configuración del entorno
```bash
python -m venv venv
venv\Scripts\activate          # Windows  (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env         # y completar con los datos del docente
uvicorn app.main:app --reload
```
Variables requeridas (sin valores): `MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, MQTT_USERNAME, MQTT_PASSWORD, MQTT_KEEPALIVE, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD`.
Documentación interactiva: `http://127.0.0.1:8000/docs`

## 4. Base de datos
Conexión por variables de entorno (`app/database/connection.py`). Tablas según `data-model.md`:
`sensores` (1:N) `sensor_magnitudes` (1:N) `mediciones`. FKs con `ON DELETE RESTRICT`.
La aplicación **solo lee** sensores y magnitudes; **solo inserta** en `mediciones`.

## 5. Organización del código
| Carpeta | Función |
|---|---|
| `schemas/` | Modelos Pydantic: validación del payload MQTT y formato de las respuestas |
| `models/` | Modelos SQLAlchemy ORM (tablas y claves foráneas) |
| `crud/` | Acceso a datos (consultas; insert solo en `mediciones`) |
| `api/` | Endpoints FastAPI y códigos HTTP |
| `mqtt/` | Cliente suscriptor y proceso de validación/almacenamiento |
| `database/` | Engine, sesión y `get_db` |
| `utils/` | Conversión UTC → hora Colombia |

## 6. Endpoints
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/sensores` | Lista de sensores |
| GET | `/sensores/{id}` | Sensor por id (404 si no existe) |
| GET | `/sensores/por-codigo/{codigo}` | Sensor por código |
| GET | `/sensores/{id}/magnitudes` | Magnitudes de un sensor |
| GET | `/sensor-magnitudes/{id}` | Sensor-magnitud por id |
| GET | `/mediciones/{id}` | Medición por id |
| GET | `/sensores/{id}/mediciones` | Histórico. Filtros: `magnitud`, `desde`, `hasta`, `limit` (combinables) |
| GET | `/sensores/{id}/ultima-medicion` | Medición más reciente (una por magnitud). Filtro opcional `magnitud` |

Fechas: se guardan en UTC y las respuestas GET se muestran en hora de Colombia. `desde`/`hasta` sin zona horaria se interpretan como hora Colombia.

## 7. Evidencias de funcionamiento
Carpeta `evidencias/`.

| # | Prueba | Entrada | Resultado / HTTP | Archivo y función | Evidencia |
|---|---|---|---|---|---|
| 1 | Recepción MQTT | [COMPLETAR] | [COMPLETAR] | `mqtt/client.py` → `_on_message` | [COMPLETAR] |
| 2 | Medición válida | [COMPLETAR] | Registro en PostgreSQL | `mqtt/client.py` → `procesar_payload`, `crud/medicion.py` → `create_mediciones` | [COMPLETAR] |
| 3 | Sensor inexistente | [COMPLETAR] | Rechazado | `mqtt/client.py` → `procesar_payload` | [COMPLETAR] |
| 4 | Unidad incorrecta | [COMPLETAR] | Rechazado | `mqtt/client.py` → `procesar_payload` | [COMPLETAR] |
| 5 | Tipo de dato incorrecto | [COMPLETAR] | Rechazado | `schemas/medicion.py` → `MedidaMQTT` | [COMPLETAR] |
| 6 | Magnitud incorrecta | [COMPLETAR] | Rechazado | `mqtt/client.py` → `procesar_payload` | [COMPLETAR] |
| 7 | Timestamp inválido | [COMPLETAR] | Rechazado | `schemas/medicion.py` → `PayloadMQTT._parse_timestamp` | [COMPLETAR] |
| 8 | Consulta por ID existente | [COMPLETAR] | 200 | `api/medicion.py` → `obtener_medicion` | [COMPLETAR] |
| 9 | Consulta por ID inexistente | [COMPLETAR] | 404 | `api/medicion.py` → `obtener_medicion` | [COMPLETAR] |
| 10 | Consulta histórica | [COMPLETAR] | 200 | `api/medicion.py` → `historico` | [COMPLETAR] |
| 11 | Rango de fechas | [COMPLETAR] | 200 | `crud/medicion.py` → `list_mediciones` | [COMPLETAR] |
| 12 | `desde` > `hasta` | [COMPLETAR] | 400 | `api/medicion.py` → `historico` | [COMPLETAR] |
| 13 | Validación HTTP incorrecta | [COMPLETAR] | 422 | FastAPI (`Query(ge=1)`, tipos de ruta) | [COMPLETAR] |
| 14 | Última medición | [COMPLETAR] | 200 | `crud/medicion.py` → `get_ultima_medicion` | [COMPLETAR] |
| 15 | Últimas N (`limit`) | [COMPLETAR] | 200 | `crud/medicion.py` → `list_mediciones` | [COMPLETAR] |
| 16 | Filtro por magnitud | [COMPLETAR] | 200 | `crud/medicion.py` → `_query_sensor` | [COMPLETAR] |
| 17 | Claves foráneas | — | — | `models/sensor_magnitud.py`, `models/medicion.py` | [COMPLETAR] |
| 18 | Separación de responsabilidades | — | — | Estructura `app/` (sección 5) | — |

Las pruebas 3–7 se pueden reproducir con: `python -m scripts.probar_validaciones [CODIGO]`

## 8. Control de versiones
- Repositorio: [COMPLETAR]
- Evidencia de commits: [COMPLETAR]
- Aporte de cada integrante:
  - [Integrante 1]: [COMPLETAR]
  - [Integrante 2]: [COMPLETAR]

## 9. Conclusiones
- Aprendizajes: [COMPLETAR]
- Dificultades: [COMPLETAR]
- Soluciones aplicadas: [COMPLETAR]
