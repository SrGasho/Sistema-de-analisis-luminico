import copy
import json
import math
import unittest
from pathlib import Path

from src.balance import _demanda, balancear, horario_modo
from src.clima import direccion_solar, luz_base
from src.geometria import angulo_refraccion, factor_angular_vidrio
from src.io_datos import cargar_hotel_data
from src.modelo import EstadoIluminacion, ModoOperacion
from src.reasignacion import proponer_reasignaciones
from src.simulacion import SimuladorUnificado

DATOS = Path(__file__).resolve().parent.parent / "data"


def leer(nombre: str) -> dict:
    return json.loads((DATOS / nombre).read_text(encoding="utf-8"))


def simulador(config: dict) -> SimuladorUnificado:
    return SimuladorUnificado(cargar_hotel_data(config))


def factores_cielo(sim: SimuladorUnificado) -> tuple[float, float, float]:
    perfil = sim.hotel.perfiles_climaticos[sim.hotel.perfil_climatico_activo]
    return luz_base(9.0, perfil, sim._lux_por_irradiancia), max(0.10, 1.0 - perfil.nubosidad), 0.15 + 0.45 * perfil.nubosidad


class CasosDelPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = leer("datos_hotel.json")
        cls.sim = simulador(cls.config)
        cls.resultados, cls.resumen, cls.propuestas = cls.sim.ejecutar()
        cls.por_clave = {(r.zona_id, r.hora): r for r in cls.resultados}

    def test_01_ventana_al_sol_sin_obstaculo(self):
        base, f_directa, f_difusa = factores_cielo(self.sim)
        direccion = direccion_solar(9.0)
        zona = next(
            z for z in self.sim.hotel.zonas.values()
            if len(z.ventanas) == 1 and z.ventanas[0].normal.dot(direccion) > 0.3
            and not self.sim._sombreada(z.ventanas[0], z.torre_id, direccion)
        )
        ventana = zona.ventanas[0]
        coseno = ventana.normal.normalized().dot(direccion)
        esperado = base * ventana.vidrio.transmitancia_visible * (coseno * factor_angular_vidrio(coseno, 1.5) * f_directa + f_difusa)
        self.assertAlmostEqual(self.sim._calcular_naturales(9.0)[zona.id], esperado, places=6)
        self.assertGreater(esperado, base * ventana.vidrio.transmitancia_visible * f_difusa)

    def test_02_ventana_sombreada_por_la_otra_torre(self):
        sombreadas = []
        for hora in (7.0, 8.0, 9.0, 10.0, 14.0, 16.0, 17.0):
            direccion = direccion_solar(hora)
            for zona in self.sim.hotel.zonas.values():
                for ventana in zona.ventanas:
                    if ventana.normal.dot(direccion) > 0 and self.sim._sombreada(ventana, zona.torre_id, direccion):
                        sombreadas.append((hora, zona, ventana))
        self.assertTrue(sombreadas)
        hora, zona, ventana = sombreadas[0]
        perfil = self.sim.hotel.perfiles_climaticos[self.sim.hotel.perfil_climatico_activo]
        base = luz_base(hora, perfil, self.sim._lux_por_irradiancia)
        f_difusa = 0.15 + 0.45 * perfil.nubosidad
        f_directa = max(0.10, 1.0 - perfil.nubosidad)
        direccion = direccion_solar(hora)
        aportes = []
        for v in zona.ventanas:
            coseno = max(0.0, v.normal.normalized().dot(direccion))
            if self.sim._sombreada(v, zona.torre_id, direccion):
                coseno = 0.0
            aportes.append(base * v.vidrio.transmitancia_visible * (coseno * factor_angular_vidrio(coseno, 1.5) * f_directa + f_difusa))
        self.assertAlmostEqual(self.sim._calcular_naturales(hora)[zona.id], sum(aportes) / len(aportes), places=6)
        self.assertAlmostEqual(aportes[zona.ventanas.index(ventana)], base * ventana.vidrio.transmitancia_visible * f_difusa, places=9)

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
        perfil = self.sim.hotel.perfiles_climaticos[self.sim.hotel.perfil_climatico_activo]
        base = luz_base(12.0, perfil, self.sim._lux_por_irradiancia)
        luz = {s.id: base * s.reflectancia for z in self.sim.hotel.zonas.values() for s in z.superficies}
        reflejadas = self.sim._calcular_reflejadas(12.0)
        con_aristas = 0
        for zona in self.sim.hotel.zonas.values():
            if not zona.ventanas:
                continue
            aportes = [sum(luz[a.origen] * a.peso for a in self.sim.grafo.entrantes.get(v.id, [])) for v in zona.ventanas]
            self.assertAlmostEqual(reflejadas[zona.id], sum(aportes) / len(aportes), places=6)
            con_aristas += any(aportes)
        self.assertGreater(con_aristas, 0)
        ventanas = {v.id for z in self.sim.hotel.zonas.values() for v in z.ventanas}
        self.assertTrue(all(origen not in ventanas for origen in self.sim.grafo.adyacencias))

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
        sim = simulador(leer("casos_prueba/deficit_severo.json"))
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
            naturales[perfil] = sum(sim._calcular_naturales(12.0).values())
            clima = sim.hotel.perfiles_climaticos[perfil]
            self.assertAlmostEqual(clima.factor_luz, min(1.0, clima.radiacion / 7.063))
        self.assertGreater(naturales["CIELO_DESPEJADO"], naturales["NUBLADO"])


if __name__ == "__main__":
    unittest.main()
