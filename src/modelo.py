from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .geometria import CajaEspacial, Vector3


class Actividad(str, Enum):
    HABITACION = "HABITACION"
    COCINA = "COCINA"
    RECREACION = "RECREACION"
    PARQUEADERO = "PARQUEADERO"


class ModoOperacion(str, Enum):
    ACTIVA = "ACTIVA"
    REDUCIDA = "REDUCIDA"
    CERRADA = "CERRADA"
    EMERGENCIA = "EMERGENCIA"


class EstadoIluminacion(str, Enum):
    DEFICIT_SEVERO = "DEFICIT_SEVERO"
    DEFICIT_LEVE = "DEFICIT_LEVE"
    CONFORTABLE = "CONFORTABLE"
    EXCESO_LEVE = "EXCESO_LEVE"
    EXCESO_SEVERO = "EXCESO_SEVERO"
    DATOS_INSUFICIENTES = "DATOS_INSUFICIENTES"


@dataclass
class Vidrio:
    tipo: str
    transmitancia_visible: float
    indice_refraccion: float


@dataclass
class Ventana:
    id: str
    posicion: Vector3
    normal: Vector3
    area: float
    vidrio: Vidrio


@dataclass
class SuperficiePared:
    id: str
    posicion: Vector3
    normal: Vector3
    reflectancia: float
    caja: CajaEspacial


@dataclass
class PerfilIluminacion:
    actividad: Actividad
    minimo: float
    objetivo: float
    maximo: float
    prioridad: float
    factor_reducido: float = 0.3

    def para_modo(self, modo: ModoOperacion) -> tuple[float, float, float]:
        if modo == ModoOperacion.REDUCIDA:
            return tuple(v * self.factor_reducido for v in (self.minimo, self.objetivo, self.maximo))
        if modo == ModoOperacion.CERRADA:
            return 0.0, 0.0, self.maximo
        return self.minimo, self.objetivo, self.maximo


@dataclass
class PerfilClimatico:
    nombre: str
    radiacion: float
    nubosidad: float
    precipitacion: float
    factor_luz: float


@dataclass
class FuenteIluminacion:
    id: str
    posicion: Vector3
    potencia_maxima: float
    eficacia: float
    cu: float
    mf: float
    zona_servida: str
    hora_inicio: float
    hora_fin: float

    def activa(self, hora: float) -> bool:
        if self.hora_inicio <= self.hora_fin:
            return self.hora_inicio <= hora < self.hora_fin
        return hora >= self.hora_inicio or hora < self.hora_fin


@dataclass
class ResultadoIluminacion:
    zona_id: str
    hora: float
    periodo: str
    modo: ModoOperacion
    luz_natural: float
    luz_reflejada: float
    luz_artificial: float
    luz_total: float
    potencia_asignada: float
    estado: EstadoIluminacion


@dataclass
class ZonaHotel:
    id: str
    actividad: Actividad
    area: float
    piso: int
    torre_id: str
    modo: ModoOperacion = ModoOperacion.CERRADA
    ventanas: list[Ventana] = field(default_factory=list)
    superficies: list[SuperficiePared] = field(default_factory=list)
    fuente_id: Optional[str] = None
    resultados: list[ResultadoIluminacion] = field(default_factory=list)


@dataclass
class HabitacionHotel(ZonaHotel):
    capacidad: int = 2
    ocupacion: int = 0

    @property
    def disponible(self) -> bool:
        return self.ocupacion < self.capacidad


@dataclass
class Piso:
    numero: int
    zonas: list[ZonaHotel] = field(default_factory=list)

    @property
    def peso(self) -> float:
        return 1.0 + 0.10 * (self.numero - 1)


@dataclass
class Torre:
    id: str
    area_referencia: float
    caja: CajaEspacial
    pisos: list[Piso] = field(default_factory=list)


@dataclass
class Huesped:
    id: str
    actividad: Actividad
    prioridad: float
    restricciones: list[str] = field(default_factory=list)


@dataclass
class Asignacion:
    huesped_id: str
    habitacion_id: str
    estado: str = "ACTIVA"


@dataclass
class GeneradorEnergia:
    capacidad_kw: float
    reserva: float
    potencia_disponible: float = 0.0

    def iniciar_instante(self) -> None:
        self.potencia_disponible = self.capacidad_kw * 1000.0


@dataclass
class Hotel:
    id: str
    torres: list[Torre]
    perfiles_iluminacion: dict[Actividad, PerfilIluminacion]
    perfiles_climaticos: dict[str, PerfilClimatico]
    perfil_climatico_activo: str
    horarios: dict[str, dict]
    fuentes: dict[str, FuenteIluminacion]
    huespedes: dict[str, Huesped]
    asignaciones: list[Asignacion]
    generador: GeneradorEnergia
    zonas: dict[str, ZonaHotel] = field(default_factory=dict)
    habitaciones: dict[str, HabitacionHotel] = field(default_factory=dict)

    def indexar(self) -> None:
        self.zonas.clear()
        self.habitaciones.clear()
        for torre in self.torres:
            for piso in torre.pisos:
                for zona in piso.zonas:
                    self.zonas[zona.id] = zona
                    if isinstance(zona, HabitacionHotel):
                        self.habitaciones[zona.id] = zona

    def zona(self, zona_id: str) -> ZonaHotel:
        return self.zonas[zona_id]
