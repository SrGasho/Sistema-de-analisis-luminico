# Propuesta de simulación lumínica y balance energético para un hotel

## Curso: Ciencias de la Computación 1

## Introducción

Se propone desarrollar un sistema educativo para estimar la iluminación de un hotel de dos torres en Bogotá. El sistema trabaja con cuatro actividades: habitaciones, cocina, recreación y parqueadero. Utiliza una jerarquía de composición, un Octree para consultas espaciales, un grafo dirigido ponderado para influencias lumínicas, un árbol AVL para la reasignación de huéspedes, un árbol rojo-negro como índice temporal de resultados y un recorrido temporal único de 24 horas.

El día y la noche no se representan mediante clases duplicadas. Las mismas zonas, perfiles, resultados y evaluadores reciben el instante y el modo de operación. Los resultados son aproximaciones educativas y no sustituyen un proyecto fotométrico o eléctrico profesional.

La geometría de las torres es fija: el sistema no mueve ni rediseña edificios. Sí mide mejoras y propone reestructuraciones de las variables que afectan la luz: actividades (orientación de ventanas y objetivos de iluminación), acabados (pared y vidrio), horarios y generador.

# 1. Escenario y entradas

## 1.1 Hotel fijo

Las torres se identifican con abreviaturas: `TP` es la Torre Pequeña y `TG` es la Torre Grande. El nombre completo se guarda como campo de presentación.

```text
Hotel
├── TP (Torre Pequeña): 4 pisos, 32 habitaciones, 4 cocinas, 4 recreaciones, 1 parqueadero
└── TG (Torre Grande):  6 pisos, 72 habitaciones, 6 cocinas, 6 recreaciones, 2 parqueaderos
```

Las áreas de referencia son aproximadamente 4.013 m² y 11.346 m², inspiradas en modelos DOE. Las cajas, zonas, ventanas, huéspedes y luminarias son datos sintéticos.

```text
TP: x=0..32,  y=0..31,35, z=0..12
TG: x=45..89, y=0..43,    z=0..18
```

Cada piso mide 3 m de alto y la separación horizontal aproximada entre torres es de 13 m. Las habitaciones tienen 24 m² y capacidad para dos huéspedes. TP tiene 8 habitaciones por piso y TG tiene 12. Hay 78 huéspedes iniciales: 24 habitaciones ocupadas en TP y 54 en TG.

## 1.2 Zonas y ventanas

| Actividad | Área | Zonas en TP | Zonas en TG | Ventanas por zona |
|---|---:|---:|---:|---:|
| Habitación | 24 m² | 32 | 72 | 1 de 2,0 m² |
| Cocina | 35 m² | 4 | 6 | 2 de 1,5 m² |
| Recreación | 80 m² | 4 | 6 | 3 de 2,0 m² |
| Parqueadero | 450 m² | 1 | 2 | 0 |

En total hay 127 zonas y 154 ventanas (52 en TP y 102 en TG). Una ventana contiene `id`, posición, normal, área y vidrio. Los IDs de zona empiezan por la abreviatura de la torre: habitaciones `TP-H-101` y `TG-H-101`; zonas comunes `TP-COC-01`, `TG-REC-01` o `TG-PAR-02`. Los huéspedes de prueba usan `H-001` a `H-078`.

Cada huésped puede tener restricciones en `huespedes.restricciones_por_huesped`. Hay dos restricciones duras, que filtran candidatas en la reasignación: `MISMA_TORRE` y `PISO_MAXIMO:n`. Hay una preferencia, `ORIENTACION:ESTE|NORTE|OESTE|SUR`, que suma puntaje si la ventana de la habitación coincide. Una restricción desconocida se rechaza al cargar los datos.

## 1.3 Actividades y horarios

| Actividad | Activa | Reducida | Cerrada | Mínimo | Objetivo | Máximo | Prioridad |
|---|---|---|---|---:|---:|---:|---:|
| Habitación | 06:00–22:00 | resto del día | nunca | 100 | 200 | 300 | 3 |
| Cocina | 06:00–22:00 | 22:00–23:00 y 05:00–06:00 | 23:00–05:00 | 300 | 400 | 500 | 3 |
| Recreación | 08:00–23:00 | 23:00–24:00 y 07:00–08:00 | 00:00–07:00 | 200 | 300 | 500 | 2 |
| Parqueadero | 00:00–24:00 | nunca | nunca | 50 | 100 | 150 | 1 |

Los valores están expresados en lux de referencia. Son presets educativos configurables, no una transcripción normativa del RETILAP. En modo `REDUCIDA` los tres niveles se multiplican por 0,3.

Los modos de operación son:

- `ACTIVA` y `REDUCIDA`: según el horario de la actividad.
- `CERRADA`: según `cierre_inicio` y `cierre_fin` del horario (cocina 23 → 5, recreación 0 → 7). Si una hora cae a la vez en la franja activa y en la de cierre, manda la activa. Los pasos cerrados no reciben energía, quedan como `DATOS_INSUFICIENTES` y no cuentan en el puntaje de habitabilidad.
- `EMERGENCIA`: lo asigna el balance, no el horario. El nivel de emergencia es `parametros_evaluacion.emergencia.nivel_lux = 10` (supuesto cercano a 1 pie-candela, 10,8 lux, que pide NFPA 101 en rutas de evacuación). La zona abierta que no alcanza su mínimo porque el generador se agotó queda en `EMERGENCIA`, se clasifica contra el mínimo de su modo de horario y ese paso cuenta como déficit.

## 1.4 Vidrios, paredes y luminarias

Vidrios:

```text
VIDRIO_CLARO:          VLT = 0,82
VIDRIO_LOW_E:          VLT = 0,71 (catálogo: 0,70–0,72)
VIDRIO_CONTROL_SOLAR:  VLT = 0,52
Índice de refracción de los tres: 1,5
```

Paredes:

```text
Blanco 0,80 | Crema 0,70 | Gris claro 0,60
Gris medio 0,45 | Oscuro 0,25
```

Fachadas: cada torre tiene cuatro (`NORTE`, `SUR`, `ESTE`, `OESTE`), con ID como `TP-F-ESTE`. Su reflectancia sale del campo `fachada` de la torre en el JSON, con los mismos presets de pared; si falta, se usa `GRIS_CLARO` (0,60).

Luminarias equivalentes:

| Actividad | Potencia | Eficacia | CU | MF |
|---|---:|---:|---:|---:|
| Habitación | 72 W | 100 lm/W | 0,70 | 0,80 |
| Cocina | 200 W | 100 lm/W | 0,70 | 0,80 |
| Recreación | 450 W | 100 lm/W | 0,70 | 0,80 |
| Parqueadero | 720 W | 100 lm/W | 0,70 | 0,80 |

El generador tiene una capacidad sintética de 22,0 kW y sólo se utiliza para iluminación.

# 2. Salidas

Para cada zona e instante (paso de 30 minutos, 48 pasos) se almacenan:

```text
hora, periodo, modo, luzNatural, luzReflejada,
luzArtificial, luzTotal, potenciaAsignada, estado
```

En el escenario base son 6.096 resultados (127 zonas × 48 pasos). Los estados son:

```text
DEFICIT_SEVERO       luz < 0,50 × mínimo
DEFICIT_LEVE         0,50 × mínimo ≤ luz < mínimo
CONFORTABLE          mínimo ≤ luz ≤ máximo
EXCESO_LEVE          máximo < luz ≤ 1,25 × máximo
EXCESO_SEVERO        luz > 1,25 × máximo
DATOS_INSUFICIENTES  zona cerrada o sin datos completos
```

**Veredicto de habitabilidad por zona.** Cada paso evaluable (los que no son `DATOS_INSUFICIENTES`) recibe una calidad `q`: 1 si es confortable, 0,5 si es déficit o exceso leve y 0 si es severo. El puntaje de la zona es el promedio de `q`. El veredicto es:

```text
HABITABLE       puntaje ≥ 0,90
CASI_HABITABLE  0,75 ≤ puntaje < 0,90
NO_HABITABLE    puntaje < 0,75 o más del 5 % de pasos en DEFICIT_SEVERO
```

También se reportan el puntaje diurno y nocturno de cada zona, la causa predominante (déficit diurno o nocturno, exceso solar o artificial) con una recomendación para las zonas casi habitables, y el puntaje del hotel ponderado por prioridad de actividad y piso.

**Salidas por franja horaria.** Con el índice rojo-negro (sección 4.5) se calculan las franjas día completo, 00–06, 06–12, 12–18, 18–22 y 22–24. Para cada una:

```text
energía en Wh y kWh
energía por actividad y por torre
hora pico y potencia pico del generador
déficit residual (lux·h bajo el mínimo)
energía no asignada (Wh que habrían cerrado ese déficit)
zonas críticas (las 10 con más horas en déficit)
horas con déficit por zona e instantes con déficit
estado predominante de cada zona en la franja
```

**Salidas de reasignación.** Cada huésped que debe moverse recibe una propuesta con estado `PROPUESTA` o `NO_HAY_ALTERNATIVA`, habitación actual y propuesta, score, restricciones del huésped y la lista de habitaciones revisadas y descartadas con motivo `MENOR_PUNTAJE`. Si no hay alternativa, el motivo es uno de estos:

```text
SIN_HABITACIONES_HABITABLES_LIBRES  no hay ninguna habitación habitable con cama libre
SIN_CAPACIDAD                       las permitidas ya se llenaron con otros huéspedes
RESTRICCIONES                       las restricciones del huésped excluyen todas las libres
```

El sistema también reporta potencia máxima, energía total en Wh, energía por torre y piso, uso del generador por hora y los conteos de las estructuras de datos: pares evaluados en el grafo, comparaciones del AVL contra la búsqueda lineal y rotaciones del rojo-negro contra el AVL.

# 3. Modelo de iluminación

## 3.1 Componentes

Para cualquier instante:

```text
E_total(z,t) = E_natural(z,t) + E_reflejada(z,t) + E_artificial(z,t)
```

Durante el día (06:00–18:00) se calcula luz solar mediante el perfil climático, orientación, sombras, vidrio y paredes. Durante la noche:

```text
E_natural = 0
E_reflejada_solar = 0
E_total = E_artificial
```

La luz artificial se mantiene separada para no confundir una luminaria nocturna con luz natural.

## 3.2 Clima de Bogotá

La ubicación de referencia es 4.7110° N, -74.0721° O. Se utilizan perfiles basados en NASA POWER, climatología 2001–2020:

| Perfil | Mes | Radiación (kWh/m²/día) | Nubosidad | Precipitación (mm/día) | `factor_luz` |
|---|---|---:|---:|---:|---:|
| Nubes parciales (base) | febrero | 4,863 | 0,7089 | 2,51 | 0,689 |
| Nublado | mayo | 4,477 | 0,8582 | 6,68 | 0,634 |
| Lluvioso | abril | 4,454 | 0,8487 | 6,97 | 0,631 |
| Cielo despejado | clear-sky anual | 7,063 | 0,0 | 0,0 | 1,000 |

La luz base usa la radiación real del perfil:

```text
factor_luz = min(1, radiación / radiación_cielo_despejado)
C(t)       = sin(π · (t − 6) / 12)            para 06:00 ≤ t < 18:00
E_base(t)  = K_lux · C(t) · factor_luz
```

`radiación_cielo_despejado` es 7,063 kWh/m²/día (NASA POWER) y está en `parametros_evaluacion.luz`. `factor_luz` lo calcula el código (`PerfilClimatico.factor_luz`); no es un dato escrito a mano. `K_lux` es 900.

La nubosidad reparte la luz entre directa y difusa:

```text
f_directa = max(0,10; 1 − nubosidad)
f_difusa  = 0,15 + 0,45 · nubosidad
```

La precipitación se carga y se reporta, pero es informativa: no entra en el cálculo. La conversión de irradiancia a lux es una aproximación mediante `K_lux`. Sin calibración, el resultado se llama lux de referencia y no lux fotométrico medido.

## 3.3 Transmisión y refracción

Para cada ventana, con `θ_i` el ángulo entre la normal de la ventana y la dirección del sol:

```text
E_ventana = E_base × VLT × (cos θ_i × F(θ_i) × f_directa + f_difusa)
E_natural(z) = promedio de E_ventana en las ventanas de la zona
```

Si otra torre bloquea el rayo solar, la componente directa es cero y solo queda la difusa. La difusa usa la VLT del catálogo sin corrección angular.

La otra torre también tapa parte del cielo. Por eso la difusa de cada ventana se multiplica por `1 − obstrucción`:

```text
obstrucción = min(1, Σ cos_ventana × A_f / (π·d² + A_f))   sobre las fachadas que la ventana tiene enfrente
```

En el escenario base 40 ventanas tienen obstrucción. `TP-H-101-V1`, al este y frente a TG, tiene 0,593.

`F(θ_i)` es el factor angular de la luz directa (`factor_angular_vidrio` en `geometria.py`). Primero se calcula el ángulo de refracción con Snell:

```text
n_aire × sin(θ_i) = n_vidrio × sin(θ_t),   n_aire = 1, n_vidrio = 1,5
```

Luego la transmitancia de Fresnel en una cara, para luz no polarizada (promedio de las componentes s y p):

```text
r_s = ((cos θ_i − n cos θ_t) / (cos θ_i + n cos θ_t))²
r_p = ((cos θ_t − n cos θ_i) / (cos θ_t + n cos θ_i))²
T(θ_i) = 1 − (r_s + r_p) / 2
```

El vidrio tiene dos caras, así que la transmitancia se eleva al cuadrado. El resultado se normaliza con la incidencia perpendicular para que a 0° se conserve la VLT del catálogo:

```text
F(θ_i) = (T(θ_i) / T(0°))²
```

| θ_i | 30° | 45° | 60° | 75° | 85° |
|---|---:|---:|---:|---:|---:|
| F(θ_i) | 0,997 | 0,979 | 0,900 | 0,605 | 0,163 |

No se modelan reflexión múltiple dentro del vidrio, absorción según el espesor, dispersión espectral ni marcos detallados.

## 3.4 Luz reflejada

La luz reflejada sólo existe de día y tiene dos partes:

```text
E_reflejada(z) = promedio de E_exterior en las ventanas de z + E_ri(z)
```

### Reflexión exterior entre torres (primer orden)

El grafo crea relaciones como:

```text
Fachada → Ventana de la otra torre
```

Los orígenes son las 8 fachadas (4 por torre). Cada fachada recibe luz del sol y del cielo según hacia dónde mira:

```text
luz_fachada = E_base × (max(0, n · sol) × f_directa + f_difusa)
```

Para cada ventana se toma su punto de salida en la fachada de su torre (`punto_en_fachada`). Desde ahí, `consultar_radio` (18 m) entrega las fachadas candidatas de la otra torre, y `d` es la distancia al punto más cercano de cada una. Se exige que ventana y fachada se miren y que un rayo entre ellas no cruce otra torre (`_visible`). El peso de la arista es:

```text
peso = ρ_fachada × cos_fachada × cos_ventana × A_f / (π·d² + A_f)
```

`A_f / (π·d² + A_f)` es un factor de vista aproximado para una superficie grande de área `A_f`. Solo se crean aristas con peso mayor que 0,0001. La luz exterior que entra por una ventana es:

```text
E_exterior(ventana) = Σ luz_fachada × peso × VLT     sobre sus aristas entrantes
```

La luz reflejada por una fachada no vuelve a reflejarse en otra. A las 12:00 del escenario base, `TG-F-OESTE` recibe 290,6 lux y su arista hacia `TP-H-101-V1` pesa 0,3559.

### Reflexión interior (flujo dividido)

La luz que entra al recinto rebota en sus superficies interiores:

```text
E_ri  = Φ × ρ / (A_int × (1 − ρ))
Φ     = Σ_ventanas (E_ventana + E_exterior) × área_ventana
A_int = 2 × área + 4 × √área × 3 m
```

`ρ` es la reflectancia de la pared del recinto. Una habitación de 24 m² tiene `A_int ≈ 106,8 m²`; con pared blanca (`ρ = 0,80`) el factor `ρ / (1 − ρ)` vale 4. La fórmula promedia todos los rebotes interiores, así que no es de primer orden, y hace que el color de la pared cambie la luz de su propio cuarto.

A las 12:00 del escenario base:

| Zona | Situación | Natural (lux) | Reflejada (lux) |
|---|---|---:|---:|
| `TP-H-101` | Ventana al este, frente a TG | 97,0 | 98,4 |
| `TP-H-102` | Ventana al norte, sin torre enfrente | 358,7 | 26,9 (casi toda interior) |
| `TG-H-101` | Ventana al este, sin torre enfrente | 238,3 | 17,9 |

La luz artificial no recibe reflexión aparte: el `CU = 0,70` del método de lúmenes ya incluye el rebote interior. El `CU` es fijo y no cambia con el color de la pared.

# 4. Estructuras de datos

## 4.1 Árbol jerárquico

```text
Hotel
├── Torre
│   ├── Piso
│   │   ├── ZonaHotel
│   │   │   └── Ventana
```

`HabitacionHotel` es una especialización de `ZonaHotel`. `Huesped` se relaciona con `HabitacionHotel` mediante `Asignacion`. La energía por torre y piso se agrega recorriendo este árbol en postorden.

## 4.2 Octree

El Octree indexa torres, fachadas, paredes, ventanas y luminarias. Se consulta para:

- detectar si una torre bloquea un rayo solar (`consultar_rayo`);
- encontrar las fachadas de la otra torre cercanas a cada ventana al construir el grafo (`consultar_radio`);
- comprobar visibilidad entre fachada y ventana.

Un objeto que atraviesa varios octantes permanece en el nodo padre. Esto evita duplicar cajas grandes.

## 4.3 Grafo de influencia

Cada arista contiene `origen` (fachada), `destino` (ventana de la otra torre) y `peso`. La distancia, la orientación, la reflectancia y la visibilidad se evalúan al construirla y quedan resumidas en el peso. Las aristas se guardan en dos diccionarios: por origen y por destino. El índice por destino permite que, en cada instante, una ventana recorra solo sus aristas entrantes. El grafo guarda también la obstrucción del cielo de cada ventana (sección 3.3).

La construcción pide al Octree, para cada ventana, las fachadas en un radio de 18 m desde su punto de salida (`Octree.consultar_radio`), en vez de compararla con todas. En el escenario base:

| Medida | Comparación ingenua | Con Octree |
|---|---:|---:|
| Pares fachada–ventana evaluados | 1.232 (8 × 154) | 68 (7.834 nodos del Octree visitados) |
| Aristas recorridas por instante en la reflexión exterior | 154 × 46 | 46 |

El grafo resultante tiene 46 aristas: `TP-F-ESTE` → 24 ventanas de TG, `TG-F-OESTE` → 16 ventanas de TP y `TP-F-NORTE` → 6 ventanas de recreaciones de TG. 40 ventanas tienen obstrucción. Las salidas son idénticas a las de la comparación ingenua; solo cambia el número de comparaciones.

## 4.4 Árbol AVL: bolsa de habitaciones para la reasignación

El AVL guarda las habitaciones con veredicto `HABITABLE` y al menos una cama libre. La clave es:

```text
(torre, piso, −calidad, habitacion_id)
calidad = w_luz × puntaje + w_energia × ahorro
```

`ahorro` es 1 menos la energía de la habitación dividida por la mayor energía de una zona. La calidad no depende del huésped. Con esta clave, las habitaciones de un mismo piso quedan juntas y ordenadas de mejor a peor.

Operaciones usadas:

- `insertar`, al construir la bolsa;
- `sucesor` (menor clave ≥ x), para obtener la mejor habitación de un piso con la clave `(torre, piso, −∞, "")`;
- `siguiente` (menor clave > x), para seguir dentro del piso cuando el huésped tiene preferencia de orientación;
- `eliminar` con rebalanceo, cuando una habitación se llena. Así dos huéspedes no reciben la misma cama.

Se eligió AVL porque el trabajo es de lectura: cada huésped hace varias consultas y como máximo una eliminación, y el equilibrio estricto mantiene la altura baja. En el escenario base el AVL tiene 78 habitaciones habitables libres, altura 7, 58 rotaciones y 417 comparaciones de construcción. Se construye y se reporta siempre, aunque nadie necesite moverse.

## 4.5 Árbol rojo-negro: índice temporal de resultados

El rojo-negro guarda los resultados de la simulación con clave `(hora, zona_id)`. Cada resultado se inserta en cuanto se calcula. Las franjas se consultan con un rango semiabierto `[inicio, fin)`, en `O(log R + k)`, y de ahí salen las salidas por franja de la sección 2.

Se eligió rojo-negro porque el índice tiene muchas inserciones (6.096) y pocas consultas (6 franjas), y en general hace menos rotaciones al insertar que un AVL. Para comprobarlo, en la simulación principal los mismos resultados se insertan también en un AVL:

| Medida (escenario base, 6.096 resultados) | Rojo-negro | AVL |
|---|---:|---:|
| Rotaciones | 9.099 | 7.232 |
| Altura | 22 | 14 |

En este escenario el rojo-negro rota más. Los resultados llegan casi ordenados: hora ascendente y, dentro de cada hora, tramos largos de IDs ascendentes. Con esa entrada el AVL rota menos. Con 6.096 claves en orden aleatorio se cumple lo esperado: 3.511 rotaciones del rojo-negro contra 4.176 del AVL. Se verificó que el árbol cumple las propiedades de rojo-negro, así que la diferencia viene del orden de los datos y no de la implementación. El índice se mantiene por su papel en las consultas: la franja 18:00–22:00 visita 1.029 nodos, contra 6.096 resultados de recorrer la lista.

# 5. Algoritmos

## 5.1 Sombra y luz natural

```text
para cada instante t:
    si t está en noche:
        natural = 0
        reflejadaSolar = 0
    si t está en día o transición:
        calcular E_base con factor_luz y vector solar
        para cada zona con ventana:
            consultar el rayo solar en el Octree
            determinar sombra por la otra torre
            calcular componente directa (Snell y Fresnel) y difusa (VLT × (1 − obstrucción))
        calcular la luz de cada fachada
        para cada ventana:
            sumar luz_fachada × peso de sus aristas entrantes, por VLT (reflexión exterior)
        para cada zona:
            reflejada = promedio de la exterior de sus ventanas + reflexión interior
```

## 5.2 Balance energético

La iluminación artificial aproximada se calcula así:

```text
E_artificial = eficacia × potenciaAsignada × CU × MF / área
```

Para cada zona abierta se calculan tres demandas de potencia después de descontar luz natural y reflejada: emergencia (para llegar a `min(10 lux, mínimo)`), mínima y objetivo. Ninguna supera la potencia de la luminaria. La prioridad de la zona es:

```text
prioridad = prioridad_actividad × (1 + 0,10 × (piso − 1)) × (1,4 si es habitación ocupada; 1 si no)
```

El balance de cada instante ejecuta:

```text
1. asignar el modo de horario a cada zona (ACTIVA, REDUCIDA o CERRADA);
2. descartar las zonas CERRADA: no reciben energía;
3. reservar el nivel de emergencia para todas las zonas abiertas;
4. completar los mínimos en este orden:
     a. seguridad: parqueaderos;
     b. habitaciones ocupadas;
     c. resto de zonas;
   dentro de cada grupo, por prioridad descendente;
   la zona que no alcanza su mínimo queda en EMERGENCIA;
5. repartir la potencia restante hasta el objetivo, por prioridad descendente,
   sin incluir zonas en EMERGENCIA;
6. guardar potencia, estado y energía del instante.
```

Los órdenes de los pasos 4 y 5 se obtienen con colas de prioridad (`heapq`). El balance solo inserta y extrae el máximo, así que una cola es suficiente y no hace falta un árbol.

La potencia del generador se estima con:

```text
P_generador = 1,20 × máximo_t(suma(P_obj(z,t)))
```

En el escenario base la demanda objetivo máxima es 18.110,7 W; por 1,20 da 21,73 kW, redondeado a 22 kW. La reserva del 20 % es didáctica. El generador no alimenta el consumo total del hotel. En el escenario base el generador alcanza en todos los instantes y ninguna zona entra en `EMERGENCIA`.

## 5.3 Reasignación de huéspedes

Se reasigna a un huésped solo si su habitación tiene veredicto `NO_HABITABLE` en el día completo (sección 2). Un paso aislado bajo el mínimo no basta: el veredicto ya pondera esos pasos.

```text
construir el AVL con las habitaciones HABITABLE con cama libre
para cada huésped en una habitación NO_HABITABLE:
    pisos = pisos permitidos por MISMA_TORRE y PISO_MAXIMO:n, en las dos torres
    para cada piso permitido:
        candidata = sucesor((torre, piso, −∞, ""))
        score = calidad + w_actividad × coincide_orientación − w_cambio × |Δpiso| / piso_máximo
        si el huésped prefiere una orientación:
            seguir con siguiente() mientras otra habitación del piso pueda superar el score
    si hay candidatas:
        elegir la de mayor score; las demás quedan descartadas con motivo MENOR_PUNTAJE
        descontar una cama; si la habitación se llena, eliminarla del AVL
    si no:
        motivo = SIN_HABITACIONES_HABITABLES_LIBRES, SIN_CAPACIDAD o RESTRICCIONES
```

Sin preferencia de orientación, `coincide_orientación` vale 1. Los pesos son `w_luz = 0,5`, `w_actividad = 0,2`, `w_energia = 0,2` y `w_cambio = 0,1`.

El costo es `O(G × F × log H)`, con `G` huéspedes a mover, `F` pisos permitidos y `H` habitaciones en el AVL, contra `O(G × H)` de revisar todas las habitaciones por huésped. En una prueba de carga sobre el escenario base, con 60 de las 78 habitaciones ocupadas marcadas `NO_HABITABLE`, el AVL hizo 2.087 comparaciones contra 6.240 de la búsqueda lineal, con 34 eliminaciones y ninguna habitación con sobrecupo; con restricciones mezcladas, 2.045 contra 6.240. La habitación elegida coincidió, huésped por huésped, con una búsqueda lineal que descuenta capacidad.

La estrategia es greedy en el orden de las asignaciones y no garantiza un óptimo global. En el escenario base nadie se reasigna porque ninguna habitación ocupada queda `NO_HABITABLE`. `deficit_severo.json` muestra el caso sin candidata (`SIN_HABITACIONES_HABITABLES_LIBRES`).

## 5.4 Mejoras medidas y reestructuración

Las mejoras son cambios puntuales que se simulan completos y se comparan contra el escenario actual por puntaje del hotel: vidrio claro en habitaciones, paredes blancas, generador 20 % mayor y objetivo de habitación en 180 lux.

La reestructuración busca, para las actividades con zonas casi habitables o no habitables, combinaciones de pared, vidrio, orientaciones de ventanas, objetivo de iluminación y horario de cocina y recreación. Acepta un cambio solo si mejora el puntaje, luego la cantidad de no habitables y luego la energía. Usa como máximo 30 evaluaciones y 3 rondas. No cambia la geometría de las torres.

# 6. Flujo completo

1. Validar exactamente dos torres.
2. Cargar pisos, zonas, ventanas, vidrios, paredes, fachadas y luminarias.
3. Cargar huéspedes, restricciones, ocupaciones y asignaciones.
4. Cargar clima, horarios de actividad y cierre, y nivel de emergencia.
5. Construir el Octree y el grafo de influencia.
6. Recorrer `00:00`–`24:00` en pasos de 30 minutos con el mismo evaluador.
7. Calcular componentes naturales, reflejadas y artificiales.
8. Ejecutar el balance, guardar resultados e insertarlos en el índice rojo-negro.
9. Calcular las salidas por franja horaria.
10. Calcular el veredicto de habitabilidad de cada zona.
11. Construir el AVL y buscar alternativas para huéspedes en habitaciones `NO_HABITABLE`.
12. Exportar reporte energético y lumínico.

La interfaz web (`web/`) se sirve con `python -m src.api`. Tiene formularios para las entradas, un plano por torre y piso con la leyenda de abreviaturas, un selector de franja horaria que colorea cada zona con su estado en la franja y muestra su reporte, los veredictos, las sugerencias, las mejoras medidas, la reestructuración y una tabla con las estructuras de datos y sus comparaciones.

# 7. Complejidad y casos de prueba

Notación: `V` ventanas, `B` torres, `T` instantes, `S` fachadas, `E` aristas, `Z` zonas, `N` nodos del árbol jerárquico, `R` resultados, `k` elementos devueltos, `G` huéspedes a mover, `F` pisos permitidos, `H` habitaciones.

```text
Sombras sin Octree:            O(V × B × T)
Sombras con Octree:            O(V × T × (log B + k)) esperado
Grafo ingenuo:                 O(S × V)
Grafo con Octree:              O(V × (log B + k)) esperado
Luz reflejada por instante:    O(S + V + E), con aristas indexadas por destino
Balance por instante:          O(Z log Z), con heapq
Agregación por torre y piso:   O(N)
Índice rojo-negro:             O(R log R) construcción, O(log R + k) por franja
Recorrer la lista por franja:  O(R)
Reasignación con AVL:          O(H log H) construcción, O(G × F × log H) consultas
Reasignación lineal:           O(G × H)
```

Valores medidos en el escenario base: 68 pares evaluados en el grafo contra 1.232 ingenuos; 1.029 nodos visitados en la franja 18:00–22:00 contra 6.096 resultados; en la prueba de carga de reasignación, 2.087 comparaciones del AVL contra 6.240 lineales.

Los 10 casos de prueba están automatizados con `unittest` en `tests/test_casos_plan.py`. Se ejecutan desde la raíz con `python -m unittest` y todos pasan.

| # | Caso | Qué verifica |
|---|---|---|
| 1 | Ventana orientada al sol y sin obstáculo | La luz natural a las 09:00 coincide con la fórmula de 3.3 y supera la sola componente difusa. |
| 2 | Ventana sombreada por la otra torre | La ventana bloqueada recibe solo la componente difusa. |
| 3 | Transmisión con cada preset de vidrio | La luz es proporcional a la VLT de cada vidrio; `F(0°) = 1`; `F(75°) < F(30°)`; Snell da `sin θ_t = sin θ_i / 1,5`. |
| 4 | Reflexión de primer orden sin cascada | Las aristas van solo de una fachada a ventanas de la otra torre, con peso ≤ reflectancia; la reflejada coincide con la exterior (aristas entrantes) más la interior; una pared oscura da menos reflejada que una blanca; de noche la reflejada es 0. |
| 5 | Noche con luz natural cero y luminaria activa | De noche la luz natural y la reflejada son cero; una habitación ocupada recibe luz artificial y no queda en déficit. |
| 6 | Generador suficiente para mínimos, pero no para todos los objetivos | Con una capacidad entre la suma de mínimos y la de objetivos, todas las zonas alcanzan su mínimo, ninguna entra en `EMERGENCIA` y se usa toda la capacidad. |
| 7 | Habitación ocupada con déficit y habitación compatible disponible | Con una sola habitación habitable de una cama libre, el primer huésped la recibe, la habitación sale del AVL y los demás reciben `SIN_CAPACIDAD`. |
| 8 | Habitación ocupada con déficit sin alternativa | `deficit_severo.json` da `SIN_HABITACIONES_HABITABLES_LIBRES`; con `MISMA_TORRE` y la única candidata en la otra torre, el motivo es `RESTRICCIONES`. |
| 9 | Zona cerrada y habitación en descanso sin falso déficit | `TP-COC-01` a las 02:00 está `CERRADA`, sin potencia y fuera del puntaje; `TP-H-101` a las 23:00 está `REDUCIDA` sin déficit. |
| 10 | Clima nublado contra cielo despejado | `factor_luz = radiación / 7,063` y el cielo despejado da más luz natural que el nublado. |

Los casos 7 y 8 modifican los veredictos del escenario base en memoria, porque ningún JSON de prueba tiene a la vez habitaciones ocupadas no habitables y habitaciones libres habitables.

# 8. Fuentes, supuestos y límites

El clima se basa en NASA POWER; las torres se inspiran en DOE Commercial Reference Buildings; la regulación se contrasta con el RETILAP vigente y sus modificaciones; ISO 30061 y NFPA 101 sirven de referencia para el nivel de emergencia; UNE-EN 12464-1 sirve como guía complementaria; Cardinal Glass respalda los presets de transmitancia y Edmund Optics la aproximación óptica.

Los rangos de lux, horarios, áreas, potencias, reflectancias, huéspedes, nivel de emergencia y capacidad del generador son supuestos didácticos. La página oficial del Ministerio informa que el RETILAP vigente fue modificado por la Resolución 40286 del 23 de junio de 2026, pero no se usa para presentar los presets como una transcripción normativa. El sistema no certifica cumplimiento ni reemplaza una medición.

Alcance: la geometría de las torres es fija. El sistema mide mejoras y propone reestructuraciones de variables de luz (actividades, acabados, horarios y generador), pero no mueve ni rediseña edificios.

Limitaciones conocidas:

- Los resultados son aproximaciones educativas en lux de referencia.
- La precipitación es informativa y no entra en el cálculo.
- La reflexión exterior entre torres es de primer orden.
- El `CU` de la luz artificial es fijo y no cambia con el color de la pared.
- Las superficies interiores de cada recinto se representan con un solo valor de reflectancia.
- Las ventanas están dentro de la caja de su torre; para la reflexión exterior se usa su punto de salida en la fachada.

# 9. Criterio de éxito

La propuesta se considera cumplida si el sistema procesa las dos torres en 24 horas, diferencia día y noche con clases compartidas, usa el Octree, el grafo, el AVL y el rojo-negro con un efecto medible en los resultados o en las comparaciones, calcula el balance energético con nivel de emergencia, clasifica las cuatro actividades, emite un veredicto de habitabilidad por zona, reporta déficits por franja horaria, puede proponer o rechazar una reasignación de huésped de forma explicable y pasa los 10 casos de prueba automatizados.
