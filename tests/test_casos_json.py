import json
import unittest
from collections import Counter
from pathlib import Path

from src.api import ejecutar_balance
from src.io_datos import cargar_hotel_data

CASOS = Path(__file__).resolve().parent.parent / "data" / "casos_prueba"
BASE = Path(__file__).resolve().parent.parent / "data" / "datos_hotel.json"


def leer(nombre: str) -> dict:
    return json.loads((CASOS / f"{nombre}.json").read_text(encoding="utf-8"))


def resumen(r: dict) -> dict:
    modos = Counter(x["modo"] for x in r["resultados"])
    return {
        "conteo_veredictos": dict(sorted(r["habitabilidad"]["conteo"].items())),
        "puntaje_hotel": r["habitabilidad"]["puntaje_hotel"]["ponderado"],
        "energia_wh": round(r["resumen"]["energia_total_wh"], 1),
        "estado_generador": r["generador"]["estado"],
        "pasos_emergencia": modos.get("EMERGENCIA", 0),
        "pasos_cerrada": modos.get("CERRADA", 0),
        "reasignaciones": dict(sorted(Counter(f"{p['estado']}:{p['motivo'] or 'PROPUESTA'}" for p in r["reasignaciones"]).items())),
    }


class CasosJson(unittest.TestCase):
    """Cada caso cuenta una situación del hotel y verifica que el sistema se comporte como dice su bloque `caso`."""

    resultados: dict = {}

    @classmethod
    def setUpClass(cls):
        cls.resultados["base"] = ejecutar_balance(json.loads(BASE.read_text(encoding="utf-8")))
        for ruta in sorted(CASOS.glob("*.json")):
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            cls.resultados[ruta.stem] = ejecutar_balance(datos)

    def r(self, nombre):
        return self.resultados[nombre]

    def veredictos(self, nombre):
        return {z["zona_id"]: z for z in self.r(nombre)["habitabilidad"]["zonas"]}

    def pasos(self, nombre, condicion):
        return [x for x in self.r(nombre)["resultados"] if condicion(x)]

    def ocupadas(self, nombre):
        datos = leer(nombre) if nombre != "base" else json.loads(BASE.read_text(encoding="utf-8"))
        return {a.habitacion_id for a in cargar_hotel_data(datos).asignaciones}

    def test_cada_caso_documenta_lo_que_espera(self):
        for ruta in sorted(CASOS.glob("*.json")):
            caso = json.loads(ruta.read_text(encoding="utf-8")).get("caso", {})
            with self.subTest(caso=ruta.stem):
                self.assertEqual(caso.get("nombre"), ruta.stem)
                self.assertTrue(caso.get("historia"))
                self.assertTrue(caso.get("que_se_espera"))
                self.assertEqual(resumen(self.r(ruta.stem)), caso["resultado_esperado"])

    def test_reglas_comunes_a_todos_los_casos(self):
        for nombre in self.resultados:
            with self.subTest(caso=nombre):
                r = self.r(nombre)
                capacidad = r["generador"]["capacidad_w"]
                self.assertLessEqual(r["generador"]["demanda_maxima_w"], capacidad + 1e-6)
                for x in r["resultados"]:
                    if x["periodo"] == "NOCHE":
                        self.assertEqual(x["luz_natural"] + x["luz_reflejada"], 0.0)
                    if x["modo"] == "CERRADA":
                        self.assertEqual((x["potencia_asignada"], x["estado"]), (0.0, "DATOS_INSUFICIENTES"))
                    if x["modo"] == "EMERGENCIA":
                        self.assertTrue(x["estado"].startswith("DEFICIT"), x)
                usados = Counter(p["habitacion_propuesta"] for p in r["reasignaciones"] if p["habitacion_propuesta"])
                hotel = cargar_hotel_data(leer(nombre) if nombre != "base" else json.loads(BASE.read_text(encoding="utf-8")))
                for habitacion_id, n in usados.items():
                    habitacion = hotel.habitaciones[habitacion_id]
                    self.assertLessEqual(n, habitacion.capacidad - habitacion.ocupacion)
                    self.assertEqual(self.veredictos(nombre)[habitacion_id]["veredicto"], "HABITABLE")

    def test_base_operacion_normal(self):
        v = self.veredictos("base")
        self.assertNotIn("NO_HABITABLE", self.r("base")["habitabilidad"]["conteo"])
        self.assertTrue(all(z["causa"] == "EXCESO_SOLAR" for z in v.values() if z["veredicto"] == "CASI_HABITABLE"))
        self.assertEqual(self.r("base")["reasignaciones"], [])
        self.assertEqual(self.pasos("base", lambda x: x["modo"] == "EMERGENCIA"), [])

    def test_temporada_lluvias(self):
        self.assertEqual(self.r("temporada_lluvias")["habitabilidad"]["conteo"], {"HABITABLE": 127})
        self.assertGreaterEqual(self.r("temporada_lluvias")["habitabilidad"]["conteo"]["HABITABLE"], self.r("base")["habitabilidad"]["conteo"]["HABITABLE"])
        self.assertGreater(self.r("temporada_lluvias")["resumen"]["energia_total_wh"], self.r("base")["resumen"]["energia_total_wh"])

    def test_generador_alta_demanda(self):
        r = self.r("generador_alta_demanda")
        self.assertEqual(r["generador"]["estado"], "ALTA_DEMANDA")
        self.assertGreater(r["generador"]["porcentaje_usado"], 80.0)
        self.assertEqual(r["habitabilidad"]["conteo"], self.r("base")["habitabilidad"]["conteo"])

    def test_deficit_leve(self):
        v = self.veredictos("deficit_leve")
        base = self.veredictos("base")
        empeoran = [z for z in v.values() if z["veredicto"] != "HABITABLE" and base[z["zona_id"]]["veredicto"] == "HABITABLE"]
        self.assertTrue(empeoran)
        self.assertTrue(all(z["puntaje_noche"] < base[z["zona_id"]]["puntaje_noche"] for z in empeoran))
        emergencia = {x["zona_id"].split("-")[1] for x in self.pasos("deficit_leve", lambda x: x["modo"] == "EMERGENCIA")}
        self.assertEqual(emergencia, {"REC"})
        self.assertEqual(self.pasos("deficit_leve", lambda x: "-PAR-" in x["zona_id"] and x["estado"].startswith("DEFICIT")), [])
        self.assertTrue(all(v[h]["veredicto"] != "NO_HABITABLE" for h in self.ocupadas("deficit_leve")))

    def test_deficit_severo(self):
        v = self.veredictos("deficit_severo")
        no_habitables = [z for z in v.values() if z["veredicto"] == "NO_HABITABLE"]
        self.assertGreater(len(no_habitables), len(v) / 2)
        self.assertTrue(all(z["causa"] == "DEFICIT_NOCTURNO" for z in no_habitables))
        self.assertEqual({z for z in v if v[z]["veredicto"] == "HABITABLE"}, {"TP-PAR-01", "TG-PAR-01", "TG-PAR-02"})
        self.assertEqual(self.pasos("deficit_severo", lambda x: "-PAR-" in x["zona_id"] and x["modo"] == "EMERGENCIA"), [])
        motivos = {p["motivo"] for p in self.r("deficit_severo")["reasignaciones"]}
        self.assertEqual(motivos, {"SIN_HABITACIONES_HABITABLES_LIBRES"})

    def test_apagon_generador(self):
        r = self.r("apagon_generador")
        self.assertEqual(r["habitabilidad"]["conteo"], {"NO_HABITABLE": 127})
        self.assertEqual(r["resumen"]["energia_total_wh"], 0.0)
        self.assertEqual(len(r["reasignaciones"]), 78)

    def test_cielo_despejado(self):
        v = self.veredictos("cielo_despejado")
        afectadas = [z for z in v.values() if z["veredicto"] != "HABITABLE"]
        self.assertTrue(afectadas)
        self.assertTrue(all(z["causa"] == "EXCESO_SOLAR" for z in afectadas))
        ocupadas_no_habitables = {z for z in v if v[z]["veredicto"] == "NO_HABITABLE"} & self.ocupadas("cielo_despejado")
        propuestas = self.r("cielo_despejado")["reasignaciones"]
        self.assertEqual({p["habitacion_actual"] for p in propuestas}, ocupadas_no_habitables)
        self.assertEqual({p["estado"] for p in propuestas}, {"PROPUESTA"})

    def test_exceso_severo_mueve_huespedes_respetando_sus_pedidos(self):
        r = self.r("exceso_severo")
        v = self.veredictos("exceso_severo")
        no_habitables = {z for z in v if v[z]["veredicto"] == "NO_HABITABLE"}
        self.assertTrue(all("-H-" in z for z in no_habitables))
        self.assertTrue({f"TP-H-{n}" for n in range(101, 125)} <= no_habitables)
        self.assertTrue(all(v[z]["causa"] == "EXCESO_SOLAR" for z in no_habitables))
        propuestas = {p["huesped_id"]: p for p in r["reasignaciones"]}
        self.assertEqual({p["estado"] for p in propuestas.values()}, {"PROPUESTA"})
        self.assertEqual({p["habitacion_actual"] for p in propuestas.values()}, no_habitables & self.ocupadas("exceso_severo"))
        hotel = cargar_hotel_data(leer("exceso_severo"))
        self.assertEqual(hotel.habitaciones[propuestas["H-001"]["habitacion_propuesta"]].torre_id, "TP")
        self.assertLessEqual(hotel.habitaciones[propuestas["H-002"]["habitacion_propuesta"]].piso, 2)
        self.assertEqual(hotel.habitaciones[propuestas["H-003"]["habitacion_propuesta"]].ventanas[0].normal.x, 1)

    def test_reasignacion_restringida(self):
        propuestas = {p["huesped_id"]: p for p in self.r("reasignacion_restringida")["reasignaciones"]}
        hotel = cargar_hotel_data(leer("reasignacion_restringida"))
        en_tp = [p for p in propuestas.values() if p["habitacion_propuesta"] and hotel.habitaciones[p["habitacion_propuesta"]].torre_id == "TP"]
        self.assertEqual(len(en_tp), 12)
        self.assertEqual({h for h, p in propuestas.items() if p["motivo"] == "SIN_CAPACIDAD"}, {"H-017", "H-018"})
        self.assertEqual({h for h, p in propuestas.items() if p["motivo"] == "RESTRICCIONES"}, {"H-019", "H-020"})
        for huesped in ("H-021", "H-022"):
            self.assertEqual(hotel.habitaciones[propuestas[huesped]["habitacion_propuesta"]].torre_id, "TG")


if __name__ == "__main__":
    unittest.main()
