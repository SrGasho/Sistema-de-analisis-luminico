from __future__ import annotations

from collections import Counter

from .arboles import IndiceAVL, IndiceRojoNegro
from .modelo import EstadoIluminacion, Hotel, ResultadoIluminacion

UMBRAL_HABITABLE = 0.90
UMBRAL_CASI = 0.75
MAXIMO_DEFICIT_SEVERO = 0.05

CAUSA_RECOMENDACION = {
    "DEFICIT_NOCTURNO": "Ampliar el horario de iluminación de la zona o revisar la potencia de sus luminarias.",
    "DEFICIT_DIURNO": "Usar iluminación complementaria en las horas de luz natural baja o revisar la orientación de la ventana.",
    "EXCESO_SOLAR": "Aplicar protección solar (cortinas o persianas) en las horas de exceso.",
    "EXCESO_ARTIFICIAL": "Reducir la potencia asignada a la zona en las horas de exceso.",
}


def _causa(resultado: ResultadoIluminacion) -> str | None:
    if resultado.estado.value.startswith("DEFICIT"):
        return "DEFICIT_NOCTURNO" if resultado.periodo == "NOCHE" else "DEFICIT_DIURNO"
    if resultado.estado.value.startswith("EXCESO"):
        return "EXCESO_SOLAR" if resultado.luz_natural >= resultado.luz_artificial else "EXCESO_ARTIFICIAL"
    return None


def evaluar_zona(zona_id: str, resultados: list[ResultadoIluminacion]) -> dict:
    evaluables = [r for r in resultados if r.estado != EstadoIluminacion.DATOS_INSUFICIENTES]
    if not evaluables:
        return {"zona_id": zona_id, "veredicto": "DATOS_INSUFICIENTES", "puntaje": None, "brecha": None, "causa": None, "recomendacion": None}

    n = len(evaluables)
    confortables = sum(r.estado == EstadoIluminacion.CONFORTABLE for r in evaluables)
    leves = sum(r.estado in (EstadoIluminacion.DEFICIT_LEVE, EstadoIluminacion.EXCESO_LEVE) for r in evaluables)
    severos_deficit = sum(r.estado == EstadoIluminacion.DEFICIT_SEVERO for r in evaluables)
    puntaje = (confortables + 0.5 * leves) / n
    proporcion_severa = severos_deficit / n

    if proporcion_severa > MAXIMO_DEFICIT_SEVERO or puntaje < UMBRAL_CASI:
        veredicto = "NO_HABITABLE"
    elif puntaje >= UMBRAL_HABITABLE:
        veredicto = "HABITABLE"
    else:
        veredicto = "CASI_HABITABLE"

    causas = Counter(c for c in (_causa(r) for r in evaluables) if c)
    causa = causas.most_common(1)[0][0] if causas else None
    brecha = round(UMBRAL_HABITABLE - puntaje, 4) if veredicto == "CASI_HABITABLE" else None
    recomendacion = None
    if veredicto == "CASI_HABITABLE" and causa:
        recomendacion = CAUSA_RECOMENDACION[causa]
    return {
        "zona_id": zona_id,
        "veredicto": veredicto,
        "puntaje": round(puntaje, 4),
        "brecha": brecha,
        "causa": causa,
        "recomendacion": recomendacion,
        "pasos_evaluables": n,
        "proporcion_deficit_severo": round(proporcion_severa, 4),
    }


def evaluar_hotel(hotel: Hotel) -> dict:
    evaluaciones = [evaluar_zona(zona.id, zona.resultados) for zona in hotel.zonas.values()]
    indice_avl = IndiceAVL()
    indice_rn = IndiceRojoNegro()
    for evaluacion in evaluaciones:
        if evaluacion["puntaje"] is None:
            continue
        clave = (evaluacion["puntaje"], evaluacion["zona_id"])
        indice_avl.insertar(clave, evaluacion["zona_id"])
        indice_rn.insertar(clave, evaluacion["zona_id"])
    casi = indice_avl.rango((UMBRAL_CASI, ""), (UMBRAL_HABITABLE, "\U0010ffff"))
    return {
        "zonas": evaluaciones,
        "conteo": dict(Counter(e["veredicto"] for e in evaluaciones)),
        "casi_habitables": casi,
        "indices": {
            "avl": {"altura": indice_avl.altura(), "rotaciones": indice_avl.rotaciones, "tamano": indice_avl.tamano},
            "rojo_negro": {"altura": indice_rn.altura(), "rotaciones": indice_rn.rotaciones, "tamano": indice_rn.tamano},
        },
    }
