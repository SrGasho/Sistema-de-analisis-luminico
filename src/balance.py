from __future__ import annotations

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
        potencia_minima = _demanda(minimo, natural.get(zona.id, 0.0) + reflejada.get(zona.id, 0.0), conversion)
        potencia_objetivo = _demanda(objetivo, natural.get(zona.id, 0.0) + reflejada.get(zona.id, 0.0), conversion)
        peso_piso = 1.0 + 0.10 * (zona.piso - 1)
        ocupacion = 1.4 if zona.id in hotel.habitaciones and hotel.habitaciones[zona.id].ocupacion > 0 else 1.0
        prioridad = perfil.prioridad * peso_piso * ocupacion
        demandas.append(Demanda(zona, minimo, objetivo, prioridad, potencia_minima, potencia_objetivo))

    asignadas: dict[str, float] = {demanda.zona.id: 0.0 for demanda in demandas}
    minimo_orden = sorted(demandas, key=lambda item: (item.zona.id not in hotel.habitaciones or hotel.habitaciones[item.zona.id].ocupacion == 0, -item.prioridad))
    for demanda in minimo_orden:
        if demanda.zona.modo == ModoOperacion.CERRADA:
            continue
        potencia = min(demanda.potencia_minima, _potencia_maxima(hotel, demanda.zona))
        asignadas[demanda.zona.id] = _asignar(hotel, potencia, asignadas, demanda.zona.id)

    for demanda in sorted(demandas, key=lambda item: -item.prioridad):
        restante = max(0.0, demanda.potencia_objetivo - asignadas[demanda.zona.id])
        if restante == 0 or demanda.zona.modo == ModoOperacion.CERRADA:
            continue
        potencia = min(restante, _potencia_maxima(hotel, demanda.zona) - asignadas[demanda.zona.id])
        asignadas[demanda.zona.id] += _asignar(hotel, potencia, asignadas, demanda.zona.id)
    return asignadas


def _demanda(nivel: float, base: float, conversion: float) -> float:
    return 0.0 if conversion <= 0 else max(0.0, (nivel - base) / conversion)


def _potencia_maxima(hotel: Hotel, zona: ZonaHotel) -> float:
    if not zona.fuente_id:
        return 0.0
    return hotel.fuentes[zona.fuente_id].potencia_maxima


def _asignar(hotel: Hotel, potencia: float, asignadas: dict[str, float], zona_id: str) -> float:
    disponible = max(0.0, hotel.generador.potencia_disponible - sum(asignadas.values()))
    asignacion = min(max(0.0, potencia), disponible)
    return asignacion
