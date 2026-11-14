import json
import unittest
from pathlib import Path

from src.io_datos import cargar_hotel, cargar_hotel_data
from src.modelo import Actividad

DATA = Path(__file__).resolve().parent.parent / "data"
BASE = DATA / "datos_hotel.json"


class SalaDeJuegosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hotel = cargar_hotel(BASE)

    def test_actividad_sala_juegos_existe_y_recreacion_no(self):
        self.assertEqual(Actividad("SALA_JUEGOS"), Actividad.SALA_JUEGOS)
        with self.assertRaises(ValueError):
            Actividad("RECREACION")

    def test_zonas_jue_por_torre(self):
        for torre, cantidad in (("TP", 4), ("TG", 6)):
            esperados = {f"{torre}-JUE-{i:02d}" for i in range(1, cantidad + 1)}
            encontrados = {z for z in self.hotel.zonas if z.startswith(f"{torre}-JUE-")}
            self.assertEqual(encontrados, esperados)
            for zona_id in esperados:
                zona = self.hotel.zonas[zona_id]
                self.assertEqual(zona.actividad, Actividad.SALA_JUEGOS)
                self.assertEqual(zona.area, 80)
                self.assertEqual(len(zona.ventanas), 3)
        self.assertFalse([z for z in self.hotel.zonas if "-REC-" in z])

    def test_perfil_sala_juegos(self):
        perfil = self.hotel.perfiles_iluminacion[Actividad.SALA_JUEGOS]
        self.assertEqual((perfil.minimo, perfil.objetivo, perfil.maximo, perfil.prioridad), (200, 300, 500, 2))

    def test_claves_de_configuracion(self):
        self.assertIn("SALA_JUEGOS", self.hotel.horarios)
        self.assertEqual(self.hotel.horarios["SALA_JUEGOS"]["inicio_activa"], 8)
        self.assertEqual(self.hotel.horarios["SALA_JUEGOS"]["fin_activa"], 23)
        self.assertNotIn("RECREACION", self.hotel.horarios)

    def test_ningun_json_menciona_recreacion(self):
        for ruta in [BASE, *sorted((DATA / "casos_prueba").glob("*.json"))]:
            texto = ruta.read_text(encoding="utf-8")
            with self.subTest(archivo=ruta.name):
                self.assertNotIn("RECREACION", texto)
                self.assertNotIn('"REC"', texto)
                self.assertNotIn("-REC-", texto)
                self.assertNotIn("recreaci", texto.lower())

    def test_escenario_viejo_falla_claro(self):
        data = json.loads(BASE.read_text(encoding="utf-8"))
        perfiles = data["perfiles_iluminacion"]
        perfiles["RECREACION"] = perfiles.pop("SALA_JUEGOS")
        with self.assertRaises(ValueError):
            cargar_hotel_data(data)


if __name__ == "__main__":
    unittest.main()
