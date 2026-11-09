from __future__ import annotations

from collections import Counter, defaultdict

from .modelo import Actividad, EstadoIluminacion, ModoOperacion, PerfilIluminacion, ResultadoIluminacion, ZonaHotel

ZONAS_SIN_VENTANAS = {Actividad.PARQUEADERO}
TOLERANCIA_LUX = 1e-9


def datos_zona_completos(zona: ZonaHotel) -> bool:
    if zona.area <= 0:
        return False
    if zona.actividad not in ZONAS_SIN_VENTANAS and not zona.ventanas:
        return False
    return all(ventana.normal.length() > 0 for ventana in zona.ventanas)


def estado_predominante(resultados: list[ResultadoIluminacion]) -> EstadoIluminacion:
    conteo = Counter(r.estado for r in resultados if r.estado != EstadoIluminacion.DATOS_INSUFICIENTES)
    if not conteo:
        return EstadoIluminacion.DATOS_INSUFICIENTES
    return conteo.most_common(1)[0][0]


def clasificar(nivel: float, perfil: PerfilIluminacion, modo: ModoOperacion) -> EstadoIluminacion:
    """La tolerancia evita que el redondeo de vatios a lux deje justo bajo el mínimo a una zona que lo alcanzó."""
    minimo, _, maximo = perfil.para_modo(modo)
    if nivel < 0.5 * minimo - TOLERANCIA_LUX:
        return EstadoIluminacion.DEFICIT_SEVERO
    if nivel < minimo - TOLERANCIA_LUX:
        return EstadoIluminacion.DEFICIT_LEVE
    if nivel <= maximo + TOLERANCIA_LUX:
        return EstadoIluminacion.CONFORTABLE
    if nivel <= 1.25 * maximo + TOLERANCIA_LUX:
        return EstadoIluminacion.EXCESO_LEVE
    return EstadoIluminacion.EXCESO_SEVERO


def resumen_zonas(resultados: list[ResultadoIluminacion]) -> dict[str, dict]:
    agrupados: dict[str, list[ResultadoIluminacion]] = defaultdict(list)
    for resultado in resultados:
        agrupados[resultado.zona_id].append(resultado)
    resumen = {}
    for zona_id, items in agrupados.items():
        niveles = [item.luz_total for item in items]
        resumen[zona_id] = {
            "promedio_lux": sum(niveles) / len(niveles),
            "maximo_lux": max(niveles),
            "pasos_deficit": sum(item.estado.value.startswith("DEFICIT") for item in items),
            "pasos_confortables": sum(item.estado == EstadoIluminacion.CONFORTABLE for item in items),
            "pasos_exceso": sum(item.estado.value.startswith("EXCESO") for item in items),
            "energia_wh": sum(item.potencia_asignada * 0.5 for item in items),
        }
    return resumen
