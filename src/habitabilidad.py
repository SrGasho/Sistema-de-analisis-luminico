from __future__ import annotations

from collections import Counter

from .arboles import IndiceAVL, IndiceRojoNegro
from .modelo import EstadoIluminacion, Hotel, ResultadoIluminacion

CAUSA_RECOMENDACION = {
    "DEFICIT_NOCTURNO": "Ampliar el horario de iluminación de la zona o revisar la potencia de sus luminarias.",
    "DEFICIT_DIURNO": "Usar iluminación complementaria en las horas de luz natural baja o revisar la orientación de la ventana.",
    "EXCESO_SOLAR": "Aplicar protección solar (cortinas o persianas) en las horas de exceso.",
    "EXCESO_ARTIFICIAL": "Reducir la potencia asignada a la zona en las horas de exceso.",
}


def umbrales(hotel: Hotel) -> dict[str, float]:
    habitabilidad = hotel.parametros.get("habitabilidad", {})
    puntaje = hotel.parametros.get("puntaje", {})
    return {
        "umbral_habitable": float(habitabilidad.get("umbral_habitable", 0.90)),
        "umbral_casi": float(habitabilidad.get("umbral_casi", 0.75)),
        "maximo_deficit_severo": float(habitabilidad.get("maximo_deficit_severo", 0.05)),
        "q_confortable": float(puntaje.get("q_confortable", 1.0)),
        "q_leve": float(puntaje.get("q_leve", 0.5)),
        "q_severo": float(puntaje.get("q_severo", 0.0)),
    }


def _causa(resultado: ResultadoIluminacion) -> str | None:
    if resultado.estado.value.startswith("DEFICIT"):
        return "DEFICIT_NOCTURNO" if resultado.periodo == "NOCHE" else "DEFICIT_DIURNO"
    if resultado.estado.value.startswith("EXCESO"):
        return "EXCESO_SOLAR" if resultado.luz_natural >= resultado.luz_artificial else "EXCESO_ARTIFICIAL"
    return None


def _puntaje(resultados: list[ResultadoIluminacion], limites: dict[str, float]) -> dict | None:
    evaluables = [r for r in resultados if r.estado != EstadoIluminacion.DATOS_INSUFICIENTES]
    if not evaluables:
        return None
    n = len(evaluables)
    suma_q = 0.0
    for resultado in evaluables:
        if resultado.estado == EstadoIluminacion.CONFORTABLE:
            suma_q += limites["q_confortable"]
        elif resultado.estado in (EstadoIluminacion.DEFICIT_LEVE, EstadoIluminacion.EXCESO_LEVE):
            suma_q += limites["q_leve"]
        else:
            suma_q += limites["q_severo"]
    severos = sum(r.estado == EstadoIluminacion.DEFICIT_SEVERO for r in evaluables)
    deficit = sum(r.estado.value.startswith("DEFICIT") for r in evaluables)
    exceso = sum(r.estado.value.startswith("EXCESO") for r in evaluables)
    return {
        "puntaje": suma_q / n,
        "proporcion_severa": severos / n,
        "proporcion_deficit": deficit / n,
        "proporcion_exceso": exceso / n,
        "pasos": n,
    }


def evaluar_zona(zona_id: str, resultados: list[ResultadoIluminacion], limites: dict[str, float], peso: float) -> dict:
    total = _puntaje(resultados, limites)
    dia = _puntaje([r for r in resultados if r.periodo != "NOCHE"], limites)
    noche = _puntaje([r for r in resultados if r.periodo == "NOCHE"], limites)
    base = {
        "zona_id": zona_id,
        "peso": round(peso, 4),
        "puntaje_dia": round(dia["puntaje"], 4) if dia else None,
        "puntaje_noche": round(noche["puntaje"], 4) if noche else None,
    }
    if total is None:
        return {**base, "veredicto": "DATOS_INSUFICIENTES", "puntaje": None, "brecha": None, "causa": None, "recomendacion": None, "pasos_evaluables": 0, "proporcion_deficit_severo": None, "proporcion_deficit": None, "proporcion_exceso": None}

    puntaje = total["puntaje"]
    severa = total["proporcion_severa"]
    if severa > limites["maximo_deficit_severo"] or puntaje < limites["umbral_casi"]:
        veredicto = "NO_HABITABLE"
    elif puntaje >= limites["umbral_habitable"]:
        veredicto = "HABITABLE"
    else:
        veredicto = "CASI_HABITABLE"

    causas = Counter(c for c in (_causa(r) for r in resultados if r.estado != EstadoIluminacion.DATOS_INSUFICIENTES) if c)
    causa = causas.most_common(1)[0][0] if causas else None
    casi = veredicto == "CASI_HABITABLE"
    return {
        **base,
        "veredicto": veredicto,
        "puntaje": round(puntaje, 4),
        "brecha": round(limites["umbral_habitable"] - puntaje, 4) if casi else None,
        "causa": causa,
        "recomendacion": CAUSA_RECOMENDACION[causa] if casi and causa else None,
        "pasos_evaluables": total["pasos"],
        "proporcion_deficit_severo": round(severa, 4),
        "proporcion_deficit": round(total["proporcion_deficit"], 4),
        "proporcion_exceso": round(total["proporcion_exceso"], 4),
    }


def _promedio_ponderado(evaluaciones: list[dict], campo: str) -> float | None:
    validas = [e for e in evaluaciones if e.get(campo) is not None]
    peso_total = sum(e["peso"] for e in validas)
    if not peso_total:
        return None
    return round(sum(e["peso"] * e[campo] for e in validas) / peso_total, 4)


def evaluar_hotel(hotel: Hotel) -> dict:
    limites = umbrales(hotel)
    evaluaciones = []
    for zona in hotel.zonas.values():
        peso = hotel.perfiles_iluminacion[zona.actividad].prioridad * (1.0 + 0.10 * (zona.piso - 1))
        evaluaciones.append(evaluar_zona(zona.id, zona.resultados, limites, peso))

    indice_avl = IndiceAVL()
    indice_rn = IndiceRojoNegro()
    for evaluacion in evaluaciones:
        if evaluacion["puntaje"] is None:
            continue
        clave = (evaluacion["puntaje"], evaluacion["zona_id"])
        indice_avl.insertar(clave, evaluacion["zona_id"])
        indice_rn.insertar(clave, evaluacion["zona_id"])

    return {
        "zonas": evaluaciones,
        "conteo": dict(Counter(e["veredicto"] for e in evaluaciones)),
        "puntaje_hotel": {
            "ponderado": _promedio_ponderado(evaluaciones, "puntaje"),
            "dia": _promedio_ponderado(evaluaciones, "puntaje_dia"),
            "noche": _promedio_ponderado(evaluaciones, "puntaje_noche"),
        },
        "umbrales": limites,
        "casi_habitables": indice_avl.rango((limites["umbral_casi"], ""), (limites["umbral_habitable"], "\U0010ffff")),
        "indices": {
            "avl": {"altura": indice_avl.altura(), "rotaciones": indice_avl.rotaciones, "tamano": indice_avl.tamano},
            "rojo_negro": {"altura": indice_rn.altura(), "rotaciones": indice_rn.rotaciones, "tamano": indice_rn.tamano},
        },
    }
