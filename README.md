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
```

Los datos son sintéticos y el resultado no sustituye un diseño fotométrico, eléctrico o arquitectónico profesional.
