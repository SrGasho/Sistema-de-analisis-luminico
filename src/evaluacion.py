from __future__ import annotations

from collections import defaultdict

from .modelo import EstadoIluminacion, ModoOperacion, PerfilIluminacion, ResultadoIluminacion


def clasificar(nivel: float, perfil: PerfilIluminacion, modo: ModoOperacion) -> EstadoIluminacion:
    if modo == ModoOperacion.CERRADA:
        return EstadoIluminacion.DATOS_INSUFICIENTES
    minimo, _, maximo = perfil.para_modo(modo)
    if nivel < 0.5 * minimo:
        return EstadoIluminacion.DEFICIT_SEVERO
    if nivel < minimo:
        return EstadoIluminacion.DEFICIT_LEVE
    if nivel <= maximo:
        return EstadoIluminacion.CONFORTABLE
    if nivel <= 1.25 * maximo:
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
