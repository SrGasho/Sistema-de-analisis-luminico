from __future__ import annotations

import math

from .geometria import Vector3
from .modelo import PerfilClimatico


def luz_base(hora: float, perfil: PerfilClimatico) -> float:
    if hora < 6.0 or hora >= 18.0:
        return 0.0
    curva = math.sin(math.pi * (hora - 6.0) / 12.0)
    return 900.0 * curva * perfil.factor_luz


def direccion_solar(hora: float) -> Vector3:
    angulo = math.pi * (hora - 6.0) / 12.0
    return Vector3(math.cos(angulo), math.sin(angulo), 0.7).normalized()


def periodo(hora: float) -> str:
    if hora < 6.0 or hora >= 18.0:
        return "NOCHE"
    if 6.0 <= hora < 7.0 or 17.0 <= hora < 18.0:
        return "TRANSICION"
    return "DIA"
