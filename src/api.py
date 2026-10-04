from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .evaluacion import resumen_zonas
from .io_datos import cargar_hotel, cargar_hotel_data
from .simulacion import SimuladorUnificado

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
DEFAULT_INPUT = ROOT / "data" / "datos_hotel.json"


def leer_escenario() -> dict:
    return json.loads(DEFAULT_INPUT.read_text(encoding="utf-8"))


def resumen_inicial(data: dict) -> dict:
    actividades = {}
    for torre in data["torres"]:
        for zona in torre["zonas_comunes"]:
            actividades[zona["actividad"]] = actividades.get(zona["actividad"], 0) + zona["cantidad"]
        actividades["HABITACION"] = actividades.get("HABITACION", 0) + torre["pisos"] * torre["habitaciones_por_piso"]
    return {
        "hotel_id": data["hotel"]["id"],
        "perfil_climatico": data["hotel"]["perfil_climatico"],
        "torres": [
            {
                "id": torre["id"],
                "pisos": torre["pisos"],
                "habitaciones": torre["pisos"] * torre["habitaciones_por_piso"],
                "habitaciones_ocupadas": torre.get("habitaciones_ocupadas", 0),
                "zonas_comunes": sum(zona["cantidad"] for zona in torre["zonas_comunes"]),
            }
            for torre in data["torres"]
        ],
        "actividades": actividades,
        "generador_kw": data["generador"]["capacidad_kw"],
        "huespedes": data["huespedes"].get("total", len(data["huespedes"])) if isinstance(data["huespedes"], dict) else len(data["huespedes"]),
    }


def validar(data: dict) -> dict:
    hotel = cargar_hotel_data(data)
    return {"valido": True, "resumen": resumen_inicial(data), "zonas_generadas": len(hotel.zonas), "habitaciones_generadas": len(hotel.habitaciones)}


def _punto_zona(zona):
    if zona.superficies:
        punto = zona.superficies[0].posicion
    elif zona.ventanas:
        punto = zona.ventanas[0].posicion
    else:
        from .geometria import Vector3
        punto = Vector3(0, 0, 0)
    dimensiones = {
        "HABITACION": (4.0, 3.0),
        "COCINA": (7.0, 5.0),
        "RECREACION": (10.0, 7.0),
        "PARQUEADERO": (15.0, 9.0),
    }
    ancho, alto = dimensiones[zona.actividad.value]
    return {"x": punto.x, "y": punto.y, "z": punto.z, "ancho": ancho, "alto": alto}


def _layout_hotel(hotel, resumen):
    torres = []
    for torre in hotel.torres:
        pisos = []
        for piso in torre.pisos:
            zonas = []
            for zona in piso.zonas:
                resultados = zona.resultados
                ultimo = resultados[-1] if resultados else None
                zonas.append({
                    "id": zona.id,
                    "actividad": zona.actividad.value,
                    "piso": piso.numero,
                    "modo": zona.modo.value,
                    "estado": ultimo.estado.value if ultimo else "DATOS_INSUFICIENTES",
                    "promedio_lux": resumen.get(zona.id, {}).get("promedio_lux", 0.0),
                    "posicion": _punto_zona(zona),
                })
            pisos.append({"numero": piso.numero, "zonas": zonas})
        torres.append({
            "id": torre.id,
            "caja": {
                "min_x": torre.caja.min_x,
                "max_x": torre.caja.max_x,
                "min_y": torre.caja.min_y,
                "max_y": torre.caja.max_y,
            },
            "pisos": pisos,
        })
    return {"torres": torres}


def _estado_generador(potencia_maxima: float, capacidad: float, deficit: int) -> str:
    if deficit > 0 or potencia_maxima > capacidad:
        return "CAPACIDAD_LIMITADA"
    if potencia_maxima > capacidad * 0.8:
        return "ALTA_DEMANDA"
    return "OPERACION_NORMAL"


def _generador_resultado(hotel, resultados, resumen):
    capacidad = hotel.generador.capacidad_kw * 1000.0
    por_hora = {}
    for resultado in resultados:
        por_hora[resultado.hora] = por_hora.get(resultado.hora, 0.0) + resultado.potencia_asignada
    potencia_maxima = max(por_hora.values(), default=0.0)
    deficit = sum(datos["pasos_deficit"] > 0 for datos in resumen.values())
    return {
        "capacidad_w": capacidad,
        "demanda_maxima_w": potencia_maxima,
        "reserva_w": max(0.0, capacidad - potencia_maxima),
        "porcentaje_usado": 0.0 if capacidad == 0 else min(100.0, potencia_maxima / capacidad * 100.0),
        "estado": _estado_generador(potencia_maxima, capacidad, deficit),
        "por_hora": [{"hora": hora, "potencia_w": potencia} for hora, potencia in sorted(por_hora.items())],
    }


def ejecutar_balance(data: dict) -> dict:
    hotel = cargar_hotel_data(data)
    resultados, resumen, reasignaciones = SimuladorUnificado(hotel).ejecutar()
    serializados = []
    for resultado in resultados:
        item = asdict(resultado)
        item["modo"] = resultado.modo.value
        item["estado"] = resultado.estado.value
        serializados.append(item)
    estados = {}
    for resultado in resultados:
        estados[resultado.estado.value] = estados.get(resultado.estado.value, 0) + 1
    return {
        "estado": "COMPLETADO",
        "resumen": {
            **resumen_inicial(data),
            "resultados_generados": len(resultados),
            "zonas_evaluadas": len(resumen),
            "potencia_maxima_w": max((resultado.potencia_asignada for resultado in resultados), default=0.0),
            "energia_total_wh": sum(resultado.potencia_asignada * 0.5 for resultado in resultados),
            "estados": estados,
            "zonas_con_deficit": sum(datos["pasos_deficit"] > 0 for datos in resumen.values()),
            "zonas_con_exceso": sum(datos["pasos_exceso"] > 0 for datos in resumen.values()),
            "reasignaciones": len(reasignaciones),
        },
        "generador": _generador_resultado(hotel, resultados, resumen),
        "layout": _layout_hotel(hotel, resumen),
        "resultados": serializados,
        "resumen_zonas": resumen,
        "reasignaciones": reasignaciones,
        "advertencias": ["Los resultados son aproximaciones educativas y usan lux de referencia."] if resultados else [],
    }


class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json({"estado": "OK"})
            return
        if path == "/api/escenario":
            try:
                data = leer_escenario()
                self._json({"config": data, "resumen_inicial": resumen_inicial(data)})
            except Exception as error:
                self._error(error)
            return
        self._static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if path == "/api/validar":
                self._json(validar(data))
                return
            if path == "/api/balancear":
                self._json(ejecutar_balance(data))
                return
            self._json({"error": "Ruta no encontrada"}, 404)
        except Exception as error:
            self._error(error)

    def _static(self, path: str) -> None:
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        target = (WEB / relative).resolve()
        if WEB.resolve() not in target.parents and target != WEB.resolve():
            self._json({"error": "Ruta no permitida"}, 403)
            return
        if not target.is_file():
            self._json({"error": "Archivo no encontrado"}, 404)
            return
        content_type = "text/html; charset=utf-8"
        if target.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif target.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, error: Exception) -> None:
        self._json({"error": str(error)}, 400)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor web del análisis lumínico hotelero")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        data = leer_escenario()
        print(json.dumps(validar(data), ensure_ascii=False))
        return
    server = ThreadingHTTPServer((args.host, args.port), WebHandler)
    print(f"Servidor web disponible en http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
