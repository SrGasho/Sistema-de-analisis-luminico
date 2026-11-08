from __future__ import annotations

import math

from .balance import balancear, horario_modo
from .clima import direccion_solar, luz_base, periodo
from .evaluacion import clasificar, datos_zona_completos, resumen_zonas
from .geometria import CajaEspacial, Rayo, Vector3, factor_angular_vidrio
from .habitabilidad import evaluar_hotel
from .influencia import GrafoInfluencia
from .modelo import EstadoIluminacion, Hotel, ModoOperacion, ResultadoIluminacion
from .octree import EntradaEspacial, Octree
from .reasignacion import proponer_reasignaciones
from .temporal import IndiceTemporal, reporte_temporal


class SimuladorUnificado:
    def __init__(self, hotel: Hotel, paso_horas: float = 0.5):
        self.hotel = hotel
        self.paso_horas = paso_horas
        self.hotel.generador.demanda_objetivo_maxima = 0.0
        self._lux_por_irradiancia = float(hotel.parametros.get("luz", {}).get("lux_por_irradiancia", 900.0))
        self.habitabilidad: dict = {}
        self.estadisticas_reasignacion: dict = {}
        self.temporal: dict = {}
        self.octree = self._crear_octree()
        self.grafo = GrafoInfluencia()
        self.grafo.construir(hotel, self.octree)

    def ejecutar(self, balancear_energia: bool = True, comparar_arboles: bool = False) -> tuple[list[ResultadoIluminacion], dict, list[dict]]:
        resultados: list[ResultadoIluminacion] = []
        indice = IndiceTemporal(comparar_arboles)
        hora = 0.0
        while hora < 24.0:
            aportes = self._aportes_naturales(hora)
            naturales = self._calcular_naturales(hora, aportes)
            reflejadas = self._calcular_reflejadas(hora, aportes)
            if balancear_energia:
                asignadas = balancear(self.hotel, hora, naturales, reflejadas)
            else:
                for zona in self.hotel.zonas.values():
                    zona.modo = horario_modo(self.hotel, zona, hora)
                asignadas = {zona.id: 0.0 for zona in self.hotel.zonas.values()}
            for zona in self.hotel.zonas.values():
                fuente = self.hotel.fuentes.get(zona.fuente_id) if zona.fuente_id else None
                artificial = self._luz_artificial(zona.id, asignadas.get(zona.id, 0.0))
                total = naturales.get(zona.id, 0.0) + reflejadas.get(zona.id, 0.0) + artificial
                perfil = self.hotel.perfiles_iluminacion.get(zona.actividad)
                estado = self._estado(zona, total, perfil, hora, balancear_energia)
                resultado = ResultadoIluminacion(zona.id, hora, periodo(hora), zona.modo, naturales.get(zona.id, 0.0), reflejadas.get(zona.id, 0.0), artificial, total, asignadas.get(zona.id, 0.0), estado)
                zona.resultados.append(resultado)
                resultados.append(resultado)
                indice.insertar(resultado)
            hora += self.paso_horas
        resumen = resumen_zonas(resultados)
        self.temporal = reporte_temporal(self.hotel, indice, self.paso_horas)
        self.habitabilidad = evaluar_hotel(self.hotel)
        veredictos = {e["zona_id"]: e for e in self.habitabilidad["zonas"]}
        propuestas: list[dict] = []
        self.estadisticas_reasignacion = {}
        if balancear_energia:
            propuestas, self.estadisticas_reasignacion = proponer_reasignaciones(self.hotel, resumen, veredictos)
        return resultados, resumen, propuestas

    def _estado(self, zona, total: float, perfil, hora: float, balanceado: bool) -> EstadoIluminacion:
        if perfil is None or not datos_zona_completos(zona) or zona.modo == ModoOperacion.CERRADA:
            return EstadoIluminacion.DATOS_INSUFICIENTES
        if not balanceado and periodo(hora) == "NOCHE":
            return EstadoIluminacion.DATOS_INSUFICIENTES
        modo = horario_modo(self.hotel, zona, hora) if zona.modo == ModoOperacion.EMERGENCIA else zona.modo
        return clasificar(total, perfil, modo)

    def _crear_octree(self) -> Octree:
        entradas = []
        for torre in self.hotel.torres:
            entradas.append(EntradaEspacial(torre.id, torre.caja, torre))
            for piso in torre.pisos:
                for zona in piso.zonas:
                    for ventana in zona.ventanas:
                        point = ventana.posicion
                        box = CajaEspacial(point.x - 0.05, point.x + 0.05, point.y - 0.05, point.y + 0.05, point.z - 0.05, point.z + 0.05)
                        entradas.append(EntradaEspacial(ventana.id, box, ventana))
                    for superficie in zona.superficies:
                        entradas.append(EntradaEspacial(superficie.id, superficie.caja, superficie))
            for fachada in torre.fachadas:
                entradas.append(EntradaEspacial(fachada.id, fachada.caja, fachada))
        for fuente in self.hotel.fuentes.values():
            point = fuente.posicion
            box = CajaEspacial(point.x - 0.05, point.x + 0.05, point.y - 0.05, point.y + 0.05, point.z - 0.05, point.z + 0.05)
            entradas.append(EntradaEspacial(fuente.id, box, fuente))
        cajas = [entrada.caja for entrada in entradas]
        octree = Octree(CajaEspacial(
            min(caja.min_x for caja in cajas) - 2, max(caja.max_x for caja in cajas) + 2,
            min(caja.min_y for caja in cajas) - 2, max(caja.max_y for caja in cajas) + 2,
            min(caja.min_z for caja in cajas) - 2, max(caja.max_z for caja in cajas) + 2,
        ))
        for entrada in entradas:
            octree.insertar(entrada)
        return octree

    def _cielo(self, hora: float) -> tuple[float, Vector3, float, float]:
        perfil = self.hotel.perfiles_climaticos[self.hotel.perfil_climatico_activo]
        base = luz_base(hora, perfil, self._lux_por_irradiancia)
        return base, direccion_solar(hora), max(0.10, 1.0 - perfil.nubosidad), 0.15 + 0.45 * perfil.nubosidad

    def _aportes_naturales(self, hora: float) -> dict[str, float]:
        base, direccion, f_directa, f_difusa = self._cielo(hora)
        aportes = {}
        for zona in self.hotel.zonas.values():
            for ventana in zona.ventanas:
                if base == 0:
                    aportes[ventana.id] = 0.0
                    continue
                coseno = max(0.0, ventana.normal.normalized().dot(direccion))
                if self._sombreada(ventana, zona.torre_id, direccion):
                    coseno = 0.0
                directa = coseno * factor_angular_vidrio(coseno, ventana.vidrio.indice_refraccion)
                cielo = 1.0 - self.grafo.obstruccion.get(ventana.id, 0.0)
                aportes[ventana.id] = base * ventana.vidrio.transmitancia_visible * (directa * f_directa + f_difusa * cielo)
        return aportes

    def _calcular_naturales(self, hora: float, aportes: dict[str, float] | None = None) -> dict[str, float]:
        aportes = self._aportes_naturales(hora) if aportes is None else aportes
        return {
            zona.id: sum(aportes[v.id] for v in zona.ventanas) / len(zona.ventanas) if zona.ventanas else 0.0
            for zona in self.hotel.zonas.values()
        }

    def _sombreada(self, ventana, torre_id: str, direccion: Vector3) -> bool:
        rayo = Rayo(ventana.posicion + direccion * 0.01, direccion)
        return any(entrada.objeto.__class__.__name__ == "Torre" and entrada.id != torre_id for entrada in self.octree.consultar_rayo(rayo))

    def luz_fachadas(self, hora: float) -> dict[str, float]:
        base, direccion, f_directa, f_difusa = self._cielo(hora)
        return {
            fachada.id: base * (max(0.0, fachada.normal.dot(direccion)) * f_directa + f_difusa)
            for fachada in self.grafo.fachadas.values()
        }

    def _calcular_reflejadas(self, hora: float, aportes: dict[str, float] | None = None) -> dict[str, float]:
        aportes = self._aportes_naturales(hora) if aportes is None else aportes
        luz_fachadas = self.luz_fachadas(hora)
        reflejadas = {}
        for zona in self.hotel.zonas.values():
            if not zona.ventanas:
                reflejadas[zona.id] = 0.0
                continue
            exteriores = {v.id: self.grafo.reflejada_para(v.id, luz_fachadas) * v.vidrio.transmitancia_visible for v in zona.ventanas}
            flujo = sum((aportes[v.id] + exteriores[v.id]) * v.area for v in zona.ventanas)
            reflejadas[zona.id] = sum(exteriores.values()) / len(zona.ventanas) + reflexion_interior(zona, flujo)
        return reflejadas

    def _luz_artificial(self, zona_id: str, potencia: float) -> float:
        zona = self.hotel.zonas[zona_id]
        if not zona.fuente_id or potencia <= 0 or zona.area <= 0:
            return 0.0
        fuente = self.hotel.fuentes[zona.fuente_id]
        return fuente.eficacia * potencia * fuente.cu * fuente.mf / zona.area


ALTO_PISO = 3.0


def area_interior(zona) -> float:
    lado = math.sqrt(zona.area)
    return 2 * zona.area + 4 * lado * ALTO_PISO


def reflexion_interior(zona, flujo_entrante: float) -> float:
    """Componente reflejada interior por el método de flujo dividido: Φ·ρ / (A·(1 − ρ))."""
    if flujo_entrante <= 0 or not zona.superficies:
        return 0.0
    rho = zona.superficies[0].reflectancia
    return flujo_entrante * rho / (area_interior(zona) * (1 - rho))
