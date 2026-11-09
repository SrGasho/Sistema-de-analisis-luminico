from __future__ import annotations

import copy
import time
from typing import Callable

from .io_datos import _completar_defaults

RANGOS_POR_DEFECTO = {
    "presupuesto_evaluaciones": 30,
    "rondas_maximas": 3,
    "paredes": ["BLANCO", "CREMA", "GRIS_CLARO"],
    "vidrios": ["VIDRIO_CLARO", "VIDRIO_LOW_E", "VIDRIO_CONTROL_SOLAR"],
    "orientaciones": [["ESTE", "NORTE", "OESTE", "SUR"], ["ESTE", "NORTE", "OESTE"], ["NORTE", "SUR"]],
    "horarios": {
        "COCINA": {"inicio_activa": [6, 8], "fin_activa": [22, 24]},
        "RECREACION": {"inicio_activa": [8, 10], "fin_activa": [22, 23]},
    },
}
ACTIVIDADES_CON_VENTANAS = ("HABITACION", "COCINA", "RECREACION")


def buscar_reestructuracion(config: dict, ejecutar: Callable[[dict], dict]) -> dict:
    rangos = _rangos(config)
    inicio = time.perf_counter()
    actual = _completar_defaults(copy.deepcopy(config))
    evaluacion = ejecutar(copy.deepcopy(actual))
    inicial = _metricas(evaluacion)
    mejor = inicial
    evaluaciones = 1
    pasos: list[dict] = []
    presupuesto = int(rangos["presupuesto_evaluaciones"])

    for _ in range(int(rangos["rondas_maximas"])):
        mejora_en_ronda = False
        for actividad in _actividades_priorizadas(evaluacion["layout"]):
            for ruta, campo, valor in _palancas(actual, actividad, rangos):
                if evaluaciones >= presupuesto:
                    break
                candidata = copy.deepcopy(actual)
                anterior = candidata.get(ruta, {}).get(actividad, {}).get(campo)
                candidata.setdefault(ruta, {}).setdefault(actividad, {})[campo] = valor
                resultado = ejecutar(candidata)
                evaluaciones += 1
                metricas = _metricas(resultado)
                if _clave(metricas) > _clave(mejor):
                    actual, evaluacion, mejor = candidata, resultado, metricas
                    pasos.append({"actividad": actividad, "campo": campo, "anterior": anterior, "nuevo": valor, "puntaje": metricas["puntaje"], "no_habitables": metricas["no_habitables"]})
                    mejora_en_ronda = True
        if not mejora_en_ronda or evaluaciones >= presupuesto:
            break

    if pasos:
        estado = "MEJORA_ENCONTRADA"
    elif not _actividades_priorizadas(evaluacion["layout"]):
        estado = "SIN_ZONAS_POR_MEJORAR"
    else:
        estado = "SIN_MEJORA"
    return {
        "estado": estado,
        "presupuesto_evaluaciones": presupuesto,
        "evaluaciones_usadas": evaluaciones,
        "segundos": round(time.perf_counter() - inicio, 1),
        "inicial": inicial,
        "final": mejor,
        "pasos": pasos,
        "configuracion_propuesta": actual,
        "rangos": rangos,
    }


def _rangos(config: dict) -> dict:
    definidos = config.get("parametros_evaluacion", {}).get("reestructuracion", {})
    return copy.deepcopy({**RANGOS_POR_DEFECTO, **definidos})


def _metricas(resultado: dict) -> dict:
    habitabilidad = resultado["habitabilidad"]
    return {
        "puntaje": habitabilidad["puntaje_hotel"]["ponderado"] or 0.0,
        "habitables": habitabilidad["conteo"].get("HABITABLE", 0),
        "casi_habitables": habitabilidad["conteo"].get("CASI_HABITABLE", 0),
        "no_habitables": habitabilidad["conteo"].get("NO_HABITABLE", 0),
        "energia_wh": resultado["resumen"]["energia_total_wh"],
    }


def _clave(metricas: dict) -> tuple:
    return (round(metricas["puntaje"], 4), -metricas["no_habitables"], -round(metricas["energia_wh"], 1))


def _actividades_priorizadas(layout: dict) -> list[str]:
    conteo: dict[str, int] = {}
    for torre in layout["torres"]:
        for piso in torre["pisos"]:
            for zona in piso["zonas"]:
                if zona["veredicto"] in ("CASI_HABITABLE", "NO_HABITABLE"):
                    conteo[zona["actividad"]] = conteo.get(zona["actividad"], 0) + 1
    return sorted(conteo, key=lambda actividad: -conteo[actividad])


def _palancas(config: dict, actividad: str, rangos: dict) -> list[tuple[str, str, object]]:
    acabado = config.get("acabados", {}).get(actividad, {})
    palancas: list[tuple[str, str, object]] = []
    for pared in rangos["paredes"]:
        if pared != acabado.get("pared"):
            palancas.append(("acabados", "pared", pared))
    if actividad in ACTIVIDADES_CON_VENTANAS and acabado.get("vidrio") is not None:
        for vidrio in rangos["vidrios"]:
            if vidrio != acabado.get("vidrio"):
                palancas.append(("acabados", "vidrio", vidrio))
        for orientaciones in rangos["orientaciones"]:
            if orientaciones != acabado.get("orientaciones"):
                palancas.append(("acabados", "orientaciones", list(orientaciones)))
    horario_actual = config.get("horarios", {}).get(actividad, {})
    for campo, valores in rangos["horarios"].get(actividad, {}).items():
        for valor in valores:
            if valor != horario_actual.get(campo):
                palancas.append(("horarios", campo, valor))
    return palancas
