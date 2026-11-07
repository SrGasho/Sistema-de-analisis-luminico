# Propuesta de simulación lumínica y balance energético para un hotel

## Curso: Ciencias de la Computación 1

## Introducción

Se propone desarrollar un sistema educativo para estimar la iluminación de un hotel de dos torres en Bogotá. El sistema trabaja con cuatro actividades: habitaciones, cocina, recreación y parqueadero. Utiliza una jerarquía de composición, un Octree para consultas espaciales, un grafo dirigido ponderado para influencias lumínicas y un recorrido temporal único de 24 horas.

El día y la noche no se representan mediante clases duplicadas. Las mismas zonas, perfiles, resultados y evaluadores reciben el instante y el modo de operación. Los resultados son aproximaciones educativas y no sustituyen un proyecto fotométrico o eléctrico profesional.

# 1. Escenario y entradas

## 1.1 Hotel fijo

```text
Hotel
├── TorrePequena: 4 pisos, 32 habitaciones, 4 cocinas, 4 recreaciones, 1 parqueadero
└── TorreGrande: 6 pisos, 72 habitaciones, 6 cocinas, 6 recreaciones, 2 parqueaderos
```

Las áreas de referencia son aproximadamente 4.013 m² y 11.346 m², inspiradas en modelos DOE. Las cajas, zonas, ventanas, huéspedes y luminarias son datos sintéticos.

```text
TorrePequena: x=0..32, y=0..31.35, z=0..12
TorreGrande:  x=45..89, y=0..43,    z=0..18
```

Cada piso mide 3 m de alto y la separación horizontal aproximada entre torres es de 13 m. Las habitaciones tienen 24 m² y capacidad para dos huéspedes. Hay 78 huéspedes iniciales: 24 habitaciones ocupadas en la torre pequeña y 54 en la grande.

## 1.2 Zonas y ventanas

| Actividad | Área | Zonas pequeñas | Zonas grandes | Ventanas por zona |
|---|---:|---:|---:|---:|
| Habitación | 24 m² | 32 | 72 | 1 de 2,0 m² |
| Cocina | 35 m² | 4 | 6 | 2 de 1,5 m² |
| Recreación | 80 m² | 4 | 6 | 3 de 2,0 m² |
| Parqueadero | 450 m² | 1 | 2 | 0 |

Una ventana contiene `id`, posición, normal, área, vidrio y resultados temporales. Los IDs de habitación siguen `TP-H-101` y `TG-H-101`; los huéspedes de prueba usan `H-001` a `H-078`.

## 1.3 Actividades y horarios

| Actividad | Horario | Mínimo | Objetivo | Máximo | Prioridad |
|---|---|---:|---:|---:|---:|
| Habitación | 06:00–22:00 activa; resto reducida | 100 | 200 | 300 | 3 |
| Cocina | 06:00–22:00 activa; resto reducida | 300 | 400 | 500 | 3 |
| Recreación | 08:00–23:00 activa; resto reducida | 200 | 300 | 500 | 2 |
| Parqueadero | 00:00–24:00 activa | 50 | 100 | 150 | 1 |

Los valores están expresados en lux de referencia. Son presets educativos configurables, no una transcripción normativa del RETILAP. El modo `EMERGENCIA` tiene un parámetro separado y debe validarse independientemente.

## 1.4 Vidrios, paredes y luminarias

Vidrios:

```text
VIDRIO_CLARO:          VLT = 0,82
VIDRIO_LOW_E:          VLT = 0,70–0,72
VIDRIO_CONTROL_SOLAR:  VLT = 0,52
```

Paredes:

```text
Blanco 0,80 | Crema 0,70 | Gris claro 0,60
Gris medio 0,45 | Oscuro 0,25
```

Luminarias equivalentes:

| Actividad | Potencia | Eficacia | CU | MF |
|---|---:|---:|---:|---:|
| Habitación | 72 W | 100 lm/W | 0,70 | 0,80 |
| Cocina | 200 W | 100 lm/W | 0,70 | 0,80 |
| Recreación | 450 W | 100 lm/W | 0,70 | 0,80 |
| Parqueadero | 720 W | 100 lm/W | 0,70 | 0,80 |

El generador tiene una capacidad sintética de 22,0 kW y sólo se utiliza para iluminación.

# 2. Salidas

Para cada zona e instante se almacenan:

```text
hora, periodo, modo, luzNatural, luzReflejada,
luzArtificial, luzTotal, potenciaAsignada, estado
```

Los estados son:

```text
DEFICIT_SEVERO
DEFICIT_LEVE
CONFORTABLE
EXCESO_LEVE
EXCESO_SEVERO
DATOS_INSUFICIENTES
```

El sistema también reporta potencia máxima, energía en Wh/kWh, puntuaciones diurnas y nocturnas, horas con déficit, energía no asignada, habitaciones críticas, huéspedes reasignados y candidatos descartados.

# 3. Modelo de iluminación

## 3.1 Componentes

Para cualquier instante:

```text
E_total(z,t) = E_natural(z,t) + E_reflejada(z,t) + E_artificial(z,t)
```

Durante el día se calcula luz solar mediante el perfil climático, orientación, sombras, vidrio y paredes. Durante la noche:

```text
E_natural = 0
E_reflejada_solar = 0
E_total = E_artificial
```

La luz artificial se mantiene separada para no confundir una luminaria nocturna con luz natural.

## 3.2 Clima de Bogotá

La ubicación de referencia es 4.7110° N, -74.0721° O. Se utilizan perfiles basados en NASA POWER, climatología 2001–2020:

```text
Nubes parciales: febrero
Nublado: mayo
Lluvioso: abril
Cielo despejado: perfil clear-sky
```

La conversión de irradiancia a lux es una aproximación mediante `K_lux`. Sin calibración, el resultado se llama lux de referencia y no lux fotométrico medido.

## 3.3 Transmisión y refracción

Para cada ventana se aplica su transmitancia visible y se cambia la dirección del rayo con Snell:

```text
n_aire × sin(theta_i) = n_vidrio × sin(theta_t)
```

El índice del vidrio se aproxima a 1,5. No se modelan polarización, reflexión interna múltiple, dispersión espectral ni marcos detallados.

## 3.4 Reflexión de primer orden

El grafo crea relaciones como:

```text
Superficie/Fuente → Ventana/ZonaHotel
```

El peso depende de reflectancia, orientación, distancia y visibilidad. La luz reflejada no vuelve a ser origen de una segunda reflexión.

# 4. Estructuras de datos

## 4.1 Árbol jerárquico

```text
Hotel
├── Torre
│   ├── Piso
│   │   ├── ZonaHotel
│   │   │   └── Ventana
```

`HabitacionHotel` es una especialización de `ZonaHotel`. `Huesped` se relaciona con `HabitacionHotel` mediante `Asignacion`.

## 4.2 Octree

El Octree indexa torres, paredes, zonas, ventanas y luminarias. Se consulta para:

- detectar si una torre bloquea un rayo solar;
- encontrar superficies y fuentes cercanas;
- filtrar candidatos del grafo;
- comprobar visibilidad entre fuente y receptor.

Un objeto que atraviesa varios octantes permanece en el nodo padre. Esto evita duplicar cajas grandes.

## 4.3 Grafo de influencia

Cada arista contiene `origen`, `destino`, `peso`, distancia, compatibilidad de orientación y visibilidad. La construcción espacial evita comparar todos los pares cuando no son cercanos.

# 5. Algoritmos

## 5.1 Sombra y luz natural

```text
para cada instante t:
    si t está en noche:
        natural = 0
        reflejadaSolar = 0
    si t está en día o transición:
        calcular vector solar y perfil climático
        para cada zona con ventana:
            consultar candidatos del rayo en el Octree
            determinar sombra
            calcular componente directa o difusa
            aplicar vidrio y refracción
        calcular reflexión de primer orden
```

## 5.2 Balance energético

La iluminación artificial aproximada se calcula así:

```text
E_artificial = eficacia × potenciaAsignada × CU × MF / área
```

Para cada zona se calculan demandas mínima y objetivo después de descontar luz natural y reflejada. El balance ejecuta:

```text
1. identificar zonas activas;
2. garantizar mínimos de seguridad;
3. garantizar mínimos de habitaciones ocupadas;
4. ordenar demandas por actividad, piso y ocupación;
5. distribuir potencia restante;
6. guardar déficit residual y energía.
```

La potencia del generador se estima con:

```text
P_generador = 1,20 × máximo_t(suma(P_obj(z,t)))
```

La reserva del 20 % es didáctica. El generador no alimenta el consumo total del hotel.

## 5.3 Reasignación de huéspedes

Cuando una habitación ocupada queda por debajo del mínimo de su actividad:

```text
candidatos = habitaciones disponibles y compatibles
para cada candidato:
    verificar mínimo de luz
    calcular score por calidad de luz, actividad, energía y cambio
escoger el mejor score
si no existe candidato:
    reportar insuficiencia de capacidad
```

La estrategia es greedy y no garantiza un óptimo global.

# 6. Flujo completo

1. Validar exactamente dos torres.
2. Cargar pisos, zonas, ventanas, vidrios, paredes y luminarias.
3. Cargar huéspedes, ocupaciones y asignaciones.
4. Cargar clima y horarios.
5. Construir Octree y grafo.
6. Recorrer `00:00`–`24:00` con el mismo evaluador.
7. Calcular componentes naturales, reflejadas y artificiales.
8. Ejecutar balance y guardar resultados.
9. Clasificar zonas.
10. Buscar alternativas para habitaciones ocupadas no conformes.
11. Exportar reporte energético y lumínico.

# 7. Complejidad y casos de prueba

```text
Sombras sin Octree:       O(V × B × T)
Sombras con Octree:       O(V × T × (log B + k)) esperado
Grafo ingenuo:            O(S²)
Grafo espacial disperso: O(S log S + E) esperado
Agregación:               O(N)
Balance por instante:     O(Z log Z)
```

Casos mínimos:

1. Ventana orientada al sol.
2. Ventana bloqueada por la otra torre.
3. Cambio entre vidrio claro, low-E y control solar.
4. Reflexión de primer orden sin cascada.
5. Noche sin luz solar y con luminaria activa.
6. Generador suficiente para mínimos, pero insuficiente para todos los objetivos.
7. Reasignación exitosa de un huésped.
8. Falta de habitación compatible.
9. Zona cerrada o habitación en descanso sin falso déficit.

# 8. Fuentes, supuestos y límites

El clima se basa en NASA POWER; las torres se inspiran en DOE Commercial Reference Buildings; la regulación se contrasta con el RETILAP vigente y sus modificaciones; ISO 30061 se reserva para el tratamiento independiente de emergencia; UNE-EN 12464-1 sirve como guía complementaria; Cardinal Glass respalda los presets de transmitancia y Edmund Optics la aproximación óptica.

Los rangos de lux, horarios, áreas, potencias, reflectancias, huéspedes y capacidad del generador son supuestos didácticos. La página oficial del Ministerio informa que el RETILAP vigente fue modificado por la Resolución 40286 del 23 de junio de 2026, pero no se usa para presentar los presets como una transcripción normativa. El sistema no certifica cumplimiento ni reemplaza una medición.

# 9. Criterio de éxito

La propuesta se considera cumplida si el sistema procesa las dos torres en 24 horas, diferencia día y noche con clases compartidas, usa el Octree y el grafo, calcula balance energético, clasifica las cuatro actividades, reporta déficits y puede proponer o rechazar una reasignación de huésped de forma explicable.
