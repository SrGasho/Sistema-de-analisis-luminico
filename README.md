# Sistema de análisis lumínico

Proyecto de Ciencias de la Computación 1 para analizar la iluminación y el balance energético de un hotel de dos torres en Bogotá: la Torre Pequeña (`TP`) y la Torre Grande (`TG`). Las zonas se identifican con la abreviatura de su torre, por ejemplo `TP-H-101` (habitación) o `TG-COC-01` (cocina).

Los datos de clima vienen de NASA POWER (promedios 2001–2020 para Bogotá). El resto del escenario es sintético. Los resultados son aproximaciones educativas y no reemplazan un diseño fotométrico, eléctrico o arquitectónico, ni certifican cumplimiento normativo.

## Qué calcula el sistema

- **Entradas completas.** Torres, pisos, habitaciones, zonas comunes, perfiles de iluminación, horarios, vidrios, paredes, orientaciones de ventanas, generador y huéspedes. Los acabados se definen por actividad y pueden personalizarse por recinto en `zonas_personalizadas` (pared, vidrio, orientaciones y `luminaria_w`, la potencia de la luminaria del recinto; `0` representa una luminaria dañada). `luminaria_w` debe ser un número mayor o igual a 0 y solo se edita en el JSON, no desde la interfaz.
- **Posición del sol.** `direccion_solar` (`src/clima.py`) calcula el sol real de Bogotá: latitud φ = 4,711° N (`parametros_evaluacion.ubicacion.latitud`), declinación de Cooper `δ = 23,45° · sen(360° · (284 + n) / 365)` y ángulo horario `ω = 15° · (hora − 12)`. El vector hacia el sol es `x = −cos δ · sen ω` (este), `y = sen δ · cos φ − cos δ · sen φ · cos ω` (norte) y `z = sen δ · sen φ + cos δ · cos φ · cos ω` (arriba). La hora se toma como hora solar. Cada perfil climático trae su `dia_del_anio` `n`: 46 (febrero) para `NUBES_PARCIALES` y `CIELO_DESPEJADO`, 105 (abril) para `LLUVIOSO` y 135 (mayo) para `NUBLADO`. En febrero el sol de mediodía está a 72,0° de altura y hacia el sur; a las 7:00 está a 13,4° y a las 9:00 a 41,8°. En abril el mediodía llega a 85,3° y en mayo a 75,9°, hacia el norte.
- **Luz natural.** La luz global sobre un plano horizontal es `G = K_lux · factor_luz · max(0, sen(altura del sol))` entre 06:00 y 18:00 (0 fuera de esa franja), con `K_lux = 900` y `factor_luz = radiación / radiación de cielo despejado` (7,063 kWh/m²/día), calculado en `PerfilClimatico.factor_luz`. En febrero con nubes parciales `G` vale 143,9 lux a las 7:00, 413,3 a las 9:00, 589,3 a las 12:00, 413,3 a las 15:00 y 66,8 a las 17:30. `G` se reparte en directa horizontal `G · (1 − kd)` y difusa horizontal `G · kd`, que suman `G`. La fracción difusa diaria `kd` sale de la correlación de Erbs, Klein y Duffie con el índice de claridad `KT = radiación / H0` (ver [Fuentes y fórmulas](#fuentes-y-fórmulas)); da 0,445 con nubes parciales, 0,484 nublado, 0,503 lluvioso y 0,248 con cielo despejado. Sobre una ventana vertical (cielo isotrópico de Liu y Jordan) la directa es `directa horizontal · cos θ / sen(altura)`, con una altura mínima de 5°, y la difusa es `0,5 · difusa horizontal · (1 − obstrucción) + 0,5 · ρ_suelo · G`, con `ρ_suelo = 0,20` (`parametros_evaluacion.luz.reflectancia_suelo`). Si la otra torre le hace sombra a la ventana, la directa es 0. La luz que entra es `VLT · (directa · factor angular + difusa)`. La obstrucción es `Σ cos_ventana × factor de vista` de las fachadas que la ventana tiene enfrente (máximo 1). En el escenario base 40 ventanas tienen obstrucción; `TP-H-101-V1`, al este y frente a TG, tiene 0,593.
- **Refracción en el vidrio.** Para la componente directa se calcula el ángulo de refracción con la ley de Snell (índice 1,5) y la transmitancia de Fresnel no polarizada en las dos caras del vidrio. El resultado se normaliza con la incidencia perpendicular, así que a 0° se conserva la transmitancia visible del catálogo (`factor_angular_vidrio` en `src/geometria.py`). La componente difusa usa la transmitancia del catálogo.
- **Luz reflejada.** Solo de día, y con dos partes que se suman:
  - **Reflexión interior.** Método de flujo dividido: `E_ri = Φ · ρ / (A_int · (1 − ρ))`. `Φ` es la suma, por ventana, de (luz natural + luz exterior reflejada) × área de la ventana; `ρ` es la reflectancia de la pared del recinto; `A_int = 2 · área + 4 · √área · 3 m` (una habitación de 24 m² da `A_int ≈ 106,8 m²`). Con pared blanca (`ρ = 0,80`) el factor `ρ / (1 − ρ)` vale 4. Promedia todos los rebotes dentro del recinto, así que el color de la pared cambia la luz de su propio cuarto.
  - **Reflexión exterior entre torres.** Sale del grafo de influencia `fachada → ventana de la otra torre`. Cada torre tiene 4 fachadas (N, S, E, O) con la reflectancia del campo `fachada` de la torre en el JSON (por defecto `GRIS_CLARO`, 0,60). Para cada ventana se toma su punto de salida en la fachada de su torre y `consultar_radio` (18 m) sobre el octree entrega las fachadas candidatas de la otra torre. Se exige que ventana y fachada se miren y que un rayo entre ellas no cruce otra torre. El peso es `ρ_fachada × cos_fachada × cos_ventana × A_f / (π · d² + A_f)`, con `d` la distancia al punto más cercano de la fachada. Cada fachada recibe la luz de una superficie vertical sin obstrucción: `directa horizontal · max(0, n · sol) / sen(altura) + 0,5 · difusa horizontal + 0,5 · ρ_suelo · G` (`TG-F-OESTE` recibe 133,2 lux a las 9:00, 190,0 a las 12:00 y 370,0 a las 15:00), y la luz exterior que entra por una ventana es `Σ luz_fachada × peso × VLT`. Esta parte es de primer orden: la luz reflejada por una fachada no vuelve a reflejarse en otra.
- **Modos de operación.** Cada zona tiene un modo en cada paso: `ACTIVA` dentro de su horario, `REDUCIDA` fuera de él, `CERRADA` en su franja de cierre (cocina de 23:00 a 05:00 y recreación de 00:00 a 07:00; si las dos franjas se cruzan, manda la activa) y `EMERGENCIA` cuando el generador no alcanza para cubrir su mínimo. Habitaciones y parqueadero nunca cierran.
- **Balance energético.** Asigna la potencia del generador en cada paso de 30 minutos, en este orden: primero un nivel de emergencia de 10 lux para todas las zonas abiertas, luego los mínimos (parqueadero como seguridad, después habitaciones ocupadas y después el resto) y al final los objetivos por prioridad. El orden se resuelve con una cola de prioridad (`heapq`). Las zonas cerradas no consumen. Lo que el generador ya entregó en el instante lo lleva la clase `Reparto` (`src/balance.py`) en un contador `usado`, así que cada entrega cuesta O(1) y el instante completo O(Z log Z), con Z zonas.
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

Son 25 pruebas en dos archivos y tardan unos 8 segundos:

- `tests/test_casos_plan.py` cubre los 10 casos de prueba del plan del proyecto: ventana al sol sin obstáculo (además comprueba que directa horizontal + difusa horizontal = `G`), ventana sombreada por la otra torre, transmisión con cada vidrio (incluye Snell y Fresnel), luz reflejada (aristas solo de fachada a ventanas de la otra torre, peso ≤ reflectancia, reflejada = exterior + interior, pared oscura con menos reflejada que una blanca), noche, generador que alcanza para mínimos pero no para objetivos, reasignación con y sin candidata, zona cerrada y cielo nublado contra despejado.
- `tests/test_casos_json.py` ejecuta el escenario base y cada caso de `data/casos_prueba/`. Comprueba que el resultado coincida con el bloque `caso.resultado_esperado` del JSON, que se cumplan las reglas comunes (de noche no hay luz natural, una zona cerrada no consume, un paso en emergencia cuenta como déficit, el generador no se pasa de su capacidad, ninguna habitación recibe más huéspedes que camas libres, ningún déficit sale de un error de redondeo) y el comportamiento propio de cada caso.

### Casos de prueba

Todos parten del hotel completo de `datos_hotel.json` (dos torres y 78 huéspedes). Cada archivo tiene un bloque `caso` con la historia, lo que se espera ver y los números esperados, para poder leer el resultado.

En el escenario base las 127 zonas son `HABITABLE` (52 de ellas con causa `EXCESO_SOLAR` en algunos pasos). El puntaje ponderado es 0,9718 (día 0,9436, noche 1,0), la energía 208.075,0 Wh y el pico del generador 15.933,7 W a las 18:00. De los 6.096 estados, 5.517 son confortables, 319 exceso leve, 260 cerrados y ninguno déficit. Nadie se reasigna.

Los resultados de los casos se dan como habitables / casi habitables / no habitables:

| Caso | Situación | Qué muestra |
|---|---|---|
| `temporada_lluvias` | Abril, cielo cubierto | 127/0/0; la energía sube a 210.495,2 Wh porque hay menos luz natural. |
| `mayo_nublado` | 15 de mayo, cielo nublado; el sol del mediodía pasa por el norte (75,9° de altura) | 127/0/0; se invierte febrero: las habitaciones con ventana al sur gastan más energía (24.950 Wh en el día, contra 19.753 de las del norte); a las 12:00 `TP-H-102` (norte) no usa luz artificial y `TP-H-104` (sur) usa 14,2 W. |
| `generador_alta_demanda` | Generador de 17 kW | 127/0/0, los mismos veredictos del escenario base, pero el generador queda en `ALTA_DEMANDA`. |
| `deficit_leve` | Las 12 habitaciones ocupadas del piso 2 de TG (`TG-H-113` a `TG-H-124`) con luminarias viejas de 30 W (`luminaria_w = 30`) | 115/12/0; con 30 W dan como máximo 70 lux, entre la mitad del mínimo y el mínimo de 100, así que las 12 quedan casi habitables por `DEFICIT_NOCTURNO`; ningún paso es `DEFICIT_SEVERO`, nadie entra en `EMERGENCIA` y nadie se reasigna. |
| `deficit_severo` | Generador de 4 kW | 59/0/68; el generador alcanza para los parqueaderos y las habitaciones ocupadas de los pisos 2 en adelante; las del piso 1, las vacías, cocinas y recreaciones pasan 660 pasos en `EMERGENCIA`; los 22 huéspedes de habitaciones no habitables reciben la cama libre de una habitación habitable. |
| `apagon_generador` | Generador de 0 kW | 0/0/127; los 78 huéspedes sin alternativa. |
| `cielo_despejado` | Febrero con cielo despejado | 75/52/0; las 52 casi habitables son habitaciones con ventana al este o al oeste, con causa `EXCESO_SOLAR` por el sol bajo de la mañana o de la tarde; nadie se reasigna. |
| `exceso_severo` | Cielo despejado y las 24 habitaciones ocupadas de TP con vidrio claro y ventana al este | 69/58/0; 18 de esas 24 quedan casi habitables, con `EXCESO_SEVERO` entre las 6:30 y las 10:00; las otras 6 siguen habitables porque TG les hace sombra en la mañana; nadie se reasigna. |
| `luminarias_danadas` | 16 habitaciones ocupadas de TP, pisos 1 y 2 (`TP-H-101` a `TP-H-116`), con `luminaria_w = 0` | 111/0/16; las 16 quedan no habitables por `DEFICIT_NOCTURNO` y sus 16 huéspedes se mueven: H-001 (`MISMA_TORRE`) a `TP-H-120`, H-002 (`PISO_MAXIMO:2`) a `TG-H-112` y H-003 (`ORIENTACION:ESTE`) a `TG-H-101`. |
| `reasignacion_restringida` | Las 24 habitaciones ocupadas de TP sin luminaria; H-001 a H-018 con `MISMA_TORRE`, H-019 y H-020 con `MISMA_TORRE` + `PISO_MAXIMO:2` | 103/0/24; 16 huéspedes llenan las 16 camas libres del piso 4 de TP; H-017 y H-018 reciben `SIN_CAPACIDAD`, H-019 y H-020 `RESTRICCIONES`, y H-021 a H-024 van a TG. |

Al cargar un escenario, cada perfil de actividad debe cumplir `0 ≤ mínimo ≤ objetivo ≤ máximo`; si no, la carga falla con un mensaje de error.

## Reasignación de huéspedes

Un huésped se reasigna solo si su habitación queda `NO_HABITABLE`.

- **Bolsa de habitaciones.** Las habitaciones `HABITABLE` con cama libre se guardan en un AVL con clave `(torre, piso, −calidad, habitacion_id)`, donde `calidad = w_luz · puntaje + w_energia · ahorro`.
- **Búsqueda.** Para cada huésped se consulta el sucesor de cada piso permitido y se resta una penalización por cambio de piso. Cuando una habitación se llena, se elimina del árbol, así que dos huéspedes no reciben la misma cama.
- **Restricciones.** Se definen en `huespedes.restricciones_por_huesped` del JSON. `MISMA_TORRE` y `PISO_MAXIMO:n` filtran candidatas. `ORIENTACION:ESTE|NORTE|OESTE|SUR` es una preferencia que suma `w_actividad` si la habitación coincide. Una restricción desconocida se rechaza al cargar.
- **Salida.** Cada propuesta trae `descartadas` (habitaciones revisadas, con motivo `MENOR_PUNTAJE`). Si no hay alternativa, `motivo` dice por qué: `SIN_HABITACIONES_HABITABLES_LIBRES`, `SIN_CAPACIDAD` o `RESTRICCIONES`.
- **Costo.** `O(G · F · log H)` con `G` huéspedes a mover, `F` pisos y `H` habitaciones, contra `O(G · H)` de la búsqueda lineal.

En el escenario base nadie queda en una habitación `NO_HABITABLE`. El AVL se construye igual con las 104 habitaciones habitables libres (altura 8, 80 rotaciones, 618 comparaciones de construcción) y no se consulta. `data/casos_prueba/luminarias_danadas.json` muestra huéspedes que sí se mueven, `reasignacion_restringida.json` los motivos `SIN_CAPACIDAD` y `RESTRICCIONES`, y `deficit_severo.json` el motivo `SIN_HABITACIONES_HABITABLES_LIBRES`.

En una prueba de carga sobre el escenario base, con 60 de las 78 habitaciones ocupadas marcadas `NO_HABITABLE`, el AVL hizo 2.792 comparaciones contra 6.240 de la búsqueda lineal, con 39 eliminaciones; con restricciones mezcladas, 3.289 contra 6.240.

## Índice temporal

Cada resultado de la simulación se inserta en un árbol rojo-negro con clave `(hora, zona_id)` apenas se calcula. Una franja `[inicio, fin)` se consulta con un recorrido de rango en `O(log R + k)`, contra `O(R)` de recorrer la lista.

Las franjas fijas son: día completo, 00–06, 06–12, 12–18, 18–22 y 22–24. Para cada una se reporta energía en Wh y kWh, energía por actividad y por torre, hora y potencia pico del generador, déficit residual (lux·h bajo el mínimo), energía no asignada (Wh que habrían cerrado ese déficit, sin pasar de la potencia de la luminaria), zonas críticas (las 10 con más horas en déficit), horas con déficit por zona, instantes con déficit y estado predominante de cada zona.

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

`/api/condicion_actual`, `/api/balancear` y la condición actual de `/api/escenario` devuelven `estado`, `resumen`, `generador`, `layout`, `habitabilidad`, `complejidad`, `temporal`, `energia_arbol`, `resultados`, `resumen_zonas`, `lineas_zonas`, `reasignaciones`, `sugerencias_habitabilidad` y `advertencias`. `resultados` solo se llena en `/api/balancear`. `lineas_zonas` trae el día de cada zona, media hora por media hora, como `[hora, modo, natural, reflejada, artificial, total, estado, mínimo, máximo]`; lo usa el gráfico «Cómo le fue en el día», que aparece debajo del plano al elegir una zona. Sin balance no hay reasignaciones.

**`complejidad`** reúne los conteos de las estructuras de datos:

| Campo | Contenido | Escenario base |
|---|---|---|
| `grafo` | `fachadas`, `ventanas`, `pares_ingenuos`, `pares_evaluados`, `nodos_octree_visitados`, `aristas` | 8 fachadas, 154 ventanas, 1.232 pares ingenuos (8 × 154), 68 evaluados, 7.834 nodos visitados, 46 aristas (`TP-F-ESTE` → 24 ventanas de TG; `TG-F-OESTE` → 16 ventanas de TP; `TP-F-NORTE` → 6 ventanas de recreaciones de TG) |
| `reasignacion` | `huespedes_a_mover`, `habitaciones`, `comparaciones_lineales` (`G · H`), `comparaciones_avl`, `comparaciones_construccion` y `avl` (`tamano_inicial`, `altura_inicial`, `tamano_final`, `eliminaciones`, `rotaciones`) | 0 huéspedes a mover; AVL de 104 habitaciones, altura 8, 80 rotaciones, 618 comparaciones de construcción |
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
data/casos_prueba/          Nueve casos sobre el hotel completo, cada uno con su historia y resultado esperado
src/modelo.py               Entidades, enumeraciones y factor de luz del perfil climático
src/geometria.py            Vectores, cajas, rayos, Snell y Fresnel
src/octree.py               Índice espacial con consultas de rayo y de radio
src/influencia.py           Grafo fachada → ventana de la otra torre (reflexión exterior de primer orden) y obstrucción del cielo
src/clima.py                Posición del sol, luz global, fracción difusa, luz sobre superficies verticales y periodos del día
src/io_datos.py             Carga, valores por defecto y validación del JSON
src/simulacion.py           Recorrido de 24 horas en pasos de 30 minutos
src/balance.py              Modos por horario, nivel de emergencia, cola de prioridad, Reparto del generador y energía por torre y piso
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

## Fuentes y fórmulas

Cada fila indica si el valor es un **dato real** (medido o publicado por un tercero), una **fórmula publicada** o un **supuesto del proyecto**. `n` es el día del año, φ la latitud, δ la declinación, ω el ángulo horario y ωs el ángulo horario de la puesta del sol.

| Qué se calcula | Fórmula en el código | Fuente |
|---|---|---|
| Clima de Bogotá: radiación, nubosidad y precipitación por perfil | `perfiles_climaticos` en `data/datos_hotel.json`; radiación de cielo despejado 7,063 kWh/m²/día | **Dato real.** NASA POWER, Climatology API, 2001–2020: [power.larc.nasa.gov](https://power.larc.nasa.gov/); [metodología](https://power.larc.nasa.gov/docs/methodology/). La nubosidad y la precipitación se cargan pero son informativas. |
| Declinación solar | `δ = 23,45° · sen(360° · (284 + n) / 365)` (`declinacion_solar`) | **Fórmula publicada.** Cooper, P. I. (1969). The absorption of radiation in solar stills. *Solar Energy*, 12(3), 333–346. [doi:10.1016/0038-092X(69)90047-4](https://doi.org/10.1016/0038-092X(69)90047-4) |
| Posición del sol | `ω = 15° · (hora − 12)`; `x = −cos δ sen ω`, `y = sen δ cos φ − cos δ sen φ cos ω`, `z = sen δ sen φ + cos δ cos φ cos ω` (`direccion_solar`) | **Fórmula publicada.** Duffie, J. A. y Beckman, W. A. (2013). *Solar Engineering of Thermal Processes*, 4.ª ed., Wiley. [doi:10.1002/9781118671603](https://doi.org/10.1002/9781118671603). Verificación con [NOAA Solar Calculator](https://gml.noaa.gov/grad/solcalc/calcdetails.html). |
| Radiación extraterrestre diaria `H0` | `H0 = 24/π · Gsc · (1 + 0,033 cos(360n/365)) · (cos φ cos δ sen ωs + ωs sen φ sen δ)`, `Gsc = 1,367 kW/m²` (`radiacion_extraterrestre_diaria`) | **Fórmula publicada.** Duffie y Beckman (2013), ec. 1.10.3. |
| Fracción difusa diaria `kd` | `KT = radiación / H0` (acotado a 0,3–0,8); para ωs > 81,4°: `kd = 1,311 − 3,022 KT + 3,427 KT² − 1,821 KT³` (`fraccion_difusa_diaria`) | **Fórmula publicada.** Erbs, D. G., Klein, S. A. y Duffie, J. A. (1982). Estimation of the diffuse radiation fraction for hourly, daily and monthly-average global radiation. *Solar Energy*, 28(4), 293–302. [doi:10.1016/0038-092X(82)90302-4](https://doi.org/10.1016/0038-092X(82)90302-4) |
| Luz global horizontal `G` | `G = K_lux · factor_luz · max(0, sen altura)` entre 06:00 y 18:00; `factor_luz = radiación / 7,063` (`luz_base`) | **Supuesto del proyecto** para `K_lux = 900` (conversión a lux de referencia, sin calibración fotométrica). La radiación es dato real (NASA POWER). |
| Directa sobre superficie vertical (factor Rb) | `directa horizontal · cos θ / max(sen altura, sen 5°)` (`directa_en_vertical`) | **Fórmula publicada** (Duffie y Beckman, 2013). La altura mínima de 5° es un **supuesto del proyecto**. |
| Difusa sobre superficie vertical (cielo isotrópico) | `0,5 · difusa horizontal · (1 − obstrucción) + 0,5 · ρ_suelo · G` (`difusa_en_vertical`) | **Fórmula publicada.** Liu, B. Y. H. y Jordan, R. C. (1960). The interrelationship and characteristic distribution of direct, diffuse and total solar radiation. *Solar Energy*, 4(3), 1–19. [doi:10.1016/0038-092X(60)90062-1](https://doi.org/10.1016/0038-092X(60)90062-1). `ρ_suelo = 0,20` es un **supuesto del proyecto** (valor típico). |
| Refracción y transmitancia del vidrio | Snell `sen θt = sen θi / n`, Fresnel no polarizada en dos caras, normalizada a 0° (`factor_angular_vidrio`) | **Fórmula publicada.** Hecht, E. (2017). *Optics*, 5.ª ed., Pearson; Edmund Optics, [Introduction to Basic Ray Optics](https://www.edmundoptics.com/knowledge-center/application-notes/optics/introduction-to-basic-ray-optics/). |
| Reflexión interior (flujo dividido) | `E_ri = Φ · ρ / (A_int · (1 − ρ))` (`reflexion_interior`) | **Fórmula publicada.** Hopkinson, R. G., Petherbridge, P. y Longmore, J. (1966). *Daylighting*. Heinemann. |
| Luz artificial (método de lúmenes) | `E = eficacia · P · CU · MF / área` | **Fórmula publicada.** IES Lighting Handbook (Illuminating Engineering Society). `CU = 0,70`, `MF = 0,80` y 100 lm/W son **supuestos del proyecto**. |
| Factor de vista de una fachada | `A_f / (π · d² + A_f)` (grafo de influencia y obstrucción) | **Supuesto del proyecto.** Aproximación propia; no viene de una fuente. |
| Transmitancia visible de los vidrios | 0,82, 0,71 y 0,52 | **Dato real.** Cardinal Glass: [LoE2-272/270](https://www.cardinalcorp.com/products/coated-glass/loe2-272-270/) y [Quad LoE-452+](https://www.cardinalcorp.com/products/coated-glass/quad-loe-452-plus/). |
| Áreas de referencia de las torres | 4.013 m² y 11.346 m² | **Dato real** como inspiración: DOE [Commercial Reference Buildings](https://www.energy.gov/cmei/buildings/commercial-reference-buildings). La geometría de cajas, zonas y ventanas es sintética. |
| Niveles mínimo, objetivo y máximo por actividad | `perfiles_iluminacion` | **Supuesto del proyecto** (presets educativos) contrastado con [RETILAP](https://www.minenergia.gov.co/es/misional/energia-electrica-2/reglamentos-tecnicos/reglamento-t%C3%A9cnico-de-iluminaci%C3%B3n-y-alumbrado-p%C3%BAblico-retilap/) y [UNE-EN 12464-1](https://revista.une.org/46/iluminacion-de-los-lugares-de-trabajo-en-interiores.html); no es una transcripción normativa. |
| Nivel de emergencia | 10 lux (`parametros_evaluacion.emergencia.nivel_lux`) | **Supuesto del proyecto**, cercano a 1 pie-candela (10,8 lux) de [NFPA 101](https://www.nfpa.org/codes-and-standards/nfpa-101-standard-development/101). |

También son **supuestos del proyecto**: `K_lux = 900`, los umbrales de clasificación (0,50 y 1,25) y de habitabilidad (0,90 y 0,75), los horarios, los pesos de prioridad y de reasignación, el factor de vista, la reflectancia del suelo 0,20 y la altura mínima de 5°.

Valores que da el modelo con estos datos:

| Perfil | `n` | `H0` (kWh/m²/día) | `KT` | `kd` |
|---|---:|---:|---:|---:|
| `NUBES_PARCIALES` (febrero) | 46 | 10,05 | 0,484 | 0,445 |
| `NUBLADO` (mayo) | 135 | 10,06 | 0,445 | 0,484 |
| `LLUVIOSO` (abril) | 105 | 10,41 | 0,428 | 0,503 |
| `CIELO_DESPEJADO` (febrero) | 46 | 10,05 | 0,703 | 0,248 |

Como directa y difusa suman `G`, más radiación da más luz. La luz natural del hotel en el día completo queda ordenada así: `CIELO_DESPEJADO` 534.973 > `NUBES_PARCIALES` 396.651 > `NUBLADO` 385.199 > `LLUVIOSO` 370.265 (suma de lux de todas las zonas en los 48 pasos).

## Limitaciones conocidas

- La geometría de cada habitación (24 m², una ventana de 2 m²) está fija en `src/io_datos.py`. En la interfaz se edita su orientación, no sus dimensiones.
- La reflexión exterior entre torres es de primer orden: la luz que refleja una fachada no se vuelve a reflejar.
- Las fachadas se modelan como superficies opacas de un solo color. El vidrio de las ventanas no se usa como fuente de reflexión: la luz que el vidrio refleja hacia afuera (la pérdida de Fresnel) se descuenta y no ilumina la otra torre. En una fachada con mucho vidrio ese reflejo puede ser fuerte y concentrado; no se calcula.
- La luz artificial usa un `CU` fijo de 0,70. Ese factor del método de lúmenes ya incluye el rebote interior, por eso no se le suma reflexión aparte, pero no cambia con el color de la pared.
- Las superficies interiores de cada recinto se representan con un solo valor de reflectancia (el de su pared).
- Las ventanas están ubicadas dentro de la caja de su torre. Para la reflexión exterior se usa su punto de salida en la fachada hacia la que miran.
- La nubosidad y la precipitación de los perfiles climáticos son informativas: se cargan y se reportan, pero no entran en el cálculo. El efecto de las nubes llega por la radiación (`factor_luz` y `KT`).
- La hora se trata como hora solar. Bogotá está a −74,07° y usa UTC−5 (meridiano de −75°), así que la diferencia con la hora del reloj es de unos minutos más la ecuación del tiempo.
- La fracción difusa es diaria: se usa una sola para todo el día, no una por hora.
- Con el sol muy bajo, la luz directa sobre una ventana o fachada vertical se limita usando una altura mínima de 5°, para que el factor `cos θ / sen(altura)` no se dispare al amanecer y al atardecer.
- `luminaria_w` solo se edita en el JSON (`zonas_personalizadas`); la interfaz no tiene un campo para cambiarla.
- El nivel de emergencia de 10 lux es un supuesto del proyecto, cercano al promedio de 1 pie-candela (10,8 lux) que pide NFPA 101 para rutas de evacuación.
- El árbol de energía solo agrega resultados. No decide la distribución de potencia: el reparto lo hace la cola de prioridad en `src/balance.py`.
- La búsqueda de reestructuración no es exhaustiva. Con un presupuesto de 30 evaluaciones puede no encontrar la mejor combinación.
- Los rangos de la reestructuración son supuestos del proyecto. No son una transcripción normativa del RETILAP.
