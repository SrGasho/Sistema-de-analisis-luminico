# Sistema de análisis lumínico

Proyecto de Ciencias de la Computación 1 para analizar la iluminación y el balance energético de un hotel de dos torres en Bogotá.

## Implementación

El MVP está implementado en Python estándar y utiliza:

- `dataclasses` para el modelo del hotel.
- `datos_hotel.json` como entrada reproducible.
- Un árbol `Hotel -> Torre -> Piso -> ZonaHotel`.
- Un Octree para consultas espaciales.
- Un grafo de adyacencia para reflexión de primer orden.
- Un eje temporal de 24 horas en pasos de 30 minutos.
- Un balance heurístico de iluminación con generador limitado.
- Reportes JSON y CSV.

## Ejecución

Desde la raíz del repositorio:

```bash
python3 -m src.main
```

También se pueden indicar rutas personalizadas:

```bash
python3 -m src.main --entrada data/datos_hotel.json --salida outputs
```

La ejecución genera `outputs/resultados.json`, `outputs/resumen.json` y `outputs/reporte.csv`.

## Aplicación web

La interfaz web muestra primero los datos del hotel mediante formularios editables. JavaScript genera el objeto JSON internamente; el usuario no necesita modificar JSON directamente. El botón **Analizar iluminación y balancear energía** ejecuta la simulación, muestra el plano esquemático, actualiza el estado del generador y presenta recomendaciones de reasignación.

Para iniciar el servidor:

```bash
python3 -m src.api
```

Después abre `http://127.0.0.1:8000` en el navegador. También se puede validar la entrada sin iniciar el servidor:

```bash
python3 -m src.api --check
```

La aplicación usa únicamente la biblioteca estándar de Python y expone:

```text
GET  /api/escenario
POST /api/validar
POST /api/balancear
GET  /api/health
```

## Estructura

```text
data/datos_hotel.json  Entrada sintética del hotel
src/modelo.py           Entidades y estados
src/geometria.py        Vectores, cajas y rayos
src/octree.py           Índice espacial
src/influencia.py       Grafo de reflexión
src/clima.py            Perfil climático y curva solar
src/simulacion.py       Recorrido temporal
src/balance.py          Demandas y asignación de potencia
src/evaluacion.py       Estados y métricas
src/reasignacion.py     Propuestas de habitaciones alternativas
src/io_datos.py         Carga y validación del JSON
src/main.py             Ejecución y reportes
src/api.py              Servidor web y endpoints JSON
web/index.html          Interfaz de entradas y resultados
web/app.js              Balanceo, resultados y descargas
web/styles.css          Estilos de la interfaz
```

Los datos son sintéticos y el resultado no sustituye un diseño fotométrico, eléctrico o arquitectónico profesional.
