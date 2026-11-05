from __future__ import annotations

import heapq
from dataclasses import dataclass

from .modelo import Actividad, Hotel, ModoOperacion, ZonaHotel


@dataclass
class Demanda:
    zona: ZonaHotel
    minimo: float
    objetivo: float
    prioridad: float
    potencia_minima: float
    potencia_objetivo: float


def horario_modo(hotel: Hotel, zona: ZonaHotel, hora: float) -> ModoOperacion:
    horario = hotel.horarios.get(zona.actividad.value, {})
    inicio = float(horario.get("inicio_activa", 0.0))
    fin = float(horario.get("fin_activa", 24.0))
    if zona.actividad == Actividad.PARQUEADERO:
        return ModoOperacion.ACTIVA
    return ModoOperacion.ACTIVA if inicio <= hora < fin else ModoOperacion.REDUCIDA


def balancear(hotel: Hotel, hora: float, natural: dict[str, float], reflejada: dict[str, float]) -> dict[str, float]:
    hotel.generador.iniciar_instante()
    demandas: list[Demanda] = []
    for zona in hotel.zonas.values():
        zona.modo = horario_modo(hotel, zona, hora)
        perfil = hotel.perfiles_iluminacion[zona.actividad]
        minimo, objetivo, _ = perfil.para_modo(zona.modo)
        fuente = hotel.fuentes[zona.fuente_id] if zona.fuente_id else None
        conversion = 0.0 if not fuente or zona.area <= 0 else fuente.eficacia * fuente.cu * fuente.mf / zona.area
        base = natural.get(zona.id, 0.0) + reflejada.get(zona.id, 0.0)
        potencia_minima = _demanda(minimo, base, conversion)
        potencia_objetivo = _demanda(objetivo, base, conversion)
        peso_piso = 1.0 + 0.10 * (zona.piso - 1)
        ocupacion = 1.4 if zona.id in hotel.habitaciones and hotel.habitaciones[zona.id].ocupacion > 0 else 1.0
        prioridad = perfil.prioridad * peso_piso * ocupacion
        demandas.append(Demanda(zona, minimo, objetivo, prioridad, potencia_minima, potencia_objetivo))

    demanda_objetivo_total = sum(d.potencia_objetivo for d in demandas if d.zona.modo != ModoOperacion.CERRADA)
    hotel.generador.demanda_objetivo_maxima = max(hotel.generador.demanda_objetivo_maxima, demanda_objetivo_total)

    asignadas: dict[str, float] = {demanda.zona.id: 0.0 for demanda in demandas}

    cola_minimos = []
    for indice, demanda in enumerate(demandas):
        ocupada = demanda.zona.id in hotel.habitaciones and hotel.habitaciones[demanda.zona.id].ocupacion > 0
        cola_minimos.append((0 if ocupada else 1, -demanda.prioridad, indice, demanda))
    heapq.heapify(cola_minimos)
    while cola_minimos:
        *_, demanda = heapq.heappop(cola_minimos)
        if demanda.zona.modo == ModoOperacion.CERRADA:
            continue
        potencia = min(demanda.potencia_minima, _potencia_maxima(hotel, demanda.zona))
        asignadas[demanda.zona.id] = _asignar(hotel, potencia, asignadas)

    cola_objetivos = [(-d.prioridad, indice, d) for indice, d in enumerate(demandas)]
    heapq.heapify(cola_objetivos)
    while cola_objetivos:
        *_, demanda = heapq.heappop(cola_objetivos)
        restante = max(0.0, demanda.potencia_objetivo - asignadas[demanda.zona.id])
        if restante == 0 or demanda.zona.modo == ModoOperacion.CERRADA:
            continue
        potencia = min(restante, _potencia_maxima(hotel, demanda.zona) - asignadas[demanda.zona.id])
        asignadas[demanda.zona.id] += _asignar(hotel, potencia, asignadas)
    return asignadas


def agregar_energia_postorden(hotel: Hotel) -> dict[str, dict]:
    resultado: dict[str, dict] = {}
    for torre in hotel.torres:
        pisos: dict[int, float] = {}
        for piso in torre.pisos:
            pisos[piso.numero] = round(sum(
                sum(r.potencia_asignada for r in zona.resultados) * 0.5
                for zona in piso.zonas
            ), 1)
        resultado[torre.id] = {"energia_wh": round(sum(pisos.values()), 1), "pisos": pisos}
    return resultado


def _demanda(nivel: float, base: float, conversion: float) -> float:
    return 0.0 if conversion <= 0 else max(0.0, (nivel - base) / conversion)


def _potencia_maxima(hotel: Hotel, zona: ZonaHotel) -> float:
    if not zona.fuente_id:
        return 0.0
    return hotel.fuentes[zona.fuente_id].potencia_maxima


def _asignar(hotel: Hotel, potencia: float, asignadas: dict[str, float]) -> float:
    disponible = max(0.0, hotel.generador.potencia_disponible - sum(asignadas.values()))
    return min(max(0.0, potencia), disponible)
