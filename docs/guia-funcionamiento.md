# Guía de funcionamiento del sistema

Esta guía recorre, en el orden en que se ejecuta, lo que hace el sistema con los datos: qué parte del código se encarga de cada paso, con qué fin y cómo lo resuelve. Las cifras corresponden al escenario base (`data/datos_hotel.json`).

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
- **Una pared** en el centro, mirando hacia la ventana, con la reflectancia de su color.
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
- orienta la pared al revés (flecha × −1), hacia adentro y de frente a la ventana.

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

### Resultado y costo del paso

Sale un `Hotel` con 127 zonas (104 habitaciones y 23 comunes), 154 ventanas, 127 paredes, 127 luminarias y 78 huéspedes asignados.

**Complejidad: lineal, O(Z + V + G)**, con Z zonas, V ventanas y G huéspedes. Aunque el bucle del edificio tiene tres niveles (torre, piso, habitación), pasa una sola vez por cada habitación y hace con ella un trabajo fijo. Las búsquedas de acabado son en diccionario, en tiempo constante. Con los datos del hotel tarda milisegundos, así que este paso nunca es el cuello de botella.

---

## Paso 2. Preparar el espacio: Octree y grafo de influencia

**Archivos:** `src/simulacion.py` (`_crear_octree`), `src/octree.py` y `src/influencia.py`.

**Fin:** organizar la geometría una sola vez, antes de recorrer el día. Así, en cada media hora, se puede responder rápido:

- si la otra torre tapa el sol de una ventana;
- cuánta luz rebota de las paredes hacia cada ventana.

Este paso no calcula luz. Construye las dos estructuras que los pasos siguientes consultan.

### 2.1 El Octree: dividir el espacio en cajas

**Idea.** Imagina el espacio de las dos torres dentro de una caja grande. Si una caja tiene demasiados objetos, se divide en 8 cajas más pequeñas (mitad de ancho, mitad de fondo y mitad de alto), y cada objeto baja a la caja pequeña que lo contiene. Esto se repite hasta que las cajas tengan pocos objetos. El resultado es un árbol donde cada nodo es una caja y tiene hasta 8 hijos.

**Para qué sirve.** Para preguntar "¿qué objetos hay por aquí?" sin revisar todos. Si una caja completa está lejos o fuera del camino, se descarta con todo lo que tiene adentro, sin mirar sus objetos uno por uno.

**Cómo se construye (`_crear_octree`).**

1. **Qué entra:** las 2 torres, las 154 ventanas (cada una como un cubo de 10 cm), las 127 paredes y las 127 luminarias. Cada objeto entra como una caja con su posición.
2. **Tamaño de la raíz:** se calcula a partir de todos esos objetos, con 2 m de margen. En el escenario va de x = −2 a 91 m, y = −2 a 45 m y z = −2 a 20 m.
3. **Reglas de inserción (`Octree.insertar`):**
   - un nodo admite hasta 16 objetos; cuando se pasa, se divide en 8 hijos y reparte los objetos;
   - un objeto que no cabe completo en un solo hijo se queda en el padre. Así no se duplican objetos grandes, como las torres, que cruzan varias cajas;
   - se divide como máximo hasta 6 niveles de profundidad.

En el escenario base el árbol queda con 97 nodos y 4 niveles. La raíz guarda 44 objetos: las torres y los que quedan justo en las líneas de división.

**Dos tipos de consulta:**

- **`consultar_rayo`:** recibe un rayo, que es un punto de partida y una dirección, y devuelve los objetos cuya caja cruza. Si el rayo no atraviesa la caja de un nodo, descarta ese nodo y todo lo que tiene debajo. Se usa para las sombras (paso 3) y para revisar si hay algo entre una pared y una ventana.
- **`consultar_radio`:** recibe un punto y una distancia, y devuelve los objetos a esa distancia o menos. Si una caja completa queda más lejos que el radio, la descarta. Se usa para construir el grafo.

### 2.2 El grafo de influencia: quién le refleja luz a quién

**Idea.** La luz del sol que pega en una pared rebota y parte de ella llega a ventanas cercanas. El grafo guarda esas relaciones como flechas pared → ventana, y cada flecha (arista) lleva un peso que dice qué fracción de la luz de esa pared llega a esa ventana.

**Cómo se construye (`GrafoInfluencia.construir`).** Para cada una de las 127 paredes:

1. **Candidatas.** Se piden al Octree las ventanas a 18 m o menos (`consultar_radio`).
2. **Se miran.** Para cada ventana candidata se revisa que la pared mire hacia la ventana y que la ventana mire hacia la pared. Es la misma comparación de flechas del paso 1: si alguna da cero o negativa, no hay rebote posible.
3. **Visibilidad.** Se lanza un rayo de la pared a la ventana (`_visible`) y se revisa que ninguna torre esté en medio. Si la pared y la ventana están en la misma torre, esa torre no cuenta como obstáculo: el rayo nace dentro de ella y siempre la cruza, aunque nada le tape el paso.
4. **Peso.** Si pasa los filtros, el peso es:

   ```
   peso = reflectancia × qué tan de frente mira la pared × qué tan de frente mira la ventana / (1 + distancia²)
   ```

   - Una pared blanca (0,80) refleja más que una oscura (0,25).
   - Mirarse de frente cuenta más que mirarse de lado.
   - El peso cae rápido con la distancia: a 1 m vale la mitad que pegado, y a 3 m, la décima parte.
5. **Se guarda** solo si el peso supera 0,0001, porque menos que eso no cambia el resultado.

**Dos índices de las mismas aristas:**

- `adyacencias`: por pared de origen, es decir, qué ventanas ilumina cada pared.
- `entrantes`: por ventana de destino, es decir, qué paredes le llegan a cada ventana.

En cada media hora el sistema necesita la segunda pregunta. Con `entrantes`, cada ventana recorre solo sus propias aristas en vez de todas.

**Primer orden.** La luz que llega a una ventana por el grafo no vuelve a rebotar: las ventanas nunca son origen de aristas. Es una simplificación que mantiene el cálculo simple.

### Resultado y costo del paso

| Medida (escenario base) | Valor |
|---|---|
| Pares pared–ventana si se comparara todo contra todo | 19.558 (127 × 154) |
| Pares que el Octree entrega como candidatos | 5.581 |
| Nodos del Octree visitados para obtenerlos | 6.911 |
| Aristas del grafo | 521 |

**Complejidad.**

- **Construir el Octree:** O(B log B) en el caso típico, con B objetos. Cada objeto baja un nivel por cada división, y hay pocos niveles.
- **Construir el grafo:** con el Octree cuesta O(S × (log B + k)), con S paredes y k candidatas por pared. Sin él costaría O(S × V), comparando cada pared con cada ventana. Por cada candidata que pasa los filtros se hace además una consulta de rayo. El costo depende de cuántas ventanas haya cerca de cada pared, más que del tamaño total del hotel.
- **Usar el grafo en cada media hora:** recorrer las aristas entrantes de todas las ventanas cuesta O(V + E). Es lineal y no se repite la construcción.

Las dos estructuras se arman una vez y se usan en los 48 pasos del día, así que su costo se reparte entre todos ellos.

### Por qué los pares se descartan

De los 5.581 pares candidatos del escenario base, la mayoría se descarta porque la pared y la ventana no se miran: cada pared mira hacia la ventana de su propio recinto, no hacia las demás.

| Motivo | Pares |
|---|---|
| Pared y ventana no se miran | 4.982 |
| Fuera de distancia (0 m o más de 18 m) | 56 |
| Tapados por la otra torre | 0 |
| Peso despreciable (0,0001 o menos) | 22 |
| Se convierten en arista | 521 |

Una versión anterior del código contaba también la torre propia como obstáculo y perdía 468 reflexiones dentro de la misma torre (solo quedaban 73 aristas). Se corrigió para que la regla coincida con la de las sombras del sol, que tampoco cuenta la torre propia.
