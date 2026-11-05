# Sistema de análisis lumínico

Proyecto de Ciencias de la Computación 1 para analizar la iluminación y el balance energético de un hotel de dos torres en Bogotá.

Los datos son sintéticos. Los resultados son aproximaciones educativas y no reemplazan un diseño fotométrico, eléctrico o arquitectónico, ni certifican cumplimiento normativo.

## Qué calcula el sistema

- **Entradas completas.** Torres, pisos, habitaciones, zonas comunes, perfiles de iluminación, horarios, vidrios, paredes, orientaciones de ventanas, generador y huéspedes. Los acabados se definen por actividad y pueden personalizarse por recinto.
- **Luz natural y reflejada.** La luz natural usa el perfil climático de Bogotá y la transmitancia del vidrio. Incluye componente directa (según la orientación de la ventana y la posición del sol) y difusa (según la nubosidad). La reflexión de primer orden sale del grafo de influencia de las superficies.
- **Balance energético.** Asigna la potencia del generador en cada paso de 30 minutos. Primero cubre los mínimos de iluminación y después los objetivos, en orden de prioridad.
- **Habitabilidad por zona.** Cada zona recibe un veredicto: `HABITABLE`, `CASI_HABITABLE`, `NO_HABITABLE` o `DATOS_INSUFICIENTES`. Las zonas casi habitables reciben una recomendación según la causa principal de su déficit o exceso.
- **Mejoras y reestructuración.** Se miden cambios concretos sobre la configuración actual y se busca una reestructuración de actividades dentro de rangos fijos.

## Criterios de habitabilidad

Cada paso evaluable recibe un puntaje `q`: 1 si está confortable, 0.5 si es déficit o exceso leve, y 0 si es déficit severo o exceso severo. El puntaje de la zona `P` es el promedio de `q` en los pasos evaluables. Los pasos nocturnos sin balance cuentan como `DATOS_INSUFICIENTES` y no entran en el cálculo.

| Veredicto | Condición |
|---|---|
| `HABITABLE` | `P ≥ 0.90` |
| `CASI_HABITABLE` | `0.75 ≤ P < 0.90` |
| `NO_HABITABLE` | `P < 0.75`, o más de 5 % de los pasos en déficit severo |

El puntaje del hotel pondera cada zona por `prioridad_actividad × (1 + 0.10 × (piso − 1))`. Estos umbrales y pesos están en `parametros_evaluacion` dentro de `data/datos_hotel.json`.

## Ejecución

Requisitos: Python 3 (el desarrollo se probó con Python 3.11). El proyecto usa solo la biblioteca estándar.

### Simulación por línea de comandos

Desde la raíz del repositorio:

```bash
python3 -m src.main
```

También se pueden indicar rutas personalizadas:

```bash
python3 -m src.main --entrada data/datos_hotel.json --salida outputs
```

La ejecución genera `outputs/resultados.json`, `outputs/resumen.json` y `outputs/reporte.csv`.

### Aplicación web

```bash
python3 -m src.api
```

Después abre `http://127.0.0.1:8000`. Para validar la entrada sin iniciar el servidor:

```bash
python3 -m src.api --check
```

El flujo de la interfaz es:

1. **Cargar escenario.** Muestra la condición actual antes del balance, con el plano y los veredictos provisionales.
2. **Editar entradas.** Los formularios generan el JSON internamente. Se pueden cambiar pisos, habitaciones, perfiles, horarios, vidrios, paredes y acabados por actividad. Cada zona del plano permite editar su pared, su vidrio y su orientación (una sola para habitaciones, varias para zonas comunes).
3. **Balancear energía.** Ejecuta el balance y compara el estado antes y después.
4. **Mejoras medidas.** Prueba cuatro cambios fijos sobre la configuración actual.
5. **Buscar reestructuración.** Ver la sección siguiente.

## Reestructuración de actividades

`POST /api/reestructurar` busca cambios que mejoren el puntaje ponderado del hotel. La búsqueda es por coordenadas: prueba un cambio a la vez, conserva el que mejora el puntaje y repite.

Cada cambio se evalúa con la simulación completa. Antes de elegir un cambio se comparan el puntaje ponderado, el número de zonas no habitables y la energía total, en ese orden. La búsqueda se detiene al agotar el presupuesto o cuando una ronda completa no mejora nada.

Solo se prueban actividades con zonas `CASI_HABITABLE` o `NO_HABITABLE`.

### Rangos

Los rangos están en `parametros_evaluacion.reestructuracion` de `data/datos_hotel.json`:

| Variable | Rango por defecto | Motivo |
|---|---|---|
| Pared | `BLANCO`, `CREMA`, `GRIS_CLARO` | Se excluyen `GRIS_MEDIO` y `OSCURO` porque reducen la luz reflejada. |
| Vidrio | `VIDRIO_CLARO`, `VIDRIO_LOW_E`, `VIDRIO_CONTROL_SOLAR` | Los tres presets del proyecto. Solo aplica a actividades con ventanas. |
| Orientaciones | Tres conjuntos de la lista de orientaciones | Cambia la exposición solar de las ventanas. |
| Objetivo de iluminancia | 0 %, 50 % o 100 % entre `minimo` y `maximo` del perfil | El objetivo afecta la demanda de energía, no la clasificación. |
| Horario de cocina y recreación | Inicio 6–10 h, fin 22–24 h | Fuera de horario la zona pasa a modo `REDUCIDA`. |

Habitaciones no cambian de horario, porque son de uso continuo.

La búsqueda no cambia la capacidad del generador ni la geometría. Tampoco modifica los recintos que tienen acabados personalizados: el cambio se aplica al valor por actividad.

El presupuesto por defecto es de 30 evaluaciones. En el escenario de dos torres, cada evaluación tarda cerca de un segundo.

### Costo energético

Un cambio puede mejorar el puntaje y subir la energía. Por ejemplo, un vidrio con menor transmitancia reduce el exceso de luz natural, pero obliga a usar más luz artificial. El resultado muestra energía antes y después para que ese costo quede visible.

## API

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/health` | Estado del servidor. |
| GET | `/api/escenario` | Carga `data/datos_hotel.json` y devuelve la condición actual. |
| POST | `/api/validar` | Valida una configuración y devuelve un resumen. |
| POST | `/api/condicion_actual` | Análisis sin balance energético. |
| POST | `/api/balancear` | Balance completo, veredictos, sugerencias y reasignaciones. |
| POST | `/api/mejoras` | Mide cuatro mejoras fijas sobre la configuración enviada. |
| POST | `/api/reestructurar` | Busca una reestructuración dentro de los rangos. |

Los errores de validación devuelven HTTP 400 con un campo `error` en español.

## Estructura

```text
data/datos_hotel.json       Escenario sintético de referencia
data/casos_prueba/          Casos para déficit, exceso y alta demanda
src/modelo.py               Entidades y enumeraciones
src/geometria.py            Vectores, cajas y rayos
src/octree.py               Índice espacial
src/influencia.py           Grafo de reflexión de primer orden
src/clima.py                Perfil climático y curva solar
src/io_datos.py             Carga, valores por defecto y validación del JSON
src/simulacion.py           Recorrido de 24 horas en pasos de 30 minutos
src/balance.py              Demandas, cola de prioridad y energía por torre y piso
src/evaluacion.py           Estados instantáneos y resúmenes por zona
src/habitabilidad.py        Puntaje, veredictos y recomendaciones
src/arboles.py              Índices AVL y rojo-negro sobre (puntaje, zona)
src/reasignacion.py         Reasignación heurística de huéspedes
src/mejoras.py              Cuatro mejoras fijas medidas con simulación
src/reestructuracion.py     Búsqueda de reestructuración de actividades
src/sugerencias.py          Recomendaciones calculadas con datos del modelo
src/api.py                  Servidor HTTP y endpoints JSON
src/main.py                 Ejecución por línea de comandos y reportes
web/index.html              Estructura de la interfaz
web/app.js                  Formularios, plano, resultados y búsquedas
web/styles.css              Estilos
```

## Limitaciones conocidas

- La geometría de cada habitación (24 m², una ventana de 2 m²) está fija en `src/io_datos.py`. En la interfaz se edita su orientación, no sus dimensiones.
- El árbol de energía solo agrega resultados. No decide la distribución de potencia: el reparto lo hace la cola de prioridad en `src/balance.py`.
- La búsqueda de reestructuración no es exhaustiva. Con un presupuesto de 30 evaluaciones puede no encontrar la mejor combinación.
- Los rangos de la reestructuración son supuestos del proyecto. No son una transcripción normativa del RETILAP.
