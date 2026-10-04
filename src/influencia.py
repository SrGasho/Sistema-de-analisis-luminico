from __future__ import annotations

from dataclasses import dataclass
import math

from .geometria import Rayo, Vector3
from .modelo import Hotel, SuperficiePared, Ventana
from .octree import EntradaEspacial, Octree


@dataclass
class AristaInfluencia:
    origen: str
    destino: str
    peso: float


class GrafoInfluencia:
    def __init__(self) -> None:
        self.adyacencias: dict[str, list[AristaInfluencia]] = {}

    def agregar_arista(self, origen: str, destino: str, peso: float) -> None:
        self.adyacencias.setdefault(origen, []).append(AristaInfluencia(origen, destino, peso))

    def construir(self, hotel: Hotel, octree: Octree, radio_maximo: float = 18.0) -> None:
        receptores = [
            ventana
            for zona in hotel.zonas.values()
            for ventana in zona.ventanas
        ]
        superficies = [
            superficie
            for zona in hotel.zonas.values()
            for superficie in zona.superficies
        ]
        for superficie in superficies:
            for ventana in receptores:
                distancia = superficie.posicion.distance_to(ventana.posicion)
                if distancia == 0 or distancia > radio_maximo:
                    continue
                direccion = (ventana.posicion - superficie.posicion).normalized()
                orientacion_origen = max(0.0, superficie.normal.normalized().dot(direccion))
                orientacion_destino = max(0.0, ventana.normal.normalized().dot(direccion * -1))
                if orientacion_origen == 0 or orientacion_destino == 0:
                    continue
                if not self._visible(superficie.posicion, ventana.posicion, octree, superficie.id, ventana.id):
                    continue
                peso = superficie.reflectancia * orientacion_origen * orientacion_destino / (1 + distancia * distancia)
                if peso > 0.0001:
                    self.agregar_arista(superficie.id, ventana.id, peso)

    def _visible(self, origen: Vector3, destino: Vector3, octree: Octree, origen_id: str, destino_id: str) -> bool:
        direccion = destino - origen
        distancia = direccion.length()
        rayo = Rayo(origen + direccion.normalized() * 0.01, direccion.normalized())
        for entrada in octree.consultar_rayo(rayo):
            if entrada.id not in {origen_id, destino_id} and entrada.objeto.__class__.__name__ == "Torre":
                if entrada.caja.center.distance_to(origen) < distancia:
                    return False
        return True

    def reflejada_para(self, receptor_id: str, luz_superficies: dict[str, float]) -> float:
        total = 0.0
        for origen, aristas in self.adyacencias.items():
            luz = luz_superficies.get(origen, 0.0)
            for arista in aristas:
                if arista.destino == receptor_id:
                    total += luz * arista.peso
        return total
