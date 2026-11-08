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
- **Una superficie interior** (llamada «pared» en el código) con la reflectancia del color de sus paredes. El cuarto no se modela con cuatro paredes, techo y piso por separado: esta superficie representa todas sus caras interiores con un solo valor de reflectancia, y se usa para la reflexión interior (paso 3).
- **Una luminaria asociada** (`L-TP-H-101`).

Cada torre recibe además sus **4 fachadas** (`_fachadas`): las caras norte, sur, este y oeste de su caja, cada una con su área, su dirección hacia afuera y la reflectancia del color indicado en el campo `fachada` de la torre (por defecto `GRIS_CLARO`, 0,60). Se usan para la reflexión entre torres (paso 2).

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
- orienta la superficie interior al revés (flecha × −1). Esa dirección ya no se usa en ningún cálculo de luz; quedó del modelo anterior.

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
| Entrada del paso | [`cargar_hotel_data`, `src/io_datos.py` línea 73](../src/io_datos.py#L73) |
| Valores por defecto | [`_completar_defaults`, línea 57](../src/io_datos.py#L57) |
| Validar acabados | [`_validar_acabados`, línea 307](../src/io_datos.py#L307) |
| Perfiles de iluminación y clima | [línea 76](../src/io_datos.py#L76) |
| Bucle de torres, pisos y zonas | [línea 87](../src/io_datos.py#L87) |
| Habitación | [`_zona_habitacion`, línea 222](../src/io_datos.py#L222) y [`_room_center`, línea 265](../src/io_datos.py#L265) |
| Zona común | [`_zona_comun`, línea 240](../src/io_datos.py#L240) y [`_common_center`, línea 274](../src/io_datos.py#L274) |
| Fachadas de cada torre | [`_fachadas`, línea 282](../src/io_datos.py#L282) y [`class Fachada`, `src/modelo.py` línea 59](../src/modelo.py#L59) |
| Acabado de cada zona | [`_acabado`, línea 196](../src/io_datos.py#L196) |
| Índices por ID | [`Hotel.indexar`, `src/modelo.py` línea 219](../src/modelo.py#L219) |
| Luminarias | [línea 130](../src/io_datos.py#L130) |
| Huéspedes y asignaciones | [línea 148](../src/io_datos.py#L148) y [línea 174](../src/io_datos.py#L174) |
| Validación final | [`_validar`, línea 331](../src/io_datos.py#L331) |

### Resultado y costo del paso

Sale un `Hotel` con 127 zonas (104 habitaciones y 23 comunes), 154 ventanas, 127 superficies interiores, 8 fachadas (4 por torre), 127 luminarias y 78 huéspedes asignados.

**Complejidad: lineal, O(Z + V + G)**, con Z zonas, V ventanas y G huéspedes. Aunque el bucle del edificio tiene tres niveles (torre, piso, habitación), pasa una sola vez por cada habitación y hace con ella un trabajo fijo. Las búsquedas de acabado son en diccionario, en tiempo constante. Con los datos del hotel tarda milisegundos, así que este paso nunca es el cuello de botella.

---

## Paso 2. Preparar el espacio: Octree y grafo de influencia

**Fin:** organizar la geometría **una sola vez**, antes de recorrer el día, para que en cada media hora se puedan responder rápido dos preguntas:

- ¿La otra torre le tapa el sol a esta ventana? (sombras, paso 3)
- ¿Cuánta luz le devuelve la fachada de la otra torre a esta ventana? (reflexión exterior, paso 3)

Este paso **no calcula luz**. Construye dos herramientas: el **Octree**, que sirve para buscar cosas en el espacio, y el **grafo de influencia**, que guarda qué fachada le refleja luz a qué ventana de la otra torre y cuánta.

La reflexión **dentro** de cada cuarto no usa el grafo: se calcula en el paso 3 con la luz que entra y el color de las paredes del cuarto.

### Dónde está en el código

| Qué | Dónde |
|---|---|
| Se arma todo al crear el simulador | [`SimuladorUnificado.__init__`, `src/simulacion.py` líneas 26–28](../src/simulacion.py#L26) |
| Llenar el Octree con los objetos del hotel | [`_crear_octree`, `src/simulacion.py` línea 73](../src/simulacion.py#L73) |
| La estructura Octree | [`class Octree`, `src/octree.py` línea 24](../src/octree.py#L24) |
| Insertar y dividir | [`_insertar`, línea 34](../src/octree.py#L34); [`_dividir`, línea 53](../src/octree.py#L53); [`_hijo_contenedor`, línea 61](../src/octree.py#L61) |
| Consulta de rayo | [`consultar_rayo`, línea 71](../src/octree.py#L71) |
| Consulta de radio | [`consultar_radio`, línea 85](../src/octree.py#L85) |
| Construir el grafo | [`GrafoInfluencia.construir`, `src/influencia.py` línea 49](../src/influencia.py#L49) |
| Punto donde la ventana sale a la fachada | [`punto_en_fachada`, `src/influencia.py` línea 18](../src/influencia.py#L18) |
| Punto más cercano de una fachada | [`punto_mas_cercano`, `src/influencia.py` línea 26](../src/influencia.py#L26) |
| Revisar si algo tapa la línea | [`_visible`, `src/influencia.py` línea 89](../src/influencia.py#L89) |
| Uso del rayo para sombras (paso 3) | [`_sombreada`, `src/simulacion.py` línea 129](../src/simulacion.py#L129) |
| Uso del grafo en cada media hora (paso 3) | [`reflejada_para`, `src/influencia.py` línea 99](../src/influencia.py#L99) |

`GrafoInfluencia.construir` significa «el método `construir` de la clase `GrafoInfluencia`». Está en `src/influencia.py` y se llama desde `src/simulacion.py` línea 28.

### 2.1 Qué es el Octree y cómo se arma

**`src/octree.py` define la estructura** (cómo se guarda y cómo se consulta). **`_crear_octree` en `src/simulacion.py` la llena** con los objetos del hotel.

**La idea.** Todo el hotel cabe en una caja grande. Si una caja tiene muchos objetos, se parte en 8 cajas iguales (se corta a la mitad a lo ancho, a lo largo y a lo alto) y cada objeto baja a la caja pequeña donde cabe completo. Las cajas que vuelven a llenarse se parten otra vez. Queda un árbol: la raíz es la caja grande y cada nodo tiene 0 u 8 hijos.

**Cómo inserta (`_insertar`):**

1. Si el nodo ya tiene hijos, busca el hijo donde el objeto **cabe completo** (`_hijo_contenedor`) y baja ahí.
2. Si no cabe completo en ningún hijo, porque queda partido entre dos cajas, se queda en el nodo actual.
3. Si el nodo pasa de **16 objetos** y no ha llegado a **6 niveles**, se parte en 8 (`_dividir`) y reparte los objetos que caben en los hijos.

**Qué se mete (`_crear_octree`):** 418 objetos: las 2 torres, las 8 fachadas, las 154 ventanas (cada una como un cubito de 10 cm), las 127 superficies interiores y las 127 luminarias. La caja raíz se calcula para que quepan todos, con 2 m de margen: x de −2 a 91 m, y de −2 a 45 m, z de −2 a 20 m.

**Cómo queda en el escenario base (medido):**

| Nivel | Nodos |
|---|---|
| 0 (raíz) | 1 |
| 1 | 8 |
| 2 | 56 |
| 3 | 32 |

- La raíz guarda 52 objetos: las **2 torres** y las **8 fachadas** (son enormes y cruzan varias cajas, así que nunca bajan) y 42 objetos que quedaron justo sobre una línea de corte.
- Ejemplo: la ventana `TP-H-101-V1` bajó 2 niveles y quedó en una caja de x −2 a 21,25 m, y −2 a 9,75 m, z −2 a 3,5 m que comparte con solo otros 2 objetos.

### 2.2 Las dos consultas del Octree

Las dos consultas recorren el árbol desde la raíz y **descartan cajas completas** sin mirar lo que tienen adentro. Esa es la ganancia.

**`consultar_rayo` (rayo): «¿qué cosas cruza esta línea?»**

Recibe un punto de partida y una dirección. En cada nodo revisa si la línea atraviesa la caja; si no, descarta ese nodo y todo lo que tiene debajo. Se usa para:

- **Sombras** (`_sombreada`, paso 3): una línea desde la ventana hacia el sol. Si cruza **la otra torre**, el sol directo no llega. Ejemplo medido: a las 7:00 el sol sale por el este; la ventana `TP-REC-03-V1` (planta baja de TP, mirando al este) lanza la línea y esta cruza `TG`. Esa ventana queda en sombra a esa hora.
- **Visibilidad para el grafo** (`_visible`): una línea de la fachada a la ventana, para revisar que nada se interponga.

**`consultar_radio` (radio): «¿qué cosas hay cerca de este punto?»**

Es otra pregunta, independiente del rayo. Recibe un punto y una distancia y devuelve los objetos a esa distancia o menos (midiendo hasta el borde de su caja). Se usa **solo para construir el grafo**: a cada ventana se le piden las fachadas a 18 m o menos.

### 2.3 Cómo se construye el grafo de influencia

**La idea.** El sol ilumina la fachada de una torre. Parte de esa luz rebota y entra por las ventanas de **la otra torre** que la tienen de frente. El grafo guarda esas relaciones como flechas **fachada → ventana**, y cada flecha (arista) tiene un **peso**: la fracción de la luz de la fachada que llega a esa ventana.

Nunca hay flechas entre recintos de la misma torre: dentro de un edificio la luz no atraviesa paredes.

**Qué hace `construir`, para cada una de las 154 ventanas:**

1. **Punto de salida** (`punto_en_fachada`). Las ventanas del modelo están cerca del centro de su cuarto, dentro de la torre. Para la reflexión exterior se lleva cada ventana hasta la cara de su torre hacia la que mira. Ejemplo: `TP-H-101-V1` está en x = 11,2 m y mira al este; su punto de salida es x = 32 m, la fachada este de TP.
2. **Candidatas** (`consultar_radio`). Fachadas a 18 m o menos del punto de salida. Las de su propia torre se descartan.
3. **Distancia** al punto más cercano de la fachada (`punto_mas_cercano`). Se descarta si es 0 o mayor que 18 m.
4. **¿Se miran?** La ventana debe mirar hacia la fachada y la fachada hacia la ventana (`cos_ventana` y `cos_fachada` mayores que 0).
5. **¿Algo se interpone?** `_visible` con `consultar_rayo`.
6. **Peso:**

   ```
   vista = área de la fachada / (π × distancia² + área de la fachada)
   peso  = reflectancia de la fachada × cos_fachada × cos_ventana × vista
   ```

   `vista` aproxima qué tanto del campo de visión de la ventana ocupa la fachada: una fachada grande y cercana ocupa mucho. Se guarda la arista si el peso pasa de 0,0001.
7. **Obstrucción del cielo.** Si la fachada de enfrente ocupa parte de la vista, esa parte del cielo queda tapada. Se guarda `obstruccion = cos_ventana × vista` (como máximo 1). En el paso 3 la luz difusa del cielo de esa ventana se multiplica por `1 − obstruccion`.

**Ejemplo real: `TP-H-101-V1`** (TP, piso 1, ventana al este, frente a TG):

| Dato | Valor |
|---|---|
| Punto de salida (fachada este de TP) | x = 32 m, y = 5,2 m, z = 1,5 m |
| Fachadas candidatas a 18 m | `TP-F-ESTE` y `TP-F-SUR` (propias, se descartan), `TG-F-OESTE` y `TG-F-SUR` |
| Fachada que la mira | `TG-F-OESTE` (área 43 × 18 = 774 m², gris claro ρ = 0,60) |
| Distancia | 13,0 m (la separación entre torres) |
| `cos_ventana`, `cos_fachada` | 1,0 y 1,0 (se miran de frente) |
| `vista` | 774 / (π × 13² + 774) = 0,593 |
| Peso | 0,60 × 1 × 1 × 0,593 = 0,356 |
| Obstrucción del cielo | 0,593 (más de la mitad de su cielo la tapa TG) |

**Dos índices de las mismas aristas** (`agregar_arista`):

- `adyacencias`: por fachada → «¿a qué ventanas ilumina esta fachada?»
- `entrantes`: por ventana → «¿qué fachadas le llegan a esta ventana?»

### 2.4 Qué guarda el grafo y cómo se usa

| Parte | Qué es |
|---|---|
| Nodos de origen | Las 8 fachadas (4 por torre) |
| Nodos de destino | Las ventanas |
| Arista | «Esta fachada le devuelve luz a esta ventana de la otra torre» |
| Peso | Fracción de la luz de la fachada que llega a la ventana |

En el escenario base hay 46 aristas:

| Fachada | Ventanas que ilumina | Peso de cada arista |
|---|---|---|
| `TP-F-ESTE` (cara este de TP) | 24 ventanas de TG que miran al oeste | 0,249 |
| `TG-F-OESTE` (cara oeste de TG) | 16 ventanas de TP que miran al este | 0,356 |
| `TP-F-NORTE` (cara norte de TP) | 6 ventanas de recreaciones de TG | 0,073 |

Las demás fachadas no tienen ventanas de la otra torre de frente. La fachada oeste de TG es más grande que la este de TP (774 m² contra 376 m²), por eso sus aristas pesan más.

**Uso en cada media hora (paso 3).** La luz que recibe una fachada depende de la hora: `E_base × (qué tan de frente le da el sol × f_directa + f_difusa)`. `reflejada_para` suma, para cada ventana, `luz de la fachada × peso`, y esa luz se multiplica por la transmitancia del vidrio al entrar.

Ejemplo: a las 12:00 `TG-F-OESTE` recibe 290,6 lux. A `TP-H-101` le entran 290,6 × 0,356 × 0,82 ≈ 84,8 lux reflejados desde la otra torre. Esa misma ventana recibe solo 97,0 lux de luz natural directa y difusa, porque TG le tapa más de la mitad del cielo. Para las ventanas que tienen la otra torre enfrente, la luz reflejada exterior es tan importante como la natural.

### Resultado y costo del paso

| Medida (escenario base) | Valor |
|---|---|
| Pares fachada–ventana si se comparara todo contra todo | 1.232 (8 × 154) |
| Fachadas candidatas de la otra torre que entrega `consultar_radio` | 68 |
| Nodos del Octree visitados para obtenerlas | 7.834 |
| Aristas del grafo | 46 |
| Ventanas con parte del cielo tapada por la otra torre | 40 |

**Por qué se descartan las candidatas:**

| Motivo | Fachadas |
|---|---|
| Son de la propia torre | 287 |
| La ventana y la fachada no se miran | 22 |
| Se convierten en arista | 46 |

**Complejidad.**

- **Construir el Octree:** O(B log B) en el caso típico, con B objetos: cada objeto baja unos pocos niveles.
- **Construir el grafo:** con el Octree, O(V × (log B + k)), con V ventanas y k candidatas por ventana, más una consulta de rayo por cada candidata que pasa los filtros. Sin el Octree sería O(V × F), cada ventana contra cada fachada. Con solo 8 fachadas la diferencia es pequeña; el Octree sirve sobre todo para que el método no dependa del número de fachadas y para las sombras.
- **Usar el grafo en cada media hora:** O(V + E), lineal en ventanas y aristas.

Las dos estructuras se arman una vez y sirven para los 48 pasos del día.

### Ideas clave del paso

- **La partición del Octree solo sirve para buscar más rápido; no cambia ningún resultado.** Es como ordenar una biblioteca por estantes: una búsqueda descarta estantes completos sin mirar sus libros.
- **Un objeto que queda entre dos cajas se queda en la caja de arriba.** No se pierde ni se duplica: lo revisa toda búsqueda que pase por esa caja. Por eso las torres y las fachadas, que son grandes, quedan en la raíz.
- **El rayo responde sí o no:** ¿la línea choca con la otra torre? Para las sombras, si choca no llega luz directa, pero la ventana sigue recibiendo la luz difusa del cielo que no está tapado y la luz reflejada.
- **El radio responde qué fachadas están cerca de una ventana**, para no comparar cada ventana con todas.
- **Cada archivo tiene un papel distinto:**
  - `octree.py` es la herramienta de búsqueda.
  - `influencia.py` guarda qué fachada le refleja luz a qué ventana y cuánta, y cuánto cielo le tapa a cada ventana.
  - `simulacion.py` crea las dos estructuras y las usa en cada paso.
- **El grafo existe para no repetir trabajo.** Como la geometría no cambia durante el día, los pesos se calculan una vez; en cada media hora solo se multiplica la luz de las fachadas por esos pesos.
- **Limitaciones:** las fachadas son superficies opacas de un solo color, y lo que el vidrio de una ventana refleja hacia afuera se pierde (no ilumina la otra torre); la reflexión exterior es de un solo rebote; las ventanas están cerca del centro de su cuarto y para la reflexión exterior se usa su punto en la fachada.

**Historia del cambio.** Una versión anterior del grafo unía la superficie interior de cada cuarto con ventanas de otros cuartos, incluso dentro de la misma torre, como si la luz atravesara las paredes del edificio. Se reemplazó por la reflexión entre fachadas de las dos torres, y la luz que rebota dentro de cada cuarto pasó a calcularse aparte (paso 3).

---

## Paso 3. Simular el día en 48 pasos de media hora

**Fin:** calcular, para cada una de las 127 zonas y en cada media hora del día, cuánta luz tiene y si esa luz está bien, falta o sobra. Es el corazón del sistema: los pasos 4 a 6 solo resumen lo que este paso produce.

**Entrada:** el hotel del paso 1 y las dos herramientas del paso 2 (Octree y grafo).
**Salida:** 6.096 resultados (127 zonas × 48 pasos), cada uno con hora, periodo, modo, luz natural, luz reflejada, luz artificial, luz total, potencia asignada y estado.

### Dónde está en el código

| Qué | Dónde |
|---|---|
| Bucle de las 48 medias horas | [`SimuladorUnificado.ejecutar`, `src/simulacion.py` línea 30](../src/simulacion.py#L30) |
| Luz base y dirección del sol | [`luz_base`, `src/clima.py` línea 9](../src/clima.py#L9); [`direccion_solar`, línea 16](../src/clima.py#L16); [`periodo`, línea 21](../src/clima.py#L21); [`_cielo`, `src/simulacion.py` línea 101](../src/simulacion.py#L101) |
| Factor del clima | [`PerfilClimatico.factor_luz`, `src/modelo.py` línea 95](../src/modelo.py#L95) |
| Luz natural por ventana | [`_aportes_naturales`, `src/simulacion.py` línea 106](../src/simulacion.py#L106) y [`_calcular_naturales`, línea 122](../src/simulacion.py#L122) |
| Sombra | [`_sombreada`, línea 129](../src/simulacion.py#L129) |
| Snell y Fresnel | [`factor_angular_vidrio`, `src/geometria.py` línea 121](../src/geometria.py#L121) |
| Luz que recibe cada fachada | [`luz_fachadas`, `src/simulacion.py` línea 133](../src/simulacion.py#L133) |
| Luz reflejada (exterior + interior) | [`_calcular_reflejadas`, línea 140](../src/simulacion.py#L140); [`area_interior`, línea 164](../src/simulacion.py#L164); [`reflexion_interior`, línea 169](../src/simulacion.py#L169) |
| Modo por horario | [`horario_modo`, `src/balance.py` línea 26](../src/balance.py#L26); [`PerfilIluminacion.para_modo`, `src/modelo.py` línea 78](../src/modelo.py#L78) |
| Balance del generador | [`balancear`, `src/balance.py` línea 52](../src/balance.py#L52); [`_categoria`, línea 38](../src/balance.py#L38); [`_demanda`, línea 114](../src/balance.py#L114); [`_asignar`, línea 124](../src/balance.py#L124) |
| Luz artificial | [`_luz_artificial`, `src/simulacion.py` línea 153](../src/simulacion.py#L153) |
| Clasificar el resultado | [`_estado`, `src/simulacion.py` línea 65](../src/simulacion.py#L65); [`clasificar`, `src/evaluacion.py` línea 25](../src/evaluacion.py#L25) |
| Guardar en el índice por hora | [`IndiceTemporal.insertar`, `src/temporal.py` línea 24](../src/temporal.py#L24) |

### 3.0 La forma del bucle

```
para hora = 0:00, 0:30, 1:00, ..., 23:30:
    1. luz natural de cada ventana y de cada zona
    2. luz reflejada de cada zona (exterior + interior)
    3. balance: modo de cada zona y reparto del generador
    4. para cada zona: luz artificial, luz total, estado; guardar el resultado
```

Los cuatro pasos se repiten 48 veces. La geometría no cambia; lo que cambia en cada vuelta es la hora, y con ella el sol y los horarios.

### 3.1 El cielo de esa hora

`_cielo` reúne cuatro números que valen para todo el hotel en esa media hora:

- **Luz base** (`luz_base`): `E_base = 900 × curva(hora) × factor_luz`. La curva es un seno: vale 0 a las 6:00, sube a 1 a las 12:00 y vuelve a 0 a las 18:00. Fuera de 6:00–18:00 vale 0. Con nubes parciales, `factor_luz` = 4,863 / 7,063 = 0,689.
- **Dirección del sol** (`direccion_solar`): una flecha que gira de este a oeste durante el día.
- **Reparto por nubosidad** (c = 0,709 en nubes parciales): luz directa `f_directa = max(0,10; 1 − c)` = 0,291 y luz difusa `f_difusa = 0,15 + 0,45 × c` = 0,469.
- **Periodo** (`periodo`): NOCHE antes de las 6:00 y desde las 18:00; TRANSICION de 6:00 a 7:00 y de 17:00 a 18:00; DIA el resto.

| Hora | Periodo | Luz base |
|---|---|---|
| 06:00 | TRANSICION | 0 |
| 07:00 | DIA | 160,4 lux |
| 09:00 | DIA | 438,2 lux |
| 12:00 | DIA | 619,7 lux |
| 15:00 | DIA | 438,2 lux |
| 17:30 | TRANSICION | 80,9 lux |
| 18:00 | NOCHE | 0 |

### 3.2 Luz natural por ventana

Para cada ventana (`_aportes_naturales`):

1. **¿Le da el sol de frente?** `coseno = flecha de la ventana · dirección del sol` (0 si el sol está de lado o detrás).
2. **¿La tapa la otra torre?** `_sombreada` lanza un rayo hacia el sol con el Octree (paso 2). Si choca con la otra torre, `coseno = 0`.
3. **¿Cuánto deja pasar el vidrio según el ángulo?** `factor_angular_vidrio` aplica Snell y Fresnel: de frente pasa todo lo que dice el catálogo; muy de lado pasa menos.
4. **Suma directa + difusa:**

   ```
   luz de la ventana = E_base × VLT × (coseno × factor_angular × f_directa + f_difusa × (1 − obstrucción))
   ```

   `VLT` es la transmitancia del vidrio (0,82 el claro) y `obstrucción` es la parte del cielo que tapa la otra torre (paso 2).

La luz natural de la zona es el promedio de sus ventanas (`_calcular_naturales`). Una zona sin ventanas, como el parqueadero, tiene luz natural 0.

### 3.3 Luz reflejada

`_calcular_reflejadas` suma dos partes por zona:

- **Exterior:** para cada ventana, `luz de la fachada de enfrente × peso de la arista × VLT` (paso 2). La luz de cada fachada es `E_base × (qué tan de frente le da el sol × f_directa + f_difusa)` (`luz_fachadas`).
- **Interior** (`reflexion_interior`): toda la luz que entró (natural + exterior, por el área de cada ventana) rebota en las paredes del cuarto:

  ```
  reflexión interior = flujo que entra × ρ / (área interior × (1 − ρ))
  ```

  `ρ` es la reflectancia del color de la pared y el área interior es piso + techo + 4 paredes de 3 m (106,8 m² en una habitación de 24 m²). Con pared blanca (ρ = 0,80), `ρ / (1 − ρ)` = 4; con pared oscura (0,25), 0,33. Por eso el color de la pared importa.

De noche las dos partes valen 0.

### 3.4 Balance del generador

`balancear` decide cuántos vatios recibe cada zona en esa media hora. Lo hace en este orden:

**a) Modo de cada zona** (`horario_modo`): ACTIVA dentro de su horario, CERRADA en su franja de cierre, REDUCIDA el resto. El parqueadero siempre está ACTIVA. En modo REDUCIDA los niveles se multiplican por 0,30 (`para_modo`): una habitación pasa de pedir 100 / 200 / 300 lux a pedir 30 / 60 / 90.

**b) Cuánto le falta a cada zona** (`_demanda`): la luz artificial convierte vatios en lux con el método de lúmenes:

```
lux por vatio = eficacia × CU × MF / área          (habitación: 100 × 0,70 × 0,80 / 24 = 2,33 lux/W)
vatios que faltan = max(0, (nivel pedido − luz natural − luz reflejada) / lux por vatio)
```

Se calculan tres demandas: para llegar al nivel de emergencia (10 lux), al mínimo y al objetivo. Ninguna puede pasar de la potencia de la luminaria (habitación 72 W, que da como máximo 168 lux).

**c) Prioridad** de cada zona: `prioridad de la actividad × (1 + 0,10 × (piso − 1)) × 1,4 si es una habitación ocupada`.

**d) Tres repartos**, cada uno hasta agotar los 22 kW (`_asignar` nunca entrega más de lo que queda):

1. **Emergencia:** a todas las zonas abiertas, lo que necesitan para llegar a 10 lux. Las zonas CERRADA no reciben nada.
2. **Mínimos**, en este orden (`_categoria`): primero el parqueadero (seguridad), luego las habitaciones ocupadas, luego el resto; dentro de cada grupo, por prioridad. La zona que no alcanza su mínimo porque el generador se agotó queda en **EMERGENCIA**.
3. **Objetivos**, por prioridad, con una cola `heapq`. Las zonas en EMERGENCIA no participan.

### 3.5 Luz artificial, total y estado

Para cada zona (`ejecutar`):

- **Luz artificial** (`_luz_artificial`): `vatios asignados × lux por vatio`.
- **Luz total** = natural + reflejada + artificial.
- **Estado** (`_estado` y `clasificar`): se compara la luz total con el mínimo y el máximo del modo de esa hora.

  | Estado | Regla |
  |---|---|
  | DEFICIT_SEVERO | menos de la mitad del mínimo |
  | DEFICIT_LEVE | entre la mitad del mínimo y el mínimo |
  | CONFORTABLE | entre el mínimo y el máximo |
  | EXCESO_LEVE | hasta 1,25 veces el máximo |
  | EXCESO_SEVERO | más de 1,25 veces el máximo |
  | DATOS_INSUFICIENTES | zona CERRADA o con datos incompletos |

  Una zona en EMERGENCIA se compara con el mínimo de su modo de horario, así que ese paso cuenta como déficit.
- El resultado se guarda en la zona y se inserta en el árbol rojo-negro (paso 4).

**Análisis sin balance.** La pestaña «Diagnóstico» de la interfaz ejecuta el mismo bucle sin el paso 3.4: no asigna energía y marca la noche como DATOS_INSUFICIENTES. Sirve para ver cómo está el hotel solo con luz natural.

### 3.6 Un día de cuatro zonas (escenario base, medido)

**`TP-H-102`** (habitación ocupada, ventana al norte, sin torre enfrente):

| Hora | Modo | Natural | Reflejada | Artificial | Total | Vatios | Estado |
|---|---|---|---|---|---|---|---|
| 02:00 | REDUCIDA | 0 | 0 | 60,0 | 60,0 | 25,7 | CONFORTABLE |
| 06:00 | ACTIVA | 0 | 0 | 168,0 | 168,0 | 72,0 | CONFORTABLE |
| 09:00 | ACTIVA | 225,6 | 16,9 | 0 | 242,5 | 0 | CONFORTABLE |
| 12:00 | ACTIVA | 358,7 | 26,9 | 0 | 385,6 | 0 | EXCESO_SEVERO |
| 19:00 | ACTIVA | 0 | 0 | 168,0 | 168,0 | 72,0 | CONFORTABLE |
| 23:00 | REDUCIDA | 0 | 0 | 60,0 | 60,0 | 25,7 | CONFORTABLE |

De día el sol basta y el generador no le da nada. A mediodía la luz pasa de 375 lux (1,25 × 300) y queda en exceso severo: es una de las 26 zonas casi habitables por exceso solar.

**`TP-H-101`** (habitación ocupada, ventana al este, con la Torre Grande enfrente):

| Hora | Natural | Reflejada | Artificial | Total | Vatios |
|---|---|---|---|---|---|
| 09:00 | 125,6 | 73,9 | 0,5 | 200,0 | 0,2 |
| 12:00 | 97,0 | 98,4 | 4,6 | 200,0 | 2,0 |
| 15:00 | 68,6 | 92,8 | 38,7 | 200,0 | 16,6 |

TG le tapa más de la mitad del cielo, pero le devuelve casi tanta luz como la que le quita. El generador completa justo hasta el objetivo (200 lux).

**`TP-COC-01`** (cocina): CERRADA a las 02:00 y 23:00 (0 vatios, DATOS_INSUFICIENTES); de día recibe entre 91 y 140 W para completar sus 400 lux de objetivo; de noche usa sus 200 W completos y llega a 320 lux.

**`TP-PAR-01`** (parqueadero, sin ventanas): recibe sus 720 W durante las 24 horas y queda en 89,6 lux, por encima de su mínimo de 50.

**Potencia total del generador a lo largo del día:**

| Hora | 00:00 | 06:00 | 09:00 | 12:00 | 15:00 | 17:30 | 18:00 | 22:00 |
|---|---|---|---|---|---|---|---|---|
| Vatios | 4.834 | 11.648 | 5.649 | 3.893 | 5.743 | 15.275 | 15.934 | 9.870 |

El pico, 15.934 W, se da entre las 18:00 y las 22:00: ya no hay sol y todo está en modo activo. Al mediodía el generador trabaja menos porque el sol hace casi todo.

Estados de los 6.096 resultados: 5.602 confortables, 156 en exceso leve, 78 en exceso severo y 260 cerrados. No hay déficit: los 22 kW alcanzan.

### Resultado y costo del paso

**Complejidad por media hora:**

- Luz natural: un rayo por ventana, O(V × (log B + k)).
- Luz reflejada: O(V + E).
- Balance: construir y ordenar las demandas con `heapq` cuesta O(Z log Z). Pero `_asignar` suma todo lo ya asignado en cada llamada, y eso lo vuelve O(Z²) en la implementación actual (ver «Observaciones»).
- Clasificar y guardar: O(Z), más O(log R) por inserción en el rojo-negro.

En total, T = 48 veces lo anterior. Con 127 zonas el día completo se simula en menos de un segundo.

### Datos que conviene saber

- **La luminaria de una habitación no alcanza su objetivo de noche.** 72 W dan como máximo 168 lux y el objetivo es 200. Como 168 está entre el mínimo (100) y el máximo (300), el estado igual es CONFORTABLE.
- **El parqueadero tampoco alcanza su objetivo** (89,6 lux contra 100), pero sí su mínimo.
- **Al mediodía el sol puede sobrar** en las habitaciones que miran al norte: el sistema no apaga la luz natural ni corre cortinas, solo lo reporta como exceso.

### Observaciones pendientes

- **Recorrido del sol.** `direccion_solar` mueve el sol de este a oeste por el lado norte, con una altura fija de unos 35°. En Bogotá en febrero (el perfil base) el sol de mediodía está alto, a unos 72° (latitud 4,7° N, declinación de unos −13°), y hacia el sur. Esto decide qué fachadas reciben sol directo y explica por qué las habitaciones con ventana al norte quedan en exceso. Es una simplificación del modelo que cambia resultados si se corrige.
- **Costo del balance.** `_asignar` recalcula la suma de lo ya asignado en cada llamada. El resultado es correcto, pero el costo real del balance es O(Z²) por media hora y no O(Z log Z) como dicen los documentos. Se arregla llevando un total acumulado.
