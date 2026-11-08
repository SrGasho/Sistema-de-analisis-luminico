# Guía de funcionamiento del sistema

Esta guía recorre, en el orden en que se ejecuta, lo que hace el sistema con los datos: qué parte del código se encarga de cada paso, con qué fin y cómo lo resuelve. Las cifras corresponden al escenario base (`data/datos_hotel.json`) y se obtuvieron ejecutando el código. Cada paso tiene una tabla «Dónde está en el código» con enlaces a la línea exacta; los números de línea corresponden a la versión actual de `main`.

Resumen del recorrido:

1. Cargar los datos y construir el hotel (`src/io_datos.py`).
2. Preparar el espacio: Octree y grafo de influencia (`src/octree.py`, `src/influencia.py`).
3. Simular el día en 48 pasos de media hora (`src/simulacion.py`, `src/clima.py`, `src/geometria.py`, `src/balance.py`, `src/evaluacion.py`).
4. Reportes por franja horaria con el árbol rojo-negro (`src/temporal.py`).
5. Veredicto de habitabilidad por zona (`src/habitabilidad.py`).
6. Reasignación de huéspedes con el árbol AVL (`src/reasignacion.py`).
7. Sugerencias y salida hacia la interfaz (`src/sugerencias.py`, `src/api.py`).

---

## Paso 1. Cargar los datos y construir el hotel

**Archivo:** `src/io_datos.py`, función `cargar_hotel_data`.

**Fin:** convertir el JSON, que es texto con números, en objetos de Python que el resto del sistema pueda usar: un `Hotel` con torres, pisos, zonas, ventanas, paredes, luminarias y huéspedes. Además revisa que los datos tengan sentido antes de simular. Las clases de esos objetos están en `src/modelo.py`, que solo describe sus campos y no hace cálculos.

### 1.1 Completar lo que falte

`_completar_defaults` copia el JSON para no modificar el original y completa los catálogos de vidrios, paredes y acabados con los valores por defecto del inicio del archivo. Si el JSON trae un valor, ese valor reemplaza al de por defecto. Así nunca falta un vidrio o una pared al construir las zonas.

### 1.2 Validar los acabados

`_validar_acabados` comprueba que cada actividad y cada recinto personalizado usen una pared y un vidrio que existan, y una orientación válida (norte, sur, este u oeste). Si hay un error, como escribir `"BLANKO"`, la carga se detiene con un mensaje claro.

### 1.3 Crear los perfiles

- **Iluminación:** un perfil por actividad, con mínimo, objetivo, máximo y prioridad.
- **Clima:** cada perfil recibe la radiación de cielo despejado de referencia (7,063 kWh/m²/día). Con ella calcula su `factor_luz` = radiación / referencia, que es la fracción de luz que deja pasar ese clima.

### 1.4 Construir el edificio

Para cada torre y cada piso se crean las habitaciones. En el piso 1 se crean además las zonas comunes. Los identificadores se numeran de forma continua por torre: en TP, el piso 1 va de `TP-H-101` a `TP-H-108` y el piso 2 empieza en `TP-H-109`.

Cada habitación (`_zona_habitacion`) recibe:

- **Posición.** `_room_center` reparte las habitaciones del piso en una cuadrícula dentro de la caja de la torre. La altura es la mitad de su piso: `(piso − 0,5) × 3 m`.
- **Una ventana de 2 m²**, medio metro hacia el lado al que mira. Las orientaciones se alternan: la primera habitación mira al este, la segunda al norte, la tercera al oeste, la cuarta al sur, y se repite.
- **Una superficie reflectante** (llamada «pared» en el código): un punto en el centro con una sola dirección, **opuesta a la ventana**, y la reflectancia de su color. El cuarto no se modela con cuatro paredes, techo y piso: esta superficie es una abstracción que representa la cara del recinto que refleja luz hacia las ventanas de otros cuartos (ver 2.4).
- **Una luminaria asociada** (`L-TP-H-101`).

Las cocinas y recreaciones (`_zona_comun`) se construyen igual, pero con varias ventanas. `_common_center` las ubica en fila, en una franja libre del piso 1, sin encimarlas.

`_acabado` decide la pared, el vidrio y la orientación de cada zona. Primero usa lo que se haya personalizado para ese recinto (lo que se edita desde el plano) y, si no hay nada, el acabado de su actividad.

**Cómo funcionan las orientaciones.** Visto desde arriba, el eje x crece hacia el este y el eje y hacia el norte. Cada orientación es una flecha de largo 1 que apunta hacia ese lado:

| Orientación | Flecha | Sentido |
|---|---|---|
| Norte | (0, 1, 0) | hacia arriba |
| Este | (1, 0, 0) | hacia la derecha |
| Sur | (0, −1, 0) | hacia abajo |
| Oeste | (−1, 0, 0) | hacia la izquierda |

El tercer número, la altura, es 0 porque las ventanas miran al horizonte. Con esa flecha el código hace tres cosas:

- ubica la ventana: centro + flecha × 0,5 es avanzar medio metro hacia ese lado;
- indica hacia dónde mira la ventana, que es hacia afuera;
- orienta la superficie al revés (flecha × −1), es decir, hacia el lado contrario de su propia ventana. Por eso una superficie nunca le refleja luz a su propio cuarto: solo a ventanas de otros cuartos que la tengan de frente.

Más adelante, al calcular la luz, la flecha de la ventana se compara con la dirección del sol. Si apuntan parecido, el sol pega de frente y entra mucha luz directa. Si quedan de lado, entra poca, y si el sol está detrás, solo entra la luz difusa del cielo. La misma comparación decide si una pared y una ventana "se miran" para que haya reflexión.

### 1.5 Indexar

`hotel.indexar()` arma diccionarios por identificador (`hotel.zonas`, `hotel.habitaciones`) para encontrar cualquier zona de inmediato sin recorrer todo el árbol.

### 1.6 Luminarias

Cada zona recibe una `FuenteIluminacion` con la potencia, la eficacia, el CU y el MF de su actividad.

### 1.7 Huéspedes, asignaciones y ocupación

- **Huéspedes.** Si el JSON solo trae un total, se generan `H-001` a `H-078`.
- **Restricciones por huésped.** No son accesos ni permisos: son pedidos que el huésped tendría si hubiera que cambiarlo de habitación. Solo se usan en la reasignación (paso 6), y solo para quienes estén en una habitación `NO_HABITABLE`.
  - `MISMA_TORRE` (no cambiar de torre) y `PISO_MAXIMO:n` (no pasar del piso n) son obligatorias: descartan las habitaciones que no las cumplen.
  - `ORIENTACION:ESTE`, u otra orientación, es una preferencia: suma puntos a la habitación que coincide, pero no descarta las demás.

  Las restricciones no cambian el reparto de energía ni la ubicación inicial de los huéspedes.
- **Asignación.** Es la relación huésped–habitación, es decir, quién duerme dónde. Si el JSON no la trae, se ocupan en orden las primeras habitaciones de cada torre: 24 en TP y 54 en TG.
- **Ocupación.** Es el número de huéspedes en cada habitación. Cada asignación suma 1. Con capacidad 2, una habitación con ocupación 0 está vacía, con 1 tiene una cama libre y con 2 está llena.

  La ocupación se usa en tres partes:
  - **Balance:** una habitación ocupada recibe energía antes que las demás y su prioridad pesa 1,4 veces más.
  - **Reasignación:** un huésped solo puede ir a una habitación con cama libre.
  - **Validación:** ninguna habitación puede pasar de su capacidad.

### 1.8 Validación final

`_validar` revisa que:

- haya exactamente dos torres y al menos una zona;
- cada perfil cumpla 0 ≤ mínimo ≤ objetivo ≤ máximo;
- ninguna habitación supere su capacidad;
- cada asignación apunte a un huésped y una habitación existentes.

### Dónde está en el código

| Qué | Dónde |
|---|---|
| Entrada del paso | [`cargar_hotel_data`, `src/io_datos.py` línea 71](../src/io_datos.py#L71) |
| Valores por defecto | [`_completar_defaults`, línea 55](../src/io_datos.py#L55) |
| Validar acabados | [`_validar_acabados`, línea 291](../src/io_datos.py#L291) |
| Perfiles de iluminación y clima | [línea 74](../src/io_datos.py#L74) |
| Bucle de torres, pisos y zonas | [línea 85](../src/io_datos.py#L85) |
| Habitación | [`_zona_habitacion`, línea 219](../src/io_datos.py#L219) y [`_room_center`, línea 262](../src/io_datos.py#L262) |
| Zona común | [`_zona_comun`, línea 237](../src/io_datos.py#L237) y [`_common_center`, línea 271](../src/io_datos.py#L271) |
| Acabado de cada zona | [`_acabado`, línea 193](../src/io_datos.py#L193) |
| Índices por ID | [`Hotel.indexar`, `src/modelo.py` línea 207](../src/modelo.py#L207) |
| Luminarias | [línea 127](../src/io_datos.py#L127) |
| Huéspedes y asignaciones | [línea 145](../src/io_datos.py#L145) y [línea 171](../src/io_datos.py#L171) |
| Validación final | [`_validar`, línea 312](../src/io_datos.py#L312) |

### Resultado y costo del paso

Sale un `Hotel` con 127 zonas (104 habitaciones y 23 comunes), 154 ventanas, 127 paredes, 127 luminarias y 78 huéspedes asignados.

**Complejidad: lineal, O(Z + V + G)**, con Z zonas, V ventanas y G huéspedes. Aunque el bucle del edificio tiene tres niveles (torre, piso, habitación), pasa una sola vez por cada habitación y hace con ella un trabajo fijo. Las búsquedas de acabado son en diccionario, en tiempo constante. Con los datos del hotel tarda milisegundos, así que este paso nunca es el cuello de botella.

---

## Paso 2. Preparar el espacio: Octree y grafo de influencia

**Fin:** organizar la geometría **una sola vez**, antes de recorrer el día, para que en cada media hora se puedan responder rápido dos preguntas:

- ¿La otra torre le tapa el sol a esta ventana? (se usa en el paso 3 para las sombras)
- ¿Cuánta luz rebota de las paredes a esta ventana? (se usa en el paso 3 para la luz reflejada)

Este paso **no calcula luz**. Construye dos herramientas: el **Octree**, que sirve para buscar cosas en el espacio, y el **grafo de influencia**, que guarda qué pared le refleja luz a qué ventana.

### Dónde está en el código

| Qué | Dónde |
|---|---|
| Se arma todo al crear el simulador | [`SimuladorUnificado.__init__`, `src/simulacion.py` líneas 24–26](../src/simulacion.py#L24) |
| Llenar el Octree con los objetos del hotel | [`_crear_octree`, `src/simulacion.py` línea 70](../src/simulacion.py#L70) |
| La estructura Octree | [`class Octree`, `src/octree.py` línea 24](../src/octree.py#L24) |
| Insertar y dividir | [`_insertar`, línea 34](../src/octree.py#L34); [`_dividir`, línea 53](../src/octree.py#L53); [`_hijo_contenedor`, línea 61](../src/octree.py#L61) |
| Consulta de rayo | [`consultar_rayo`, línea 71](../src/octree.py#L71) |
| Consulta de radio | [`consultar_radio`, línea 85](../src/octree.py#L85) |
| Construir el grafo | [`GrafoInfluencia.construir`, `src/influencia.py` línea 29](../src/influencia.py#L29) |
| Revisar si algo tapa pared → ventana | [`_visible`, `src/influencia.py` línea 70](../src/influencia.py#L70) |
| Uso de la consulta de rayo para sombras (paso 3) | [`_sombreada`, `src/simulacion.py` línea 118](../src/simulacion.py#L118) |
| Uso del grafo en cada media hora (paso 3) | [`reflejada_para`, `src/influencia.py` línea 80](../src/influencia.py#L80) |

`GrafoInfluencia.construir` significa «el método `construir` de la clase `GrafoInfluencia`». Está en `src/influencia.py` y se llama desde `src/simulacion.py` línea 26.

### 2.1 Qué es el Octree y cómo se arma

**`src/octree.py` define la estructura** (cómo se guarda y cómo se consulta). **`_crear_octree` en `src/simulacion.py` la llena** con los objetos del hotel.

**La idea.** Todo el hotel cabe en una caja grande. Si una caja tiene muchos objetos, se parte en 8 cajas iguales (se corta a la mitad a lo ancho, a lo largo y a lo alto) y cada objeto baja a la caja pequeña donde cabe completo. Las cajas que vuelven a llenarse se parten otra vez. Queda un árbol: la raíz es la caja grande y cada nodo tiene 0 u 8 hijos.

**Cómo inserta (`_insertar`):**

1. Si el nodo ya tiene hijos, busca el hijo donde el objeto **cabe completo** (`_hijo_contenedor`) y baja ahí.
2. Si no cabe completo en ningún hijo, porque queda partido entre dos cajas, se queda en el nodo actual.
3. Si el nodo pasa de **16 objetos** y no ha llegado a **6 niveles**, se parte en 8 (`_dividir`) y reparte los objetos que caben en los hijos.

**Qué se mete (`_crear_octree`):** las 2 torres, las 154 ventanas (cada una como un cubito de 10 cm), las 127 paredes y las 127 luminarias. La caja raíz se calcula para que quepan todos, con 2 m de margen: x de −2 a 91 m, y de −2 a 45 m, z de −2 a 20 m.

**Cómo queda en el escenario base (medido):**

| Nivel | Nodos |
|---|---|
| 0 (raíz) | 1 |
| 1 | 8 |
| 2 | 56 |
| 3 | 32 |

- La raíz guarda 44 objetos: las **2 torres** (cada una es enorme y cruza varias cajas, así que nunca baja) y 42 objetos que quedaron justo sobre una línea de corte.
- Ejemplo: la ventana `TP-H-101-V1` bajó 2 niveles y quedó en una caja de x −2 a 21,25 m, y −2 a 9,75 m, z −2 a 3,5 m que comparte con solo otros 2 objetos.

### 2.2 Las dos consultas del Octree

Las dos consultas recorren el árbol desde la raíz y **descartan cajas completas** sin mirar lo que tienen adentro. Esa es la ganancia.

**`consultar_rayo` (rayo): «¿qué cosas cruza esta línea?»**

Recibe un punto de partida y una dirección. En cada nodo revisa si la línea atraviesa la caja; si no, descarta ese nodo y todo lo que tiene debajo. Devuelve los objetos cuya caja cruza la línea.

Se usa para **dos** cosas, y ninguna es calcular la reflexión:

- **Sombras** (`_sombreada`, paso 3): se lanza una línea desde la ventana hacia el sol. Si cruza **la otra torre**, el sol directo no llega a esa ventana. Ejemplo medido: a las 7:00 el sol sale por el este; la ventana `TP-REC-03-V1` (planta baja de TP, mirando al este) lanza la línea y esta cruza `TG`, que está al este de TP. Esa ventana queda en sombra a esa hora y solo recibe la luz difusa del cielo.
- **Visibilidad para el grafo** (`_visible`, paso 2.3): se lanza una línea de una pared a una ventana para saber si una torre se interpone.

**`consultar_radio` (radio): «¿qué cosas hay cerca de este punto?»**

Es otra pregunta, independiente del rayo. Recibe un punto y una distancia y devuelve los objetos a esa distancia o menos. En cada nodo mide la distancia del punto a la caja; si la caja entera está más lejos que el radio, la descarta.

Se usa **solo para construir el grafo**: a cada pared se le piden las ventanas a 18 m o menos, para no compararla con las 154. Ejemplo medido: para la pared `TP-H-106-P1` la consulta visitó 49 de los 97 nodos y devolvió 49 ventanas candidatas.

### 2.3 Cómo se construye el grafo de influencia

**La idea.** Cuando el sol ilumina una pared, parte de esa luz rebota y llega a las ventanas que la pared «ve». El grafo guarda esas relaciones como flechas **pared → ventana**. Cada flecha (arista) tiene un **peso**: la fracción de la luz de la pared que llega a esa ventana.

**Qué hace `construir`, para cada una de las 127 paredes:**

1. **Candidatas.** `consultar_radio` entrega las ventanas a 18 m o menos.
2. **Distancia.** Descarta la ventana si está a 0 m o a más de 18 m.
3. **¿Se miran?** La pared debe mirar hacia la ventana y la ventana hacia la pared. Se mide con las flechas del paso 1: `cos_pared` = qué tan de frente mira la pared a la ventana (1 de frente, 0 de lado o de espaldas) y `cos_ventana` lo mismo desde la ventana. Si alguno es 0, se descarta.
4. **¿Algo se interpone?** `_visible` lanza una línea de la pared a la ventana con `consultar_rayo`. Si cruza una torre, se descarta. Si pared y ventana están en la misma torre, esa torre no cuenta, porque la línea nace dentro de ella.
5. **Peso.** `peso = reflectancia × cos_pared × cos_ventana / (1 + distancia²)`. Se guarda la arista si el peso pasa de 0,0001.

**Ejemplo real: la pared `TP-H-106-P1`** (habitación 106, piso 1 de TP, pared blanca ρ = 0,80, mirando al sur):

- `consultar_radio` devolvió 49 ventanas candidatas.
- 41 se descartaron porque no se miran con la pared.
- 8 se convirtieron en aristas:

| Ventana | Distancia | `cos_pared` | `cos_ventana` | Peso |
|---|---|---|---|---|
| `TP-H-102-V1` (mira al norte, de frente) | 9,95 m | 1,000 | 1,000 | 0,00800 |
| `TP-H-110-V1` (igual, un piso arriba) | 10,39 m | 0,957 | 0,957 | 0,00673 |
| `TP-H-118-V1` | 11,62 m | 0,856 | 0,856 | 0,00431 |
| `TP-H-126-V1` | 13,42 m | 0,742 | 0,742 | 0,00243 |
| `TP-H-101-V1` (mira al este, en diagonal) | 14,58 m | 0,717 | 0,697 | 0,00187 |
| `TP-H-109-V1` | 14,89 m | 0,702 | 0,683 | 0,00172 |
| `TP-H-117-V1` | 15,77 m | 0,663 | 0,645 | 0,00137 |
| `TP-H-125-V1` | 17,13 m | 0,610 | 0,593 | 0,00098 |

Comprobación del primero: 0,80 × 1,000 × 1,000 / (1 + 9,95²) = 0,80 / 100,0 ≈ 0,0080. Se ve que el peso baja con la distancia y con el ángulo.

**Dos índices de las mismas aristas** (`agregar_arista`):

- `adyacencias`: por pared → «¿a qué ventanas ilumina esta pared?»
- `entrantes`: por ventana → «¿qué paredes le llegan a esta ventana?». Por ejemplo, a `TP-H-101-V1` le llegan 4 paredes: `TP-H-106-P1` (0,00187), `TP-H-114-P1` (0,00172), `TP-H-122-P1` (0,00137) y `TP-H-130-P1` (0,00098).

En el paso 3, en cada media hora, cada ventana suma `luz de la pared × peso` de sus entrantes (`reflejada_para`). Es un solo rebote: las ventanas nunca son origen de aristas.

### 2.4 Qué guarda el grafo y cómo se usa

**Qué reflexión representa.** Es luz **exterior que rebota entre recintos**, no la luz que rebota dentro de un cuarto. Cada superficie recibe la luz exterior del sol (`E_base`) y la refleja hacia las ventanas de otros cuartos que la tienen de frente a 18 m o menos. Como mira hacia el lado contrario de su propia ventana, de las 521 aristas ninguna une una superficie con la ventana de su mismo recinto. La reflexión interior (luz que entra y rebota en las paredes, techo y piso del propio cuarto) no está modelada.

```
  TP-H-102 (ventana mira al NORTE ↑)          TP-H-106 (superficie mira al SUR ↓)
        ┌───────┐                                   ┌───────┐
        │       │  ventana ↑  ······ luz rebotada ·· ↓ sup.  │
        └───────┘                                   └───────┘
     y ≈ 5,7 m          ←—— 9,95 m ——→              y ≈ 15,7 m
```

**Por qué una superficie tiene varias aristas.** El grafo nace en las superficies (origen) y llega a ventanas (destino). Cada superficie tiene tantas aristas como ventanas de otros cuartos estén a 18 m o menos, la tengan de frente y no tengan una torre en medio. `TP-H-106-P1` tiene 8: las 4 ventanas de su misma columna en los 4 pisos (`102`, `110`, `118`, `126`), que miran al norte hacia ella, y las 4 de la columna vecina (`101`, `109`, `117`, `125`), que la ven en diagonal y reciben menos.

| Parte | Qué es |
|---|---|
| Nodos | Las paredes, que originan la luz rebotada, y las ventanas, que la reciben |
| Arista | Una flecha pared → ventana: «esta pared le pasa luz a esta ventana» |
| Peso | Qué fracción de la luz de esa pared llega a esa ventana |

El radio se mira desde la pared: cada pared busca sus ventanas cercanas, y estas solo son candidatas. Cada par recibe su propio peso, o se descarta. No hay una reflexión igual para todas: más cerca y más de frente pesa más.

En el escenario base hay 521 aristas. 85 de las 154 ventanas reciben al menos una (la que más recibe tiene 12). Las otras 69 no reciben luz reflejada porque ninguna pared cercana las mira.

**Uso en cada media hora (paso 3).** `reflejada_para` calcula:

```
luz reflejada de la ventana = suma de (luz que recibe cada pared × peso de su arista)
```

La luz reflejada de la zona es el promedio de sus ventanas.

**Ejemplo real: `TP-H-101`.** Tiene una ventana con 4 aristas entrantes, cuyos pesos suman 0,00595.

| Hora | Luz que recibe cada pared | Luz reflejada en `TP-H-101` |
|---|---|---|
| 09:00 | 438,2 lux | 438,2 × 0,00595 ≈ 2,6 lux |
| 12:00 | 619,7 lux | 619,7 × 0,00595 ≈ 3,7 lux |
| 20:00 | 0 (noche) | 0 lux |

Los pesos no cambian durante el día; cambia la luz que reciben las paredes. Por eso el grafo se arma una vez.

Como referencia de tamaño: a las 12:00 esa habitación recibe 238,3 lux de luz natural (directa y difusa) y solo 3,7 lux reflejados. En este modelo la reflexión es un aporte pequeño. A mediodía, la zona del hotel con más luz reflejada recibe 20,5 lux.

### Resultado y costo del paso

| Medida (escenario base) | Valor |
|---|---|
| Pares pared–ventana si se comparara todo contra todo | 19.558 (127 × 154) |
| Pares candidatos que entrega `consultar_radio` | 5.581 |
| Nodos del Octree visitados para obtenerlos | 6.911 |
| Paredes con al menos una arista | 72 de 127 |
| Aristas del grafo | 521 |

**Por qué se descartan los pares candidatos:**

| Motivo | Pares |
|---|---|
| Pared y ventana no se miran | 4.982 |
| Fuera de distancia (0 m o más de 18 m) | 56 |
| Tapados por la otra torre | 0 |
| Peso despreciable (0,0001 o menos) | 22 |
| Se convierten en arista | 521 |

La mayoría no se miran porque cada superficie mira en una sola dirección, la contraria a su propia ventana, y solo la ven las ventanas de otros cuartos que miran justo hacia ella.

**Complejidad.**

- **Construir el Octree:** O(B log B) en el caso típico, con B objetos: cada objeto baja unos pocos niveles.
- **Construir el grafo:** con el Octree, O(S × (log B + k)), con S paredes y k candidatas por pared, más una consulta de rayo por cada candidata que pasa los filtros. Sin el Octree sería O(S × V): cada pared contra cada ventana. El costo depende de cuántas ventanas haya cerca de cada pared, no del tamaño total del hotel.
- **Usar el grafo en cada media hora:** O(V + E), lineal en ventanas y aristas.

Las dos estructuras se arman una vez y sirven para los 48 pasos del día.

### Ideas clave del paso

- **La partición del Octree solo sirve para buscar más rápido; no cambia ningún resultado.** Es como ordenar una biblioteca por estantes: una búsqueda descarta estantes completos sin mirar sus libros. Con o sin Octree los resultados son idénticos; solo cambia cuántos pares se revisan (5.581 en vez de 19.558).
- **Un objeto que queda entre dos cajas se queda en la caja de arriba.** No se pierde ni se duplica: lo revisa toda búsqueda que pase por esa caja. Solo cuesta que se revise más seguido, por eso conviene que sean pocos (44 de 410 objetos, incluidas las 2 torres).
- **El rayo responde sí o no:** ¿la línea de la ventana hacia el sol choca con la otra torre? Si choca, no llega luz directa, pero la ventana sigue recibiendo luz difusa del cielo y luz reflejada. Solo las torres cuentan como obstáculo. El rayo no calcula reflexión ni de dónde viene la luz; la dirección del sol se calcula según la hora.
- **El radio responde qué ventanas están cerca de una pared**, para comparar cada pared solo con sus vecinas. No revisa cuántas ventanas tiene cada habitación ni sus medidas; eso se define en el paso 1. El límite de 18 m se debe a que a esa distancia el peso ya se divide entre 1 + 18² = 325.
- **Cada archivo tiene un papel distinto:**
  - `octree.py` es la herramienta de búsqueda.
  - `influencia.py` guarda qué pared le refleja luz a qué ventana, y cuánta, y en cada media hora suma la luz reflejada de cada ventana.
  - `simulacion.py` crea las dos estructuras y las usa en cada paso: el Octree para las sombras y el grafo para la luz reflejada.
- **El Octree descarta por espacio** (lejos o fuera de la línea) y **`influencia.py` descarta por física** (no se miran, hay una torre en medio o el peso es despreciable).
- **El grafo existe para no repetir trabajo.** Como la geometría no cambia durante el día, se calcula una vez; en cada media hora solo se multiplica la luz de las paredes por los pesos guardados.

**Corrección hecha.** Una versión anterior contaba la torre propia como obstáculo en `_visible` y perdía 468 reflexiones dentro de la misma torre (solo quedaban 73 aristas). Ahora la regla coincide con la de las sombras, que tampoco cuenta la torre propia.
