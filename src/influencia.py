from __future__ import annotations

from dataclasses import dataclass
import math

from .geometria import CajaEspacial, Rayo, Vector3
from .modelo import Fachada, Hotel, Ventana
from .octree import Octree


@dataclass
class AristaInfluencia:
    origen: str
    destino: str
    peso: float


def punto_en_fachada(ventana: Ventana, caja: CajaEspacial) -> Vector3:
    """Lleva la ventana hasta la cara de su torre hacia la que mira."""
    p, n = ventana.posicion, ventana.normal
    x = caja.max_x if n.x > 0 else caja.min_x if n.x < 0 else p.x
    y = caja.max_y if n.y > 0 else caja.min_y if n.y < 0 else p.y
    return Vector3(x, y, p.z)


def punto_mas_cercano(punto: Vector3, caja: CajaEspacial) -> Vector3:
    return Vector3(
        min(max(punto.x, caja.min_x), caja.max_x),
        min(max(punto.y, caja.min_y), caja.max_y),
        min(max(punto.z, caja.min_z), caja.max_z),
    )


class GrafoInfluencia:
    """Reflexión exterior de primer orden: fachada de una torre -> ventanas de la otra torre."""

    def __init__(self) -> None:
        self.adyacencias: dict[str, list[AristaInfluencia]] = {}
        self.entrantes: dict[str, list[AristaInfluencia]] = {}
        self.fachadas: dict[str, Fachada] = {}
        self.obstruccion: dict[str, float] = {}
        self.estadisticas: dict[str, int] = {}

    def agregar_arista(self, origen: str, destino: str, peso: float) -> None:
        arista = AristaInfluencia(origen, destino, peso)
        self.adyacencias.setdefault(origen, []).append(arista)
        self.entrantes.setdefault(destino, []).append(arista)

    def construir(self, hotel: Hotel, octree: Octree, radio_maximo: float = 18.0) -> None:
        self.fachadas = {f.id: f for torre in hotel.torres for f in torre.fachadas}
        cajas = {torre.id: torre.caja for torre in hotel.torres}
        ventanas = [(zona.torre_id, v) for zona in hotel.zonas.values() for v in zona.ventanas]
        pares_evaluados = 0
        octree.nodos_visitados = 0
        for torre_id, ventana in ventanas:
            salida = punto_en_fachada(ventana, cajas[torre_id])
            candidatas = [
                e.objeto for e in octree.consultar_radio(salida, radio_maximo)
                if isinstance(e.objeto, Fachada) and e.objeto.torre_id != torre_id
            ]
            pares_evaluados += len(candidatas)
            for fachada in candidatas:
                destino = punto_mas_cercano(salida, fachada.caja)
                distancia = salida.distance_to(destino)
                if distancia == 0 or distancia > radio_maximo:
                    continue
                direccion = (destino - salida).normalized()
                coseno_ventana = max(0.0, ventana.normal.normalized().dot(direccion))
                coseno_fachada = max(0.0, fachada.normal.normalized().dot(direccion * -1))
                if coseno_ventana == 0 or coseno_fachada == 0:
                    continue
                if not self._visible(salida, destino, octree, {torre_id, fachada.torre_id}):
                    continue
                vista = fachada.area / (math.pi * distancia * distancia + fachada.area)
                tapado = coseno_ventana * vista
                peso = fachada.reflectancia * coseno_fachada * tapado
                if peso > 0.0001:
                    self.agregar_arista(fachada.id, ventana.id, peso)
                    self.obstruccion[ventana.id] = min(1.0, self.obstruccion.get(ventana.id, 0.0) + tapado)
        self.estadisticas = {
            "fachadas": len(self.fachadas),
            "ventanas": len(ventanas),
            "pares_ingenuos": len(self.fachadas) * len(ventanas),
            "pares_evaluados": pares_evaluados,
            "nodos_octree_visitados": octree.nodos_visitados,
            "aristas": sum(len(aristas) for aristas in self.adyacencias.values()),
        }

    def _visible(self, origen: Vector3, destino: Vector3, octree: Octree, torres_excluidas: set[str]) -> bool:
        direccion = destino - origen
        distancia = direccion.length()
        rayo = Rayo(origen + direccion.normalized() * 0.01, direccion.normalized())
        for entrada in octree.consultar_rayo(rayo):
            if entrada.id not in torres_excluidas and entrada.objeto.__class__.__name__ == "Torre":
                if entrada.caja.center.distance_to(origen) < distancia:
                    return False
        return True

    def reflejada_para(self, receptor_id: str, luz_fachadas: dict[str, float]) -> float:
        return sum(luz_fachadas.get(a.origen, 0.0) * a.peso for a in self.entrantes.get(receptor_id, []))
