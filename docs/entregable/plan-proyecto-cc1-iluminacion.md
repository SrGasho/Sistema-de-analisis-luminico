# Plan del sistema educativo de iluminación y balance energético hotelero

## Proyecto de Ciencias de la Computación 1

## 1. Resumen

El proyecto propone diseñar e implementar un sistema educativo que estime la iluminación de un hotel de dos torres ubicado en Bogotá. El hotel se analiza durante 24 horas y contiene cuatro actividades: habitaciones, cocina, sala de juegos y parqueadero.

El sistema combina un árbol jerárquico, un Octree, un grafo dirigido ponderado, un árbol AVL, un árbol rojo-negro, una cola de prioridad y recorridos de agregación. Durante el día calcula la posición real del sol en Bogotá y luz natural con la radiación real de NASA POWER, separada en directa y difusa con la correlación de Erbs, Klein y Duffie, transmisión por vidrio con refracción de Snell y transmitancia de Fresnel, reflexión interior de cada recinto, reflexión de primer orden entre las fachadas de las dos torres y luz artificial complementaria. Durante la noche toma la luz solar como cero y distribuye la potencia artificial disponible mediante un balance heurístico.

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
- Representar habitaciones, cocinas, salas de juegos y parqueaderos con zonas reutilizables.
- Usar un eje temporal único entre 00:00 y 24:00, sin clases diurnas/nocturnas duplicadas.
- Calcular sombras con cajas espaciales y consultas de Octree.
- Representar la reflexión entre torres mediante un grafo dirigido `fachada → ventana de la otra torre`, construido con consultas de radio del Octree.
- Calcular la reflexión exterior entre torres en primer orden y la reflexión interior de cada recinto con el método de flujo dividido.
- Incorporar tres presets de vidrio y cinco reflectancias educativas de pared y de fachada.
- Usar perfiles climáticos de Bogotá basados en NASA POWER, con la radiación real en el cálculo de la luz global y la posición real del sol según la latitud y el día del año de cada perfil.
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
- Mejoras medidas a partir de los problemas del escenario: para las zonas casi habitables o no habitables, según la causa, vidrio de control solar (`EXCESO_SOLAR`), reponer luminarias débiles, ampliar el generador (solo si hubo `EMERGENCIA`) y vidrio claro o paredes blancas (`DEFICIT_DIURNO`). Solo se muestran las que suben el puntaje del hotel; sin zonas con problemas, el resultado es `TODO_HABITABLE`.
- Reestructuración de variables de luz: pared, vidrio, orientación de ventanas y horarios de cocina y sala de juegos. No cambia los objetivos de lux.
- Interfaz web con formularios de entradas, plano por torre y piso, selector de franja horaria, veredictos, sugerencias, mejoras medidas, reestructuración y tablas de estructuras de datos. El diagnóstico abre con una guía plegable, «Cómo leer los resultados»; los IDs de zona en sugerencias, mejoras y reasignaciones abren el plano con esa zona seleccionada; y «Aplicar y simular», en el detalle de una zona, aplica el cambio y vuelve a ejecutar la simulación y el balance.
- Los 10 casos de prueba de la sección 12 como pruebas automáticas.

### 5.2 No incluido

- Diseño fotométrico profesional.
- Archivos IES/LDT o mallas arquitectónicas complejas.
- Deslumbramiento profesional, confort circadiano o modelo térmico.
- Consumo total del hotel, ascensores, climatización o agua caliente.
- Reflexión especular o reflexiones exteriores de segundo orden (de una fachada a otra).
- Cambios en la geometría de las torres. Las torres son fijas: el sistema no mueve ni rediseña edificios, pisos ni habitaciones. Las mejoras y la reestructuración solo cambian variables de luz (orientación de ventanas, acabados, luminarias por recinto, horarios y generador).
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
| Salas de juegos | 4 | 6 | 80 m² |
| Parqueaderos | 1 | 2 | 450 m² |
| Ventanas | 52 | 102 | Habitación 1, cocina 2, sala de juegos 3 |
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
| Sala de juegos | 450 W | 100 lm/W | 0,70 | 0,80 |
| Parqueadero | 720 W | 100 lm/W | 0,70 | 0,80 |

Un recinto puede cambiar la potencia de su luminaria con `luminaria_w` en `zonas_personalizadas` (número ≥ 0; 0 representa una luminaria dañada). Se valida al cargar y solo se edita en el JSON, no desde la interfaz.

El generador se fija en 22,0 kW nominales, redondeando hacia arriba la demanda objetivo máxima más una reserva didáctica del 20 %. Sólo se dimensiona el subsistema de iluminación.

## 7. Perfiles, horarios y clasificación

Los siguientes son presets educativos. El RETILAP vigente debe consultarse para la categoría exacta, plano de trabajo, uniformidad, mantenimiento y demás requisitos. No se presentan como una transcripción normativa.

| Actividad | Mínimo | Objetivo | Máximo | Prioridad |
|---|---:|---:|---:|---:|
| Habitación activa | 100 lux | 200 lux | 300 lux | 3 |
| Cocina activa | 300 lux | 400 lux | 500 lux | 3 |
| Sala de juegos activa | 200 lux | 300 lux | 500 lux | 2 |
| Parqueadero activo | 50 lux | 100 lux | 150 lux | 1 |

Horarios sintéticos:

```text
Habitaciones:    06:00–22:00 ACTIVA; 22:00–06:00 REDUCIDA
Cocinas:         06:00–22:00 ACTIVA; 23:00–05:00 CERRADA; resto REDUCIDA
Salas de juegos: 08:00–23:00 ACTIVA; 00:00–07:00 CERRADA; resto REDUCIDA
Parqueaderos:    00:00–24:00 ACTIVA
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

La ubicación de referencia es Bogotá, aproximadamente 4.7110° N, -74.0721° O (`parametros_evaluacion.ubicacion`). Se usan perfiles derivados de NASA POWER (2001–2020) con radiación, nubosidad y precipitación. La nubosidad y la precipitación se cargan y se reportan, pero son informativas: no entran en el cálculo.

La posición del sol es la real (`direccion_solar` en `clima.py`). La hora se toma como hora solar:

```text
φ = 4,711°
δ = 23,45° × sen(360° × (284 + n) / 365)       declinación de Cooper; n = dia_del_anio del perfil
ω = 15° × (hora − 12)                           ángulo horario
sol: x = −cos δ sen ω (este)
     y = sen δ cos φ − cos δ sen φ cos ω (norte)
     z = sen δ sen φ + cos δ cos φ cos ω (arriba)
```

En febrero el sol de mediodía está a 72,0° de altura y hacia el sur; a las 7:00 está a 13,4° y a las 9:00 a 41,8°. En abril llega a 85,3° y en mayo a 75,9°, hacia el norte.

La luz global horizontal usa la radiación del perfil activo:

```text
G(t)       = K_lux × factor_luz × max(0, sen(altura del sol))   entre 06:00 y 18:00; 0 fuera
factor_luz = radiación / radiación de cielo despejado
```

`K_lux` es una conversión calibrable a lux de referencia (900, en `parametros_evaluacion.luz.lux_por_irradiancia`). La radiación de cielo despejado es 7,063 kWh/m²/día. El factor se calcula en el código (`PerfilClimatico.factor_luz`), no se escribe a mano. En febrero con nubes parciales, `G` vale 143,9 lux a las 7:00, 413,3 a las 9:00, 589,3 a las 12:00, 413,3 a las 15:00 y 66,8 a las 17:30.

`G` se reparte con una fracción difusa diaria `kd` (Erbs, Klein y Duffie, 1982, forma para ωs > 81,4°): `KT = radiación / H0`, `kd = 1,311 − 3,022 KT + 3,427 KT² − 1,821 KT³`, directa horizontal `G × (1 − kd)` y difusa horizontal `G × kd`, que suman `G`. `H0` es la radiación extraterrestre diaria (Duffie y Beckman, ec. 1.10.3): `H0 = 24/π × 1,367 × (1 + 0,033 cos(360n/365)) × (cos φ cos δ sen ωs + ωs sen φ sen δ)`.

| Perfil | Mes (`n`) | Radiación (kWh/m²/día) | Nubosidad | `factor_luz` | `H0` | `KT` | `kd` |
|---|---|---:|---:|---:|---:|---:|---:|
| `NUBES_PARCIALES` | febrero (46) | 4,863 | 0,7089 | 0,689 | 10,05 | 0,484 | 0,445 |
| `NUBLADO` | mayo (135) | 4,477 | 0,8582 | 0,634 | 10,06 | 0,445 | 0,484 |
| `LLUVIOSO` | abril (105) | 4,454 | 0,8487 | 0,631 | 10,41 | 0,428 | 0,503 |
| `CIELO_DESPEJADO` | febrero (46) | 7,063 | 0,0 | 1,000 | 10,05 | 0,703 | 0,248 |

Con estas fracciones la luz natural del hotel en el día completo crece con la radiación: `CIELO_DESPEJADO` 534.973 > `NUBES_PARCIALES` 396.651 > `NUBLADO` 385.199 > `LLUVIOSO` 370.265 (suma de lux de todas las zonas en los 48 pasos).

Sobre una superficie vertical (ventana o fachada) se usa el cielo isotrópico de Liu y Jordan (1960):

```text
directa_vertical = directa horizontal × cos θi / max(sen(altura), sen 5°)
difusa_vertical  = 0,5 × difusa horizontal × (1 − obstrucción) + 0,5 × ρ_suelo × G
```

con `ρ_suelo = 0,20` (`parametros_evaluacion.luz.reflectancia_suelo`). La altura mínima de 5° evita que la directa se dispare al amanecer.

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
E_ventana = VLT × (directa_vertical × factor_angular + difusa_vertical)
```

Si la ventana está en sombra, `cos θi` se toma como cero y solo queda la difusa. La otra torre también tapa parte del cielo: la difusa del cielo se multiplica por `1 − obstrucción`, con `obstrucción = Σ cos_ventana × factor de vista` de las fachadas que la ventana tiene enfrente (máximo 1). En el escenario base 40 ventanas tienen obstrucción; `TP-H-101-V1` (al este, frente a TG) tiene 0,593. La luz natural de la zona es el promedio de sus ventanas.

La luz reflejada sólo existe de día y suma dos partes:

```text
E_reflejada = E_exterior + E_ri

Reflexión exterior entre torres (primer orden):
E_exterior(ventana) = Σ luz_fachada × peso × VLT
luz_fachada         = directa_vertical(n · sol) + difusa_vertical(sin obstrucción)
peso                = ρ_fachada × cos_fachada × cos_ventana × A_f / (π·d² + A_f)

Reflexión interior (flujo dividido):
E_ri  = Φ × ρ / (A_int × (1 − ρ))
Φ     = Σ_ventanas (E_natural + E_exterior) × área_ventana
A_int = 2 × área + 4 × √área × 3 m
```

`ρ` es la reflectancia de la pared del recinto. Una habitación de 24 m² tiene `A_int ≈ 106,8 m²`, y con pared blanca (`ρ = 0,80`) el factor `ρ / (1 − ρ)` vale 4. La reflexión interior promedia todos los rebotes dentro del recinto y hace que el color de la pared cambie la luz de su propio cuarto. La zona toma el promedio de la reflexión exterior de sus ventanas.

A las 12:00 de febrero el sol está al sur, así que las ventanas al este y al norte solo reciben difusa. En el escenario base, `TP-H-101` (al este, frente a TG) recibe 92,0 lux naturales y 66,5 reflejados; `TP-H-102` (al norte, sin torre enfrente) recibe 155,8 naturales y 11,7 reflejados, casi todos interiores (1,0 con pared oscura); `TG-H-101` (al este, sin torre enfrente) recibe 155,8 y 11,7. La fachada `TG-F-OESTE` recibe 133,2 lux a las 9:00, 190,0 a las 12:00 y 370,0 a las 15:00.

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
    calcular la posición del sol, G y su reparto en directa y difusa
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

Todas las entregas pasan por un `Reparto` (`balance.py`), que guarda en `usado` lo que el generador ya entregó en el instante. Cada entrega cuesta O(1), sin volver a sumar lo asignado, y el instante completo O(Z log Z).

El peso sólo determina prioridad. No convierte una zona oscura en confortable.

En el escenario base el generador de 22 kW alcanza: el pico es 15.933,7 W a las 18:00, la demanda objetivo máxima es 18.110,7 W y ninguna zona entra en `EMERGENCIA`. Con un generador de 4 kW (`deficit_severo.json`) el parqueadero nunca queda en déficit por su prioridad de seguridad, las habitaciones ocupadas de los pisos 2 en adelante siguen habitables y las demás zonas pasan 660 pasos en `EMERGENCIA`.

El estado del generador es `CAPACIDAD_LIMITADA` si alguna zona entró en `EMERGENCIA` en alguna media hora o la potencia superó la capacidad, `ALTA_DEMANDA` si la potencia pasó del 80 % de la capacidad y `OPERACION_NORMAL` en los demás casos. Un déficit sin emergencia no lo cambia. El resultado incluye también `pasos_emergencia` y `demanda_objetivo_maxima_w`.

## 11. Métricas y complejidad

El sistema reporta estado por zona e instante, puntuación diurna/nocturna, veredicto por zona, energía por torre y actividad, potencia máxima, déficit residual, energía no asignada, zonas críticas, horas con déficit, huéspedes reasignados, candidatos descartados y conteos de las estructuras de datos.

Resultado del escenario base: las 127 zonas habitables (52 con causa `EXCESO_SOLAR` en algunos pasos), 0 casi habitables y 0 no habitables; puntaje ponderado 0,9718 (día 0,9436, noche 1,0); energía 208.075,0 Wh. De los 6.096 estados, 5.517 son confortables, 319 exceso leve, 260 cerrados y ninguno déficit.

Costes:

```text
Sombras ingenuas:          O(V × B × T)
Octree esperado:           O(V × T × (log B + k))
Grafo ingenuo:             O(S × V)
Grafo con Octree:          O(V × (log N + k) + E)
Agregación jerárquica:     O(N)
Balance por instante:      O(Z log Z), con Reparto O(1) por entrega
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
| Aristas del grafo | — | 46 (`TP-F-ESTE` → 24 ventanas de TG, `TG-F-OESTE` → 16 de TP, `TP-F-NORTE` → 6 de salas de juegos de TG) |
| Nodos visitados para la franja 18–22 (6.096 resultados) | 6.096 | 1.030 |
| AVL de reasignación (104 habitaciones habitables libres) | — | altura 8, 80 rotaciones, 618 comparaciones de construcción |
| Comparaciones de la reasignación en la prueba de carga (60 de 78 ocupadas marcadas `NO_HABITABLE`) | 6.240 | 2.792 (39 eliminaciones); 3.289 con restricciones mezcladas |

En el escenario base nadie está en una habitación `NO_HABITABLE`, así que el AVL se construye y se reporta pero no se consulta. La prueba del caso 7 (sección 12) verifica que el AVL hace menos comparaciones que la búsqueda lineal.

Rotaciones al insertar los mismos 6.096 resultados:

| Datos | Rojo-negro | AVL |
|---|---:|---:|
| Escenario base, en el orden de la simulación | 7.960 (altura 22) | 7.779 (altura 14) |
| 6.096 claves en orden aleatorio (semilla 1) | 3.556 | 4.312 |

Con claves aleatorias el rojo-negro rota menos, como se esperaba. Con los resultados de la simulación rota más, porque llegan casi ordenados: hora ascendente y, dentro de cada hora, tramos largos de IDs ascendentes. Se verificó que el árbol cumple las propiedades de rojo-negro. El índice cumple su papel en las consultas por franja, pero el argumento de las rotaciones no se sostiene con estos datos.

El coste real depende de la distribución espacial y de la cantidad de candidatos.

## 12. Casos de prueba

Los 10 casos son pruebas automáticas con `unittest` en `tests/test_casos_plan.py`. Se ejecutan desde la raíz del repositorio con `python -m unittest`. Salvo donde se indica, usan el escenario base.

| # | Caso | Qué verifica |
|---|---|---|
| 1 | Ventana orientada al sol y sin obstáculo | La luz natural coincide con la fórmula de la sección 8 y supera la que daría solo la difusa; la directa horizontal más la difusa horizontal suman `G`. |
| 2 | Ventana sombreada por la otra torre | La ventana sombreada solo aporta luz difusa. |
| 3 | Transmisión con cada preset de vidrio | La luz natural es proporcional a la VLT; el factor angular vale 1 a 0° y baja con la incidencia; Snell da `sen θt = sen θi / 1,5`. |
| 4 | Reflexión de primer orden sin cascada | Las aristas van solo de una fachada a ventanas de la otra torre y su peso no supera la reflectancia de la fachada; la reflejada de cada zona es la exterior (aristas entrantes) más la interior; una pared oscura da menos reflejada que una blanca; de noche la reflejada es 0. |
| 5 | Noche con luz natural cero y luminaria artificial activa | Natural y reflejada son cero de noche y una habitación ocupada no queda en déficit a las 20:00. |
| 6 | Generador suficiente para mínimos pero insuficiente para todos los objetivos | Con la capacidad entre la suma de mínimos y la de objetivos, todas las zonas reciben su mínimo, ninguna entra en `EMERGENCIA` y se usa toda la capacidad. |
| 7 | Habitación ocupada `NO_HABITABLE` con habitación compatible disponible | Para controlar exactamente cuántas camas quedan libres, se arma con veredictos modificados sobre el escenario base (`luminarias_danadas.json` muestra el caso con datos completos): todas las habitaciones quedan `NO_HABITABLE` menos una ocupada con una cama libre. El primer huésped la recibe, la habitación sale del AVL y los demás reciben `SIN_CAPACIDAD`. El AVL hace menos comparaciones que la búsqueda lineal. |
| 8 | Habitación ocupada `NO_HABITABLE` sin alternativa disponible | Con `apagon_generador.json` las 78 propuestas son `SIN_HABITACIONES_HABITABLES_LIBRES`. Aparte, un huésped con `MISMA_TORRE` y la única candidata en la otra torre recibe `RESTRICCIONES`. |
| 9 | Zona cerrada y habitación en descanso sin falso déficit | La cocina a las 02:00 está `CERRADA`, sin energía y fuera del puntaje; la habitación a las 23:00 está `REDUCIDA` sin déficit. |
| 10 | Comparación entre clima nublado y cielo despejado | `factor_luz` es radiación / 7,063 y la luz natural con cielo despejado supera la del nublado. |

Además, `tests/test_casos_json.py` ejecuta el escenario base y los diez casos de `data/casos_prueba/` y compara cada uno con el bloque `caso.resultado_esperado` de su JSON. En total son 26 pruebas. Resultados, como habitables / casi habitables / no habitables:

| Caso | Situación | Resultado |
|---|---|---|
| `temporada_lluvias` | Abril, cielo cubierto | 127/0/0; nadie se reasigna. |
| `mayo_nublado` | Mayo, cielo nublado; sol del mediodía por el norte | 127/0/0; las habitaciones al sur gastan más que las del norte, al revés que en febrero. |
| `generador_alta_demanda` | Generador de 17 kW | 127/0/0; generador en `ALTA_DEMANDA`. |
| `deficit_leve` | 12 habitaciones de TG con luminarias de 30 W | 115/12/0; déficit nocturno leve, sin `EMERGENCIA` ni reasignaciones; generador en `OPERACION_NORMAL`. |
| `deficit_severo` | Generador de 4 kW | 59/0/68; 660 pasos en `EMERGENCIA`; generador en `CAPACIDAD_LIMITADA`; 22 huéspedes reasignados. |
| `apagon_generador` | Generador de 0 kW | 0/0/127; generador en `CAPACIDAD_LIMITADA`; 78 huéspedes sin alternativa. |
| `cielo_despejado` | Febrero con cielo despejado | 75/52/0; causa `EXCESO_SOLAR` en habitaciones con ventana al este u oeste; nadie se reasigna. |
| `exceso_severo` | Cielo despejado; 24 habitaciones ocupadas de TP con vidrio claro y ventana al este | 69/58/0; 18 de esas 24 quedan casi habitables con `EXCESO_SEVERO` entre las 6:30 y las 10:00; 6 siguen habitables porque TG les hace sombra en la mañana; nadie se reasigna. |
| `luminarias_danadas` | `TP-H-101` a `TP-H-116` (ocupadas, pisos 1 y 2) con `luminaria_w = 0` | 111/0/16 por `DEFICIT_NOCTURNO`; generador en `OPERACION_NORMAL`; los 16 huéspedes se mueven: H-001 (`MISMA_TORRE`) a `TP-H-120`, H-002 (`PISO_MAXIMO:2`) a `TG-H-112`, H-003 (`ORIENTACION:ESTE`) a `TG-H-101`. |
| `reasignacion_restringida` | Las 24 habitaciones ocupadas de TP sin luminaria; H-001 a H-018 con `MISMA_TORRE`; H-019 y H-020 con `MISMA_TORRE` + `PISO_MAXIMO:2` | 103/0/24; generador en `OPERACION_NORMAL`; 16 llenan las 16 camas del piso 4 de TP; H-017 y H-018 `SIN_CAPACIDAD`; H-019 y H-020 `RESTRICCIONES`; H-021 a H-024 van a TG. |

## 13. Fuentes y límites

Fuentes principales: NASA POWER para clima; Cooper (1969) para la declinación; Duffie y Beckman (2013) para la posición del sol, la radiación extraterrestre `H0` y el factor `Rb`; Erbs, Klein y Duffie (1982) para la fracción difusa; Liu y Jordan (1960) para el cielo isotrópico sobre superficies verticales; Hecht (2017) para Snell y Fresnel; Hopkinson, Petherbridge y Longmore (1966) para el flujo dividido; IES Lighting Handbook para el método de lúmenes; DOE Commercial Reference Buildings para las plantillas de torres; página oficial del RETILAP y Resolución 40286 de 2026 para el marco regulatorio; ISO 30061 para iluminación de emergencia; NFPA 101 como referencia del nivel de emergencia; UNE-EN 12464-1 como guía complementaria; Cardinal Glass para transmitancias; Edmund Optics para óptica básica.

Los rangos, pesos, horarios, áreas de zonas, potencias, capacidad del generador, nivel de emergencia, huéspedes y posiciones son supuestos sintéticos. También son supuestos del proyecto `K_lux = 900`, el factor de vista `A_f / (π·d² + A_f)` (aproximación propia, sin fuente), la reflectancia del suelo 0,20 (valor típico) y la altura mínima de 5°. El resultado usa lux de referencia cuando no existe calibración fotométrica, y los valores son aproximaciones educativas. No constituye una certificación de cumplimiento. La sección «Fuentes y fórmulas» del `README.md` reúne cada fórmula con su fuente y enlace.

Limitaciones conocidas:

- La nubosidad y la precipitación son informativas y no entran en el cálculo.
- La hora se trata como hora solar. Bogotá está a −74,07° y usa UTC−5, así que la diferencia con el reloj es de unos minutos más la ecuación del tiempo.
- La fracción difusa es diaria: una sola para todo el día, no horaria.
- Con el sol muy bajo, la luz directa sobre una ventana vertical se limita con una altura mínima de 5°.
- `luminaria_w` solo se edita en el JSON.
- La reflexión exterior entre torres es de primer orden.
- Las fachadas se modelan como superficies opacas de un solo color. El vidrio de las ventanas no se usa como fuente de reflexión: la luz que el vidrio refleja hacia afuera (la pérdida de Fresnel) se descuenta y no ilumina la otra torre. En una fachada con mucho vidrio ese reflejo puede ser fuerte y concentrado; no se calcula.
- El `CU` de la luz artificial es fijo y no cambia con el color de la pared.
- Las superficies interiores de cada recinto se representan con un solo valor de reflectancia.
- Las ventanas están dentro de la caja de su torre; para la reflexión exterior se usa su punto de salida en la fachada.

## 14. Criterio de éxito

El proyecto será exitoso si construye las dos torres, recorre 24 horas con un modelo único, consulta el Octree, calcula la reflexión interior y la reflexión exterior de primer orden entre torres, aplica el balance con emergencia y mínimos de seguridad, clasifica las cuatro actividades, emite veredictos por zona, reporta energía y déficits por franja, produce propuestas coherentes de reasignación sin alterar la geometría, y pasa los 10 casos de prueba.
