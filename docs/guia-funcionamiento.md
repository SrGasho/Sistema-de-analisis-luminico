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

`_validar_acabados` comprueba que cada actividad y cada recinto personalizado usen una pared y un vidrio que existan, y una orientación válida (norte, sur, este u oeste). También revisa que `luminaria_w`, si un recinto lo trae, sea un número mayor o igual a 0. Si hay un error, como escribir `"BLANKO"`, la carga se detiene con un mensaje claro.

### 1.3 Crear los perfiles

- **Iluminación:** un perfil por actividad, con mínimo, objetivo, máximo y prioridad.
- **Clima:** cada perfil recibe la radiación de cielo despejado de referencia (7,063 kWh/m²/día). Con ella calcula su `factor_luz` = radiación / referencia, que es la fracción de luz que deja pasar ese clima. Cada perfil trae además `dia_del_anio`, el día que representa, porque la posición del sol cambia con la fecha (paso 3):

  | Perfil | `dia_del_anio` | Fecha | Radiación (kWh/m²/día) | `factor_luz` |
  |---|---|---|---|---|
  | `NUBES_PARCIALES` (base) | 46 | 15 de febrero | 4,863 | 0,689 |
  | `NUBLADO` | 135 | 15 de mayo | 4,477 | 0,634 |
  | `LLUVIOSO` | 105 | 15 de abril | 4,454 | 0,631 |
  | `CIELO_DESPEJADO` | 46 | 15 de febrero | 7,063 | 1,000 |

  Si un perfil no trae `dia_del_anio`, se usa 46.
- **Ubicación y suelo:** `parametros_evaluacion.ubicacion.latitud` (4,711° N, Bogotá) y `parametros_evaluacion.luz.reflectancia_suelo` (0,20) no se guardan en un objeto propio. Los lee el simulador al crearse ([`src/simulacion.py` líneas 23–24](../src/simulacion.py#L23)) y los usa para el sol y la luz que rebota en el suelo (paso 3).

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

Más adelante, al calcular la luz, la flecha de la ventana se compara con la dirección del sol. Si apuntan parecido, el sol pega de frente y entra mucha luz directa. Si quedan de lado, entra poca, y si el sol está detrás, solo entra la luz difusa del cielo y la que rebota en el suelo. La misma comparación decide si una pared y una ventana "se miran" para que haya reflexión.

### 1.5 Indexar

`hotel.indexar()` arma diccionarios por identificador (`hotel.zonas`, `hotel.habitaciones`) para encontrar cualquier zona de inmediato sin recorrer todo el árbol.

### 1.6 Luminarias

Cada zona recibe una `FuenteIluminacion` con la potencia, la eficacia, el CU y el MF de su actividad. La potencia de la actividad (72 W en una habitación) se puede cambiar por recinto con `luminaria_w` en `zonas_personalizadas`. Con `luminaria_w = 0` la luminaria está dañada: la zona no recibe luz artificial y de noche queda a oscuras. Así se prueba la reasignación de huéspedes en el caso `luminarias_danadas`. Este campo no se edita desde la interfaz; se escribe en el JSON.

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
| Validar acabados y `luminaria_w` | [`_validar_acabados`, línea 308](../src/io_datos.py#L308); `luminaria_w` en [línea 330](../src/io_datos.py#L330) |
| Perfiles de iluminación y clima | [línea 76](../src/io_datos.py#L76); `dia_del_anio` en [línea 84](../src/io_datos.py#L84) y [`class PerfilClimatico`, `src/modelo.py` línea 87](../src/modelo.py#L87) |
| Bucle de torres, pisos y zonas | [línea 87](../src/io_datos.py#L87) |
| Habitación | [`_zona_habitacion`, línea 223](../src/io_datos.py#L223) y [`_room_center`, línea 266](../src/io_datos.py#L266) |
| Zona común | [`_zona_comun`, línea 241](../src/io_datos.py#L241) y [`_common_center`, línea 275](../src/io_datos.py#L275) |
| Fachadas de cada torre | [`_fachadas`, línea 283](../src/io_datos.py#L283) y [`class Fachada`, `src/modelo.py` línea 59](../src/modelo.py#L59) |
| Acabado de cada zona | [`_acabado`, línea 197](../src/io_datos.py#L197) |
| Índices por ID | [`Hotel.indexar`, `src/modelo.py` línea 220](../src/modelo.py#L220) |
| Luminarias | [línea 130](../src/io_datos.py#L130); potencia por recinto en [línea 138](../src/io_datos.py#L138) |
| Huéspedes y asignaciones | [línea 149](../src/io_datos.py#L149) y [línea 175](../src/io_datos.py#L175) |
| Validación final | [`_validar`, línea 336](../src/io_datos.py#L336) |

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
| Se arma todo al crear el simulador | [`SimuladorUnificado.__init__`, `src/simulacion.py` líneas 28–30](../src/simulacion.py#L28) |
| Llenar el Octree con los objetos del hotel | [`_crear_octree`, `src/simulacion.py` línea 75](../src/simulacion.py#L75) |
| La estructura Octree | [`class Octree`, `src/octree.py` línea 24](../src/octree.py#L24) |
| Insertar y dividir | [`_insertar`, línea 34](../src/octree.py#L34); [`_dividir`, línea 53](../src/octree.py#L53); [`_hijo_contenedor`, línea 61](../src/octree.py#L61) |
| Consulta de rayo | [`consultar_rayo`, línea 71](../src/octree.py#L71) |
| Consulta de radio | [`consultar_radio`, línea 85](../src/octree.py#L85) |
| Construir el grafo | [`GrafoInfluencia.construir`, `src/influencia.py` línea 49](../src/influencia.py#L49) |
| Punto donde la ventana sale a la fachada | [`punto_en_fachada`, `src/influencia.py` línea 18](../src/influencia.py#L18) |
| Punto más cercano de una fachada | [`punto_mas_cercano`, `src/influencia.py` línea 26](../src/influencia.py#L26) |
| Revisar si algo tapa la línea | [`_visible`, `src/influencia.py` línea 89](../src/influencia.py#L89) |
| Uso del rayo para sombras (paso 3) | [`_sombreada`, `src/simulacion.py` línea 130](../src/simulacion.py#L130) |
| Uso del grafo en cada media hora (paso 3) | [`reflejada_para`, `src/influencia.py` línea 99](../src/influencia.py#L99) |

`GrafoInfluencia.construir` significa «el método `construir` de la clase `GrafoInfluencia`». Está en `src/influencia.py` y se llama desde `src/simulacion.py` línea 30.

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

- **Sombras** (`_sombreada`, paso 3): una línea desde la ventana hacia el sol. Si cruza **la otra torre**, el sol directo no llega. Ejemplo medido: a las 7:00 el sol está bajo (13,4° de altura) hacia el este-sureste; la ventana `TP-COC-01-V1` (cocina en la planta baja de TP, mirando al este) lanza la línea y esta cruza `TG`. Esa ventana queda en sombra a esa hora. A las 7:00 quedan en sombra 19 de las 72 ventanas que tienen el sol delante; a las 9:00, con el sol a 41,8°, ninguna, porque el rayo pasa por encima de TG (18 m de alto).
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

**Uso en cada media hora (paso 3).** La luz que recibe una fachada depende de la hora: es la luz directa del sol sobre esa cara vertical más la difusa del cielo y del suelo (fórmulas en el paso 3.2). `reflejada_para` suma, para cada ventana, `luz de la fachada × peso`, y esa luz se multiplica por la transmitancia del vidrio al entrar.

Ejemplo: a las 12:00 el sol está casi encima y algo al sur, así que no le pega a la cara oeste de TG; `TG-F-OESTE` recibe solo luz difusa, 190,0 lux. A `TP-H-101` le entran 190,0 × 0,356 × 0,82 ≈ 55,4 lux reflejados desde la otra torre. Esa misma ventana recibe 92,0 lux de luz natural, porque TG le tapa más de la mitad del cielo. A las 15:00, cuando el sol ya pega en la cara oeste de TG (370,0 lux), la reflexión exterior sube a 370,0 × 0,356 × 0,82 ≈ 108 lux y supera la luz natural de la ventana (64,6 lux). Para las ventanas que tienen la otra torre enfrente, la luz reflejada exterior pesa tanto como la natural.

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
| Bucle de las 48 medias horas | [`SimuladorUnificado.ejecutar`, `src/simulacion.py` línea 32](../src/simulacion.py#L32) |
| Estado del cielo en esa media hora | [`class Cielo`, `src/clima.py` línea 16](../src/clima.py#L16); [`cielo`, línea 81](../src/clima.py#L81); [`_cielo`, `src/simulacion.py` línea 103](../src/simulacion.py#L103) |
| Posición del sol | [`declinacion_solar`, `src/clima.py` línea 33](../src/clima.py#L33); [`direccion_solar`, línea 38](../src/clima.py#L38) |
| Luz global horizontal | [`luz_base`, `src/clima.py` línea 73](../src/clima.py#L73); [`PerfilClimatico.factor_luz`, `src/modelo.py` línea 96](../src/modelo.py#L96) |
| Fracción difusa | [`radiacion_extraterrestre_diaria`, `src/clima.py` línea 50](../src/clima.py#L50); [`fraccion_difusa_diaria`, línea 61](../src/clima.py#L61) |
| Periodo del día | [`periodo`, `src/clima.py` línea 107](../src/clima.py#L107) |
| Luz natural por ventana | [`_aportes_naturales`, `src/simulacion.py` línea 107](../src/simulacion.py#L107) y [`_calcular_naturales`, línea 123](../src/simulacion.py#L123) |
| Luz sobre una superficie vertical | [`coseno_incidencia`, `src/clima.py` línea 91](../src/clima.py#L91); [`directa_en_vertical`, línea 95](../src/clima.py#L95); [`difusa_en_vertical`, línea 102](../src/clima.py#L102) |
| Sombra | [`_sombreada`, `src/simulacion.py` línea 130](../src/simulacion.py#L130) |
| Snell y Fresnel | [`factor_angular_vidrio`, `src/geometria.py` línea 121](../src/geometria.py#L121) |
| Luz que recibe cada fachada | [`luz_fachadas`, `src/simulacion.py` línea 134](../src/simulacion.py#L134) |
| Luz reflejada (exterior + interior) | [`_calcular_reflejadas`, línea 141](../src/simulacion.py#L141); [`area_interior`, línea 165](../src/simulacion.py#L165); [`reflexion_interior`, línea 170](../src/simulacion.py#L170) |
| Modo por horario | [`horario_modo`, `src/balance.py` línea 26](../src/balance.py#L26); [`PerfilIluminacion.para_modo`, `src/modelo.py` línea 78](../src/modelo.py#L78) |
| Balance del generador | [`balancear`, `src/balance.py` línea 52](../src/balance.py#L52); [`_categoria`, línea 38](../src/balance.py#L38); [`_demanda`, línea 115](../src/balance.py#L115); [`Reparto`, línea 125](../src/balance.py#L125) |
| Luz artificial | [`_luz_artificial`, `src/simulacion.py` línea 154](../src/simulacion.py#L154) |
| Clasificar el resultado | [`_estado`, `src/simulacion.py` línea 67](../src/simulacion.py#L67); [`clasificar`, `src/evaluacion.py` línea 25](../src/evaluacion.py#L25) |
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

`_cielo` arma un objeto `Cielo` con cuatro datos que valen para todo el hotel en esa media hora: la luz global sobre el suelo (`G`), qué parte de ella es difusa (`kd`), la dirección del sol y la reflectancia del suelo. Las fórmulas y sus fuentes están en la sección «Fuentes y fórmulas» del README.

**a) Dónde está el sol** (`declinacion_solar` y `direccion_solar`). Se usa la geometría solar real de Bogotá, con tres datos:

- **Latitud** φ = 4,711° N (`ubicacion.latitud`).
- **Declinación** δ, la latitud a la que el sol queda justo encima ese día (fórmula de Cooper): `δ = 23,45° × sen(360° × (284 + n) / 365)`, con n = `dia_del_anio`. El 15 de febrero (n = 46) vale −13,3°: el sol va por el sur de Bogotá. El 15 de abril vale +9,4° y el 15 de mayo +18,8°: el sol va por el norte.
- **Ángulo horario** `ω = 15° × (hora − 12)`: el sol avanza 15° por hora y ω = 0 al mediodía.

Con ellos sale una flecha de largo 1 hacia el sol, en los mismos ejes de las ventanas (x este, y norte, z arriba):

```
x = −cos δ × sen ω
y =  sen δ × cos φ − cos δ × sen φ × cos ω
z =  sen δ × sen φ + cos δ × cos φ × cos ω      (z = seno de la altura del sol)
```

La hora del modelo es hora solar: 12:00 es el momento en que el sol está más alto. No se corrige a la hora del reloj.

**b) Cuánta luz llega al suelo** (`luz_base`):

```
G = 900 × factor_luz × max(0, sen(altura del sol))       entre 6:00 y 18:00; 0 fuera de esa franja
```

900 es la luz de referencia en lux con el sol en el cenit y cielo despejado. `factor_luz` = 4,863 / 7,063 = 0,689 con nubes parciales (paso 1.3). Con el sol bajo, la luz se reparte en más suelo y `G` baja; por eso la curva sigue el seno de la altura.

**c) Qué parte es difusa** (`radiacion_extraterrestre_diaria` y `fraccion_difusa_diaria`). La luz que llega se divide en directa (el haz del sol, que hace sombra) y difusa (la que viene de todo el cielo). Un día nublado tiene más difusa. El modelo lo estima así:

1. `H0` es la radiación que llegaría ese día sin atmósfera (Duffie y Beckman, ec. 1.10.3). El 15 de febrero en Bogotá vale 10,049 kWh/m²/día.
2. El **índice de claridad** `KT = radiación del perfil / H0` dice qué fracción atraviesa la atmósfera. Se limita entre 0,3 y 0,8, el rango donde vale la correlación.
3. La **correlación de Erbs** convierte `KT` en la fracción difusa `kd`. Para días cortos, como los de Bogotá (ωs ≤ 81,4°): `kd = 1,391 − 3,560·KT + 4,189·KT² − 2,137·KT³`.

| Perfil | `H0` | `KT` | `kd` (difusa) | Directa |
|---|---|---|---|---|
| `NUBES_PARCIALES` | 10,049 | 0,484 | 0,445 | 0,555 |
| `NUBLADO` | 10,059 | 0,445 | 0,484 | 0,516 |
| `LLUVIOSO` | 10,408 | 0,428 | 0,503 | 0,497 |
| `CIELO_DESPEJADO` | 10,049 | 0,703 | 0,248 | 0,752 |

La directa más la difusa siempre suman 1, y un cielo con menos radiación tiene más parte difusa. El campo `nubosidad` del perfil ya no entra en el cálculo: queda como dato informativo, porque la radiación ya trae el efecto de las nubes.

**d) Periodo** (`periodo`): NOCHE antes de las 6:00 y desde las 18:00; TRANSICION de 6:00 a 7:00 y de 17:00 a 18:00; DIA el resto.

**El 15 de febrero con nubes parciales (medido):**

| Hora | Periodo | Altura del sol | Hacia dónde está | `G` | Directa horizontal | Difusa horizontal |
|---|---|---|---|---|---|---|
| 06:00 | TRANSICION | −1,1° (no ha salido) | este | 0 | 0 | 0 |
| 07:00 | DIA | 13,4° | este-sureste (105°) | 143,9 | 79,9 | 64,0 |
| 09:00 | DIA | 41,8° | este-sureste (112°) | 413,3 | 229,5 | 183,8 |
| 12:00 | DIA | 72,0° | sur (180°) | 589,3 | 327,2 | 262,1 |
| 15:00 | DIA | 41,8° | oeste-suroeste (248°) | 413,3 | 229,5 | 183,8 |
| 17:30 | TRANSICION | 6,2° | oeste-suroeste (256°) | 66,8 | 37,1 | 29,7 |
| 18:00 | NOCHE | −1,1° | oeste | 0 | 0 | 0 |

Los grados de «hacia dónde está» se miden desde el norte en el sentido del reloj (90° este, 180° sur, 270° oeste). La mañana y la tarde son simétricas alrededor de las 12:00. En febrero el sol nunca pasa por el norte, así que **las ventanas que miran al norte nunca reciben sol directo** ese día.

### 3.2 Luz natural por ventana

Una ventana es vertical, y el `Cielo` describe la luz sobre el suelo horizontal. Para cada ventana (`_aportes_naturales`) se pasa de una a otra en cuatro pasos:

1. **¿Le da el sol de frente?** `coseno = flecha de la ventana · flecha del sol` (`coseno_incidencia`). Vale 1 si el sol está justo enfrente y 0 si está de lado o detrás.
2. **¿La tapa la otra torre?** Si el coseno es mayor que 0, `_sombreada` lanza un rayo hacia el sol con el Octree (paso 2). Si choca con la otra torre, el coseno pasa a 0.
3. **Luz directa sobre la ventana** (`directa_en_vertical`, factor Rb de Duffie y Beckman):

   ```
   directa = directa horizontal × coseno / max(sen(altura del sol), sen 5°)
   ```

   Dividir por el seno de la altura da la luz del haz medida de frente al sol; multiplicar por el coseno la proyecta sobre la ventana. Con el sol muy bajo el seno se acerca a 0 y la división se dispararía; por eso se usa como mínimo el seno de 5° (0,087).
4. **Luz difusa sobre la ventana** (`difusa_en_vertical`, cielo isotrópico de Liu y Jordan): una pared vertical ve la mitad del cielo y la mitad del suelo.

   ```
   difusa = 0,5 × difusa horizontal × (1 − obstrucción) + 0,5 × reflectancia del suelo × G
   ```

   `obstrucción` es la parte del cielo que tapa la otra torre (paso 2). El segundo término es la luz que rebota en el suelo, con reflectancia 0,20.
5. **Paso por el vidrio:**

   ```
   luz de la ventana = VLT × (directa × factor_angular + difusa)
   ```

   `VLT` es la transmitancia del vidrio (0,82 el claro). `factor_angular_vidrio` aplica Snell y Fresnel a la parte directa: de frente pasa todo lo que dice el catálogo y muy de lado pasa menos. La difusa llega desde todos los ángulos y usa la transmitancia del catálogo.

**Tres ventanas de TP medidas:**

| Ventana | Hora | Coseno | Directa | Difusa (cielo + suelo) | Luz que entra |
|---|---|---|---|---|---|
| `TP-H-101` (este, TG enfrente) | 07:00 | 0,940 | 79,9 × 0,940 / 0,232 = 323,4 | 13,0 + 14,4 = 27,4 | 0,82 × (323,4 × 0,999 + 27,4) = 287,5 |
| `TP-H-102` (norte) | 12:00 | 0 | 0 | 131,1 + 58,9 = 190,0 | 0,82 × 190,0 = 155,8 |
| `TP-H-103` (oeste) | 15:00 | 0,688 | 229,5 × 0,688 / 0,667 = 236,8 | 91,9 + 41,3 = 133,2 | 0,82 × (236,8 × 0,975 + 133,2) = 298,5 |

- En `TP-H-101` la difusa del cielo es pequeña (13,0) porque TG le tapa el 59,3 % del cielo. A las 7:00 el sol igual le llega: el rayo sale hacia el este-sureste y pasa por el sur de TG (cuando llega a x = 45 m, el borde de TG, ya va en y = −3,8 m). Si la ventana estuviera en la fachada (x = 32 m) y no cerca del centro del cuarto, el rayo sí chocaría con TG; es una consecuencia de la limitación de posición descrita en el paso 2.
- `TP-H-102` mira al norte y en febrero no recibe sol directo en ninguna hora. Vive de la difusa y del suelo.
- El factor angular baja de 0,999 a 0,975 cuando el sol pasa de casi frontal (coseno 0,94) a 46,5° de lado (coseno 0,688).

La luz natural de la zona es el promedio de sus ventanas (`_calcular_naturales`). Una zona sin ventanas, como el parqueadero, tiene luz natural 0.

### 3.3 Luz reflejada

`_calcular_reflejadas` suma dos partes por zona:

- **Exterior:** para cada ventana, `luz de la fachada de enfrente × peso de la arista × VLT` (paso 2). La luz de cada fachada (`luz_fachadas`) usa las mismas fórmulas de la ventana, sin vidrio y sin obstrucción: `directa_en_vertical(coseno de la fachada) + difusa_en_vertical`. Medido:

  | Fachada | 09:00 | 12:00 | 15:00 |
  |---|---|---|---|
  | Este (TP y TG) | 370,0 | 190,0 | 133,2 |
  | Oeste (TP y TG) | 133,2 | 190,0 | 370,0 |
  | Sur | 231,5 | 296,3 | 231,5 |
  | Norte | 133,2 | 190,0 | 133,2 |

  La cara que no ve el sol recibe solo la difusa (133,2 a las 9:00 y 15:00; 190,0 a las 12:00). Las fachadas no revisan sombras entre torres.
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

**d) Tres repartos**, cada uno hasta agotar los 22 kW. Un objeto `Reparto` lleva la cuenta: guarda la capacidad del generador y un total `usado`. Cada vez que una zona pide vatios, `entregar` le da lo pedido o lo que quede, lo que sea menor, y suma eso a `usado`. Así nunca se entrega más de lo que hay, y saber cuánto queda cuesta una resta, sin volver a sumar lo ya repartido.

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
| 07:00 | ACTIVA | 38,0 | 2,8 | 159,1 | 200,0 | 68,2 | CONFORTABLE |
| 09:00 | ACTIVA | 109,3 | 8,2 | 82,6 | 200,0 | 35,4 | CONFORTABLE |
| 12:00 | ACTIVA | 155,8 | 11,7 | 32,5 | 200,0 | 13,9 | CONFORTABLE |
| 17:30 | ACTIVA | 17,6 | 1,3 | 168,0 | 187,0 | 72,0 | CONFORTABLE |
| 19:00 | ACTIVA | 0 | 0 | 168,0 | 168,0 | 72,0 | CONFORTABLE |
| 23:00 | REDUCIDA | 0 | 0 | 60,0 | 60,0 | 25,7 | CONFORTABLE |

Sin sol directo en todo el día, la luz natural nunca le basta: el generador completa el resto hasta el objetivo de 200 lux. A las 12:00 le faltan 32,5 lux, que son 13,9 W (32,5 / 2,33 lux/W). A las 17:30 ni con los 72 W llega a 200 y se queda en 187,0. La reflejada (11,7 a las 12:00) es solo interior, porque no tiene torre enfrente; con pared blanca, ρ / (1 − ρ) = 4.

**`TP-H-101`** (habitación ocupada, ventana al este, con la Torre Grande enfrente):

| Hora | Natural | Reflejada | Artificial | Total | Vatios | Estado |
|---|---|---|---|---|---|---|
| 07:00 | 287,5 | 36,1 | 0 | 323,6 | 0 | EXCESO_LEVE |
| 09:00 | 253,8 | 60,8 | 0 | 314,7 | 0 | EXCESO_LEVE |
| 12:00 | 92,0 | 66,5 | 41,5 | 200,0 | 17,8 | CONFORTABLE |
| 15:00 | 64,6 | 120,9 | 14,5 | 200,0 | 6,2 | CONFORTABLE |
| 17:30 | 10,4 | 111,7 | 77,9 | 200,0 | 33,4 | CONFORTABLE |

En la mañana el sol bajo del este le entra casi de frente y pasa del máximo de 300 lux, sin llegar a 375 (1,25 × 300), así que es exceso leve. En la tarde el sol está detrás de la ventana, pero ilumina la cara oeste de TG, y TG le devuelve más luz (120,9 a las 15:00) que la natural que le deja (64,6).

**`TP-COC-01`** (cocina, ventana al este): CERRADA a las 02:00 y 23:00 (0 vatios, DATOS_INSUFICIENTES). A las 7:00 está en sombra de TG (paso 2.2), tiene solo 26,2 lux naturales y usa sus 200 W completos. A las 9:00, 12:00 y 15:00 recibe 132, 161 y 167 W para completar sus 400 lux de objetivo (a las 12:00: natural 107,3, reflejada 35,2, artificial 257,5). De noche usa sus 200 W completos y llega a 320 lux.

**`TP-PAR-01`** (parqueadero, sin ventanas): recibe sus 720 W durante las 24 horas y queda en 89,6 lux, por encima de su mínimo de 50.

**Potencia total del generador a lo largo del día:**

| Hora | 00:00 | 06:00 | 07:00 | 09:00 | 12:00 | 15:00 | 17:30 | 18:00 | 22:00 |
|---|---|---|---|---|---|---|---|---|---|
| Vatios | 4.834 | 11.648 | 8.837 | 7.174 | 7.220 | 7.754 | 13.080 | 15.934 | 9.870 |

El pico, 15.934 W, se da entre las 18:00 y las 22:00: ya no hay sol y todo está en modo activo. De 9:00 a 15:00 el generador trabaja a menos de la mitad del pico porque el sol aporta una parte de la luz, pero no baja de unos 7.200 W: los 3 parqueaderos siguen en 720 W cada uno (2.160 W), y las zonas sin sol directo a esa hora, como `TP-H-102`, todavía piden una parte. La demanda objetivo más alta del día, si el generador no tuviera límite, es 18.110,7 W.

Estados de los 6.096 resultados: 5.517 confortables, 319 en exceso leve y 260 cerrados. No hay exceso severo ni déficit: los 22 kW alcanzan. Los 319 excesos leves son de 52 habitaciones: las 26 con ventana al este, entre las 6:30 y las 9:30, y las 26 con ventana al oeste, entre las 14:30 y las 17:30. Es el sol bajo de la mañana o de la tarde entrando casi de frente.

### Resultado y costo del paso

**Complejidad por media hora:**

- Luz natural: un rayo por ventana, O(V × (log B + k)).
- Luz reflejada: O(V + E).
- Balance: O(Z log Z). Ordenar las demandas y sacarlas de la cola `heapq` cuesta O(Z log Z), y cada entrega de `Reparto` cuesta O(1) porque lleva el total acumulado.
- El cielo (sol, `G` y `kd`) se calcula con unas pocas fórmulas por media hora: O(1).
- Clasificar y guardar: O(Z), más O(log R) por inserción en el rojo-negro.

En total, T = 48 veces lo anterior. Con 127 zonas el día completo se simula en menos de un segundo.

### Datos que conviene saber

- **La luminaria de una habitación no alcanza su objetivo de noche.** 72 W dan como máximo 168 lux y el objetivo es 200. Como 168 está entre el mínimo (100) y el máximo (300), el estado igual es CONFORTABLE.
- **El parqueadero tampoco alcanza su objetivo** (89,6 lux contra 100), pero sí su mínimo.
- **El sol puede sobrar en la mañana o en la tarde** en las habitaciones que miran al este o al oeste: el sistema no apaga la luz natural ni corre cortinas, solo lo reporta como exceso. Con el sol real, el exceso del escenario base nunca llega a severo.
- **La fecha cambia qué ventanas reciben sol.** En febrero el sol va por el sur y las ventanas al norte nunca lo ven. En abril y mayo (perfiles `LLUVIOSO` y `NUBLADO`) la declinación es positiva y el sol del mediodía va por el norte: 85,3° de altura en abril y 75,9° en mayo.
- **Un día despejado da más luz que uno nublado.** Suma de la luz natural de todas las zonas en el día: despejado 534.973, nubes parciales 396.651, nublado 385.199 y lluvioso 370.265. Un cielo nublado tiene más luz difusa en proporción, pero menos luz en total.
- **La luz excesiva no vuelve una habitación no habitable.** Con el sol real el exceso dura pocas horas. Para probar la reasignación de huéspedes se usan luminarias dañadas (`luminaria_w = 0`), que dejan la habitación a oscuras de noche (casos `luminarias_danadas` y `reasignacion_restringida`).

### Historia del cambio

Una versión anterior de este paso tenía dos simplificaciones que se corrigieron:

- **El sol era inventado.** Giraba de este a oeste por el lado norte con una altura fija de unos 35°, y la luz se repartía con `f_directa = max(0,10; 1 − nubosidad)` y `f_difusa = 0,15 + 0,45 × nubosidad`. Esas dos fracciones no sumaban 1, y un día nublado salía más claro que uno despejado. Las habitaciones al norte quedaban en exceso severo a mediodía, cuando en febrero en Bogotá no reciben sol directo. Hoy se usa la posición real del sol, la correlación de Erbs para la parte difusa y el cielo isotrópico de Liu y Jordan para pasar la luz a superficies verticales.
- **El balance volvía a sumar todo.** Una función `_asignar` recalculaba lo ya entregado en cada llamada, lo que costaba O(Z²) por media hora. `Reparto` lleva el total acumulado y da el mismo reparto (diferencias menores a 0,000000001 W) en O(Z log Z). Este cambio no tiene relación con los árboles AVL o rojo-negro: el balance usa una cola de prioridad (`heapq`).
