from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from .io_datos import cargar_hotel
from .simulacion import SimuladorUnificado


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulación educativa de iluminación hotelera")
    parser.add_argument("--entrada", default="data/datos_hotel.json")
    parser.add_argument("--salida", default="outputs")
    args = parser.parse_args()

    hotel = cargar_hotel(args.entrada)
    resultados, resumen, propuestas = SimuladorUnificado(hotel).ejecutar()
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    _guardar_json(salida / "resultados.json", resultados, resumen, propuestas)
    _guardar_csv(salida / "reporte.csv", resultados)
    _guardar_json(salida / "resumen.json", [], resumen, propuestas)
    print(f"Simulación completada: {len(resultados)} resultados")
    print(f"Zonas evaluadas: {len(resumen)}")
    print(f"Propuestas de reasignación: {len(propuestas)}")


def _guardar_json(ruta: Path, resultados, resumen, propuestas) -> None:
    payload = {
        "resultados": [asdict(resultado) | {"modo": resultado.modo.value, "estado": resultado.estado.value} for resultado in resultados],
        "resumen": resumen,
        "reasignaciones": propuestas,
    }
    ruta.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _guardar_csv(ruta: Path, resultados) -> None:
    campos = ["zona_id", "hora", "periodo", "modo", "luz_natural", "luz_reflejada", "luz_artificial", "luz_total", "potencia_asignada", "estado"]
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=campos)
        writer.writeheader()
        for resultado in resultados:
            row = asdict(resultado)
            row["modo"] = resultado.modo.value
            row["estado"] = resultado.estado.value
            writer.writerow(row)


if __name__ == "__main__":
    main()
