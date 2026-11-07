from __future__ import annotations

from .arboles import IndiceAVL
from .modelo import HabitacionHotel, Hotel

ORIENTACIONES = {(1, 0): "ESTE", (0, 1): "NORTE", (-1, 0): "OESTE", (0, -1): "SUR"}


def orientacion(habitacion: HabitacionHotel) -> str | None:
    if not habitacion.ventanas:
        return None
    normal = habitacion.ventanas[0].normal
    return ORIENTACIONES.get((round(normal.x), round(normal.y)))


def leer_restricciones(restricciones: list[str]) -> dict:
    salida = {"misma_torre": False, "piso_maximo": None, "orientacion": None}
    for texto in restricciones:
        nombre, _, valor = texto.partition(":")
        if nombre == "MISMA_TORRE" and not valor:
            salida["misma_torre"] = True
        elif nombre == "PISO_MAXIMO" and valor.isdigit() and int(valor) >= 1:
            salida["piso_maximo"] = int(valor)
        elif nombre == "ORIENTACION" and valor in ORIENTACIONES.values():
            salida["orientacion"] = valor
        else:
            raise ValueError(f"Restricción de huésped no reconocida: {texto}")
    return salida


def proponer_reasignaciones(hotel: Hotel, resumen: dict[str, dict], veredictos: dict[str, dict]) -> tuple[list[dict], dict]:
    pesos = hotel.parametros.get("reasignacion", {})
    w_luz = float(pesos.get("w_luz", 0.5))
    w_actividad = float(pesos.get("w_actividad", 0.2))
    w_energia = float(pesos.get("w_energia", 0.2))
    w_cambio = float(pesos.get("w_cambio", 0.1))
    piso_maximo = max(piso.numero for torre in hotel.torres for piso in torre.pisos)
    energia_maxima = max((datos.get("energia_wh", 0.0) for datos in resumen.values()), default=0.0) or 1.0

    bolsa = IndiceAVL()
    libres: dict[str, int] = {}
    claves: dict[str, tuple] = {}
    iniciales: dict[tuple[str, int], int] = {}
    for habitacion in hotel.habitaciones.values():
        evaluacion = veredictos.get(habitacion.id, {})
        if not habitacion.disponible or evaluacion.get("veredicto") != "HABITABLE":
            continue
        ahorro = 1.0 - min(1.0, resumen.get(habitacion.id, {}).get("energia_wh", 0.0) / energia_maxima)
        calidad = w_luz * (evaluacion.get("puntaje") or 0.0) + w_energia * ahorro
        clave = (habitacion.torre_id, habitacion.piso, -calidad, habitacion.id)
        bolsa.insertar(clave, habitacion)
        libres[habitacion.id] = habitacion.capacidad - habitacion.ocupacion
        claves[habitacion.id] = clave
        iniciales[(habitacion.torre_id, habitacion.piso)] = iniciales.get((habitacion.torre_id, habitacion.piso), 0) + 1
    comparaciones_construccion = bolsa.comparaciones
    tamano_inicial = bolsa.tamano
    altura_inicial = bolsa.altura()

    propuestas = []
    huespedes_movidos = 0
    for asignacion in hotel.asignaciones:
        habitacion = hotel.habitaciones.get(asignacion.habitacion_id)
        huesped = hotel.huespedes.get(asignacion.huesped_id)
        if habitacion is None or huesped is None:
            continue
        if veredictos.get(habitacion.id, {}).get("veredicto") != "NO_HABITABLE":
            continue
        huespedes_movidos += 1
        reglas = leer_restricciones(huesped.restricciones)
        pisos = [
            (torre.id, piso.numero)
            for torre in hotel.torres
            if not reglas["misma_torre"] or torre.id == habitacion.torre_id
            for piso in torre.pisos
            if reglas["piso_maximo"] is None or piso.numero <= reglas["piso_maximo"]
        ]

        revisadas = []
        for torre_id, numero in pisos:
            penalizacion = w_cambio * abs(numero - habitacion.piso) / max(1, piso_maximo)
            mejor_piso = None
            actual = bolsa.sucesor((torre_id, numero, float("-inf"), ""))
            while actual is not None and actual[0][:2] == (torre_id, numero):
                clave, candidata = actual
                calidad = -clave[2]
                if mejor_piso is not None and calidad + w_actividad - penalizacion <= mejor_piso:
                    break
                coincide = reglas["orientacion"] is None or orientacion(candidata) == reglas["orientacion"]
                score = round(calidad + w_actividad * (1.0 if coincide else 0.0) - penalizacion, 4)
                revisadas.append({"habitacion_id": candidata.id, "score": score})
                mejor_piso = score if mejor_piso is None else max(mejor_piso, score)
                if reglas["orientacion"] is None:
                    break
                actual = bolsa.siguiente(clave)

        if revisadas:
            elegida = max(revisadas, key=lambda r: (r["score"], r["habitacion_id"]))
            destino = elegida["habitacion_id"]
            libres[destino] -= 1
            if libres[destino] == 0:
                bolsa.eliminar(claves[destino])
            descartadas = [{**r, "motivo": "MENOR_PUNTAJE"} for r in revisadas if r is not elegida]
            propuestas.append({"huesped_id": huesped.id, "habitacion_actual": habitacion.id, "habitacion_propuesta": destino, "estado": "PROPUESTA", "score": elegida["score"], "motivo": None, "descartadas": descartadas, "restricciones": huesped.restricciones})
        else:
            permitidas = sum(iniciales.get(p, 0) for p in pisos)
            if not tamano_inicial:
                motivo = "SIN_HABITACIONES_HABITABLES_LIBRES"
            elif permitidas:
                motivo = "SIN_CAPACIDAD"
            else:
                motivo = "RESTRICCIONES"
            propuestas.append({"huesped_id": huesped.id, "habitacion_actual": habitacion.id, "habitacion_propuesta": None, "estado": "NO_HAY_ALTERNATIVA", "score": None, "motivo": motivo, "descartadas": [], "restricciones": huesped.restricciones})

    estadisticas = {
        "huespedes_a_mover": huespedes_movidos,
        "habitaciones": len(hotel.habitaciones),
        "comparaciones_lineales": huespedes_movidos * len(hotel.habitaciones),
        "comparaciones_avl": bolsa.comparaciones - comparaciones_construccion,
        "comparaciones_construccion": comparaciones_construccion,
        "avl": {"tamano_inicial": tamano_inicial, "altura_inicial": altura_inicial, "tamano_final": bolsa.tamano, "eliminaciones": bolsa.eliminaciones, "rotaciones": bolsa.rotaciones},
    }
    return propuestas, estadisticas
