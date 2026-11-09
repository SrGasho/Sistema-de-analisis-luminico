from __future__ import annotations

import copy
import math
from typing import Callable

from .io_datos import cargar_hotel_data

PROBLEMA = ("NO_HABITABLE", "CASI_HABITABLE")
MAXIMO_ZONAS_LISTADAS = 12


def medir_mejoras(config: dict, ejecutar: Callable[[dict], dict]) -> dict:
    """Propone cambios a partir de los problemas del escenario y mide cada uno con una simulación completa."""
    base = ejecutar(copy.deepcopy(config))
    puntaje_antes = base["habitabilidad"]["puntaje_hotel"]["ponderado"] or 0.0
    conteo_antes = base["habitabilidad"]["conteo"]
    problemas = [z for z in base["habitabilidad"]["zonas"] if z["veredicto"] in PROBLEMA]
    if not problemas:
        return {"estado": "TODO_HABITABLE", "puntaje": puntaje_antes, "probadas": 0, "mejoras": [], "sin_efecto": []}

    medidas = []
    for identificador, titulo, descripcion, zonas, aplicar in _candidatas(config, base, problemas):
        candidata = copy.deepcopy(config)
        aplicar(candidata)
        resultado = ejecutar(candidata)
        puntaje_despues = resultado["habitabilidad"]["puntaje_hotel"]["ponderado"] or 0.0
        medidas.append({
            "id": identificador,
            "titulo": titulo,
            "descripcion": descripcion,
            "zonas": zonas[:MAXIMO_ZONAS_LISTADAS],
            "zonas_total": len(zonas),
            "puntaje_antes": puntaje_antes,
            "puntaje_despues": puntaje_despues,
            "delta": round(puntaje_despues - puntaje_antes, 4),
            "conteo_antes": conteo_antes,
            "conteo_despues": resultado["habitabilidad"]["conteo"],
        })
    con_efecto = sorted((m for m in medidas if m["delta"] > 0), key=lambda m: -m["delta"])
    return {
        "estado": "CON_MEJORAS" if con_efecto else "SIN_EFECTO",
        "puntaje": puntaje_antes,
        "probadas": len(medidas),
        "mejoras": con_efecto,
        "sin_efecto": [m["titulo"] for m in medidas if m["delta"] <= 0],
    }


def _candidatas(config: dict, base: dict, problemas: list[dict]) -> list[tuple]:
    hotel = cargar_hotel_data(copy.deepcopy(config))
    personal = config.get("zonas_personalizadas", {})
    por_causa: dict[str, list[str]] = {}
    for evaluacion in problemas:
        por_causa.setdefault(str(evaluacion.get("causa")), []).append(evaluacion["zona_id"])

    def acabado(zona_id: str, campo: str):
        zona = hotel.zonas[zona_id]
        valor = personal.get(zona_id, {}).get(campo)
        return valor if valor is not None else config.get("acabados", {}).get(zona.actividad.value, {}).get(campo)

    def por_zona(zonas: list[str], cambios: dict) -> Callable[[dict], None]:
        def aplicar(candidata: dict) -> None:
            destino = candidata.setdefault("zonas_personalizadas", {})
            for zona_id in zonas:
                destino.setdefault(zona_id, {}).update(cambios)
        return aplicar

    candidatas = []
    con_ventanas = lambda zonas: [z for z in zonas if hotel.zonas[z].ventanas]

    soleadas = [z for z in con_ventanas(por_causa.get("EXCESO_SOLAR", [])) if acabado(z, "vidrio") != "VIDRIO_CONTROL_SOLAR"]
    if soleadas:
        candidatas.append((
            "VIDRIO_CONTROL_SOLAR", f"Vidrio de control solar en {len(soleadas)} zonas con exceso de sol",
            "Cambia el vidrio de esas zonas por VIDRIO_CONTROL_SOLAR, que deja pasar menos luz.",
            soleadas, por_zona(soleadas, {"vidrio": "VIDRIO_CONTROL_SOLAR"}),
        ))

    deficit = por_causa.get("DEFICIT_NOCTURNO", []) + por_causa.get("DEFICIT_DIURNO", [])
    debiles = [z for z in deficit if "luminaria_w" in personal.get(z, {}) and hotel.zonas[z].fuente_id
               and personal[z]["luminaria_w"] < config["luminarias"][hotel.zonas[z].actividad.value]["potencia_w"]]
    if debiles:
        def reponer(candidata: dict) -> None:
            for zona_id in debiles:
                candidata["zonas_personalizadas"][zona_id].pop("luminaria_w", None)
        candidatas.append((
            "REPONER_LUMINARIAS", f"Reponer las luminarias de {len(debiles)} zonas",
            "Devuelve a esas zonas la potencia de luminaria de su actividad (hoy tienen menos o están dañadas).",
            debiles, reponer,
        ))

    generador = base.get("generador", {})
    if generador.get("pasos_emergencia", 0) > 0:
        actual = float(config["generador"]["capacidad_kw"])
        requerida = math.ceil(1.2 * generador.get("demanda_objetivo_maxima_w", 0.0) / 100.0) / 10.0
        nueva = max(requerida, round(actual * 1.2, 1))

        def ampliar(candidata: dict) -> None:
            candidata["generador"]["capacidad_kw"] = nueva
        candidatas.append((
            "AMPLIAR_GENERADOR", f"Generador de {nueva:.1f} kW",
            f"Hoy tiene {actual:.1f} kW y alguna zona se quedó sin su mínimo. {nueva:.1f} kW cubren los objetivos de todas las zonas con un 20 % de reserva.",
            [], ampliar,
        ))

    oscuras = con_ventanas(por_causa.get("DEFICIT_DIURNO", []))
    sin_claro = [z for z in oscuras if acabado(z, "vidrio") != "VIDRIO_CLARO"]
    if sin_claro:
        candidatas.append((
            "VIDRIO_CLARO", f"Vidrio claro en {len(sin_claro)} zonas con falta de luz de día",
            "Cambia el vidrio de esas zonas por VIDRIO_CLARO, el que deja pasar más luz.",
            sin_claro, por_zona(sin_claro, {"vidrio": "VIDRIO_CLARO"}),
        ))
    sin_blanco = [z for z in oscuras if acabado(z, "pared") != "BLANCO"]
    if sin_blanco:
        candidatas.append((
            "PAREDES_BLANCAS", f"Paredes blancas en {len(sin_blanco)} zonas con falta de luz de día",
            "Pinta de blanco las paredes de esas zonas para que reflejen más la luz que entra.",
            sin_blanco, por_zona(sin_blanco, {"pared": "BLANCO"}),
        ))
    return candidatas
