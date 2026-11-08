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
    potencia_emergencia: float


def _en_intervalo(hora: float, inicio: float, fin: float) -> bool:
    if inicio <= fin:
        return inicio <= hora < fin
    return hora >= inicio or hora < fin


def horario_modo(hotel: Hotel, zona: ZonaHotel, hora: float) -> ModoOperacion:
    if zona.actividad == Actividad.PARQUEADERO:
        return ModoOperacion.ACTIVA
    horario = hotel.horarios.get(zona.actividad.value, {})
    if _en_intervalo(hora, float(horario.get("inicio_activa", 0.0)), float(horario.get("fin_activa", 24.0))):
        return ModoOperacion.ACTIVA
    if "cierre_inicio" in horario and "cierre_fin" in horario:
        if _en_intervalo(hora, float(horario["cierre_inicio"]), float(horario["cierre_fin"])):
            return ModoOperacion.CERRADA
    return ModoOperacion.REDUCIDA


def _categoria(hotel: Hotel, zona: ZonaHotel) -> int:
    if zona.actividad == Actividad.PARQUEADERO:
        return 0
    if zona.id in hotel.habitaciones and hotel.habitaciones[zona.id].ocupacion > 0:
        return 1
    return 2


def _en_orden(cola: list) -> list[Demanda]:
    cola = list(cola)
    heapq.heapify(cola)
    return [heapq.heappop(cola)[-1] for _ in range(len(cola))]


def balancear(hotel: Hotel, hora: float, natural: dict[str, float], reflejada: dict[str, float]) -> dict[str, float]:
    hotel.generador.iniciar_instante()
    nivel_emergencia = float(hotel.parametros.get("emergencia", {}).get("nivel_lux", 10.0))
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
        potencia_emergencia = _demanda(min(nivel_emergencia, minimo), base, conversion)
        peso_piso = 1.0 + 0.10 * (zona.piso - 1)
        ocupacion = 1.4 if zona.id in hotel.habitaciones and hotel.habitaciones[zona.id].ocupacion > 0 else 1.0
        prioridad = perfil.prioridad * peso_piso * ocupacion
        demandas.append(Demanda(zona, minimo, objetivo, prioridad, potencia_minima, potencia_objetivo, potencia_emergencia))

    demanda_objetivo_total = sum(d.potencia_objetivo for d in demandas if d.zona.modo != ModoOperacion.CERRADA)
    hotel.generador.demanda_objetivo_maxima = max(hotel.generador.demanda_objetivo_maxima, demanda_objetivo_total)

    asignadas: dict[str, float] = {demanda.zona.id: 0.0 for demanda in demandas}
    generador = Reparto(hotel.generador.potencia_disponible)
    abiertas = [(_categoria(hotel, d.zona), -d.prioridad, i, d) for i, d in enumerate(demandas) if d.zona.modo != ModoOperacion.CERRADA]
    orden = _en_orden(abiertas)

    for demanda in orden:
        potencia = min(demanda.potencia_emergencia, _potencia_maxima(hotel, demanda.zona))
        asignadas[demanda.zona.id] = generador.entregar(potencia)

    for demanda in orden:
        alcanzable = min(demanda.potencia_minima, _potencia_maxima(hotel, demanda.zona))
        restante = max(0.0, alcanzable - asignadas[demanda.zona.id])
        asignadas[demanda.zona.id] += generador.entregar(restante)
        if asignadas[demanda.zona.id] < alcanzable - 1e-6:
            demanda.zona.modo = ModoOperacion.EMERGENCIA

    cola_objetivos = [(-d.prioridad, indice, d) for indice, d in enumerate(demandas)]
    heapq.heapify(cola_objetivos)
    while cola_objetivos:
        *_, demanda = heapq.heappop(cola_objetivos)
        restante = max(0.0, demanda.potencia_objetivo - asignadas[demanda.zona.id])
        if restante == 0 or demanda.zona.modo in (ModoOperacion.CERRADA, ModoOperacion.EMERGENCIA):
            continue
        potencia = min(restante, _potencia_maxima(hotel, demanda.zona) - asignadas[demanda.zona.id])
        asignadas[demanda.zona.id] += generador.entregar(potencia)
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


class Reparto:
    """Lleva la cuenta de lo que ya entregó el generador en el instante, para no volver a sumarlo."""

    def __init__(self, capacidad: float) -> None:
        self.capacidad = capacidad
        self.usado = 0.0

    def entregar(self, potencia: float) -> float:
        entregado = min(max(0.0, potencia), max(0.0, self.capacidad - self.usado))
        self.usado += entregado
        return entregado
