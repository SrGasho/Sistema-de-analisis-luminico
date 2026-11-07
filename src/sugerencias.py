from __future__ import annotations

from collections import Counter

from .modelo import Hotel

NO_O_CASI = ("NO_HABITABLE", "CASI_HABITABLE")
IMPACTO_MEDIDO = "Efecto medido en la sección Mejoras medidas."


def _sugerencia(categoria: str, tipo: str, prioridad: str, titulo: str, diagnostico: str, accion: str, items: list[str]) -> dict:
    return {
        "categoria": categoria,
        "tipo": tipo,
        "prioridad": prioridad,
        "icono": "",
        "titulo": titulo,
        "diagnostico": diagnostico,
        "accion_propuesta": accion,
        "impacto_esperado": IMPACTO_MEDIDO,
        "items": items,
    }


def generar_sugerencias_habitabilidad(
    hotel: Hotel,
    resumen: dict[str, dict],
    resultados: list,
    generador_info: dict,
    reasignaciones: list[dict],
    habitabilidad: dict | None = None,
) -> list[dict]:
    sugerencias: list[dict] = []
    veredictos = {e["zona_id"]: e for e in (habitabilidad or {}).get("zonas", [])}
    habitaciones = list(hotel.habitaciones)
    no_habitables = [zid for zid in habitaciones if veredictos.get(zid, {}).get("veredicto") == "NO_HABITABLE"]
    casi = [zid for zid in habitaciones if veredictos.get(zid, {}).get("veredicto") == "CASI_HABITABLE"]

    propuestas = [r for r in reasignaciones if r.get("estado") == "PROPUESTA"]
    sin_alternativa = [r for r in reasignaciones if r.get("estado") == "NO_HAY_ALTERNATIVA"]
    if propuestas:
        sugerencias.append(_sugerencia(
            "REASIGNACION_OPERATIVA", "operativa", "ALTA",
            f"Reasignar {len(propuestas)} huéspedes a habitaciones habitables",
            f"{len(propuestas)} habitaciones ocupadas no son habitables y existen habitaciones libres que sí lo son.",
            "Cambiar la asignación de esos huéspedes a las habitaciones propuestas.",
            [f"Huésped {p['huesped_id']}: {p['habitacion_actual']} -> {p['habitacion_propuesta']}" for p in propuestas[:6]],
        ))
    if sin_alternativa:
        sugerencias.append(_sugerencia(
            "REASIGNACION_OPERATIVA", "capacidad", "CRITICA",
            f"Sin habitación alternativa para {len(sin_alternativa)} huéspedes",
            f"{len(sin_alternativa)} habitaciones ocupadas no son habitables y no hay habitaciones habitables con cama libre que cumplan sus restricciones.",
            "Revisar la capacidad del generador o la asignación de zonas comunes en horario nocturno.",
            [f"Huésped {p['huesped_id']} en {p['habitacion_actual']}" for p in sin_alternativa[:6]],
        ))

    if casi:
        sugerencias.append(_sugerencia(
            "CASI_HABITABLE", "operativa", "MEDIA",
            f"{len(casi)} habitaciones están cerca de ser habitables",
            "Su puntaje está entre el umbral casi habitable y el umbral habitable.",
            "Aplicar la recomendación específica de cada habitación.",
            [f"{zid}: {veredictos[zid].get('recomendacion') or 'sin recomendación específica'}" for zid in casi[:6]],
        ))

    deficit_diurno = [zid for zid in no_habitables if str(veredictos[zid].get("causa")) == "DEFICIT_DIURNO"]
    if deficit_diurno:
        vidrios = Counter(hotel.habitaciones[zid].ventanas[0].vidrio.tipo for zid in deficit_diurno if hotel.habitaciones[zid].ventanas)
        if vidrios:
            vidrio_actual, usos = vidrios.most_common(1)[0]
            if vidrio_actual != "VIDRIO_CLARO":
                sugerencias.append(_sugerencia(
                    "VIDRIOS_VLT", "arquitectonica", "MEDIA",
                    "Cambiar el vidrio en habitaciones con déficit diurno",
                    f"{len(deficit_diurno)} habitaciones no habitables tienen déficit en horas de luz; {usos} usan {vidrio_actual}.",
                    "Usar VIDRIO_CLARO en esas habitaciones.",
                    [f"Zona {zid}" for zid in deficit_diurno[:5]],
                ))

    exceso_solar = [zid for zid in habitaciones if veredictos.get(zid, {}).get("veredicto") in NO_O_CASI and str(veredictos[zid].get("causa")) == "EXCESO_SOLAR"]
    if exceso_solar:
        sugerencias.append(_sugerencia(
            "VIDRIOS_VLT", "arquitectonica", "MEDIA",
            "Controlar la luz solar en habitaciones con exceso",
            f"{len(exceso_solar)} habitaciones superan su máximo de iluminación en horas de sol.",
            "Usar protección solar o VIDRIO_CONTROL_SOLAR en las fachadas afectadas.",
            [f"Zona {zid}" for zid in exceso_solar[:5]],
        ))

    afectadas = [zid for zid in habitaciones if veredictos.get(zid, {}).get("veredicto") in NO_O_CASI]
    if afectadas:
        reflectancias = [hotel.habitaciones[zid].superficies[0].reflectancia for zid in afectadas if hotel.habitaciones[zid].superficies]
        promedio = sum(reflectancias) / len(reflectancias) if reflectancias else None
        if promedio is not None and promedio < 0.80:
            sugerencias.append(_sugerencia(
                "REFLECTANCIA_PAREDES", "arquitectonica", "MEDIA",
                "Aumentar la reflectancia de las paredes",
                f"Las habitaciones afectadas tienen una reflectancia media de {promedio:.2f}.",
                "Pintar las paredes en BLANCO (reflectancia 0,80).",
                [],
            ))

    if generador_info.get("estado") in ("CAPACIDAD_LIMITADA", "ALTA_DEMANDA"):
        capacidad_kw = hotel.generador.capacidad_kw
        requerida_kw = 1.20 * hotel.generador.demanda_objetivo_maxima / 1000.0
        sugerencias.append(_sugerencia(
            "GENERADOR_ENERGIA", "electrica", "ALTA" if generador_info.get("estado") == "CAPACIDAD_LIMITADA" else "MEDIA",
            "Revisar la capacidad del generador",
            f"La demanda objetivo máxima es {hotel.generador.demanda_objetivo_maxima / 1000.0:.1f} kW. Con la reserva del 20 % se requieren {requerida_kw:.1f} kW frente a {capacidad_kw:.1f} kW instalados.",
            f"Instalar al menos {requerida_kw:.1f} kW para cubrir los objetivos de todas las zonas.",
            [],
        ))

    if no_habitables:
        por_piso = Counter(hotel.habitaciones[zid].piso for zid in no_habitables)
        sugerencias.append(_sugerencia(
            "DISTRIBUCION_PISOS", "operativa", "INFORMATIVA",
            "Habitaciones no habitables por piso",
            f"Distribución de las {len(no_habitables)} habitaciones no habitables según su piso.",
            "Revisar la asignación de huéspedes en los pisos con más habitaciones no habitables.",
            [f"Piso {piso}: {total} habitaciones" for piso, total in sorted(por_piso.items())],
        ))

    nocturnas = [zid for zid in habitaciones if veredictos.get(zid, {}).get("veredicto") in NO_O_CASI and str(veredictos[zid].get("causa")) == "DEFICIT_NOCTURNO"]
    if nocturnas:
        sugerencias.append(_sugerencia(
            "MODOS_HORARIOS", "operativa", "MEDIA",
            "Revisar la iluminación nocturna de habitaciones",
            f"{len(nocturnas)} habitaciones tienen déficit en horas nocturnas.",
            "Ampliar el horario de iluminación o revisar la potencia de las luminarias de esas zonas.",
            [f"Zona {zid}" for zid in nocturnas[:5]],
        ))

    return sugerencias
