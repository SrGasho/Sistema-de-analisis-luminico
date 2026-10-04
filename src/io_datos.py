from __future__ import annotations

import copy
import json
from pathlib import Path

from .geometria import CajaEspacial, Vector3
from .modelo import (
    Actividad,
    Asignacion,
    FuenteIluminacion,
    GeneradorEnergia,
    HabitacionHotel,
    Hotel,
    Huesped,
    PerfilClimatico,
    PerfilIluminacion,
    Piso,
    SuperficiePared,
    Torre,
    Ventana,
    Vidrio,
    ZonaHotel,
)


def cargar_hotel(ruta: str | Path) -> Hotel:
    data = json.loads(Path(ruta).read_text(encoding="utf-8"))
    return cargar_hotel_data(data)


def cargar_hotel_data(data: dict) -> Hotel:
    data = copy.deepcopy(data)
    perfiles = {
        Actividad(nombre): PerfilIluminacion(Actividad(nombre), **valores)
        for nombre, valores in data["perfiles_iluminacion"].items()
    }
    climas = {
        nombre: PerfilClimatico(nombre, **valores)
        for nombre, valores in data["perfiles_climaticos"].items()
    }
    fuentes: dict[str, FuenteIluminacion] = {}
    torres: list[Torre] = []
    for tower_data in data["torres"]:
        torre = Torre(
            id=tower_data["id"],
            area_referencia=tower_data["area_referencia"],
            caja=_box(tower_data["caja"]),
        )
        room_index = 0
        for piso_numero in range(1, tower_data["pisos"] + 1):
            piso = Piso(piso_numero)
            for _ in range(tower_data["habitaciones_por_piso"]):
                room_index += 1
                zona_id = f"{torre.id}-H-{100 + room_index}"
                zona = _zona_habitacion(zona_id, torre, piso_numero, room_index, tower_data)
                piso.zonas.append(zona)
            if piso_numero == 1:
                for common in tower_data["zonas_comunes"]:
                    for index in range(1, common["cantidad"] + 1):
                        zona_id = f"{torre.id}-{common['codigo']}-{index:02d}"
                        zona = _zona_comun(zona_id, torre, piso_numero, common, index)
                        piso.zonas.append(zona)
            torre.pisos.append(piso)
        torres.append(torre)

    hotel = Hotel(
        id=data["hotel"]["id"],
        torres=torres,
        perfiles_iluminacion=perfiles,
        perfiles_climaticos=climas,
        perfil_climatico_activo=data["hotel"]["perfil_climatico"],
        fuentes=fuentes,
        huespedes={},
        asignaciones=[],
        generador=GeneradorEnergia(**data["generador"]),
    )
    hotel.indexar()
    for zona in hotel.zonas.values():
        if zona.fuente_id:
            config = data["luminarias"][zona.actividad.value]
            fuente = FuenteIluminacion(
                id=zona.fuente_id,
                posicion=zona.ventanas[0].posicion if zona.ventanas else _zona_center(zona),
                potencia_maxima=config["potencia_w"],
                eficacia=config["eficacia_lm_w"],
                cu=config["cu"],
                mf=config["mf"],
                zona_servida=zona.id,
                hora_inicio=0.0,
                hora_fin=24.0,
            )
            fuentes[fuente.id] = fuente
    hotel.fuentes = fuentes
    guest_config = data["huespedes"]
    if isinstance(guest_config, dict):
        total_huespedes = guest_config["total"]
        guest_template = guest_config
        guest_data_list = [
            {
                "id": f"H-{index:03d}",
                "actividad": guest_template["actividad"],
                "prioridad": guest_template.get("prioridad", 1.0),
                "restricciones": guest_template.get("restricciones", []),
            }
            for index in range(1, total_huespedes + 1)
        ]
    else:
        guest_data_list = guest_config
    for guest_data in guest_data_list:
        guest = Huesped(
            id=guest_data["id"],
            actividad=Actividad(guest_data["actividad"]),
            prioridad=guest_data.get("prioridad", 1.0),
            restricciones=guest_data.get("restricciones", []),
        )
        hotel.huespedes[guest.id] = guest

    assignments = data.get("asignaciones", [])
    if not assignments and isinstance(guest_config, dict):
        guest_index = 1
        for tower_data in data["torres"]:
            occupied = tower_data.get("habitaciones_ocupadas", 0)
            for room_index in range(1, occupied + 1):
                if guest_index > guest_config["total"]:
                    break
                assignments.append({
                    "huesped_id": f"H-{guest_index:03d}",
                    "habitacion_id": f"{tower_data['id']}-H-{100 + room_index}",
                })
                guest_index += 1
    for assignment in assignments:
        asignacion = Asignacion(**assignment)
        hotel.asignaciones.append(asignacion)
        if asignacion.habitacion_id in hotel.habitaciones:
            hotel.habitaciones[asignacion.habitacion_id].ocupacion += 1
    _validar(hotel)
    return hotel


def _zona_habitacion(zona_id: str, torre: Torre, piso: int, index: int, config: dict) -> HabitacionHotel:
    center = _room_center(torre.caja, piso, index, config["habitaciones_por_piso"])
    orientation = [Vector3(1, 0, 0), Vector3(0, 1, 0), Vector3(-1, 0, 0), Vector3(0, -1, 0)][(index - 1) % 4]
    ventana = Ventana(f"{zona_id}-V1", center + orientation * 0.5, orientation, 2.0, Vidrio("VIDRIO_CLARO", 0.82, 1.5))
    superficie = SuperficiePared(f"{zona_id}-P1", center, orientation * -1, 0.70, CajaEspacial(center.x - 0.5, center.x + 0.5, center.y - 0.5, center.y + 0.5, center.z - 0.5, center.z + 0.5))
    return HabitacionHotel(zona_id, Actividad.HABITACION, 24.0, piso, torre.id, ventanas=[ventana], superficies=[superficie], fuente_id=f"L-{zona_id}")


def _zona_comun(zona_id: str, torre: Torre, piso: int, config: dict, index: int) -> ZonaHotel:
    center = torre.caja.center + Vector3((index - 1) * 2.0, 0, -torre.caja.center.z + 1.5)
    ventanas = []
    for window_index in range(config["ventanas"]):
        orientation = [Vector3(1, 0, 0), Vector3(0, 1, 0), Vector3(-1, 0, 0)][window_index % 3]
        ventanas.append(Ventana(f"{zona_id}-V{window_index + 1}", center + orientation, orientation, config["area_ventana"], Vidrio("VIDRIO_LOW_E", 0.71, 1.5)))
    superficie = SuperficiePared(f"{zona_id}-P1", center, Vector3(0, 1, 0), 0.70, CajaEspacial(center.x - 1, center.x + 1, center.y - 1, center.y + 1, center.z - 1, center.z + 1))
    return ZonaHotel(zona_id, Actividad(config["actividad"]), config["area"], piso, torre.id, ventanas=ventanas, superficies=[superficie], fuente_id=f"L-{zona_id}")


def _room_center(box: CajaEspacial, piso: int, index: int, rooms_per_floor: int) -> Vector3:
    columns = max(1, int(rooms_per_floor ** 0.5))
    row = (index - 1) // columns
    column = (index - 1) % columns
    width = (box.max_x - box.min_x) / (columns + 1)
    depth = (box.max_y - box.min_y) / (rooms_per_floor // columns + 2)
    return Vector3(box.min_x + (column + 1) * width, box.min_y + (row + 1) * depth, (piso - 0.5) * 3.0)


def _zona_center(zona: ZonaHotel) -> Vector3:
    if zona.ventanas:
        return zona.ventanas[0].posicion
    if zona.superficies:
        return zona.superficies[0].posicion
    return Vector3(0, 0, 0)


def _box(values: dict) -> CajaEspacial:
    return CajaEspacial(values["min_x"], values["max_x"], values["min_y"], values["max_y"], values["min_z"], values["max_z"])


def _validar(hotel: Hotel) -> None:
    if len(hotel.torres) != 2:
        raise ValueError("El hotel debe contener exactamente dos torres")
    if len(hotel.zonas) == 0:
        raise ValueError("El hotel no contiene zonas")
    for asignacion in hotel.asignaciones:
        if asignacion.huesped_id not in hotel.huespedes:
            raise ValueError(f"Huésped inexistente: {asignacion.huesped_id}")
        if asignacion.habitacion_id not in hotel.habitaciones:
            raise ValueError(f"Habitación inexistente: {asignacion.habitacion_id}")
