# Plan del sistema educativo de iluminación y balance energético hotelero

## Proyecto de Ciencias de la Computación 1

## 1. Resumen

El proyecto propone diseñar e implementar un sistema educativo que estime la iluminación de un hotel de dos torres ubicado en Bogotá. El hotel se analiza durante 24 horas y contiene cuatro actividades: habitaciones, cocina, recreación y parqueadero.

El sistema combina un árbol jerárquico, un Octree, un grafo dirigido ponderado y recorridos de agregación. Durante el día calcula luz natural, transmisión por vidrio, refracción simplificada, reflexión de primer orden y luz artificial complementaria. Durante la noche toma la luz solar como cero y distribuye la potencia artificial disponible mediante un balance heurístico.

El modelo no pretende sustituir un diseño fotométrico, eléctrico o arquitectónico profesional. Las torres, zonas, huéspedes, luminarias y potencias son datos sintéticos didácticos; las fuentes publicadas se distinguen explícitamente de los supuestos del proyecto.

## 2. Contexto y problema computacional

La iluminación de una zona hotelera depende de la orientación, la hora, el clima, las sombras, el vidrio, las paredes reflectantes, la actividad y la disponibilidad de iluminación artificial. Además, de noche el generador puede no alcanzar para llevar todas las zonas a su objetivo al mismo tiempo.

Dado un hotel con dos torres, pisos, zonas, ventanas, superficies, luminarias, huéspedes y un generador, el sistema debe:

1. Calcular la iluminación natural y reflejada de cada zona durante el día.
2. Calcular la iluminación artificial complementaria y nocturna.
3. Clasificar cada zona según su perfil de actividad y modo de operación.
4. Cubrir primero los mínimos de seguridad y de habitaciones ocupadas.
5. Distribuir la potencia restante según prioridad de actividad, piso y ocupación.
6. Medir potencia, energía, déficits y estados durante las 24 horas.
7. Proponer una habitación compatible cuando una habitación ocupada no alcance el mínimo.

La reasignación es una recomendación greedy: modifica la relación huésped–habitación en el modelo, no la geometría ni una reserva real.

## 3. Objetivo general

Diseñar e implementar un sistema de análisis lumínico y balance energético que utilice árboles, Octree, grafos y algoritmos de agregación para estudiar un hotel de dos torres en Bogotá durante un día completo.

## 4. Objetivos específicos

- Representar `Hotel → Torre → Piso → ZonaHotel → Ventana` mediante composición.
- Mantener exactamente dos torres fijas, una pequeña y una grande.
- Representar habitaciones, cocinas, recreaciones y parqueaderos con zonas reutilizables.
- Usar un eje temporal único entre 00:00 y 24:00, sin clases diurnas/nocturnas duplicadas.
- Calcular sombras con cajas espaciales y consultas de Octree.
- Representar influencias de superficies y fuentes mediante un grafo dirigido.
- Calcular una sola reflexión secundaria.
- Incorporar tres presets de vidrio y cinco reflectancias educativas de pared.
- Usar perfiles climáticos de Bogotá basados en NASA POWER.
- Dimensionar y utilizar un generador exclusivo para iluminación.
- Clasificar zonas con rangos configurables por actividad.
- Proponer reasignaciones de huéspedes cuando el balance no cubra una habitación ocupada.
- Comparar la complejidad de búsquedas ingenuas y búsquedas espaciales.

## 5. Alcance

### 5.1 Incluido

- Hotel con exactamente dos torres.
- 4 pisos en `TorrePequena` y 6 pisos en `TorreGrande`.
- 32 y 72 habitaciones respectivamente.
- Cocinas, zonas recreativas y parqueaderos sintéticos.
- Ventanas con posición, normal, área y vidrio.
- Paredes con reflectancia nominal.
- Clima de Bogotá con perfiles de nubes parciales, nublado, lluvioso y cielo despejado.
- Simulación discreta de 24 horas.
- Luz natural, reflejada y artificial separadas.
- Modos `ACTIVA`, `REDUCIDA`, `CERRADA` y `EMERGENCIA`.
- Balance energético de mínimos y objetivos.
- Puntuaciones, estados, déficits y energía consumida.
- Reasignación heurística de huéspedes.

### 5.2 No incluido

- Diseño fotométrico profesional.
- Archivos IES/LDT o mallas arquitectónicas complejas.
- Deslumbramiento profesional, confort circadiano o modelo térmico.
- Consumo total del hotel, ascensores, climatización o agua caliente.
- Reflexión especular o reflexiones de segundo orden.
- Optimización global de geometría, luminarias o asignaciones.
- Sistema real de reservas o traslado físico de huéspedes.
- Certificación normativa.

## 6. Escenario sintético reproducible

Las áreas de referencia se inspiran en modelos comerciales del DOE, pero la geometría y los registros siguientes son supuestos del proyecto.

| Elemento | TorrePequena | TorreGrande | Regla común |
|---|---:|---:|---|
| Área de referencia | 4.013 m² | 11.346 m² | Plantilla educativa |
| Pisos | 4 | 6 | 3 m por piso |
| Habitaciones | 32 | 72 | 24 m², capacidad 2 |
| Cocinas | 4 | 6 | 35 m² |
| Recreaciones | 4 | 6 | 80 m² |
| Parqueaderos | 1 | 2 | 450 m² |
| Ventanas | 52 | 102 | Habitación 1, cocina 2, recreación 3 |
| Habitaciones ocupadas | 24 | 54 | 78 huéspedes en total |

Cajas espaciales:

```text
TorrePequena: x=0..32, y=0..31.35, z=0..12
TorreGrande:  x=45..89, y=0..43,    z=0..18
separación horizontal aproximada: 13 m
```

Los IDs de habitaciones usan `TP-H-101` y `TG-H-101`; los huéspedes de prueba usan `H-001` a `H-078`. No representan personas reales.

Luminarias equivalentes por zona:

| Actividad | Potencia | Eficacia | CU | MF |
|---|---:|---:|---:|---:|
| Habitación | 72 W | 100 lm/W | 0,70 | 0,80 |
| Cocina | 200 W | 100 lm/W | 0,70 | 0,80 |
| Recreación | 450 W | 100 lm/W | 0,70 | 0,80 |
| Parqueadero | 720 W | 100 lm/W | 0,70 | 0,80 |

El generador se fija en 22,0 kW nominales, redondeando hacia arriba la demanda objetivo máxima más una reserva didáctica del 20 %. Sólo se dimensiona el subsistema de iluminación.

## 7. Perfiles, horarios y clasificación

Los siguientes son presets educativos. El RETILAP vigente debe consultarse para la categoría exacta, plano de trabajo, uniformidad, mantenimiento y demás requisitos. No se presentan como una transcripción normativa.

| Actividad | Mínimo | Objetivo | Máximo | Prioridad |
|---|---:|---:|---:|---:|
| Habitación activa | 100 lux | 200 lux | 300 lux | 3 |
| Cocina activa | 300 lux | 400 lux | 500 lux | 3 |
| Recreación activa | 200 lux | 300 lux | 500 lux | 2 |
| Parqueadero activo | 50 lux | 100 lux | 150 lux | 1 |

Horarios sintéticos:

```text
Habitaciones: 06:00–22:00 ACTIVA; 22:00–06:00 REDUCIDA
Cocinas:      06:00–22:00 ACTIVA; resto REDUCIDA
Recreación:   08:00–23:00 ACTIVA; resto REDUCIDA
Parqueaderos: 00:00–24:00 ACTIVA
```

La emergencia usa un parámetro separado. No se deduce de los rangos normales.

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
faltan datos             → DATOS_INSUFICIENTES
```

Los factores 0,50 y 1,25 son reglas del proyecto, no valores normativos.

## 8. Clima, vidrio y paredes

La ubicación de referencia es Bogotá, aproximadamente 4.7110° N, -74.0721° O. Se usan perfiles derivados de NASA POWER y una conversión calibrable a lux de referencia. La radiación no se convierte directamente a lux sin una hipótesis fotométrica adicional.

Vidrios:

| Preset | Transmitancia visible | Uso sintético |
|---|---:|---|
| `VIDRIO_CLARO` | 0,82 | Habitaciones y fachadas de baja protección |
| `VIDRIO_LOW_E` | 0,70–0,72 | Habitaciones y zonas generales |
| `VIDRIO_CONTROL_SOLAR` | 0,52 | Exposición solar alta |

Paredes:

```text
Blanco 0,80   Crema 0,70   Gris claro 0,60
Gris medio 0,45   Oscuro 0,25
```

La refracción usa la ley de Snell con un índice de vidrio cercano a 1,5. La reflexión se limita al primer orden.

## 9. Estructuras y flujo

### Árbol

```text
Hotel
├── TorrePequena / TorreGrande
│   ├── Piso
│   │   ├── ZonaHotel
│   │   │   └── Ventana
```

### Octree

Indexa cajas de torres, paredes, zonas, ventanas y luminarias. Sirve para rayos de sombra, radios de influencia y visibilidad.

### Grafo

```text
Superficie o Fuente → Ventana o ZonaHotel
```

Cada arista contiene un peso de distancia, orientación, reflectancia y visibilidad. Sólo se calcula reflexión de primer orden.

### Algoritmo general

```text
cargar hotel y validar dos torres
cargar pisos, zonas, ventanas, vidrios, paredes, luminarias y huéspedes
cargar clima y horarios
construir Octree y grafo de influencia

para cada instante t entre 00:00 y 24:00:
    determinar periodo y modo de cada zona
    calcular luz natural, transmisión, refracción y reflexión si es de día
    calcular demandas mínima y objetivo
    asignar primero mínimos de seguridad y habitaciones ocupadas
    distribuir potencia restante por prioridad
    calcular luz artificial y luz total
    clasificar cada zona y guardar resultado

para cada huésped en habitación no conforme:
    buscar habitación disponible y compatible
    ordenar candidatos por luz, actividad, ahorro de energía y cambio
    registrar la mejor propuesta o indicar que no existe

agregar métricas, energía y déficits
exportar reporte
```

## 10. Balance energético

Para cada zona se calcula la potencia artificial aproximada:

```text
E_artificial = eficacia × potenciaAsignada × CU × MF / área
```

La demanda mínima y la demanda objetivo se calculan después de descontar luz natural y reflejada. El balance:

1. identifica zonas activas;
2. calcula mínimos y objetivos;
3. cubre mínimos de seguridad y habitaciones ocupadas;
4. ordena el resto por `pesoActividad × pesoPiso × factorOcupacion`;
5. asigna potencia hasta el objetivo o hasta agotar el generador;
6. registra déficit residual y energía en Wh/kWh.

El peso sólo determina prioridad. No convierte una zona oscura en confortable.

## 11. Métricas y complejidad

El sistema reporta estado por zona e instante, puntuación diurna/nocturna, energía por torre y actividad, potencia máxima, déficit residual, zonas críticas, huéspedes reasignados y candidatos.

Costes aproximados:

```text
Sombras ingenuas:       O(V × B × T)
Octree esperado:        O(V × T × (log B + k))
Grafo ingenuo:          O(S²)
Grafo espacial disperso:O(S log S + E)
Agregación jerárquica:  O(N)
Balance por instante:  O(Z log Z)
```

El coste real depende de la distribución espacial y de la cantidad de candidatos.

## 12. Casos de prueba

1. Ventana orientada al sol y sin obstáculo.
2. Ventana sombreada por la otra torre.
3. Transmisión con cada preset de vidrio.
4. Reflexión de primer orden sin cascada.
5. Noche con luz natural cero y luminaria artificial activa.
6. Generador suficiente para mínimos pero insuficiente para todos los objetivos.
7. Habitación ocupada con déficit y habitación compatible disponible.
8. Habitación ocupada con déficit sin alternativa disponible.
9. Zona cerrada y habitación en descanso sin falso déficit.
10. Comparación entre clima nublado y cielo despejado.

## 13. Fuentes y límites

Fuentes principales: NASA POWER para clima; DOE Commercial Reference Buildings para las plantillas de torres; página oficial del RETILAP y Resolución 40286 de 2026 para el marco regulatorio; ISO 30061 para iluminación de emergencia; UNE-EN 12464-1 como guía complementaria; Cardinal Glass para transmitancias; Edmund Optics para óptica básica.

Los rangos, pesos, horarios, áreas de zonas, potencias, capacidad del generador, huéspedes y posiciones son supuestos sintéticos. El resultado usa lux de referencia cuando no existe calibración fotométrica. No constituye una certificación de cumplimiento.

## 14. Criterio de éxito

El proyecto será exitoso si construye las dos torres, recorre 24 horas con un modelo único, consulta el Octree, calcula reflexión de primer orden, aplica el balance, clasifica las cuatro actividades, reporta energía y déficits, y produce propuestas coherentes de reasignación sin alterar la geometría.
