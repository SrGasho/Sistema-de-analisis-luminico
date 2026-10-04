from __future__ import annotations

from dataclasses import dataclass, field
import math

from .geometria import CajaEspacial, Rayo, Vector3


@dataclass
class EntradaEspacial:
    id: str
    caja: CajaEspacial
    objeto: object


@dataclass
class NodoOctree:
    caja: CajaEspacial
    profundidad: int
    objetos: list[EntradaEspacial] = field(default_factory=list)
    hijos: list[NodoOctree] = field(default_factory=list)


class Octree:
    def __init__(self, caja: CajaEspacial, capacidad: int = 16, profundidad_maxima: int = 6):
        self.raiz = NodoOctree(caja, 0)
        self.capacidad = capacidad
        self.profundidad_maxima = profundidad_maxima

    def insertar(self, entrada: EntradaEspacial) -> None:
        self._insertar(self.raiz, entrada)

    def _insertar(self, nodo: NodoOctree, entrada: EntradaEspacial) -> None:
        if nodo.hijos:
            indice = self._hijo_contenedor(nodo, entrada.caja)
            if indice is not None:
                self._insertar(nodo.hijos[indice], entrada)
                return
        nodo.objetos.append(entrada)
        if len(nodo.objetos) > self.capacidad and nodo.profundidad < self.profundidad_maxima:
            if not nodo.hijos:
                self._dividir(nodo)
            restantes = []
            for objeto in nodo.objetos:
                indice = self._hijo_contenedor(nodo, objeto.caja)
                if indice is None:
                    restantes.append(objeto)
                else:
                    self._insertar(nodo.hijos[indice], objeto)
            nodo.objetos = restantes

    def _dividir(self, nodo: NodoOctree) -> None:
        box = nodo.caja
        cx, cy, cz = box.center.x, box.center.y, box.center.z
        for x in ((box.min_x, cx), (cx, box.max_x)):
            for y in ((box.min_y, cy), (cy, box.max_y)):
                for z in ((box.min_z, cz), (cz, box.max_z)):
                    nodo.hijos.append(NodoOctree(CajaEspacial(*x, *y, *z), nodo.profundidad + 1))

    def _hijo_contenedor(self, nodo: NodoOctree, box: CajaEspacial) -> int | None:
        for index, hijo in enumerate(nodo.hijos):
            if (
                hijo.caja.min_x <= box.min_x and box.max_x <= hijo.caja.max_x
                and hijo.caja.min_y <= box.min_y and box.max_y <= hijo.caja.max_y
                and hijo.caja.min_z <= box.min_z and box.max_z <= hijo.caja.max_z
            ):
                return index
        return None

    def consultar_rayo(self, rayo: Rayo) -> list[EntradaEspacial]:
        encontrados: dict[str, EntradaEspacial] = {}
        self._consultar_rayo(self.raiz, rayo, encontrados)
        return list(encontrados.values())

    def _consultar_rayo(self, nodo: NodoOctree, rayo: Rayo, encontrados: dict[str, EntradaEspacial]) -> None:
        if not rayo.intersects(nodo.caja):
            return
        for objeto in nodo.objetos:
            if rayo.intersects(objeto.caja):
                encontrados[objeto.id] = objeto
        for hijo in nodo.hijos:
            self._consultar_rayo(hijo, rayo, encontrados)

    def consultar_radio(self, centro: Vector3, radio: float) -> list[EntradaEspacial]:
        encontrados: dict[str, EntradaEspacial] = {}
        self._consultar_radio(self.raiz, centro, radio, encontrados)
        return list(encontrados.values())

    def _consultar_radio(self, nodo: NodoOctree, centro: Vector3, radio: float, encontrados: dict[str, EntradaEspacial]) -> None:
        if _distancia_caja(centro, nodo.caja) > radio:
            return
        for objeto in nodo.objetos:
            if _distancia_caja(centro, objeto.caja) <= radio:
                encontrados[objeto.id] = objeto
        for hijo in nodo.hijos:
            self._consultar_radio(hijo, centro, radio, encontrados)


def _distancia_caja(point: Vector3, box: CajaEspacial) -> float:
    dx = max(box.min_x - point.x, 0, point.x - box.max_x)
    dy = max(box.min_y - point.y, 0, point.y - box.max_y)
    dz = max(box.min_z - point.z, 0, point.z - box.max_z)
    return math.sqrt(dx * dx + dy * dy + dz * dz)
