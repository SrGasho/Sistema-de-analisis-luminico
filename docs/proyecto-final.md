# Sistema de análisis lumínico de un hotel de dos torres en Bogotá

**Explicación del proyecto final**
Ciencias de la Computación 1 · Docente: Santiago Salazar
Integrantes: Juan David Quiroga Gómez (20222020206) y Maikol Quitian Caicedo (20232020150)

Este documento explica el proyecto como se presentaría al final del curso: qué problema resuelve, cómo lo resuelve el código, qué estructuras de datos usa y por qué, qué decisiones se tomaron en el camino, cómo se validó y qué ve el usuario en la interfaz. Las cifras salen de ejecutar el código sobre el escenario base (`data/datos_hotel.json`) y los casos de `data/casos_prueba/`. El detalle línea por línea está en la [guía de funcionamiento](guia-funcionamiento.md) y las fórmulas con sus fuentes en el [README](../README.md#fuentes-y-fórmulas).

---

## 1. El problema

Un hotel en Bogotá tiene dos torres: la Torre Pequeña (TP, 4 pisos) y la Torre Grande (TG, 6 pisos), separadas por 13 m. Tiene habitaciones, cocinas, salas de juegos y parqueaderos, y un generador de 22 kW para la luz artificial. El sistema responde cuatro preguntas para un día completo:

1. **¿Cuánta luz tiene cada zona en cada media hora?** La que entra del sol y del cielo, la que rebota en la otra torre y en las paredes, y la que pone la luminaria.
2. **¿Alcanza el generador?** Si no alcanza para todo, ¿a quién le da primero?
3. **¿Cada zona es habitable?** Se juzga el día completo de la zona, no una hora suelta.
4. **Si un huésped quedó en una habitación no habitable, ¿a dónde se le puede mover** respetando lo que pidió?

Y además: ¿qué cambios (vidrios, paredes, horarios, generador) mejorarían el hotel?

El proyecto es educativo: modela la física de forma simplificada pero con fórmulas publicadas, y pone el acento en las estructuras de datos que hacen eficiente cada pregunta.

---

## 2. Qué entra al sistema

Todo entra por un archivo JSON. La interfaz lo edita sin que el usuario toque código.

| Sección del JSON | Qué describe | Ejemplo del escenario base |
|---|---|---|
| `hotel` | Identificador y perfil de clima activo | `NUBES_PARCIALES` |
| `torres` | Pisos, habitaciones por piso, ocupadas, zonas comunes, caja en metros, color de fachada | TP: 4 pisos × 8 habitaciones; TG: 6 × 12 |
| `perfiles_iluminacion` | Mínimo, objetivo y máximo de lux, y prioridad, por actividad | Habitación 100 / 200 / 300, prioridad 3 |
| `perfiles_climaticos` | Radiación, nubosidad, precipitación y día del año de cada clima | Febrero: 4,863 kWh/m²/día, día 46 |
| `horarios` | Horas activas y de cierre por actividad | Cocina activa de 6:00 a 22:00 y cerrada de 23:00 a 5:00 |
| `luminarias` | Potencia, eficacia, CU y MF por actividad | Habitación 72 W, 100 lm/W |
| `vidrios`, `paredes`, `acabados` | Transmitancia de cada vidrio, reflectancia de cada pared, y qué usa cada actividad | Vidrio claro 0,82; pared blanca 0,80 |
| `zonas_personalizadas` | Cambios a un recinto puntual: pared, vidrio, orientación, potencia de luminaria (`luminaria_w`) | `TP-H-101: {luminaria_w: 0}` (dañada) |
| `huespedes` y `asignaciones` | Quién duerme dónde y qué pide si hay que moverlo | `H-001: ["MISMA_TORRE"]` |
| `generador` | Capacidad | 22 kW |
| `parametros_evaluacion` | Umbrales, pesos, ubicación (latitud 4,711°), reflectancia del suelo, rangos de la reestructuración | Habitable desde 0,90 |

Con estos datos el sistema arma 127 zonas (104 habitaciones y 23 comunes), 154 ventanas, 8 fachadas, 127 luminarias y 78 huéspedes.

---

## 3. Cómo funciona: el recorrido completo

El sistema hace siete pasos, siempre en el mismo orden.

```
JSON ─▶ 1. Armar el hotel ─▶ 2. Octree + grafo ─▶ 3. Simular 48 medias horas ─▶ 4. Índice rojo-negro
                                                         │                            │
                                                         ▼                            ▼
                                              5. Veredicto por zona  ──▶  6. Reasignación (AVL)
                                                         │
                                                         ▼
                                              7. Sugerencias, mejoras y salida a la interfaz
```

### Paso 1. Armar el hotel (`src/io_datos.py`)

Convierte el JSON en objetos (`src/modelo.py`): torres, pisos, zonas con sus ventanas, superficies interiores y luminarias, fachadas y huéspedes. Completa valores por defecto, valida que todo exista (un vidrio mal escrito detiene la carga) y que ninguna habitación pase de su capacidad. Cada habitación recibe una ventana de 2 m² y una orientación que se alterna (este, norte, oeste, sur). **Costo lineal** en el número de zonas, ventanas y huéspedes.

### Paso 2. Preparar el espacio (`src/octree.py`, `src/influencia.py`)

Se hace **una sola vez** antes del día, porque la geometría no cambia:

- **Octree**: divide el espacio del hotel en cajas de 8 en 8 para responder rápido «¿la otra torre se cruza en la línea entre esta ventana y el sol?» (sombras) y «¿qué fachadas están cerca de esta ventana?».
- **Grafo de influencia**: guarda qué fachada de la otra torre le refleja luz a qué ventana, con un peso (qué fracción le llega), y cuánto cielo le tapa. En el escenario base tiene 46 aristas. Por ejemplo, la cara oeste de TG le devuelve a `TP-H-101` el 35,6 % de su luz y le tapa el 59,3 % del cielo.

Sin el Octree habría que comparar cada ventana con cada fachada (1.232 pares); con él se revisan 68 candidatas.

### Paso 3. Simular el día (`src/simulacion.py`, `src/clima.py`, `src/geometria.py`, `src/balance.py`)

Un bucle de 48 vueltas, una por media hora. En cada vuelta:

1. **El sol.** Su posición real en Bogotá para el día del perfil (declinación de Cooper, ángulo horario, latitud 4,711°). En febrero el sol del mediodía está a 72° hacia el sur; en mayo, a 75,9° hacia el norte.
2. **El cielo.** La luz global sobre el suelo, `G = 900 × factor_luz × sen(altura)`, y la fracción difusa con la correlación de Erbs. A las 12:00 de febrero con nubes parciales: `G` = 589,3 lux, 44,5 % difusa.
3. **Luz natural por ventana.** Directa (si el sol está delante y la otra torre no lo tapa, con Snell y Fresnel en el vidrio) más difusa del cielo visible y del suelo (cielo isotrópico de Liu y Jordan).
4. **Luz reflejada.** La que devuelve la fachada de la otra torre (grafo) más la que rebota en las paredes del cuarto (método de flujo dividido; una pared blanca multiplica por 4 y una oscura por 0,33).
5. **Balance del generador.** Decide el modo de cada zona por horario (activa, reducida al 30 %, cerrada) y reparte los 22 kW en tres rondas: primero 10 lux de emergencia a todas, luego los mínimos (parqueaderos primero por seguridad, después habitaciones ocupadas), y por último los objetivos con una cola de prioridad (`heapq`).
6. **Luz artificial, total y estado.** Convierte vatios en lux con el método de lúmenes (2,33 lux/W en una habitación), suma todo y compara con el mínimo y el máximo: confortable, déficit o exceso, leve o severo.

Sale **6.096 resultados** (127 zonas × 48 medias horas). **Costo por media hora**: O(V(log B + k)) para las sombras, O(V + E) para la reflejada y O(Z log Z) para el balance.

### Paso 4. Índice por hora con el árbol rojo-negro (`src/temporal.py`, `src/arboles.py`)

Cada resultado se inserta, apenas se calcula, en un árbol rojo-negro con clave `(hora, zona)`. Al final, el sistema le pide al árbol los resultados de 6 franjas (día completo, madrugada, mañana, tarde, noche, cierre) y arma un reporte de cada una: energía, pico del generador, déficit, zonas críticas y estado predominante de cada zona.

### Paso 5. Veredicto de habitabilidad (`src/habitabilidad.py`)

Cada media hora recibe una nota: 1 si fue confortable, 0,5 si fue leve y 0 si fue severa. El **puntaje** es el promedio. Con él:

```
0 ─────────── 0,75 ─────────── 0,90 ─────────── 1
  NO_HABITABLE    CASI_HABITABLE     HABITABLE
```

Además, si la zona estuvo **a oscuras** (déficit severo) más del 5 % del tiempo, es no habitable aunque su puntaje sea alto: en una habitación eso es hora y media. Se reporta la **causa** (el problema que más se repitió) y, para las casi habitables, una recomendación y la brecha hasta 0,90. El puntaje del hotel es el promedio ponderado por prioridad y piso.

### Paso 6. Reasignación de huéspedes con el árbol AVL (`src/reasignacion.py`)

Solo se mueve a quien quedó en una habitación no habitable. Las habitaciones habitables con cama libre entran a un AVL ordenado por (torre, piso, mejor calidad primero). Para cada huésped se consultan los pisos que permiten sus restricciones (`MISMA_TORRE`, `PISO_MAXIMO:n`), se toma la mejor de cada piso, y gana la de mayor score: calidad de luz y ahorro, más un premio si coincide la orientación pedida, menos una penalización por alejarlo de su piso. Cuando una habitación se llena, sale del árbol. Si no hay opción, se explica por qué: no había habitaciones, se llenaron o sus restricciones lo impiden.

### Paso 7. Sugerencias, mejoras y salida (`src/sugerencias.py`, `src/mejoras.py`, `src/reestructuracion.py`, `src/api.py`)

- **Sugerencias**: reglas que leen los veredictos y el generador y proponen acciones (controlar el sol, revisar luminarias, ampliar el generador, mover huéspedes).
- **Mejoras medidas**: mira las zonas casi o no habitables y prueba un cambio por cada tipo de problema: vidrio de control solar donde sobra sol, reponer luminarias débiles o dañadas, un generador más grande si alguna zona quedó en emergencia, y vidrio claro o paredes blancas donde falta luz de día. Cada cambio es una simulación completa y solo se muestran los que suben el puntaje. Si todo es habitable, dice que no hace falta ninguna mejora.
- **Reestructuración**: una búsqueda local (*hill climbing*) que prueba un cambio a la vez sobre las actividades con problemas (pared, vidrio, orientaciones y, en cocina y sala de juegos, horarios), acepta el primero que mejora y repite, con un tope de 30 simulaciones. No toca los objetivos de lux.
- **API**: un servidor HTTP de la biblioteca estándar (`python3 -m src.api`) que entrega todo como JSON a la interfaz web.

---

## 4. Estructuras de datos: cuál, para qué y cuánto ahorra

| Estructura | Para qué | Por qué esa | Medido en el escenario base |
|---|---|---|---|
| **Octree** | Sombras (consulta de rayo) y fachadas cercanas (consulta de radio) | Descarta cajas completas del espacio sin mirar su contenido | 418 objetos, 4 niveles. Grafo: 68 candidatas en vez de 1.232 pares |
| **Grafo de influencia** (listas de adyacencia en dos sentidos) | Reflexión entre torres y cielo tapado | Los pesos se calculan una vez y se reusan en las 48 medias horas | 46 aristas, 40 ventanas con cielo tapado |
| **Cola de prioridad** (`heapq`) | Repartir los objetivos del generador por prioridad | Saca siempre la zona más prioritaria en O(log Z) | O(Z log Z) por media hora |
| **Árbol rojo-negro** | Índice de los 6.096 resultados por hora para consultar franjas | Los resultados llegan casi ordenados; un árbol sin balancear degeneraría | Altura 22 (sin balancear sería 686); 111.161 comparaciones para insertar todo (sin balancear: 2.030.952); una media hora se consulta visitando 136 nodos en vez de 6.096 |
| **Árbol AVL** | Bolsa de habitaciones libres para la reasignación | El trabajo es casi todo lectura (buscar la mejor de un piso) y el AVL es más bajo | 104 habitaciones, altura 8. En `reasignacion_restringida`: 752 comparaciones contra 2.496 de revisar todas |

El AVL también se construye con los mismos 6.096 resultados para comparar con el rojo-negro: queda con altura 14 y 7.779 rotaciones, contra 22 y 7.960 del rojo-negro.

---

## 5. Modelo físico y de dónde sale cada número

El README tiene la tabla completa con referencias. En resumen:

| Qué | Tipo | Fuente |
|---|---|---|
| Clima de Bogotá (radiación, nubosidad, precipitación) | Dato real | NASA POWER 2001–2020 |
| Posición del sol, radiación extraterrestre | Fórmula publicada | Cooper (1969); Duffie y Beckman (2013) |
| Fracción difusa | Fórmula publicada | Erbs, Klein y Duffie (1982) |
| Luz sobre superficies verticales | Fórmula publicada | Liu y Jordan (1960); factor Rb de Duffie y Beckman |
| Vidrio según el ángulo | Fórmula publicada | Snell y Fresnel (Hecht, *Optics*) |
| Reflexión dentro del cuarto | Fórmula publicada | Método de flujo dividido (Hopkinson et al., 1966) |
| Luz artificial | Fórmula publicada | Método de lúmenes (IES) |
| Transmitancia de los vidrios | Dato real | Fichas de Cardinal Glass |
| Niveles de lux por actividad | Supuesto contrastado | RETILAP |
| Sala de juegos: 200 / 300 / 500 lux | Supuesto contrastado | 300 lux para zonas de juegos y salas deportivas (EN 12464-1); 200 lux para juegos recreativos como el tenis de mesa. No se pudo verificar el valor del RETILAP para este espacio |
| 900 lux de referencia, umbrales 0,75 / 0,90, pesos, factor de vista | Supuestos del proyecto | — |

---

## 6. Decisiones tomadas durante el proyecto

Al revisar el código paso a paso aparecieron errores y simplificaciones que cambiaban los resultados. Estas son las decisiones que se tomaron:

| Decisión | Qué estaba mal o faltaba | Qué se hizo | Efecto |
|---|---|---|---|
| **D11 y R28** | Las habitaciones quedaban mal ubicadas dentro de su torre | Se reparten en una cuadrícula por piso | Sombras y reflexiones coherentes con el plano |
| **D13** | La reflectancia de la pared se aplicaba dos veces | Se aplica una sola vez | Reflejada más baja y realista |
| **D15** | El grafo unía cuartos de la misma torre, como si la luz atravesara paredes | El grafo va de una fachada a las ventanas de la **otra** torre, con factor de vista y cielo tapado; la reflexión dentro del cuarto se calcula aparte con el método de flujo dividido | La reflexión exterior solo existe donde hay una torre enfrente |
| **Limitación aceptada** | El vidrio de las ventanas también refleja luz hacia afuera | No se modela; las fachadas son superficies opacas de un color | Queda documentada en la guía |
| **D16** | El sol era inventado: giraba por el norte a 35° fijos, y las fracciones directa y difusa no sumaban 1; un día nublado salía más claro que uno despejado | Sol real de Bogotá por fecha, correlación de Erbs y cielo isotrópico de Liu y Jordan, con fuentes en el README | Las ventanas al norte ya no tienen sol en febrero; despejado (534.973) > nubes (396.651) > nublado (385.199) > lluvioso (370.265) en luz natural del día |
| **Balance** | Cada entrega del generador volvía a sumar todo lo repartido: O(Z²) | La clase `Reparto` lleva el total acumulado | O(Z log Z), mismos resultados. No tiene relación con los árboles |
| **`luminaria_w`** | Con el sol real, el exceso de luz nunca deja una habitación no habitable, así que no había forma realista de probar la reasignación | Campo por recinto para la potencia de la luminaria; 0 = dañada | Casos `luminarias_danadas` y `reasignacion_restringida` |
| **D17** | El redondeo al convertir vatios a lux dejaba zonas 0,00000000000001 lux bajo el mínimo y las marcaba en déficit; la energía no asignada contaba vatios que la luminaria no podía dar | Tolerancia de 0,000000001 lux al clasificar; la energía no asignada no pasa de la potencia de la luminaria | `deficit_leve` pasó a ser un caso de luminarias viejas de 30 W (115/12/0); `deficit_severo` pasó de 3/56/68 a 59/0/68 |
| **Causa de una zona a oscuras** | Una zona no habitable por oscuridad podía salir con causa «exceso solar» | Si la zona es no habitable por más del 5 % a oscuras, la causa se cuenta solo entre esas medias horas | Las 101 no habitables del diagnóstico base tienen causa de déficit |
| **Gráfico del día** | No se podía ver cómo le fue a una zona hora por hora | Gráfico de barras debajo del plano con la escala de habitabilidad | Ver sección 7 |
| **Caso `mayo_nublado`** | No había un caso con el sol por el norte | Mayo nublado: las habitaciones al sur gastan más que las del norte, al revés de febrero | Muestra que la fecha importa |
| **Mejoras según el problema** | Las mejoras eran cuatro cambios fijos que casi nunca cambiaban nada | Cada mejora sale de un problema del caso (sol de más, luminaria débil, generador corto, falta de luz de día) y solo se muestra si sube el puntaje | En todos los casos con problemas hay una mejora que deja las 127 zonas habitables |
| **Estado del generador** | Quedaba en «capacidad limitada» con cualquier déficit, aunque sobrara energía, y las sugerencias pedían un generador más grande | Solo es «capacidad limitada» si alguna zona entró en emergencia o se pasó la capacidad | `deficit_leve` y `luminarias_danadas` quedan en operación normal |
| **Reestructuración sin objetivos** | Bajaba el objetivo de lux al mínimo solo para ahorrar energía, porque el puntaje no depende del objetivo | Ya no prueba objetivos | Las propuestas cambian acabados, orientaciones u horarios |
| **Revisión de la interfaz** | Recomendaciones repetidas, criterios técnicos al final, leyendas pequeñas abajo, «Aplicar» sin simular, la noche sin explicar en el gráfico | Ayuda de lectura al inicio del Diagnóstico, zonas clicables que abren el plano, leyendas arriba, «Aplicar y simular», puntaje por franja, botón de balance en las pestañas vacías, tablas técnicas plegables | Ver sección 7 |

---

## 7. La salida: qué ve el usuario y qué significa

La aplicación web (`python3 -m src.api`, luego abrir `http://127.0.0.1:8000`) tiene seis pestañas que siguen el orden del trabajo: **configurar → ver el diagnóstico → ver el plano → balancear → buscar mejoras → revisar el detalle técnico**. Hay modo oscuro y claro (botón arriba a la derecha; la elección se recuerda).

### Flujo de uso

1. Al abrir, se carga el escenario base y se calcula la condición actual **sin balance**.
2. **«Cargar escenario»** recalcula la condición actual con lo que haya en los formularios y lleva a la pestaña Diagnóstico.
3. **«Balancear energía»** valida las entradas, ejecuta el día completo con el generador y lleva a la pestaña Balance. En segundo plano mide las mejoras.
4. Si se edita cualquier campo, el estado dice «Cambios pendientes de analizar»: los resultados que se ven son de la configuración anterior hasta volver a cargar o balancear.

### Pestaña 1. Configurar

**Qué quiere mostrar:** que todo el escenario es un dato que el usuario puede cambiar sin programar.

- **Escenario general:** perfil de clima (los cuatro perfiles de Bogotá) y capacidad del generador.
- **Torres:** pisos, habitaciones por piso y habitaciones ocupadas.
- **Perfiles de actividad:** mínimo, objetivo y máximo de lux, y potencia de la luminaria de cada actividad.
- **Horarios:** horas activas y de cierre. Fuera del horario activo la zona pide el 30 % de la luz; en el cierre no consume.
- **Vidrios y paredes:** transmitancia de cada vidrio, reflectancia de cada pared, y qué pared, vidrio y orientaciones usa cada actividad.
- **Botones:** descargar o cargar la configuración como JSON (así se usan los casos de prueba), cargar escenario y balancear.

Cada campo tiene un ícono «!» con la explicación.

### Pestaña 2. Diagnóstico

**Qué quiere mostrar:** cómo estaría el hotel **solo con luz natural**, antes de repartir energía. Es un diagnóstico provisional: la noche no se evalúa porque sin luz artificial siempre estaría a oscuras.

- **Tarjetas:** zonas analizadas, zonas con déficit y con exceso (entre las casi y no habitables).
- **Habitabilidad por zona:** cuántas zonas son habitables, casi y no habitables, y los puntajes del hotel (ponderado, de día y de noche). En el escenario base: 0 / 26 / 101 y 70,3 %. Es lo esperado: los parqueaderos no tienen ventanas y las cocinas necesitan 300 lux.
- **No habitables por causa:** cuántas hay según su problema principal, en palabras (por ejemplo, «Falta luz de día: 99 zonas»). Solo aparece si hay alguna.
- **Cómo leer los resultados** (arriba de todo, se abre con un clic): qué significa cada estado, cuántos puntos vale, la escala 75 % / 90 %, la regla del 5 % a oscuras y los lux de cada actividad.
- **Sugerencias:** tarjetas con prioridad (crítica, alta, media, informativa), diagnóstico, acción y zonas afectadas. La de casi habitables lista hasta 12 zonas con su puntaje, lo que les falta para 90 % y su recomendación. **Cada zona es un enlace**: al hacer clic se abre el Plano con esa torre, ese piso y esa zona seleccionados.

### Pestaña 3. Plano

**Qué quiere mostrar:** dónde están los problemas en el edificio y cómo le fue a cada zona durante el día.

**Leyendas** (arriba del plano, grandes): las tres capas de color (separación de espacios, habitabilidad del día y confort lumínico, con «sin datos»), con la capa que se está viendo marcada, y las abreviaturas TP = Torre Pequeña y TG = Torre Grande.

**Selectores:**

| Selector | Qué hace |
|---|---|
| Torre y Piso | Elige la planta a dibujar. En el piso 1 aparecen las zonas comunes |
| Franja horaria | «Veredicto del día» o una de las 6 franjas. Con una franja, cada zona se pinta con su estado predominante en ese rango de horas (consulta al rojo-negro) |
| Vista | «Antes del balance (provisional)» o «Después del balance» |
| Capa de color | **Habitabilidad** (veredicto del día), **Separación de espacios** (un color por actividad) o **Confort lumínico** (estado predominante: confortable, déficit o exceso) |

**El dibujo** es un plano tipo CAD: grilla, ejes, cotas reales de la torre, pasillo, escaleras y ascensores, rótulo y rosa de los vientos. Cada habitación tiene cama, baño, puerta y una línea de ventana en la fachada, su identificador y una etiqueta de color con su luz promedio en lux. Las cocinas, salas de juegos y parqueaderos tienen su propio mobiliario.

**Colores:**

| Color | Significado |
|---|---|
| Verde | Habitable o confortable |
| Ámbar | Casi habitable |
| Rojo | No habitable, o exceso de luz (claro si es leve, intenso si es severo) |
| Azul | Déficit de luz (claro si es leve, intenso si es severo) |
| Gris o rayado | Sin datos: la zona estuvo cerrada |

**Detalle de la zona** (al hacer clic): ubicación, uso, estado, luz promedio, modo, veredicto, puntaje y recomendación. Debajo hay un formulario para cambiar la pared, el vidrio y la orientación **de ese recinto** sin tocar el resto de su actividad. El botón **«Aplicar y simular»** guarda el cambio, vuelve a calcular el día y el balance, y deja el plano en la misma zona con su gráfico actualizado; las pestañas Diagnóstico y Balance también quedan al día.

**Reporte de la franja** (si se eligió una): energía, pico del generador, déficit residual en lux·h, energía no asignada, horas con déficit, energía por actividad y por torre, zonas críticas y cuántos nodos visitó el rojo-negro contra los 6.096 de una lista.

**Gráfico «Cómo le fue en el día»** (debajo de todo, a todo el ancho), para la zona elegida:

- **Arriba, la escala** de 0 a 1 en tres tramos (rojo: no habitable; ámbar: casi; verde: habitable) y un triángulo en el puntaje de la zona.
- **Abajo, una barra por media hora.** Su altura es la nota (1, 0,5 o 0) y su color, el estado. La línea punteada es el puntaje, que es el promedio de las barras. El fondo oscuro marca la noche y una franja de color bajo las barras repite el estado, incluso cuando la nota es 0 o la zona está cerrada.
- **Al pasar el mouse** por una barra se ve la hora, el modo, la luz natural, reflejada y artificial, el total y el mínimo y máximo de ese momento.
- **Puntaje por franja:** sobre las barras, una tarjeta para madrugada, mañana, tarde, noche y cierre, con su puntaje y su tramo. En la vista «antes del balance» la noche dice «se evalúa después del balance», y un aviso explica por qué: sin luminarias la noche siempre estaría a oscuras.
- **Un texto** cuenta cuántas medias horas estuvo a oscuras, porque más del 5 % la vuelve no habitable.

Ejemplo, `TG-H-113` en `deficit_leve`: barras verdes de madrugada, rojas claras de 6:30 a 9:30 (el sol de la mañana entra por su ventana al este), verdes a mediodía, azules claras de 18:00 a 21:30 (su luminaria de 30 W solo da 70 lux) y el triángulo en 82,3 %, en el tramo ámbar. Se lee de un vistazo que el problema es la luminaria de noche.

### Pestaña 4. Balance

**Qué quiere mostrar:** el resultado con el generador repartiendo energía.

Antes del primer balance esta pestaña (y también Mejoras y Detalle técnico) muestra un botón **«Balancear energía ahora»**.

- **Tarjetas:** zonas evaluadas, resultados (6.096), zonas con déficit, con exceso y reasignaciones.
- **Estado del generador:** una barra con el porcentaje de la capacidad que usó en su peor media hora, la capacidad, la demanda máxima y la reserva. Verde es operación normal, ámbar es alta demanda (más del 80 %) y rojo es capacidad limitada. En el escenario base: 15.934 W de 22.000 (72,4 %), operación normal.
- **Antes y después del balance:** el puntaje provisional contra el del balance (70,3 % → 97,2 % en el escenario base), y tablas con cuántas zonas hay de cada veredicto y cuántas medias horas de cada estado, antes y después, con la diferencia.
- **Habitabilidad por zona y sugerencias**, igual que en Diagnóstico pero con el balance.
- **Reasignaciones de huéspedes:** una tarjeta por huésped con su habitación actual, la propuesta y su score, sus restricciones y las habitaciones descartadas; o el motivo si no hay alternativa.
- **Descargas:** el resultado completo en JSON y un CSV con los 6.096 resultados (zona, hora, periodo, modo, luz natural, reflejada, artificial, total, vatios y estado).

### Pestaña 5. Mejoras

**Qué quiere mostrar:** qué cambios ayudarían, medidos con simulaciones y no estimados.

- **Mejoras medidas:** cambios que salen de los problemas del caso, cada uno medido con una simulación. Cada tarjeta dice qué cambia, el puntaje antes y después, cuántas zonas quedan habitables, casi y no habitables, y en qué zonas (enlaces al plano). En el escenario base dice «Todas las zonas son habitables: no hace falta ninguna mejora». Ejemplos: en `cielo_despejado`, vidrio de control solar en 52 zonas (92,4 % → 96,0 %, 127 habitables); en `deficit_leve`, reponer 12 luminarias (127 habitables); en `deficit_severo`, un generador más grande (+11,2 puntos, 127 habitables).
- **Reestructuración:** un botón lanza la búsqueda (hasta 30 simulaciones) y el texto explica qué prueba: solo las actividades con zonas casi o no habitables, un cambio a la vez (pared, vidrio, orientaciones y, en cocina y sala de juegos, horarios). Muestra puntaje, casi y no habitables, y energía, antes y después; la lista de cambios aceptados en orden; y un botón para cargar la propuesta en los formularios y balancear de nuevo. En `cielo_despejado` encuentra, en 7 simulaciones, vidrio de control solar para las habitaciones y ventanas solo al norte y al sur: las 52 casi habitables pasan a habitables (92,4 % → 99,8 %), aunque la energía sube de 193.038 a 220.190 Wh porque entra menos sol. En `deficit_leve` no alcanza a resolverlo (quedan 11 casi habitables): el problema son las luminarias, que la búsqueda no cambia; ahí la mejora medida sí lo resuelve.

### Pestaña 6. Detalle técnico

**Qué quiere mostrar:** que las estructuras de datos ahorran trabajo, con conteos reales.

Las tablas están **plegadas**: cada una muestra un título y una frase, y al abrirla trae una explicación en palabras sencillas.

- **Cuánto trabajo ahorran las estructuras de datos:** cuánto costaría sin cada estructura y cuánto contó el programa: Octree (1.232 pares contra 68), rojo-negro para traer la noche (6.096 contra 1.030 nodos) y AVL para la reasignación; y la altura del rojo-negro contra la del AVL con los mismos resultados.
- **Estados de todas las medias horas** y **resumen por zona** (luz promedio y máxima, medias horas en déficit y en confort, energía).
- Los criterios de confort que antes estaban aquí pasaron a «Cómo leer los resultados», al inicio del Diagnóstico, escritos en lenguaje sencillo.

---

## 8. Cómo se validó

`python3 -m unittest` ejecuta **26 pruebas** en unos 12 segundos.

- `tests/test_casos_plan.py`: los 10 casos del plan del proyecto (ventana al sol, ventana sombreada, cada vidrio, reflexión, noche, generador que alcanza para mínimos pero no para objetivos, reasignación con y sin alternativa, zona cerrada, nublado contra despejado).
- `tests/test_casos_json.py`: el escenario base y los 10 casos de `data/casos_prueba/`. Cada caso trae su historia y su resultado esperado, y la prueba revisa que coincidan. Además revisa reglas comunes: de noche no hay luz natural, una zona cerrada no consume, el generador no se pasa de su capacidad, nadie recibe una cama que no existe, ningún déficit sale de un redondeo, toda zona a oscuras tiene causa de déficit, y las sugerencias y mejoras corresponden al problema de cada caso.

**Los casos de prueba** (habitables / casi / no habitables):

| Caso | Qué cuenta | Resultado |
|---|---|---|
| Escenario base | Febrero, nubes parciales, generador de 22 kW | 127 / 0 / 0 |
| `temporada_lluvias` | Abril, cielo cubierto | 127 / 0 / 0; más energía por menos luz natural |
| `mayo_nublado` | Mayo, el sol pasa por el norte | 127 / 0 / 0; las habitaciones al sur gastan más que las del norte |
| `generador_alta_demanda` | Generador de 17 kW | 127 / 0 / 0; el generador queda en alta demanda |
| `cielo_despejado` | Febrero despejado | 75 / 52 / 0; exceso solar de mañana o de tarde |
| `exceso_severo` | 24 habitaciones de TP con ventana al este y cielo despejado | 69 / 58 / 0; exceso severo de 6:30 a 10:00 |
| `deficit_leve` | 12 habitaciones con luminarias viejas de 30 W | 115 / 12 / 0; déficit nocturno leve |
| `deficit_severo` | Generador de 4 kW | 59 / 0 / 68; 22 huéspedes reasignados |
| `luminarias_danadas` | 16 habitaciones sin luminaria; tres huéspedes con pedidos | 111 / 0 / 16; los 16 se mueven respetando sus pedidos |
| `reasignacion_restringida` | 24 habitaciones sin luminaria y un grupo que no quiere cambiar de torre | 103 / 0 / 24; 20 se mueven, 2 sin capacidad, 2 por restricciones |
| `apagon_generador` | Generador en 0 | 0 / 0 / 127; nadie tiene a dónde ir |

Cada caso se puede cargar en la interfaz con «Cargar configuración JSON».

---

## 9. Resultados del escenario base

| Medida | Valor |
|---|---|
| Veredictos | 127 habitables |
| Puntaje del hotel | 97,18 % (día 94,36 %, noche 100 %) |
| Estados de los 6.096 resultados | 5.517 confortables, 319 en exceso leve, 260 cerrados |
| Energía del día | 208,08 kWh |
| Pico del generador | 15.934 W a las 18:00 (72,4 % de la capacidad) |
| Habitaciones con exceso leve | 52: las 26 al este entre 6:30 y 9:30 y las 26 al oeste entre 14:30 y 17:30 |
| Diagnóstico sin balance | 0 / 26 / 101, puntaje 70,3 % |

---

## 10. Limitaciones y trabajo futuro

**Del modelo físico**

- El vidrio de las ventanas no refleja luz hacia la otra torre, y la reflexión exterior es de un solo rebote.
- Las ventanas están cerca del centro de su cuarto; para la reflexión exterior se usa su punto en la fachada, pero las sombras se calculan desde la ventana. Por eso `TP-H-101` recibe el sol de las 7:00 aunque la Torre Grande esté enfrente.
- La hora es hora solar, sin corrección a la hora del reloj.
- El exceso de luz no tiene un límite propio como el de la oscuridad: nunca vuelve una zona no habitable en estos casos.

**De las decisiones del sistema**

- **El ahorro de energía casi no pesa en la reasignación.** Se divide por la energía de un parqueadero (17.280 Wh), mientras las habitaciones gastan entre 617 y 968 Wh. El término cambia solo 0,004 entre habitaciones.
- **La reasignación es voraz:** el orden de los huéspedes decide quién se queda sin cama.
- **Las sugerencias** no se verifican con simulación; lo que sí se mide está en Mejoras.
- **Las mejoras** prueban un cambio por tipo de problema, no combinaciones.
- **La reestructuración** cambia acabados por actividad, no por recinto, y no toca las luminarias.

**De la interfaz**

- En la capa «Habitabilidad», el veredicto colorea la etiqueta de cada recinto y el panel de detalle, pero no el relleno del recinto en el plano.
- El rótulo del plano dice «Sinergia cromática» y «Confort lumínico» aunque el selector y la leyenda ya usan «Separación de espacios» y «Habitabilidad»: el rótulo es parte del dibujo y no se tocó.
- `luminaria_w` solo se edita en el JSON, no desde el formulario del recinto.
- Las áreas que muestra el plano (24, 35, 80 y 450 m²) son texto fijo.

---

## 11. Cómo ejecutarlo

```bash
python3 -m unittest                 # 26 pruebas
python3 -m src.main                 # simulación por línea de comandos
python3 -m src.api                  # aplicación web en http://127.0.0.1:8000
```

No necesita instalar nada: solo Python 3 y la biblioteca estándar.

---