from __future__ import annotations

from .modelo import Hotel


def proponer_reasignaciones(hotel: Hotel, resumen: dict[str, dict], veredictos: dict[str, dict]) -> list[dict]:
    pesos = hotel.parametros.get("reasignacion", {})
    w_luz = float(pesos.get("w_luz", 0.5))
    w_actividad = float(pesos.get("w_actividad", 0.2))
    w_energia = float(pesos.get("w_energia", 0.2))
    w_cambio = float(pesos.get("w_cambio", 0.1))
    piso_maximo = max(piso.numero for torre in hotel.torres for piso in torre.pisos)
    energia_maxima = max((datos.get("energia_wh", 0.0) for datos in resumen.values()), default=0.0) or 1.0

    propuestas = []
    for asignacion in hotel.asignaciones:
        habitacion = hotel.habitaciones.get(asignacion.habitacion_id)
        huesped = hotel.huespedes.get(asignacion.huesped_id)
        if habitacion is None or huesped is None:
            continue
        if veredictos.get(habitacion.id, {}).get("veredicto") != "NO_HABITABLE":
            continue

        candidatos = []
        for candidata in hotel.habitaciones.values():
            if candidata.id == habitacion.id or not candidata.disponible:
                continue
            evaluacion = veredictos.get(candidata.id, {})
            if evaluacion.get("veredicto") != "HABITABLE":
                continue
            calidad = evaluacion.get("puntaje") or 0.0
            ahorro = 1.0 - min(1.0, resumen.get(candidata.id, {}).get("energia_wh", 0.0) / energia_maxima)
            penalizacion = abs(candidata.piso - habitacion.piso) / max(1, piso_maximo)
            score = w_luz * calidad + w_actividad * 1.0 + w_energia * ahorro - w_cambio * penalizacion
            candidatos.append((round(score, 4), candidata.id))
        candidatos.sort(reverse=True)

        if candidatos:
            score, destino = candidatos[0]
            propuestas.append({"huesped_id": huesped.id, "habitacion_actual": habitacion.id, "habitacion_propuesta": destino, "estado": "PROPUESTA", "score": score})
        else:
            propuestas.append({"huesped_id": huesped.id, "habitacion_actual": habitacion.id, "habitacion_propuesta": None, "estado": "NO_HAY_ALTERNATIVA", "score": None})
    return propuestas
