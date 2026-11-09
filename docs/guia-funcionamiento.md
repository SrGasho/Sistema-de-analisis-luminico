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
| Clasificar el resultado | [`_estado`, `src/simulacion.py` línea 67](../src/simulacion.py#L67); [`clasificar`, `src/evaluacion.py` línea 26](../src/evaluacion.py#L26) |
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

  Una zona en EMERGENCIA se compara con el mínimo de su modo de horario, así que ese paso cuenta como déficit. Cada comparación acepta una diferencia de 0,000000001 lux (`TOLERANCIA_LUX`): si el balance entregó justo los vatios del mínimo, el redondeo de vatios a lux no la deja en déficit.
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

---

## Paso 4. Reportes por franja horaria con el árbol rojo-negro

**Fin:** responder preguntas como «¿qué pasó en el hotel entre las 18:00 y las 22:00?» sin recorrer los 6.096 resultados del paso 3. Para eso, cada resultado se guarda, apenas se calcula, en un árbol rojo-negro ordenado por hora. Después se piden al árbol solo los resultados de la franja, y con ellos se arma un reporte de energía, pico del generador, déficit y estado de cada zona.

**Entrada:** los 6.096 resultados del paso 3, que llegan uno a uno.
**Salida:** 6 reportes, uno por franja, que la interfaz muestra en la pestaña «3. Plano».

Este paso no cambia ningún resultado: solo los ordena y los resume.

### Dónde está en el código

| Qué | Dónde |
|---|---|
| Las 6 franjas | [`FRANJAS`, `src/temporal.py` línea 9](../src/temporal.py#L9) |
| El índice por hora | [`class IndiceTemporal`, línea 19](../src/temporal.py#L19); [`insertar`, línea 24](../src/temporal.py#L24); [`franja`, línea 30](../src/temporal.py#L30); [`estadisticas`, línea 33](../src/temporal.py#L33) |
| Se crea el índice y se inserta cada resultado | [`src/simulacion.py` línea 34](../src/simulacion.py#L34) y [línea 55](../src/simulacion.py#L55) |
| Se arman los reportes al final del día | [`src/simulacion.py` línea 58](../src/simulacion.py#L58); [`reporte_temporal`, `src/temporal.py` línea 112](../src/temporal.py#L112) |
| Reporte de una franja | [`reporte_franja`, línea 54](../src/temporal.py#L54); [`_minimo`, línea 40](../src/temporal.py#L40); [`_conversion`, línea 46](../src/temporal.py#L46) |
| El árbol rojo-negro | [`class IndiceRojoNegro`, `src/arboles.py` línea 173](../src/arboles.py#L173); [`insertar`, línea 180](../src/arboles.py#L180); [`_reparar`, línea 220](../src/arboles.py#L220); [`_rotar_izq`, línea 255](../src/arboles.py#L255); [`_rotar_der`, línea 271](../src/arboles.py#L271) |
| Consulta por rango | [`IndiceRojoNegro.rango`, `src/arboles.py` línea 203](../src/arboles.py#L203) |
| AVL de comparación | [`class IndiceAVL`, `src/arboles.py` línea 17](../src/arboles.py#L17); se pide en [`src/api.py` línea 137](../src/api.py#L137) |
| Se envía a la interfaz | [`src/api.py` líneas 170–171](../src/api.py#L170) |
| Selector y reporte en la interfaz | [`renderFranjaSelector`, `web/app.js` línea 93](../web/app.js#L93); [`renderFranjaReport`, línea 103](../web/app.js#L103); [`claveVisual`, línea 86](../web/app.js#L86); [`renderComplexity`, línea 129](../web/app.js#L129) |

### 4.1 Qué se guarda y con qué clave

Cada nodo del árbol guarda un `ResultadoIluminacion` del paso 3 (hora, zona, modo, las tres luces, total, vatios y estado). El nodo no copia el resultado: apunta al mismo objeto que ya está en la zona.

La **clave** con la que se ordena es la pareja `(hora, zona_id)`. Python compara parejas por partes: primero la hora y, si es la misma, el identificador en orden alfabético. Así, todos los resultados de las 0:00 quedan antes que los de las 0:30, y dentro de la misma hora `TG-…` queda antes que `TP-…` porque «G» va antes que «P». La pareja es única: una zona tiene un solo resultado por media hora.

Ejemplo del orden: `(0,0, "TG-COC-01") < (0,0, "TP-H-101") < (0,5, "TG-COC-01")`.

### 4.2 Por qué hace falta un árbol balanceado

El paso 3 inserta los resultados en el orden en que los calcula: hora por hora y, dentro de cada hora, primero las 41 zonas de TP y luego las 86 de TG. Ese orden está casi ordenado: en 5.759 de los 6.095 pares seguidos, la clave nueva es mayor que la anterior.

Un árbol binario de búsqueda sin balancear se deforma con datos así. Cada clave nueva va casi siempre a la derecha de la anterior y el árbol se vuelve una cadena larga. Medido con las mismas 6.096 claves:

| Árbol | Altura | Comparaciones para insertar todo | Rotaciones |
|---|---|---|---|
| Búsqueda sin balancear | 640 | 1.891.104 | 0 |
| Rojo-negro | 22 | 112.587 | 9.099 |
| AVL (solo para comparar) | 14 | — | 7.232 |

La altura es el número de nodos del camino más largo de la raíz a una hoja, y marca lo que cuesta llegar a cualquier resultado. El árbol sin balancear no llega a 6.096 de altura porque cada hora trae claves de TG menores que las de TP de la misma hora; aun así, cada inserción recorre en promedio unos 310 nodos. El rojo-negro recorre en promedio unos 18.

El rojo-negro garantiza una altura de como máximo 2 × log₂(n + 1), que con n = 6.096 da 25,1. La medida, 22, está dentro del límite.

### 4.3 Cómo inserta el árbol rojo-negro

Cada nodo tiene un color, rojo o negro, y el árbol cumple siempre cuatro reglas:

1. La raíz es negra.
2. Un nodo rojo no puede tener un hijo rojo.
3. Todos los caminos de un nodo hasta el fondo del árbol cruzan el mismo número de nodos negros (la **altura negra**).
4. Los huecos vacíos del fondo cuentan como negros.

Las reglas 2 y 3 juntas impiden que un camino sea más del doble de largo que otro: el camino más corto puede ser todo negro, y el más largo solo puede intercalar un rojo entre cada par de negros.

**`insertar`** baja desde la raíz como en cualquier árbol de búsqueda: a la izquierda si la clave nueva es menor y a la derecha si no. Cuelga el nodo nuevo en el hueco donde termina, siempre de color **rojo**. Un nodo rojo nuevo no cambia la altura negra, así que la regla 3 se mantiene. Solo puede romperse la regla 2, si el padre también es rojo.

**`_reparar`** arregla la regla 2 mirando al **tío** del nodo nuevo (el otro hijo del abuelo):

- **Tío rojo:** se cambian colores. Padre y tío pasan a negro y el abuelo a rojo. El problema puede subir al abuelo, así que se repite desde ahí.
- **Tío negro o vacío:** se hacen una o dos **rotaciones**. Una rotación gira tres nodos para que el del medio quede arriba, sin romper el orden de las claves. Después se ajustan los colores y se termina.

Al final la raíz se pinta de negro.

**Ejemplo con las cuatro primeras claves de las 0:00** (medido con el código):

| Se inserta | Qué pasa | Árbol resultante | Rotaciones |
|---|---|---|---|
| `TP-H-101` | Es la raíz; se pinta de negro | 101 (N) | 0 |
| `TP-H-102` | Va a la derecha de 101, rojo; su padre es negro, no hay nada que arreglar | 101 (N) → derecha 102 (R) | 0 |
| `TP-H-103` | Va a la derecha de 102. Padre rojo y tío vacío: se rota a la izquierda sobre 101 | 102 (N), con 101 (R) a la izquierda y 103 (R) a la derecha | 1 |
| `TP-H-104` | Va a la derecha de 103. Padre rojo y tío (101) rojo: se cambian colores; 101 y 103 pasan a negro | 102 (N), con 101 (N) y 103 (N), y 104 (R) debajo de 103 | 1 |

Sin la rotación del tercer paso, las tres claves quedarían en una línea, que es justo lo que le pasa al árbol sin balancear.

**Cómo queda el árbol completo** en el escenario base: 6.096 nodos, altura 22, altura negra 11 y 780 nodos rojos.

**La raíz** es el nodo con clave `(5,0, "TP-H-108")`: el resultado de la habitación `TP-H-108` a las 5:00 (modo REDUCIDA, 0 lux naturales, 60 lux artificiales con 25,7 W, CONFORTABLE). No tiene nada especial como dato; está arriba porque las rotaciones la subieron hasta ahí.

- Fue el resultado número 1.278 en insertarse, no el primero. La primera raíz fue `(0,0, "TP-H-101")`, y la raíz cambió 10 veces durante el día: `TP-H-102`, `TP-H-104` y `TP-H-108` de las 0:00, luego `(0,5, "TG-H-140")`, `(1,0, "TP-H-108")`, `(2,5, "TG-H-140")` y, desde la inserción 3.396, `(5,0, "TP-H-108")`, que ya no cambió hasta la 6.096.
- Cada cambio pasa cuando una rotación cerca de la raíz sube a otro nodo para que ningún camino quede demasiado largo.
- A su izquierda quedan los 1.367 resultados de antes de las 5:00 y a su derecha los 4.728 de después. Sus hijos directos son `(2,5, "TG-H-140")` y `(10,5, "TG-H-140")`.
- **Nadie la elige.** No hay ninguna línea del código que diga cuál debe ser la raíz. Sale de dos cosas: el orden en que llegan las claves y las reglas de reparación. Con los mismos datos en el mismo orden la raíz siempre es la misma; si cambia el orden, cambia la raíz. Medido con las mismas 6.096 claves:

  | Orden de inserción | Raíz | Altura |
  |---|---|---|
  | El del paso 3 | `(5,0, "TP-H-108")` | 22 |
  | Ordenado de menor a mayor | `(8,0, "TG-H-110")` | 22 |
  | Al azar (semilla 1) | `(11,0, "TP-H-113")` | 15 |
  | Al azar (semilla 2) | `(9,0, "TG-H-139")` | 15 |

- **El último cambio de raíz** pasó al insertar `(13,0, "TG-H-139")`, el resultado número 3.396. Esa inserción dejó dos rojos seguidos, la reparación cambió colores subiendo por el árbol hasta llegar junto a la raíz, y ahí hizo una rotación: la raíz anterior, `(2,5, "TG-H-140")`, bajó a la izquierda y su hijo derecho, `(5,0, "TP-H-108")`, subió. Las 2.700 inserciones que siguieron se arreglaron más abajo, sin tocar la raíz.
- La raíz no queda en la mitad del día (la mitad exacta sería `(12,0, "TG-COC-01")`) porque el rojo-negro no reparte el mismo número de nodos a cada lado. Lo que asegura es que ningún camino sea más del doble de largo que otro, y con eso basta para que la altura se quede en 22.

### 4.4 La consulta por rango

`IndiceTemporal.franja(inicio, fin)` le pide al árbol todos los resultados con clave entre `(inicio, "")` y `(fin, "")`. La cadena vacía `""` es menor que cualquier identificador, así que:

- `(inicio, "")` queda justo antes del primer resultado de la hora `inicio`: esa hora **entra**.
- `(fin, "")` queda justo antes del primer resultado de la hora `fin`: esa hora **no entra**.

Por eso cada franja es un intervalo `[inicio, fin)`. La franja 18:00–22:00 incluye las 18:00 y las 21:30, pero no las 22:00, que son de la franja de cierre. Ningún resultado cae en dos franjas, salvo en «Día completo», que contiene todas.

`rango` recorre el árbol desde la raíz y poda:

- baja a la izquierda solo si la clave del nodo es mayor que el mínimo (a la izquierda puede haber claves del rango);
- guarda el nodo si su clave está dentro del rango;
- baja a la derecha solo si la clave del nodo es menor que el máximo.

Como recorre en orden (izquierda, nodo, derecha), los resultados salen ordenados por hora y zona. El costo es O(log R + k): unos pocos nodos para llegar al borde del rango más los k nodos que se devuelven. Medido en el escenario base:

| Consulta | Resultados (k) | Nodos visitados | Recorrer la lista completa |
|---|---|---|---|
| Solo las 12:00 | 127 | 142 | 6.096 |
| Noche 18:00–22:00 | 1.016 | 1.029 | 6.096 |
| Madrugada 00:00–06:00 | 1.524 | 1.532 | 6.096 |
| Día completo | 6.096 | 6.096 | 6.096 |

**Recorrido real de la consulta de las 12:00** (rango de `(12,0, "")` a `(12,5, "")`, medido con el código). En cada nodo el árbol hace las tres preguntas de arriba:

| Profundidad | Nodo | ¿Está en el rango? | Hacia dónde sigue |
|---|---|---|---|
| 0 (raíz) | `(5,0, "TP-H-108")` | No, es antes | Solo a la derecha: a la izquierda todo es aún más temprano |
| 1 | `(10,5, "TG-H-140")` | No, es antes | Solo a la derecha |
| 2 | `(16,0, "TG-H-108")` | No, es después | Solo a la izquierda: a la derecha todo es aún más tarde |
| 3 | `(13,0, "TP-H-108")` | No, es después | Solo a la izquierda |
| 4 | `(12,0, "TG-H-108")` | **Sí**, primer nodo de las 12:00 | A los dos lados |

En 4 pasos el árbol descartó la raíz y tres ramas enteras: todo lo de antes de las 5:00, todo lo de 5:00 a 10:30 y todo lo de después de las 16:00. Desde el nodo de la profundidad 4 hacia abajo están mezclados los 127 resultados de las 12:00 con algunos de las 11:00, 11:30 y 12:30 en los bordes. La consulta visita 142 nodos: guarda los 127 de las 12:00 y descarta 15 (los 4 del camino de arriba, 5 de las 11:00 y 11:30 y 6 de las 12:30).

Los resultados de una misma hora no quedan uno al lado del otro en el dibujo del árbol; quedan repartidos en una rama y entre distintas profundidades. Lo que sí garantiza el árbol es que, leído en orden (izquierda, nodo, derecha), salen seguidos.

**Cómo llegan al análisis.** `rango` va metiendo en una lista de Python cada nodo que está dentro del rango, en el orden en que los visita. Como visita en orden, la lista sale ordenada: `TG-COC-01`, `TG-COC-02`, … hasta `TP-REC-04`, todos de las 12:00. `IndiceTemporal.franja` devuelve esa lista, y `reporte_franja` la recorre una sola vez con un `for`: por cada resultado suma sus vatios a la energía, a su actividad, a su torre y a su hora, cuenta su estado y, si está en déficit, suma lo que le faltó. Al terminar el `for`, el reporte está listo. El árbol solo se usa para encontrar los resultados; el análisis trabaja con la lista.

Los nodos visitados de más (15 en las 12:00) son los del camino hasta el borde del rango. En «Día completo» no hay ganancia, porque hay que devolver todo. El contador de nodos visitados (`comparaciones`) es el mismo que usa la inserción; `reporte_franja` lo lee antes y después de la consulta y reporta la diferencia.

### 4.5 Qué calcula cada franja

Las franjas están fijas en el código (`FRANJAS`):

| Franja | Desde | Hasta (sin incluir) | Medias horas | Resultados |
|---|---|---|---|---|
| Día completo | 0:00 | 24:00 | 48 | 6.096 |
| Madrugada | 0:00 | 6:00 | 12 | 1.524 |
| Mañana | 6:00 | 12:00 | 12 | 1.524 |
| Tarde | 12:00 | 18:00 | 12 | 1.524 |
| Noche | 18:00 | 22:00 | 8 | 1.016 |
| Cierre | 22:00 | 24:00 | 4 | 508 |

`reporte_franja` recorre una vez los resultados de la franja y calcula:

| Campo | Qué es | Cómo se calcula |
|---|---|---|
| `energia_wh`, `energia_kwh` | Energía que entregó el generador | Suma de `vatios × 0,5 h` |
| `energia_por_actividad_wh`, `energia_por_torre_wh` | La misma energía repartida | Suma por actividad y por torre |
| `hora_pico`, `potencia_pico_w` | Media hora en que el generador entregó más | Suma de vatios por hora y se toma la mayor; si hay empate, la más temprana |
| `deficit_residual_lux_h` | Cuánta luz faltó, sumada en el tiempo | Para cada resultado en déficit: `(mínimo − luz total) × 0,5 h` |
| `energia_no_asignada_wh` | Energía que el generador habría tenido que entregar para llegar al mínimo | Para cada resultado en déficit: `min((mínimo − luz total) / lux por vatio, potencia de la luminaria − vatios asignados) × 0,5 h`. No cuenta lo que la luminaria no puede dar |
| `zonas_con_deficit`, `horas_deficit_por_zona` | Qué zonas tuvieron déficit y cuántas horas | Cada resultado en déficit suma 0,5 h a su zona |
| `zonas_criticas` | Las 10 zonas con más horas de déficit | Orden por horas, de mayor a menor; si empatan, por identificador |
| `horas_con_deficit` | Medias horas en las que alguna zona tuvo déficit | Conjunto de horas, ordenado |
| `estados_por_zona` | Estado predominante de cada zona en la franja | El estado que más se repite, sin contar `DATOS_INSUFICIENTES`; si hay empate, gana el que apareció primero |
| `comparaciones_arbol`, `comparaciones_lineales` | Costo de la consulta | Nodos visitados contra los 6.096 de una lista |

Dos detalles:

- **El mínimo de una zona en EMERGENCIA** (`_minimo`) es el de su modo de horario, igual que en el paso 3.5. Si a las 19:00 una habitación quedó en EMERGENCIA, su mínimo es el del modo ACTIVA, 100 lux, y no el de emergencia.
- **Lux por vatio** (`_conversion`) es la misma conversión del balance: `eficacia × CU × MF / área`, 2,33 lux/W en una habitación.

**Escenario base (medido):**

| Franja | Energía | Pico | Zonas con estado | Estado predominante |
|---|---|---|---|---|
| Día completo | 208,08 kWh | 15.934 W a las 18:00 | 127 | 127 CONFORTABLE |
| Madrugada | 29,76 kWh | 5.584 W a las 5:00 | 117 | 117 CONFORTABLE |
| Mañana | 47,47 kWh | 11.648 W a las 6:00 | 127 | 109 CONFORTABLE, 18 EXCESO_LEVE |
| Tarde | 51,12 kWh | 13.080 W a las 17:30 | 127 | 119 CONFORTABLE, 8 EXCESO_LEVE |
| Noche | 63,74 kWh | 15.934 W a las 18:00 | 127 | 127 CONFORTABLE |
| Cierre | 15,99 kWh | 9.870 W a las 22:00 | 127 | 127 CONFORTABLE |

- No hay déficit en ninguna franja: déficit residual, energía no asignada y zonas críticas valen 0.
- En la madrugada solo 117 zonas tienen estado. Las otras 10 están CERRADA durante toda la franja y solo tienen resultados `DATOS_INSUFICIENTES`, que no se cuentan. En el plano se pintan como `DATOS_INSUFICIENTES`.
- En el día completo las 52 habitaciones con exceso leve aparecen como CONFORTABLE, porque el exceso dura a lo sumo 7 de sus 48 medias horas. Las franjas de mañana y tarde sí lo muestran: 18 habitaciones al este en la mañana y 8 al oeste en la tarde.
- La noche es la franja que más gasta (63,74 kWh en 4 horas): no hay sol y casi todo está en modo ACTIVA.
- Energía del día por actividad: habitaciones 81,96 kWh, parqueaderos 51,84, recreación 44,97 y cocinas 29,30. Por torre: TG 136,18 kWh y TP 71,90.

**Un caso con déficit: `luminarias_danadas`** (16 habitaciones de TP sin luminaria). En la franja de noche:

| Campo | Valor | De dónde sale |
|---|---|---|
| Zonas con déficit | 16 | Las 16 habitaciones sin luminaria |
| Horas de déficit por zona | 4,0 | Las 8 medias horas de la franja |
| Déficit residual | 6.400 lux·h | 16 zonas × 4 h × 100 lux (tienen 0 lux y su mínimo es 100) |
| Energía no asignada | 0 Wh | Las luminarias tienen 0 W: aunque el generador tuviera energía de sobra, no hay por dónde entregarla |
| Pico | 14.782 W a las 18:00 | Menos que en el base (15.934 W) porque esas 16 luminarias no consumen |

La energía no asignada sí aparece cuando lo que falta es generador. En `deficit_severo` (4 kW), la noche tiene 69 zonas con déficit, 36.633,3 lux·h de déficit residual y 25.578,6 Wh de energía no asignada: lo que el generador habría tenido que entregar, sin pasar de la potencia de cada luminaria, para que esas zonas llegaran a su mínimo.

En el día completo, las zonas más críticas son `TP-H-102`, `TP-H-106`, `TP-H-110` y `TP-H-114`, con 16,5 horas de déficit cada una. Son las que miran al norte. Además de las 12 horas de noche, sin sol directo su luz natural queda por debajo del mínimo de 100 lux de 6:00 a 8:00 y de 16:00 a 17:30.

### 4.6 El AVL al lado, solo para comparar

Si el simulador se crea con `comparar_arboles=True`, `IndiceTemporal` inserta cada resultado también en un árbol AVL (el mismo tipo de árbol del paso 6). La API lo pide siempre que devuelve resultados completos ([`src/api.py` línea 137](../src/api.py#L137)). El AVL no se usa para ningún reporte: solo se miden su altura y sus rotaciones, y la pestaña «6. Detalle técnico» muestra las dos medidas lado a lado.

Con estos datos el AVL queda más bajo (altura 14 contra 22) y hace menos rotaciones (7.232 contra 9.099). Queda más bajo porque su regla es más estricta: las dos ramas de cada nodo difieren en altura a lo sumo en 1. El rojo-negro admite ramas más desiguales, y muchas de sus reparaciones solo cambian colores sin rotar. Al insertar, los dos hacen como máximo dos rotaciones por clave. Los dos responden la consulta en O(log R + k) y devuelven los mismos resultados.

### 4.7 Dónde se ve en la interfaz

- **Pestaña «3. Plano», selector «Franja horaria».** Con «Veredicto del día (sin franja)» el plano usa el veredicto del paso 5 o el estado de la zona, según el selector de color. Al elegir una franja, cada zona se pinta con su estado predominante en esa franja (`estados_por_zona`), y debajo del plano aparece el reporte: energía, pico, déficit residual, energía no asignada, horas con déficit, tablas por actividad y por torre, zonas críticas y los nodos visitados del rojo-negro contra los 6.096 de la lista.
- **Pestaña «6. Detalle técnico».** Muestra el tamaño, la altura y las rotaciones del rojo-negro y del AVL.

### Resultado y costo del paso

| Operación | Costo | Escenario base |
|---|---|---|
| Insertar un resultado | O(log R) | 18 nodos en promedio |
| Insertar los R resultados del día | O(R log R) | 112.587 comparaciones, 9.099 rotaciones, 0,01 s |
| Consultar una franja | O(log R + k) | Entre 142 y 6.096 nodos |
| Armar el reporte de la franja | O(k) | Una pasada por los k resultados |
| Memoria | O(R) | 6.096 nodos que apuntan a los resultados, sin copiarlos |

R = 6.096 resultados (127 zonas × 48 medias horas). El árbol se construye durante el bucle del paso 3; los 6 reportes se arman una vez, al final del día.

### Ideas clave del paso

- **El árbol ordena por tiempo, no por zona.** La clave `(hora, zona_id)` hace que todos los resultados de una hora queden juntos y en orden, y así una franja es un trozo seguido del árbol.
- **El balanceo importa porque los datos llegan casi ordenados.** Sin él, el árbol de búsqueda tendría altura 640 y costaría 17 veces más comparaciones insertar el día completo.
- **Las rotaciones no cambian el orden.** Solo cambian quién está arriba, para que ningún camino sea demasiado largo.
- **La consulta por rango poda.** Se salta las ramas que quedan completas antes del inicio o después del fin, y la ganancia crece cuanto más corta es la franja.
- **El reporte es una suma sencilla** sobre lo que devolvió la consulta: energía, pico, déficit y estado predominante.

### Datos que conviene saber

- **Las franjas están fijas en el código.** No se pueden cambiar desde el JSON ni desde la interfaz.

### Historia del cambio (D17)

Al escribir este paso aparecieron dos errores, que se corrigieron:

- **Déficit por redondeo.** El balance entrega justo la potencia del mínimo: `(mínimo − luz natural − reflejada) / lux por vatio`. Al volver a convertir esos vatios en lux, el total podía quedar 0,00000000000001 lux por debajo del mínimo, y `clasificar` lo marcaba como `DEFICIT_LEVE` porque comparaba con `nivel < mínimo`. En el caso `deficit_leve` de entonces (generador de 10 kW), 851 de sus 867 resultados en déficit eran de este tipo; en `deficit_severo`, 903 de 1.563. Hoy `clasificar` acepta una diferencia de 0,000000001 lux (`TOLERANCIA_LUX`, [`src/evaluacion.py` línea 8](../src/evaluacion.py#L8)) y la prueba `test_sin_deficit_por_redondeo` revisa que ningún déficit de ningún caso quede a menos de 0,000001 lux del mínimo.
  - Con el arreglo, el generador de 10 kW ya no producía un déficit leve: casi todo el hotel quedaba habitable (125/1/1). La razón es que, cuando falta generador, el balance cubre los mínimos completos o deja la zona en EMERGENCIA con 10 lux, que es déficit severo. Un déficit leve real aparece cuando la luminaria no alcanza el mínimo, así que `deficit_leve` pasó a ser el caso de 12 habitaciones con luminarias viejas de 30 W (70 lux como máximo): 115/12/0.
  - `deficit_severo` (4 kW) pasó de 3/56/68 a 59/0/68. Las habitaciones ocupadas de los pisos 2 en adelante sí alcanzan su mínimo y quedan habitables, y los 22 huéspedes afectados se mueven a sus camas libres. El caso «nadie tiene a dónde ir» lo muestra ahora `apagon_generador`.
- **La energía no asignada no miraba la luminaria.** Contaba los vatios que harían falta para llegar al mínimo aunque la luminaria no pudiera darlos. En `luminarias_danadas` reportaba 5.529,5 Wh en el día cuando al generador le sobraba potencia. Ahora no pasa de `potencia de la luminaria − vatios asignados` y en ese caso da 0.

---

## Paso 5. Veredicto de habitabilidad por zona

**Fin:** convertir los 48 estados que tiene cada zona en el día (paso 3) en una sola respuesta: ¿se puede usar esta zona? La respuesta es uno de tres veredictos, **HABITABLE**, **CASI_HABITABLE** o **NO_HABITABLE**, con un puntaje entre 0 y 1, la causa principal del problema y, si está cerca de ser habitable, una recomendación.

**Entrada:** los resultados que el paso 3 guardó en cada zona (`zona.resultados`) y los umbrales de `parametros_evaluacion` del JSON.
**Salida:** un veredicto por zona (127), el conteo de veredictos y el puntaje del hotel completo. El paso 6 usa estos veredictos para decidir quién se cambia de habitación y a dónde.

Este paso no usa árboles: es un conteo sobre los resultados de cada zona.

### Dónde está en el código

| Qué | Dónde |
|---|---|
| Se llama al terminar el día | [`src/simulacion.py` línea 59](../src/simulacion.py#L59) |
| Umbrales y valores de cada estado | [`umbrales`, `src/habitabilidad.py` línea 15](../src/habitabilidad.py#L15); en el JSON, [`parametros_evaluacion.puntaje` y `.habitabilidad`, `data/datos_hotel.json` líneas 242–251](../data/datos_hotel.json#L242) |
| Puntaje de una lista de resultados | [`_puntaje`, línea 36](../src/habitabilidad.py#L36) |
| Veredicto, causa y recomendación de una zona | [`evaluar_zona`, línea 61](../src/habitabilidad.py#L61); [`_causa`, línea 28](../src/habitabilidad.py#L28); [`CAUSA_RECOMENDACION`, línea 7](../src/habitabilidad.py#L7) |
| Puntaje del hotel | [`evaluar_hotel`, línea 110](../src/habitabilidad.py#L110); [`_promedio_ponderado`, línea 102](../src/habitabilidad.py#L102) |
| Conteos que se envían a la interfaz | [`src/api.py` líneas 159–168](../src/api.py#L159) |
| Tarjetas y recomendaciones en la interfaz | [`renderVeredictos`, `web/app.js` línea 201](../web/app.js#L201); se usa en [línea 530](../web/app.js#L530) (Diagnóstico) y [línea 1216](../web/app.js#L1216) (Balance) |
| Color del plano por veredicto | [`claveVisual`, `web/app.js` línea 86](../web/app.js#L86) |

### 5.0 La idea con una habitación

Antes de las reglas, un ejemplo completo. `TG-H-113`, en el caso `deficit_leve`, tiene una luminaria vieja de 30 W que da como máximo 70 lux. Su día, en las 48 medias horas que calculó el paso 3, fue así:

| Horas | Medias horas | Qué pasó | Estado |
|---|---|---|---|
| 0:00 a 5:30 | 12 | Modo reducido; pide 30 lux y tiene 60 | CONFORTABLE |
| 6:00 | 1 | Ya es modo activo (pide 100) y aún no hay sol: 70 lux | DEFICIT_LEVE |
| 6:30 a 9:30 | 7 | El sol de la mañana entra por su ventana al este: unos 310 a 340 lux, pasa del máximo de 300 | EXCESO_LEVE |
| 10:00 a 17:00 | 15 | Luz natural más luminaria, dentro del rango | CONFORTABLE |
| 17:30 | 1 | Queda poco sol: 89 lux | DEFICIT_LEVE |
| 18:00 a 21:30 | 8 | De noche, modo activo, solo la luminaria: 70 lux | DEFICIT_LEVE |
| 22:00 a 23:30 | 4 | Modo reducido otra vez | CONFORTABLE |

**Puntaje: una nota por media hora.** Es como calificar cada media hora del día y sacar el promedio:

- cada media hora confortable vale **1** punto: 12 + 15 + 4 = 31 medias horas, **31 puntos**;
- cada media hora con un problema leve vale **0,5**: 10 de déficit leve y 7 de exceso leve, 17 × 0,5 = **8,5 puntos**;
- una media hora con un problema severo valdría **0** (esta habitación no tiene ninguna).

Puntaje = (31 + 8,5) / 48 = 39,5 / 48 = **0,8229**, es decir, un 82 %.

**Veredicto: dónde cae el puntaje en la escala.**

```
0 ─────────── 0,75 ─────────── 0,90 ─────────── 1
  NO_HABITABLE    CASI_HABITABLE     HABITABLE
                        ↑
                     0,8229
```

0,8229 está entre 0,75 y 0,90: **CASI_HABITABLE**. Para ser habitable le faltan 0,90 − 0,8229 = 0,0771 (la **brecha**).

Además de la escala hay un control aparte: si la zona pasó **más del 5 % de su tiempo a oscuras** (déficit severo, menos de la mitad del mínimo), es NO_HABITABLE aunque su puntaje sea bueno. `TG-H-113` nunca estuvo a oscuras, así que este control no la afecta.

**Causa: qué problema se repitió más.** Se toman solo las medias horas con problema y se les pone una etiqueta según el tipo y la hora:

| Etiqueta | Medias horas de `TG-H-113` |
|---|---|
| Falta luz de noche (`DEFICIT_NOCTURNO`) | 8 (de 18:00 a 21:30) |
| Sobra sol (`EXCESO_SOLAR`) | 7 (de 6:30 a 9:30) |
| Falta luz de día (`DEFICIT_DIURNO`) | 2 (6:00 y 17:30) |

La que más se repite es `DEFICIT_NOCTURNO`, y esa es la **causa** de la zona. Con la causa se elige la recomendación: «ampliar el horario de iluminación de la zona o revisar la potencia de sus luminarias», que es justo su problema real.

Las secciones siguientes explican cada parte con detalle.

### 5.1 Qué resultados cuentan

De los 48 resultados de una zona solo cuentan los **evaluables**: se descartan los `DATOS_INSUFICIENTES`, que son las medias horas en que la zona estaba CERRADA (o, en el diagnóstico sin balance, la noche). Una zona cerrada no puede estar bien ni mal iluminada.

| Zona (escenario base) | Resultados | Cerrados | Evaluables |
|---|---|---|---|
| `TP-H-101` (habitación) | 48 | 0 | 48 |
| `TP-COC-01` (cocina) | 48 | 12 | 36 |
| `TP-REC-01` (recreación) | 48 | 14 | 34 |
| `TP-PAR-01` (parqueadero) | 48 | 0 | 48 |

Si una zona no tiene ningún resultado evaluable, su veredicto es `DATOS_INSUFICIENTES`.

### 5.2 El puntaje

Cada estado vale un número `q` (`parametros_evaluacion.puntaje`):

| Estado | q |
|---|---|
| CONFORTABLE | 1,0 |
| DEFICIT_LEVE o EXCESO_LEVE | 0,5 |
| DEFICIT_SEVERO o EXCESO_SEVERO | 0,0 |

El **puntaje** de la zona es el promedio de `q` en sus resultados evaluables:

```
puntaje = suma de q / número de resultados evaluables
```

Ejemplos del escenario base:

- `TP-H-101` (ventana al este): 42 confortables y 6 en exceso leve. Puntaje = (42 × 1 + 6 × 0,5) / 48 = 45 / 48 = **0,9375**.
- `TP-H-103` (ventana al oeste): 41 confortables y 7 en exceso leve. Puntaje = (41 + 3,5) / 48 = **0,9271**.
- `TP-H-102` (ventana al norte): 48 confortables. Puntaje = **1,0**.
- `TP-COC-01`: 36 evaluables, todos confortables. Puntaje = **1,0**; las 12 medias horas cerradas no le bajan el puntaje.

El puntaje mide la fracción del tiempo en que la zona estuvo bien, y da media nota a los ratos en que estuvo un poco mal.

### 5.3 El veredicto

`evaluar_zona` aplica tres reglas, en este orden (`parametros_evaluacion.habitabilidad`):

1. **NO_HABITABLE** si más del 5 % de los resultados evaluables son `DEFICIT_SEVERO` (`maximo_deficit_severo` = 0,05), **o** si el puntaje es menor que 0,75 (`umbral_casi`).
2. **HABITABLE** si el puntaje es 0,90 o más (`umbral_habitable`).
3. **CASI_HABITABLE** en el resto: puntaje entre 0,75 y 0,90, sin pasar del 5 % de déficit severo.

La primera regla tiene dos partes porque mide dos cosas distintas. El puntaje mide cuánto tiempo estuvo mal la zona. El límite de déficit severo mide si estuvo **a oscuras**, aunque fuera poco tiempo: una habitación con menos de la mitad del mínimo de luz no se puede usar, por bien que esté el resto del día. El exceso severo no tiene ese límite: sobra luz, pero se puede usar con una cortina.

**Qué significan los umbrales en una habitación con 48 resultados evaluables:**

| Si los únicos problemas son… | HABITABLE | CASI_HABITABLE | NO_HABITABLE |
|---|---|---|---|
| Pasos leves (q = 0,5) | hasta 9 (4,5 h) | de 10 a 24 | 25 o más |
| Pasos en exceso severo (q = 0) | hasta 4 (2 h) | de 5 a 12 | 13 o más |
| Pasos en déficit severo (q = 0) | hasta 2 (1 h) | — | 3 o más (1,5 h) |

Con 2 pasos en déficit severo la proporción es 2/48 = 4,2 %; con 3 es 6,25 % y ya pasa del 5 %. Por eso hora y media a oscuras basta para que una habitación sea no habitable.

**Ejemplos medidos:**

| Caso y zona | Estados evaluables | Puntaje | Déficit severo | Veredicto |
|---|---|---|---|---|
| Base, `TP-H-101` | 42 confortables, 6 exceso leve | 0,9375 | 0 % | HABITABLE |
| `exceso_severo`, `TP-H-101` | 39 confortables, 1 exceso leve, 8 exceso severo | 0,8229 | 0 % | CASI_HABITABLE |
| `deficit_leve`, `TG-H-113` | 31 confortables, 10 déficit leve, 7 exceso leve | 0,8229 | 0 % | CASI_HABITABLE |
| `deficit_leve`, `TG-H-114` | 37 confortables, 11 déficit leve | 0,8854 | 0 % | CASI_HABITABLE |
| `deficit_severo`, `TP-COC-01` | 27 confortables, 9 déficit severo (de 36) | 0,7500 | 25,0 % | NO_HABITABLE |
| `deficit_severo`, `TG-H-170` | 39 confortables, 9 déficit severo | 0,8125 | 18,75 % | NO_HABITABLE |
| `luminarias_danadas`, `TP-H-101` | 17 confortables, 6 exceso leve, 25 déficit severo | 0,4167 | 52,1 % | NO_HABITABLE |

- `TP-COC-01` en `deficit_severo` tiene puntaje 0,75 justo, que no es menor que 0,75. Queda no habitable solo por la regla del déficit severo.
- `TG-H-170` tiene un puntaje que sería casi habitable (0,8125), pero pasó 4,5 horas a oscuras. La regla del déficit severo la vuelve no habitable.
- En `deficit_severo` las 68 zonas no habitables lo son por el déficit severo; 28 de ellas también tienen puntaje menor que 0,75.

### 5.4 Puntaje de día y de noche

`evaluar_zona` calcula además el puntaje con los resultados de día y con los de noche por separado. «Día» es todo lo que no es NOCHE, es decir, de 6:00 a 17:30 (24 medias horas, contando la transición); «noche» es de 18:00 a 5:30 (24 medias horas).

| Caso y zona | Día | Noche | Total |
|---|---|---|---|
| Base, `TP-H-101` | 0,875 | 1,0 | 0,9375 |
| `deficit_leve`, `TG-H-113` | 0,8125 | 0,8333 | 0,8229 |
| `luminarias_danadas`, `TP-H-101` | 0,8333 | 0,0 | 0,4167 |

Estos dos puntajes **no deciden el veredicto**; solo ayudan a ver cuándo está el problema. En `luminarias_danadas` la habitación está bien de día y a oscuras toda la noche. En `deficit_leve`, de noche tiene 70 lux en las 8 medias horas activas (de 18:00 a 21:30) y está bien en las 16 de modo reducido, donde el mínimo es 30.

### 5.5 Causa y recomendación

`_causa` le pone una etiqueta a cada resultado evaluable que no está confortable:

| Etiqueta | Cuándo |
|---|---|
| `DEFICIT_NOCTURNO` | Déficit (leve o severo) de noche |
| `DEFICIT_DIURNO` | Déficit de día |
| `EXCESO_SOLAR` | Exceso con más luz natural que artificial |
| `EXCESO_ARTIFICIAL` | Exceso con más luz artificial que natural |

La **causa** de la zona es la etiqueta que más se repite. Si dos empatan, gana la que apareció primero en el día. Hay una excepción: si la zona es NO_HABITABLE porque pasó más del 5 % del tiempo a oscuras, solo se cuentan las medias horas en déficit severo, porque son las que decidieron el veredicto. Así la causa siempre es un déficit (diurno o nocturno) en esas zonas. Ejemplo: `TG-H-113` en `deficit_leve` tiene 8 pasos `DEFICIT_NOCTURNO`, 7 `EXCESO_SOLAR` (la mañana, por su ventana al este) y 2 `DEFICIT_DIURNO` (las 6:00 y las 17:30). Su causa es `DEFICIT_NOCTURNO` por un solo paso.

Cada causa tiene una recomendación fija (`CAUSA_RECOMENDACION`):

| Causa | Recomendación |
|---|---|
| `DEFICIT_NOCTURNO` | Ampliar el horario de iluminación de la zona o revisar la potencia de sus luminarias |
| `DEFICIT_DIURNO` | Usar iluminación complementaria en las horas de luz natural baja o revisar la orientación de la ventana |
| `EXCESO_SOLAR` | Aplicar protección solar (cortinas o persianas) en las horas de exceso |
| `EXCESO_ARTIFICIAL` | Reducir la potencia asignada a la zona en las horas de exceso |

La recomendación y la **brecha** (cuánto le falta para 0,90) solo se dan a las zonas **CASI_HABITABLE**. Ejemplo: `TG-H-114` en `deficit_leve` tiene brecha 0,90 − 0,8854 = 0,0146. Las zonas habitables no la necesitan, y para las no habitables el sistema solo da el diagnóstico, sin proponer cambios automáticos. La causa sí se calcula para todas: en el escenario base, `TP-H-101` es habitable y su causa es `EXCESO_SOLAR`.

### 5.6 El puntaje del hotel

El puntaje del hotel es el promedio de los puntajes de las zonas, **ponderado** por la importancia de cada una:

```
peso = prioridad de la actividad × (1 + 0,10 × (piso − 1))
puntaje del hotel = suma de (peso × puntaje) / suma de pesos
```

Las prioridades son 3 para habitaciones y cocinas, 2 para recreaciones y 1 para parqueaderos. Una habitación del piso 1 pesa 3,0 y una del piso 6, 4,5. Este peso no tiene el factor 1,4 de habitación ocupada que usa el balance (paso 3.4).

En el escenario base:

- Los pesos suman 433,4.
- El puntaje ponderado es **0,9718**; el promedio simple sería 0,9738. Baja un poco porque las 52 habitaciones con exceso leve pesan en promedio 3,66, más que el promedio de todas las zonas (3,41).
- El puntaje de día es 0,9436 y el de noche 1,0. Se calculan igual, con los puntajes de día y de noche de cada zona.
- Los puntajes de las 127 zonas son: 75 zonas con 1,0; 3 con 0,9688; 3 con 0,9583; 4 con 0,9479; 16 con 0,9375 y 26 con 0,9271. Todas pasan de 0,90: **127 habitables**.

### 5.7 Veredictos de todos los casos

| Caso | Habitables / casi / no | Puntaje del hotel | Causas |
|---|---|---|---|
| Escenario base | 127 / 0 / 0 | 0,9718 | — |
| `cielo_despejado` | 75 / 52 / 0 | 0,9236 | 52 casi por `EXCESO_SOLAR` |
| `exceso_severo` | 69 / 58 / 0 | 0,9152 | 58 casi por `EXCESO_SOLAR` |
| `deficit_leve` | 115 / 12 / 0 | 0,9621 | 12 casi por `DEFICIT_NOCTURNO` |
| `deficit_severo` | 59 / 0 / 68 | 0,8600 | 68 no por `DEFICIT_NOCTURNO` |
| `luminarias_danadas` | 111 / 0 / 16 | 0,9026 | 16 no por `DEFICIT_NOCTURNO` |
| `apagon_generador` | 0 / 0 / 127 | 0,3569 | 117 no por `DEFICIT_NOCTURNO` y 10 por `DEFICIT_DIURNO` |

El exceso solar, aunque sea severo, nunca vuelve una zona no habitable en estos casos: dura pocas horas y no tiene límite propio. El déficit severo sí, porque basta con hora y media.

### 5.8 El diagnóstico antes del balance

La pestaña «2. Diagnóstico» ejecuta el paso 3 sin repartir energía (paso 3.5, «Análisis sin balance») y luego este mismo paso. De noche todo es `DATOS_INSUFICIENTES`, así que el veredicto solo mira el día, con 24 resultados evaluables por zona. Sirve para ver cómo estaría el hotel solo con luz natural.

En el escenario base da 0 / 26 / 101 y un puntaje de 0,7031:

- `TP-PAR-01` no tiene ventanas: sus 24 resultados de día son déficit severo, puntaje 0 y NO_HABITABLE.
- `TP-COC-01` necesita 300 lux y solo con luz natural tiene 17 pasos en déficit severo: puntaje 0,1458.
- `TP-H-101` queda casi habitable (0,8333): solo tiene 1 paso en déficit severo, a las 6:00, y 1 de 24 es el 4,2 %.

### 5.9 Quién usa los veredictos

- **El paso 6 (reasignación)** solo mueve a los huéspedes de habitaciones ocupadas `NO_HABITABLE`, y solo los manda a habitaciones `HABITABLE` con cama libre. Las casi habitables no se tocan: ni pierden a sus huéspedes ni reciben otros.
- **El plano** pinta cada zona con su veredicto cuando no hay una franja elegida y el selector de color está en «habitabilidad».
- **Las pestañas «2. Diagnóstico» y «4. Balance»** muestran las tarjetas con el conteo y los tres puntajes del hotel, las recomendaciones de hasta 12 zonas casi habitables y el número de zonas no habitables por causa.
- **El resumen de la API** cuenta cuántas zonas casi o no habitables tienen causa de déficit (`zonas_con_deficit`) y cuántas de exceso (`zonas_con_exceso`).

### Resultado y costo del paso

| Operación | Costo |
|---|---|
| Veredicto de una zona | O(T): recorre sus T = 48 resultados unas pocas veces (total, día, noche y causas) |
| Veredictos del hotel | O(Z × T) = O(R), lineal en los 6.096 resultados |
| Puntaje del hotel | O(Z) |

Es un paso lineal y no necesita ninguna estructura especial.

### Ideas clave del paso

- **El puntaje mide tiempo bien iluminado.** Cada media hora confortable suma 1, cada leve suma la mitad y cada severa no suma.
- **El déficit severo tiene un límite propio.** Más del 5 % del tiempo a oscuras (hora y media en una habitación) vuelve la zona no habitable, aunque el puntaje sea bueno.
- **La causa es la etiqueta más frecuente,** salvo en las zonas no habitables por oscuridad, donde se cuenta solo entre las medias horas a oscuras. La recomendación sale de la causa. Solo las casi habitables reciben recomendación, porque son las que pueden pasar a habitables con un cambio pequeño.
- **Las medias horas cerradas no cuentan**, ni a favor ni en contra.
- **Los veredictos son la entrada del paso 6.**

### Historia del cambio

- **La causa no siempre era lo que decidió el veredicto.** Antes la causa era siempre la etiqueta más frecuente, aunque el veredicto viniera de otra. Medias horas de `TP-H-103` en el diagnóstico (solo cuenta el día, 24 medias horas):

  | Horas | Luz | Estado | Etiqueta |
  |---|---|---|---|
  | 6:00 a 7:00 (3) | 0 a 41 lux | DEFICIT_SEVERO | `DEFICIT_DIURNO` |
  | 7:30 a 8:00 (2) | 62 y 82 lux | DEFICIT_LEVE | `DEFICIT_DIURNO` |
  | 8:30 a 14:00 (12) | dentro del rango | CONFORTABLE | — |
  | 14:30 a 17:30 (7) | 302 a 336 lux | EXCESO_LEVE | `EXCESO_SOLAR` |

  Puntaje = (12 + 9 × 0,5) / 24 = 0,6875.

  La habitación es NO_HABITABLE por sus 3 medias horas a oscuras de 6:00 a 7:00 (12,5 %, más del 5 %), y además por su puntaje. Pero su causa salía `EXCESO_SOLAR`, porque tenía 7 medias horas de exceso en la tarde contra 5 de déficit. Lo mismo pasaba con 31 de las 101 zonas no habitables del diagnóstico, y la interfaz las contaba como «exceso solar».

  Ahora, si una zona es no habitable por estar a oscuras más del 5 % del tiempo, la causa se cuenta solo entre esas medias horas. `TP-H-103` pasa a `DEFICIT_DIURNO`, y las 101 no habitables del diagnóstico base tienen causa `DEFICIT_DIURNO`. Ningún veredicto ni puntaje cambia. En `apagon_generador`, 10 zonas pasaron de `DEFICIT_DIURNO` a `DEFICIT_NOCTURNO`, porque sus medias horas a oscuras son de noche. La prueba `test_causa_de_zona_a_oscuras_es_el_deficit` revisa que toda zona con más del 5 % de déficit severo tenga causa de déficit.

  Una zona puede seguir siendo no habitable con causa `EXCESO_SOLAR` si lo es por su puntaje y no por oscuridad. Pasa en el diagnóstico de `cielo_despejado` (16 zonas) y de `exceso_severo` (19): muchas horas de sol fuerte y sin luz artificial.
