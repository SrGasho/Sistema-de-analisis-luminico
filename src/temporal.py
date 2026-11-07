from __future__ import annotations

from collections import Counter

from .arboles import IndiceAVL, IndiceRojoNegro
from .balance import horario_modo
from .modelo import EstadoIluminacion, Hotel, ModoOperacion, ResultadoIluminacion

FRANJAS = [
    ("Día completo", 0.0, 24.0),
    ("Madrugada 00:00–06:00", 0.0, 6.0),
    ("Mañana 06:00–12:00", 6.0, 12.0),
    ("Tarde 12:00–18:00", 12.0, 18.0),
    ("Noche 18:00–22:00", 18.0, 22.0),
    ("Cierre 22:00–24:00", 22.0, 24.0),
]


class IndiceTemporal:
    def __init__(self, comparar_con_avl: bool = False) -> None:
        self.arbol = IndiceRojoNegro()
        self.avl = IndiceAVL() if comparar_con_avl else None

    def insertar(self, resultado: ResultadoIluminacion) -> None:
        clave = (resultado.hora, resultado.zona_id)
        self.arbol.insertar(clave, resultado)
        if self.avl is not None:
            self.avl.insertar(clave, resultado)

    def franja(self, inicio: float, fin: float) -> list[ResultadoIluminacion]:
        return self.arbol.rango((inicio, ""), (fin, ""))

    def estadisticas(self) -> dict:
        datos = {"rojo_negro": {"tamano": self.arbol.tamano, "altura": self.arbol.altura(), "rotaciones": self.arbol.rotaciones}}
        if self.avl is not None:
            datos["avl"] = {"tamano": self.avl.tamano, "altura": self.avl.altura(), "rotaciones": self.avl.rotaciones}
        return datos


def _minimo(hotel: Hotel, resultado: ResultadoIluminacion) -> float:
    zona = hotel.zonas[resultado.zona_id]
    modo = horario_modo(hotel, zona, resultado.hora) if resultado.modo == ModoOperacion.EMERGENCIA else resultado.modo
    return hotel.perfiles_iluminacion[zona.actividad].para_modo(modo)[0]


def _conversion(hotel: Hotel, zona_id: str) -> float:
    zona = hotel.zonas[zona_id]
    if not zona.fuente_id or zona.area <= 0:
        return 0.0
    fuente = hotel.fuentes[zona.fuente_id]
    return fuente.eficacia * fuente.cu * fuente.mf / zona.area


def reporte_franja(hotel: Hotel, indice: IndiceTemporal, etiqueta: str, inicio: float, fin: float, paso_horas: float) -> dict:
    antes = indice.arbol.comparaciones
    resultados = indice.franja(inicio, fin)
    comparaciones = indice.arbol.comparaciones - antes

    energia = 0.0
    por_actividad: Counter = Counter()
    por_torre: Counter = Counter()
    potencia_por_hora: Counter = Counter()
    horas_deficit: Counter = Counter()
    horas_con_deficit: set[float] = set()
    deficit_lux_h = 0.0
    no_asignada_wh = 0.0
    estados: dict[str, Counter] = {}
    for resultado in resultados:
        zona = hotel.zonas[resultado.zona_id]
        wh = resultado.potencia_asignada * paso_horas
        energia += wh
        por_actividad[zona.actividad.value] += wh
        por_torre[zona.torre_id] += wh
        potencia_por_hora[resultado.hora] += resultado.potencia_asignada
        if resultado.estado != EstadoIluminacion.DATOS_INSUFICIENTES:
            estados.setdefault(resultado.zona_id, Counter())[resultado.estado.value] += 1
        if resultado.estado.value.startswith("DEFICIT"):
            horas_deficit[resultado.zona_id] += paso_horas
            horas_con_deficit.add(resultado.hora)
            faltante = max(0.0, _minimo(hotel, resultado) - resultado.luz_total)
            deficit_lux_h += faltante * paso_horas
            conversion = _conversion(hotel, resultado.zona_id)
            if conversion > 0:
                no_asignada_wh += faltante / conversion * paso_horas

    hora_pico, potencia_pico = max(potencia_por_hora.items(), key=lambda item: (item[1], -item[0]), default=(None, 0.0))
    criticas = sorted(horas_deficit.items(), key=lambda item: (-item[1], item[0]))[:10]
    return {
        "etiqueta": etiqueta,
        "inicio": inicio,
        "fin": fin,
        "resultados": len(resultados),
        "energia_wh": round(energia, 1),
        "energia_kwh": round(energia / 1000.0, 3),
        "energia_por_actividad_wh": {k: round(v, 1) for k, v in sorted(por_actividad.items())},
        "energia_por_torre_wh": {k: round(v, 1) for k, v in sorted(por_torre.items())},
        "hora_pico": hora_pico,
        "potencia_pico_w": round(potencia_pico, 1),
        "deficit_residual_lux_h": round(deficit_lux_h, 1),
        "energia_no_asignada_wh": round(no_asignada_wh, 1),
        "zonas_con_deficit": len(horas_deficit),
        "zonas_criticas": [{"zona_id": zona_id, "horas_deficit": horas, "actividad": hotel.zonas[zona_id].actividad.value, "torre": hotel.zonas[zona_id].torre_id} for zona_id, horas in criticas],
        "horas_deficit_por_zona": {k: v for k, v in sorted(horas_deficit.items())},
        "horas_con_deficit": sorted(horas_con_deficit),
        "estados_por_zona": {zona_id: conteo.most_common(1)[0][0] for zona_id, conteo in estados.items()},
        "comparaciones_arbol": comparaciones,
        "comparaciones_lineales": indice.arbol.tamano,
    }


def reporte_temporal(hotel: Hotel, indice: IndiceTemporal, paso_horas: float) -> dict:
    return {
        "franjas": [reporte_franja(hotel, indice, etiqueta, inicio, fin, paso_horas) for etiqueta, inicio, fin in FRANJAS],
        "indices": indice.estadisticas(),
    }
