"""Suite de pruebas unitarias automatizadas para el integrador meteorológico.

Cubre las 5 categorías exigidas en la especificación:
1. Transformación correcta.
2. Conversión de unidades.
3. Registro válido localmente.
4. Registro inválido localmente.
5. Casos límite seleccionados (límites de rango, errores de normalización y reintentos HTTP).

Comando de ejecución:
    pytest
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import requests

# Asegurar que el módulo raíz sea visible para pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrador import (
    fahrenheit_a_celsius,
    ms_a_kmh,
    normalizar_fecha_iso,
    normalizar_registro_a,
    normalizar_registro_b,
    validar_registro_local,
    ClienteHTTPInstitucional,
)


# =====================================================================
# 1. PRUEBAS DE TRANSFORMACIÓN CORRECTA
# =====================================================================
def test_transformacion_correcta_proveedor_a():
    """Verifica la transformación correcta de un registro del Proveedor A."""
    muestra_a = {
        "provider_record_id": "A-0001",
        "station": {
            "code": "STA-02",
            "city_name": "Medellin",
            "country_code": "CO",
        },
        "location": {
            "lat": 6.242282,
            "lon": -75.595933,
        },
        "measurements": {
            "temperature_f": 68.0,       # 68°F = 20.0°C
            "relative_humidity": 75.5,
            "wind_speed_ms": 10.0,       # 10 m/s = 36.0 km/h
        },
        "observed_at": "2026-09-01T12:00:00-05:00",
        "source": "weather_provider_a",
    }

    norm, err, rid = normalizar_registro_a(muestra_a, 1)

    assert err is None
    assert rid == "A-0001"
    assert norm["ciudad"] == "Medellin"
    assert norm["pais"] == "CO"
    assert norm["latitud"] == 6.242282
    assert norm["longitud"] == -75.595933
    assert norm["temperatura_c"] == 20.0
    assert norm["humedad"] == 75.5
    assert norm["viento_kmh"] == 36.0
    assert "2026-09-01T12:00:00" in norm["fecha_hora"]
    assert norm["origen"] == "proveedor_a"


def test_transformacion_correcta_proveedor_b():
    """Verifica la transformación correcta de un registro del Proveedor B."""
    muestra_b = {
        "record_code": "B-0001",
        "municipality": "Bogota",
        "country": "CO",
        "latitude_deg": "4.711000",
        "longitude_deg": "-74.072100",
        "temp_celsius": "18.5",
        "humidity_pct": "62.0",
        "wind_kmh": "14.2",
        "measurement_time": "01/09/2026 14:30",
        "origin_code": "PB",
    }

    norm, err, rid = normalizar_registro_b(muestra_b, 1)

    assert err is None
    assert rid == "B-0001"
    assert norm["ciudad"] == "Bogota"
    assert norm["pais"] == "CO"
    assert norm["latitud"] == 4.711
    assert norm["longitud"] == -74.0721
    assert norm["temperatura_c"] == 18.5
    assert norm["humedad"] == 62.0
    assert norm["viento_kmh"] == 14.2
    assert "2026-09-01T14:30:00" in norm["fecha_hora"]
    assert norm["origen"] == "proveedor_b"


# =====================================================================
# 2. PRUEBAS DE CONVERSIÓN DE UNIDADES
# =====================================================================
def test_conversion_unidades_temperatura():
    """Verifica la conversión de Fahrenheit a Celsius para puntos clave."""
    assert fahrenheit_a_celsius(32.0) == 0.0     # Punto de congelación del agua
    assert fahrenheit_a_celsius(212.0) == 100.0  # Punto de ebullición
    assert fahrenheit_a_celsius(66.1) == 18.94   # Caso real dataset A-0001
    assert fahrenheit_a_celsius(-40.0) == -40.0  # Escala idéntica


def test_conversion_unidades_viento():
    """Verifica la conversión de velocidad de m/s a km/h."""
    assert ms_a_kmh(0.0) == 0.0
    assert ms_a_kmh(10.0) == 36.0
    assert ms_a_kmh(8.47) == 30.49               # Caso real dataset A-0001
    assert ms_a_kmh(2.76) == 9.94


# =====================================================================
# 3. PRUEBA DE REGISTRO VÁLIDO LOCALMENTE
# =====================================================================
def test_registro_valido_local():
    """Verifica que un registro con valores conformes supera la validación local."""
    registro = {
        "ciudad": "Cali",
        "pais": "CO",
        "latitud": 3.4516,
        "longitud": -76.5320,
        "temperatura_c": 24.5,
        "humedad": 70.0,
        "viento_kmh": 12.0,
        "fecha_hora": "2026-09-01T10:00:00-05:00",
        "origen": "proveedor_a",
    }

    es_valido, motivos = validar_registro_local(registro)
    assert es_valido is True
    assert len(motivos) == 0


# =====================================================================
# 4. PRUEBA DE REGISTROS INVÁLIDOS LOCALMENTE
# =====================================================================
@pytest.mark.parametrize(
    "campo,valor_invalido,motivo_esperado",
    [
        ("humedad", 108.4, "Humedad fuera de rango"),       # Análogo a A-0015
        ("latitud", 95.245, "Latitud fuera de rango"),      # Análogo a A-0031
        ("longitud", -195.0, "Longitud fuera de rango"),    # Análogo a A-0175
        ("viento_kmh", -8.64, "Viento debe ser mayor"),     # Análogo a A-0088
        ("ciudad", "", "La ciudad no puede"),
        ("pais", "   ", "El país no puede"),
        ("origen", "proveedor_invalido", "Origen no permitido"),
    ],
)
def test_registro_invalido_rechazos_especificos(campo, valor_invalido, motivo_esperado):
    """Verifica que los registros que violan las reglas de negocio sean rechazados."""
    registro_base = {
        "ciudad": "Medellin",
        "pais": "CO",
        "latitud": 6.25,
        "longitud": -75.56,
        "temperatura_c": 22.0,
        "humedad": 50.0,
        "viento_kmh": 10.0,
        "fecha_hora": "2026-09-01T08:00:00-05:00",
        "origen": "proveedor_a",
    }
    registro_base[campo] = valor_invalido

    es_valido, motivos = validar_registro_local(registro_base)
    assert es_valido is False
    assert any(motivo_esperado in m for m in motivos)


# =====================================================================
# 5. CASOS LÍMITE (BOUNDARY CASES) Y RESILIENCIA
# =====================================================================
def test_caso_limite_fronteras_validas():
    """Verifica los valores extremos exactos permitidos por el contrato."""
    registro_frontera = {
        "ciudad": "Polo Norte",
        "pais": "XX",
        "latitud": 90.0,             # Límite superior exacto
        "longitud": -180.0,          # Límite inferior exacto
        "temperatura_c": -15.0,
        "humedad": 0.0,              # Humedad mínima
        "viento_kmh": 0.0,           # Viento en calma
        "fecha_hora": "2026-09-01T00:00:00-05:00",
        "origen": "proveedor_b",
    }
    es_valido, motivos = validar_registro_local(registro_frontera)
    assert es_valido is True
    assert len(motivos) == 0

    registro_frontera_opuesta = {
        "ciudad": "Polo Sur",
        "pais": "XX",
        "latitud": -90.0,            # Límite inferior exacto
        "longitud": 180.0,           # Límite superior exacto
        "temperatura_c": 45.0,
        "humedad": 100.0,            # Humedad máxima
        "viento_kmh": 150.0,
        "fecha_hora": "2026-09-01T00:00:00-05:00",
        "origen": "proveedor_a",
    }
    es_valido2, motivos2 = validar_registro_local(registro_frontera_opuesta)
    assert es_valido2 is True
    assert len(motivos2) == 0


def test_caso_limite_error_normalizacion_datos_corruptos():
    """Verifica que registros con datos no convertibles se clasifiquen como error de normalización."""
    # Proveedor A con temperatura "N/A" (como A-0082)
    reg_corrupto_a = {
        "provider_record_id": "A-0082",
        "station": {"city_name": "Medellin", "country_code": "CO"},
        "location": {"lat": 6.25, "lon": -75.56},
        "measurements": {"temperature_f": "N/A", "relative_humidity": 50, "wind_speed_ms": 5},
        "observed_at": "2026-09-01T00:00:00-05:00",
    }
    norm_a, err_a, _ = normalizar_registro_a(reg_corrupto_a, 82)
    assert norm_a is None
    assert "Error de conversión de tipos" in err_a

    # Proveedor B con fecha mal formada (como B-0171)
    reg_corrupto_b = {
        "record_code": "B-0171",
        "municipality": "Medellin",
        "country": "CO",
        "latitude_deg": "6.25",
        "longitude_deg": "-75.56",
        "temp_celsius": "20.0",
        "humidity_pct": "50.0",
        "wind_kmh": "10.0",
        "measurement_time": "31/13/2026 28:75",
        "origin_code": "PB",
    }
    norm_b, err_b, _ = normalizar_registro_b(reg_corrupto_b, 171)
    assert norm_b is None
    assert "Error de conversión de tipos" in err_b


def test_cliente_http_politica_reintentos_5xx_y_agotamiento():
    """Simula errores 500 del servidor verificando que se ejecutan hasta 3 intentos antes de reportar error."""
    cliente = ClienteHTTPInstitucional(url_base="https://mock-api.local", equipo="equipo_test", timeout_segundos=0.1)

    medicion_dummy = {
        "ciudad": "Medellin",
        "pais": "CO",
        "latitud": 6.25,
        "longitud": -75.56,
        "temperatura_c": 21.0,
        "humedad": 55.0,
        "viento_kmh": 10.0,
        "fecha_hora": "2026-09-01T00:00:00-05:00",
        "origen": "proveedor_a",
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.json.return_value = {"detail": "Servicio temporalmente saturado"}

    with patch.object(cliente.session, "post", return_value=mock_resp) as mock_post:
        with patch("time.sleep") as mock_sleep:
            resultado = cliente.enviar_medicion(medicion_dummy)

    # Debe haber ejecutado exactamente 3 intentos (1 inicial + 2 reintentos)
    assert mock_post.call_count == 3
    assert mock_sleep.call_count == 2
    assert resultado["estado"] == "error_comunicacion"
    assert resultado["intentos"] == 3
    assert resultado["status_code"] == 503


def test_cliente_http_sin_reintento_para_errores_4xx():
    """Verifica que los errores 4xx (como 400 o 422) NO se reintentan y retornan inmediatamente."""
    cliente = ClienteHTTPInstitucional(url_base="https://mock-api.local", equipo="equipo_test", timeout_segundos=0.1)

    medicion_dummy = {
        "ciudad": "Medellin",
        "pais": "CO",
        "latitud": 6.25,
        "longitud": -75.56,
        "temperatura_c": 21.0,
        "humedad": 55.0,
        "viento_kmh": 10.0,
        "fecha_hora": "2026-09-01T00:00:00-05:00",
        "origen": "proveedor_a",
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"detail": "Equipo no autorizado"}

    with patch.object(cliente.session, "post", return_value=mock_resp) as mock_post:
        resultado = cliente.enviar_medicion(medicion_dummy)

    # Solo 1 intento para errores 4xx
    assert mock_post.call_count == 1
    assert resultado["estado"] == "rechazado_api"
    assert resultado["status_code"] == 400
