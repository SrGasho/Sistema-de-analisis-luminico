import copy
import json
import math
import unittest
from pathlib import Path

from src.balance import _demanda, balancear, horario_modo
from src.clima import coseno_incidencia, difusa_en_vertical, directa_en_vertical, luz_base
from src.geometria import angulo_refraccion, factor_angular_vidrio
from src.io_datos import cargar_hotel_data
from src.modelo import EstadoIluminacion, ModoOperacion
from src.reasignacion import proponer_reasignaciones
from src.simulacion import SimuladorUnificado, area_interior, reflexion_interior

DATOS = Path(__file__).resolve().parent.parent / "data"


def leer(nombre: str) -> dict:
    return json.loads((DATOS / nombre).read_text(encoding="utf-8"))


def simulador(config: dict) -> SimuladorUnificado:
    return SimuladorUnificado(cargar_hotel_data(config))


def luz_ventana(sim: SimuladorUnificado, zona, ventana, hora: float) -> float:
    estado = sim._cielo(hora)
    coseno = coseno_incidencia(ventana.normal, estado.sol)
    if sim._sombreada(ventana, zona.torre_id, estado.sol):
        coseno = 0.0
    cielo_visible = 1.0 - sim.grafo.obstruccion.get(ventana.id, 0.0)
    directa = directa_en_vertical(estado, coseno) * factor_angular_vidrio(coseno, ventana.vidrio.indice_refraccion)
    return ventana.vidrio.transmitancia_visible * (directa + difusa_en_vertical(estado, cielo_visible))


class CasosDelPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = leer("datos_hotel.json")
        cls.sim = simulador(cls.config)
        cls.resultados, cls.resumen, cls.propuestas = cls.sim.ejecutar()
        cls.por_clave = {(r.zona_id, r.hora): r for r in cls.resultados}

    def test_01_ventana_al_sol_sin_obstaculo(self):
        estado = self.sim._cielo(9.0)
        zona = next(
            z for z in self.sim.hotel.zonas.values()
            if len(z.ventanas) == 1 and coseno_incidencia(z.ventanas[0].normal, estado.sol) > 0.3
            and not self.sim._sombreada(z.ventanas[0], z.torre_id, estado.sol)
        )
        ventana = zona.ventanas[0]
        esperado = luz_ventana(self.sim, zona, ventana, 9.0)
        self.assertAlmostEqual(self.sim._calcular_naturales(9.0)[zona.id], esperado, places=6)
        solo_difusa = ventana.vidrio.transmitancia_visible * difusa_en_vertical(estado, 1.0 - self.sim.grafo.obstruccion.get(ventana.id, 0.0))
        self.assertGreater(esperado, solo_difusa)
        self.assertAlmostEqual(estado.directa_horizontal + estado.difusa_horizontal, estado.global_horizontal, places=9)

    def test_02_ventana_sombreada_por_la_otra_torre(self):
        sombreadas = []
        for hora in (6.5, 7.0, 7.5, 8.0, 16.0, 16.5, 17.0, 17.5):
            sol = self.sim._cielo(hora).sol
            for zona in self.sim.hotel.zonas.values():
                for ventana in zona.ventanas:
                    if coseno_incidencia(ventana.normal, sol) > 0 and self.sim._sombreada(ventana, zona.torre_id, sol):
                        sombreadas.append((hora, zona, ventana))
        self.assertTrue(sombreadas)
        hora, zona, ventana = sombreadas[0]
        estado = self.sim._cielo(hora)
        aportes = [luz_ventana(self.sim, zona, v, hora) for v in zona.ventanas]
        self.assertAlmostEqual(self.sim._calcular_naturales(hora)[zona.id], sum(aportes) / len(aportes), places=6)
        solo_difusa = ventana.vidrio.transmitancia_visible * difusa_en_vertical(estado, 1.0 - self.sim.grafo.obstruccion.get(ventana.id, 0.0))
        self.assertAlmostEqual(aportes[zona.ventanas.index(ventana)], solo_difusa, places=9)

    def test_03_transmision_con_cada_preset_de_vidrio(self):
        naturales = {}
        for vidrio, datos in self.config["vidrios"].items():
            config = copy.deepcopy(self.config)
            config["acabados"]["HABITACION"]["vidrio"] = vidrio
            naturales[vidrio] = (simulador(config)._calcular_naturales(12.0)["TP-H-101"], datos["transmitancia_visible"])
        referencia, vlt_referencia = naturales["VIDRIO_CLARO"]
        for natural, vlt in naturales.values():
            self.assertAlmostEqual(natural / referencia, vlt / vlt_referencia, places=6)
        self.assertAlmostEqual(factor_angular_vidrio(1.0, 1.5), 1.0)
        self.assertLess(factor_angular_vidrio(math.cos(math.radians(75)), 1.5), factor_angular_vidrio(math.cos(math.radians(30)), 1.5))
        self.assertAlmostEqual(math.sin(angulo_refraccion(math.cos(math.radians(60)), 1.5)), math.sin(math.radians(60)) / 1.5)

    def test_04_reflexion_de_primer_orden_sin_cascada(self):
        grafo = self.sim.grafo
        torre_de = {v.id: z.torre_id for z in self.sim.hotel.zonas.values() for v in z.ventanas}
        self.assertTrue(grafo.adyacencias)
        for origen, aristas in grafo.adyacencias.items():
            fachada = grafo.fachadas[origen]
            for arista in aristas:
                self.assertNotEqual(torre_de[arista.destino], fachada.torre_id)
                self.assertLessEqual(arista.peso, fachada.reflectancia)
        self.assertTrue(set(grafo.adyacencias) <= set(grafo.fachadas))
        aportes = self.sim._aportes_naturales(12.0)
        luz_fachadas = self.sim.luz_fachadas(12.0)
        reflejadas = self.sim._calcular_reflejadas(12.0, aportes)
        for zona in self.sim.hotel.zonas.values():
            if not zona.ventanas:
                self.assertEqual(reflejadas[zona.id], 0.0)
                continue
            exteriores = {v.id: sum(luz_fachadas[a.origen] * a.peso for a in grafo.entrantes.get(v.id, [])) * v.vidrio.transmitancia_visible for v in zona.ventanas}
            flujo = sum((aportes[v.id] + exteriores[v.id]) * v.area for v in zona.ventanas)
            rho = zona.superficies[0].reflectancia
            interior = flujo * rho / (area_interior(zona) * (1 - rho))
            self.assertAlmostEqual(reflexion_interior(zona, flujo), interior, places=9)
            self.assertAlmostEqual(reflejadas[zona.id], sum(exteriores.values()) / len(zona.ventanas) + interior, places=6)
        habitacion = self.sim.hotel.zonas["TP-H-102"]
        oscura = copy.deepcopy(self.config)
        oscura["zonas_personalizadas"] = {"TP-H-102": {"pared": "OSCURO"}}
        self.assertGreater(reflejadas["TP-H-102"], simulador(oscura)._calcular_reflejadas(12.0)["TP-H-102"])
        self.assertEqual(self.sim._calcular_reflejadas(20.0)["TP-H-102"], 0.0)
        self.assertEqual(habitacion.superficies[0].reflectancia, 0.80)

    def test_05_noche_sin_luz_natural_y_con_artificial(self):
        ocupada = self.sim.hotel.asignaciones[0].habitacion_id
        for hora in (0.0, 5.5, 18.0, 20.0, 23.5):
            self.assertEqual(self.sim._calcular_naturales(hora), {z: 0.0 for z in self.sim.hotel.zonas})
            self.assertTrue(all(v == 0.0 for v in self.sim._calcular_reflejadas(hora).values()))
        resultado = self.por_clave[(ocupada, 20.0)]
        self.assertEqual(resultado.luz_natural + resultado.luz_reflejada, 0.0)
        self.assertGreater(resultado.luz_artificial, 0.0)
        self.assertNotIn(resultado.estado, (EstadoIluminacion.DEFICIT_LEVE, EstadoIluminacion.DEFICIT_SEVERO))

    def test_06_generador_para_minimos_pero_no_para_objetivos(self):
        hotel = cargar_hotel_data(self.config)
        hora = 20.0
        minimos, objetivos = {}, {}
        for zona in hotel.zonas.values():
            modo = horario_modo(hotel, zona, hora)
            if modo == ModoOperacion.CERRADA or not zona.fuente_id:
                continue
            fuente = hotel.fuentes[zona.fuente_id]
            conversion = fuente.eficacia * fuente.cu * fuente.mf / zona.area
            minimo, objetivo, _ = hotel.perfiles_iluminacion[zona.actividad].para_modo(modo)
            minimos[zona.id] = min(_demanda(minimo, 0.0, conversion), fuente.potencia_maxima)
            objetivos[zona.id] = min(_demanda(objetivo, 0.0, conversion), fuente.potencia_maxima)
        capacidad = (sum(minimos.values()) + sum(objetivos.values())) / 2
        self.assertLess(sum(minimos.values()), capacidad)
        self.assertLess(capacidad, sum(objetivos.values()))
        hotel.generador.capacidad_kw = capacidad / 1000.0
        cero = {z: 0.0 for z in hotel.zonas}
        asignadas = balancear(hotel, hora, cero, cero)
        for zona_id, minimo in minimos.items():
            self.assertGreaterEqual(asignadas[zona_id], minimo - 1e-6)
        self.assertFalse(any(z.modo == ModoOperacion.EMERGENCIA for z in hotel.zonas.values()))
        self.assertAlmostEqual(sum(asignadas.values()), capacidad, places=3)

    def _veredictos(self):
        return {e["zona_id"]: dict(e) for e in self.sim.habitabilidad["zonas"]}

    def test_07_habitacion_ocupada_con_deficit_y_alternativa(self):
        veredictos = self._veredictos()
        habitaciones = self.sim.hotel.habitaciones
        ocupadas = {a.habitacion_id for a in self.sim.hotel.asignaciones}
        con_una_cama = next(h for h in ocupadas if habitaciones[h].capacidad - habitaciones[h].ocupacion == 1)
        for zona_id in habitaciones:
            veredictos[zona_id]["veredicto"] = "NO_HABITABLE"
        veredictos[con_una_cama]["veredicto"] = "HABITABLE"
        propuestas, estadisticas = proponer_reasignaciones(self.sim.hotel, self.resumen, veredictos)
        aceptadas = [p for p in propuestas if p["estado"] == "PROPUESTA"]
        self.assertEqual(len(aceptadas), 1)
        self.assertEqual(aceptadas[0]["habitacion_propuesta"], con_una_cama)
        self.assertTrue(all(p["motivo"] == "SIN_CAPACIDAD" for p in propuestas if p["estado"] != "PROPUESTA"))
        self.assertEqual(estadisticas["avl"]["eliminaciones"], 1)
        self.assertLess(estadisticas["comparaciones_avl"], estadisticas["comparaciones_lineales"])

    def test_08_habitacion_ocupada_con_deficit_sin_alternativa(self):
        sim = simulador(leer("casos_prueba/apagon_generador.json"))
        _, _, propuestas = sim.ejecutar()
        self.assertTrue(propuestas)
        self.assertTrue(all(p["estado"] == "NO_HAY_ALTERNATIVA" and p["motivo"] == "SIN_HABITACIONES_HABITABLES_LIBRES" for p in propuestas))

        veredictos = self._veredictos()
        hotel = self.sim.hotel
        asignacion = hotel.asignaciones[0]
        origen = hotel.habitaciones[asignacion.habitacion_id]
        otra_torre = next(h for h in hotel.habitaciones.values() if h.torre_id != origen.torre_id and h.disponible)
        for zona_id in hotel.habitaciones:
            veredictos[zona_id]["veredicto"] = "NO_HABITABLE"
        veredictos[otra_torre.id]["veredicto"] = "HABITABLE"
        huesped = hotel.huespedes[asignacion.huesped_id]
        anteriores = huesped.restricciones
        huesped.restricciones = ["MISMA_TORRE"]
        try:
            propuestas, _ = proponer_reasignaciones(hotel, self.resumen, veredictos)
        finally:
            huesped.restricciones = anteriores
        propia = next(p for p in propuestas if p["huesped_id"] == huesped.id)
        self.assertEqual((propia["estado"], propia["motivo"]), ("NO_HAY_ALTERNATIVA", "RESTRICCIONES"))

    def test_09_zona_cerrada_y_habitacion_en_descanso_sin_falso_deficit(self):
        cocina = self.por_clave[("TP-COC-01", 2.0)]
        self.assertEqual(cocina.modo, ModoOperacion.CERRADA)
        self.assertEqual(cocina.potencia_asignada, 0.0)
        self.assertEqual(cocina.estado, EstadoIluminacion.DATOS_INSUFICIENTES)
        habitacion = self.por_clave[("TP-H-101", 23.0)]
        self.assertEqual(habitacion.modo, ModoOperacion.REDUCIDA)
        self.assertNotIn(habitacion.estado, (EstadoIluminacion.DEFICIT_LEVE, EstadoIluminacion.DEFICIT_SEVERO))
        evaluacion = next(e for e in self.sim.habitabilidad["zonas"] if e["zona_id"] == "TP-COC-01")
        cerrados = sum(r.modo == ModoOperacion.CERRADA for r in self.resultados if r.zona_id == "TP-COC-01")
        self.assertGreater(cerrados, 0)
        self.assertEqual(evaluacion["pasos_evaluables"], 48 - cerrados)
        self.assertEqual(evaluacion["proporcion_deficit"], 0.0)

    def test_10_nublado_contra_cielo_despejado(self):
        naturales = {}
        for perfil in ("NUBLADO", "CIELO_DESPEJADO"):
            config = copy.deepcopy(self.config)
            config["hotel"]["perfil_climatico"] = perfil
            sim = simulador(config)
            naturales[perfil] = sum(sum(sim._calcular_naturales(paso / 2).values()) for paso in range(12, 36))
            clima = sim.hotel.perfiles_climaticos[perfil]
            self.assertAlmostEqual(clima.factor_luz, min(1.0, clima.radiacion / 7.063))
        self.assertGreater(naturales["CIELO_DESPEJADO"], naturales["NUBLADO"])


if __name__ == "__main__":
    unittest.main()
