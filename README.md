# Sistema de análisis lumínico

Proyecto de Ciencias de la Computación 1 para analizar la iluminación y el balance energético de un hotel de dos torres en Bogotá: la Torre Pequeña (`TP`) y la Torre Grande (`TG`). Las zonas se identifican con la abreviatura de su torre, por ejemplo `TP-H-101` (habitación) o `TG-COC-01` (cocina).

Los datos de clima vienen de NASA POWER (promedios 2001–2020 para Bogotá). El resto del escenario es sintético. Los resultados son aproximaciones educativas y no reemplazan un diseño fotométrico, eléctrico o arquitectónico, ni certifican cumplimiento normativo.

## Qué calcula el sistema

- **Entradas completas.** Torres, pisos, habitaciones, zonas comunes, perfiles de iluminación, horarios, vidrios, paredes, orientaciones de ventanas, generador y huéspedes. Los acabados se definen por actividad y pueden personalizarse por recinto.
- **Luz natural.** La luz base es `E_base = K_lux · C(t) · factor_luz`, donde `C(t)` es la curva solar de 06:00 a 18:00 y `factor_luz = radiación / radiación de cielo despejado` (7,063 kWh/m²/día). El código calcula ese factor a partir de la radiación de cada perfil climático (`PerfilClimatico.factor_luz`). La luz que entra por cada ventana tiene una componente directa, según la orientación de la ventana, la posición del sol y la nubosidad, y una difusa, según la nubosidad. La otra torre tapa parte del cielo: la difusa se multiplica por `1 − obstrucción`, donde `obstrucción = Σ cos_ventana × factor de vista` de las fachadas que la ventana tiene enfrente (máximo 1). En el escenario base 40 ventanas tienen obstrucción; `TP-H-101-V1`, al este y frente a TG, tiene 0,593.
- **Refracción en el vidrio.** Para la componente directa se calcula el ángulo de refracción con la ley de Snell (índice 1,5) y la transmitancia de Fresnel no polarizada en las dos caras del vidrio. El resultado se normaliza con la incidencia perpendicular, así que a 0° se conserva la transmitancia visible del catálogo (`factor_angular_vidrio` en `src/geometria.py`). La componente difusa usa la transmitancia del catálogo.
- **Luz reflejada.** Solo de día, y con dos partes que se suman:
  - **Reflexión interior.** Método de flujo dividido: `E_ri = Φ · ρ / (A_int · (1 − ρ))`. `Φ` es la suma, por ventana, de (luz natural + luz exterior reflejada) × área de la ventana; `ρ` es la reflectancia de la pared del recinto; `A_int = 2 · área + 4 · √área · 3 m` (una habitación de 24 m² da `A_int ≈ 106,8 m²`). Con pared blanca (`ρ = 0,80`) el factor `ρ / (1 − ρ)` vale 4. Promedia todos los rebotes dentro del recinto, así que el color de la pared cambia la luz de su propio cuarto.
  - **Reflexión exterior entre torres.** Sale del grafo de influencia `fachada → ventana de la otra torre`. Cada torre tiene 4 fachadas (N, S, E, O) con la reflectancia del campo `fachada` de la torre en el JSON (por defecto `GRIS_CLARO`, 0,60). Para cada ventana se toma su punto de salida en la fachada de su torre y `consultar_radio` (18 m) sobre el octree entrega las fachadas candidatas de la otra torre. Se exige que ventana y fachada se miren y que un rayo entre ellas no cruce otra torre. El peso es `ρ_fachada × cos_fachada × cos_ventana × A_f / (π · d² + A_f)`, con `d` la distancia al punto más cercano de la fachada. Cada fachada recibe `E_base × (max(0, n · sol) × f_directa + f_difusa)`, y la luz exterior que entra por una ventana es `Σ luz_fachada × peso × VLT`. Esta parte es de primer orden: la luz reflejada por una fachada no vuelve a reflejarse en otra.
- **Modos de operación.** Cada zona tiene un modo en cada paso: `ACTIVA` dentro de su horario, `REDUCIDA` fuera de él, `CERRADA` en su franja de cierre (cocina de 23:00 a 05:00 y recreación de 00:00 a 07:00; si las dos franjas se cruzan, manda la activa) y `EMERGENCIA` cuando el generador no alcanza para cubrir su mínimo. Habitaciones y parqueadero nunca cierran.
- **Balance energético.** Asigna la potencia del generador en cada paso de 30 minutos, en este orden: primero un nivel de emergencia de 10 lux para todas las zonas abiertas, luego los mínimos (parqueadero como seguridad, después habitaciones ocupadas y después el resto) y al final los objetivos por prioridad. El orden se resuelve con una cola de prioridad (`heapq`). Las zonas cerradas no consumen.
- **Habitabilidad por zona.** Cada zona recibe un veredicto: `HABITABLE`, `CASI_HABITABLE`, `NO_HABITABLE` o `DATOS_INSUFICIENTES`. Las zonas casi habitables reciben una recomendación según la causa principal de su déficit o exceso.
- **Reasignación de huéspedes.** Si la habitación de un huésped queda `NO_HABITABLE`, se busca otra habitación habitable con cama libre en un árbol AVL. Ver la sección [Reasignación de huéspedes](#reasignación-de-huéspedes).
- **Reportes por franja horaria.** Los resultados se guardan en un árbol rojo-negro ordenado por hora para consultar franjas. Ver la sección [Índice temporal](#índice-temporal).
- **Mejoras y reestructuración.** Se miden cambios concretos sobre la configuración actual y se busca una reestructuración de actividades dentro de rangos fijos.

## Alcance

La geometría de las torres es fija: el sistema no mueve ni rediseña edificios, pisos ni habitaciones. Sí mide mejoras y propone reestructuraciones de las variables de luz: actividades (orientación de ventanas y objetivos de iluminancia), acabados (pared y vidrio), horarios y capacidad del generador.

## Criterios de habitabilidad

Cada paso evaluable recibe un puntaje `q`: 1 si está confortable, 0,5 si es déficit o exceso leve, y 0 si es déficit severo o exceso severo. El puntaje de la zona `P` es el promedio de `q` en los pasos evaluables. No entran en el cálculo los pasos `CERRADA` ni, en la condición actual, los pasos nocturnos sin balance: los dos quedan como `DATOS_INSUFICIENTES`. Un paso en `EMERGENCIA` sí cuenta y se clasifica contra el mínimo del modo que le corresponde por horario, así que cuenta como déficit.

| Veredicto | Condición |
|---|---|
| `HABITABLE` | `P ≥ 0,90` |
| `CASI_HABITABLE` | `0,75 ≤ P < 0,90` |
| `NO_HABITABLE` | `P < 0,75`, o más de 5 % de los pasos en déficit severo |

El puntaje del hotel pondera cada zona por `prioridad_actividad × (1 + 0,10 × (piso − 1))`. Estos umbrales y pesos están en `parametros_evaluacion` dentro de `data/datos_hotel.json`.

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

La ejecución genera `outputs/resultados.json`, `outputs/resumen.json` y `outputs/reporte.csv`. Estos archivos traen resultados, resumen por zona, reasignaciones y sugerencias. Los campos `complejidad` y `temporal` solo los devuelve la API.

### Aplicación web

```bash
python3 -m src.api
```

Después abre `http://127.0.0.1:8000`. El servidor acepta `--host` y `--port`. Para validar la entrada sin iniciar el servidor:

```bash
python3 -m src.api --check
```

La interfaz se organiza en seis pestañas. Un botón en el encabezado cambia entre modo oscuro y claro; el plano conserva su aspecto en los dos.

1. **Configurar.** Los formularios generan el JSON internamente. Se pueden cambiar pisos, habitaciones, perfiles, horarios (incluido el cierre), vidrios, paredes y acabados por actividad. Desde aquí se carga un JSON propio, se descarga la configuración, se carga el escenario y se balancea la energía.
2. **Diagnóstico.** La condición antes del balance: veredictos provisionales y sugerencias.
3. **Plano.** El plano por torre y piso, con los selectores de franja horaria, vista (antes o después del balance) y capa de color, y la leyenda de abreviaturas (`TP` = Torre Pequeña, `TG` = Torre Grande). Cada zona permite editar su pared, su vidrio y su orientación.
4. **Balance.** Generador, comparación antes y después, veredictos, sugerencias y reasignaciones (con restricciones, habitaciones descartadas y motivo). Al balancear, la interfaz abre esta pestaña.
5. **Mejoras.** Las cuatro mejoras medidas y la búsqueda de reestructuración.
6. **Detalle técnico.** Estructuras de datos y comparaciones, estados calculados, resumen de zonas y rangos de confort.

### Pruebas

Desde la raíz del repositorio:

```bash
python3 -m unittest
```

Son 21 pruebas en dos archivos y tardan unos 11 segundos:

- `tests/test_casos_plan.py` cubre los 10 casos de prueba del plan del proyecto: ventana al sol sin obstáculo, ventana sombreada por la otra torre, transmisión con cada vidrio (incluye Snell y Fresnel), luz reflejada (aristas solo de fachada a ventanas de la otra torre, peso ≤ reflectancia, reflejada = exterior + interior, pared oscura con menos reflejada que una blanca), noche, generador que alcanza para mínimos pero no para objetivos, reasignación con y sin candidata, zona cerrada y cielo nublado contra despejado.
- `tests/test_casos_json.py` ejecuta el escenario base y cada caso de `data/casos_prueba/`. Comprueba que el resultado coincida con el bloque `caso.resultado_esperado` del JSON, que se cumplan las reglas comunes (de noche no hay luz natural, una zona cerrada no consume, un paso en emergencia cuenta como déficit, el generador no se pasa de su capacidad, ninguna habitación recibe más huéspedes que camas libres) y el comportamiento propio de cada caso.

### Casos de prueba

Todos parten del hotel completo de `datos_hotel.json` (dos torres y 78 huéspedes). Cada archivo tiene un bloque `caso` con la historia, lo que se espera ver y los números esperados, para poder leer el resultado.

| Caso | Situación | Qué muestra |
|---|---|---|
| `temporada_lluvias` | Abril, cielo cubierto | Las 127 zonas habitables (el sol fuerte del escenario base deja 26 casi habitables); la energía sube porque hay menos luz natural. |
| `generador_alta_demanda` | Generador de 17 kW | Los mismos veredictos del escenario base (101 habitables, 26 casi habitables), pero el generador queda en `ALTA_DEMANDA`. |
| `deficit_leve` | Generador de 10 kW | 89 habitables, 37 casi habitables y 1 no habitable; las nuevas casi habitables frente al escenario base empeoran por la noche; solo las recreaciones entran en `EMERGENCIA`; el parqueadero nunca queda en déficit. |
| `deficit_severo` | Generador de 4 kW | 3 habitables, 53 casi habitables y 71 no habitables; 25 huéspedes sin alternativa porque solo los parqueaderos quedan habitables. |
| `apagon_generador` | Generador de 0 kW | Las 127 zonas no habitables y los 78 huéspedes sin alternativa. |
| `cielo_despejado` | Cielo despejado | 101 habitables y 26 no habitables por exceso solar (las habitaciones con ventana al norte, de cara al sol); 20 huéspedes se mueven. |
| `exceso_severo` | Cielo despejado y 24 habitaciones de TP con vidrio claro al norte | 83 habitables y 44 no habitables (las 24 ocupadas de TP y las de ventana al norte); 38 huéspedes se mueven, y H-001 (`MISMA_TORRE`), H-002 (`PISO_MAXIMO:2`) y H-003 (`ORIENTACION:ESTE`) reciben habitaciones que cumplen su pedido. |
| `reasignacion_restringida` | El mismo exceso, con un grupo que pidió quedarse en TP | 83 habitables y 44 no habitables; 34 propuestas: 12 huéspedes llenan las 12 camas libres de TP piso 4 y los demás sin restricciones van a TG; 2 reciben `SIN_CAPACIDAD` (H-017, H-018) y 2 `RESTRICCIONES` (H-019, H-020). |

Al cargar un escenario, cada perfil de actividad debe cumplir `0 ≤ mínimo ≤ objetivo ≤ máximo`; si no, la carga falla con un mensaje de error.

## Reasignación de huéspedes

Un huésped se reasigna solo si su habitación queda `NO_HABITABLE`.

- **Bolsa de habitaciones.** Las habitaciones `HABITABLE` con cama libre se guardan en un AVL con clave `(torre, piso, −calidad, habitacion_id)`, donde `calidad = w_luz · puntaje + w_energia · ahorro`.
- **Búsqueda.** Para cada huésped se consulta el sucesor de cada piso permitido y se resta una penalización por cambio de piso. Cuando una habitación se llena, se elimina del árbol, así que dos huéspedes no reciben la misma cama.
- **Restricciones.** Se definen en `huespedes.restricciones_por_huesped` del JSON. `MISMA_TORRE` y `PISO_MAXIMO:n` filtran candidatas. `ORIENTACION:ESTE|NORTE|OESTE|SUR` es una preferencia que suma `w_actividad` si la habitación coincide. Una restricción desconocida se rechaza al cargar.
- **Salida.** Cada propuesta trae `descartadas` (habitaciones revisadas, con motivo `MENOR_PUNTAJE`). Si no hay alternativa, `motivo` dice por qué: `SIN_HABITACIONES_HABITABLES_LIBRES`, `SIN_CAPACIDAD` o `RESTRICCIONES`.
- **Costo.** `O(G · F · log H)` con `G` huéspedes a mover, `F` pisos y `H` habitaciones, contra `O(G · H)` de la búsqueda lineal.

En el escenario base nadie queda en una habitación `NO_HABITABLE`. El AVL se construye igual con las 78 habitaciones habitables libres (altura 7, 58 rotaciones, 417 comparaciones de construcción) y no se consulta. `data/casos_prueba/exceso_severo.json` muestra huéspedes que sí se mueven y `reasignacion_restringida.json` los tres motivos de falta de alternativa.

## Índice temporal

Cada resultado de la simulación se inserta en un árbol rojo-negro con clave `(hora, zona_id)` apenas se calcula. Una franja `[inicio, fin)` se consulta con un recorrido de rango en `O(log R + k)`, contra `O(R)` de recorrer la lista.

Las franjas fijas son: día completo, 00–06, 06–12, 12–18, 18–22 y 22–24. Para cada una se reporta energía en Wh y kWh, energía por actividad y por torre, hora y potencia pico del generador, déficit residual (lux·h bajo el mínimo), energía no asignada (Wh que habrían cerrado ese déficit), zonas críticas (las 10 con más horas en déficit), horas con déficit por zona, instantes con déficit y estado predominante de cada zona.

En `/api/balancear` los mismos resultados se insertan también en un AVL para comparar rotaciones:

| Medida | Escenario base (6.096 resultados) |
|---|---|
| Rotaciones rojo-negro / AVL | 9.099 / 7.232 |
| Altura rojo-negro / AVL | 22 / 14 |

En este escenario el rojo-negro rota más que el AVL, porque los resultados llegan casi ordenados (hora ascendente y tramos largos de IDs ascendentes). Con 6.096 claves aleatorias el rojo-negro rota menos: 3.511 contra 4.176.

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
| Horario de cocina y recreación | Inicio 6–10 h, fin 22–24 h | Fuera de horario la zona pasa a modo `REDUCIDA`, o a `CERRADA` dentro de su franja de cierre. La franja activa manda sobre la de cierre. |

Habitaciones no cambian de horario, porque son de uso continuo.

La búsqueda no cambia la capacidad del generador ni la geometría. La capacidad del generador sí se prueba en las mejoras medidas. Tampoco modifica los recintos que tienen acabados personalizados: el cambio se aplica al valor por actividad.

El presupuesto por defecto es de 30 evaluaciones. En el escenario de dos torres, cada evaluación tarda cerca de un segundo.

### Costo energético

Un cambio puede mejorar el puntaje y subir la energía. Por ejemplo, un vidrio con menor transmitancia reduce el exceso de luz natural, pero obliga a usar más luz artificial. El resultado muestra energía antes y después para que ese costo quede visible.

## API

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/health` | Estado del servidor. |
| GET | `/api/escenario` | Carga `data/datos_hotel.json` y devuelve la configuración, su resumen y la condición actual. |
| POST | `/api/validar` | Valida una configuración y devuelve un resumen. |
| POST | `/api/condicion_actual` | Análisis sin balance energético. |
| POST | `/api/balancear` | Balance completo, veredictos, sugerencias, reasignaciones, complejidad y reportes por franja. |
| POST | `/api/mejoras` | Mide cuatro mejoras fijas sobre la configuración enviada. |
| POST | `/api/reestructurar` | Busca una reestructuración dentro de los rangos. |

Cualquier error al procesar una solicitud devuelve HTTP 400 con un campo `error` en español. Una ruta POST que no existe devuelve HTTP 404.

### Respuesta del análisis

`/api/condicion_actual`, `/api/balancear` y la condición actual de `/api/escenario` devuelven `estado`, `resumen`, `generador`, `layout`, `habitabilidad`, `complejidad`, `temporal`, `energia_arbol`, `resultados`, `resumen_zonas`, `reasignaciones`, `sugerencias_habitabilidad` y `advertencias`. `resultados` solo se llena en `/api/balancear`. Sin balance no hay reasignaciones.

**`complejidad`** reúne los conteos de las estructuras de datos:

| Campo | Contenido | Escenario base |
|---|---|---|
| `grafo` | `fachadas`, `ventanas`, `pares_ingenuos`, `pares_evaluados`, `nodos_octree_visitados`, `aristas` | 8 fachadas, 154 ventanas, 1.232 pares ingenuos (8 × 154), 68 evaluados, 7.834 nodos visitados, 46 aristas (`TP-F-ESTE` → 24 ventanas de TG; `TG-F-OESTE` → 16 ventanas de TP; `TP-F-NORTE` → 6 ventanas de recreaciones de TG) |
| `reasignacion` | `huespedes_a_mover`, `habitaciones`, `comparaciones_lineales` (`G · H`), `comparaciones_avl`, `comparaciones_construccion` y `avl` (`tamano_inicial`, `altura_inicial`, `tamano_final`, `eliminaciones`, `rotaciones`) | 0 huéspedes a mover; AVL de 78 habitaciones, altura 7, 58 rotaciones, 417 comparaciones de construcción |
| `temporal` | `rojo_negro` (`tamano`, `altura`, `rotaciones`) y, solo en `/api/balancear`, `avl` con los mismos campos | Ver [Índice temporal](#índice-temporal) |

**`temporal`** es una lista con un reporte por franja. Cada reporte trae `etiqueta`, `inicio`, `fin`, `resultados`, `energia_wh`, `energia_kwh`, `energia_por_actividad_wh`, `energia_por_torre_wh`, `hora_pico`, `potencia_pico_w`, `deficit_residual_lux_h`, `energia_no_asignada_wh`, `zonas_con_deficit`, `zonas_criticas`, `horas_deficit_por_zona`, `horas_con_deficit`, `estados_por_zona`, `comparaciones_arbol` y `comparaciones_lineales`.

**`reasignaciones`** es una lista con una entrada por huésped a mover: `huesped_id`, `habitacion_actual`, `habitacion_propuesta`, `estado` (`PROPUESTA` o `NO_HAY_ALTERNATIVA`), `score`, `motivo`, `descartadas` (`habitacion_id`, `score`, `motivo`) y `restricciones`.

## Documentación

| Documento | Contenido |
|---|---|
| `docs/guia-funcionamiento.md` | Recorrido paso a paso de lo que hace el sistema con los datos, en el orden en que se ejecuta. |
| `docs/entregable/architecture-proyecto-cc1-iluminacion.md` | Arquitectura: decisiones, clases, reglas de cálculo, flujo y complejidad. |
| `docs/entregable/plan-proyecto-cc1-iluminacion.md` | Plan del proyecto: objetivos, alcance, escenario, métricas y casos de prueba. |
| `docs/entregable/entregable-propuesta-simulacion-luminica.md` | Propuesta de simulación: entradas, salidas, modelo de iluminación y algoritmos. |
| `docs/entregable/entregable-arquitectura-iluminacion.tex` | Documento del entregable en LaTeX (formato ICONTEC). Usa `diagrama-clases-hotel.png`, que se exporta desde el `.mmd`. |
| `docs/entregable/diagrama-clases-hotel.mmd` | Diagrama de clases en Mermaid. |

## Estructura

```text
data/datos_hotel.json       Escenario de referencia con torres TP y TG
docs/                       Guía de funcionamiento y documentos del entregable
data/casos_prueba/          Ocho casos sobre el hotel completo, cada uno con su historia y resultado esperado
src/modelo.py               Entidades, enumeraciones y factor de luz del perfil climático
src/geometria.py            Vectores, cajas, rayos, Snell y Fresnel
src/octree.py               Índice espacial con consultas de rayo y de radio
src/influencia.py           Grafo fachada → ventana de la otra torre (reflexión exterior de primer orden) y obstrucción del cielo
src/clima.py                Curva solar, luz base y periodos del día
src/io_datos.py             Carga, valores por defecto y validación del JSON
src/simulacion.py           Recorrido de 24 horas en pasos de 30 minutos
src/balance.py              Modos por horario, nivel de emergencia, cola de prioridad y energía por torre y piso
src/evaluacion.py           Estados instantáneos y resúmenes por zona
src/habitabilidad.py        Puntaje, veredictos y recomendaciones
src/arboles.py              AVL (inserción, eliminación, sucesor, rango) y rojo-negro (inserción, rango)
src/reasignacion.py         Reasignación de huéspedes con bolsa AVL y restricciones
src/temporal.py             Índice rojo-negro de resultados y reportes por franja horaria
src/mejoras.py              Cuatro mejoras fijas medidas con simulación
src/reestructuracion.py     Búsqueda de reestructuración de actividades
src/sugerencias.py          Recomendaciones calculadas con datos del modelo
src/api.py                  Servidor HTTP y endpoints JSON
src/main.py                 Ejecución por línea de comandos y reportes
tests/test_casos_plan.py    Los 10 casos de prueba del plan con unittest
tests/test_casos_json.py    Ejecuta y verifica cada caso de data/casos_prueba/
web/index.html              Estructura de la interfaz
web/app.js                  Formularios, plano, franjas, resultados y búsquedas
web/styles.css              Estilos
```

## Limitaciones conocidas

- La geometría de cada habitación (24 m², una ventana de 2 m²) está fija en `src/io_datos.py`. En la interfaz se edita su orientación, no sus dimensiones.
- La reflexión exterior entre torres es de primer orden: la luz que refleja una fachada no se vuelve a reflejar.
- La luz artificial usa un `CU` fijo de 0,70. Ese factor del método de lúmenes ya incluye el rebote interior, por eso no se le suma reflexión aparte, pero no cambia con el color de la pared.
- Las superficies interiores de cada recinto se representan con un solo valor de reflectancia (el de su pared).
- Las ventanas están ubicadas dentro de la caja de su torre. Para la reflexión exterior se usa su punto de salida en la fachada hacia la que miran.
- La precipitación de los perfiles climáticos es informativa: se carga y se reporta, pero no entra en el cálculo.
- El nivel de emergencia de 10 lux es un supuesto del proyecto, cercano al promedio de 1 pie-candela (10,8 lux) que pide NFPA 101 para rutas de evacuación.
- El árbol de energía solo agrega resultados. No decide la distribución de potencia: el reparto lo hace la cola de prioridad en `src/balance.py`.
- La búsqueda de reestructuración no es exhaustiva. Con un presupuesto de 30 evaluaciones puede no encontrar la mejor combinación.
- Los rangos de la reestructuración son supuestos del proyecto. No son una transcripción normativa del RETILAP.
