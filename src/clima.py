from __future__ import annotations

import math
from dataclasses import dataclass

from .geometria import Vector3
from .modelo import PerfilClimatico

LATITUD_BOGOTA = 4.711
DIA_POR_DEFECTO = 46
CONSTANTE_SOLAR_KW = 1.367
SENO_ALTURA_MINIMA = math.sin(math.radians(5.0))


@dataclass(frozen=True)
class Cielo:
    """Condición del cielo en una media hora."""

    global_horizontal: float
    fraccion_difusa: float
    sol: Vector3
    reflectancia_suelo: float

    @property
    def directa_horizontal(self) -> float:
        return self.global_horizontal * (1.0 - self.fraccion_difusa)

    @property
    def difusa_horizontal(self) -> float:
        return self.global_horizontal * self.fraccion_difusa


def declinacion_solar(dia_del_anio: int) -> float:
    """Declinación del sol en radianes (Cooper, 1969)."""
    return math.radians(23.45) * math.sin(2 * math.pi * (284 + dia_del_anio) / 365)


def direccion_solar(hora: float, latitud: float = LATITUD_BOGOTA, dia_del_anio: int = DIA_POR_DEFECTO) -> Vector3:
    """Vector unitario hacia el sol: x = este, y = norte, z = arriba. La hora es hora solar."""
    phi = math.radians(latitud)
    delta = declinacion_solar(dia_del_anio)
    omega = math.radians(15.0 * (hora - 12.0))
    return Vector3(
        -math.cos(delta) * math.sin(omega),
        math.sin(delta) * math.cos(phi) - math.cos(delta) * math.sin(phi) * math.cos(omega),
        math.sin(delta) * math.sin(phi) + math.cos(delta) * math.cos(phi) * math.cos(omega),
    )


def radiacion_extraterrestre_diaria(latitud: float, dia_del_anio: int) -> float:
    """Radiación diaria fuera de la atmósfera sobre un plano horizontal, en kWh/m²/día (Duffie y Beckman, ec. 1.10.3)."""
    phi = math.radians(latitud)
    delta = declinacion_solar(dia_del_anio)
    omega_s = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta))))
    excentricidad = 1 + 0.033 * math.cos(2 * math.pi * dia_del_anio / 365)
    return (24 / math.pi) * CONSTANTE_SOLAR_KW * excentricidad * (
        math.cos(phi) * math.cos(delta) * math.sin(omega_s) + omega_s * math.sin(phi) * math.sin(delta)
    )


def fraccion_difusa_diaria(indice_claridad: float, latitud: float, dia_del_anio: int) -> float:
    """Fracción difusa diaria según el índice de claridad (correlación de Erbs, Klein y Duffie, 1982)."""
    k = min(0.8, max(0.3, indice_claridad))
    phi = math.radians(latitud)
    omega_s = math.degrees(math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(declinacion_solar(dia_del_anio))))))
    if omega_s <= 81.4:
        fraccion = 1.391 - 3.560 * k + 4.189 * k ** 2 - 2.137 * k ** 3
    else:
        fraccion = 1.311 - 3.022 * k + 3.427 * k ** 2 - 1.821 * k ** 3
    return min(1.0, max(0.0, fraccion))


def luz_base(hora: float, perfil: PerfilClimatico, lux_por_irradiancia: float = 900.0, latitud: float = LATITUD_BOGOTA) -> float:
    """Luz global sobre un plano horizontal, en lux de referencia: K · factor_luz · sen(altura del sol)."""
    if hora < 6.0 or hora >= 18.0:
        return 0.0
    seno_altura = direccion_solar(hora, latitud, perfil.dia_del_anio).z
    return lux_por_irradiancia * perfil.factor_luz * max(0.0, seno_altura)


def cielo(hora: float, perfil: PerfilClimatico, lux_por_irradiancia: float, latitud: float, reflectancia_suelo: float) -> Cielo:
    indice = perfil.radiacion / radiacion_extraterrestre_diaria(latitud, perfil.dia_del_anio)
    return Cielo(
        luz_base(hora, perfil, lux_por_irradiancia, latitud),
        fraccion_difusa_diaria(indice, latitud, perfil.dia_del_anio),
        direccion_solar(hora, latitud, perfil.dia_del_anio),
        reflectancia_suelo,
    )


def coseno_incidencia(normal: Vector3, sol: Vector3) -> float:
    return max(0.0, normal.normalized().dot(sol))


def directa_en_vertical(estado: Cielo, coseno: float) -> float:
    """Luz directa sobre una superficie vertical: directa horizontal × cos θ / sen(altura) (Duffie y Beckman, factor Rb)."""
    if coseno <= 0 or estado.global_horizontal <= 0:
        return 0.0
    return estado.directa_horizontal * coseno / max(estado.sol.z, SENO_ALTURA_MINIMA)


def difusa_en_vertical(estado: Cielo, cielo_visible: float = 1.0) -> float:
    """Cielo isotrópico (Liu y Jordan, 1960): una superficie vertical ve medio cielo y medio suelo."""
    return 0.5 * estado.difusa_horizontal * cielo_visible + 0.5 * estado.reflectancia_suelo * estado.global_horizontal


def periodo(hora: float) -> str:
    if hora < 6.0 or hora >= 18.0:
        return "NOCHE"
    if 6.0 <= hora < 7.0 or 17.0 <= hora < 18.0:
        return "TRANSICION"
    return "DIA"
