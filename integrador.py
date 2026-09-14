"""Cliente integrador institucional de datos meteorologicos.

Taller 1 — Integracion de datos entre aplicaciones
Curso: Aplicaciones y Servicios Web
Estudiante: Sara Yulieth Quimbayo Osorio
"""

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import requests

# =====================================================================
# 13. CONFIGURACIÓN Y CONSTANTES PRINCIPALES
# =====================================================================
URL_BASE: str = os.getenv("API_URL_BASE", "https://appsweb.quantaiot.co")
EQUIPO: str = os.getenv("EQUIPO", "sara_quimbayo")

BASE_DIR: Path = Path(__file__).resolve().parent
DATOS_DIR: Path = BASE_DIR / "datos"
SALIDA_DIR: Path = BASE_DIR / "salida"

RUTA_PROVEEDOR_A: Path = DATOS_DIR / "proveedor_a.json"
RUTA_PROVEEDOR_B: Path = DATOS_DIR / "proveedor_b.csv"
RUTA_NORMALIZADAS: Path = SALIDA_DIR / "normalizadas.json"
RUTA_REPORTE: Path = SALIDA_DIR / "reporte.json"

# Zona horaria local (Colombia UTC-5)
TZ_COLOMBIA = timezone(timedelta(hours=-5))


# =====================================================================
# 2. LECTURA DE FUENTES DE DATOS
# =====================================================================
def leer_proveedor_a(ruta: Path) -> List[Dict[str, Any]]:
    """Lee y carga el archivo JSON del Proveedor A."""
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo de Proveedor A no encontrado en: {ruta}")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
            return datos.get("records", [])
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decodificando JSON de Proveedor A: {e}")


def leer_proveedor_b(ruta: Path) -> List[Dict[str, Any]]:
    """Lee y carga el archivo CSV del Proveedor B."""
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo de Proveedor B no encontrado en: {ruta}")
    registros = []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            lector = csv.DictReader(f, delimiter=";")
            for fila in lector:
                registros.append(dict(fila))
        return registros
    except csv.Error as e:
        raise ValueError(f"Error procesando CSV de Proveedor B: {e}")


# =====================================================================
# 3. CONVERSIÓN Y NORMALIZACIÓN
# =====================================================================
def fahrenheit_a_celsius(temp_f: float) -> float:
    """Convierte grados Fahrenheit a Celsius redondeando a 2 decimales."""
    return round((temp_f - 32.0) * 5.0 / 9.0, 2)


def ms_a_kmh(velocidad_ms: float) -> float:
    """Convierte metros por segundo a kilómetros por hora redondeando a 2 decimales."""
    return round(velocidad_ms * 3.6, 2)


def normalizar_fecha_iso(cadena_fecha: str, formato_origen: Optional[str] = None) -> str:
    """Convierte y valida una cadena de fecha al estándar ISO 8601."""
    if not cadena_fecha or not str(cadena_fecha).strip():
        raise ValueError("Cadena de fecha vacía")

    cadena_limpia = str(cadena_fecha).strip()
    if formato_origen:
        dt = datetime.strptime(cadena_limpia, formato_origen)
        # Asignar zona horaria de Colombia para consistencia institucional
        dt = dt.replace(tzinfo=TZ_COLOMBIA)
        return dt.isoformat()

    # Si ya viene en formato ISO (ej. Proveedor A)
    dt = datetime.fromisoformat(cadena_limpia)
    return dt.isoformat()


def normalizar_registro_a(
    registro: Dict[str, Any], indice: int
) -> Tuple[Optional[Dict[str, Any]], Optional[str], str]:
    """Transforma un registro del Proveedor A al contrato institucional.

    Retorna: (registro_normalizado, error_normalizacion, trazabilidad_id)
    """
    rid = registro.get("provider_record_id") or f"A-{indice:04d}"

    try:
        station = registro.get("station")
        location = registro.get("location")
        measurements = registro.get("measurements")
        observed_at = registro.get("observed_at")

        if not isinstance(station, dict) or not isinstance(location, dict) or not isinstance(measurements, dict):
            return None, "Estructura anidada incompleta o inválida", rid

        ciudad = station.get("city_name")
        pais = station.get("country_code")
        lat = location.get("lat")
        lon = location.get("lon")
        temp_f = measurements.get("temperature_f")
        humedad = measurements.get("relative_humidity")
        viento_ms = measurements.get("wind_speed_ms")

        if ciudad is None or not str(ciudad).strip():
            return None, "Campo 'ciudad' ausente o vacío", rid
        if pais is None or not str(pais).strip():
            return None, "Campo 'pais' ausente o vacío", rid

        lat_f = float(lat)
        lon_f = float(lon)
        temp_f_val = float(temp_f)
        hum_val = float(humedad)
        viento_ms_val = float(viento_ms)

        fecha_iso = normalizar_fecha_iso(observed_at)

        temp_c = fahrenheit_a_celsius(temp_f_val)
        viento_kmh = ms_a_kmh(viento_ms_val)

        normalizado = {
            "ciudad": str(ciudad).strip(),
            "pais": str(pais).strip(),
            "latitud": round(lat_f, 6),
            "longitud": round(lon_f, 6),
            "temperatura_c": temp_c,
            "humedad": round(hum_val, 2),
            "viento_kmh": viento_kmh,
            "fecha_hora": fecha_iso,
            "origen": "proveedor_a",
        }
        return normalizado, None, rid

    except (ValueError, TypeError) as exc:
        return None, f"Error de conversión de tipos: {exc}", rid
    except Exception as exc:
        return None, f"Error inesperado durante la normalización: {exc}", rid


def normalizar_registro_b(
    registro: Dict[str, Any], indice: int
) -> Tuple[Optional[Dict[str, Any]], Optional[str], str]:
    """Transforma un registro del Proveedor B al contrato institucional.

    Retorna: (registro_normalizado, error_normalizacion, trazabilidad_id)
    """
    rid = registro.get("record_code") or f"B-{indice:04d}"

    try:
        ciudad = registro.get("municipality")
        pais = registro.get("country")
        lat_str = registro.get("latitude_deg")
        lon_str = registro.get("longitude_deg")
        temp_str = registro.get("temp_celsius")
        hum_str = registro.get("humidity_pct")
        viento_str = registro.get("wind_kmh")
        tiempo_str = registro.get("measurement_time")

        if ciudad is None or not str(ciudad).strip():
            return None, "Campo 'municipality' ausente o vacío", rid
        if pais is None or not str(pais).strip():
            return None, "Campo 'country' ausente o vacío", rid

        lat_f = float(lat_str)
        lon_f = float(lon_str)
        temp_c = float(temp_str)
        hum_val = float(hum_str)
        viento_kmh = float(viento_str)

        fecha_iso = normalizar_fecha_iso(tiempo_str, formato_origen="%d/%m/%Y %H:%M")

        normalizado = {
            "ciudad": str(ciudad).strip(),
            "pais": str(pais).strip(),
            "latitud": round(lat_f, 6),
            "longitud": round(lon_f, 6),
            "temperatura_c": round(temp_c, 2),
            "humedad": round(hum_val, 2),
            "viento_kmh": round(viento_kmh, 2),
            "fecha_hora": fecha_iso,
            "origen": "proveedor_b",
        }
        return normalizado, None, rid

    except (ValueError, TypeError) as exc:
        return None, f"Error de conversión de tipos: {exc}", rid
    except Exception as exc:
        return None, f"Error inesperado durante la normalización: {exc}", rid


# =====================================================================
# 4. VALIDACIÓN LOCAL
# =====================================================================
def validar_registro_local(registro: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Aplica las reglas de negocio del contrato institucional al registro normalizado.

    Retorna: (es_valido, lista_de_motivos_rechazo)
    """
    motivos: List[str] = []

    ciudad = registro.get("ciudad")
    if not isinstance(ciudad, str) or not ciudad.strip():
        motivos.append("La ciudad no puede estar vacía")

    pais = registro.get("pais")
    if not isinstance(pais, str) or not pais.strip():
        motivos.append("El país no puede estar vacío")

    latitud = registro.get("latitud")
    if latitud is None or not (-90.0 <= float(latitud) <= 90.0):
        motivos.append(f"Latitud fuera de rango [-90, 90]: {latitud}")

    longitud = registro.get("longitud")
    if longitud is None or not (-180.0 <= float(longitud) <= 180.0):
        motivos.append(f"Longitud fuera de rango [-180, 180]: {longitud}")

    temp = registro.get("temperatura_c")
    if temp is None or not isinstance(temp, (int, float)):
        motivos.append(f"Temperatura debe ser numérica: {temp}")

    humedad = registro.get("humedad")
    if humedad is None or not (0.0 <= float(humedad) <= 100.0):
        motivos.append(f"Humedad fuera de rango [0, 100]: {humedad}")

    viento = registro.get("viento_kmh")
    if viento is None or float(viento) < 0.0:
        motivos.append(f"Viento debe ser mayor o igual a 0: {viento}")

    fecha_hora = registro.get("fecha_hora")
    if not isinstance(fecha_hora, str) or not fecha_hora.strip():
        motivos.append("Fecha y hora institucional no válida")

    origen = registro.get("origen")
    if origen not in ("proveedor_a", "proveedor_b"):
        motivos.append(f"Origen no permitido por el contrato: {origen}")

    return len(motivos) == 0, motivos


# =====================================================================
# 7 Y 8. INTEGRACIÓN HTTP Y GESTIÓN DE REINTENTOS
# =====================================================================
class ClienteHTTPInstitucional:
    """Cliente HTTP para interactuar con la API meteorológica institucional."""

    def __init__(self, url_base: str, equipo: str, timeout_segundos: float = 8.0):
        self.url_base = url_base.rstrip("/")
        self.equipo = equipo
        self.timeout = timeout_segundos
        self.session = requests.Session()

    def enviar_medicion(self, medicion: Dict[str, Any]) -> Dict[str, Any]:
        """Envía una medición normalizada y válida a la API institucional.

        Implementa política de reintentos para 5xx, timeout y errores de conexión:
        1 intento inicial + hasta 2 reintentos adicionales (máximo 3 intentos).
        No reintenta errores 4xx.
        """
        endpoint = f"{self.url_base}/api/v1/mediciones"
        headers = {
            "Content-Type": "application/json",
            "X-Equipo": self.equipo,
        }

        # Filtrar estrictamente solo los campos del contrato institucional
        campos_contrato = [
            "ciudad", "pais", "latitud", "longitud",
            "temperatura_c", "humedad", "viento_kmh",
            "fecha_hora", "origen"
        ]
        payload = {k: medicion[k] for k in campos_contrato if k in medicion}

        max_intentos = 3
        ultimo_error: Optional[str] = None
        ultimo_codigo: Optional[int] = None
        ultimo_detalle: Any = None

        for intento in range(1, max_intentos + 1):
            try:
                respuesta = self.session.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                ultimo_codigo = respuesta.status_code

                try:
                    cuerpo_json = respuesta.json()
                    ultimo_detalle = cuerpo_json
                except Exception:
                    ultimo_detalle = respuesta.text

                # 201: Registro exitoso
                if respuesta.status_code == 201:
                    return {
                        "estado": "aceptado_api",
                        "status_code": 201,
                        "intentos": intento,
                        "respuesta": ultimo_detalle,
                    }

                # 4xx: Errores del cliente (no se reintentan automáticamente)
                if 400 <= respuesta.status_code < 500:
                    return {
                        "estado": "rechazado_api",
                        "status_code": respuesta.status_code,
                        "intentos": intento,
                        "respuesta": ultimo_detalle,
                    }

                # 5xx: Errores del servidor (se reintentan)
                ultimo_error = f"HTTP {respuesta.status_code} - {ultimo_detalle}"

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as req_exc:
                ultimo_error = f"Falla de comunicación ({type(req_exc).__name__}): {req_exc}"
            except Exception as exc:
                ultimo_error = f"Error no clasificado: {exc}"

            if intento < max_intentos:
                time.sleep(0.3 * (2 ** (intento - 1)))

        return {
            "estado": "error_comunicacion",
            "status_code": ultimo_codigo,
            "intentos": max_intentos,
            "error": ultimo_error,
            "respuesta": ultimo_detalle,
        }

    def consultar_mediciones(self) -> Dict[str, Any]:
        """Consulta mediante GET las mediciones registradas para el equipo."""
        endpoint = f"{self.url_base}/api/v1/mediciones"
        parametros = {"equipo": self.equipo}

        try:
            respuesta = self.session.get(endpoint, params=parametros, timeout=self.timeout)
            try:
                cuerpo = respuesta.json()
            except Exception:
                cuerpo = respuesta.text

            return {
                "status_code": respuesta.status_code,
                "exito": respuesta.status_code == 200,
                "datos": cuerpo,
            }
        except Exception as exc:
            return {
                "status_code": None,
                "exito": False,
                "error": str(exc),
            }


# =====================================================================
# 6 Y 10. GENERACIÓN DE SALIDAS Y REPORTES
# =====================================================================
def exportar_normalizadas(ruta: Path, registros_normalizados: List[Dict[str, Any]]) -> None:
    """Exporta todas las mediciones normalizadas a salida/normalizadas.json."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(registros_normalizados, f, indent=2, ensure_ascii=False)


def exportar_reporte(ruta: Path, contenido_reporte: Dict[str, Any]) -> None:
    """Exporta el reporte consolidado y trazabilidad a salida/reporte.json."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(contenido_reporte, f, indent=2, ensure_ascii=False)


# =====================================================================
# 11 Y 12. ORQUESTACIÓN DEL PROCESO COMPLETO
# =====================================================================
def procesar_integracion(
    url_base: str = URL_BASE,
    equipo: str = EQUIPO,
    ejecutar_envio: bool = True,
) -> Dict[str, Any]:
    """Ejecuta el ciclo de vida completo de lectura, normalización, validación,

    envío HTTP y generación de reportes.
    """
    print("=" * 70)
    print("INICIANDO PROCESO DE INTEGRACIÓN METEOROLÓGICA INSTITUCIONAL")
    print(f"Estudiante: Sara Yulieth Quimbayo Osorio")
    print(f"Equipo: {equipo} | URL API: {url_base}")
    print("=" * 70)

    # 1. Lectura segura de datasets
    print("\n[1/5] Leyendo datasets de origen...")
    try:
        raw_a = leer_proveedor_a(RUTA_PROVEEDOR_A)
        print(f"  -> Proveedor A cargado: {len(raw_a)} registros.")
    except Exception as e:
        print(f"  [ALERTA] No se pudo leer Proveedor A: {e}")
        raw_a = []

    try:
        raw_b = leer_proveedor_b(RUTA_PROVEEDOR_B)
        print(f"  -> Proveedor B cargado: {len(raw_b)} registros.")
    except Exception as e:
        print(f"  [ALERTA] No se pudo leer Proveedor B: {e}")
        raw_b = []

    total_procesados = len(raw_a) + len(raw_b)
    print(f"Total de registros procesados: {total_procesados}")

    # 2. Normalización
    print("\n[2/5] Normalizando registros al contrato institucional...")
    registros_para_normalizadas_json: List[Dict[str, Any]] = []
    trazabilidad: List[Dict[str, Any]] = []

    c_normalizados = 0
    c_errores_normalizacion = 0

    # Procesar Proveedor A
    for idx, raw_reg in enumerate(raw_a, start=1):
        norm, err, rid = normalizar_registro_a(raw_reg, idx)
        item_traza = {
            "trazabilidad_id": rid,
            "origen": "proveedor_a",
            "indice_fuente": idx,
        }
        if err:
            c_errores_normalizacion += 1
            item_traza["estado"] = "error_normalizacion"
            item_traza["motivo"] = err
        else:
            c_normalizados += 1
            item_traza["estado"] = "normalizado"
            item_traza["datos_normalizados"] = norm
            registros_para_normalizadas_json.append(norm)

        trazabilidad.append(item_traza)

    # Procesar Proveedor B
    for idx, raw_reg in enumerate(raw_b, start=1):
        norm, err, rid = normalizar_registro_b(raw_reg, idx)
        item_traza = {
            "trazabilidad_id": rid,
            "origen": "proveedor_b",
            "indice_fuente": idx,
        }
        if err:
            c_errores_normalizacion += 1
            item_traza["estado"] = "error_normalizacion"
            item_traza["motivo"] = err
        else:
            c_normalizados += 1
            item_traza["estado"] = "normalizado"
            item_traza["datos_normalizados"] = norm
            registros_para_normalizadas_json.append(norm)

        trazabilidad.append(item_traza)

    print(f"  -> Registros normalizados: {c_normalizados}")
    print(f"  -> Errores de normalización: {c_errores_normalizacion}")

    # Exportar evidencia normalizadas.json
    exportar_normalizadas(RUTA_NORMALIZADAS, registros_para_normalizadas_json)
    print(f"  -> Archivo generado: {RUTA_NORMALIZADAS} ({len(registros_para_normalizadas_json)} registros)")

    # 3. Validación local
    print("\n[3/5] Aplicando validación local contra reglas de negocio...")
    c_validos_local = 0
    c_rechazados_local = 0
    registros_a_enviar: List[Dict[str, Any]] = []

    for item in trazabilidad:
        if item["estado"] != "normalizado":
            continue

        norm_data = item["datos_normalizados"]
        es_valido, motivos = validar_registro_local(norm_data)
        if es_valido:
            c_validos_local += 1
            item["estado_validacion"] = "valido_localmente"
            registros_a_enviar.append(item)
        else:
            c_rechazados_local += 1
            item["estado_validacion"] = "rechazado_localmente"
            item["motivos_rechazo_local"] = motivos

    print(f"  -> Registros válidos localmente: {c_validos_local}")
    print(f"  -> Registros rechazados localmente: {c_rechazados_local}")

    # 4. Integración HTTP con la API institucional
    c_enviados = 0
    c_aceptados_api = 0
    c_rechazados_api = 0
    c_errores_comunicacion = 0
    cliente_api = ClienteHTTPInstitucional(url_base=url_base, equipo=equipo)

    if ejecutar_envio and registros_a_enviar:
        print(f"\n[4/5] Enviando {len(registros_a_enviar)} mediciones válidas a la API institucional...")
        for item in registros_a_enviar:
            medicion = item["datos_normalizados"]
            c_enviados += 1
            res_envio = cliente_api.enviar_medicion(medicion)

            estado_res = res_envio["estado"]
            item["resultado_api"] = res_envio

            if estado_res == "aceptado_api":
                c_aceptados_api += 1
            elif estado_res == "rechazado_api":
                c_rechazados_api += 1
            else:
                c_errores_comunicacion += 1

        print(f"  -> Envíos completados:")
        print(f"     Aceptados por API: {c_aceptados_api}")
        print(f"     Rechazados por API: {c_rechazados_api}")
        print(f"     Errores de comunicación: {c_errores_comunicacion}")
    else:
        print("\n[4/5] Envíos HTTP omitidos o no hay registros válidos.")

    # 5. Consulta final GET a la API
    print("\n[5/5] Realizando consulta de verificación final (GET /api/v1/mediciones)...")
    consulta_final = cliente_api.consultar_mediciones()
    print(f"  -> Código de respuesta GET: {consulta_final.get('status_code')}")

    # Consolidar reporte final
    reporte_final = {
        "metadatos": {
            "estudiante": "Sara Yulieth Quimbayo Osorio",
            "equipo": equipo,
            "url_base": url_base,
            "fecha_ejecucion": datetime.now(TZ_COLOMBIA).isoformat(),
        },
        "resumen": {
            "registros_procesados": total_procesados,
            "registros_normalizados": c_normalizados,
            "errores_normalizacion": c_errores_normalizacion,
            "registros_validos_localmente": c_validos_local,
            "registros_rechazados_localmente": c_rechazados_local,
            "registros_enviados": c_enviados,
            "registros_aceptados_por_api": c_aceptados_api,
            "registros_rechazados_por_api": c_rechazados_api,
            "errores_de_comunicacion": c_errores_comunicacion,
        },
        "consulta_verificacion_api": consulta_final,
        "trazabilidad": trazabilidad,
    }

    exportar_reporte(RUTA_REPORTE, reporte_final)
    print(f"\nReporte final generado exitosamente en: {RUTA_REPORTE}")
    print("=" * 70)
    print("PROCESO FINALIZADO CON ÉXITO")
    print("=" * 70)

    return reporte_final


def main():
    """Función principal de entrada."""
    try:
        procesar_integracion()
    except KeyboardInterrupt:
        print("\nEjecución interrumpida por el usuario.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[ERROR NO CONTROLADO EVITADO]: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
