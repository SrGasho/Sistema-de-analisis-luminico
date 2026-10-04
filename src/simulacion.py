from __future__ import annotations

from .balance import balancear, horario_modo
from .clima import direccion_solar, luz_base, periodo
from .evaluacion import clasificar, resumen_zonas
from .geometria import CajaEspacial, Rayo, Vector3
from .influencia import GrafoInfluencia
from .modelo import Hotel, ModoOperacion, ResultadoIluminacion
from .octree import EntradaEspacial, Octree
from .reasignacion import proponer_reasignaciones


class SimuladorUnificado:
    def __init__(self, hotel: Hotel, paso_horas: float = 0.5):
        self.hotel = hotel
        self.paso_horas = paso_horas
        self.octree = self._crear_octree()
        self.grafo = GrafoInfluencia()
        self.grafo.construir(hotel, self.octree)

    def ejecutar(self, balancear_energia: bool = True) -> tuple[list[ResultadoIluminacion], dict, list[dict]]:
        resultados: list[ResultadoIluminacion] = []
        hora = 0.0
        while hora < 24.0:
            naturales = self._calcular_naturales(hora)
            reflejadas = self._calcular_reflejadas(hora)
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
                perfil = self.hotel.perfiles_iluminacion[zona.actividad]
                estado = clasificar(total, perfil, zona.modo)
                resultado = ResultadoIluminacion(zona.id, hora, periodo(hora), zona.modo, naturales.get(zona.id, 0.0), reflejadas.get(zona.id, 0.0), artificial, total, asignadas.get(zona.id, 0.0), estado)
                zona.resultados.append(resultado)
                resultados.append(resultado)
            hora += self.paso_horas
        resumen = resumen_zonas(resultados)
        propuestas = proponer_reasignaciones(self.hotel, resumen) if balancear_energia else []
        return resultados, resumen, propuestas

    def _crear_octree(self) -> Octree:
        cajas = [torre.caja for torre in self.hotel.torres]
        min_x = min(caja.min_x for caja in cajas) - 2
        max_x = max(caja.max_x for caja in cajas) + 2
        min_y = min(caja.min_y for caja in cajas) - 2
        max_y = max(caja.max_y for caja in cajas) + 2
        min_z = min(caja.min_z for caja in cajas) - 2
        max_z = max(caja.max_z for caja in cajas) + 2
        octree = Octree(CajaEspacial(min_x, max_x, min_y, max_y, min_z, max_z))
        for torre in self.hotel.torres:
            octree.insertar(EntradaEspacial(torre.id, torre.caja, torre))
            for piso in torre.pisos:
                for zona in piso.zonas:
                    for ventana in zona.ventanas:
                        point = ventana.posicion
                        box = CajaEspacial(point.x - 0.05, point.x + 0.05, point.y - 0.05, point.y + 0.05, point.z - 0.05, point.z + 0.05)
                        octree.insertar(EntradaEspacial(ventana.id, box, ventana))
                    for superficie in zona.superficies:
                        octree.insertar(EntradaEspacial(superficie.id, superficie.caja, superficie))
        for fuente in self.hotel.fuentes.values():
            point = fuente.posicion
            box = CajaEspacial(point.x - 0.05, point.x + 0.05, point.y - 0.05, point.y + 0.05, point.z - 0.05, point.z + 0.05)
            octree.insertar(EntradaEspacial(fuente.id, box, fuente))
        return octree

    def _calcular_naturales(self, hora: float) -> dict[str, float]:
        perfil = self.hotel.perfiles_climaticos[self.hotel.perfil_climatico_activo]
        base = luz_base(hora, perfil)
        direccion = direccion_solar(hora)
        naturales = {}
        for zona in self.hotel.zonas.values():
            if not zona.ventanas or base == 0:
                naturales[zona.id] = 0.0
                continue
            aportes = []
            for ventana in zona.ventanas:
                directa = max(0.0, ventana.normal.normalized().dot(direccion))
                sombreada = self._sombreada(ventana, zona.torre_id, direccion)
                aporte = base * (0.15 if sombreada else directa) * ventana.vidrio.transmitancia_visible
                aportes.append(aporte)
            naturales[zona.id] = sum(aportes) / len(aportes)
        return naturales

    def _sombreada(self, ventana, torre_id: str, direccion: Vector3) -> bool:
        rayo = Rayo(ventana.posicion + direccion * 0.01, direccion)
        return any(entrada.objeto.__class__.__name__ == "Torre" and entrada.id != torre_id for entrada in self.octree.consultar_rayo(rayo))

    def _calcular_reflejadas(self, hora: float) -> dict[str, float]:
        perfil = self.hotel.perfiles_climaticos[self.hotel.perfil_climatico_activo]
        base = luz_base(hora, perfil)
        superficies = {superficie.id: base * superficie.reflectancia for zona in self.hotel.zonas.values() for superficie in zona.superficies}
        ventanas_por_zona = {zona.id: zona.ventanas for zona in self.hotel.zonas.values()}
        reflejadas = {}
        for zona_id, ventanas in ventanas_por_zona.items():
            aportes = [self.grafo.reflejada_para(ventana.id, superficies) for ventana in ventanas]
            reflejadas[zona_id] = sum(aportes) / len(aportes) if aportes else 0.0
        return reflejadas

    def _luz_artificial(self, zona_id: str, potencia: float) -> float:
        zona = self.hotel.zonas[zona_id]
        if not zona.fuente_id or potencia <= 0 or zona.area <= 0:
            return 0.0
        fuente = self.hotel.fuentes[zona.fuente_id]
        return fuente.eficacia * potencia * fuente.cu * fuente.mf / zona.area
