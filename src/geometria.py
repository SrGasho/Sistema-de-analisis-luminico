from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Vector3:
    x: float
    y: float
    z: float

    def __add__(self, other: Vector3) -> Vector3:
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3) -> Vector3:
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, value: float) -> Vector3:
        return Vector3(self.x * value, self.y * value, self.z * value)

    def dot(self, other: Vector3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def length(self) -> float:
        return math.sqrt(self.dot(self))

    def normalized(self) -> Vector3:
        length = self.length()
        return self if length == 0 else self * (1 / length)

    def distance_to(self, other: Vector3) -> float:
        return (self - other).length()


@dataclass(frozen=True)
class CajaEspacial:
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float

    @property
    def center(self) -> Vector3:
        return Vector3(
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
            (self.min_z + self.max_z) / 2,
        )

    def contains(self, point: Vector3) -> bool:
        return (
            self.min_x <= point.x <= self.max_x
            and self.min_y <= point.y <= self.max_y
            and self.min_z <= point.z <= self.max_z
        )

    def intersects(self, other: CajaEspacial) -> bool:
        return not (
            self.max_x < other.min_x or other.max_x < self.min_x
            or self.max_y < other.min_y or other.max_y < self.min_y
            or self.max_z < other.min_z or other.max_z < self.min_z
        )

    def expanded(self, amount: float) -> CajaEspacial:
        return CajaEspacial(
            self.min_x - amount,
            self.max_x + amount,
            self.min_y - amount,
            self.max_y + amount,
            self.min_z - amount,
            self.max_z + amount,
        )


@dataclass(frozen=True)
class Rayo:
    origen: Vector3
    direccion: Vector3

    def intersects(self, box: CajaEspacial) -> bool:
        direction = self.direccion
        origin = self.origen
        t_min = -math.inf
        t_max = math.inf
        for value, delta, low, high in (
            (origin.x, direction.x, box.min_x, box.max_x),
            (origin.y, direction.y, box.min_y, box.max_y),
            (origin.z, direction.z, box.min_z, box.max_z),
        ):
            if abs(delta) < 1e-12:
                if value < low or value > high:
                    return False
                continue
            t1 = (low - value) / delta
            t2 = (high - value) / delta
            t_min = max(t_min, min(t1, t2))
            t_max = min(t_max, max(t1, t2))
            if t_min > t_max:
                return False
        return t_max >= max(0.0, t_min)
