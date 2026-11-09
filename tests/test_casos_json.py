import json
import unittest
from collections import Counter
from pathlib import Path

from src.api import ejecutar_balance
from src.io_datos import cargar_hotel_data
from src.modelo import ModoOperacion

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
        viejas = {f"TG-H-{n}" for n in range(113, 125)}
        self.assertEqual({z for z in v if v[z]["veredicto"] != "HABITABLE"}, viejas)
        self.assertTrue(all(v[h]["veredicto"] == "CASI_HABITABLE" and v[h]["causa"] == "DEFICIT_NOCTURNO" for h in viejas))
        estados = {x["estado"] for x in self.pasos("deficit_leve", lambda x: x["estado"].startswith("DEFICIT"))}
        self.assertEqual(estados, {"DEFICIT_LEVE"})
        self.assertEqual(self.pasos("deficit_leve", lambda x: x["modo"] == "EMERGENCIA"), [])
        self.assertEqual(self.r("deficit_leve")["reasignaciones"], [])

    def test_sin_deficit_por_redondeo(self):
        for nombre in self.resultados:
            hotel = cargar_hotel_data(leer(nombre) if nombre != "base" else json.loads(BASE.read_text(encoding="utf-8")))
            with self.subTest(caso=nombre):
                for x in self.pasos(nombre, lambda x: x["estado"] == "DEFICIT_LEVE" and x["modo"] != "EMERGENCIA"):
                    minimo = hotel.perfiles_iluminacion[hotel.zonas[x["zona_id"]].actividad].para_modo(ModoOperacion(x["modo"]))[0]
                    self.assertLess(x["luz_total"], minimo - 1e-6, x)

    def test_causa_de_zona_a_oscuras_es_el_deficit(self):
        diagnostico = ejecutar_balance(json.loads(BASE.read_text(encoding="utf-8")), balancear_energia=False, incluir_resultados=False)
        zonas = {z["zona_id"]: z for z in diagnostico["habitabilidad"]["zonas"]}
        self.assertEqual((zonas["TP-H-103"]["veredicto"], zonas["TP-H-103"]["causa"]), ("NO_HABITABLE", "DEFICIT_DIURNO"))
        for nombre in self.resultados:
            for z in list(self.veredictos(nombre).values()) + list(zonas.values()):
                if z["proporcion_deficit_severo"] and z["proporcion_deficit_severo"] > 0.05:
                    self.assertTrue(z["causa"].startswith("DEFICIT"), (nombre, z))

    def test_deficit_severo(self):
        v = self.veredictos("deficit_severo")
        no_habitables = [z for z in v.values() if z["veredicto"] == "NO_HABITABLE"]
        self.assertGreater(len(no_habitables), len(v) / 2)
        self.assertTrue(all(z["causa"] == "DEFICIT_NOCTURNO" for z in no_habitables))
        self.assertTrue({"TP-PAR-01", "TG-PAR-01", "TG-PAR-02"} <= {z for z in v if v[z]["veredicto"] == "HABITABLE"})
        self.assertEqual(self.pasos("deficit_severo", lambda x: "-PAR-" in x["zona_id"] and x["modo"] == "EMERGENCIA"), [])
        propuestas = self.r("deficit_severo")["reasignaciones"]
        ocupadas = self.ocupadas("deficit_severo")
        self.assertEqual(len(propuestas), len([h for h in ocupadas if v[h]["veredicto"] == "NO_HABITABLE"]))
        self.assertTrue(all(p["estado"] == "PROPUESTA" and p["habitacion_propuesta"] in ocupadas for p in propuestas))

    def test_apagon_generador(self):
        r = self.r("apagon_generador")
        self.assertEqual(r["habitabilidad"]["conteo"], {"NO_HABITABLE": 127})
        self.assertEqual(r["resumen"]["energia_total_wh"], 0.0)
        self.assertEqual(len(r["reasignaciones"]), 78)

    def test_cielo_despejado(self):
        v = self.veredictos("cielo_despejado")
        hotel = cargar_hotel_data(leer("cielo_despejado"))
        afectadas = [z for z in v.values() if z["veredicto"] != "HABITABLE"]
        self.assertTrue(afectadas)
        self.assertTrue(all(z["veredicto"] == "CASI_HABITABLE" and z["causa"] == "EXCESO_SOLAR" for z in afectadas))
        for z in afectadas:
            if z["zona_id"] in hotel.habitaciones:
                self.assertNotEqual(hotel.habitaciones[z["zona_id"]].ventanas[0].normal.x, 0)
        self.assertEqual(self.r("cielo_despejado")["reasignaciones"], [])

    def test_exceso_severo_es_intenso_pero_corto(self):
        v = self.veredictos("exceso_severo")
        ocupadas_tp = {f"TP-H-{n}" for n in range(101, 125)}
        casi = {z for z in ocupadas_tp if v[z]["veredicto"] == "CASI_HABITABLE"}
        self.assertGreater(len(casi), len(ocupadas_tp) / 2)
        self.assertTrue(all(v[z]["causa"] == "EXCESO_SOLAR" for z in ocupadas_tp))
        self.assertFalse(any(v[z]["veredicto"] == "NO_HABITABLE" for z in ocupadas_tp))
        for zona_id in casi:
            severos = self.pasos("exceso_severo", lambda x, z=zona_id: x["zona_id"] == z and x["estado"] == "EXCESO_SEVERO")
            self.assertTrue(severos)
            self.assertTrue(all(x["hora"] < 12 for x in severos))
        self.assertEqual(self.r("exceso_severo")["reasignaciones"], [])

    def test_luminarias_danadas_mueve_huespedes_respetando_sus_pedidos(self):
        r = self.r("luminarias_danadas")
        v = self.veredictos("luminarias_danadas")
        danadas = {f"TP-H-{n}" for n in range(101, 117)}
        self.assertEqual({z for z in v if v[z]["veredicto"] == "NO_HABITABLE"}, danadas)
        self.assertTrue(all(v[z]["causa"] == "DEFICIT_NOCTURNO" for z in danadas))
        propuestas = {p["huesped_id"]: p for p in r["reasignaciones"]}
        self.assertEqual({p["estado"] for p in propuestas.values()}, {"PROPUESTA"})
        self.assertEqual({p["habitacion_actual"] for p in propuestas.values()}, danadas)
        hotel = cargar_hotel_data(leer("luminarias_danadas"))
        self.assertEqual(hotel.habitaciones[propuestas["H-001"]["habitacion_propuesta"]].torre_id, "TP")
        self.assertLessEqual(hotel.habitaciones[propuestas["H-002"]["habitacion_propuesta"]].piso, 2)
        self.assertEqual(hotel.habitaciones[propuestas["H-003"]["habitacion_propuesta"]].ventanas[0].normal.x, 1)
        dia = r["temporal"][0]
        self.assertEqual(dia["zonas_con_deficit"], 16)
        self.assertEqual(dia["energia_no_asignada_wh"], 0.0)

    def test_reasignacion_restringida(self):
        propuestas = {p["huesped_id"]: p for p in self.r("reasignacion_restringida")["reasignaciones"]}
        hotel = cargar_hotel_data(leer("reasignacion_restringida"))
        en_tp = [p for p in propuestas.values() if p["habitacion_propuesta"] and hotel.habitaciones[p["habitacion_propuesta"]].torre_id == "TP"]
        self.assertEqual(len(en_tp), 16)
        self.assertTrue(all(hotel.habitaciones[p["habitacion_propuesta"]].piso == 4 for p in en_tp))
        self.assertEqual({h for h, p in propuestas.items() if p["motivo"] == "SIN_CAPACIDAD"}, {"H-017", "H-018"})
        self.assertEqual({h for h, p in propuestas.items() if p["motivo"] == "RESTRICCIONES"}, {"H-019", "H-020"})
        for huesped in ("H-021", "H-022", "H-023", "H-024"):
            self.assertEqual(hotel.habitaciones[propuestas[huesped]["habitacion_propuesta"]].torre_id, "TG")

if __name__ == "__main__":
    unittest.main()
