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

VECTORES_ORIENTACION = {
    "ESTE": Vector3(1, 0, 0),
    "NORTE": Vector3(0, 1, 0),
    "OESTE": Vector3(-1, 0, 0),
    "SUR": Vector3(0, -1, 0),
}


ACABADOS_POR_DEFECTO = {
    "HABITACION": {"pared": "BLANCO", "vidrio": "VIDRIO_CLARO", "orientaciones": ["ESTE", "NORTE", "OESTE", "SUR"]},
    "COCINA": {"pared": "BLANCO", "vidrio": "VIDRIO_LOW_E", "orientaciones": ["ESTE", "NORTE", "OESTE"]},
    "RECREACION": {"pared": "BLANCO", "vidrio": "VIDRIO_LOW_E", "orientaciones": ["ESTE", "NORTE", "OESTE"]},
    "PARQUEADERO": {"pared": "BLANCO", "vidrio": None, "orientaciones": []},
}
VIDRIOS_POR_DEFECTO = {
    "VIDRIO_CLARO": {"transmitancia_visible": 0.82, "indice_refraccion": 1.5},
    "VIDRIO_LOW_E": {"transmitancia_visible": 0.71, "indice_refraccion": 1.5},
    "VIDRIO_CONTROL_SOLAR": {"transmitancia_visible": 0.52, "indice_refraccion": 1.5},
}
PAREDES_POR_DEFECTO = {
    "BLANCO": {"reflectancia": 0.80},
    "CREMA": {"reflectancia": 0.70},
    "GRIS_CLARO": {"reflectancia": 0.60},
    "GRIS_MEDIO": {"reflectancia": 0.45},
    "OSCURO": {"reflectancia": 0.25},
}


def _completar_defaults(data: dict) -> dict:
    data["vidrios"] = {**VIDRIOS_POR_DEFECTO, **data.get("vidrios", {})}
    data["paredes"] = {**PAREDES_POR_DEFECTO, **data.get("paredes", {})}
    acabados = {}
    for actividad, base in ACABADOS_POR_DEFECTO.items():
        acabados[actividad] = {**base, **data.get("acabados", {}).get(actividad, {})}
    data["acabados"] = acabados
    data.setdefault("zonas_personalizadas", {})
    return data


def cargar_hotel(ruta: str | Path) -> Hotel:
    data = json.loads(Path(ruta).read_text(encoding="utf-8"))
    return cargar_hotel_data(data)


def cargar_hotel_data(data: dict) -> Hotel:
    data = _completar_defaults(copy.deepcopy(data))
    _validar_acabados(data)
    perfiles = {
        Actividad(nombre): PerfilIluminacion(Actividad(nombre), **valores)
        for nombre, valores in data["perfiles_iluminacion"].items()
    }
    referencia = data.get("parametros_evaluacion", {}).get("luz", {}).get("radiacion_cielo_despejado")
    if referencia is None:
        referencia = max(valores["radiacion"] for valores in data["perfiles_climaticos"].values())
    climas = {
        nombre: PerfilClimatico(nombre, valores["radiacion"], valores["nubosidad"], valores["precipitacion"], float(referencia))
        for nombre, valores in data["perfiles_climaticos"].items()
    }
    torres: list[Torre] = []
    for tower_data in data["torres"]:
        torre = Torre(
            id=tower_data["id"],
            area_referencia=tower_data["area_referencia"],
            caja=_box(tower_data["caja"]),
            nombre=tower_data.get("nombre", tower_data["id"]),
        )
        room_index = 0
        for piso_numero in range(1, tower_data["pisos"] + 1):
            piso = Piso(piso_numero)
            for _ in range(tower_data["habitaciones_por_piso"]):
                room_index += 1
                zona_id = f"{torre.id}-H-{100 + room_index}"
                piso.zonas.append(_zona_habitacion(zona_id, torre, piso_numero, room_index, tower_data, data))
            if piso_numero == 1:
                for common in tower_data["zonas_comunes"]:
                    for index in range(1, common["cantidad"] + 1):
                        zona_id = f"{torre.id}-{common['codigo']}-{index:02d}"
                        piso.zonas.append(_zona_comun(zona_id, torre, piso_numero, common, index, data))
            torre.pisos.append(piso)
        torres.append(torre)

    hotel = Hotel(
        id=data["hotel"]["id"],
        torres=torres,
        perfiles_iluminacion=perfiles,
        perfiles_climaticos=climas,
        perfil_climatico_activo=data["hotel"]["perfil_climatico"],
        horarios=data.get("horarios", {}),
        parametros=data.get("parametros_evaluacion", {}),
        fuentes={},
        huespedes={},
        asignaciones=[],
        generador=GeneradorEnergia(**data["generador"]),
    )
    hotel.indexar()

    fuentes: dict[str, FuenteIluminacion] = {}
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
        guest_data_list = [
            {
                "id": f"H-{index:03d}",
                "actividad": guest_config["actividad"],
                "prioridad": guest_config.get("prioridad", 1.0),
                "restricciones": guest_config.get("restricciones", []),
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


def _acabado(data: dict, zona_id: str, actividad: str) -> dict:
    base = data["acabados"].get(actividad, {})
    personal = data.get("zonas_personalizadas", {}).get(zona_id, {})
    return {
        "pared": personal.get("pared", base.get("pared", "BLANCO")),
        "vidrio": personal.get("vidrio", base.get("vidrio")),
        "orientaciones": personal.get("orientaciones", base.get("orientaciones", ["NORTE"])),
    }


def _vidrio(data: dict, nombre: str) -> Vidrio:
    valores = data["vidrios"][nombre]
    return Vidrio(nombre, valores["transmitancia_visible"], valores["indice_refraccion"])


def _reflectancia(data: dict, pared: str) -> float:
    return data["paredes"][pared]["reflectancia"]


def _validar_ventanas(zona_id: str, acabado: dict, cantidad: int) -> None:
    if cantidad and acabado["vidrio"] is None:
        raise ValueError(f"La zona {zona_id} tiene ventanas y necesita un vidrio")
    if cantidad and not acabado["orientaciones"]:
        raise ValueError(f"La zona {zona_id} tiene ventanas y necesita al menos una orientación")


def _zona_habitacion(zona_id: str, torre: Torre, piso: int, index: int, config: dict, data: dict) -> HabitacionHotel:
    acabado = _acabado(data, zona_id, "HABITACION")
    _validar_ventanas(zona_id, acabado, 1)
    center = _room_center(torre.caja, piso, index, config["habitaciones_por_piso"])
    orientaciones = acabado["orientaciones"]
    orientation = VECTORES_ORIENTACION[orientaciones[(index - 1) % len(orientaciones)]]
    ventana = Ventana(f"{zona_id}-V1", center + orientation * 0.5, orientation, 2.0, _vidrio(data, acabado["vidrio"]))
    superficie = SuperficiePared(
        f"{zona_id}-P1",
        center,
        orientation * -1,
        _reflectancia(data, acabado["pared"]),
        CajaEspacial(center.x - 0.5, center.x + 0.5, center.y - 0.5, center.y + 0.5, center.z - 0.5, center.z + 0.5),
    )
    return HabitacionHotel(zona_id, Actividad.HABITACION, 24.0, piso, torre.id, ventanas=[ventana], superficies=[superficie], fuente_id=f"L-{zona_id}")


def _zona_comun(zona_id: str, torre: Torre, piso: int, config: dict, index: int, data: dict) -> ZonaHotel:
    actividad = config["actividad"]
    acabado = _acabado(data, zona_id, actividad)
    _validar_ventanas(zona_id, acabado, config["ventanas"])
    center = torre.caja.center + Vector3((index - 1) * 2.0, 0, -torre.caja.center.z + 1.5)
    orientaciones = acabado["orientaciones"]
    ventanas = []
    for window_index in range(config["ventanas"]):
        orientation = VECTORES_ORIENTACION[orientaciones[window_index % len(orientaciones)]]
        ventanas.append(Ventana(
            f"{zona_id}-V{window_index + 1}",
            center + orientation,
            orientation,
            config["area_ventana"],
            _vidrio(data, acabado["vidrio"]),
        ))
    superficie = SuperficiePared(
        f"{zona_id}-P1",
        center,
        Vector3(0, 1, 0),
        _reflectancia(data, acabado["pared"]),
        CajaEspacial(center.x - 1, center.x + 1, center.y - 1, center.y + 1, center.z - 1, center.z + 1),
    )
    return ZonaHotel(zona_id, Actividad(actividad), config["area"], piso, torre.id, ventanas=ventanas, superficies=[superficie], fuente_id=f"L-{zona_id}")


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


def _validar_acabados(data: dict) -> None:
    paredes = data.get("paredes", {})
    vidrios = data.get("vidrios", {})
    for actividad, acabado in data.get("acabados", {}).items():
        if acabado.get("pared") not in paredes:
            raise ValueError(f"Pared no definida para {actividad}: {acabado.get('pared')}")
        if acabado.get("vidrio") is not None and acabado["vidrio"] not in vidrios:
            raise ValueError(f"Vidrio no definido para {actividad}: {acabado.get('vidrio')}")
        for orientacion in acabado.get("orientaciones", []):
            if orientacion not in VECTORES_ORIENTACION:
                raise ValueError(f"Orientación no válida: {orientacion}")
    for zona_id, personal in data.get("zonas_personalizadas", {}).items():
        if "pared" in personal and personal["pared"] not in paredes:
            raise ValueError(f"Pared no definida para {zona_id}: {personal['pared']}")
        if personal.get("vidrio") is not None and personal["vidrio"] not in vidrios:
            raise ValueError(f"Vidrio no definido para {zona_id}: {personal['vidrio']}")
        for orientacion in personal.get("orientaciones", []):
            if orientacion not in VECTORES_ORIENTACION:
                raise ValueError(f"Orientación no válida en {zona_id}: {orientacion}")


def _validar(hotel: Hotel) -> None:
    if len(hotel.torres) != 2:
        raise ValueError("El hotel debe contener exactamente dos torres")
    if len(hotel.zonas) == 0:
        raise ValueError("El hotel no contiene zonas")
    for habitacion in hotel.habitaciones.values():
        if habitacion.ocupacion > habitacion.capacidad:
            raise ValueError(f"Ocupación mayor que la capacidad en {habitacion.id}")
    for asignacion in hotel.asignaciones:
        if asignacion.huesped_id not in hotel.huespedes:
            raise ValueError(f"Huésped inexistente: {asignacion.huesped_id}")
        if asignacion.habitacion_id not in hotel.habitaciones:
            raise ValueError(f"Habitación inexistente: {asignacion.habitacion_id}")
