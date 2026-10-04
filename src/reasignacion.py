from __future__ import annotations

from .modelo import Actividad, EstadoIluminacion, Hotel


def proponer_reasignaciones(hotel: Hotel, resumen: dict[str, dict]) -> list[dict]:
    propuestas = []
    for asignacion in hotel.asignaciones:
        habitacion = hotel.habitaciones.get(asignacion.habitacion_id)
        huesped = hotel.huespedes.get(asignacion.huesped_id)
        if not habitacion or not huesped:
            continue
        datos = resumen.get(habitacion.id, {})
        if datos.get("pasos_deficit", 0) == 0:
            continue
        candidatos = []
        for candidata in hotel.habitaciones.values():
            if candidata.id == habitacion.id or candidata.ocupacion >= candidata.capacidad:
                continue
            if candidata.actividad != Actividad.HABITACION:
                continue
            calidad = resumen.get(candidata.id, {}).get("promedio_lux", 0.0)
            if resumen.get(candidata.id, {}).get("pasos_deficit", 1) > 0:
                continue
            score = calidad - 10.0 * abs(candidata.piso - habitacion.piso)
            candidatos.append((score, candidata.id))
        candidatos.sort(reverse=True)
        if candidatos:
            propuestas.append({"huesped_id": huesped.id, "habitacion_actual": habitacion.id, "habitacion_propuesta": candidatos[0][1], "estado": "PROPUESTA", "score": candidatos[0][0]})
        else:
            propuestas.append({"huesped_id": huesped.id, "habitacion_actual": habitacion.id, "habitacion_propuesta": None, "estado": "NO_HAY_ALTERNATIVA", "score": None})
    return propuestas
