# Plan del sistema educativo de iluminación y balance energético hotelero

## Proyecto de Ciencias de la Computación 1

## 1. Resumen

El proyecto propone diseñar e implementar un sistema educativo que estime la iluminación de un hotel de dos torres ubicado en Bogotá. El hotel se analiza durante 24 horas y contiene cuatro actividades: habitaciones, cocina, recreación y parqueadero.

El sistema combina un árbol jerárquico, un Octree, un grafo dirigido ponderado, un árbol AVL, un árbol rojo-negro, una cola de prioridad y recorridos de agregación. Durante el día calcula luz natural con la radiación real de NASA POWER, transmisión por vidrio con refracción de Snell y transmitancia de Fresnel, reflexión interior de cada recinto, reflexión de primer orden entre las fachadas de las dos torres y luz artificial complementaria. Durante la noche toma la luz solar como cero y distribuye la potencia artificial disponible mediante un balance heurístico.

El modelo no pretende sustituir un diseño fotométrico, eléctrico o arquitectónico profesional. Las torres, zonas, huéspedes, luminarias y potencias son datos sintéticos didácticos; las fuentes publicadas se distinguen explícitamente de los supuestos del proyecto.

## 2. Contexto y problema computacional

La iluminación de una zona hotelera depende de la orientación, la hora, el clima, las sombras, el vidrio, las paredes reflectantes, la actividad y la disponibilidad de iluminación artificial. Además, de noche el generador puede no alcanzar para llevar todas las zonas a su objetivo al mismo tiempo.

Dado un hotel con dos torres, pisos, zonas, ventanas, superficies, luminarias, huéspedes y un generador, el sistema debe:

1. Calcular la iluminación natural y reflejada de cada zona durante el día.
2. Calcular la iluminación artificial complementaria y nocturna.
3. Clasificar cada zona según su perfil de actividad y modo de operación.
4. Reservar primero un nivel de emergencia para todas las zonas abiertas y luego cubrir los mínimos de seguridad y de habitaciones ocupadas.
5. Distribuir la potencia restante según prioridad de actividad, piso y ocupación.
6. Medir potencia, energía, déficits y estados durante las 24 horas.
7. Proponer una habitación compatible cuando una habitación ocupada reciba el veredicto `NO_HABITABLE`.
8. Emitir un veredicto de habitabilidad por zona, medir mejoras y proponer reestructuraciones de las variables de luz.

La reasignación es una recomendación greedy: modifica la relación huésped–habitación en el modelo, no la geometría ni una reserva real.

## 3. Objetivo general

Diseñar e implementar un sistema de análisis lumínico y balance energético que utilice árboles, Octree, grafos y algoritmos de agregación para estudiar un hotel de dos torres en Bogotá durante un día completo.

## 4. Objetivos específicos

- Representar `Hotel → Torre → Piso → ZonaHotel → Ventana` mediante composición.
- Mantener exactamente dos torres fijas: `TP` (Torre Pequeña) y `TG` (Torre Grande).
- Representar habitaciones, cocinas, recreaciones y parqueaderos con zonas reutilizables.
- Usar un eje temporal único entre 00:00 y 24:00, sin clases diurnas/nocturnas duplicadas.
- Calcular sombras con cajas espaciales y consultas de Octree.
- Representar la reflexión entre torres mediante un grafo dirigido `fachada → ventana de la otra torre`, construido con consultas de radio del Octree.
- Calcular la reflexión exterior entre torres en primer orden y la reflexión interior de cada recinto con el método de flujo dividido.
- Incorporar tres presets de vidrio y cinco reflectancias educativas de pared y de fachada.
- Usar perfiles climáticos de Bogotá basados en NASA POWER, con la radiación real en el cálculo de la luz base.
- Calcular la refracción con la ley de Snell y la transmitancia de Fresnel según el ángulo de incidencia.
- Dimensionar y utilizar un generador exclusivo para iluminación.
- Clasificar zonas con rangos configurables por actividad y emitir un veredicto de habitabilidad por zona.
- Proponer reasignaciones de huéspedes cuando una habitación ocupada sea `NO_HABITABLE`, usando un AVL como bolsa de habitaciones habitables con cama libre.
- Indexar los resultados de la simulación en un árbol rojo-negro por `(hora, zona_id)` para consultar franjas horarias.
- Comparar con conteos medidos la complejidad de las versiones ingenuas y las que usan estructuras: pares evaluados en el grafo, comparaciones de la reasignación, nodos visitados por franja y rotaciones del rojo-negro contra el AVL.

## 5. Alcance

### 5.1 Incluido

- Hotel con exactamente dos torres.
- 4 pisos en `TP` y 6 pisos en `TG`.
- 32 y 72 habitaciones respectivamente.
- Cocinas, zonas recreativas y parqueaderos sintéticos.
- Ventanas con posición, normal, área y vidrio.
- Paredes con reflectancia nominal y cuatro fachadas por torre con la reflectancia del campo `fachada` de la torre (por defecto `GRIS_CLARO`, 0,60).
- Clima de Bogotá con perfiles de nubes parciales, nublado, lluvioso y cielo despejado.
- Simulación discreta de 24 horas.
- Luz natural, reflejada y artificial separadas.
- Modos `ACTIVA`, `REDUCIDA`, `CERRADA` y `EMERGENCIA`.
- Balance energético de nivel de emergencia, mínimos y objetivos.
- Puntuaciones, estados, déficits, energía consumida y veredicto de habitabilidad por zona.
- Reasignación heurística de huéspedes con restricciones y candidatos descartados.
- Reporte por franja horaria con el índice rojo-negro.
- Mejoras medidas y reestructuración de variables de luz: actividades (orientación de ventanas, objetivos), acabados (pared, vidrio), horarios y generador.
- Interfaz web con formularios de entradas, plano por torre y piso, selector de franja horaria, veredictos, sugerencias, mejoras medidas, reestructuración y tabla de estructuras de datos.
- Los 10 casos de prueba de la sección 12 como pruebas automáticas.

### 5.2 No incluido

- Diseño fotométrico profesional.
- Archivos IES/LDT o mallas arquitectónicas complejas.
- Deslumbramiento profesional, confort circadiano o modelo térmico.
- Consumo total del hotel, ascensores, climatización o agua caliente.
- Reflexión especular o reflexiones exteriores de segundo orden (de una fachada a otra).
- Cambios en la geometría de las torres. Las torres son fijas: el sistema no mueve ni rediseña edificios, pisos ni habitaciones. Las mejoras y la reestructuración solo cambian variables de luz (actividades, acabados, horarios y generador).
- Sistema real de reservas o traslado físico de huéspedes.
- Certificación normativa.

## 6. Escenario sintético reproducible

Las áreas de referencia se inspiran en modelos comerciales del DOE, pero la geometría y los registros siguientes son supuestos del proyecto. `TP` es la Torre Pequeña y `TG` la Torre Grande.

| Elemento | TP | TG | Regla común |
|---|---:|---:|---|
| Área de referencia | 4.013 m² | 11.346 m² | Plantilla educativa |
| Pisos | 4 | 6 | 3 m por piso |
| Habitaciones | 32 | 72 | 24 m², capacidad 2 |
| Cocinas | 4 | 6 | 35 m² |
| Recreaciones | 4 | 6 | 80 m² |
| Parqueaderos | 1 | 2 | 450 m² |
| Ventanas | 52 | 102 | Habitación 1, cocina 2, recreación 3 |
| Habitaciones ocupadas | 24 | 54 | 78 huéspedes en total |

Cajas espaciales:

```text
TP: x=0..32, y=0..31.35, z=0..12
TG: x=45..89, y=0..43,    z=0..18
separación horizontal aproximada: 13 m
```

Los IDs de zonas usan el prefijo de la torre: `TP-H-101` y `TG-H-101` para habitaciones, `TG-COC-01` para cocinas, y así para las demás actividades. Cada torre conserva su nombre completo como campo de presentación. Los huéspedes de prueba usan `H-001` a `H-078`. No representan personas reales.

Luminarias equivalentes por zona:

| Actividad | Potencia | Eficacia | CU | MF |
|---|---:|---:|---:|---:|
| Habitación | 72 W | 100 lm/W | 0,70 | 0,80 |
| Cocina | 200 W | 100 lm/W | 0,70 | 0,80 |
| Recreación | 450 W | 100 lm/W | 0,70 | 0,80 |
| Parqueadero | 720 W | 100 lm/W | 0,70 | 0,80 |

El generador se fija en 22,0 kW nominales, redondeando hacia arriba la demanda objetivo máxima más una reserva didáctica del 20 %. Sólo se dimensiona el subsistema de iluminación.

## 7. Perfiles, horarios y clasificación

Los siguientes son presets educativos. El RETILAP vigente debe consultarse para la categoría exacta, plano de trabajo, uniformidad, mantenimiento y demás requisitos. No se presentan como una transcripción normativa.

| Actividad | Mínimo | Objetivo | Máximo | Prioridad |
|---|---:|---:|---:|---:|
| Habitación activa | 100 lux | 200 lux | 300 lux | 3 |
| Cocina activa | 300 lux | 400 lux | 500 lux | 3 |
| Recreación activa | 200 lux | 300 lux | 500 lux | 2 |
| Parqueadero activo | 50 lux | 100 lux | 150 lux | 1 |

Horarios sintéticos:

```text
Habitaciones: 06:00–22:00 ACTIVA; 22:00–06:00 REDUCIDA
Cocinas:      06:00–22:00 ACTIVA; 23:00–05:00 CERRADA; resto REDUCIDA
Recreación:   08:00–23:00 ACTIVA; 00:00–07:00 CERRADA; resto REDUCIDA
Parqueaderos: 00:00–24:00 ACTIVA
```

Las habitaciones y los parqueaderos nunca cierran. Los horarios de apertura y de cierre están en el JSON (`horarios`) y se pueden editar. Si las dos franjas se cruzan, la franja activa manda; así la reestructuración puede extender la cocina hasta las 24:00. Los pasos `CERRADA` no reciben energía, quedan como `DATOS_INSUFICIENTES` y no cuentan en el puntaje de habitabilidad.

La emergencia usa un parámetro separado (`parametros_evaluacion.emergencia.nivel_lux`, 10 lux por defecto). No se deduce de los rangos normales. Es un supuesto cercano al promedio de 1 pie-candela (10,8 lux) que pide NFPA 101 para rutas de evacuación. El modo `EMERGENCIA` no tiene horario: lo asigna el balance a la zona que no alcanza su mínimo porque el generador se agotó. Esa zona se clasifica contra el mínimo de su modo de horario, así que el paso cuenta como déficit.

Para una zona `z` y un instante `t`:

```text
E_total(z,t) = E_natural(z,t) + E_reflejada(z,t) + E_artificial(z,t)
```

Durante la noche:

```text
E_natural = 0
E_reflejada_solar = 0
E_total = E_artificial
```

La clasificación individual es:

```text
E < 0,50 × mínimo       → DEFICIT_SEVERO
0,50 × mínimo ≤ E < min → DEFICIT_LEVE
mínimo ≤ E ≤ máximo     → CONFORTABLE
máximo < E ≤ 1,25×max  → EXCESO_LEVE
E > 1,25 × máximo       → EXCESO_SEVERO
faltan datos o CERRADA   → DATOS_INSUFICIENTES
```

Los factores 0,50 y 1,25 son reglas del proyecto, no valores normativos.

El veredicto de habitabilidad resume los pasos evaluables de cada zona. Cada paso aporta `q = 1` si es confortable, `q = 0,5` si es déficit o exceso leve, y `q = 0` si es severo. El puntaje es el promedio de `q`:

```text
puntaje ≥ 0,90                              → HABITABLE
0,75 ≤ puntaje < 0,90                       → CASI_HABITABLE
puntaje < 0,75 o déficit severo > 5 % pasos → NO_HABITABLE
```

## 8. Clima, vidrio y paredes

La ubicación de referencia es Bogotá, aproximadamente 4.7110° N, -74.0721° O. Se usan perfiles derivados de NASA POWER (2001–2020) con radiación, nubosidad y precipitación. La precipitación se carga y se reporta, pero es informativa: no entra en el cálculo.

La luz base usa la radiación del perfil activo:

```text
E_base(t)  = K_lux × C(t) × factor_luz
factor_luz = radiación / radiación de cielo despejado
C(t)       = sen(π × (t − 6) / 12) entre 06:00 y 18:00; 0 fuera de esa franja
```

`K_lux` es una conversión calibrable a lux de referencia (900, en `parametros_evaluacion.luz.lux_por_irradiancia`). La radiación de cielo despejado es 7,063 kWh/m²/día. El factor se calcula en el código (`PerfilClimatico.factor_luz`), no se escribe a mano:

| Perfil | Radiación (kWh/m²/día) | Nubosidad | `factor_luz` |
|---|---:|---:|---:|
| `NUBES_PARCIALES` | 4,863 | 0,7089 | 0,689 |
| `NUBLADO` | 4,477 | 0,8582 | 0,634 |
| `LLUVIOSO` | 4,454 | 0,8487 | 0,631 |
| `CIELO_DESPEJADO` | 7,063 | 0,0 | 1,000 |

La nubosidad `c` reparte la luz en directa y difusa: `f_directa = max(0,10; 1 − c)` y `f_difusa = 0,15 + 0,45 × c`.

Vidrios:

| Preset | Transmitancia visible | Uso sintético |
|---|---:|---|
| `VIDRIO_CLARO` | 0,82 | Habitaciones y fachadas de baja protección |
| `VIDRIO_LOW_E` | 0,71 | Habitaciones y zonas generales |
| `VIDRIO_CONTROL_SOLAR` | 0,52 | Exposición solar alta |

Paredes:

```text
Blanco 0,80   Crema 0,70   Gris claro 0,60
Gris medio 0,45   Oscuro 0,25
```

Para la luz directa, cada ventana calcula el ángulo de refracción con la ley de Snell (`sen θt = sen θi / n`, con `n = 1,5`). Con ese ángulo calcula la transmitancia de Fresnel no polarizada, promedio de las componentes s y p, en las dos caras del vidrio. El resultado se normaliza con la incidencia perpendicular (`factor_angular_vidrio` en `geometria.py`), así que a 0° se conserva la transmitancia visible del catálogo:

| Incidencia | 30° | 45° | 60° | 75° | 85° |
|---|---:|---:|---:|---:|---:|
| Factor angular | 0,997 | 0,979 | 0,900 | 0,605 | 0,163 |

La luz difusa usa la transmitancia visible del catálogo sin factor angular. Por ventana:

```text
E_ventana = E_base × VLT × (cos θi × factor_angular × f_directa + f_difusa)
```

Si la ventana está en sombra, `cos θi` se toma como cero y solo queda la difusa. La otra torre también tapa parte del cielo: la difusa se multiplica por `1 − obstrucción`, con `obstrucción = Σ cos_ventana × factor de vista` de las fachadas que la ventana tiene enfrente (máximo 1). En el escenario base 40 ventanas tienen obstrucción; `TP-H-101-V1` (al este, frente a TG) tiene 0,593. La luz natural de la zona es el promedio de sus ventanas.

La luz reflejada sólo existe de día y suma dos partes:

```text
E_reflejada = E_exterior + E_ri

Reflexión exterior entre torres (primer orden):
E_exterior(ventana) = Σ luz_fachada × peso × VLT
luz_fachada         = E_base × (max(0, n · sol) × f_directa + f_difusa)
peso                = ρ_fachada × cos_fachada × cos_ventana × A_f / (π·d² + A_f)

Reflexión interior (flujo dividido):
E_ri  = Φ × ρ / (A_int × (1 − ρ))
Φ     = Σ_ventanas (E_natural + E_exterior) × área_ventana
A_int = 2 × área + 4 × √área × 3 m
```

`ρ` es la reflectancia de la pared del recinto. Una habitación de 24 m² tiene `A_int ≈ 106,8 m²`, y con pared blanca (`ρ = 0,80`) el factor `ρ / (1 − ρ)` vale 4. La reflexión interior promedia todos los rebotes dentro del recinto y hace que el color de la pared cambie la luz de su propio cuarto. La zona toma el promedio de la reflexión exterior de sus ventanas.

A las 12:00 del escenario base, `TP-H-101` (al este, frente a TG) recibe 97,0 lux naturales y 98,4 reflejados; `TP-H-102` (al norte, sin torre enfrente) recibe 358,7 naturales y 26,9 reflejados, casi todos interiores; `TG-H-101` recibe 238,3 y 17,9.

## 9. Estructuras y flujo

### Árbol

```text
Hotel
├── TP / TG
│   ├── Piso
│   │   ├── ZonaHotel
│   │   │   └── Ventana
```

La energía se agrega por piso y por torre con un recorrido en postorden.

### Octree

Indexa cajas de torres, fachadas, paredes, ventanas y luminarias. Sirve para rayos de sombra y radios de influencia. Los objetos que cruzan octantes se quedan en el nodo padre.

### Grafo

```text
Fachada (8: N, S, E, O de cada torre) → Ventana de la otra torre
```

Para cada ventana se toma su punto de salida en la fachada de su torre y `Octree.consultar_radio` entrega las fachadas de la otra torre a 18 m o menos, en vez de comparar todos los pares. La distancia `d` se mide al punto más cercano de la fachada; ventana y fachada deben mirarse y un rayo debe unirlas sin cruzar otra torre. El peso de la arista es `ρ_fachada × cos_fachada × cos_ventana × A_f / (π·d² + A_f)` (sección 8). Sólo se calcula reflexión exterior de primer orden: la luz reflejada no vuelve a ser origen. Al construir el grafo también se guarda la obstrucción del cielo de cada ventana. Las aristas se indexan por destino, así que cada ventana recorre solo las aristas que le llegan.

### Cola de prioridad

El balance de cada instante ordena las demandas con `heapq`. Solo necesita insertar y extraer la de mayor prioridad, así que un árbol no aporta nada ahí.

### AVL: bolsa de habitaciones para la reasignación

Guarda las habitaciones con veredicto `HABITABLE` y cama libre, con clave `(torre, piso, −calidad, habitacion_id)`. La calidad es `w_luz × puntaje + w_energia × ahorro` y no depende del huésped. Para cada huésped que hay que mover se consulta el sucesor de cada piso permitido; cuando una habitación se llena, se elimina del árbol. Así dos huéspedes no reciben la misma cama. Se eligió AVL porque el trabajo es de lectura: varias consultas y como máximo una eliminación por huésped.

Restricciones por huésped (`huespedes.restricciones_por_huesped` en el JSON):

- `MISMA_TORRE` y `PISO_MAXIMO:n` son duras y filtran candidatos.
- `ORIENTACION:ESTE|NORTE|OESTE|SUR` es una preferencia: suma al término de actividad si la habitación coincide.

Cada propuesta registra las habitaciones revisadas y descartadas con su motivo. Si no hay alternativa, el motivo es `SIN_HABITACIONES_HABITABLES_LIBRES`, `SIN_CAPACIDAD` o `RESTRICCIONES`.

### Rojo-negro: índice temporal de resultados

Cada resultado se inserta en cuanto se calcula, con clave `(hora, zona_id)`. Una franja `[inicio, fin)` se consulta como rango en `O(log R + k)`. Las franjas fijas son día completo, 00–06, 06–12, 12–18, 18–22 y 22–24. Para cada una se reporta energía en Wh y kWh, energía por actividad y por torre, hora y potencia pico del generador, déficit residual, energía no asignada, zonas críticas, horas con déficit por zona e instantes con déficit. La interfaz usa el índice en el selector de franja horaria del plano.

Se eligió rojo-negro porque hay muchas inserciones y pocas consultas, y en general rota menos que el AVL al insertar. La sección 11 muestra que con el orden en que llegan los resultados eso no se cumple.

### Algoritmo general

```text
cargar hotel y validar dos torres
cargar pisos, zonas, ventanas, vidrios, paredes, fachadas, luminarias y huéspedes
cargar clima, horarios y restricciones
construir Octree
construir grafo fachada → ventana de la otra torre con consultas de radio del Octree
y la obstrucción del cielo de cada ventana

para cada instante t entre 00:00 y 24:00:
    determinar periodo y modo de horario de cada zona
    si es de día: calcular luz natural con Snell y Fresnel, sombras y obstrucción,
                  luz de las fachadas, reflexión exterior y reflexión interior
    calcular demandas de emergencia, mínima y objetivo
    reservar el nivel de emergencia para todas las zonas abiertas
    cubrir mínimos: parqueadero, habitaciones ocupadas, resto
    marcar EMERGENCIA la zona que no alcanza su mínimo
    distribuir potencia restante hasta el objetivo por prioridad
    calcular luz artificial y luz total
    clasificar cada zona, guardar el resultado e insertarlo en el rojo-negro

calcular veredicto de habitabilidad por zona
construir el AVL con habitaciones HABITABLE con cama libre
para cada huésped en habitación NO_HABITABLE:
    filtrar pisos y torres por restricciones
    consultar el sucesor de cada piso en el AVL
    elegir la mejor candidata según luz, actividad, ahorro de energía y cambio
    si se llena, eliminarla del AVL
    registrar la propuesta, los descartes y el motivo si no existe alternativa

agregar métricas, energía y déficits por franja
exportar reporte
```

## 10. Balance energético

Para cada zona se calcula la potencia artificial aproximada:

```text
E_artificial = eficacia × potenciaAsignada × CU × MF / área
```

El `CU = 0,70` del método de lúmenes ya incluye el rebote interior de la luz de la luminaria, por eso no se le suma reflexión aparte. El `CU` es fijo: no cambia con el color de la pared.

Las demandas de emergencia, mínima y objetivo se calculan después de descontar luz natural y reflejada. La prioridad de cada zona es `prioridadActividad × pesoPiso × factorOcupacion`, con `pesoPiso = 1 + 0,10 × (piso − 1)` y `factorOcupacion = 1,4` para habitaciones ocupadas (1,0 en las demás). El balance:

1. identifica zonas abiertas; las `CERRADA` no reciben energía;
2. calcula las demandas de emergencia (10 lux, o el mínimo si es menor), mínima y objetivo;
3. reserva el nivel de emergencia para todas las zonas abiertas;
4. cubre mínimos en este orden: seguridad (parqueadero), habitaciones ocupadas y resto, cada grupo por prioridad;
5. marca `EMERGENCIA` la zona que no alcanza su mínimo; esa zona no recibe más potencia en el instante;
6. asigna potencia hasta el objetivo por prioridad, con una cola `heapq`, hasta agotar el generador;
7. registra déficit residual y energía en Wh/kWh.

El peso sólo determina prioridad. No convierte una zona oscura en confortable.

En el escenario base el generador de 22 kW alcanza: el pico es 15.933,7 W a las 18:00 y ninguna zona entra en `EMERGENCIA`. Con un generador de 10 kW (`deficit_leve.json`) solo las recreaciones entran en `EMERGENCIA`, el parqueadero nunca queda en déficit por su prioridad de seguridad y las habitaciones ocupadas siguen habitables.

## 11. Métricas y complejidad

El sistema reporta estado por zona e instante, puntuación diurna/nocturna, veredicto por zona, energía por torre y actividad, potencia máxima, déficit residual, energía no asignada, zonas críticas, horas con déficit, huéspedes reasignados, candidatos descartados y conteos de las estructuras de datos.

Resultado del escenario base: 101 zonas habitables, 26 casi habitables (todas por exceso solar) y 0 no habitables; puntaje ponderado 0,9726 (día 0,9451, noche 1,0); energía 194.432,4 Wh.

Costes:

```text
Sombras ingenuas:          O(V × B × T)
Octree esperado:           O(V × T × (log B + k))
Grafo ingenuo:             O(S × V)
Grafo con Octree:          O(V × (log N + k) + E)
Agregación jerárquica:     O(N)
Balance por instante:      O(Z log Z)
Reasignación lineal:       O(G × H)
Reasignación con AVL:      O(G × F × log H)
Franja con lista:          O(R)
Franja con rojo-negro:     O(log R + k)
```

`S` es el número de fachadas, `V` el de ventanas, `G` el número de huéspedes a mover, `F` el número de pisos, `H` el número de habitaciones y `R` el número de resultados.

Conteos medidos en el escenario base:

| Medida | Versión ingenua | Con estructura |
|---|---:|---:|
| Pares fachada–ventana al construir el grafo (8 fachadas, 154 ventanas) | 1.232 | 68 (7.834 nodos del Octree visitados) |
| Aristas del grafo | — | 46 (`TP-F-ESTE` → 24 ventanas de TG, `TG-F-OESTE` → 16 de TP, `TP-F-NORTE` → 6 de recreaciones de TG) |
| Nodos visitados para la franja 18–22 (6.096 resultados) | 6.096 | 1.029 |
| AVL de reasignación (78 habitaciones habitables libres) | — | altura 7, 58 rotaciones, 417 comparaciones de construcción |

En el escenario base nadie está en una habitación `NO_HABITABLE`, así que el AVL se construye y se reporta pero no se consulta. La prueba del caso 7 (sección 12) verifica que el AVL hace menos comparaciones que la búsqueda lineal.

Rotaciones al insertar los mismos 6.096 resultados:

| Datos | Rojo-negro | AVL |
|---|---:|---:|
| Escenario base, en el orden de la simulación | 9.099 (altura 22) | 7.232 (altura 14) |
| 6.096 claves en orden aleatorio | 3.511 | 4.176 |

Con claves aleatorias el rojo-negro rota menos, como se esperaba. Con los resultados de la simulación rota más, porque llegan casi ordenados: hora ascendente y, dentro de cada hora, tramos largos de IDs ascendentes. Se verificó que el árbol cumple las propiedades de rojo-negro. El índice cumple su papel en las consultas por franja, pero el argumento de las rotaciones no se sostiene con estos datos.

El coste real depende de la distribución espacial y de la cantidad de candidatos.

## 12. Casos de prueba

Los 10 casos son pruebas automáticas con `unittest` en `tests/test_casos_plan.py`. Se ejecutan desde la raíz del repositorio con `python -m unittest`. Salvo donde se indica, usan el escenario base.

| # | Caso | Qué verifica |
|---|---|---|
| 1 | Ventana orientada al sol y sin obstáculo | La luz natural coincide con la fórmula de la sección 8 y supera la que daría solo la difusa. |
| 2 | Ventana sombreada por la otra torre | La ventana sombreada solo aporta luz difusa. |
| 3 | Transmisión con cada preset de vidrio | La luz natural es proporcional a la VLT; el factor angular vale 1 a 0° y baja con la incidencia; Snell da `sen θt = sen θi / 1,5`. |
| 4 | Reflexión de primer orden sin cascada | Las aristas van solo de una fachada a ventanas de la otra torre y su peso no supera la reflectancia de la fachada; la reflejada de cada zona es la exterior (aristas entrantes) más la interior; una pared oscura da menos reflejada que una blanca; de noche la reflejada es 0. |
| 5 | Noche con luz natural cero y luminaria artificial activa | Natural y reflejada son cero de noche y una habitación ocupada no queda en déficit a las 20:00. |
| 6 | Generador suficiente para mínimos pero insuficiente para todos los objetivos | Con la capacidad entre la suma de mínimos y la de objetivos, todas las zonas reciben su mínimo, ninguna entra en `EMERGENCIA` y se usa toda la capacidad. |
| 7 | Habitación ocupada `NO_HABITABLE` con habitación compatible disponible | Ningún JSON de prueba produce este caso, así que se arma con veredictos modificados sobre el escenario base: todas las habitaciones quedan `NO_HABITABLE` menos una ocupada con una cama libre. El primer huésped la recibe, la habitación sale del AVL y los demás reciben `SIN_CAPACIDAD`. El AVL hace menos comparaciones que la búsqueda lineal. |
| 8 | Habitación ocupada `NO_HABITABLE` sin alternativa disponible | Con `deficit_severo.json` todas las propuestas son `SIN_HABITACIONES_HABITABLES_LIBRES`. Aparte, un huésped con `MISMA_TORRE` y la única candidata en la otra torre recibe `RESTRICCIONES`. |
| 9 | Zona cerrada y habitación en descanso sin falso déficit | La cocina a las 02:00 está `CERRADA`, sin energía y fuera del puntaje; la habitación a las 23:00 está `REDUCIDA` sin déficit. |
| 10 | Comparación entre clima nublado y cielo despejado | `factor_luz` es radiación / 7,063 y la luz natural con cielo despejado supera la del nublado. |

## 13. Fuentes y límites

Fuentes principales: NASA POWER para clima; DOE Commercial Reference Buildings para las plantillas de torres; página oficial del RETILAP y Resolución 40286 de 2026 para el marco regulatorio; ISO 30061 para iluminación de emergencia; NFPA 101 como referencia del nivel de emergencia; UNE-EN 12464-1 como guía complementaria; Cardinal Glass para transmitancias; Edmund Optics para óptica básica.

Los rangos, pesos, horarios, áreas de zonas, potencias, capacidad del generador, nivel de emergencia, huéspedes y posiciones son supuestos sintéticos. El resultado usa lux de referencia cuando no existe calibración fotométrica, y los valores son aproximaciones educativas. No constituye una certificación de cumplimiento.

Limitaciones conocidas:

- La precipitación es informativa y no entra en el cálculo.
- La reflexión exterior entre torres es de primer orden.
- El `CU` de la luz artificial es fijo y no cambia con el color de la pared.
- Las superficies interiores de cada recinto se representan con un solo valor de reflectancia.
- Las ventanas están dentro de la caja de su torre; para la reflexión exterior se usa su punto de salida en la fachada.

## 14. Criterio de éxito

El proyecto será exitoso si construye las dos torres, recorre 24 horas con un modelo único, consulta el Octree, calcula la reflexión interior y la reflexión exterior de primer orden entre torres, aplica el balance con emergencia y mínimos de seguridad, clasifica las cuatro actividades, emite veredictos por zona, reporta energía y déficits por franja, produce propuestas coherentes de reasignación sin alterar la geometría, y pasa los 10 casos de prueba.
