# Revisión del Entregable 2 y plan para AVL y rojo-negro

Estado: **decisiones tomadas; plan pendiente de confirmación**. No se ha cambiado código a partir de este documento.

## Cómo usar este documento

- Cada hallazgo tiene un código (`R1`, `R2`…) y cada decisión pendiente otro (`D1`, `D2`…).
- Responde en el chat citando los códigos. Por ejemplo: "D2 opción A, D6 sí, R10 dejarlo así".
- Con tus respuestas actualizo la sección **Decisiones tomadas** y después ejecuto solo las tareas aprobadas del **Plan**.
- Si algo no está en este documento, no se hace sin preguntarte primero.

## Fuentes revisadas

Todos los documentos están copiados en esta carpeta (`docs/temporal/`). Desde ahora, la copia de esta carpeta es la referencia.

| Documento | Archivo |
|---|---|
| Propuesta de simulación | `entregable-propuesta-simulacion-luminica.md` |
| Arquitectura | `architecture-proyecto-cc1-iluminacion.md` |
| Plan del proyecto | `plan-proyecto-cc1-iluminacion.md` |
| Entregable LaTeX | `entregable-arquitectura-iluminacion.tex` |
| Diagrama de clases (Mermaid) | `diagrama-clases-hotel.mmd` |
| Enunciado del Entregable 2 | No existe un enunciado oficial (`D1`). El Entregable 2 pedía el código completo sin el balanceo; esta entrega cubre todo, balance incluido. La referencia son los documentos de esta carpeta. |
| Código revisado | Este repositorio, `main` en `09906de` |

## 1. Revisión de cumplimiento

Estados: **Cumple**, **Parcial**, **No cumple**, **Conflicto** (el documento y lo que pediste después se contradicen).

### 1.1 Datos reales

| Código | Compromiso en los documentos | Estado | Evidencia |
|---|---|---|---|
| R1 | Clima de Bogotá con NASA POWER 2001–2020 | **Parcial** | Los valores del JSON coinciden exactamente con la API de NASA POWER (consultada hoy): febrero 4,8635 kWh/m²/día y 70,89 % de nubosidad; mayo 4,4764 y 85,82 %; abril 4,4541 y 84,87 %; cielo despejado anual 7,0635. **Pero la radiación no se usa en el cálculo.** La luz base sale de `factor_luz` (0,85, 0,60, 0,50, 1,00), que es un número inventado. Prueba: cambiar `radiacion` a 99 no cambia ningún resultado. El LaTeX promete `E_base = K_lux · I_clima · C(t)` y el código calcula `K_lux · C(t) · factor_luz`. |
| R2 | Nubosidad en la luz directa y difusa | **Cumple** | `f_directa = max(0,10; 1 − c)` y `f_difusa = 0,15 + 0,45c` usan la nubosidad real de NASA. |
| R3 | Precipitación en los perfiles | **Cumple (informativo)** | Se carga y se reporta. Los documentos no prometen usarla en el cálculo. |
| R4 | Áreas DOE (4.013 m² y 11.346 m²), VLT de Cardinal Glass, reflectancias, luminarias | **Cumple** | Coinciden con el JSON. Las áreas de referencia se cargan, pero no entran en ningún cálculo. |
| R5 | Generador = 1,20 × demanda objetivo máxima | **Cumple** | La demanda objetivo máxima medida es 18.110,7 W. Por 1,20 da 21,73 kW, redondeado a los 22 kW del JSON. |

Con la opción A de `D2`, el escenario base pasa de 101 a 127 zonas habitables (puntaje 0,9346 → 0,9829) y la energía de 192.884 Wh a 207.217 Wh. En ese caso el escenario base ya no tiene zonas casi habitables, y para mostrar las recomendaciones habría que usar `data/casos_prueba/deficit_leve.json`.

### 1.2 Modelo físico

| Código | Compromiso | Estado | Evidencia |
|---|---|---|---|
| R6 | Refracción con la ley de Snell (índice 1,5) | **No cumple** | `indice_refraccion` se carga en `Vidrio`, pero ningún cálculo lo usa. No hay Snell en el código. Los cuatro documentos lo prometen. |
| R7 | Noche con luz natural y reflejada solar en cero | **Cumple** | `luz_base` devuelve 0 fuera de 06:00–18:00. |
| R8 | Reflexión de primer orden, sin cascada | **Cumple** | La luz reflejada no vuelve a ser origen. |
| R9 | Modos `ACTIVA`, `REDUCIDA`, `CERRADA` y `EMERGENCIA` | **Parcial** | En una simulación solo aparecen `ACTIVA` (4.092 pasos) y `REDUCIDA` (2.004). `CERRADA` y `EMERGENCIA` existen en el enum, pero nunca se asignan. El caso de prueba 9 ("zona cerrada") no se puede ejecutar. |
| R10 | Balance: primero mínimos de seguridad, luego habitaciones ocupadas | **Parcial** | Las habitaciones ocupadas sí van primero. No existe una categoría de "mínimos de seguridad" (parqueadero, emergencia) distinta del resto. |

### 1.3 Estructuras y complejidad

| Código | Compromiso | Estado | Evidencia |
|---|---|---|---|
| R11 | Octree para sombras; objetos que cruzan octantes se quedan en el padre | **Cumple** | `octree.py` y `_sombreada` en `simulacion.py`. |
| R12 | Grafo construido con consultas espaciales, sin comparar todos los pares (`O(S log S + E)`) | **No cumple** | `GrafoInfluencia.construir` compara las 127 superficies con las 154 ventanas (19.558 pares) y filtra por distancia. `Octree.consultar_radio` existe, pero nadie lo llama. Además, `reflejada_para` recorre todas las aristas para cada ventana en cada paso. |
| R13 | Objetivo: comparar la complejidad de búsquedas ingenuas y espaciales | **No cumple** | No hay medición ni reporte de comparaciones. |
| R14 | Árbol jerárquico y agregación `O(N)` | **Cumple** | `agregar_energia_postorden` en `balance.py`. |
| R15 | AVL y rojo-negro (pedido tuyo en el chat, no está en los documentos) | **Parcial** | Ver sección 2. El rojo-negro se llena pero nunca se consulta. El AVL hace una sola consulta que un filtro de lista resuelve igual. La consulta incluye el límite superior: una zona con puntaje exacto 0,90 sale como casi habitable, aunque la regla dice que es habitable. |

### 1.4 Salidas

| Código | Salida prometida | Estado |
|---|---|---|
| R16 | Por zona e instante: hora, periodo, modo, luz natural, reflejada, artificial, total, potencia y estado | **Cumple** |
| R17 | Puntaje diurno y nocturno, potencia máxima, energía en Wh | **Cumple** |
| R18 | Energía en kWh, déficit residual, energía no asignada, consumo por actividad, comparación entre torres, zonas críticas, horas con déficit | **No cumple**. Hoy solo hay energía por torre y piso. |
| R19 | Reasignación: candidatos descartados y "falta de capacidad" | **Parcial**. Se reporta `NO_HAY_ALTERNATIVA`, pero no qué candidatos se descartaron ni por qué. |

### 1.5 Reasignación de huéspedes

| Código | Hallazgo | Estado |
|---|---|---|
| R20 | Los documentos piden reasignar cuando una habitación ocupada "queda por debajo del mínimo". El código solo reasigna si la zona es `NO_HABITABLE`. | **Parcial** |
| R21 | El código no descuenta la capacidad de la habitación propuesta. Dos huéspedes podrían recibir la misma habitación con una sola cama libre. En los seis casos de prueba no ocurrió, pero el código no lo impide. | **Parcial** |
| R22 | `restricciones` del huésped se carga y no se usa. `w_actividad` multiplica siempre 1,0, así que no distingue nada. | **Parcial** |

### 1.6 Coherencia entre documentos y código

| Código | Hallazgo | Estado |
|---|---|---|
| R23 | Los documentos usan IDs `TP-H-101` y `TG-H-101`. El código usa `TorrePequena-H-101`. | Diferencia menor |
| R24 | Arquitectura 2.4 ("el sistema no modifica torres, ventanas ni paredes") y Plan 5.2 ("no incluye optimización") chocan con las mejoras medidas y la reestructuración que pediste. | **Conflicto** |
| R25 | Ningún documento ni el diagrama de clases menciona: veredicto de habitabilidad por zona, AVL, rojo-negro, mejoras medidas, reestructuración ni la interfaz web. | Documentos desactualizados |
| R26 | Los 10 casos de prueba del Plan (sombra, Snell, reflexión, noche, generador, reasignación con y sin candidata, zona cerrada, nublado contra despejado) no tienen verificación automática. Los 6 JSON de `data/casos_prueba/` cubren estados lumínicos, no esos casos. | **Parcial** |

### 1.7 Lo que sí cumple sin observaciones

Dos torres fijas con sus cajas, pisos, áreas y conteo de ventanas (52 y 102); perfiles por actividad y horarios; presets de vidrio y pared; clasificación instantánea con factores 0,50 y 1,25; método de lúmenes para la luz artificial; balance `O(Z log Z)` por instante; entradas configurables por actividad y por recinto (pared, vidrio, orientación).

## 2. AVL y rojo-negro con un uso real

### 2.1 Por qué el uso actual es pobre

- Los dos árboles guardan las mismas 127 claves `(puntaje, zona_id)`.
- El rojo-negro nunca se consulta.
- El AVL hace una consulta de rango que un filtro de lista resuelve igual de rápido.
- Ningún resultado del sistema cambia si se borran los dos árboles.

### 2.2 Criterio para elegir dónde usarlos

Cada árbol se pone donde su propiedad importa:

- **AVL:** equilibrio estricto y altura mínima. Conviene cuando hay **muchas consultas** y pocas modificaciones.
- **Rojo-negro:** menos rotaciones al insertar. Conviene cuando hay **muchas inserciones**.

Y el uso tiene que cumplir tres condiciones:

1. Cambia un resultado o habilita una salida que hoy no existe.
2. Usa operaciones reales del árbol (insertar, eliminar, mínimo, sucesor, rango), no solo insertar.
3. Se puede medir contra la versión ingenua. Esto también cubre `R13`.

### 2.3 Propuesta P1: AVL como bolsa de habitaciones para la reasignación

**Problema que resuelve:** `R19`, `R20`, `R21` y `R22`.

- **Qué guarda:** las habitaciones con cama libre y veredicto `HABITABLE`, con clave `(piso, −calidad, habitacion_id)`. La calidad combina puntaje lumínico y ahorro de energía, y no depende del huésped.
- **Cómo se usa:**
  1. Para cada huésped que hay que mover, se busca la mejor habitación de cada piso con una consulta de sucesor en `O(log H)`. Luego se resta la penalización por cambio de piso y se elige la mejor.
  2. Al asignar, la habitación se actualiza. Si se llena, se **elimina** del árbol. Así dos huéspedes no reciben la misma cama (`R21`).
  3. Los candidatos revisados y descartados quedan registrados con su motivo (`R19`).
- **Por qué AVL:** cada huésped hace varias consultas y como máximo una eliminación. El trabajo es de lectura, y el equilibrio estricto ayuda ahí.
- **Costo:** `O(G · F · log H)` con 78 huéspedes, hasta 10 pisos y 104 habitaciones. Hoy es `O(G · H)`. Se reporta el número de comparaciones de las dos formas.
- **Falta implementar:** eliminación en el AVL y consulta de sucesor.

### 2.4 Propuesta P2: rojo-negro como índice temporal de resultados

**Problema que resuelve:** `R18`.

- **Qué guarda:** los 6.096 resultados de la simulación (127 zonas × 48 pasos), con clave `(hora, zona_id)`. Cada resultado se inserta en cuanto se calcula.
- **Cómo se usa:** consultas por franja horaria. Por ejemplo, "qué zonas están en déficit entre 18:00 y 22:00", "energía consumida en esa franja", "hora pico del generador" y "horas con déficit por zona". Con eso salen el déficit residual, las horas con déficit y las zonas críticas que hoy faltan.
- **En la interfaz:** un selector de franja horaria en el plano, que muestra el estado de cada zona en esa franja.
- **Por qué rojo-negro:** son 6.096 inserciones y pocas consultas. Hace menos rotaciones al insertar que el AVL. Se reportan las rotaciones de los dos árboles con los mismos datos para mostrarlo.
- **Costo:** `O(R log R)` para construirlo y `O(log R + k)` por consulta de franja, contra `O(R)` de recorrer la lista.

### 2.5 Qué pasa con el uso actual

Se quita el índice duplicado de `habitabilidad.py`. La lista de casi habitables se obtiene directo de los veredictos, que es lo que la interfaz ya hace, y desaparece el error del límite 0,90.

### 2.6 Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Árbol en el balance de energía por instante | El balance solo inserta y extrae el máximo. Para eso una cola de prioridad (`heapq`) es más simple y más rápida. Un árbol ahí sería forzado. |
| Árbol para el grafo de influencia | Buscar aristas por destino se resuelve con un diccionario en `O(1)`. |
| Árbol en la reestructuración | Son 30 evaluaciones como máximo. No hay volumen que lo justifique. |

## 3. Decisiones pendientes

| Código | Pregunta | Opciones | Recomendación |
|---|---|---|---|
| D1 | ¿Hay un enunciado oficial del Entregable 2? | Subirlo / No existe, usar los documentos | Subirlo si existe |
| D2 | ¿Cómo usar la radiación real de NASA? (`R1`) | **A.** `factor_luz = radiación / radiación de cielo despejado`, calculado en el código y no escrito a mano. **B.** Conversión física completa (eficacia luminosa del día y factor de luz diurna); hay que recalibrar todo. **C.** Dejarlo y documentar que `factor_luz` es un supuesto. | A |
| D3 | Refracción de Snell (`R6`) | **A.** Calcular el ángulo de transmisión con Snell y ajustar la transmitancia según el ángulo de incidencia (Fresnel). **B.** Quitarla de los documentos. | A |
| D4 | Modos `CERRADA` y `EMERGENCIA` (`R9`, `R10`) | **A.** `CERRADA` por horario para zonas comunes y `EMERGENCIA` con su propio nivel mínimo cuando el generador no alcanza. **B.** Quitarlos de los documentos. | A |
| D5 | Grafo de influencia (`R12`) | **A.** Construirlo con `Octree.consultar_radio` e indexar aristas por destino. **B.** Dejarlo y corregir la complejidad en los documentos. | A |
| D6 | AVL y rojo-negro (sección 2) | **P1 + P2** / Solo P1 / Solo P2 / Otra idea | P1 + P2 |
| D7 | ¿Cuándo se reasigna a un huésped? (`R20`) | **A.** Si la zona es `NO_HABITABLE` (como hoy). **B.** Si la habitación tiene algún paso bajo el mínimo (como dicen los documentos). | A, y actualizar los documentos |
| D8 | IDs (`R23`) | **A.** Dejar los del código y corregir los documentos. **B.** Cambiar el código a `TP-H-101`. | A |
| D9 | Casos de prueba (`R26`) | **A.** Escribir los 10 casos como pruebas automáticas. **B.** No agregar pruebas. | Tú decides; no agrego pruebas sin tu autorización |
| D10 | Documentos del entregable (`R24`, `R25`) | **A.** Moverlos a `docs/` del repo y actualizarlos al final. **B.** Actualizarlos donde están, sin git. **C.** No tocarlos. | A |

## 4. Decisiones tomadas

| Código | Decisión | Detalle |
|---|---|---|
| D1 | No existe enunciado oficial | La referencia son los documentos de `docs/temporal/`. Solo cambia la fila "Enunciado" de la tabla de fuentes. |
| D2 | **A** | `factor_luz = radiación / radiación de cielo despejado`, calculado en el código. Se miden los 7 escenarios después del paso. |
| D3 | **A** | Snell y transmitancia de Fresnel según el ángulo de incidencia. Se mide después de `D2`; si el escenario base vuelve a cambiar, se anota. |
| D4 | **A** | **`CERRADA`:** cocina de 23:00 a 05:00 y recreación de 00:00 a 07:00. Habitaciones y parqueadero nunca cierran. Los pasos `CERRADA` no cuentan en el puntaje de habitabilidad. **`EMERGENCIA`:** primero se reserva para todas las zonas abiertas un nivel de emergencia de 10 lux (supuesto, cercano al promedio de 1 pie-candela, 10,8 lux, que pide NFPA 101 para rutas de evacuación). Luego se cubren los mínimos en este orden: seguridad (parqueadero), habitaciones ocupadas y resto. La zona que no alcanza su mínimo queda en `EMERGENCIA` y ese paso cuenta como déficit. Los horarios y el nivel van en el JSON. |
| D5 | **A** | Mismo radio que el filtro actual. Las salidas deben quedar idénticas; solo cambia el conteo de comparaciones. |
| D6 | **P1 + P2, uso obligatorio de los dos** | El AVL se construye y se reporta siempre (altura, tamaño, comparaciones), aunque en el escenario base nadie se reasigne. La reasignación se demuestra con `deficit_severo.json`. La comparación de rotaciones AVL contra rojo-negro se hace solo en la simulación principal, no en mejoras ni reestructuración. |
| P1 | Ajustes | Clave `(torre, piso, −calidad, habitacion_id)`. Busca en las dos torres, salvo que el huésped tenga `MISMA_TORRE`. Se corrige el texto "No existe alternativa en esta torre" de la interfaz. |
| D7 | **A** | Se reasigna solo si la zona es `NO_HABITABLE`. Se corrigen los documentos. |
| D8 | **B + leyenda** | Torres `TP` y `TG`, habitaciones `TP-H-101` y `TG-H-101`. El nombre completo queda como campo de presentación y hay una leyenda ("TP = Torre Pequeña, TG = Torre Grande") en la interfaz y en los documentos. |
| D9 | **A** | Los 10 casos del Plan como pruebas con `unittest` (biblioteca estándar; el proyecto no tiene dependencias). |
| D10 | **A** | Los documentos pasan a `docs/` y se actualizan al final. Para `R24` se escribe que la geometría de las torres es fija y que el sistema solo cambia variables de luz: actividades, acabados, vidrios, horarios y generador. El LaTeX mantiene el formato ICONTEC y el texto justificado. |
| R22 | **a** | Restricciones por huésped en el JSON (`huespedes.restricciones_por_huesped`). Duras, filtran candidatos: `MISMA_TORRE` y `PISO_MAXIMO:n`. Preferencia, alimenta `w_actividad`: `ORIENTACION:N/E/S/O` (1 si la habitación coincide, 0 si no). Se agregan restricciones a algunos huéspedes de `deficit_severo.json` para que se usen. |
| Commits | | Uno por paso, directo en `main`, autor y committer Juan David Quiroga Gomez, sin coautores. |

## 5. Plan (pendiente de confirmación)

El orden importa: primero los datos y el modelo, porque cambian los resultados que usan los árboles.

0. **Registrar decisiones:** este documento.
1. **Radiación real** (`D2`): luz base con la radiación de NASA y medición de los 7 escenarios.
2. **Snell y Fresnel** (`D3`) y nueva medición.
3. **Modos `CERRADA` y `EMERGENCIA`** (`D4`, `R9`, `R10`): horarios de cierre, nivel de emergencia, orden del balance y puntaje sin pasos cerrados.
4. **Grafo espacial** (`D5`, `R12`): construcción con `Octree.consultar_radio`, aristas por destino y conteo de comparaciones antes y después.
5. **IDs abreviados** (`D8`): `TP` y `TG` en el JSON, el código, los casos de prueba y la interfaz, con leyenda.
6. **AVL en la reasignación** (`P1`, `R19`–`R22`): eliminación y sucesor en el AVL, bolsa de habitaciones, reserva de capacidad, restricciones, candidatos descartados con motivo y comparaciones contra la búsqueda lineal.
7. **Rojo-negro temporal** (`P2`, `R18`): índice de resultados, salidas faltantes, selector de franja horaria en la interfaz y comparación de rotaciones contra el AVL.
8. **Quitar el índice duplicado** de `habitabilidad.py` (sección 2.5) y corregir el límite 0,90.
9. **Pruebas** (`D9`): los 10 casos del Plan.
10. **Documentos** (`D10`): README, los cuatro documentos y el diagrama de clases, en `docs/`.

Cada paso va en su propio commit. Al terminar cada paso actualizo este documento.

### 5.1 Avance

**Paso 1, radiación real (hecho).** `factor_luz` ya no está en los JSON: se calcula como `radiación / radiacion_cielo_despejado` (7,063 kWh/m²/día, en `parametros_evaluacion.luz`; si falta, se usa la mayor radiación de los perfiles). Factores resultantes: nubes parciales 0,689, nublado 0,634, lluvioso 0,631, despejado 1,000.

| Escenario | Habitables / casi / no (antes → después) | Puntaje | Energía Wh |
|---|---|---|---|
| `datos_hotel` | 101/26/0 → 127/0/0 | 0,9346 → 0,9829 | 192.883,5 → 207.215,2 |
| `confortable_base` | 101/26/0 → 127/0/0 | 0,9346 → 0,9829 | 192.883,5 → 207.215,2 |
| `deficit_leve` | 6/2/2 → 8/2/0 | 0,8950 → 0,9367 | 42.192,2 → 43.160,1 |
| `deficit_severo` | 0/0/10 → 0/0/10 | 0,2734 → 0,2812 | 0 → 0 |
| `exceso_leve` | 8/2/0 → 8/2/0 | 0,9583 → 0,9583 | 51.105,5 → 51.105,5 |
| `exceso_severo` | 6/0/4 → 6/0/4 | 0,5000 → 0,5000 | 51.105,5 → 51.105,5 |
| `generador_alta_demanda` | 8/2/0 → 10/0/0 | 0,9401 → 0,9818 | 51.363,6 → 53.357,0 |

Los dos casos de exceso usan cielo despejado (factor 1,0 antes y después), por eso no cambian. La luz natural baja (0,85 → 0,69 en el perfil base), pero las zonas que antes quedaban en exceso de día ahora quedan confortables y el balance compensa con más energía artificial.

## 6. Cierre de la carpeta temporal

Cuando digas "cierra la revisión", se hace esto, en un solo commit:

1. Los documentos del entregable actualizados (`D10`) pasan a su lugar final. Si eliges `D10` A, quedan en `docs/` del repo; si no, se devuelven a donde indiques.
2. Lo que siga vigente de esta revisión (decisiones tomadas, limitaciones conocidas) pasa al README.
3. Se borran `docs/temporal/` y `.kiro/steering/revision-entregable-2.md`.

La carpeta seguirá en el historial de git. Eso es esperado.

## 7. Fuera de alcance

- Cambiar la geometría de las habitaciones o agregar torres.
- Cambiar los umbrales de habitabilidad (0,90 y 0,75).
- Usar árboles en el balance de energía por instante (ver 2.6).

**Paso 2, Snell y Fresnel (hecho).** Para la luz directa, cada ventana calcula el ángulo de refracción con Snell (`indice_refraccion` del vidrio, 1,5) y la transmitancia de Fresnel no polarizada en las dos caras del vidrio. El resultado se normaliza con la incidencia perpendicular, así que la VLT del catálogo se conserva a 0°. La luz difusa sigue usando la VLT del catálogo. Factor angular: 30° → 0,997; 45° → 0,979; 60° → 0,900; 75° → 0,605; 85° → 0,163.

| Escenario | Habitables / casi / no | Puntaje (paso 1 → paso 2) | Energía Wh (paso 1 → paso 2) |
|---|---|---|---|
| `datos_hotel` | 127/0/0 sin cambio | 0,9829 → 0,9839 | 207.215,2 → 208.001,3 |
| `confortable_base` | 127/0/0 sin cambio | 0,9829 → 0,9839 | 207.215,2 → 208.001,3 |
| `deficit_leve` | 8/2/0 sin cambio | 0,9367 → 0,9340 | 43.160,1 → 43.184,2 |
| `deficit_severo` | 0/0/10 sin cambio | 0,2812 → 0,2812 | 0 → 0 |
| `exceso_leve` | 8/2/0 sin cambio | 0,9583 → 0,9636 | 51.105,5 → 51.725,6 |
| `exceso_severo` | 6/0/4 sin cambio | 0,5000 → 0,5000 | 51.105,5 → 51.725,6 |
| `generador_alta_demanda` | 10/0/0 sin cambio | 0,9818 → 0,9818 | 53.357,0 → 53.482,4 |

El escenario base no cambia de veredictos. Snell baja un poco la luz directa con incidencia oblicua y el balance lo compensa con algo más de energía.

**Paso 3, modos `CERRADA` y `EMERGENCIA` (hecho).**

- `horarios` en los JSON tiene `cierre_inicio` y `cierre_fin` para cocina (23 → 5) y recreación (0 → 7). La franja activa manda sobre la de cierre, para que la reestructuración pueda abrir la cocina hasta las 24. La interfaz permite editar el cierre.
- Los pasos `CERRADA` no reciben energía y quedan como `DATOS_INSUFICIENTES`, así que no cuentan en el puntaje. Es lo que la leyenda de la interfaz ya decía de ese estado.
- `parametros_evaluacion.emergencia.nivel_lux = 10` (si falta, 10). El balance reserva primero ese nivel para todas las zonas abiertas, luego cubre mínimos en el orden parqueadero → habitaciones ocupadas → resto, y por último los objetivos. La zona que no alcanza su mínimo porque el generador se agotó queda en `EMERGENCIA` y se clasifica contra el mínimo de su modo de horario, por lo que cuenta como déficit.

| Escenario | Habitables / casi / no (paso 2 → paso 3) | Puntaje | Energía Wh | Pasos `CERRADA` / `EMERGENCIA` |
|---|---|---|---|---|
| `datos_hotel` | 127/0/0 → 127/0/0 | 0,9839 → 0,9839 | 208.001,3 → 194.729,7 | 260 / 0 |
| `confortable_base` | 127/0/0 → 127/0/0 | 0,9839 → 0,9839 | 208.001,3 → 194.729,7 | 260 / 0 |
| `deficit_leve` | 8/2/0 → 7/3/0 | 0,9340 → 0,9277 | 43.184,2 → 41.791,3 | 52 / 8 |
| `deficit_severo` | 0/0/10 → 0/0/10 | 0,2812 → 0,3145 | 0 → 0 | 52 / 328 |
| `exceso_leve` | 8/2/0 → 8/2/0 | 0,9636 → 0,9636 | 51.725,6 → 49.076,5 | 52 / 0 |
| `exceso_severo` | 6/0/4 → 6/0/4 | 0,5000 → 0,5000 | 51.725,6 → 49.076,5 | 52 / 0 |
| `generador_alta_demanda` | 10/0/0 → 10/0/0 | 0,9818 → 0,9818 | 53.482,4 → 50.827,5 | 52 / 0 |

La energía baja porque las zonas cerradas ya no consumen. En `deficit_leve` (generador de 1,8 kW) el parqueadero pasa a tener prioridad de seguridad: deja de tener déficit nocturno y la recreación de la torre B queda en `EMERGENCIA` de 18:00 a 22:00 (habitable → casi habitable). El escenario base nunca entra en `EMERGENCIA` porque su generador alcanza. En `deficit_severo` el generador es de 0 kW: el puntaje sube un poco porque los pasos cerrados ya no cuentan como déficit.

**Paso 4, grafo espacial (hecho).** `GrafoInfluencia.construir` pide a `Octree.consultar_radio` las ventanas a 18 m de cada superficie, en vez de recorrer todas. Las aristas también se indexan por destino, así que `reflejada_para` solo recorre las aristas que llegan a la ventana. La API devuelve `complejidad.grafo` con los conteos. Los resultados de los 7 escenarios son idénticos bit a bit a los del paso 3 (misma huella SHA-256 de resultados, reasignaciones y veredictos).

| Medida (escenario base) | Antes | Después |
|---|---|---|
| Pares superficie–ventana evaluados al construir | 19.558 | 2.516 (6.047 nodos del octree visitados) |
| Aristas recorridas por instante en `reflejada_para` | 154 × 183 = 28.182 | 183 |
| Tiempo de `ejecutar()` (48 pasos) | 0,98 s | 0,50 s |

**Hallazgo nuevo (R27), sin corregir.** Al probar el octree apareció que 75 habitaciones (20 de la torre pequeña y 55 de la grande) tienen su ventana y su pared fuera de la caja de su torre. Por ejemplo, `TorreGrande-H-172` está en `y = 172`, y la caja de la torre llega a `y = 43`. La causa está en `_room_center` de `io_datos.py`: reparte las habitaciones de toda la torre en filas como si fueran de un solo piso. El octree original usaba como raíz la caja de las torres y por eso no encontraba esas ventanas. Ahora la raíz cubre todos los objetos, lo que conserva los resultados actuales. Corregir la posición cambia la geometría de las habitaciones, que está fuera de alcance (sección 7), así que queda pendiente como `D11`.

**Paso 5, IDs abreviados (hecho).** Las torres de `datos_hotel.json` y `confortable_base.json` se llaman `TP` y `TG`, con un campo `nombre` ("Torre Pequeña", "Torre Grande") para mostrar. Las zonas quedan `TP-H-101`, `TG-COC-01`, etc. La interfaz muestra "TP · Torre Pequeña" en el selector y en el formulario de torres, y una leyenda de abreviaturas bajo el plano. Las medidas del plano salen de la caja de la torre en vez de buscar "pequena" en el ID. Los demás casos de prueba usan `TorreA` y `TorreB`, que no tienen abreviatura, y no cambian. Los resultados numéricos no cambian.

**Paso 6, AVL en la reasignación (hecho).**

- `IndiceAVL` tiene `eliminar` (con rebalanceo), `sucesor` (menor clave ≥ x), `siguiente` (menor clave > x) y un contador de comparaciones. Se probó con 200 secuencias aleatorias de 200 inserciones y 150 eliminaciones: el árbol queda balanceado y ordenado, y las consultas coinciden con una búsqueda lineal.
- `reasignacion.py` arma la bolsa con las habitaciones `HABITABLE` con cama libre, con clave `(torre, piso, −calidad, id)`, donde calidad = `w_luz · puntaje + w_energia · ahorro`. Para cada huésped que hay que mover se consulta el sucesor de cada piso permitido. Si el huésped tiene preferencia de orientación, se siguen los sucesores del piso mientras alguno todavía pueda ganar con el bono. Al llenarse una habitación, se elimina del árbol.
- Restricciones (`R22`): `huespedes.restricciones_por_huesped` en el JSON, con `MISMA_TORRE`, `PISO_MAXIMO:n` y `ORIENTACION:ESTE|NORTE|OESTE|SUR`. Se usan los nombres completos de orientación del JSON en vez de N/E/S/O. Una restricción desconocida se rechaza al cargar. Sin preferencia de orientación, `w_actividad` suma 1,0 como antes, así que los puntajes de huéspedes sin restricciones no cambian.
- Cada propuesta trae `descartadas` (habitaciones revisadas con motivo `MENOR_PUNTAJE`) y, si no hay alternativa, `motivo`: `SIN_HABITACIONES_HABITABLES_LIBRES`, `SIN_CAPACIDAD` o `RESTRICCIONES` (`R19`). La interfaz muestra restricciones, descartadas y motivo, y ya no dice "en esta torre".
- La API devuelve `complejidad.reasignacion` con comparaciones lineales (`G · H`), comparaciones del AVL, comparaciones de construcción y datos del árbol.

Resultados:

- En los 7 escenarios los conteos no cambian (0 o 2 reasignaciones, todas `NO_HAY_ALTERNATIVA` donde ya lo eran).
- `deficit_severo` tiene ahora restricciones en sus dos huéspedes. Como sus 4 habitaciones son `NO_HABITABLE`, el motivo es `SIN_HABITACIONES_HABITABLES_LIBRES`: el caso demuestra "sin candidata", pero no "con candidata". Ningún caso de prueba actual tiene a la vez habitaciones ocupadas no habitables y habitaciones libres habitables.
- En el escenario base el AVL se construye con las 104 habitaciones (altura 8, 109 rotaciones, 622 comparaciones de construcción) y no se consulta, porque nadie está en una habitación `NO_HABITABLE`.
- Prueba de carga fuera del repo, sobre el escenario base con 60 de las 78 habitaciones ocupadas marcadas `NO_HABITABLE`: 2.790 comparaciones del AVL contra 6.240 lineales; 39 eliminaciones; ninguna habitación con sobrecupo. Con restricciones mezcladas: 3.451 contra 6.240, 51 propuestas y 9 `SIN_CAPACIDAD`. En las dos corridas la habitación elegida coincide, huésped por huésped, con una búsqueda lineal que descuenta capacidad.

**Paso 7, rojo-negro temporal (hecho).**

- `src/temporal.py`: cada resultado se inserta en un `IndiceRojoNegro` con clave `(hora, zona_id)` apenas se calcula. Las franjas se consultan con `rango((inicio, ""), (fin, ""))`, que es un intervalo semiabierto `[inicio, fin)`.
- Franjas fijas: día completo, 00–06, 06–12, 12–18, 18–22 y 22–24. Para cada una, la API (`temporal`) devuelve las salidas que faltaban (`R18`): energía en Wh y kWh, energía por actividad y por torre, hora y potencia pico del generador, déficit residual (lux·h bajo el mínimo), energía no asignada (Wh que habrían cerrado ese déficit), zonas críticas (top 10 por horas en déficit), horas con déficit por zona, instantes con déficit y estado predominante de cada zona.
- Interfaz: selector "Franja horaria" en el plano. Con una franja elegida, cada zona se colorea con su estado en esa franja y aparece el reporte debajo del plano. En resultados hay una tabla "Estructuras de datos y comparaciones" con el grafo, el AVL de reasignación y la comparación de rotaciones.
- Solo en la simulación principal (`/api/balancear`) los mismos resultados se insertan también en un AVL para comparar rotaciones.

| Medida | Escenario base (6.096 resultados) | `deficit_leve` (480) |
|---|---|---|
| Rotaciones rojo-negro / AVL | **9.099 / 7.232** | 465 / 564 |
| Altura rojo-negro / AVL | 22 / 14 | 15 / 10 |
| Nodos visitados en la franja 18–22 contra recorrer la lista | 1.029 contra 6.096 | 89 contra 480 |

**Hallazgo: en el escenario base el rojo-negro rota más que el AVL.** La sección 2.4 justificaba el rojo-negro porque rota menos al insertar. Con claves aleatorias eso se cumple (prueba aparte con 6.096 claves: 3.511 contra 4.176). Pero aquí los resultados llegan casi en orden: hora ascendente y, dentro de cada hora, tramos largos de IDs ascendentes. Con esa entrada, el rojo-negro hace 9.099 rotaciones contra 7.232 del AVL. Se verificó que el árbol cumple las propiedades de rojo-negro, así que no es un error de implementación. El índice funciona y cumple su papel en las consultas, pero el argumento de las rotaciones no se sostiene con estos datos. Queda pendiente como `D12`.

**Paso 8, índice duplicado (hecho).** `evaluar_hotel` ya no construye el AVL ni el rojo-negro de puntajes. `casi_habitables` sale directo de los veredictos, así que una zona con puntaje exacto 0,90 queda como habitable, igual que en la regla. Se quitó `habitabilidad.indices`, que ninguna parte de la interfaz leía. Veredictos y resultados no cambian.
