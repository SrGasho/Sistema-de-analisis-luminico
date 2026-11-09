from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .balance import agregar_energia_postorden, horario_modo
from .evaluacion import estado_predominante, resumen_zonas
from .mejoras import medir_mejoras
from .modelo import ModoOperacion
from .io_datos import cargar_hotel, cargar_hotel_data
from .reestructuracion import buscar_reestructuracion
from .simulacion import SimuladorUnificado
from .sugerencias import generar_sugerencias_habitabilidad

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
                "nombre": torre.get("nombre", torre["id"]),
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


def _layout_hotel(hotel, resumen, veredictos=None):
    veredictos = veredictos or {}
    torres = []
    for torre in hotel.torres:
        pisos = []
        for piso in torre.pisos:
            zonas = []
            for zona in piso.zonas:
                zonas.append({
                    "id": zona.id,
                    "actividad": zona.actividad.value,
                    "piso": piso.numero,
                    "modo": zona.modo.value,
                    "estado": estado_predominante(zona.resultados).value,
                    "veredicto": veredictos.get(zona.id, {}).get("veredicto", "DATOS_INSUFICIENTES"),
                    "promedio_lux": resumen.get(zona.id, {}).get("promedio_lux", 0.0),
                    "posicion": _punto_zona(zona),
                })
            pisos.append({"numero": piso.numero, "zonas": zonas})
        torres.append({
            "id": torre.id,
            "nombre": torre.nombre,
            "caja": {
                "min_x": torre.caja.min_x,
                "max_x": torre.caja.max_x,
                "min_y": torre.caja.min_y,
                "max_y": torre.caja.max_y,
            },
            "pisos": pisos,
        })
    return {"torres": torres}


def _lineas_zonas(hotel) -> dict[str, list]:
    """Día de cada zona, media hora por media hora: [hora, modo, natural, reflejada, artificial, total, estado, mínimo, máximo]."""
    lineas = {}
    for zona in hotel.zonas.values():
        perfil = hotel.perfiles_iluminacion[zona.actividad]
        filas = []
        for r in zona.resultados:
            modo = horario_modo(hotel, zona, r.hora) if r.modo == ModoOperacion.EMERGENCIA else r.modo
            minimo, _, maximo = perfil.para_modo(modo)
            filas.append([r.hora, r.modo.value, round(r.luz_natural, 1), round(r.luz_reflejada, 1), round(r.luz_artificial, 1), round(r.luz_total, 1), r.estado.value, round(minimo, 1), round(maximo, 1)])
        lineas[zona.id] = filas
    return lineas


def _estado_generador(potencia_maxima: float, capacidad: float, emergencias: int) -> str:
    """Capacidad limitada solo si el generador se quedó corto: alguna zona entró en EMERGENCIA o se pasó de la capacidad."""
    if emergencias > 0 or potencia_maxima > capacidad:
        return "CAPACIDAD_LIMITADA"
    if potencia_maxima > capacidad * 0.8:
        return "ALTA_DEMANDA"
    return "OPERACION_NORMAL"


def _generador_resultado(hotel, resultados, resumen, balanceado: bool = True):
    capacidad = hotel.generador.capacidad_kw * 1000.0
    por_hora = {}
    for resultado in resultados:
        por_hora[resultado.hora] = por_hora.get(resultado.hora, 0.0) + resultado.potencia_asignada
    potencia_maxima = max(por_hora.values(), default=0.0)
    emergencias = sum(resultado.modo == ModoOperacion.EMERGENCIA for resultado in resultados)
    return {
        "capacidad_w": capacidad,
        "demanda_maxima_w": potencia_maxima,
        "reserva_w": max(0.0, capacidad - potencia_maxima),
        "porcentaje_usado": 0.0 if capacidad == 0 else min(100.0, potencia_maxima / capacidad * 100.0),
        "estado": _estado_generador(potencia_maxima, capacidad, emergencias) if balanceado else "SIN_BALANCEAR",
        "pasos_emergencia": emergencias,
        "demanda_objetivo_maxima_w": hotel.generador.demanda_objetivo_maxima,
        "por_hora": [{"hora": hora, "potencia_w": potencia} for hora, potencia in sorted(por_hora.items())],
    }


def ejecutar_balance(data: dict, balancear_energia: bool = True, incluir_resultados: bool = True, incluir_lineas: bool = True) -> dict:
    hotel = cargar_hotel_data(data)
    simulador = SimuladorUnificado(hotel)
    resultados, resumen, reasignaciones = simulador.ejecutar(balancear_energia=balancear_energia, comparar_arboles=incluir_resultados)
    habitabilidad = simulador.habitabilidad
    serializados = []
    for resultado in resultados:
        item = asdict(resultado)
        item["modo"] = resultado.modo.value
        item["estado"] = resultado.estado.value
        serializados.append(item)
    estados = {}
    for resultado in resultados:
        estados[resultado.estado.value] = estados.get(resultado.estado.value, 0) + 1
    generador_resultado = _generador_resultado(hotel, resultados, resumen, balancear_energia)
    sugerencias = generar_sugerencias_habitabilidad(hotel, resumen, resultados, generador_resultado, reasignaciones, habitabilidad)
    return {
        "estado": "BALANCE_COMPLETADO" if balancear_energia else "ANALISIS_ACTUAL",
        "resumen": {
            **resumen_inicial(data),
            "resultados_generados": len(resultados),
            "zonas_evaluadas": len(resumen),
            "potencia_maxima_w": max((resultado.potencia_asignada for resultado in resultados), default=0.0),
            "energia_total_wh": sum(resultado.potencia_asignada * 0.5 for resultado in resultados),
            "estados": estados,
            "zonas_con_deficit": sum(1 for e in habitabilidad["zonas"] if e["veredicto"] in ("NO_HABITABLE", "CASI_HABITABLE") and str(e.get("causa") or "").startswith("DEFICIT")),
            "zonas_con_exceso": sum(1 for e in habitabilidad["zonas"] if e["veredicto"] in ("NO_HABITABLE", "CASI_HABITABLE") and str(e.get("causa") or "").startswith("EXCESO")),
            "reasignaciones": len(reasignaciones),
            "habitables": habitabilidad["conteo"].get("HABITABLE", 0),
            "casi_habitables": habitabilidad["conteo"].get("CASI_HABITABLE", 0),
            "no_habitables": habitabilidad["conteo"].get("NO_HABITABLE", 0),
            "sugerencias": len(sugerencias),
        },
        "generador": generador_resultado,
        "layout": _layout_hotel(hotel, resumen, {e["zona_id"]: e for e in habitabilidad["zonas"]}),
        "habitabilidad": habitabilidad,
        "complejidad": {"grafo": simulador.grafo.estadisticas, "reasignacion": simulador.estadisticas_reasignacion, "temporal": simulador.temporal["indices"]},
        "temporal": simulador.temporal["franjas"],
        "energia_arbol": agregar_energia_postorden(hotel),
        "resultados": serializados if incluir_resultados else [],
        "resumen_zonas": resumen,
        "lineas_zonas": _lineas_zonas(hotel) if incluir_lineas else {},
        "reasignaciones": reasignaciones,
        "sugerencias_habitabilidad": sugerencias,
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
                actual = ejecutar_balance(data, balancear_energia=False, incluir_resultados=False)
                self._json({"config": data, "resumen_inicial": resumen_inicial(data), "analisis_actual": actual})
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
            if path == "/api/condicion_actual":
                self._json(ejecutar_balance(data, balancear_energia=False, incluir_resultados=False))
                return
            if path == "/api/mejoras":
                self._json(medir_mejoras(data, lambda config: ejecutar_balance(config, incluir_resultados=False, incluir_lineas=False)))
                return
            if path == "/api/balancear":
                self._json(ejecutar_balance(data))
                return
            if path == "/api/reestructurar":
                self._json(buscar_reestructuracion(data, lambda config: ejecutar_balance(config, incluir_resultados=False, incluir_lineas=False)))
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
