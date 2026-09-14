# Análisis Técnico y de Integración de Datos Meteorológicos

**Taller 1 — Integración de datos entre aplicaciones**  
**Curso:** Aplicaciones y Servicios Web  
**Estudiante:** Sara Yulieth Quimbayo Osorio  
**Fecha:** Septiembre de 2026  

---

## 1. Tabla Comparativa de Contratos

Durante la fase inicial del proyecto revisé las especificaciones técnicas de las dos fuentes de datos externas y las confronté con los requerimientos del contrato institucional (`CONTRATO_API.md`). El resultado de este contraste se resume en la siguiente tabla:

| Concepto / Campo | Proveedor A (`proveedor_a.json`) | Proveedor B (`proveedor_b.csv`) | Contrato Institucional | Transformación Requerida |
| :--- | :--- | :--- | :--- | :--- |
| **Identificador** | `provider_record_id` (string en raíz) | `record_code` (string en columna) | No se envía en el body de la API | Se retiene en el integrador como `trazabilidad_id` para control y auditoría en `reporte.json`. |
| **Ciudad** | `station.city_name` (string anidado) | `municipality` (string plano) | `ciudad` (string, no vacío) | Extraer del subobjeto en A o renombrar columna en B; aplicar limpieza de espacios con `strip()`. |
| **País** | `station.country_code` (código ISO) | `country` (código ISO) | `pais` (string, no vacío) | Desanidar en A y renombrar en B; aplicar saneamiento de texto con `strip()`. |
| **Latitud** | `location.lat` (number flotante) | `latitude_deg` (cadena de texto) | `latitud` (number, rango [-90, 90]) | Extraer en A; convertir cadena a `float` en B; redondear a 6 cifras decimales. |
| **Longitud** | `location.lon` (number flotante) | `longitude_deg` (cadena de texto) | `longitud` (number, rango [-180, 180]) | Extraer en A; convertir cadena a `float` en B; redondear a 6 cifras decimales. |
| **Temperatura** | `measurements.temperature_f` (°F flotante) | `temp_celsius` (°C en cadena de texto) | `temperatura_c` (number en °C) | En A: aplicar fórmula térmica $(T_F - 32) \times 5/9$; en B: parsear a `float`; redondear a 2 decimales. |
| **Humedad** | `measurements.relative_humidity` (flotante %) | `humidity_pct` (cadena de texto %) | `humedad` (number, rango [0, 100]) | Extraer de `measurements` en A; convertir texto a `float` en B; redondear a 2 decimales. |
| **Viento** | `measurements.wind_speed_ms` (m/s flotante) | `wind_kmh` (km/h en cadena de texto) | `viento_kmh` (number, $\ge 0$) | En A: convertir cinemáticamente $v_{m/s} \times 3.6$; en B: parsear a `float`; redondear a 2 decimales. |
| **Fecha y Hora** | `observed_at` (ISO 8601 con offset) | `measurement_time` (`DD/MM/YYYY HH:MM`) | `fecha_hora` (ISO 8601 estricto con TZ) | En A: validar estándar ISO; en B: parsear patrón con `strptime`, inyectar UTC-5 Colombia y exportar con `isoformat()`. |
| **Origen** | `source: "weather_provider_a"` | No presente en el archivo | `origen` (`"proveedor_a"` / `"proveedor_b"`) | Inyectar el valor literal exacto permitido por el contrato según la fuente procesada. |

---

## 2. Respuestas a las Preguntas Oficiales

### 1. ¿Qué diferencias encontró entre los contratos de los proveedores?

Identifiqué cuatro discrepancias estructurales entre ambos proveedores:

1. **Estructura y encapsulamiento:** El Proveedor A distribuye la información de manera jerárquica en un documento JSON, encapsulando las variables en tres objetos secundarios (`station`, `location` y `measurements`). En contraste, el Proveedor B utiliza un archivo plano CSV delimitado por punto y coma (`;`), donde no existe jerarquía y cada línea representa una fila de texto sin tipado nativo.
2. **Sistemas de unidades físicas:** El Proveedor A registra magnitudes bajo el sistema anglosajón y técnico internacional: temperatura en grados Fahrenheit (°F) y velocidad del viento en metros por segundo (m/s). El Proveedor B entrega magnitudes en el sistema métrico habitual (grados Celsius y kilómetros por hora), aunque representadas como texto.
3. **Representación temporal y husos horarios:** El Proveedor A incluye fechas en formato ISO 8601 con zona horaria explícita (`2026-09-01T12:00:00-05:00`). El Proveedor B, en cambio, emplea una notación local estándar (`DD/MM/YYYY HH:MM`) sin información de segundos ni desplazamiento respecto a UTC, requiriendo contextualización manual hacia el huso horario colombiano.
4. **Nomenclatura de campos:** No existe concordancia nominal entre las fuentes. Por ejemplo, el municipio se denomina `city_name` en el Proveedor A, `municipality` en el Proveedor B y `ciudad` en el contrato institucional. Lo mismo ocurre con las coordenadas (`lat`/`lon` vs `latitude_deg`/`longitude_deg` vs `latitud`/`longitud`).

### 2. ¿Qué transformaciones fueron necesarias?

Para homologar las mediciones al contrato institucional implementé las siguientes operaciones dentro de `integrador.py`:

* **Conversión termodinámica (°F a °C):** Apliqué la ecuación exacta $T_C = (T_F - 32) \times \frac{5}{9}$ para los registros del Proveedor A, limitando el resultado a dos decimales con `round(..., 2)`.
* **Conversión anemométrica (m/s a km/h):** Multipliqué la velocidad del viento del Proveedor A por el factor cinemático constante de $3.6$ ($1 \text{ m/s} = 3.6 \text{ km/h}$), redondeando a dos decimales.
* **Normalización temporal a ISO 8601 (UTC-5):** Para el Proveedor B utilicé `datetime.strptime(cadena, "%d/%m/%Y %H:%M")`. Al objeto obtenido le asigné explícitamente el huso horario de Colombia mediante `timezone(timedelta(hours=-5))` y generé la representación canónica con `.isoformat()`. Para el Proveedor A utilicé `datetime.fromisoformat()` para validar su estructura.
* **Aplanamiento y casteo de tipos:** Extraje los campos de los subobjetos del Proveedor A hacia un diccionario de nivel único. En el Proveedor B convertí cada cadena numérica a `float` y apliqué `strip()` sobre las cadenas de texto para eliminar espacios residuales.
* **Inyección de metadatos de integración:** Incorporé el campo `origen` exigido por el contrato (`"proveedor_a"` o `"proveedor_b"`) y preservé el identificador original de cada registro para la trazabilidad interna.

### 3. ¿Qué tipos de errores encontró antes de enviar información?

En la etapa de depuración previa al envío HTTP clasifiqué los errores detectados en dos categorías conceptuales independientes:

#### a) Errores de Normalización (12 registros en total)
Corresponden a fallos sintácticos o de tipo donde el registro ni siquiera puede ser transformado a la estructura del contrato institucional. El programa capturó excepciones de tipo `ValueError` y los marcó como `error_normalizacion`:
* **Cadenas de texto en campos numéricos:** Ocurre cuando un proveedor introduce cadenas no convertibles a número. Caso documentado: registro `A-0082`, cuyo campo `measurements.temperature_f` contenía el valor `"N/A"`, lo que provocó un fallo al ejecutar `float("N/A")`. En el Proveedor B, el registro `B-0114` contenía la palabra `"error"` en `temp_celsius`.
* **Fechas con valores o formatos imposibles:** Caso documentado: registro `B-0171`, con la marca temporal `"31/13/2026 28:75"`. El mes 13 y la hora 28 no existen en el calendario gregoriano, disparando un error en `strptime`. Otros casos correspondieron a marcas temporales vacías (como `A-0040` y `B-0076`).

#### b) Rechazos de Validación Local (8 registros en total)
Corresponden a mediciones que superaron la normalización estructural y de tipos —quedando registradas válidamente en `salida/normalizadas.json`—, pero que violan las reglas de dominio y límites físicos definidos en `CONTRATO_API.md`:
* **Humedad fuera de rango [0, 100]:** Caso documentado: registro `A-0015`, con una humedad relativa normalizada de `108.4%`. En el Proveedor B, el registro `B-0004` presentó una humedad de `117.5%`.
* **Latitud fuera del intervalo geográfico [-90, 90]:** Caso documentado: registro `B-0006`, con una latitud de `-94.22°`. En el Proveedor A, el registro `A-0031` contenía una latitud de `95.245°`.

### 4. ¿Qué diferencias encontró entre validación local y validación del servidor?

La validación local y la validación del servidor cumplen propósitos complementarios en la arquitectura de integración:

* **Validación local (filtro de cliente):** Es síncrona, estática y no requiere estado. Opera bajo las reglas visibles del contrato (`CONTRATO_API.md`), verificando presencias de campos obligatorios, tipado primitivo y rangos numéricos plausibles. Su función principal es defensiva: evita enviar datos corruptos a la red, reduce el consumo de ancho de banda y mitiga la carga innecesaria en la infraestructura central.
* **Validación del servidor (autoridad central y estado):** Es autoritativa, contextual y evalúa condiciones que el cliente no puede verificar por sí mismo. El servidor revisa permisos de seguridad, validez del encabezado `X-Equipo`, unicidad de los registros frente a la base de datos para prevenir duplicados (`HTTP 409`) y consistencia relacional.

Durante la ejecución del integrador comprobé esta diferencia de forma directa: las 380 mediciones que superaron la validación local fueron enviadas con su estructura impecable, pero el servidor las rechazó con código `HTTP 400` porque el identificador de equipo configurado no estaba habilitado en las credenciales del backend. La validación local es una condición indispensable, pero jamás sustituye la autorización ni las reglas de persistencia del servidor.

### 5. ¿Qué decisión de implementación considera más importante y por qué?

La decisión técnica más importante fue **separar estrictamente la etapa de normalización de la etapa de validación de negocio**, combinada con una gestión diferenciada de códigos HTTP en el cliente:

1. **Separación de responsabilidades y cumplimiento del numeral 6:** Si hubiese implementado una única función que validara y descartara registros al mismo tiempo, los datos con humedades superiores a 100 o latitudes anómalas habrían desaparecido en la lectura. Al separar ambas fases, logré que `salida/normalizadas.json` conserve la totalidad de registros sintácticamente válidos (388 registros), permitiendo que la etapa de validación actúe como un filtro posterior que separa los 380 registros aptos para envío de los 8 rechazados por reglas de negocio. Esto garantiza una trazabilidad completa y auditable.
2. **Estrategia asimétrica de reintentos:** En `ClienteHTTPInstitucional` establecí que las respuestas `4xx` (como el `HTTP 400` recibido) no activen reintentos, pues corresponden a errores deterministas del cliente donde repetir la solicitud solo congestionaría la red. Por el contrario, los errores `5xx`, caídas de conexión y timeouts cuentan con una política de retroceso exponencial (*backoff*) de hasta 3 intentos, protegiendo al integrador ante fallos transitorios de infraestructura.

---

## 3. Evidencia Resumida de Ejecución Real

### Resumen Consolidado de Métricas

La ejecución completa del programa `python integrador.py` contra el entorno real arrojó las siguientes métricas, documentadas en `salida/reporte.json`:

| Métrica | Registros | Detalle u Observación |
| :--- | :---: | :--- |
| **Total procesados** | **400** | 200 provenientes de Proveedor A y 200 de Proveedor B. |
| **Normalizados con éxito** | **388** | Generados y respaldados en `salida/normalizadas.json`. |
| **Errores de normalización** | **12** | 6 en Proveedor A y 6 en Proveedor B (tipos corruptos o fechas vacías/inválidas). |
| **Válidos localmente** | **380** | Cumplen todas las restricciones de dominio institucional. |
| **Rechazados localmente** | **8** | 4 en Proveedor A y 4 en Proveedor B (humedad > 100% o latitud fuera de rango). |
| **Enviados a la API** | **380** | Coincide con el 100% de los registros válidos localmente. |
| **Aceptados por la API (`201`)** | **0** | Ningún registro almacenado en base de datos central. |
| **Rechazados por la API (`400`)** | **380** | Rechazo por validación de credenciales del encabezado `X-Equipo`. |
| **Errores de comunicación** | **0** | Sin timeouts ni pérdidas de paquete durante los 380 envíos HTTP. |

---

### Casos Reales Documentados con `trazabilidad_id`

#### Errores de Normalización (datos no convertibles)

* **Registro `A-0082` (Proveedor A):**  
  ```json
  {
    "trazabilidad_id": "A-0082",
    "origen": "proveedor_a",
    "indice_fuente": 82,
    "estado": "error_normalizacion",
    "motivo": "Error de conversión de tipos: could not convert string to float: 'N/A'"
  }
  ```
  *Causa:* El campo `temperature_f` contenía la cadena `"N/A"`, impidiendo la conversión numérica.

* **Registro `B-0171` (Proveedor B):**  
  ```json
  {
    "trazabilidad_id": "B-0171",
    "origen": "proveedor_b",
    "indice_fuente": 171,
    "estado": "error_normalizacion",
    "motivo": "Error de conversión de tipos: time data '31/13/2026 28:75' does not match format '%d/%m/%Y %H:%M'"
  }
  ```
  *Causa:* Fecha astronómicamente inválida (mes 13 y hora 28).

#### Rechazos de Validación Local (datos fuera de reglas de negocio)

* **Registro `A-0015` (Proveedor A):**  
  ```json
  {
    "trazabilidad_id": "A-0015",
    "origen": "proveedor_a",
    "estado": "normalizado",
    "datos_normalizados": {
      "ciudad": "Barranquilla",
      "pais": "CO",
      "latitud": 10.969955,
      "longitud": -74.762201,
      "temperatura_c": 28.67,
      "humedad": 108.4,
      "viento_kmh": 10.01,
      "fecha_hora": "2026-09-01T07:00:00-05:00",
      "origen": "proveedor_a"
    },
    "estado_validacion": "rechazado_localmente",
    "motivos_rechazo_local": [
      "Humedad fuera de rango [0, 100]: 108.4"
    ]
  }
  ```
  *Causa:* Humedad relativa del `108.4%`, valor físicamente inviable que infringe la cota máxima del contrato.

* **Registro `B-0006` (Proveedor B):**  
  ```json
  {
    "trazabilidad_id": "B-0006",
    "origen": "proveedor_b",
    "estado": "normalizado",
    "datos_normalizados": {
      "ciudad": "Cali",
      "pais": "CO",
      "latitud": -94.22,
      "longitud": -76.492907,
      "temperatura_c": 18.11,
      "humedad": 62.0,
      "viento_kmh": 21.68,
      "fecha_hora": "2026-09-01T09:45:00-05:00",
      "origen": "proveedor_b"
    },
    "estado_validacion": "rechazado_localmente",
    "motivos_rechazo_local": [
      "Latitud fuera de rango [-90, 90]: -94.22"
    ]
  }
  ```
  *Causa:* Latitud de `-94.22°`, superando los límites geográficos del modelo esférico terrestre.

---

### Respuesta Real Recibida desde la API Institucional (Envío POST)

Al transmitir una medición normalizada y válida localmente mediante `POST /api/v1/mediciones`:

* **Cabeceras enviadas:**  
  `Content-Type: application/json`  
  `X-Equipo: sara_quimbayo`  
* **Payload enviado (ejemplo medición `A-0001`):**  
  ```json
  {
    "ciudad": "Medellin",
    "pais": "CO",
    "latitud": 6.242282,
    "longitud": -75.595933,
    "temperatura_c": 18.94,
    "humedad": 81.3,
    "viento_kmh": 30.49,
    "fecha_hora": "2026-09-01T00:00:00-05:00",
    "origen": "proveedor_a"
  }
  ```
* **Respuesta del servidor:**  
  Código de estado: `HTTP 400 Bad Request`  
  Cuerpo devuelto:  
  ```json
  {
    "detail": "X-Equipo ausente o no autorizado"
  }
  ```

---

### Resultado de la Consulta Final mediante GET

Al finalizar la ronda de envíos, el programa ejecutó la verificación de persistencia mediante `GET /api/v1/mediciones?equipo=sara_quimbayo`:

* **Código HTTP obtenido:** `400 Bad Request`  
* **Cuerpo de respuesta recibido:**  
  ```json
  {
    "detail": "Equipo no autorizado"
  }
  ```
* **Diagnóstico técnico:** La API institucional mantiene una lista de control de acceso basada en el identificador del equipo. Al no encontrarse registrado de forma previa en la base de datos del servidor institucional, este rechazó tanto la inserción como la lectura de mediciones. El integrador procesó este código sin abortar la ejecución, evitando excepciones no controladas y dejando constancia explícita en `salida/reporte.json`.
