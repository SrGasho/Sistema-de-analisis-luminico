from __future__ import annotations

from .modelo import Actividad, EstadoIluminacion, Hotel, ModoOperacion


def generar_sugerencias_habitabilidad(
    hotel: Hotel,
    resumen: dict[str, dict],
    resultados: list,
    generador_info: dict,
    reasignaciones: list[dict],
) -> list[dict]:
    sugerencias: list[dict] = []

    # 1. Reasignaciones operativas de huéspedes
    if reasignaciones:
        propuestas_exitosas = [r for r in reasignaciones if r.get("estado") == "PROPUESTA"]
        sin_alternativa = [r for r in reasignaciones if r.get("estado") == "NO_HAY_ALTERNATIVA"]

        if propuestas_exitosas:
            sugerencias.append({
                "categoria": "REASIGNACION_OPERATIVA",
                "tipo": "operativa",
                "prioridad": "ALTA",
                "icono": "",
                "titulo": f"Reasignación inmediata de {len(propuestas_exitosas)} huéspedes en déficit",
                "diagnostico": f"Se identificaron {len(propuestas_exitosas)} habitaciones ocupadas con pasos de déficit lumínico donde existen habitaciones alternativas con confort pleno.",
                "accion_propuesta": "Ejecutar el cambio de asignación a las habitaciones propuestas en pisos superiores o fachadas con mejor iluminación natural.",
                "impacto_esperado": "Eliminación inmediata del déficit para los huéspedes reasignados sin aumentar el consumo eléctrico.",
                "items": [f"Huésped {p['huesped_id']}: {p['habitacion_actual']} -> {p['habitacion_propuesta']}" for p in propuestas_exitosas[:6]],
            })

        if sin_alternativa:
            sugerencias.append({
                "categoria": "REASIGNACION_OPERATIVA",
                "tipo": "capacidad",
                "prioridad": "CRITICA",
                "icono": "",
                "titulo": f"Falta de capacidad para {len(sin_alternativa)} huéspedes en déficit",
                "diagnostico": f"{len(sin_alternativa)} habitaciones ocupadas sufren déficit pero no existen habitaciones confortables vacías disponibles en la misma torre.",
                "accion_propuesta": "Habilitar habitaciones en la otra torre, aumentar potencia del generador o revisar el horario de uso de zonas comunes para liberar energía.",
                "impacto_esperado": "Evita mantener huéspedes en condiciones no conformes de habitabilidad.",
                "items": [f"Huésped {p['huesped_id']} en {p['habitacion_actual']} (sin alternativa disponible)" for p in sin_alternativa[:6]],
            })

    # 2. Análisis de Vidrios y Transmitancia Visible (VLT)
    zonas_con_deficit = [zid for zid, d in resumen.items() if d.get("pasos_deficit", 0) > 0 and zid in hotel.habitaciones]
    zonas_con_exceso = [zid for zid, d in resumen.items() if d.get("pasos_exceso", 0) > 0 and zid in hotel.habitaciones]

    vidrio_actual_nombre = "VIDRIO_CLARO"
    if hotel.torres and hotel.torres[0].pisos and hotel.torres[0].pisos[0].zonas:
        z0 = hotel.torres[0].pisos[0].zonas[0]
        if z0.ventanas:
            vidrio_actual_nombre = z0.ventanas[0].vidrio.tipo

    if zonas_con_deficit and vidrio_actual_nombre != "VIDRIO_CLARO":
        sugerencias.append({
            "categoria": "VIDRIOS_VLT",
            "tipo": "arquitectonica",
            "prioridad": "MEDIA",
            "icono": "",
            "titulo": "Mejora de transmitancia en ventanas (Vidrio Claro VLT 0.82)",
            "diagnostico": f"Se detectaron {len(zonas_con_deficit)} habitaciones con déficit lumínico diurno. El acristalamiento actual ({vidrio_actual_nombre}) restringe la entrada de luz natural.",
            "accion_propuesta": "Sustituir por VIDRIO_CLARO con transmitancia visible de 0.82 (VLT) en fachadas afectadas.",
            "impacto_esperado": "Aumento del flujo lumínico natural incidente entre 15% y 58%, reduciendo horas de déficit sin consumo de combustible.",
            "items": [f"Zona {z}" for z in zonas_con_deficit[:5]],
        })

    if zonas_con_exceso:
        sugerencias.append({
            "categoria": "VIDRIOS_VLT",
            "tipo": "arquitectonica",
            "prioridad": "MEDIA",
            "icono": "",
            "titulo": "Protección contra deslumbramiento solar en fachadas expuestas",
            "diagnostico": f"{len(zonas_con_exceso)} habitaciones superan los 300 lux máximos (llegando a más de 500 lux en horas pico de sol), generando potencial deslumbramiento visual.",
            "accion_propuesta": "Instalar VIDRIO_CONTROL_SOLAR (VLT 0.52) o persianas/parasoles exteriores en fachadas Este y Oeste para atenuar radiación solar directa.",
            "impacto_esperado": "Confort visual garantizado en horas de radiación directa y mitigación de sobrecalentamiento interior.",
            "items": [f"Zona {z}" for z in zonas_con_exceso[:5]],
        })

    # 3. Análisis de Reflectancia de Paredes
    reflectancia_actual = 0.80
    for z in hotel.zonas.values():
        if z.superficies:
            reflectancia_actual = z.superficies[0].reflectancia
            break

    if zonas_con_deficit and reflectancia_actual < 0.80:
        sugerencias.append({
            "categoria": "REFLECTANCIA_PAREDES",
            "tipo": "arquitectonica",
            "prioridad": "MEDIA",
            "icono": "",
            "titulo": "Optimización de reflectancia de paredes interiores (Blanco 0.80)",
            "diagnostico": f"La reflectancia actual de paredes ({reflectancia_actual:.2f}) limita la distribución de luz reflejada de primer orden por el grafo de influencia.",
            "accion_propuesta": "Pintar superficies interiores en color BLANCO (reflectancia 0.80) o CREMA (0.70).",
            "impacto_esperado": "Incremento de iluminancia indirecta difusa en hasta un 33%, mejorando uniformidad sin fuentes adicionales.",
            "items": [],
        })

    # 4. Capacidad del Generador y Balance Eléctrico
    capacidad_w = generador_info.get("capacidad_w", 22000.0)
    demanda_max_w = generador_info.get("demanda_maxima_w", 0.0)
    estado_gen = generador_info.get("estado", "")
    porcentaje = generador_info.get("porcentaje_usado", 0.0)

    if estado_gen == "CAPACIDAD_LIMITADA" or (zonas_con_deficit and demanda_max_w >= capacidad_w * 0.95):
        potencia_requerida = max(demanda_max_w * 1.25, capacidad_w * 1.3)
        sugerencias.append({
            "categoria": "GENERADOR_ENERGIA",
            "tipo": "electrica",
            "prioridad": "ALTA",
            "icono": "",
            "titulo": "Ampliación de capacidad del generador eléctrico",
            "diagnostico": f"El generador ha alcanzado su límite operativo ({demanda_max_w/1000:.1f} kW de {capacidad_w/1000:.1f} kW disponibles), provocando déficit en zonas de menor prioridad.",
            "accion_propuesta": f"Incrementar la capacidad nominal del generador a al menos {potencia_requerida/1000:.1f} kW para cubrir la demanda objetivo de todas las zonas activas manteniendo el 20% de reserva didáctica.",
            "impacto_esperado": "Eliminación completa de déficits en horas nocturnas para habitaciones y zonas comunes.",
            "items": [],
        })
    elif estado_gen == "ALTA_DEMANDA" or porcentaje > 80.0:
        sugerencias.append({
            "categoria": "GENERADOR_ENERGIA",
            "tipo": "electrica",
            "prioridad": "MEDIA",
            "icono": "",
            "titulo": "Gestión de reserva del generador en picos de demanda",
            "diagnostico": f"La demanda máxima alcanza el {porcentaje:.1f}% de la capacidad del generador, invadiendo el margen de reserva didáctica del 20%.",
            "accion_propuesta": "Reprogramar horarios de zonas recreativas o escalonar el encendido de luminarias de parqueadero (720 W) para mitigar el pico horario.",
            "impacto_esperado": "Operación segura del generador en margen normal (< 80%) sin riesgo de apagón por sobrecarga.",
            "items": [],
        })

    # 5. Distribución por Pisos y Sombras Arrojadas
    deficits_por_piso: dict[int, int] = {}
    for zid, d in resumen.items():
        if zid in hotel.habitaciones and d.get("pasos_deficit", 0) > 0:
            hab = hotel.habitaciones[zid]
            deficits_por_piso[hab.piso] = deficits_por_piso.get(hab.piso, 0) + 1

    if any(deficits_por_piso.get(p, 0) > deficits_por_piso.get(p + 2, 0) for p in [1, 2]):
        sugerencias.append({
            "categoria": "DISTRIBUCION_PISOS",
            "tipo": "operativa",
            "prioridad": "MEDIA",
            "icono": "",
            "titulo": "Priorización de asignación en pisos superiores (Pisos 3 a 6)",
            "diagnostico": "Los pisos 1 y 2 reciben sombra proyectada de la torre vecina (separación de 13 m modelada en Octree) y tienen menor peso de prioridad (1 + 0.10·(p-1)).",
            "accion_propuesta": "Asignar huéspedes preferentemente en pisos 3 o superiores, donde la radiación solar es libre y la prioridad del generador es mayor.",
            "impacto_esperado": "Aprovechamiento de hasta 25% más luz natural incidente y mayor asignación de potencia en caso de racionamiento.",
            "items": [f"Piso {p}: {c} habitaciones con déficit" for p, c in sorted(deficits_por_piso.items())],
        })

    # 6. Modo Reducido y Optimización Horaria
    sugerencias.append({
        "categoria": "MODOS_HORARIOS",
        "tipo": "operativa",
        "prioridad": "INFORMATIVA",
        "icono": "",
        "titulo": "Asegurar transición a modo REDUCIDO en descanso nocturno",
        "diagnostico": "Las habitaciones en descanso no deben marcarse automáticamente como deficitarias si están en modo REDUCIDA (30% de lux objetivo: 60 lux).",
        "accion_propuesta": "Confirmar que entre 22:00 y 06:00 las habitaciones no ocupadas o en descanso permanezcan en modo REDUCIDA para no sobrecargar el generador.",
        "impacto_esperado": "Ahorro de hasta 70% de potencia eléctrica nocturna disponible para las zonas críticas de seguridad.",
        "items": [],
    })

    return sugerencias
