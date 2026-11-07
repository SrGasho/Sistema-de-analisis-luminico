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
