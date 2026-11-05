from __future__ import annotations

from typing import Any, Hashable, Optional


class NodoAVL:
    __slots__ = ("clave", "valor", "izq", "der", "altura")

    def __init__(self, clave: Hashable, valor: Any) -> None:
        self.clave = clave
        self.valor = valor
        self.izq: Optional[NodoAVL] = None
        self.der: Optional[NodoAVL] = None
        self.altura = 1


class IndiceAVL:
    def __init__(self) -> None:
        self.raiz: Optional[NodoAVL] = None
        self.rotaciones = 0
        self.tamano = 0

    def insertar(self, clave: Hashable, valor: Any) -> None:
        self.raiz = self._insertar(self.raiz, clave, valor)
        self.tamano += 1

    def altura(self) -> int:
        return _altura_avl(self.raiz)

    def rango(self, minimo: Hashable, maximo: Hashable) -> list[Any]:
        salida: list[Any] = []

        def visitar(nodo: Optional[NodoAVL]) -> None:
            if nodo is None:
                return
            if minimo < nodo.clave:
                visitar(nodo.izq)
            if minimo <= nodo.clave <= maximo:
                salida.append(nodo.valor)
            if nodo.clave < maximo:
                visitar(nodo.der)

        visitar(self.raiz)
        return salida

    def _insertar(self, nodo: Optional[NodoAVL], clave: Hashable, valor: Any) -> NodoAVL:
        if nodo is None:
            return NodoAVL(clave, valor)
        if clave < nodo.clave:
            nodo.izq = self._insertar(nodo.izq, clave, valor)
        else:
            nodo.der = self._insertar(nodo.der, clave, valor)
        _actualizar_avl(nodo)
        balance = _altura_avl(nodo.izq) - _altura_avl(nodo.der)
        if balance > 1 and clave < nodo.izq.clave:
            return self._rotar_der(nodo)
        if balance < -1 and clave > nodo.der.clave:
            return self._rotar_izq(nodo)
        if balance > 1:
            nodo.izq = self._rotar_izq(nodo.izq)
            return self._rotar_der(nodo)
        if balance < -1:
            nodo.der = self._rotar_der(nodo.der)
            return self._rotar_izq(nodo)
        return nodo

    def _rotar_der(self, y: NodoAVL) -> NodoAVL:
        x = y.izq
        y.izq = x.der
        x.der = y
        _actualizar_avl(y)
        _actualizar_avl(x)
        self.rotaciones += 1
        return x

    def _rotar_izq(self, x: NodoAVL) -> NodoAVL:
        y = x.der
        x.der = y.izq
        y.izq = x
        _actualizar_avl(x)
        _actualizar_avl(y)
        self.rotaciones += 1
        return y


def _altura_avl(nodo: Optional[NodoAVL]) -> int:
    return nodo.altura if nodo else 0


def _actualizar_avl(nodo: NodoAVL) -> None:
    nodo.altura = 1 + max(_altura_avl(nodo.izq), _altura_avl(nodo.der))


class NodoRojoNegro:
    __slots__ = ("clave", "valor", "izq", "der", "padre", "rojo")

    def __init__(self, clave: Hashable, valor: Any) -> None:
        self.clave = clave
        self.valor = valor
        self.izq: Optional[NodoRojoNegro] = None
        self.der: Optional[NodoRojoNegro] = None
        self.padre: Optional[NodoRojoNegro] = None
        self.rojo = True


class IndiceRojoNegro:
    def __init__(self) -> None:
        self.raiz: Optional[NodoRojoNegro] = None
        self.rotaciones = 0
        self.tamano = 0

    def insertar(self, clave: Hashable, valor: Any) -> None:
        nuevo = NodoRojoNegro(clave, valor)
        padre = None
        actual = self.raiz
        while actual is not None:
            padre = actual
            actual = actual.izq if clave < actual.clave else actual.der
        nuevo.padre = padre
        if padre is None:
            self.raiz = nuevo
        elif clave < padre.clave:
            padre.izq = nuevo
        else:
            padre.der = nuevo
        self.tamano += 1
        self._reparar(nuevo)

    def altura(self) -> int:
        def medir(nodo: Optional[NodoRojoNegro]) -> int:
            return 0 if nodo is None else 1 + max(medir(nodo.izq), medir(nodo.der))
        return medir(self.raiz)

    def rango(self, minimo: Hashable, maximo: Hashable) -> list[Any]:
        salida: list[Any] = []

        def visitar(nodo: Optional[NodoRojoNegro]) -> None:
            if nodo is None:
                return
            if minimo < nodo.clave:
                visitar(nodo.izq)
            if minimo <= nodo.clave <= maximo:
                salida.append(nodo.valor)
            if nodo.clave < maximo:
                visitar(nodo.der)

        visitar(self.raiz)
        return salida

    def _reparar(self, z: NodoRojoNegro) -> None:
        while z.padre is not None and z.padre.rojo:
            abuelo = z.padre.padre
            if abuelo is None:
                break
            if z.padre is abuelo.izq:
                tio = abuelo.der
                if tio is not None and tio.rojo:
                    z.padre.rojo = False
                    tio.rojo = False
                    abuelo.rojo = True
                    z = abuelo
                else:
                    if z is z.padre.der:
                        z = z.padre
                        self._rotar_izq(z)
                    z.padre.rojo = False
                    z.padre.padre.rojo = True
                    self._rotar_der(z.padre.padre)
            else:
                tio = abuelo.izq
                if tio is not None and tio.rojo:
                    z.padre.rojo = False
                    tio.rojo = False
                    abuelo.rojo = True
                    z = abuelo
                else:
                    if z is z.padre.izq:
                        z = z.padre
                        self._rotar_der(z)
                    z.padre.rojo = False
                    z.padre.padre.rojo = True
                    self._rotar_izq(z.padre.padre)
        self.raiz.rojo = False

    def _rotar_izq(self, x: NodoRojoNegro) -> None:
        y = x.der
        x.der = y.izq
        if y.izq is not None:
            y.izq.padre = x
        y.padre = x.padre
        if x.padre is None:
            self.raiz = y
        elif x is x.padre.izq:
            x.padre.izq = y
        else:
            x.padre.der = y
        y.izq = x
        x.padre = y
        self.rotaciones += 1

    def _rotar_der(self, x: NodoRojoNegro) -> None:
        y = x.izq
        x.izq = y.der
        if y.der is not None:
            y.der.padre = x
        y.padre = x.padre
        if x.padre is None:
            self.raiz = y
        elif x is x.padre.der:
            x.padre.der = y
        else:
            x.padre.izq = y
        y.der = x
        x.padre = y
        self.rotaciones += 1
