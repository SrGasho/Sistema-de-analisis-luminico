from __future__ import annotations

import copy
from typing import Callable


ACTIVIDADES = ["HABITACION", "COCINA", "RECREACION", "PARQUEADERO"]


def _vidrio_claro_habitaciones(config: dict) -> None:
    config.setdefault("acabados", {}).setdefault("HABITACION", {})["vidrio"] = "VIDRIO_CLARO"


def _paredes_blancas(config: dict) -> None:
    acabados = config.setdefault("acabados", {})
    for actividad in ACTIVIDADES:
        acabados.setdefault(actividad, {})["pared"] = "BLANCO"


def _generador_mas_veinte(config: dict) -> None:
    config["generador"]["capacidad_kw"] = round(config["generador"]["capacidad_kw"] * 1.2, 2)


def _objetivo_habitacion_180(config: dict) -> None:
    config["perfiles_iluminacion"]["HABITACION"]["objetivo"] = 180


CANDIDATAS: list[tuple[str, str, Callable[[dict], None]]] = [
    ("VIDRIO_CLARO_HABITACIONES", "Usar VIDRIO_CLARO en las habitaciones", _vidrio_claro_habitaciones),
    ("PAREDES_BLANCAS", "Pintar las paredes en BLANCO", _paredes_blancas),
    ("GENERADOR_MAS_20", "Aumentar 20 % la capacidad del generador", _generador_mas_veinte),
    ("OBJETIVO_HABITACION_180", "Bajar el objetivo de habitación a 180 lux", _objetivo_habitacion_180),
]


def medir_mejoras(config: dict, ejecutar: Callable[[dict], dict]) -> list[dict]:
    base = ejecutar(copy.deepcopy(config))
    puntaje_antes = base["habitabilidad"]["puntaje_hotel"]["ponderado"]
    medidas = []
    for identificador, titulo, aplicar in CANDIDATAS:
        candidata = copy.deepcopy(config)
        aplicar(candidata)
        if candidata == config:
            continue
        resultado = ejecutar(candidata)
        puntaje_despues = resultado["habitabilidad"]["puntaje_hotel"]["ponderado"]
        medidas.append({
            "id": identificador,
            "titulo": titulo,
            "puntaje_antes": puntaje_antes,
            "puntaje_despues": puntaje_despues,
            "delta": round(puntaje_despues - puntaje_antes, 4),
            "conteo_despues": resultado["habitabilidad"]["conteo"],
        })
    return sorted(medidas, key=lambda medida: -medida["delta"])
